import os
from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

# Security configurations
SECRET_KEY = os.getenv("SECRET_KEY", "neural-nexus-v2-master-secret-0912384756")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

import bcrypt
# Fix for passlib/bcrypt compatibility issue
try:
    if not hasattr(bcrypt, "__about__"):
        class BcryptAbout:
            __version__ = getattr(bcrypt, "__version__", "4.0.1")
        bcrypt.__about__ = BcryptAbout()
except Exception:
    pass

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Using the network IP for tokenUrl as requested
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://10.10.20.122:8000/api/auth/login")

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

class User(BaseModel):
    email: str
    role: str
    full_name: Optional[str] = None

def verify_password(plain_password, hashed_password):
    try:
        # Truncate to 72 bytes to avoid bcrypt limit error if necessary
        # However, the error usually comes from a version mismatch in passlib
        if isinstance(plain_password, str):
            plain_password = plain_password.encode('utf-8')
        if len(plain_password) > 72:
            plain_password = plain_password[:72]
            
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        # Fallback to direct bcrypt if passlib fails
        try:
            if isinstance(hashed_password, str):
                hashed_password = hashed_password.encode('utf-8')
            return bcrypt.checkpw(plain_password, hashed_password)
        except:
            return False

def get_password_hash(password):
    if isinstance(password, str):
        password = password.encode('utf-8')
    if len(password) > 72:
        password = password[:72]
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
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
