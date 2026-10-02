# 知识库问答（RAG 应用）

上传文档 → 智能问答，AI 基于文档内容回答并标注出处。

当前没有可用的公网演示站点，可按下方步骤本地运行。

## 功能

- 📤 上传 PDF / TXT / MD 文档
- 🔍 自动处理：读取 → 切片 → 向量化 → 存入数据库
- 💬 提问后 DeepSeek 基于文档回答，附来源标注
- ↪️ 连续追问会参考当前页面最近 10 条对话
- 🧭 启动后自动检查示例知识库状态，索引可用时无需先上传即可提问
- 📊 显示处理状态（处理中 / 完成 / 错误）

> **演示数据说明：**上传资料会进入当前服务共用的知识库，所有访问此实例的访客都可能检索到。请勿上传个人信息、客户资料或其他敏感文档。单次最多上传 5 个文件，单个不超过 10 MB，总计不超过 20 MB。对话上下文仅保留在当前页面内，不会保存成历史会话。

## 技术架构

```
用户浏览器 → FastAPI → LlamaIndex
                        ├── HuggingFace Embedding（文本转向量，本地运行）
                        ├── Chroma（向量数据库，文件存储）
                        └── DeepSeek API（生成答案）
```

## 本地运行

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境（Windows）
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 API Key

编辑 `.env` 文件，填入 DeepSeek API Key：

```
DEEPSEEK_API_KEY=sk-你的key
```

> 从 [platform.deepseek.com](https://platform.deepseek.com) 获取

默认使用 `deepseek-v4-pro`，API 地址默认为 `https://api.deepseek.com/v1`。如需覆盖模型或地址，可在 `.env` 添加 `DEEPSEEK_MODEL` 或 `DEEPSEEK_BASE_URL`。不要把 `.env` 或 API Key 提交到 GitHub。

### 3. 启动

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

浏览器打开 **http://localhost:8000/**

## 项目结构

```
starter-rag-app/
├── main.py          # FastAPI 入口（路由）
├── config.py        # 环境变量 + 全局配置
├── indexer.py       # 文档处理（切片、embedding、向量库）
├── query.py         # 问答（检索 + DeepSeek 生成）
├── static/          # 前端页面
│   ├── index.html
│   ├── style.css
│   └── app.js
├── data/
│   ├── uploads/     # 上传的文档
│   └── chroma_db/   # 向量数据库文件
├── .env             # API Key（不提交到 Git）
└── requirements.txt
```

## 快速验证

1. 启动服务并打开 `http://localhost:8000/`，示例知识库可用时，输入框会自动启用。
2. 对示例资料提问，再追问“刚才提到的时间是什么？”；第二次回答会收到当前页面最近的对话上下文。
3. 选择一个小型 TXT 文件上传，点击“建立索引”，再确认可以检索新资料。
4. 上传超过限制的文件或不支持的格式，应看到中文错误提示，服务器不会保存超限文件。

部署到公开平台前，请配置 `DEEPSEEK_API_KEY`、持久化 `data/` 目录，并提醒访客上传内容会进入共享知识库。当前仓库没有可用的线上演示地址。

## 学习记录

RAG 练习项目。Embedding 模型首次启动时会下载；网络受限时，可在 `.env` 配置 HuggingFace 镜像 `HF_ENDPOINT=https://hf-mirror.com`。
