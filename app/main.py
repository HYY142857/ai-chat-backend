import os
from fastapi import FastAPI
from app.routers import chat, upload, auth
from tortoise.contrib.fastapi import register_tortoise
from typing import Dict
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-chat-frontend-lilac.vercel.app",
        "http://localhost:5173",  # 保留本地开发用
    ],       # 允许所有来源（开发用），生产环境改成具体域名
    allow_credentials=True,
    allow_methods=["*"],       # 允许所有 HTTP 方法
    allow_headers=["*"],       # 允许所有请求头
)

db_url = os.getenv("DATABASE_URL")
if db_url:
    db_url = db_url.replace("postgresql://", "postgres://")
    # asyncpg 不接受 URL 里的 ?sslmode=xxx，直接去掉
    if "?" in db_url:
        db_url = db_url.split("?")[0]
else:
    # 本地环境：SQLite
    db_url = "sqlite://db.sqlite3"

# Tortoise-ORM 配置
TORTOISE_ORM: Dict = {
    "connections": {
        "default": db_url,
    },
    "apps": {
        "models": {
            "models": ["app.models.user", "app.models.chat_message","app.models.file_record", "aerich.models"],  # 模型模块和 Aerich 迁移模型
            "default_connection": "default",
        }
    },
    # 连接池配置（推荐）
    "use_tz": False,  # 是否使用时区
    "timezone": "UTC",  # 默认时区
}

register_tortoise(app,
                  config=TORTOISE_ORM,
                  generate_schemas=True,  # 开发环境自动生成表结构
                  add_exception_handlers=True  # 添加默认异常处理
                  )



@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}


app.include_router(chat.router)
app.include_router(upload.router)
app.include_router(auth.router)

import time
@app.middleware("http")
async def log_requests(request, call_next):
    # 记录请求开始
    start_time = time.time()
    print(f"[请求] {request.method} {request.url}", flush=True)

    # 放行，让路由去处理
    response = await call_next(request)

    # 记录请求结束
    duration = time.time() - start_time
    print(f"[响应] {response.status_code}  耗时 {duration:.2f}s")

    return response