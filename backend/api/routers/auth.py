"""
Authentication API endpoints.
"""

from datetime import datetime, timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jose import jwt
from passlib.context import CryptContext

from ..schemas import LoginRequest, LoginResponse
from ..dependencies import get_config, get_current_user
from ...core.config import Config

router = APIRouter()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Mock user database - in production, this would be in the database
MOCK_USERS = {
    "faculty1": {
        "username": "faculty1",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password123"
        "role": "faculty",
        "permissions": ["read_attendance", "create_session", "view_reports"]
    },
    "admin": {
        "username": "admin",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password123"
        "role": "admin",
        "permissions": ["*"]
    }
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, config: Config) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(seconds=config.security.jwt_expiration)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        config.security.jwt_secret, 
        algorithm="HS256"
    )
    return encoded_jwt


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    config: Annotated[Config, Depends(get_config)]
):
    """
    Authenticate user and return access token.
    
    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
    - Set up API authentication and authorization middleware
    """
    # Validate user credentials
    user = MOCK_USERS.get(login_data.username)
    if not user or not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Create access token
    token_data = {
        "sub": user["username"],
        "role": user["role"],
        "permissions": user["permissions"]
    }
    
    access_token = create_access_token(token_data, config)
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=config.security.jwt_expiration,
        user_info={
            "username": user["username"],
            "role": user["role"],
            "permissions": user["permissions"]
        }
    )


@router.post("/logout")
async def logout():
    """
    Logout user (client-side token removal).
    """
    return {"message": "Successfully logged out"}


@router.get("/me")
async def get_current_user_info(
    current_user: Annotated[dict, Depends(get_current_user)]
):
    """
    Get current authenticated user information.
    """
    return {
        "username": current_user["user_id"],
        "role": current_user["role"],
        "permissions": current_user["permissions"]
    }


@router.post("/refresh")
async def refresh_token(
    current_user: Annotated[dict, Depends(get_current_user)],
    config: Annotated[Config, Depends(get_config)]
):
    """
    Refresh access token.
    """
    # Create new token with same data
    token_data = {
        "sub": current_user["user_id"],
        "role": current_user["role"],
        "permissions": current_user["permissions"]
    }
    
    access_token = create_access_token(token_data, config)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": config.security.jwt_expiration
    }