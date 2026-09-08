from core.clients import get_dashscope_client
from core.settings import settings


def create_embedding(query: str) -> list[float]:
    query = query.strip()
    if not query:
        raise ValueError("Query cannot be empty")

    response = get_dashscope_client().embeddings.create(
        model=settings.embedding_model,
        input=query,
        dimensions=settings.embedding_dimension,
        encoding_format="float",
    )
    if not response.data:
        raise RuntimeError("Embedding API returned no embedding")
    return response.data[0].embedding
