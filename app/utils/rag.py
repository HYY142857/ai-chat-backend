from app.utils.vector_store import search_documents


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """
    把长文本切成小块，带 overlap 避免边界信息丢失
    """
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i:i + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def retrieve_relevant_chunks(query: str, user_id: int, top_k: int = 5) -> list:
    """
    从向量数据库中找出跟 query 最相关的片段
    返回：[{"chunk": "...", "score": 0.xx, "filename": "..."}]
    """
    results = search_documents(user_id, query, top_k=top_k)

    # 过滤掉相似度太低的（低于 0.3 认为不相关）
    filtered = [r for r in results if r["score"] >= 0.3]

    return filtered


def build_context_prompt(relevant_chunks: list) -> str:
    """
    把检索到的相关片段拼成 RAG 的上下文 prompt
    """
    if not relevant_chunks:
        return ""

    # 按文件分组
    file_chunks = {}
    for item in relevant_chunks:
        fname = item["filename"]
        if fname not in file_chunks:
            file_chunks[fname] = []
        file_chunks[fname].append(item["chunk"])

    # 拼接
    parts = []
    for fname, chunks in file_chunks.items():
        content = "\n\n".join(chunks)
        parts.append(f"【文件：{fname}】\n{content}")

    return "\n\n".join(parts)
