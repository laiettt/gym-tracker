"""Session auth 工具：簽章 cookie、驗證帳密。

為什麼自己刻而不用第三方：單人自用 app，依賴愈少愈好；stdlib 的 hmac +
base64 + json 就能做出足夠安全的 signed cookie。

環境變數：
- GYM_USERNAME / GYM_PASSWORD：有設就開啟整站認證；未設代表開發模式，完全不擋。
- SESSION_SECRET：簽章金鑰；未設時從 username+password 推導（單人場景可接受，
    代價是改密碼會讓所有 session 失效，本來就該失效）。
- SESSION_DAYS：cookie 有效天數，預設 30。
"""
import hashlib
import hmac
import json
import os
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

AUTH_COOKIE_NAME = "gym_session"


def _env_username() -> str:
    return os.environ.get("GYM_USERNAME", "").strip()


def _env_password() -> str:
    return os.environ.get("GYM_PASSWORD", "").strip()


def session_seconds() -> int:
    try:
        days = int(os.environ.get("SESSION_DAYS", "30"))
    except ValueError:
        days = 30
    return max(1, days) * 24 * 3600


def _secret_key() -> bytes:
    """取簽章金鑰。明示 SESSION_SECRET 優先；否則從帳密推導確保重啟後一致。"""
    explicit = os.environ.get("SESSION_SECRET", "").strip()
    if explicit:
        return explicit.encode("utf-8")
    return hashlib.sha256(
        f"{_env_username()}::{_env_password()}".encode("utf-8")
    ).digest()


def is_auth_enabled() -> bool:
    """帳密環境變數皆有值時啟用認證；本地開發不設就完全不擋。"""
    return bool(_env_username() and _env_password())


def verify_credentials(username: str, password: str) -> bool:
    """比對帳密，用 compare_digest 防 timing attack。"""
    return (
        secrets.compare_digest(username, _env_username())
        and secrets.compare_digest(password, _env_password())
    )


def _sign(payload: bytes) -> bytes:
    return hmac.new(_secret_key(), payload, hashlib.sha256).digest()


def _b64e(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64d(s: str) -> bytes:
    # 補回被 strip 掉的 padding
    pad = "=" * (-len(s) % 4)
    return urlsafe_b64decode(s + pad)


def create_session_token() -> str:
    """格式：<b64(payload)>.<b64(sig)>。payload 為 {u, exp} 的 JSON。"""
    payload = json.dumps(
        {"u": _env_username(), "exp": int(time.time()) + session_seconds()},
        separators=(",", ":"),
    ).encode("utf-8")
    sig = _sign(payload)
    return f"{_b64e(payload)}.{_b64e(sig)}"


def verify_session_token(token: str) -> bool:
    if not token or "." not in token:
        return False
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        payload = _b64d(payload_b64)
        sig = _b64d(sig_b64)
    except Exception:
        return False
    if not hmac.compare_digest(sig, _sign(payload)):
        return False
    try:
        data = json.loads(payload)
    except Exception:
        return False
    if data.get("u") != _env_username():
        return False
    try:
        exp = int(data.get("exp", 0))
    except (TypeError, ValueError):
        return False
    return exp >= int(time.time())
