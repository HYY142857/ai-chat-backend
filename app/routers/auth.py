from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from passlib.hash import pbkdf2_sha256
from app.models.user import User
import jwt,datetime

SECRET_KEY = "your-secret-key"  # 加密用的密钥，随便写一串复杂的字符串

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
    user = await User.filter(username=req.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    if not pbkdf2_sha256.verify(req.password, user.password):
        raise HTTPException(status_code=401, detail="密码错误")

    # 生成 Token
    token = jwt.encode(
        {
            "user_id": user.id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)  # 24小时后过期
        },
        SECRET_KEY,
        algorithm="HS256"
    )

    return {"message": "登录成功", "token": token}

