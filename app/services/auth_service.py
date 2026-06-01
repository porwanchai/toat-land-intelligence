import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Union, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.user import User, APIKey

logger = logging.getLogger(__name__)

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration keys
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM

# FastApi Security Dependencies injection
bearer_token_scheme = HTTPBearer(auto_error=False)
api_key_header_scheme = APIKeyHeader(name=settings.API_KEY_HEADER_NAME, auto_error=False)

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def hash_api_key(plain_key: str) -> str:
        """
        Uses SHA-256 to hash the API key, matching industry security standards.
        Keys are stored securely in database, protecting against SQL injection leakages.
        """
        return hashlib.sha256(plain_key.encode()).hexdigest()

    @staticmethod
    def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Creates JWT access tokens.
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
            
        to_encode = {"exp": expire, "sub": str(subject)}
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @classmethod
    async def get_current_user(
        cls,
        db: AsyncSession,
        token: HTTPAuthorizationCredentials = Security(bearer_token_scheme),
        api_key: str = Security(api_key_header_scheme)
    ) -> User:
        """
        Dual Authentication Strategy:
        1. Authenticate using Bearer JWT tokens if provided.
        2. If JWT is absent, authenticate using X-API-Key headers.
        Raises 401 Unauthorized if both are absent or invalid.
        """
        # Strategy 1: JWT Verification
        if token:
            try:
                payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
                email: str = payload.get("sub")
                if email is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid authentication payload. JWT claims missing."
                    )
            except JWTError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired access token credentials."
                )

            # Query database
            stmt = select(User).where(User.email == email)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            if user and user.is_active:
                return user
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account associated with this token is currently deactivated."
            )

        # Strategy 2: API Key Hashing Verification
        if api_key:
            hashed = cls.hash_api_key(api_key)
            stmt = select(APIKey).where(APIKey.hashed_key == hashed, APIKey.is_active == True)
            result = await db.execute(stmt)
            db_key = result.scalar_one_or_none()
            
            if db_key:
                # Check expiration
                if db_key.expires_at and db_key.expires_at < datetime.utcnow():
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Provided API Key has already expired."
                    )
                
                # Fetch associated user profile
                user_stmt = select(User).where(User.id == db_key.user_id)
                user_res = await db.execute(user_stmt)
                user = user_res.scalar_one_or_none()
                if user and user.is_active:
                    return user

        # Denied
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are required to access this resource. Please supply a valid JWT or API Key."
        )
