# services/security.py
"""轻量级的密码哈希与登录 token 实现（只用标准库，不额外引入依赖）。

- 密码：PBKDF2-HMAC-SHA256 + 随机盐，保存成 "算法$轮数$盐$哈希"
- token：base64(payload).base64(HMAC-SHA256 签名)，带过期时间
"""

import base64
import hashlib
import hmac
import json
import secrets
import time

from config import settings

_HASH_ALGO = "pbkdf2_sha256"
_ITERATIONS = 200_000
TOKEN_TTL_SECONDS = 7 * 24 * 3600  # 7 天


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return "$".join(
        [
            _HASH_ALGO,
            str(_ITERATIONS),
            base64.b64encode(salt).decode(),
            base64.b64encode(digest).decode(),
        ]
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_b64, hash_b64 = (stored or "").split("$")
        if algo != _HASH_ALGO:
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(body: str) -> bytes:
    return hmac.new(settings.AUTH_SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()


def create_token(user_id: int) -> str:
    payload = {"uid": user_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return f"{body}.{_b64encode(_sign(body))}"


def decode_token(token: str) -> int | None:
    """校验签名和过期时间，返回 user_id；失败返回 None"""
    try:
        body, signature = (token or "").split(".")
        if not hmac.compare_digest(_b64decode(signature), _sign(body)):
            return None
        payload = json.loads(_b64decode(body))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return int(payload.get("uid"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
