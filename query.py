"""
问答模块：检索相关文档片段 → 拼接 prompt → DeepSeek 生成答案（带出处）
"""

import requests
from typing import Any

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from indexer import get_index

MAX_HISTORY_MESSAGES = 10
MAX_HISTORY_CHARS = 4000


def build_chat_messages(question: str, history: list[dict[str, Any]], context: str) -> list[dict[str, str]]:
    """Build a bounded, role-safe conversation prompt for a follow-up question."""
    system_prompt = (
        "你是一个知识库助手，请严格根据本次检索到的文档内容回答问题。\n"
        "规则：\n"
        "1. 用中文清晰回答，并在答案末尾标注「📎 来源：」和片段编号。\n"
        "2. 如果文档只覆盖部分问题，说明已知信息及未覆盖部分。\n"
        "3. 如果文档没有相关信息，回答「该文档中未找到相关信息」，不要编造。\n"
        "4. 历史对话仅用于理解上下文；文档内容是事实依据。\n\n"
        f"本次检索到的文档内容：\n{context}"
    )

    safe_history = []
    for message in history if isinstance(history, list) else []:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        content = message.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue
        content = content.strip()
        if content:
            safe_history.append({"role": role, "content": content[:MAX_HISTORY_CHARS]})

    return [
        {"role": "system", "content": system_prompt},
        *safe_history[-MAX_HISTORY_MESSAGES:],
        {"role": "user", "content": question},
    ]


def query_documents(question: str, history: list[dict[str, Any]] | None = None) -> dict:
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

        # 步骤 3：带上最近的多轮对话，让“继续解释”等追问有上下文
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": build_chat_messages(question, history or [], context),
            "temperature": 0.3,
            "max_tokens": 1024,
        }

        resp = requests.post(
            DEEPSEEK_BASE_URL + "/chat/completions",
            json=payload,
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()
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

    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as e:
        return {"error": f"查询失败: {str(e)}"}
