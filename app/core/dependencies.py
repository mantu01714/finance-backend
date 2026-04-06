"""
FastAPI dependencies for authentication and role-based access control.

Usage in routes:
    current_user: User = Depends(get_current_active_user)
    _: User = Depends(require_roles(UserRole.admin))
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.models import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_error
    except JWTError:
        raise credentials_error

    user = db.get(User, int(user_id))
    if user is None:
        raise credentials_error
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is inactive. Contact an administrator.",
        )
    return current_user


def require_roles(*roles: UserRole):
    """
    Dependency factory.  Returns a dependency that raises 403 unless
    the current user has one of the specified roles.

    Example:
        Depends(require_roles(UserRole.admin, UserRole.analyst))
    """
    def _guard(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {[r.value for r in roles]}",
            )
        return current_user

    return _guard


# Convenience aliases
require_admin = require_roles(UserRole.admin)
require_analyst_or_above = require_roles(UserRole.admin, UserRole.analyst)
