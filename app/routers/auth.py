from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from passlib.hash import pbkdf2_sha256
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])


class AuthRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
async def register(req: AuthRequest):
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
    # 查找用户
    user = await User.filter(username=req.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    # 验证密码
    if not pbkdf2_sha256.verify(req.password, user.password):
        raise HTTPException(status_code=401, detail="密码错误")

    return {"message": "登录成功", "user_id": user.id}
