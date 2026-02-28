from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from core.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
DEFAULT_TOKEN_EXPIRE_MINUTES = 15

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

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
    expire = datetime.now(datetime.timezone.utc) + timedelta(minutes=expire_minutes)

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)