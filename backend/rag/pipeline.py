from rag.embedding import create_embedding
from rag.generation import generate_answer
from rag.prompt import build_context, build_messages
from rag.reranker import rerank_chunks
from rag.retrieval import retrieve_chunks


def run_rag(query: str) -> str:
    query = query.strip()

    if not query:
        raise ValueError("Query cannot be empty")

    print(f"[RAG] Query: {query}")

    query_vector = create_embedding(query)
    print(f"[RAG] Embedding dimension: {len(query_vector)}")

    retrieved = retrieve_chunks(query_vector)
    print(f"[RAG] Retrieved chunks: {len(retrieved)}")

    reranked = rerank_chunks(query, retrieved)
    print(f"[RAG] Reranked chunks: {len(reranked)}")

    if not reranked:
        return "I could not find enough relevant information in the Nawaloka website content to answer that question."

    context = build_context(reranked)
    messages = build_messages(query, context)

    answer = generate_answer(messages)
    print("[RAG] Answer generated")

    return answer
