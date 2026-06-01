from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password length must be at least 6 characters")
    full_name: Optional[str] = None
    role: Optional[str] = Field("public", description="Role: admin, officer, or public")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    role: str

class APIKeyCreateRequest(BaseModel):
    key_name: str = Field(..., description="Descriptive label for this integration key")
    expires_in_days: Optional[int] = Field(365, description="Days until key expires. Defaults to 1 year.")

class APIKeyCreatedResponse(BaseModel):
    key_name: str
    plain_api_key: str = Field(..., description="Display once only! This key cannot be recovered after closing.")
    hashed_key: str
    created_at: datetime
    expires_at: Optional[datetime] = None
