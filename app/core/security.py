from datetime import datetime, timedelta, timezone
from fastapi import Request, HTTPException
import jwt as pyjwt
from app.core.config import SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_HOURS

def create_token(username: str) -> str:
    return pyjwt.encode(
        {"sub": username, "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)},
        SECRET_KEY, algorithm=JWT_ALGORITHM,
    )

def verify_token(token: str) -> str | None:
    try:
        return pyjwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM]).get("sub")
    except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
        return None

async def get_current_user(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    token = ""
    if auth.startswith("Bearer "):
        token = auth[7:]
    else:
        # Fallback for EventSource which cannot send headers
        token = request.query_params.get("token", "")

    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return username.strip()
