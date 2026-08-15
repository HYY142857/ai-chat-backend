from fastapi import APIRouter
from pydantic import BaseModel
from app.models.user import User
from app.models.chat_message import ChatMessage
from openai import AsyncOpenAI
from fastapi.responses import StreamingResponse
from fastapi import Depends, HTTPException
from app.utils.auth import get_current_user

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


class HistoryResponse(BaseModel):
    messages: list

# 创建客户端
client = AsyncOpenAI(
    api_key="sk-f423fb4302d547b3a5b05c331fc12b8c",
    base_url="https://api.deepseek.com"
)

@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest,user_id: int = Depends(get_current_user)):
    # 查出这个用户
    user = await User.filter(id=user_id).first()

    # 查出最近 10 条聊天记录（倒序，最新的在后面）
    history = await ChatMessage.filter(user_id=user_id).order_by("-created_at").limit(10)
    history = list(reversed(history))  # 加上这行，变成正序
    # 拼成 messages 数组
    messages = []
    for record in history:
        messages.append({"role": "user", "content": record.message})
        messages.append({"role": "assistant", "content": record.reply})

    # 加上当前这条消息
    messages.append({"role": "user", "content": req.message})

    # 调用 DeepSeek API
    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=messages
    )
    reply_text = response.choices[0].message.content
    

    # 存进数据库
    await ChatMessage.create(user=user, message=req.message, reply=reply_text)

    return {"reply": reply_text}

@router.post("/history")
async def history(user_id: int = Depends(get_current_user)):
    # 查出这个用户的所有聊天记录
    records = await ChatMessage.filter(user_id=user_id).order_by("created_at")

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
async def chat_stream(req: ChatRequest, user_id: int = Depends(get_current_user)):
    user = await User.filter(id=user_id).first()

    # 查出最近 10 条聊天记录（倒序，最新的在后面）
    history = await ChatMessage.filter(user_id=user_id).order_by("-created_at").limit(10)
    history = list(reversed(history))  # 加上这行，变成正序

    # 拼成 messages 数组
    messages = []
    for record in history:
        messages.append({"role": "user", "content": record.message})
        messages.append({"role": "assistant", "content": record.reply})

    # 加上当前这条消息
    messages.append({"role": "user", "content": req.message})
    
    # 调用 DeepSeek，开启流式
    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
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

@router.delete("/{message_id}")
async def delete_message(message_id: int, user_id: int = Depends(get_current_user)):
    # 查出这条记录
    record = await ChatMessage.filter(id=message_id, user_id=user_id).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="聊天记录不存在")

    await record.delete()
    return {"message": "删除成功"}

@router.delete("")
async def delete_all_messages(user_id: int = Depends(get_current_user)):
    await ChatMessage.filter(user_id=user_id).delete()
    return {"message": "已清空所有聊天记录"}