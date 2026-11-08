from dotenv import load_dotenv
load_dotenv()
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
            "models": ["app.models.user", "app.models.chat_message","app.models.conversation","app.models.file_record", "aerich.models"],  # 模型模块和 Aerich 迁移模型
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

# === 自动补全缺失的表和列（解决 Render 免费版不能手动 ALTER 的问题） ===
import sqlite3
import os as _os

# === 自动补全缺失的表和列（同时支持 SQLite 和 PostgreSQL） ===
import os as _os

def _migrate_db():
    """检查数据库，补全 conversations 表和 chat_messages.conversation_id 列"""
    raw = db_url  # 你 main.py 里已经定义好了

    if raw.startswith("sqlite://"):
        backend = "sqlite"
        db_path = raw[len("sqlite://"):]
        if not _os.path.exists(db_path):
            print("[DB] SQLite 文件不存在，跳过迁移（让 generate_schemas 去建）", flush=True)
            return
    elif raw.startswith("postgres://") or raw.startswith("postgresql://"):
        backend = "postgres"
    else:
        print(f"[DB] 未知的数据库类型，跳过迁移: {raw}", flush=True)
        return

    try:
        if backend == "sqlite":
            import sqlite3
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            # 1. 检查 conversations 表
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
            if not cur.fetchone():
                cur.execute("""
                    CREATE TABLE conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER REFERENCES users(id),
                        title VARCHAR(100) DEFAULT '新对话',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print("[DB] SQLite: 自动创建 conversations 表", flush=True)

            # 2. 检查 conversation_id 列
            cur.execute("PRAGMA table_info(chat_messages)")
            cols = [r[1] for r in cur.fetchall()]
            if "conversation_id" not in cols:
                cur.execute("ALTER TABLE chat_messages ADD COLUMN conversation_id INTEGER REFERENCES conversations(id)")
                print("[DB] SQLite: 给 chat_messages 加 conversation_id 列", flush=True)

            conn.commit()
            conn.close()

        else:  # PostgreSQL
            import asyncio
            import asyncpg

            async def pg_migrate():
                conn = await asyncpg.connect(raw)

                # 1. 检查 conversations 表
                exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'conversations')"
                )
                if not exists:
                    await conn.execute("""
                        CREATE TABLE conversations (
                            id SERIAL PRIMARY KEY,
                            user_id INT REFERENCES users(id),
                            title VARCHAR(100) DEFAULT '新对话',
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW()
                        )
                    """)
                    print("[DB] PostgreSQL: 自动创建 conversations 表", flush=True)

                # 2. 检查 conversation_id 列
                cols = await conn.fetch(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'chat_messages'"
                )
                col_names = [r["column_name"] for r in cols]
                if "conversation_id" not in col_names:
                    await conn.execute(
                        "ALTER TABLE chat_messages ADD COLUMN conversation_id INT REFERENCES conversations(id)"
                    )
                    print("[DB] PostgreSQL: 给 chat_messages 加 conversation_id 列", flush=True)

                await conn.close()

            asyncio.run(pg_migrate())

    except Exception as e:
        print(f"[DB] 迁移失败（可以忽略）: {e}", flush=True)

_migrate_db()
# === 迁移结束 ===
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