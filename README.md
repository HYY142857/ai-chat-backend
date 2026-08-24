# AI Chat Platform

基于 FastAPI + React 构建的全栈 AI 智能对话平台，集成 DeepSeek 大模型 API 与 RAG 检索增强生成，支持 SSE 流式输出、JWT 用户认证、邀请码注册、多轮对话记忆、Token 用量追踪。

**在线地址**：https://ai-chat-frontend-lilac.vercel.app

**API 文档**：https://ai-chat-backend-be6s.onrender.com/docs

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| ORM | Tortoise ORM |
| 数据库（本地） | SQLite |
| 数据库（生产） | PostgreSQL (Neon) |
| AI 模型 | DeepSeek API |
| RAG 检索 | 自定义关键词匹配 + 文本切块 |
| 认证 | JWT (PyJWT) + HTTPBearer |
| 流式输出 | Server-Sent Events (SSE) |
| 文件解析 | PyPDF2 (PDF)、python-docx (Word) |
| 密码加密 | passlib (PBKDF2-SHA256) |
| 前端 | React 19 + Vite 8 |
| 部署 | Render (后端) + Vercel (前端) |

## 系统架构

```
                    用户
                     │
                     ▼
           ┌─────────────────┐
           │  React Frontend │  ← Vercel 部署
           │  (Vite + SPA)   │
           └────────┬────────┘
                    │ REST API / SSE
                    ▼
           ┌─────────────────┐
           │  FastAPI Backend│  ← Render 部署
           └────────┬────────┘
                    │
          ┌─────────┼──────────┐
          ▼         ▼          ▼
      PostgreSQL  DeepSeek   本地文件存储
       (Neon)      API       (uploads/)
```

## 功能列表

- 邀请码注册（防止未授权用户注册）
- 用户登录（JWT Token 认证，24 小时过期）
- AI 智能对话（接入 DeepSeek API）
- SSE 流式输出（逐字返回，类似 ChatGPT 效果）
- 多轮对话上下文（最近 10 轮记忆）
- RAG 检索增强（上传 PDF/Word 后，AI 基于文档内容回答）
- 聊天记录持久化（PostgreSQL）
- Token 用量追踪（记录每次请求的 prompt/completion tokens）
- 管理员接口（查看所有用户及用量）
- 文件上传与文字提取（PDF/Word）
- 聊天记录删除（单条 / 全部清空）
- 请求日志中间件
- 移动端响应式布局
- CORS 跨域支持

## API 接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/health` | 健康检查 | 否 |
| POST | `/auth/register` | 用户注册（需邀请码） | 否 |
| POST | `/auth/login` | 用户登录，返回 JWT Token | 否 |
| GET | `/auth/me` | 获取当前用户信息及 Token 用量 | 是 |
| GET | `/auth/admin/users` | 管理员查看所有用户（仅 user_id=1） | 是 |
| POST | `/chat` | AI 对话（一次性返回） | 是 |
| POST | `/chat/stream` | AI 对话（SSE 流式输出） | 是 |
| POST | `/chat/history` | 查询聊天记录 | 是 |
| DELETE | `/chat` | 清空所有聊天记录 | 是 |
| DELETE | `/chat/{message_id}` | 删除指定聊天记录 | 是 |
| POST | `/upload` | 文件上传（PDF/Word 文字提取） | 是 |

## 本地运行

### 后端

```bash
git clone https://github.com/HYY142857/ai-chat-backend.git
cd ai-chat-backend

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt

# 创建 .env 文件（参考 .env.example）
cp .env.example .env

# 启动服务
uvicorn app.main:app --reload
```

启动后访问 http://127.0.0.1:8000/docs 查看 API 文档。

### 前端

```bash
git clone https://github.com/HYY142857/ai-chat-frontend.git
cd ai-chat-frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## 环境变量

参考 [.env.example](.env.example) 文件，在 Render 部署时需要在 Environment 中配置对应变量。

## 项目结构

```
ai-chat-backend/
├── app/
│   ├── main.py              # FastAPI 应用入口 + ORM 配置 + 中间件
│   ├── routers/
│   │   ├── auth.py          # 注册/登录/用户信息/管理员接口
│   │   ├── chat.py          # 对话/流式输出/历史/删除
│   │   └── upload.py        # 文件上传与文字提取
│   ├── models/
│   │   ├── user.py          # 用户模型（含 total_tokens）
│   │   ├── chat_message.py  # 聊天记录模型（含 token 用量）
│   │   └── file_record.py   # 文件记录模型
│   └── utils/
│       ├── auth.py          # JWT 认证模块
│       └── rag.py           # RAG 检索模块
├── uploads/                  # 上传文件存储目录
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## 数据库 ER 图

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────────┐
│    users     │       │  chat_messages   │       │   file_records   │
├──────────────┤       ├──────────────────┤       ├──────────────────┤
│ id (PK)      │──┐    │ id (PK)          │       │ id (PK)          │
│ username     │  │    │ user_id (FK)     │       │ user_id (FK)     │
│ password     │  ├───<│ message          │  ┌────│ original_name    │
│ total_tokens │  │    │ reply            │  │    │ saved_name       │
│ created_at   │  │    │ prompt_tokens    │  │    │ file_size        │
└──────────────┘  │    │ completion_tokens│  │    │ content          │
                  │    │ created_at       │  │    │ created_at       │
                  │    └──────────────────┘  │    └──────────────────┘
                  │                          │
                  └──────────────────────────┘
```

## 部署

- **后端**：Render (https://ai-chat-backend-be6s.onrender.com)
- **前端**：Vercel (https://ai-chat-frontend-lilac.vercel.app)
- **数据库**：Neon PostgreSQL（免费 0.5GB）
- **容器化**：Docker 镜像 `hyy1119/ai-chat-backend:latest`

## License

MIT
