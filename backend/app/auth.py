# backend/app/auth.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .models import User
from .schemas import User as UserSchema
import logging

logger = logging.getLogger(__name__)

# Configuration
SECRET_KEY = "hycon-labs-equipment-system-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    """Verify JWT token and return email"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        return email
    except JWTError:
        return None

def authenticate_user(db: Session, email: str, password: str):
    """Authenticate user with email and password (database auth)"""
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return False
    return user

def authenticate_user_ldap(db: Session, username: str, password: str):
    """
    Authenticate user via LDAP and auto-create/update user in database
    
    Args:
        db: Database session
        username: Username (can be email, username, or DOMAIN\\username)
        password: User's password
        
    Returns:
        User object if successful, False if failed
    """
    try:
        # Import here to avoid circular imports
        from .ldap_auth import ldap_auth
        
        # Try LDAP authentication
        ldap_user_info = ldap_auth.authenticate_user(username, password)
        
        if not ldap_user_info:
            logger.info(f"LDAP authentication failed for: {username}")
            return False
        
        logger.info(f"LDAP authentication successful for: {ldap_user_info['username']}")
        
        # Check if user exists in database
        user = db.query(User).filter(User.email == ldap_user_info['email']).first()
        
        if user:
            # Update existing user with latest AD info
            user.name = ldap_user_info['name']
            user.role = ldap_user_info['role']
            logger.info(f"Updated existing user: {user.email} with role: {user.role}")
        else:
            # Create new user from LDAP info
            user = User(
                email=ldap_user_info['email'],
                name=ldap_user_info['name'],
                role=ldap_user_info['role'],
                password_hash=get_password_hash(password)  # Store hashed password as backup
            )
            db.add(user)
            logger.info(f"Created new user from LDAP: {user.email} with role: {user.role}")
        
        db.commit()
        db.refresh(user)
        
        return user
        
    except Exception as e:
        logger.error(f"Error in LDAP authentication for {username}: {str(e)}")
        db.rollback()
        return False

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> UserSchema:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    email = verify_token(credentials.credentials)
    if email is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return UserSchema.from_orm(user)

async def get_current_admin(
    current_user: UserSchema = Depends(get_current_user)
) -> UserSchema:
    """Ensure current user is admin"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user