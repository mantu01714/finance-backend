"""
User management routes.

Access control:
  GET  /users/me          → any authenticated, active user
  GET  /users             → admin only
  GET  /users/{id}        → admin only
  POST /users             → admin only  (create user with custom role)
  PUT  /users/{id}        → admin only
  DELETE /users/{id}      → admin only  (soft deactivate)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, require_admin
from app.core.security import hash_password
from app.models.models import User
from app.schemas.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_active_user)):
    """Return the profile of the currently authenticated user."""
    return current_user


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """List all users (admin only)."""
    return db.query(User).order_by(User.id).all()


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Create a new user with a specified role (admin only)."""
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Update user details, role, or status (admin only)."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = payload.model_dump(exclude_none=True)

    if "password" in update_data:
        user.hashed_password = hash_password(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Deactivate a user account (soft delete — sets is_active=False).
    Admins cannot deactivate themselves.
    """
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    db.commit()
