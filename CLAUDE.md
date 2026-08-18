# 项目：知识库问答应用（RAG 练习项目）

这是给 Claude Code 看的项目说明。把 CLAUDE.md 放到工作目录，运行 `claude`，让它按本文件把项目做完。

## 项目背景

一个知识库问答应用：用户上传 PDF/文档，然后针对内容提问，AI 基于文档内容回答并标注出处。用来练习 RAG 的完整工程化流程。目标是部署上线，任何人都能使用。

## 功能需求（必须）

1. 网页上传一个或多个 PDF（支持 txt/md 更佳）
2. 后台自动处理：读取文本 → 切片 → 生成 embedding → 存入向量库
3. 用户提问 → 检索相关片段 → 大模型基于片段回答，并说明答案来自哪些文档/段落
4. 显示处理状态（正在处理 / 完成）
5. 同一个会话里可以连续追问

## 技术要求

- 后端：Python + FastAPI
- RAG 框架：LlamaIndex（API 设计对 RAG 最友好，上手快；LangChain 更灵活但概念多）
- 向量库：Chroma（本地文件即可，部署时也存文件）
- Embedding：HuggingFace sentence-transformers（`all-MiniLM-L6-v2`，80MB 小模型，离线运行，部署不需要额外 API）
- 回答模型：DeepSeek API（`deepseek-v4-pro`，API 格式兼容 OpenAI，LlamaIndex 原生支持；⚠️ 不要用 deepseek-chat，旧别名会被静默映射到弱模型）
- API Key：通过环境变量 `DEEPSEEK_API_KEY` 传入，部署时配在 Render/Railway 环境变量里
- 前端：简单网页即可，不追求花哨

## 技术选型理由

| 选择 | 理由 |
|------|------|
| DeepSeek 而非 Claude | 国内直接访问、中文更好、便宜 90%+ |
| HuggingFace embedding 而非 Ollama | 部署到云端时本地 Ollama 不可用；HuggingFace 模型跟随代码部署，无额外依赖 |
| LlamaIndex 而非 LangChain | LlamaIndex 的 RAG API 更简洁，一个 `VectorStoreIndex` 就搞定索引+检索，适合入门 |
| Chroma 而非 Pinecone/Weaviate | 文件型数据库，不需要注册外部服务，部署零配置 |

## 开发约定

- 每完成一个环节（上传 → 索引 → 问答），停下来让我运行验证
- 用 5–10 份真实文档测试，记录检索质量（答得准不准、出处对不对）
- 代码结构清晰：upload / index / query 分开
- 最后给出：本地运行方法 + 部署到 Render 或 Railway 的步骤

## 验收标准

- 上传文档后能提问，答案带出处
- 换几份没见过的文档，回答依然可用
- 部署后有一个公开访问的链接
- 代码已提交到 GitHub，README 说明项目用途和运行方式
