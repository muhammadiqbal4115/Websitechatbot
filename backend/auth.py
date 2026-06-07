import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours

bearer_scheme = HTTPBearer(auto_error=False)


def verify_password(plain: str, hashed: str) -> bool:
    sha256_hash = hashlib.sha256(plain.encode()).hexdigest()
    return bcrypt.checkpw(sha256_hash.encode(), hashed.encode())


def authenticate_admin(username: str, password: str) -> bool:
    expected_user = os.getenv("ADMIN_USERNAME", "admin")
    expected_hash = os.getenv("ADMIN_PASSWORD_HASH")

    if not expected_hash:
        return False
    if username != expected_user:
        return False
    return verify_password(password, expected_hash)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    admin_username = os.getenv("ADMIN_USERNAME", "admin")

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        username: str = payload.get("sub")
        if username != admin_username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
