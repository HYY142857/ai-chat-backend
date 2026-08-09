from fastapi import FastAPI
from app.routers import chat, upload, auth
from tortoise.contrib.fastapi import register_tortoise
from typing import Dict

app = FastAPI()


# Tortoise-ORM 配置
TORTOISE_ORM: Dict = {
    "connections": {
        # 开发环境使用 SQLite（基于文件，无需服务器）
        "default": "sqlite://db.sqlite3",
    },
    "apps": {
        "models": {
            "models": ["app.models.user", "app.models.chat_message", "aerich.models"],  # 模型模块和 Aerich 迁移模型
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
