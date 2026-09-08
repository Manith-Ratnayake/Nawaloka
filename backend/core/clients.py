from functools import lru_cache
from urllib.parse import urlparse

from openai import AsyncOpenAI, OpenAI
from opensearchpy import OpenSearch, RequestsHttpConnection
from sqlalchemy import Engine, create_engine

from core.settings import settings


@lru_cache(maxsize=1)
def get_dashscope_client() -> OpenAI:
    if not settings.dashscope_api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is not set")
    return OpenAI(api_key=settings.dashscope_api_key, base_url=settings.dashscope_base_url)


@lru_cache(maxsize=1)
def get_dashscope_async_client() -> AsyncOpenAI:
    if not settings.dashscope_api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is not set")
    return AsyncOpenAI(api_key=settings.dashscope_api_key, base_url=settings.dashscope_base_url)


@lru_cache(maxsize=1)
def get_gateway_async_client() -> AsyncOpenAI:
    if not settings.ai_gateway_api_key:
        raise RuntimeError("AI_GATEWAY_API_KEY is not set")
    return AsyncOpenAI(api_key=settings.ai_gateway_api_key, base_url=settings.ai_gateway_base_url)


@lru_cache(maxsize=1)
def get_opensearch_client() -> OpenSearch:
    if not settings.opensearch_host:
        raise RuntimeError("OPENSEARCH_HOST is not set")

    parsed = urlparse(settings.opensearch_host)
    if not parsed.hostname:
        raise RuntimeError("Invalid OPENSEARCH_HOST")
    if not parsed.username or not parsed.password:
        raise RuntimeError("OPENSEARCH_HOST must include the OpenSearch username and password")

    return OpenSearch(
        hosts=[{"host": parsed.hostname, "port": parsed.port or 443}],
        http_auth=(parsed.username, parsed.password),
        use_ssl=parsed.scheme == "https",
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30,
    )


def sqlalchemy_url() -> str:
    if not settings.db_sql_host:
        raise RuntimeError("DB_SQL_HOST is not set")
    if settings.db_sql_host.startswith("postgresql://"):
        return settings.db_sql_host.replace("postgresql://", "postgresql+psycopg://", 1)
    return settings.db_sql_host


@lru_cache(maxsize=1)
def get_database_engine() -> Engine:
    return create_engine(sqlalchemy_url(), pool_pre_ping=True)