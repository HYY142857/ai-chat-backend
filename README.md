# AI Chat Backend

基于 FastAPI 构建的 AI 智能对话后端系统，集成 DeepSeek 大模型 API，支持 SSE 流式输出、JWT 用户认证、聊天记录持久化。

**在线演示**：https://ai-chat-backend-be6s.onrender.com/docs

## 技术栈

- **后端框架**：FastAPI
- **ORM**：Tortoise ORM
- **数据库**：SQLite
- **AI 模型**：DeepSeek API
- **认证**：JWT（PyJWT）+ HTTPBearer
- **流式输出**：Server-Sent Events (SSE)
- **容器化**：Docker

## 功能列表

- 用户注册与登录（密码哈希存储）
- JWT Token 认证（HTTPBearer，支持 Swagger UI 自动授权）
- AI 智能对话（接入 DeepSeek API）
- SSE 流式输出（逐字返回，类似 ChatGPT 效果）
- 聊天记录存储与历史查询（仅可查看自己的记录）
- 文件上传（UUID 重命名，关联用户）
- 请求日志中间件（记录请求方法、路径、状态码、耗时）
- CORS 跨域支持

## API 接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/health` | 健康检查 | 否 |
| POST | `/auth/register` | 用户注册 | 否 |
| POST | `/auth/login` | 用户登录，返回 JWT Token | 否 |
| POST | `/chat` | AI 对话（一次性返回） | 是 |
| POST | `/chat/stream` | AI 对话（SSE 流式输出） | 是 |
| POST | `/chat/history` | 查询当前用户的聊天记录 | 是 |
| POST | `/upload` | 文件上传 | 是 |

## 本地运行

### 环境要求

- Python 3.11+
- pip

### 安装与启动

```bash
# 克隆项目
git clone https://github.com/HYY142857/ai-chat-backend.git
cd ai-chat-backend

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload
```

启动后访问 http://127.0.0.1:8000/docs 查看 API 文档。

### Docker 运行

```bash
# 构建镜像
docker build -t ai-chat-backend .

# 运行容器
docker run -p 8000:8000 ai-chat-backend
```

## 项目结构

```
ai-chat-backend/
├── app/
│   ├── main.py              # FastAPI 应用入口 + 中间件 + ORM 配置
│   ├── routers/
│   │   ├── auth.py          # 注册/登录接口
│   │   ├── chat.py          # 对话/历史/流式输出接口
│   │   └── upload.py        # 文件上传接口
│   ├── models/
│   │   ├── user.py          # 用户模型
│   │   └── chat_message.py  # 聊天记录模型
│   ├── schemas/
│   ├── services/
│   └── utils/
├── uploads/                  # 上传文件存储目录
├── Dockerfile
├── requirements.txt
└── README.md
```

## 部署

项目使用 Docker 容器化，已部署至 Render 云平台。

- Docker Hub 镜像：`hyy1119/ai-chat-backend:latest`
- 在线地址：https://ai-chat-backend-be6s.onrender.com

## 使用示例

### 注册

```bash
curl -X POST https://ai-chat-backend-be6s.onrender.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "123456"}'
```

### 登录

```bash
curl -X POST https://ai-chat-backend-be6s.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "123456"}'
```

### AI 对话（需携带 Token）

```bash
curl -X POST https://ai-chat-backend-be6s.onrender.com/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token>" \
  -d '{"message": "你好"}'
```

## License

MIT
