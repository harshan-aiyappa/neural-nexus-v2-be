import os
from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from app.logging_utils import logger

# Security configurations
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # Use a persistent but unique fallback for development only
    SECRET_KEY = "neural-nexus-v2-dev-internal-fallback-key"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

import bcrypt
# Fix for passlib/bcrypt compatibility issue on some Windows environments
try:
    if not hasattr(bcrypt, "__about__"):
        class BcryptAbout:
            __version__ = getattr(bcrypt, "__version__", "4.0.1")
        bcrypt.__about__ = BcryptAbout()
except Exception:
    pass

# Robust bcrypt/passlib setup for Windows Dev Env
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Using the network IP for tokenUrl as requested. auto_error=False allows the IP bypass to work without a token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://10.10.20.122:8000/api/auth/login", auto_error=False)

class TokenData(BaseModel):
    sub: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None

class User(BaseModel):
    email: str
    role: str
    full_name: Optional[str] = None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        # Standardize input for bcrypt limit (72 bytes)
        p_bytes = plain_password.encode('utf-8')
        if len(p_bytes) > 72:
            p_bytes = p_bytes[:72]
        
        # Passlib handles strings or bytes
        return pwd_context.verify(p_bytes, hashed_password)
    except Exception:
        # Fallback to direct bcrypt if passlib fails
        try:
            p_bytes = plain_password.encode('utf-8') if isinstance(plain_password, str) else plain_password
            if len(p_bytes) > 72:
                p_bytes = p_bytes[:72]
            h_bytes = hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password
            return bcrypt.checkpw(p_bytes, h_bytes)
        except:
            return False

def get_password_hash(password: str) -> str:
    p_bytes = password.encode('utf-8')
    if len(p_bytes) > 72:
        p_bytes = p_bytes[:72]
    return pwd_context.hash(p_bytes)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(request: Request, token: Optional[str] = Depends(oauth2_scheme)):
    # Security Bypass for specific local network systems
    client_ip = request.client.host
    allowed_ips = ["127.0.0.1", "10.10.20.199", "10.10.20.86", "10.10.20.122"]
    
    if client_ip in allowed_ips:
        # Return a mock research user with full permissions
        return TokenData(sub="internal-system", email="admin@neural-nexus.dev", role="RESEARCHER")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email, role=role)
    except JWTError:
        raise credentials_exception
    return token_data


class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: TokenData = Depends(get_current_user)):
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for your role"
            )
        return user
