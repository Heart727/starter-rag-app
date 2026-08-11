# 知识库问答（RAG 应用）

上传文档 → 智能问答，AI 基于文档内容回答并标注出处。

## 在线体验

> 🔗 [https://starter-rag-app-production.up.railway.app](https://starter-rag-app-production.up.railway.app)

## 功能

- 📤 上传 PDF / TXT / MD 文档
- 🔍 自动处理：读取 → 切片 → 向量化 → 存入数据库
- 💬 提问后 DeepSeek 基于文档回答，附来源标注
- 📊 显示处理状态（处理中 / 完成 / 错误）

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

## 部署

### Render（推荐）

1. 代码推送到 GitHub
2. 在 [render.com](https://render.com) 创建 Web Service
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. 环境变量添加 `DEEPSEEK_API_KEY`
6. 部署

> Render 免费套餐有 750 小时/月，够学习使用

## 学习记录

vibe coding 第 5–6 周 RAG 练习项目。踩坑记录：
- HuggingFace 在国内需配镜像 `HF_ENDPOINT=https://hf-mirror.com`
- DeepSeek API 兼容 OpenAI 格式，但需直接调 HTTP 绕过模型名校验
