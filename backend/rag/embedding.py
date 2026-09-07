import os

from openai import OpenAI


EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
DASHSCOPE_BASE_URL = os.getenv(
    "DASHSCOPE_BASE_URL",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)


def create_embedding(query: str) -> list[float]:
    query = query.strip()

    if not query:
        raise ValueError("Query cannot be empty")

    api_key = os.getenv("DASHSCOPE_API_KEY")

    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is not set")

    client = OpenAI(api_key=api_key, base_url=DASHSCOPE_BASE_URL)

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query,
        dimensions=EMBEDDING_DIMENSION,
        encoding_format="float",
    )

    if not response.data:
        raise RuntimeError("Embedding API returned no embedding")

    return response.data[0].embedding
