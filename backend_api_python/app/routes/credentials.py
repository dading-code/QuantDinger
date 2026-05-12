"""
Exchange credentials vault.

encrypted_config stores Fernet ciphertext derived from SECRET_KEY (see app.utils.credential_crypto).
"""

import traceback
import json
from flask import Blueprint, request, jsonify, g

import requests as rq

from app.utils.db import get_db_connection
from app.utils.logger import get_logger
from app.utils.auth import login_required
from app.utils.credential_crypto import encrypt_credential_blob, decrypt_credential_blob
from app.services.live_trading.factory import exchange_demo_mode_enabled

logger = get_logger(__name__)

credentials_bp = Blueprint('credentials', __name__)


@credentials_bp.route('/desktop-brokers-policy', methods=['GET'])
@login_required
def desktop_brokers_policy():
    """
    Whether IBKR / MT5 (local TWS or MT5 terminal) may be configured on this deployment.
    Frontend uses this to disable options and show guidance before save/test.
    """
    from app.utils.local_brokers import desktop_broker_cloud_reject_message, local_desktop_brokers_allowed

    allowed = local_desktop_brokers_allowed()
    return jsonify(
        {
            'code': 1,
            'msg': 'success',
            'data': {
                'allow_local_desktop_brokers': allowed,
                'disabled_message': None if allowed else desktop_broker_cloud_reject_message(),
            },
        }
    )


def _api_key_hint(api_key: str) -> str:
    if not api_key:
        return ''
    s = str(api_key)
    if len(s) <= 8:
        return s[:2] + '***'
    return f"{s[:4]}...{s[-4:]}"


