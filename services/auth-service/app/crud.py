from typing import Optional

import bcrypt
from sqlalchemy.orm import Session

from .database import DBRole, DBUser
from .models import UserCreate


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    Passwords are encoded to bytes and hashed with a salt.
    """
    # Convert password to bytes
    password_bytes = password.encode("utf-8")
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string for storage
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    """
    try:
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def get_user_by_id(db: Session, user_id: int):
    """Get user by ID."""
    return db.query(DBUser).filter(DBUser.id == user_id).first()


def get_user_by_username(db: Session, username: str):
    """Get user by username."""
    return db.query(DBUser).filter(DBUser.username == username).first()


def get_user_by_email(db: Session, email: str):
    """Get user by email."""
    return db.query(DBUser).filter(DBUser.email == email).first()


def create_user(db: Session, user: UserCreate):
    """Create a new user."""
    # Hash the password using bcrypt
    hashed_password = hash_password(user.password)

    db_user = DBUser(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
    )

    # Assign default user role
    user_role = db.query(DBRole).filter(DBRole.name == "user").first()
    if user_role:
        db_user.roles.append(user_role)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, username: str, password: str):
    """Authenticate user with username and password."""
    user = get_user_by_username(db, username)
    if not user:
        return False
    # Verify the password using bcrypt
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_role(db: Session, name: str, description: str = ""):
    """Create a new role."""
    db_role = DBRole(name=name, description=description)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role


def get_all_users(db: Session, skip: int = 0, limit: int = 100):
    """Get all users with pagination."""
    return db.query(DBUser).offset(skip).limit(limit).all()


def update_user_profile(
    db: Session,
    user_id: int,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
):
    """Update user profile information."""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None

    if email is not None:
        db_user.email = email
    if full_name is not None:
        db_user.full_name = full_name

    db.commit()
    db.refresh(db_user)
    return db_user


def change_user_password(
    db: Session, user_id: int, current_password: str, new_password: str
) -> Optional[bool]:
    """Change user password after verifying current password."""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None

    # Check if current password is same as stored password
    if current_password == new_password:
        return True

    # Verify current password
    if not verify_password(current_password, db_user.hashed_password):
        return False

    # Hash and update new password
    db_user.hashed_password = hash_password(new_password)
    db.commit()
    db.refresh(db_user)
    return db_user


def reset_user_password(db: Session, user_id: int, new_password: str):
    """Reset user password (admin function)."""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None

    db_user.hashed_password = hash_password(new_password)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_status(db: Session, user_id: int, is_active: bool):
    """Update user active status (enable/disable account)."""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None

    db_user.is_active = is_active
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int):
    """Delete a user from the database."""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None

    db.delete(db_user)
    db.commit()
    return True


def get_user_count(db: Session):
    """Get total count of users."""
    return db.query(DBUser).count()


def search_users(db: Session, search_term: str, skip: int = 0, limit: int = 100):
    """Search users by username, email, or full name."""
    search_pattern = f"%{search_term}%"
    return (
        db.query(DBUser)
        .filter(
            (DBUser.username.ilike(search_pattern))
            | (DBUser.email.ilike(search_pattern))
            | (DBUser.full_name.ilike(search_pattern))
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
