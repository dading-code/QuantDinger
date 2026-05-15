from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from typing import Any, Dict, List
from datetime import datetime, timezone

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from app.utils.logger import get_logger
from app.utils.db import get_db_connection

logger = get_logger(__name__)


_background_loop: asyncio.AbstractEventLoop | None = None
_bg_loop_lock = threading.Lock()


def get_background_loop() -> asyncio.AbstractEventLoop:
    global _background_loop
    if _background_loop is not None:
        return _background_loop
    with _bg_loop_lock:
        if _background_loop is not None:
            return _background_loop
        _background_loop = asyncio.new_event_loop()
        t = threading.Thread(
            target=_background_loop.run_forever,
            daemon=True,
            name="ws-bg-loop",
        )
        t.start()
        logger.info("Background asyncio event loop started for WebSocket sync calls")
        return _background_loop


class WebSocketSignalHub:
    def __init__(self):
        self._lock = threading.Lock()
        self.clients: Dict[str, WebSocketServerProtocol] = {}
        self.client_metadata: Dict[str, Dict[str, Any]] = {}
        self.backlog: List[Dict[str, Any]] = []
        self.max_backlog_size = 100
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'messages_sent': 0,
            'messages_failed': 0,
        }
        logger.info("WebSocketSignalHub initialized")

    async def register_client(
        self,
        websocket: WebSocketServerProtocol,
        api_key: str,
        credential_id: int | None = None,
        broker_account_id: str | None = None,
    ) -> str | None:
        client_id = str(uuid.uuid4())

        from app.services.api_key_manager import APIKeyService
        user_info = APIKeyService.validate_api_key(api_key)

        if not user_info:
            await websocket.close(code=4001, reason="Invalid API key")
            logger.warning("Client rejected: invalid API key")
            return None

        user_id = user_info['user_id']
        cred_id = credential_id or user_info.get('credential_id')
        validation_result = self._validate_broker_account(user_id, cred_id, broker_account_id)

        if not validation_result['valid']:
            error_msg = validation_result.get('error', 'Broker account mismatch')
            await websocket.close(code=4002, reason=error_msg)
            logger.warning(
                f"Client rejected: broker account validation failed for user {user_info['username']}. "
                f"Reason: {error_msg}"
            )
            return None

        metadata = {
            'client_id': client_id,
            'api_key': api_key,
            'user_id': user_id,
            'username': user_info['username'],
            'email': user_info['email'],
            'connected_at': datetime.now(timezone.utc).isoformat(),
            'last_heartbeat': time.time(),
            'ip_address': websocket.remote_address[0] if websocket.remote_address else None,
            'broker_account_id': broker_account_id,
            'broker_validated': validation_result.get('validated', False),
        }

        with self._lock:
            self.clients[client_id] = websocket
            self.client_metadata[client_id] = metadata
            self.stats['total_connections'] += 1
            self.stats['active_connections'] = len(self.clients)

        logger.info(
            f"Client registered: {client_id} for user: {user_info['username']} "
            f"(broker: {broker_account_id}, validated: {validation_result.get('validated', False)})"
        )

        await self._send_to_client(client_id, {
            'type': 'connection_established',
            'client_id': client_id,
            'message': f'Welcome {user_info["username"]}, connected to QuantDinger Signal Hub',
            'user': {
                'username': user_info['username'],
                'email': user_info['email'],
                'role': user_info['role'],
            },
            'broker_validation': {
                'valid': validation_result['valid'],
                'validated': validation_result.get('validated', False),
                'expected_account': validation_result.get('expected_account'),
                'actual_account': validation_result.get('actual_account'),
            },
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })

        recent = []
        with self._lock:
            recent = list(self.backlog)
        if recent:
            await self._send_to_client(client_id, {
                'type': 'backlog_replay',
                'count': len(recent),
                'signals': recent,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            })
            logger.debug(f"Replayed {len(recent)} backlog signals to client {client_id}")

        asyncio.create_task(self._monitor_heartbeat(client_id))
        return client_id

    async def unregister_client(self, client_id: str):
        with self._lock:
            self.clients.pop(client_id, None)
            self.client_metadata.pop(client_id, None)
            self.stats['active_connections'] = len(self.clients)
        logger.info(f"Client unregistered: {client_id} (remaining: {self.stats['active_connections']})")

    async def broadcast_signal(self, signal_data: Dict[str, Any], target_user_id: int | None = None):
        message = {
            'type': 'trading_signal',
            'signal_id': str(uuid.uuid4()),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': signal_data,
        }

        with self._lock:
            self.backlog.append(message)
            if len(self.backlog) > self.max_backlog_size:
                self.backlog.pop(0)

            failed_clients = []
            for client_id, websocket in list(self.clients.items()):
                if target_user_id is not None:
                    client_user_id = self.client_metadata.get(client_id, {}).get('user_id')
                    if client_user_id != target_user_id:
                        continue
                try:
                    await websocket.send(json.dumps(message, ensure_ascii=False))
                    self.stats['messages_sent'] += 1
                except Exception as e:
                    logger.error(f"Failed to send signal to client {client_id}: {e}")
                    self.stats['messages_failed'] += 1
                    failed_clients.append(client_id)

        for client_id in failed_clients:
            await self.unregister_client(client_id)

        logger.debug(f"Signal broadcasted to {len(self.clients)} clients")

    async def _send_to_client(self, client_id: str, message: Dict[str, Any]):
        with self._lock:
            websocket = self.clients.get(client_id)
        if websocket is None:
            return
        try:
            await websocket.send(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Failed to send message to client {client_id}: {e}")
            await self.unregister_client(client_id)

    async def _monitor_heartbeat(self, client_id: str):
        while True:
            await asyncio.sleep(30)
            with self._lock:
                meta = self.client_metadata.get(client_id)
                if meta is None:
                    break
                last_hb = meta.get('last_heartbeat', 0)
                if time.time() - last_hb > 90:
                    logger.warning(f"Client {client_id} heartbeat timeout, disconnecting")
            if time.time() - last_hb > 90:
                await self.unregister_client(client_id)
                break

    def _validate_broker_account(
        self,
        user_id: int,
        credential_id: int | None = None,
        broker_account_id: str | None = None,
    ) -> Dict[str, Any]:
        result = {
            'valid': True,
            'validated': False,
            'expected_account': None,
            'actual_account': broker_account_id,
        }

        if not broker_account_id:
            logger.info(f"User {user_id}: No broker_account_id provided, skipping validation")
            return result

        try:
            from app.utils.credential_crypto import decrypt_credential_blob

            with get_db_connection() as db:
                cur = db.cursor()

                if credential_id:
                    cur.execute("""
                        SELECT id, exchange_id, encrypted_config
                        FROM qd_exchange_credentials
                        WHERE id = %s AND user_id = %s AND exchange_id IN ('mt5', 'ibkr')
                    """, (credential_id, user_id))
                else:
                    cur.execute("""
                        SELECT id, exchange_id, encrypted_config
                        FROM qd_exchange_credentials
                        WHERE user_id = %s AND exchange_id IN ('mt5', 'ibkr')
                    """, (user_id,))

                credentials = cur.fetchall()
                cur.close()

            if not credentials:
                logger.info(f"User {user_id}: No MT5/IBKR credentials found, skipping validation")
                return result

            matched = False
            expected_accounts = []

            for cred in credentials:
                exchange_id = cred['exchange_id']
                try:
                    config_json = decrypt_credential_blob(cred['encrypted_config'])
                    config = json.loads(config_json) if isinstance(config_json, str) else config_json

                    if exchange_id == 'mt5':
                        expected_login = str(config.get('mt5_login', '')).strip()
                        if expected_login:
                            expected_accounts.append(expected_login)
                            if expected_login == str(broker_account_id).strip():
                                matched = True
                                result['expected_account'] = expected_login
                                break

                    elif exchange_id == 'ibkr':
                        expected_account = str(config.get('ibkr_account', '')).strip()
                        if not expected_account:
                            logger.info(f"User {user_id}: IBKR account not configured, skipping validation")
                            result['validated'] = True
                            return result

                        expected_accounts.append(expected_account)
                        if expected_account == str(broker_account_id).strip():
                            matched = True
                            result['expected_account'] = expected_account
                            break
                except Exception as e:
                    logger.warning(f"Failed to decrypt credential {cred['id']}: {e}")
                    continue

            result['validated'] = True

            if not matched:
                result['valid'] = False
                result['expected_account'] = ', '.join(expected_accounts) if expected_accounts else 'N/A'
                result['error'] = (
                    f"Broker account mismatch: Cloud expects [{result['expected_account']}], "
                    f"but local client logged in as [{broker_account_id}]. "
                    f"Please ensure your local terminal is logged into the correct account."
                )
                logger.warning(f"User {user_id}: {result['error']}")

        except Exception as e:
            logger.error(f"Failed to validate broker account for user {user_id}: {e}")
            result['error'] = f"Validation error: {str(e)}"

        return result

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                **self.stats,
                'queue_size': len(self.backlog),
                'clients': [
                    {
                        'client_id': cid,
                        'connected_at': meta.get('connected_at'),
                        'last_heartbeat': meta.get('last_heartbeat'),
                    }
                    for cid, meta in self.client_metadata.items()
                ],
            }


