from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import get_db
from app.models import User, UserRole, Customer
from app.schemas.auth import RegisterRequest, LoginRequest, UserResponse
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.api.deps import current_user
import secrets

def set_auth_cookies(response: Response, user: User):
    secure = settings.environment == "production"
    same_site = "none" if secure else "lax"
    response.set_cookie(settings.access_cookie_name, create_access_token(str(user.id), user.token_version), httponly=True, secure=secure, samesite=same_site, max_age=settings.access_token_expire_minutes * 60, path="/", domain=settings.cookie_domain)
    response.set_cookie(settings.csrf_cookie_name, secrets.token_urlsafe(32), httponly=False, secure=secure, samesite=same_site, max_age=settings.access_token_expire_minutes * 60, path="/", domain=settings.cookie_domain)

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(409, "An account with this email already exists")
    user = User(email=payload.email.lower(), full_name=payload.full_name, password_hash=hash_password(payload.password), role=UserRole.CUSTOMER)
    db.add(user)
    db.flush()
    existing_customer = db.scalar(select(Customer).where(Customer.email == user.email))
    if existing_customer:
        existing_customer.user_id = user.id
    else:
        db.add(Customer(user_id=user.id, billing_name=user.full_name, email=user.email))
    db.commit()
    db.refresh(user)
    set_auth_cookies(response, user)
    return user

@router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    set_auth_cookies(response, user)
    return user

@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(current_user)):
    return user

@router.post("/bootstrap-admin", response_model=UserResponse, status_code=201)
def bootstrap_admin(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    if not settings.allow_admin_bootstrap:
        raise HTTPException(403, "Admin bootstrap is disabled")
    if db.scalar(select(User).where(User.role == UserRole.ADMIN)):
        raise HTTPException(409, "An admin already exists")
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(409, "Email already exists")
    user = User(email=payload.email.lower(), full_name=payload.full_name, password_hash=hash_password(payload.password), role=UserRole.ADMIN)
    db.add(user)
    db.commit()
    db.refresh(user)
    set_auth_cookies(response, user)
    return user

@router.post("/logout", status_code=204)
def logout(response: Response, db: Session = Depends(get_db), user: User = Depends(current_user)):
    user.token_version += 1
    db.commit()
    response.delete_cookie(settings.access_cookie_name, path="/", domain=settings.cookie_domain)
    response.delete_cookie(settings.csrf_cookie_name, path="/", domain=settings.cookie_domain)
    response.status_code = 204
    return response
