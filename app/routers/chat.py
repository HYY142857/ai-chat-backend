from fastapi import APIRouter
from pydantic import BaseModel
from app.models.user import User
from app.models.chat_message import ChatMessage

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    user_id: int
    message: str


class ChatResponse(BaseModel):
    reply: str


class HistoryRequest(BaseModel):
    user_id: int


class HistoryResponse(BaseModel):
    messages: list

@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # 查出这个用户
    user = await User.filter(id=req.user_id).first()

    # AI 的回复（暂时写死）
    reply_text = f"收到：{req.message}"

    # 存进数据库
    await ChatMessage.create(user=user, message=req.message, reply=reply_text)

    return {"reply": reply_text}

@router.post("/history")
async def history(req: HistoryRequest):
    # 查出这个用户的所有聊天记录
    records = await ChatMessage.filter(user_id=req.user_id).order_by("created_at")

    # 把每条记录整理成字典返回
    result = []
    for r in records:
        result.append({
            "message": r.message,
            "reply": r.reply,
            "created_at": str(r.created_at),
        })

    return {"messages": result}