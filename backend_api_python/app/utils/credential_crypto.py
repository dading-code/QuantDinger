"""
Fernet encryption for qd_exchange_credentials.encrypted_config.

Uses CREDENTIAL_ENCRYPTION_KEY from the environment (SHA-256 digest → urlsafe base64 → Fernet key).
Falls back to SECRET_KEY for backward compatibility, but CREDENTIAL_ENCRYPTION_KEY is recommended.

Version history:
- v1: 使用 SECRET_KEY 派生 Fernet key (原始实现，保持兼容)
"""

from __future__ import annotations

import base64
import hashlib
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


def _get_fernet_key() -> bytes:
    """
    获取 Fernet 加密密钥。

    优先使用 CREDENTIAL_ENCRYPTION_KEY，回退到 SECRET_KEY。
    建议在生产环境设置独立的 CREDENTIAL_ENCRYPTION_KEY 以支持密钥轮换。
    """
    # 优先使用专用的凭证加密密钥
    secret = (os.getenv("CREDENTIAL_ENCRYPTION_KEY") or "").strip()
    # 向后兼容：如果没有专用密钥，使用 SECRET_KEY
    if not secret:
        secret = (os.getenv("SECRET_KEY") or "").strip()
    if not secret:
        raise ValueError(
            "CREDENTIAL_ENCRYPTION_KEY or SECRET_KEY is not set; "
            "cannot encrypt or decrypt exchange credentials"
        )
    return base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())


def _fernet_from_secret() -> Fernet:
    key = _get_fernet_key()
    return Fernet(key)


def encrypt_credential_blob(plaintext_json: str) -> str:
    """
    Encrypt JSON text for storage in encrypted_config.

    版本标记：目前所有加密数据均为 v1 格式，为未来密钥轮换预留。
    格式：v1:<fernet-ciphertext>
    """
    if plaintext_json is None:
        plaintext_json = ""
    f = _fernet_from_secret()
    ciphertext = f.encrypt(plaintext_json.encode("utf-8")).decode("ascii")
    return f"v1:{ciphertext}"


def decrypt_credential_blob(stored: Any) -> str:
    """
    Decrypt DB value to JSON text. Empty / None yields empty string.

    支持版本化的加密格式，便于未来实现密钥轮换。
    """
    if stored is None:
        return ""
    s = stored.decode("utf-8") if isinstance(stored, (bytes, bytearray)) else str(stored)
    s = s.strip()
    if not s:
        return ""

    # 处理版本化格式
    if s.startswith("v1:"):
        ciphertext = s[3:]
    else:
        # 向后兼容：旧格式无版本前缀
        ciphertext = s

    f = _fernet_from_secret()
    try:
        return f.decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise ValueError(
            "Cannot decrypt exchange credential (wrong encryption key or data not encrypted with this key)"
        ) from e
