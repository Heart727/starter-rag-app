"""
文档索引模块：加载文档 → 切片 → 生成 embedding → 存入 Chroma 向量库

使用 LlamaIndex 封装整个流程，一个 SimpleDirectoryReader + VectorStoreIndex 搞定。
"""

import os
import shutil
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

from config import UPLOAD_DIR, CHROMA_DIR, EMBEDDING_MODEL

# ----- 全局状态（简单记录处理进度）-----
processing_status = {
    "status": "idle",       # idle | processing | done | error
    "message": "",
    "doc_count": 0,
}

# ----- 初始化 Embedding 模型 -----
# 首次运行会从 HuggingFace 下载模型（约 80MB），之后缓存本地
print(f"[indexer] 加载 Embedding 模型: {EMBEDDING_MODEL} ...")
embed_model = HuggingFaceEmbedding(model_name=EMBEDDING_MODEL)

# 设置 LlamaIndex 全局配置
Settings.embed_model = embed_model
Settings.node_parser = SentenceSplitter(chunk_size=500, chunk_overlap=50)


def get_index():
    """
    获取或创建向量索引。
    - 如果 chroma_db 已有数据，直接加载
    - 否则返回 None（需要先上传文档）
    """
    db_path = os.path.join(CHROMA_DIR)
    if not os.path.exists(db_path) or not os.listdir(db_path):
        return None

    # 连接已有 Chroma 数据库
    chroma_client = chromadb.PersistentClient(path=db_path)
    try:
        collection = chroma_client.get_collection("rag_docs")
    except Exception:
        return None

    vector_store = ChromaVectorStore(chroma_collection=collection)
    return VectorStoreIndex.from_vector_store(vector_store)


def process_documents():
    """
    处理上传目录中的所有文档：
    1. 读取所有文件
    2. 切片为段落
    3. 生成 embedding 向量
    4. 存入 Chroma 向量库

    返回处理后的文档数量。
    """
    global processing_status
    processing_status = {"status": "processing", "message": "正在读取文档...", "doc_count": 0}

    # 检查上传目录是否有文件
    files = os.listdir(UPLOAD_DIR)
    if not files:
        processing_status = {"status": "idle", "message": "没有待处理的文档", "doc_count": 0}
        return 0

    try:
        # 步骤 1：读取文档
        processing_status["message"] = "正在读取文档..."
        documents = SimpleDirectoryReader(UPLOAD_DIR).load_data()
        processing_status["doc_count"] = len(documents)

        if not documents:
            processing_status = {"status": "done", "message": "未找到可解析的内容", "doc_count": 0}
            return 0

        # 步骤 2+3+4：切片 → embedding → 存入 Chroma
        processing_status["message"] = "正在切片并生成向量..."

        # 清空旧向量库，重建
        db_path = os.path.join(CHROMA_DIR)
        if os.path.exists(db_path):
            shutil.rmtree(db_path)
        os.makedirs(db_path, exist_ok=True)

        # 创建 Chroma 客户端和集合
        chroma_client = chromadb.PersistentClient(path=db_path)
        chroma_collection = chroma_client.create_collection("rag_docs")
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        # 构建索引（自动完成切片、embedding、存储）
        VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            show_progress=True,
        )

        processing_status = {
            "status": "done",
            "message": f"处理完成，共 {len(documents)} 份文档",
            "doc_count": len(documents),
        }
        return len(documents)

    except Exception as e:
        processing_status = {
            "status": "error",
            "message": f"处理失败: {str(e)}",
            "doc_count": 0,
        }
        return 0
