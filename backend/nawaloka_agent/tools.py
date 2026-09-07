import asyncio

from agents import function_tool

from rag.embedding import create_embedding
from rag.prompt import build_context
from rag.reranker import rerank_chunks
from rag.retrieval import retrieve_chunks


def search_website_sync(query: str) -> str:
    query = query.strip()

    if not query:
        raise ValueError("Search query cannot be empty")

    print(f"[TOOL] search_website query: {query}")

    query_vector = create_embedding(query)
    retrieved = retrieve_chunks(query_vector)
    reranked = rerank_chunks(query, retrieved)

    print(f"[TOOL] Retrieved: {len(retrieved)} | Reranked: {len(reranked)}")

    if not reranked:
        return "No sufficiently relevant Nawaloka website content was found."

    return build_context(reranked)


@function_tool
async def search_website(query: str) -> str:
    """Search the indexed Nawaloka Hospitals website and return the most relevant reranked source passages.

    Args:
        query: A focused search query describing the Nawaloka information needed.
    """

    return await asyncio.to_thread(search_website_sync, query)
