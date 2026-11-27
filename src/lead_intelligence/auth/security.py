import hashlib
import re
import secrets

from argon2 import PasswordHasher, Type, extract_parameters
from argon2.exceptions import InvalidHashError, VerificationError

PASSWORD_MIN_LENGTH = 15
PASSWORD_MAX_BYTES = 1024
USERNAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9_.-]{2,63}")
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}")
_HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def normalize_username(username: str) -> str:
    if not isinstance(username, str) or not username.isascii():
        raise ValueError("Invalid username")
    normalized = username.strip().lower()
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError("Username must contain 3–64 permitted ASCII characters")
    return normalized


def _password_bytes(password: str) -> bytes:
    if not isinstance(password, str) or len(password) > PASSWORD_MAX_BYTES:
        raise ValueError("Invalid password length")
    try:
        encoded = password.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("Invalid password encoding") from None
    if not encoded or len(encoded) > PASSWORD_MAX_BYTES or b"\x00" in encoded:
        raise ValueError("Invalid password length or content")
    return encoded


def hash_password(password: str) -> str:
    encoded = _password_bytes(password)
    if len(password) < PASSWORD_MIN_LENGTH or not password.strip():
        raise ValueError("Password must contain at least 15 characters")
    return _HASHER.hash(encoded)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        encoded = _password_bytes(password)
        if not isinstance(password_hash, str) or len(password_hash) > 512:
            return False
        params = extract_parameters(password_hash)
        # Reject unsupported or unexpectedly expensive stored hash parameters.
        if (
            params.type != Type.ID
            or params.version != 19
            or not 19456 <= params.memory_cost <= 131072
            or not 2 <= params.time_cost <= 5
            or not 1 <= params.parallelism <= 4
            or not 16 <= params.salt_len <= 64
            or not 16 <= params.hash_len <= 64
        ):
            return False
        return _HASHER.verify(password_hash, encoded)
    except (ValueError, InvalidHashError, VerificationError):
        return False


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    if not isinstance(token, str) or not TOKEN_PATTERN.fullmatch(token):
        raise ValueError("Invalid session token")
    return hashlib.sha256(token.encode("ascii")).hexdigest()
