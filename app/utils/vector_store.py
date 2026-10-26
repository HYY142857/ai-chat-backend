import os
import chromadb
from chromadb.config import Settings
from openai import OpenAI

# 初始化 Embedding 客户端（用 DeepSeek 的 embedding 接口）
embed_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# ChromaDB 持久化目录
CHROMA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "chroma_db"
)

# 初始化 ChromaDB 客户端
chroma_client = chromadb.PersistentClient(
    path=CHROMA_DIR,
    settings=Settings(anonymized_telemetry=False)
)

# 获取或创建 collection（整个项目用一个 collection，靠 user_id 过滤）
collection = chroma_client.get_or_create_collection(
    name="rag_documents",
    metadata={"hnsw:space": "cosine"}  # 余弦相似度
)

def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    调用硅基流动 BGE-M3 Embedding 接口
    """
    from dotenv import load_dotenv
    load_dotenv()

    #优先BGE-M3 Embedding接口
    api_key = os.getenv("SILICONFLOW_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("请在 .env 文件中设置 SILICONFLOW_API_KEY 或 DEEPSEEK_API_KEY")

    embed_client = OpenAI(
        api_key=api_key,
        base_url="https://api.siliconflow.cn/v1"
    )

    response = embed_client.embeddings.create(
        model="BAAI/bge-m3",
        input=texts
    )
    return [item.embedding for item in response.data]

def add_documents(user_id: int, file_id: int, filename: str, chunks: list[str]):
    """
    把一个文件的多个文本块存入向量数据库
    user_id: 用于隔离不同用户的数据
    file_id: FileRecord 的 ID
    filename: 原始文件名
    chunks: 切好的文本块列表
    """
    if not chunks:
        return

    # 批量生成 embedding
    embeddings = get_embeddings(chunks)

    # 每个 chunk 一个唯一 ID
    ids = [f"user_{user_id}_file_{file_id}_chunk_{i}" for i in range(len(chunks))]

    # 元数据：用来过滤和溯源
    metadatas = [
        {"user_id": user_id, "file_id": file_id, "filename": filename, "chunk_index": i}
        for i in range(len(chunks))
    ]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas
    )

def search_documents(user_id: int, query: str, top_k: int = 5) -> list[dict]:
    """
    在指定用户的文档中，搜索跟 query 最相关的文本块
    返回：[{"chunk": "...", "score": 0.xx, "filename": "..."}]
    """
    # 把问题转成向量
    query_embedding = get_embeddings([query])[0]

    # 向量搜索，按 user_id 过滤
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={"user_id": user_id}
    )

    # 整理结果
    documents = results["documents"][0] if results["documents"] else []
    metadatas = results["metadatas"][0] if results["metadatas"] else []
    distances = results["distances"][0] if results["distances"] else []

    output = []
    for i, doc in enumerate(documents):
        # ChromaDB 返回的是 distance（距离），越小越相似
        # 转成相似度分数，越大越相似（方便理解）
        distance = distances[i] if i < len(distances) else 1.0
        similarity = 1.0 - distance  # 余弦距离转相似度近似值
        filename = metadatas[i].get("filename", "未知文件") if i < len(metadatas) else "未知文件"
        output.append({
            "chunk": doc,
            "score": round(similarity, 4),
            "filename": filename
        })

    return output

def delete_file_documents(user_id: int, file_id: int):
    """
    删除某个文件对应的所有向量（比如文件被删了的时候调用）
    """
    # 先查再删（ChromaDB 不支持按 where 条件直接删，需要拿 id 列表）
    results = collection.get(
        where={"user_id": user_id, "file_id": file_id}
    )
    if results["ids"]:
        collection.delete(ids=results["ids"])