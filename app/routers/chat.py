from fastapi import APIRouter,Depends, HTTPException
from pydantic import BaseModel
from app.models.user import User
from app.models.chat_message import ChatMessage
from app.models.conversation import Conversation
from app.models.file_record import FileRecord
from openai import AsyncOpenAI
from fastapi.responses import StreamingResponse
from app.utils.auth import get_current_user
import os
import asyncio

router = APIRouter(prefix="/chat", tags=["Chat"])

async def summarise_title(client, conversation, user_first_message: str, assistant_first_reply: str):
    """
    同步：让 LLM 总结对话标题，更新 Conversation.title
    """
    try:
        # 把规则、例子、实际问题都放在 user message 里，避免 prompt 混淆
        prompt = f"""请根据以下规则，为用户的问题生成一个简洁的中文标题。

【规则】
- 5-15 字，概括对话主题
- 只输出标题本身，不要加任何解释、引号、句号、换行
- 可以包含常见英文缩写（如 GPT、CPU、iOS），但不要输出英文单词后缀
- 不要直接复制用户的问题原文，要提炼概括

【例子】
问题：洋葱浏览器区别于其他浏览器的地方在于？
标题：洋葱浏览器与普通浏览器的核心区别

问题：GPT-4 和 Claude 哪个更强？
标题：GPT-4 与 Claude 能力对比

问题：Python 怎么快速入门？
标题：Python 快速入门方法

【用户的问题】
{user_first_message}

【现在请直接输出标题】"""

        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个简洁的中文标题生成器。只输出标题本身。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=50,
        )
        new_title = response.choices[0].message.content
        print(f"[Title] 原始输出: '{new_title}'", flush=True)
        
        # 最基本清理
        new_title = new_title.strip()
        new_title = new_title.strip('"\'「」『』《》()（）')
        new_title = new_title.strip()
        new_title = new_title.rstrip('。.！!？?')
        new_title = new_title.strip()
        
        # 兜底：如果 AI 输出太长（可能把规则或问题抄进去了），只取前 15 字
        if len(new_title) > 30:
            print(f"[Title] 输出过长，截断: '{new_title}'", flush=True)
            new_title = new_title[:15]
        
        if new_title and len(new_title) >= 2:
            conversation.title = new_title
            await conversation.save()
            print(f"[Title] 会话 {conversation.id} 标题更新为: {new_title}", flush=True)
        else:
            print(f"[Title] 总结结果无效，保留默认标题: '{new_title}'", flush=True)
    except Exception as e:
        print(f"[Title] 总结失败，保留默认标题（可忽略）: {e}", flush=True)

# 新建会话
@router.post("/conversations", response_model=dict)
async def create_conversation(user_id: int = Depends(get_current_user)):
    user = await User.filter(id=user_id).first()
    conv = await Conversation.create(user=user)
    return {"id": conv.id, "title": conv.title, "created_at": str(conv.created_at)}

# 获取会话列表
@router.get("/conversations")
async def list_conversations(user_id: int = Depends(get_current_user)):
    convs = await Conversation.filter(user_id=user_id).order_by("-updated_at")
    result = []
    for c in convs:
        # 取这个会话第一条消息作为预览
        first_msg = await ChatMessage.filter(conversation_id=c.id).order_by("created_at").first()
        preview = first_msg.message if first_msg else "(空会话)"
        result.append({
            "id": c.id,
            "title": c.title,
            "preview": preview[:30],  # 前 30 字作为左侧预览
            "created_at": str(c.created_at),
        })
    return {"conversations": result}

