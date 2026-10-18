from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.app_user import AppUser
from app.services.auth import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AppUser:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Autenticación requerida")
    try:
        claims = decode_access_token(credentials.credentials)
        user_id = claims.get("sub")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido o vencido")
    if not isinstance(user_id, str):
        raise HTTPException(status_code=401, detail="Token inválido")
    user = db.query(AppUser).filter(AppUser.id == user_id, AppUser.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario inactivo o inexistente")
    return user

__all__ = ["get_db", "get_current_user"]
