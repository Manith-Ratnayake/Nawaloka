import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env", override=False)

with (ROOT_DIR / "config.yaml").open("r", encoding="utf-8") as file:
    CONFIG = yaml.safe_load(file) or {}


def config_value(section: str, key: str, default=None):
    return CONFIG.get(section, {}).get(key, default)


@dataclass(frozen=True)
class Settings:
    cohere_api_key: str | None = os.getenv("COHERE")
    ai_gateway_api_key: str | None = os.getenv("AI_GATEWAY_API_KEY")
    ai_gateway_base_url: str = os.getenv("AI_GATEWAY_BASE_URL", "https://ai-gateway.vercel.sh/v1")
    dashscope_api_key: str | None = os.getenv("DASHSCOPE_API_KEY")
    dashscope_base_url: str = os.getenv("DASHSCOPE_BASE_URL", config_value("dashscope", "base_url", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"))
    dashscope_rerank_url: str = os.getenv("DASHSCOPE_RERANK_URL", config_value("dashscope", "rerank_url", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/reranks"))
    opensearch_host: str | None = os.getenv("OPENSEARCH_HOST")
    opensearch_index: str = os.getenv("OPENSEARCH_INDEX", config_value("opensearch", "index", "nawaloka"))
    embedding_model: str = os.getenv("EMBEDDING_MODEL", config_value("embedding", "model", "text-embedding-v4"))
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", config_value("embedding", "dimension", 1024)))
    retrieval_top_k: int = int(os.getenv("RETRIEVAL_TOP_K", config_value("retrieval", "top_k", 7)))
    rerank_model: str = os.getenv("RERANK_MODEL", config_value("reranker", "model", "qwen3-rerank"))
    rerank_top_n: int = int(os.getenv("RERANK_TOP_N", config_value("reranker", "top_n", 5)))
    query_agent_model: str = os.getenv("QUERY_AGENT_MODEL", config_value("query_agent", "model", "qwen3.7-flash"))
    query_agent_max_subqueries: int = int(os.getenv("QUERY_AGENT_MAX_SUBQUERIES", config_value("query_agent", "max_subqueries", 4)))
    sql_agent_model: str = os.getenv("SQL_AGENT_MODEL", config_value("sql_agent", "model", "qwen3.7-flash"))
    db_sql_host: str | None = os.getenv("DB_SQL_HOST")
    upstash_redis_url: str | None = os.getenv("UPSTASH_REDIS_URL")
    upstash_redis_token: str | None = os.getenv("UPSTASH_REDIS_TOKEN")
    faq_similarity_threshold: float = float(os.getenv("FAQ_SIMILARITY_THRESHOLD", config_value("faq_cache", "similarity_threshold", 0.88)))
    faq_key_prefix: str = os.getenv("FAQ_KEY_PREFIX", config_value("faq_cache", "key_prefix", "faq:"))
    faq_index_key: str = os.getenv("FAQ_INDEX_KEY", config_value("faq_cache", "index_key", "faq:index"))




settings = Settings()