@credentials_bp.route('/list', methods=['GET'])
@login_required
def list_credentials():
    """List all credentials for the current user with associated API Keys."""
    try:
        user_id = g.user_id

        with get_db_connection() as db:
            cur = db.cursor()
            # 关联查询API Key信息（只取最新的一个active API Key）
            cur.execute(
                """
                SELECT ec.id, ec.user_id, ec.name, ec.exchange_id, ec.api_key_hint, 
                       ec.encrypted_config, ec.created_at, ec.updated_at,
                       ak.api_key as api_key_value, ak.key_name as api_key_name
                FROM qd_exchange_credentials ec
                LEFT JOIN qd_api_keys ak ON ak.id = (
                    SELECT id FROM qd_api_keys 
                    WHERE credential_id = ec.id AND active = true 
                    ORDER BY id DESC LIMIT 1
                )
                WHERE ec.user_id = %s
                ORDER BY ec.id DESC
                """,
                (user_id,)
            )
            rows = cur.fetchall() or []
            cur.close()

        items = []
        for row in rows:
            item = dict(row or {})
            item['enable_demo_trading'] = False
            try:
                plain = decrypt_credential_blob(item.get('encrypted_config'))
                cfg = json.loads(plain) if plain else {}
                item['enable_demo_trading'] = exchange_demo_mode_enabled(cfg if isinstance(cfg, dict) else {})
            except Exception:
                item['enable_demo_trading'] = False
            item.pop('encrypted_config', None)
            
            # 脱敏处理API Key（只显示前8位和后4位）
            api_key_value = item.pop('api_key_value', None)
            if api_key_value:
                if len(api_key_value) > 12:
                    item['api_key'] = api_key_value[:8] + '...' + api_key_value[-4:]
                    item['api_key_full'] = api_key_value  # 完整Key用于复制
                else:
                    item['api_key'] = api_key_value
                    item['api_key_full'] = api_key_value
            else:
                item['api_key'] = None
                item['api_key_full'] = None
            
            items.append(item)

        return jsonify({'code': 1, 'msg': 'success', 'data': {'items': items}})
    except Exception as e:
        logger.error(f"list_credentials failed: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'code': 0, 'msg': str(e), 'data': {'items': []}}), 500


CRYPTO_EXCHANGES = [
    'binance', 'okx', 'bitget', 'bybit', 'coinbaseexchange',
    'kraken', 'kucoin', 'gate', 'deepcoin', 'htx'
]


def _egress_ipify(url: str) -> str:
    try:
        r = rq.get(url, timeout=8)
        if r.status_code != 200:
            return ""
        j = r.json()
        if not isinstance(j, dict):
            return ""
        return str(j.get("ip") or "").strip()
    except Exception:
        return ""


@credentials_bp.route('/egress-ip', methods=['GET'])
@login_required
def get_egress_ip():
    """
    Public egress IPv4/IPv6 of this API server (for exchange API key IP whitelist).
    Uses ipify's v4-only / v6-only endpoints so each family is detected independently.
    """
    ipv4 = _egress_ipify("https://api4.ipify.org?format=json")
    ipv6 = _egress_ipify("https://api6.ipify.org?format=json")
    return jsonify(
        {
            "code": 1,
            "msg": "success",
            "data": {
                "ipv4": ipv4 or None,
                "ipv6": ipv6 or None,
                # 兼容旧前端：优先 IPv4，否则 IPv6
                "ip": ipv4 or ipv6 or None,
            },
        }
    )


@credentials_bp.route('/create', methods=['POST'])
@login_required
def create_credential():
    """Create a new credential for the current user.

    Supports crypto exchanges, IBKR (US stocks) and MT5 (Forex).
    """
    try:
        user_id = g.user_id
        data = request.get_json() or {}
        name = (data.get('name') or '').strip()
        exchange_id = (data.get('exchange_id') or '').strip().lower()

        if not exchange_id:
            return jsonify({'code': 0, 'msg': 'Missing exchange_id', 'data': None}), 400

        if exchange_id in ('ibkr', 'mt5'):
            from app.utils.local_brokers import desktop_broker_cloud_reject_message, local_desktop_brokers_allowed

            if not local_desktop_brokers_allowed():
                return jsonify({'code': 0, 'msg': desktop_broker_cloud_reject_message(), 'data': None}), 403

        config = {'exchange_id': exchange_id}
        hint = ''

        if exchange_id == 'ibkr':
            # Interactive Brokers (US stocks)
            # clientId must differ from manual /api/ibkr/connect (defaults to 1) or TWS drops one session.
            _ib_cid = data.get('ibkr_client_id')
            try:
                ibkr_client_id = int(_ib_cid) if _ib_cid not in (None, '') else 7
            except (TypeError, ValueError):
                ibkr_client_id = 7
            config.update({
                'ibkr_host': (data.get('ibkr_host') or '127.0.0.1').strip(),
                'ibkr_port': int(data.get('ibkr_port') or 7497),
                'ibkr_client_id': ibkr_client_id,
                'ibkr_account': (data.get('ibkr_account') or '').strip()
            })
            hint = f"{config['ibkr_host']}:{config['ibkr_port']}"
        elif exchange_id == 'mt5':
            # MetaTrader 5 (Forex)
            mt5_server = (data.get('mt5_server') or '').strip()
            mt5_login = str(data.get('mt5_login') or '').strip()
            mt5_password = (data.get('mt5_password') or '').strip()
            if not mt5_server or not mt5_login or not mt5_password:
                return jsonify({'code': 0, 'msg': 'Missing mt5_server/mt5_login/mt5_password', 'data': None}), 400
            
            # 尝试验证 MT5 账号并获取实际 Login ID
            expected_account_id = ''
            try:
                from app.services.live_trading.factory import create_mt5_client
                client = create_mt5_client({
                    'exchange_id': 'mt5',
                    'mt5_login': mt5_login,
                    'mt5_password': mt5_password,
                    'mt5_server': mt5_server,
                    'market_category': 'Forex'
                })
                account_info = client.get_account_info()
                if account_info and 'login' in account_info:
                    expected_account_id = str(account_info['login'])
                    logger.info(f"MT5 credential verified. Expected Account ID: {expected_account_id}")
                client.disconnect()
            except Exception as e:
                logger.warning(f"Failed to verify MT5 credentials during binding: {e}")
                # 即使验证失败也允许保存，但会记录警告
                expected_account_id = mt5_login

            config.update({
                'mt5_server': mt5_server,
                'mt5_login': mt5_login,
                'mt5_password': mt5_password,
                'mt5_terminal_path': (data.get('mt5_terminal_path') or '').strip()
            })
            hint = f"{mt5_server}/{mt5_login}"
        elif exchange_id in CRYPTO_EXCHANGES:
            # Crypto exchanges
            api_key = (data.get('api_key') or '').strip()
            secret_key = (data.get('secret_key') or '').strip()
            if not api_key or not secret_key:
                return jsonify({'code': 0, 'msg': 'Missing api_key/secret_key', 'data': None}), 400
            config.update({
                'api_key': api_key,
                'secret_key': secret_key,
                'passphrase': (data.get('passphrase') or '').strip(),
                'enable_demo_trading': exchange_demo_mode_enabled(data),
            })
            hint = _api_key_hint(api_key)
        else:
            return jsonify({'code': 0, 'msg': f'Unsupported exchange: {exchange_id}', 'data': None}), 400

        plaintext_config = json.dumps(config, ensure_ascii=False)
        stored_blob = encrypt_credential_blob(plaintext_config)

        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                INSERT INTO qd_exchange_credentials (user_id, name, exchange_id, api_key_hint, encrypted_config, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id
                """,
                (user_id, name, exchange_id, hint, stored_blob)
            )
            row = cur.fetchone()
            new_id = (row or {}).get('id')
            db.commit()
            cur.close()

        return jsonify({'code': 1, 'msg': 'success', 'data': {'id': new_id}})
    except Exception as e:
        logger.error(f"create_credential failed: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'code': 0, 'msg': str(e), 'data': None}), 500


@credentials_bp.route('/delete', methods=['DELETE'])
@login_required
def delete_credential():
    """Delete a credential for the current user."""
    try:
        user_id = g.user_id
        cred_id = request.args.get('id', type=int)
        if not cred_id:
            return jsonify({'code': 0, 'msg': 'Missing id', 'data': None}), 400

        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                "DELETE FROM qd_exchange_credentials WHERE id = %s AND user_id = %s",
                (cred_id, user_id)
            )
            db.commit()
            cur.close()

        return jsonify({'code': 1, 'msg': 'success', 'data': None})
    except Exception as e:
        logger.error(f"delete_credential failed: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'code': 0, 'msg': str(e), 'data': None}), 500


@credentials_bp.route('/get', methods=['GET'])
@login_required
def get_credential():
    """
    Return decrypted credential for form auto-fill.
    """
    try:
        user_id = g.user_id
        cred_id = request.args.get('id', type=int)
        if not cred_id:
            return jsonify({'code': 0, 'msg': 'Missing id', 'data': None}), 400

        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                """
                SELECT id, user_id, name, exchange_id, encrypted_config, api_key_hint, created_at, updated_at
                FROM qd_exchange_credentials
                WHERE id = %s AND user_id = %s
                """,
                (cred_id, user_id)
            )
            row = cur.fetchone()
            cur.close()

        if not row:
            return jsonify({'code': 0, 'msg': 'Not found', 'data': None}), 404

        raw = row.get('encrypted_config')
        plain = decrypt_credential_blob(raw)
        decrypted = json.loads(plain) if plain else {}
        # Ensure exchange_id is present
        decrypted['exchange_id'] = row.get('exchange_id') or decrypted.get('exchange_id')

        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': {
                'id': row.get('id'),
                'name': row.get('name'),
                'exchange_id': row.get('exchange_id'),
                'api_key_hint': row.get('api_key_hint'),
                'config': decrypted
            }
        })
    except Exception as e:
        logger.error(f"get_credential failed: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'code': 0, 'msg': str(e), 'data': None}), 500


# ============================================================================
# Local Broker Helper APIs (for MT5, IBKR that require local client)
# ============================================================================

LOCAL_BROKERS = ['mt5', 'ibkr']


@credentials_bp.route('/is-local-broker', methods=['GET'])
@login_required
def is_local_broker():
    """
    Check if an exchange requires local execution (MT5, IBKR).
    
    Query params:
        exchange_id: Exchange identifier (e.g., 'mt5', 'ibkr', 'binance')
    
    Returns:
        {
            "code": 1,
            "data": {
                "is_local": true,
                "exchange_id": "mt5",
                "requires_client": true,
                "client_download_url": "/download/local-client"
            }
        }
    """
    try:
        exchange_id = request.args.get('exchange_id', '').lower().strip()
        
        if not exchange_id:
            return jsonify({'code': 0, 'msg': 'Missing exchange_id parameter', 'data': None}), 400
        
        is_local = exchange_id in LOCAL_BROKERS
        
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': {
                'exchange_id': exchange_id,
                'is_local': is_local,
                'requires_client': is_local,
                'client_download_url': '/download/local-client' if is_local else None,
                'client_name': 'QuantDinger Local Client' if is_local else None,
                'description': '需要下载本地客户端以接收交易信号并执行' if is_local else None
            }
        })
    except Exception as e:
        logger.error(f"is_local_broker failed: {e}")
        return jsonify({'code': 0, 'msg': str(e), 'data': None}), 500


@credentials_bp.route('/local-brokers/list', methods=['GET'])
@login_required
def list_local_brokers():
    """
    Get list of all exchanges that require local execution.
    
    Returns:
        {
            "code": 1,
            "data": {
                "brokers": [
                    {
                        "exchange_id": "mt5",
                        "name": "MetaTrader 5",
                        "requires_client": true,
                        "description": "外汇/差价合约交易平台"
                    },
                    {
                        "exchange_id": "ibkr",
                        "name": "Interactive Brokers",
                        "requires_client": true,
                        "description": "美股/全球股票交易平台"
                    }
                ]
            }
        }
    """
    try:
        brokers = [
            {
                'exchange_id': 'mt5',
                'name': 'MetaTrader 5',
                'requires_client': True,
                'description': '外汇/差价合约交易平台',
                'icon': 'mt5'
            },
            {
                'exchange_id': 'ibkr',
                'name': 'Interactive Brokers',
                'requires_client': True,
                'description': '美股/全球股票交易平台',
                'icon': 'ibkr'
            }
        ]
        
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': {
                'brokers': brokers,
                'total': len(brokers)
            }
        })
    except Exception as e:
        logger.error(f"list_local_brokers failed: {e}")
        return jsonify({'code': 0, 'msg': str(e), 'data': None}), 500


