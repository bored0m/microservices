import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import ADMIN_EMAILS, CORS_ORIGINS
from .database import Base, engine, get_db
from .deps import get_current_user
from .models import User
from .schemas import LoginIn, RegisterIn, TokenOut, UserMe, UserPublic
from .security import create_access_token, hash_password, verify_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("auth")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    log.info("Auth service started, tables ready")
    yield


app = FastAPI(
    title="Identity & Auth Service",
    description="Регистрация, аутентификация (JWT) и профили пользователей «Умного города».",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"]
)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@app.post("/auth/register", response_model=UserMe, status_code=status.HTTP_201_CREATED, tags=["auth"])
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = data.email.lower()
    exists = db.scalar(select(User).where((User.email == email) | (User.username == data.username)))
    if exists:
        log.warning("Registration conflict for email=%s", email)
        raise HTTPException(status.HTTP_409_CONFLICT, "Email or username already taken")
    user = User(
        email=email,
        username=data.username,
        password_hash=hash_password(data.password),
        role="admin" if email in ADMIN_EMAILS else "resident",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email or username already taken")
    db.refresh(user)
    log.info("User registered id=%s role=%s", user.id, user.role)
    return user


@app.post("/auth/login", response_model=TokenOut, tags=["auth"])
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if user is None or not verify_password(data.password, user.password_hash):
        log.warning("Failed login for email=%s", data.email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")
    log.info("User logged in id=%s", user.id)
    return TokenOut(access_token=create_access_token(user.id, user.role))


@app.get("/users/me", response_model=UserMe, tags=["users"])
def me(user: User = Depends(get_current_user)):
    """Также используется другими сервисами для проверки токена."""
    return user


@app.get("/users", response_model=list[UserPublic], tags=["users"])
def list_users(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(User).order_by(User.id)).all()


@app.get("/users/{user_id}", response_model=UserPublic, tags=["users"])
def get_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user
