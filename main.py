"""
FastAPI 主入口：提供文件上传、处理状态、问答三个 API，
以及一个前端页面（/ 路径）。
"""

import os
import re
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import UPLOAD_DIR
from indexer import process_documents, processing_status, get_index
from query import query_documents


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    启动钩子：Railway 免费版没有持久化存储，每次重新部署 chroma_db 都会被清空。
    所以启动时检测：如果还没有索引，就自动重建（优先用户上传，无上传时用内置示例文档），
    让 demo 部署完就能直接提问，不需要人手动点"处理文档"。
    """
    try:
        if get_index() is None:
            count = process_documents()
            print(f"[startup] 检测到没有索引，自动重建完成，共 {count} 份文档")
        else:
            print("[startup] 已有索引，跳过自动重建")
    except Exception as e:
        # 失败不阻止启动：用户仍可在页面上手动点"处理文档"
        print(f"[startup] 自动重建索引失败: {e}")
    yield


app = FastAPI(title="知识库问答 RAG 应用", lifespan=lifespan)

# 静态文件目录（前端页面）
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 允许的文件类型
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_UPLOAD_FILES = 5
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_UPLOAD_BYTES = 20 * 1024 * 1024


def safe_upload_filename(filename: str | None) -> str:
    """Return a short, cross-platform filename without path or reserved-name hazards."""
    basename = (filename or "").replace("\\", "/").split("/")[-1]
    cleaned = re.sub(r'[\x00-\x1f<>:"/\\|?*]', "_", basename).strip(" .")[:180]
    if not cleaned:
        return "document"
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    if cleaned.split(".", 1)[0].upper() in reserved:
        cleaned = "_" + cleaned
    return cleaned


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=20)


@app.get("/")
def home():
    """首页"""
    return FileResponse("static/index.html")


# ===== API 1：文件上传 =====
@app.post("/api/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    """
    上传一个或多个文档。
    支持 PDF、TXT、MD 格式。
    """
    if not files:
        raise HTTPException(status_code=400, detail="请至少选择一个文件")
    if len(files) > MAX_UPLOAD_FILES:
        raise HTTPException(status_code=413, detail=f"一次最多上传 {MAX_UPLOAD_FILES} 个文件")

    prepared_files = []
    total_bytes = 0
    for file in files:
        filename = safe_upload_filename(file.filename)
        # 校验文件类型
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {ext}，仅支持 {', '.join(ALLOWED_EXTENSIONS)}",
            )

        content = await file.read(MAX_FILE_BYTES + 1)
        if not content:
            raise HTTPException(status_code=400, detail=f"文件内容为空：{filename}")
        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail=f"单个文件不能超过 {MAX_FILE_BYTES // (1024 * 1024)} MB：{filename}")
        total_bytes += len(content)
        if total_bytes > MAX_TOTAL_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="本次上传总大小不能超过 20 MB")
        prepared_files.append((filename, content))

    saved_files = []
    for filename, content in prepared_files:
        # 随机前缀避免同名文件覆盖；原名仍保留在文件路径中供检索溯源。
        stored_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        file_path = os.path.join(UPLOAD_DIR, stored_name)
        with open(file_path, "wb") as f:
            f.write(content)
        saved_files.append(filename)

    return {"message": f"成功上传 {len(saved_files)} 个文件", "files": saved_files}


# ===== API 2：开始处理文档 =====
@app.post("/api/process")
def start_processing():
    """对已上传的文档执行：读取 → 切片 → embedding → 存向量库"""
    count = process_documents()
    return {"message": f"处理完成，共 {count} 份文档", "doc_count": count}


# ===== API 3：查询处理状态 =====
@app.get("/api/status")
def get_status():
    """获取当前处理状态（前端轮询使用）"""
    # 补充索引信息
    index = get_index()
    return {
        **processing_status,
        "has_index": index is not None,
    }


# ===== API 4：调试：查看有哪些文件 =====
@app.get("/api/files")
def list_files():
    """查看 sample_docs 和 uploads 目录各有什么文件"""
    import os as _os
    sample_dir = _os.path.join(_os.path.dirname(__file__), "sample_docs")
    return {
        "sample_docs": _os.listdir(sample_dir) if _os.path.isdir(sample_dir) else [],
        "uploads": _os.listdir(UPLOAD_DIR) if _os.path.isdir(UPLOAD_DIR) else [],
    }

# ===== API 5：问答 =====
@app.get("/api/query")
def ask(question: str):
    """
    向知识库提问。
    必须传参数 ?question=你的问题
    """
    if not question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")
    result = query_documents(question.strip())
    return result


@app.post("/api/query")
def ask_with_history(body: QueryRequest):
    """向知识库提问，并带上当前浏览器会话中最近的对话上下文。"""
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")
    result = query_documents(body.question.strip(), body.history)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
