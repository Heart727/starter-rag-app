"""
文档索引模块：加载文档 → 切片 → 生成 embedding → 存入 Chroma 向量库

Embedding 使用 HuggingFace 本地模型（all-MiniLM-L6-v2，约 80MB）。
国内开发时通过 HF_ENDPOINT 镜像下载，部署后直接访问 HuggingFace。
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

from config import UPLOAD_DIR, CHROMA_DIR

# 示例文档目录（随代码打包，部署后始终可用）
SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_docs")

# ----- 全局状态 -----
processing_status = {
    "status": "idle",
    "message": "",
    "doc_count": 0,
}

# ----- Embedding 模型（HuggingFace，首次自动下载 ~80MB）-----
# 国内开发：设置 HF_ENDPOINT=https://hf-mirror.com
# 部署环境：不用设，直接连 HuggingFace
print("[indexer] Loading Embedding model...")
embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")

Settings.embed_model = embed_model
Settings.node_parser = SentenceSplitter(chunk_size=500, chunk_overlap=50)


def get_index():
    """获取或创建向量索引"""
    db_path = os.path.join(CHROMA_DIR)
    if not os.path.exists(db_path) or not os.listdir(db_path):
        return None

    chroma_client = chromadb.PersistentClient(path=db_path)
    try:
        collection = chroma_client.get_collection("rag_docs")
    except Exception:
        return None

    vector_store = ChromaVectorStore(chroma_collection=collection)
    return VectorStoreIndex.from_vector_store(vector_store)


def process_documents():
    """处理上传目录中的所有文档，返回文档数量"""
    global processing_status
    processing_status = {"status": "processing", "message": "正在读取文档...", "doc_count": 0}

    # 合并示例文档和用户上传文档
    all_files = []
    if os.path.isdir(SAMPLE_DIR):
        all_files.extend(os.listdir(SAMPLE_DIR))
    if os.path.isdir(UPLOAD_DIR):
        all_files.extend(os.listdir(UPLOAD_DIR))

    if not all_files:
        processing_status = {"status": "idle", "message": "没有待处理的文档", "doc_count": 0}
        return 0

    try:
        processing_status["message"] = "正在读取文档..."
        # 分别加载两个目录的文档
        documents = []
        if os.path.isdir(SAMPLE_DIR) and os.listdir(SAMPLE_DIR):
            documents.extend(SimpleDirectoryReader(SAMPLE_DIR).load_data())
        if os.path.isdir(UPLOAD_DIR) and os.listdir(UPLOAD_DIR):
            documents.extend(SimpleDirectoryReader(UPLOAD_DIR).load_data())
        processing_status["doc_count"] = len(documents)

        if not documents:
            processing_status = {"status": "done", "message": "未找到可解析的内容", "doc_count": 0}
            return 0

        processing_status["message"] = "正在切片并生成向量..."

        db_path = os.path.join(CHROMA_DIR)
        if os.path.exists(db_path):
            shutil.rmtree(db_path)
        os.makedirs(db_path, exist_ok=True)

        chroma_client = chromadb.PersistentClient(path=db_path)
        chroma_collection = chroma_client.create_collection("rag_docs")
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        VectorStoreIndex.from_documents(documents, storage_context=storage_context, show_progress=True)

        processing_status = {
            "status": "done",
            "message": f"处理完成，共 {len(documents)} 份文档",
            "doc_count": len(documents),
        }
        return len(documents)

    except Exception as e:
        processing_status = {"status": "error", "message": f"处理失败: {str(e)}", "doc_count": 0}
        return 0
