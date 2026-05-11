"""
User API Key Management Service

用于管理用户的API Key，支持：
- 生成新的API Key
- 验证API Key并关联用户
- 查询用户的API Key列表
- 停用/删除API Key
"""

import secrets
import hashlib
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from app.utils.db import get_db_connection
import logging

logger = logging.getLogger(__name__)


class APIKeyService:
    """API Key管理服务"""
    
    @staticmethod
    def generate_api_key() -> str:
        """
        生成安全的API Key
        
        Returns:
            API Key字符串
        """
        # 生成32字节的随机数，转为十六进制（64字符）
        return f"qd_{secrets.token_hex(32)}"
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        对API Key进行哈希（存储时使用）
        
        Args:
            api_key: 原始API Key
            
        Returns:
            SHA256哈希值
        """
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def create_api_key(user_id: int, key_name: str = 'Default', 
                       description: str = '', expires_days: int = 365) -> Dict:
        """
        为用户创建新的API Key
        
        Args:
            user_id: 用户ID
            key_name: Key名称
            description: 描述
            expires_days: 过期天数（0表示永不过期）
            
        Returns:
            包含api_key和key_info的字典
        """
        # 生成API Key
        api_key = APIKeyService.generate_api_key()
        api_key_hash = APIKeyService.hash_api_key(api_key)
        
        # 计算过期时间
        expires_at = None
        if expires_days > 0:
            expires_at = datetime.now() + timedelta(days=expires_days)
        
        # 插入数据库
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute("""
                INSERT INTO qd_api_keys (user_id, api_key, key_name, description, 
                                        active, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING id, created_at
            """, (user_id, api_key_hash, key_name, description, True, expires_at))
            
            result = cur.fetchone()
            db.commit()
            cur.close()
        
        logger.info(f"Created API key for user {user_id}: {key_name} (ID: {result[0]})")
        
        return {
            'api_key': api_key,  # 只在创建时返回一次
            'key_info': {
                'id': result[0],
                'key_name': key_name,
                'description': description,
                'active': True,
                'expires_at': expires_at.isoformat() if expires_at else None,
                'created_at': result[1].isoformat() if result[1] else None
            }
        }
    
    @staticmethod
    def validate_api_key(api_key: str) -> Optional[Dict]:
        """
        验证API Key并返回用户信息
        
        Args:
            api_key: API Key字符串
            
        Returns:
            如果有效，返回用户信息字典；否则返回None
        """
        api_key_hash = APIKeyService.hash_api_key(api_key)
        
        with get_db_connection() as db:
            cur = db.cursor()
            
            # 查询API Key
            cur.execute("""
                SELECT ak.id, ak.user_id, ak.key_name, ak.active, 
                       ak.expires_at, ak.last_used_at
                FROM qd_api_keys ak
                WHERE ak.api_key = ?
            """, (api_key_hash,))
            
            key_row = cur.fetchone()
            
            if not key_row:
                cur.close()
                logger.warning(f"Invalid API key used")
                return None
            
            # 检查是否激活
            if not key_row['active']:
                cur.close()
                logger.warning(f"API key is inactive: {key_row['key_name']}")
                return None
            
            # 检查是否过期
            if key_row['expires_at'] and key_row['expires_at'] < datetime.now():
                cur.close()
                logger.warning(f"API key expired: {key_row['key_name']}")
                return None
            
            # 更新最后使用时间
            cur.execute("""
                UPDATE qd_api_keys 
                SET last_used_at = NOW()
                WHERE id = ?
            """, (key_row['id'],))
            db.commit()
            
            # 获取用户信息
            cur.execute("""
                SELECT id, username, email, role, status
                FROM qd_users
                WHERE id = ?
            """, (key_row['user_id'],))
            
            user = cur.fetchone()
            cur.close()
            
            if not user or user['status'] != 'active':
                logger.warning(f"User is inactive: {key_row['user_id']}")
                return None
            
            logger.info(f"API key validated for user: {user['username']}")
            
            return {
                'user_id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role'],
                'key_id': key_row['id'],
                'key_name': key_row['key_name']
            }
    
    @staticmethod
    def get_user_api_keys(user_id: int) -> List[Dict]:
        """
        获取用户的所有API Key
        
        Args:
            user_id: 用户ID
            
        Returns:
            API Key列表（不包含完整key，只显示前缀）
        """
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute("""
                SELECT id, api_key, key_name, description, active, 
                       expires_at, last_used_at, created_at
                FROM qd_api_keys
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            
            keys = cur.fetchall()
            cur.close()
        
        # 隐藏完整API Key，只显示前缀
        result = []
        for key in keys:
            full_key = key['api_key']
            prefix = full_key[:12] + '...' if full_key else 'N/A'
            
            result.append({
                'id': key['id'],
                'api_key_prefix': prefix,
                'key_name': key['key_name'],
                'description': key['description'],
                'active': key['active'],
                'expires_at': key['expires_at'].isoformat() if key['expires_at'] else None,
                'last_used_at': key['last_used_at'].isoformat() if key['last_used_at'] else None,
                'created_at': key['created_at'].isoformat() if key['created_at'] else None
            })
        
        return result
    
    @staticmethod
    def revoke_api_key(user_id: int, key_id: int) -> bool:
        """
        停用API Key
        
        Args:
            user_id: 用户ID
            key_id: API Key ID
            
        Returns:
            是否成功
        """
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute("""
                UPDATE qd_api_keys 
                SET active = FALSE, updated_at = NOW()
                WHERE id = ? AND user_id = ?
            """, (key_id, user_id))
            
            affected = cur.rowcount
            db.commit()
            cur.close()
        
        if affected > 0:
            logger.info(f"Revoked API key {key_id} for user {user_id}")
        
        return affected > 0
    
    @staticmethod
    def delete_api_key(user_id: int, key_id: int) -> bool:
        """
        删除API Key
        
        Args:
            user_id: 用户ID
            key_id: API Key ID
            
        Returns:
            是否成功
        """
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute("""
                DELETE FROM qd_api_keys
                WHERE id = ? AND user_id = ?
            """, (key_id, user_id))
            
            affected = cur.rowcount
            db.commit()
            cur.close()
        
        if affected > 0:
            logger.info(f"Deleted API key {key_id} for user {user_id}")
        
        return affected > 0
