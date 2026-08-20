from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from passlib.hash import pbkdf2_sha256
from app.models.user import User
import jwt,datetime
from app.utils.auth import get_current_user, SECRET_KEY


router = APIRouter(prefix="/auth", tags=["Auth"])

class AuthRequest(BaseModel):
    username: str
    password: str
    invite_code: str = ""

@router.post("/register")
async def register(req: AuthRequest):
    import os
    correct_code = os.getenv("INVITE_CODE", "默认邀请码")
    if req.invite_code != correct_code:
        raise HTTPException(status_code=403, detail="邀请码错误")

    # 检查用户名是否已存在
    existing = await User.filter(username=req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 密码哈希后存入数据库
    hashed_password = pbkdf2_sha256.hash(req.password)
    user = await User.create(username=req.username, password=hashed_password)

    return {"message": "注册成功", "user_id": user.id}


@router.post("/login")
async def login(req: AuthRequest):
    user = await User.filter(username=req.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    if not pbkdf2_sha256.verify(req.password, user.password):
        raise HTTPException(status_code=401, detail="密码错误")

    # 生成 Token
    token = jwt.encode(
        {
            "user_id": user.id,
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
        },
        SECRET_KEY,
        algorithm="HS256"
    )

    return {"message": "登录成功", "token": token}

@router.get("/me")
async def get_me(user_id: int = Depends(get_current_user)):
    user = await User.filter(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return {
        "id": user.id,
        "username": user.username,
        "created_at": str(user.created_at),
        "total_tokens": user.total_tokens
    }

@router.get("/admin/users")
async def admin_users(user_id: int = Depends(get_current_user)):
    if user_id != 1:  # 只有你能访问
        raise HTTPException(status_code=403, detail="无权限")
    
    users = await User.all()
    result = []
    for u in users:
        result.append({
            "id": u.id,
            "username": u.username,
            "total_tokens": u.total_tokens,
            "created_at": str(u.created_at),
        })
    return {"users": result}