# 删除会话（连带删除该会话所有消息）
@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: int, user_id: int = Depends(get_current_user)):
    conv = await Conversation.filter(id=conv_id, user_id=user_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    await ChatMessage.filter(conversation_id=conv_id).delete()
    await conv.delete()
    return {"message": "会话已删除"}


class ChatRequest(BaseModel):
    message: str
    conversation_id: int | None = None  # 可选，如果不传就不关联会话  


class ChatResponse(BaseModel):
    reply: str


class HistoryResponse(BaseModel):
    messages: list

# 创建客户端
client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest,user_id: int = Depends(get_current_user)):
    # 查出这个用户
    user = await User.filter(id=user_id).first()

     # 处理会话：有 conversation_id 就用，没有就新建
    if req.conversation_id:
        conversation = await Conversation.filter(id=req.conversation_id, user_id=user_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        # 新建会话，用默认 title "新对话"，AI 总结后才更新
        conversation = await Conversation.create(user=user)

    # 判断：只有 title 还是默认的 "新对话" 才触发总结（只触发一次）
    should_summarise_title = (conversation.title == "新对话")

    # 关键改动：查历史只查这个会话的，不再查所有消息
    history = await ChatMessage.filter(
        conversation_id=conversation.id
    ).order_by("-created_at").limit(10)
    history = list(reversed(history))
    
    # 拼成 messages 数组
    messages = []
    for record in history:
        messages.append({"role": "user", "content": record.message})
        messages.append({"role": "assistant", "content": record.reply})

    # 加上当前这条消息
    messages.append({"role": "user", "content": req.message})

    # 向量检索：从 ChromaDB 找跟问题最相关的片段
    from app.utils.rag import retrieve_relevant_chunks, build_context_prompt
    relevant_chunks = retrieve_relevant_chunks(req.message, user_id, top_k=5)
    context = build_context_prompt(relevant_chunks)

    if context:
        messages.insert(0, {
            "role": "system",
            "content": (
                "以下是从用户上传的文件中检索到的相关内容，"
                "请严格基于这些内容回答用户的问题，不要编造。"
                "如果检索内容里没有答案，就说'在上传的文件中没有找到相关信息'。\n\n"
                f"{context}"
            )
        })

    # 调用 DeepSeek API
    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=messages
    )
    reply_text = response.choices[0].message.content
    

    # 存进数据库
    await ChatMessage.create(user=user, 
                             conversation=conversation,
                             message=req.message, 
                             reply=reply_text, 
                             prompt_tokens=response.usage.prompt_tokens, 
                             completion_tokens=response.usage.completion_tokens
                            )
    
    # 如果是新建会话，同步等标题总结完再返回（前端刷新时就是新标题）
    if should_summarise_title:
        await summarise_title(client, conversation, req.message, reply_text)
    
    user.total_tokens += response.usage.prompt_tokens + response.usage.completion_tokens
    await user.save()
    await conversation.save()  # 直接 save，updated_at 会自动更新

    return {"reply": reply_text,"conversation_id": conversation.id}

@router.get("/conversations/{conv_id}/messages")
async def get_conversation_messages(conv_id: int, user_id: int = Depends(get_current_user)):
    # 确认会话属于这个用户
    conv = await Conversation.filter(id=conv_id, user_id=user_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    records = await ChatMessage.filter(conversation_id=conv_id).order_by("created_at")
    result = []
    for r in records:
        result.append({
            "id": r.id,
            "message": r.message,
            "reply": r.reply,
            "created_at": str(r.created_at),
        })
    return {"messages": result}

@router.post("/stream")
async def chat_stream(req: ChatRequest, user_id: int = Depends(get_current_user)):
    user = await User.filter(id=user_id).first()

     # 处理会话：有 conversation_id 就用，没有就新建
    if req.conversation_id:
        conversation = await Conversation.filter(id=req.conversation_id, user_id=user_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        # 新建会话，用默认 title "新对话"，AI 总结后才更新
        conversation = await Conversation.create(user=user)

    # 判断：只有 title 还是默认的 "新对话" 才触发总结（只触发一次）
    should_summarise_title = (conversation.title == "新对话")

    # 关键改动：查历史只查这个会话的，不再查所有消息
    history = await ChatMessage.filter(
        conversation_id=conversation.id
    ).order_by("-created_at").limit(10)
    history = list(reversed(history))

    # 拼成 messages 数组
    messages = []
    for record in history:
        messages.append({"role": "user", "content": record.message})
        messages.append({"role": "assistant", "content": record.reply})

    # 向量检索：从 ChromaDB 找跟问题最相关的片段
    from app.utils.rag import retrieve_relevant_chunks, build_context_prompt
    relevant_chunks = retrieve_relevant_chunks(req.message, user_id, top_k=5)
    context = build_context_prompt(relevant_chunks)

    if context:
        messages.insert(0, {
            "role": "system",
            "content": (
                "以下是从用户上传的文件中检索到的相关内容，"
                "请严格基于这些内容回答用户的问题，不要编造。"
                "如果检索内容里没有答案，就说'在上传的文件中没有找到相关信息'。\n\n"
                f"{context}"
            )
        })

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
        try:
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            completion_tokens = response.usage.completion_tokens if response.usage else 0
        except AttributeError:
            prompt_tokens = 0
            completion_tokens = 0

        await ChatMessage.create(user=user, 
                                 message=req.message, 
                                 conversation=conversation,
                                 reply=full_reply,
                                 prompt_tokens=prompt_tokens, 
                                 completion_tokens=completion_tokens
                                )

        # 如果是新建会话，同步等标题总结完再返回（前端刷新时就是新标题）
        if should_summarise_title and full_reply:
            await summarise_title(client, conversation, req.message, full_reply)

        if prompt_tokens or completion_tokens:
            user.total_tokens += prompt_tokens + completion_tokens
            await user.save()
        yield "data: [DONE]\n\n"  # 告诉前端结束了

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"conversation_id": str(conversation.id)})

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