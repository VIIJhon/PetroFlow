"""
User Management API Endpoints
Handles user CRUD, role modifications, and account activation/deactivation.
Authored by Jhon Villegas
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse
)
from app.api.deps import get_current_active_user
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all system users.
    Accessible by Admin and Engineer roles.
    """
    # RBAC Check: Only admin and engineer can list users
    if current_user.role not in [UserRole.ADMIN, UserRole.ENGINEER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para ver la lista de usuarios."
        )

    try:
        query = db.query(User)

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        if role:
            query = query.filter(User.role == role)

        if search:
            query = query.filter(
                (User.username.ilike(f"%{search}%")) |
                (User.email.ilike(f"%{search}%")) |
                (User.full_name.ilike(f"%{search}%"))
            )

        total = query.count()
        users = query.order_by(User.username).offset(skip).limit(limit).all()

        # Build responses with is_admin field computed
        user_responses = []
        for u in users:
            user_responses.append({
                "id": u.id,
                "email": u.email,
                "username": u.username,
                "full_name": u.full_name,
                "role": u.role.value if hasattr(u.role, 'value') else str(u.role),
                "is_active": u.is_active,
                "is_admin": u.role == UserRole.ADMIN,
                "created_at": u.created_at,
                "updated_at": u.updated_at,
                "last_login": u.last_login
            })

        return {"users": user_responses, "total": total}

    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener usuarios: {str(e)}"
        )


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_by_admin(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Register a new user inside the platform.
    Only accessible by Admin.
    """
    # RBAC Check: Only admin can create users
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden crear nuevos usuarios."
        )

    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_in.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El correo electrónico '{user_in.email}' ya está registrado."
        )

    # Check if username already exists
    existing_username = db.query(User).filter(User.username == user_in.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El nombre de usuario '{user_in.username}' ya está tomado."
        )

    try:
        # Resolve UserRole Enum
        role_val = UserRole(user_in.role.value if hasattr(user_in.role, 'value') else user_in.role)
        
        # Hash password and save
        hashed_pwd = get_password_hash(user_in.password)
        new_user = User(
            email=user_in.email,
            username=user_in.username,
            hashed_password=hashed_pwd,
            full_name=user_in.full_name,
            role=role_val,
            is_active=True,
            is_verified=True  # Admin created users are pre-verified
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {
            "id": new_user.id,
            "email": new_user.email,
            "username": new_user.username,
            "full_name": new_user.full_name,
            "role": new_user.role.value if hasattr(new_user.role, 'value') else str(new_user.role),
            "is_active": new_user.is_active,
            "is_admin": new_user.role == UserRole.ADMIN,
            "created_at": new_user.created_at,
            "updated_at": new_user.updated_at,
            "last_login": new_user.last_login
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al registrar usuario: {str(e)}"
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user_by_admin(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a user's details and system permissions/role.
    Only accessible by Admin.
    """
    # RBAC Check: Only admin can update users
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden editar usuarios."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )

    # Prevent admin from self-demoting or self-deactivating
    if user.id == current_user.id:
        if user_in.is_active is False or (user_in.role and user_in.role != UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puede degradar su propio rol de Administrador ni inactivar su propia cuenta."
            )

    # Check unique email if updated
    if user_in.email and user_in.email != user.email:
        existing = db.query(User).filter(User.email == user_in.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El correo electrónico '{user_in.email}' ya está registrado por otro usuario."
            )

    try:
        update_data = user_in.dict(exclude_unset=True)
        
        # Check role mapping
        if "role" in update_data and update_data["role"]:
            role_enum_val = UserRole(update_data["role"].value if hasattr(update_data["role"], 'value') else update_data["role"])
            user.role = role_enum_val
            del update_data["role"]

        for field, value in update_data.items():
            setattr(user, field, value)

        db.commit()
        db.refresh(user)

        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
            "is_active": user.is_active,
            "is_admin": user.role == UserRole.ADMIN,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "last_login": user.last_login
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar usuario: {str(e)}"
        )


@router.delete("/{user_id}", response_model=UserResponse)
async def deactivate_user_by_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Soft-delete / deactivate a user.
    Only accessible by Admin.
    """
    # RBAC Check: Only admin can deactivate users
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden inactivar usuarios."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede desactivar su propia cuenta administrativa."
        )

    try:
        user.is_active = False
        db.commit()
        db.refresh(user)

        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
            "is_active": user.is_active,
            "is_admin": user.role == UserRole.ADMIN,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "last_login": user.last_login
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error deactivating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al inactivar usuario: {str(e)}"
        )


@router.post("/{user_id}/reactivate", response_model=UserResponse)
async def reactivate_user_by_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Reactivate a suspended or inactive user.
    Only accessible by Admin.
    """
    # RBAC Check: Only admin can reactivate users
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden activar usuarios."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )

    try:
        user.is_active = True
        db.commit()
        db.refresh(user)

        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
            "is_active": user.is_active,
            "is_admin": user.role == UserRole.ADMIN,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "last_login": user.last_login
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error reactivating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al activar usuario: {str(e)}"
        )
