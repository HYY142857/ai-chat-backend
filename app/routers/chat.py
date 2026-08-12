from fastapi import APIRouter
from pydantic import BaseModel
from app.models.user import User
from app.models.chat_message import ChatMessage
from openai import AsyncOpenAI
from fastapi.responses import StreamingResponse

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

# 创建客户端
client = AsyncOpenAI(
    api_key="sk-f423fb4302d547b3a5b05c331fc12b8c",
    base_url="https://api.deepseek.com"
)

@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # 查出这个用户
    user = await User.filter(id=req.user_id).first()

    # 调用 DeepSeek API
    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": req.message}
        ]
    )
    reply_text = response.choices[0].message.content
    

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

@router.post("/stream")
async def chat_stream(req: ChatRequest):
    user = await User.filter(id=req.user_id).first()

    # 调用 DeepSeek，开启流式
    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": req.message}],
        stream=True
    )

    # 定义一个生成器，一块一块地发数据
    async def generate():
        full_reply = ""
        async for chunk in response:
            piece = chunk.choices[0].delta.content
            if piece:
                full_reply += piece
                yield f"data: {piece}\n\n"  # SSE 格式

        # 流结束后存数据库
        await ChatMessage.create(user=user, message=req.message, reply=full_reply)
        yield "data: [DONE]\n\n"  # 告诉前端结束了

    return StreamingResponse(generate(), media_type="text/event-stream")