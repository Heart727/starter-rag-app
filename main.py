"""
FastAPI 主入口：提供文件上传、处理状态、问答三个 API，
以及一个前端页面（/ 路径）。
"""

import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import UPLOAD_DIR
from indexer import process_documents, processing_status, get_index
from query import query_documents

app = FastAPI(title="知识库问答 RAG 应用")

# 静态文件目录（前端页面）
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 允许的文件类型
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


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
    saved_files = []
    for file in files:
        # 校验文件类型
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {ext}，仅支持 {', '.join(ALLOWED_EXTENSIONS)}",
            )

        # 保存文件
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        saved_files.append(file.filename)

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


# ===== API 4：问答 =====
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
