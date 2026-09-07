def chunk_text(text: str, chunk_size: int = 500) -> list:
    """把长文本切成小块"""
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])
    return chunks

def retrieve_relevant_chunks(query: str, documents: list) -> list:
    """从文档列表中找出跟 query 最相关的片段"""

    # 去掉常见的无意义字符
    stop_chars = set("的了是在我你他她它们这个那些什么吗呢吧啊哦？！，。、：； ")
    keywords = [ch for ch in query if ch not in stop_chars and ch.strip()]

    if len(keywords) < 4:
        return []  # 问题太短，不做 RAG 检索

    scored_chunks = []
    for doc in documents:
        chunks = chunk_text(doc["content"])
        for chunk in chunks:
            score = sum(1 for kw in keywords if kw in chunk)
            # 至少匹配 5 个关键词，且匹配率 >= 50%
            if score >= 5 and score / len(keywords) >= 0.5:
                scored_chunks.append({"chunk": chunk, "score": score})

    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    return [item["chunk"] for item in scored_chunks[:5]]