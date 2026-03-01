from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from core.config import settings
from fastapi.security import HTTPBearer

from .exception_handlers import BaseDomainError

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
DEFAULT_TOKEN_EXPIRE_MINUTES = 15

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)


token_bearer = HTTPBearer()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(
    data: dict,
    expires_in_minutes: int | None = None
) -> str:
    to_encode = data.copy()

    expire_minutes = expires_in_minutes or DEFAULT_TOKEN_EXPIRE_MINUTES
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        return payload
    except JWTError:
        raise BaseDomainError("Invalid or expired token", 401)