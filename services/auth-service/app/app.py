from datetime import timedelta
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from . import crud
from .auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_active_user,
)
from .database import get_db
from .models import (
    PasswordChange,
    PasswordReset,
    User,
    UserCreate,
    UserStatusUpdate,
    UserUpdate,
)

app = FastAPI(title="Authentication Demo", version="1.0.0")


@app.get("/")
async def root():
    return {"message": "Welcome to FastAPI Authentication Demo"}


@app.post("/register", response_model=User)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if user already exists
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = crud.create_user(db=db, user=user)
    return User(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        full_name=new_user.full_name,
        is_active=new_user.is_active,
    )


@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """Authenticate user and return access token."""
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user


@app.get("/protected")
async def protected_route(current_user: User = Depends(get_current_active_user)):
    return {"message": f"Hello {current_user.full_name}, this is a protected route!"}


@app.put("/users/me", response_model=User)
async def update_my_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update current user's profile information."""
    # Check if email is being changed and if it's already taken
    if user_update.email and user_update.email != current_user.email:
        existing_user = crud.get_user_by_email(db, email=user_update.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

    updated_user = crud.update_user_profile(
        db,
        user_id=current_user.id,
        email=user_update.email,
        full_name=user_update.full_name,
    )

    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    return User(
        id=updated_user.id,
        username=updated_user.username,
        email=updated_user.email,
        full_name=updated_user.full_name,
        is_active=updated_user.is_active,
    )


@app.post("/users/me/password")
async def change_my_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Change current user's password."""
    result = crud.change_user_password(
        db,
        user_id=current_user.id,
        current_password=password_change.current_password,
        new_password=password_change.new_password,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    elif result is True:
        raise HTTPException(
            status_code=400,
            detail="New password cannot be the same as the current password",
        )
    elif result is False:
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    return {"message": "Password changed successfully"}


@app.delete("/users/me")
async def delete_my_account(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Delete current user's account."""
    result = crud.delete_user(db, user_id=current_user.id)

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "Account deleted successfully"}


@app.get("/users", response_model=List[User])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all users (requires authentication)."""
    users = crud.get_all_users(db, skip=skip, limit=limit)
    return [
        User(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
        )
        for user in users
    ]


@app.get("/users/search", response_model=List[User])
async def search_users(
    q: str,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Search users by username, email, or full name."""
    users = crud.search_users(db, search_term=q, skip=skip, limit=limit)
    return [
        User(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
        )
        for user in users
    ]


@app.get("/users/count")
async def get_user_count(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Get total count of users."""
    count = crud.get_user_count(db)
    return {"count": count}


@app.get("/users/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get user by ID (requires authentication)."""
    user = crud.get_user_by_id(db, user_id=user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return User(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
    )


@app.put("/users/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update user profile (admin function)."""
    # Check if email is being changed and if it's already taken
    if user_update.email:
        existing_user = crud.get_user_by_email(db, email=user_update.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=400, detail="Email already registered")

    updated_user = crud.update_user_profile(
        db, user_id=user_id, email=user_update.email, full_name=user_update.full_name
    )

    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    return User(
        id=updated_user.id,
        username=updated_user.username,
        email=updated_user.email,
        full_name=updated_user.full_name,
        is_active=updated_user.is_active,
    )


@app.post("/users/{user_id}/password-reset")
async def reset_user_password(
    user_id: int,
    password_reset: PasswordReset,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Reset user password (admin function)."""
    result = crud.reset_user_password(
        db, user_id=user_id, new_password=password_reset.new_password
    )

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "Password reset successfully"}


@app.patch("/users/{user_id}/status", response_model=User)
async def update_user_status(
    user_id: int,
    status_update: UserStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Enable or disable user account (admin function)."""
    updated_user = crud.update_user_status(
        db, user_id=user_id, is_active=status_update.is_active
    )

    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    return User(
        id=updated_user.id,
        username=updated_user.username,
        email=updated_user.email,
        full_name=updated_user.full_name,
        is_active=updated_user.is_active,
    )


@app.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete user (admin function)."""
    # Prevent users from deleting themselves via this endpoint
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400, detail="Use /users/me endpoint to delete your own account"
        )

    result = crud.delete_user(db, user_id=user_id)

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "User deleted successfully"}
