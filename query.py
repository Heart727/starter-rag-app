"""
问答模块：检索相关文档片段 → 拼接 prompt → DeepSeek 生成答案（带出处）
"""

import requests
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from indexer import get_index


def query_documents(question: str) -> dict:
    """
    查询知识库：
    1. 加载向量索引
    2. 检索最相关的文档片段（top-k=3）
    3. 拼接上下文 prompt
    4. 调用 DeepSeek API 生成答案和出处

    返回 {"answer": str, "sources": list} 或 {"error": str}
    """
    # 检查 API Key
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "your-deepseek-api-key-here":
        return {"error": "请先在 .env 文件中设置 DEEPSEEK_API_KEY"}

    # 加载索引
    index = get_index()
    if index is None:
        return {"error": "还没有索引任何文档，请先上传文档并处理"}

    try:
        # 步骤 1：检索相关片段（top-3）
        retriever = index.as_retriever(similarity_top_k=3)
        nodes = retriever.retrieve(question)

        if not nodes:
            return {"answer": "未找到相关文档内容。", "sources": []}

        # 步骤 2：拼接上下文
        context_parts = []
        for i, node in enumerate(nodes, 1):
            context_parts.append(f"[片段{i}] {node.get_content()}")

        context = "\n\n".join(context_parts)

        # 步骤 3：构建 prompt
        prompt = (
            "你是一个知识库助手，请严格根据以下文档内容回答问题。\n"
            "\n"
            "规则：\n"
            "1. 如果文档中有答案，用中文清晰回答，并在答案末尾标注「📎 来源：」加上片段编号\n"
            "2. 如果文档中只有部分相关信息，说明已知的部分，同时指出哪些问题文档未覆盖\n"
            "3. 如果文档中完全没有相关信息，回答「该文档中未找到相关信息」，不要编造\n"
            "\n"
            f"文档内容：\n{context}\n\n"
            f"用户问题：{question}\n\n"
            "回答："
        )

        # 步骤 4：调用 DeepSeek API
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1024,
        }

        resp = requests.post(
            DEEPSEEK_BASE_URL + "/chat/completions",
            json=payload,
            headers=headers,
            timeout=60,
        )
        data = resp.json()

        if "error" in data:
            return {"error": f"DeepSeek API 错误: {data['error']}"}

        answer = data["choices"][0]["message"]["content"]

        # 提取来源信息
        sources = []
        for node in nodes:
            sources.append({
                "text": node.get_content()[:300] + "...",
                "score": round(node.score or 0, 4),
            })

        return {
            "answer": answer,
            "sources": sources,
        }

    except Exception as e:
        return {"error": f"查询失败: {str(e)}"}
