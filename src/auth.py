"""
Authentication utilities for multi-tenant knowledger application.
Handles password hashing, JWT tokens, and session management.
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from src.database import User

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# Password hashing
def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)

# JWT token functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# User authentication
def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user

def create_user(db: Session, email: str, password: str) -> User:
    """Create a new user."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise ValueError("User with this email already exists")
    
    # Hash password
    password_hash = hash_password(password)
    
    # Create user
    user = User(
        email=email,
        password_hash=password_hash,
        created_at=datetime.utcnow(),
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_from_token(db: Session, token: str) -> Optional[User]:
    """Get user from JWT token."""
    payload = decode_access_token(token)
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    return user

# Linking code generation for Telegram
def generate_linking_code() -> str:
    """Generate a unique 6-character linking code."""
    return secrets.token_urlsafe(6)[:6].upper()

def create_linking_code(db: Session, user_id: int) -> str:
    """Create a linking code for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")
    
    # Generate unique code
    while True:
        code = generate_linking_code()
        # Check if code is already in use
        existing = db.query(User).filter(User.linking_code == code).first()
        if not existing:
            break
    
    user.linking_code = code
    db.commit()
    return code

def link_telegram_account(db: Session, linking_code: str, telegram_user_id: str) -> Optional[User]:
    """Link a Telegram account to a user using a linking code."""
    user = db.query(User).filter(User.linking_code == linking_code).first()
    if not user:
        return None
    
    # Check if Telegram ID is already linked to another account
    existing = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    if existing and existing.id != user.id:
        raise ValueError("This Telegram account is already linked to another user")
    
    user.telegram_user_id = telegram_user_id
    user.linking_code = None  # Clear the linking code after use
    db.commit()
    return user

def get_user_by_telegram_id(db: Session, telegram_user_id: str) -> Optional[User]:
    """Get a user by their Telegram user ID."""
    return db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
