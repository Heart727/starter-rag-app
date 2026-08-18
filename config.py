"""
全局配置：从 .env 读取环境变量，导出给其他模块使用。

重要：HF_ENDPOINT 必须在导入 HuggingFace 相关库之前设置，
     所以本文件要在所有其他项目模块之前导入。
"""
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# HuggingFace 镜像（本地开发时用，部署时不需要）
_hf_endpoint = os.getenv("HF_ENDPOINT")
if _hf_endpoint:
    os.environ["HF_ENDPOINT"] = _hf_endpoint

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
# 兼容旧配置：deepseek-chat 是已过时的别名。DeepSeek 对旧别名不会报错，
# 而是静默映射到弱模型 deepseek-v4-flash，导致线上悄悄降级。
# 这里主动纠正，无论 .env / 部署平台环境变量写的是哪个旧值，最终都用 v4-pro。
if DEEPSEEK_MODEL == "deepseek-chat":
    DEEPSEEK_MODEL = "deepseek-v4-pro"

# HuggingFace Embedding 模型
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# 文件目录
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")

# 确保目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)
