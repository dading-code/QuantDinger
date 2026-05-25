from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from typing import Any, Dict, List, Optional
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
        
        # 🆕 新增：MCP 请求响应映射
        self.pending_requests: Dict[str, asyncio.Future] = {}
        
        # 🆕 新增：按账户ID索引（支持多客户端）
        self.account_clients: Dict[str, str] = {}  # account_id -> client_id
        
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
            # 检查是否是开发模式白名单
            dev_tokens = ["test-token", "observer-token", "dev-debug"]
            if api_key in dev_tokens:
                logger.warning(f"[开发模式] 使用测试 Token: {api_key[:8]}...")
                # 创建虚拟用户信息用于开发模式
                user_info = {
                    'user_id': 999,
                    'username': 'dev_user',
                    'email': 'dev@localhost',
                    'role': 'admin',
                    'credential_id': None
                }
            else:
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
            
            # 🆕 维护账户-客户端映射
            if broker_account_id:
                self.account_clients[broker_account_id] = client_id

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
            # 🆕 获取客户端的账户ID并清理映射
            metadata = self.client_metadata.get(client_id)
            if metadata:
                broker_account_id = metadata.get('broker_account_id')
                if broker_account_id and self.account_clients.get(broker_account_id) == client_id:
                    del self.account_clients[broker_account_id]
            
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
    
    async def request_mcp(self, tool_name: str, params: dict, account_id: str = None, timeout: int = 10) -> Optional[dict]:
        """
        🆕 向 Desktop 发送 MCP 请求并等待响应
        
        Args:
            tool_name: MCP 工具名称
            params: 请求参数
            account_id: 目标账户（None 表示随机选择一个在线账户）
            timeout: 超时时间
        
        Returns:
            响应数据或 None
        """
        # 如果没有指定账户，选择第一个在线账户
        if not account_id:
            online_accounts = self.get_online_accounts()
            if not online_accounts:
                logger.warning("[MCP请求] 没有在线的 Desktop 客户端")
                return None
            account_id = online_accounts[0]
        
        # 获取账户对应的客户端
        with self._lock:
            client_id = self.account_clients.get(account_id)
            if not client_id:
                logger.warning(f"[MCP请求] 账户 {account_id} 没有在线客户端")
                return None
        
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        message = {
            "type": "mcp_request",
            "request_id": request_id,
            "tool_name": tool_name,
            "params": params
        }
        
        logger.info(f"[MCP请求] account={account_id}, tool={tool_name}, request_id={request_id}")
        
        # 创建 Future 等待响应
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self.pending_requests[request_id] = future
        
        try:
            await self._send_to_client(client_id, message)
            response = await asyncio.wait_for(future, timeout=timeout)
            logger.info(f"[MCP响应] request_id={request_id}, success={response.get('success')}")
            return response
        except asyncio.TimeoutError:
            logger.warning(f"[MCP超时] request_id={request_id}")
            return None
        except Exception as e:
            logger.error(f"[MCP失败] request_id={request_id}, error={e}")
            return None
        finally:
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
    
    def handle_mcp_response(self, request_id: str, response_data: dict):
        """🆕 处理 Desktop 返回的 MCP 响应"""
        if request_id in self.pending_requests:
            future = self.pending_requests[request_id]
            if not future.done():
                future.set_result(response_data)
    
    def get_online_accounts(self) -> List[str]:
        """🆕 获取所有在线账户列表"""
        accounts = list(self.account_clients.keys())
        logger.info(f"[DEBUG] get_online_accounts() 调用 | 在线账户数={len(accounts)} | 账户列表={accounts}")
        return accounts
    
    def is_account_online(self, account_id: str) -> bool:
        """🆕 检查账户是否在线"""
        return account_id in self.account_clients

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


async def websocket_handler(websocket):
    """
    WebSocket connection handler for use with websockets.serve().

    支持两种认证方式：
    1. URL 参数模式（兼容 AI_Trading_Monitor_MT5_Observer）:
       ws://host/ws/v1/agent/{account_id}?token={token}
       
    2. WebSocket 消息模式（原有模式）:
       {"api_key": "...", "broker_account_id": "..."}

    Protocol:
        1. Client connects with auth (URL params or message)
        2. Server validates and sends connection_established
        3. Client sends {"type": "heartbeat"} periodically
        4. Server sends MCP requests and receives responses
    """
    client_id = None
    try:
        # 尝试从 URL 参数获取认证信息（兼容 AI_Trading_Monitor_MT5_Observer）
        api_key = None
        broker_account_id = None
        
        # websockets 16+ 使用 websocket.request.path 获取路径
        try:
            path = websocket.request.path if hasattr(websocket, 'request') and hasattr(websocket.request, 'path') else None
        except:
            path = None
        
        logger.info(f"[WebSocket] 收到连接请求，path={path}")
        
        if path:
            # 解析路径：/ws/v1/agent/{account_id}?token={token}
            import urllib.parse
            parsed = urllib.parse.urlparse(f"http://localhost{path}")
            query = urllib.parse.parse_qs(parsed.query)
            
            # 获取 token（Observer 使用的认证方式）
            if 'token' in query:
                api_key = query['token'][0]
            
            # 从路径提取 account_id
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 4 and path_parts[2] == 'agent':
                broker_account_id = path_parts[3]
        
        # 如果 URL 参数没有提供认证，尝试从 WebSocket 消息获取（原有模式）
        if not api_key:
            auth_message = await asyncio.wait_for(websocket.recv(), timeout=10)
            auth_data = json.loads(auth_message)
            
            api_key = auth_data.get('api_key', '')
            broker_account_id = auth_data.get('broker_account_id', broker_account_id)
            
            if not api_key:
                await websocket.close(code=4001, reason="API key required")
                return

        # 验证 API Key
        valid_key = False
        
        # 开发模式白名单
        dev_tokens = ["test-token", "observer-token", "dev-debug"]
        
        if api_key in dev_tokens:
            logger.warning(f"[开发模式] 使用测试 Token: {api_key[:8]}...")
            valid_key = True
        
        # 生产模式：从数据库验证
        if not valid_key and api_key:
            try:
                from app.services.api_key_manager import APIKeyService
                key_info = APIKeyService.validate_api_key(api_key)
                if key_info:
                    logger.info(f"[API Key验证成功] user={key_info.get('username')}")
                    valid_key = True
                else:
                    logger.warning(f"[API Key验证失败] 无效的 API Key")
            except Exception as e:
                logger.error(f"[API Key验证异常] {e}")
        
        if not valid_key:
            print(f"[WebSocket] ❌ 验证失败，关闭连接", flush=True)
            await websocket.close(code=4003, reason="Invalid API key")
            return
        else:
            logger.info(f"[WebSocket] 验证通过")
        
        hub = get_signal_hub()
        client_id = await hub.register_client(websocket, api_key, broker_account_id=broker_account_id)

        if client_id is None:
            return
        
        # 发送连接成功消息
        msg_data = {
            "type": "connection_established",
            "account_id": broker_account_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await websocket.send(json.dumps(msg_data))

        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get('type', '')

                if msg_type == 'ping' or msg_type == 'heartbeat':
                    # 支持两种心跳格式：
                    # 1. {"type": "ping"} - 原有格式
                    # 2. {"type": "heartbeat"} - AI_Trading_Monitor_MT5_Observer 格式
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

                elif msg_type == 'mcp_response':
                    # 🆕 处理 MCP 响应
                    request_id = data.get('request_id')
                    if request_id:
                        hub.handle_mcp_response(request_id, data)
                        logger.debug(f"[MCP响应] request_id={request_id[:12]}")

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