_signal_hub: WebSocketSignalHub | None = None


def get_signal_hub() -> WebSocketSignalHub:
    global _signal_hub
    if _signal_hub is None:
        _signal_hub = WebSocketSignalHub()
    return _signal_hub


async def websocket_handler(websocket, path: str = None):
    """
    WebSocket connection handler for use with websockets.serve().

    Protocol:
        1. Client sends JSON auth: {"api_key": "...", "broker_account_id": "..."}
        2. Server validates and sends connection_established
        3. Client receives trading_signal messages
        4. Client sends {"type": "ping"} for heartbeat
    """
    client_id = None
    try:
        auth_message = await asyncio.wait_for(websocket.recv(), timeout=10)
        auth_data = json.loads(auth_message)

        api_key = auth_data.get('api_key', '')
        if not api_key:
            await websocket.close(code=4001, reason="API key required")
            return

        broker_account_id = auth_data.get('broker_account_id')

        hub = get_signal_hub()
        client_id = await hub.register_client(websocket, api_key, broker_account_id=broker_account_id)

        if client_id is None:
            return

        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get('type', '')

                if msg_type == 'ping':
                    await hub._send_to_client(client_id, {
                        'type': 'pong',
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                    })
                    with hub._lock:
                        meta = hub.client_metadata.get(client_id)
                        if meta:
                            meta['last_heartbeat'] = time.time()

                elif msg_type == 'get_stats':
                    await hub._send_to_client(client_id, {
                        'type': 'stats',
                        'data': hub.get_stats(),
                    })

                else:
                    logger.warning(f"Unknown message type from client {client_id}: {msg_type}")

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from client {client_id}")
            except Exception as e:
                logger.error(f"Error processing message from client {client_id}: {e}")

    except asyncio.TimeoutError:
        logger.warning("WebSocket authentication timeout")
        await websocket.close(code=4003, reason="Authentication timeout")
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket handler error: {e}")
    finally:
        if client_id:
            hub = get_signal_hub()
            await hub.unregister_client(client_id)


if __name__ == "__main__":
    if not WEBSOCKETS_AVAILABLE:
        import sys
        print("ERROR: websockets library not installed")
        print("Install with: pip install websockets")
        sys.exit(1)

    async def main():
        hub = get_signal_hub()
        async with websockets.serve(websocket_handler, "0.0.0.0", 8765):
            logger.info("WebSocket Signal Hub started on ws://0.0.0.0:8765/ws")
            logger.info("Connect with: ws://localhost:8765/ws")
            logger.info("Send auth message: {'api_key': 'your-api-key'}")
            await asyncio.Future()

    asyncio.run(main())
