import hashlib
import os
from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = os.environ.get("JWT_SECRET", "change-this-secret-for-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", 60 * 24 * 7))

try:
    pwd_context = CryptContext(schemes=["bcrypt", "pbkdf2_sha256"], deprecated="auto")
except Exception:
    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return hashlib.sha256(plain_password.encode("utf-8")).hexdigest() == hashed_password


def get_password_hash(password: str) -> str:
    try:
        return pwd_context.hash(password)
    except Exception:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if "sub" not in to_encode and "email" in to_encode:
        to_encode["sub"] = to_encode["email"]
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return {}
