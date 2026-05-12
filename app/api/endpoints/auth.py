from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.config import USERS
from app.core.security import create_token, get_current_user

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(req: LoginRequest):
    u = (req.username or "").strip()
    p = (req.password or "").strip()
    if u not in USERS or USERS[u] != p:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    return {"token": create_token(u), "username": u}

@router.get("/me")
async def me(user: str = Depends(get_current_user)):
    return {"username": user}
