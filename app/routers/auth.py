import logging
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, APIKeyCreateRequest, APIKeyCreatedResponse
from app.models.user import User, APIKey
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["System Authentication & API Keys"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    Registers a new user account profile in the database.
    """
    # 1. Check if user already exists
    stmt = select(User).where(User.email == user_in.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address has already been registered."
        )

    # 2. Hash password and insert profile
    hashed_pwd = AuthService.hash_password(user_in.password)
    user_record = User(
        email=user_in.email,
        hashed_password=hashed_pwd,
        full_name=user_in.full_name,
        role=user_in.role,
        is_active=True
    )
    
    db.add(user_record)
    await db.commit()
    await db.refresh(user_record)

    # 3. Issue Access Token immediately on registration
    token = AuthService.create_access_token(user_record.email)
    return TokenResponse(
        access_token=token,
        email=user_record.email,
        role=user_record.role
    )

@router.post("/login", response_model=TokenResponse)
async def login_user(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Exchanges credentials for JWT authentication bearer tokens.
    """
    # 1. Query email
    stmt = select(User).where(User.email == credentials.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not AuthService.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password credentials."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account has been deactivated. Access denied."
        )

    # 2. Issue Access Token
    token = AuthService.create_access_token(user.email)
    return TokenResponse(
        access_token=token,
        email=user.email,
        role=user.role
    )

@router.post("/api-keys", response_model=APIKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def generate_integration_api_key(
    req: APIKeyCreateRequest,
    user_email: str,  # simple verification for demonstration mapping
    db: AsyncSession = Depends(get_db)
):
    """
    Generates a secure system API Key for server-to-server integration setups.
    - Generates 32-character high entropy keys (`secrets.token_urlsafe(32)`).
    - Hashes key via SHA-256 before writing to DB.
    - Returns plain text key ONCE ONLY.
    """
    # Verify user profile exists
    stmt = select(User).where(User.email == user_email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User profile was not found.")

    # 1. Create high-entropy key
    plain_key = f"toat_{secrets.token_urlsafe(32)}"
    hashed = AuthService.hash_api_key(plain_key)

    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(days=req.expires_in_days) if req.expires_in_days else None

    # 2. Save Key
    key_record = APIKey(
        key_name=req.key_name,
        hashed_key=hashed,
        user_id=user.id,
        is_active=True,
        expires_at=expires_at
    )
    
    db.add(key_record)
    await db.commit()
    await db.refresh(key_record)

    return APIKeyCreatedResponse(
        key_name=key_record.key_name,
        plain_api_key=plain_key,
        hashed_key=hashed,
        created_at=key_record.created_at,
        expires_at=key_record.expires_at
    )
