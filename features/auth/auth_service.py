from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from api.users import users_service
from core.security import verify_password, create_access_token

def login(payload: dict, db: Session) -> dict:
    try:
      email = payload.get("email")
      user = users_service.get_by_email(email, db)
      if not user or not verify_password(payload.get("password"), user.password):
        raise HTTPException(status = status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")
      
      access_token = create_access_token({"id": user.id})
      refresh_token = create_access_token({"id": user.id}, 2880)
      return {"access_token": access_token, "refresh_token": refresh_token}
      
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")    