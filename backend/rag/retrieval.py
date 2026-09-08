from core.clients import get_opensearch_client
from core.settings import settings


def retrieve_chunks(query: str, query_vector: list[float], top_k: int | None = None) -> list[dict]:
    top_k = top_k or settings.retrieval_top_k
    candidate_k = top_k * 2
    client = get_opensearch_client()

    print(f"[Retrieval] Starting hybrid search | top_k={top_k}")

    # Exclude the embedding vector from results — saves bandwidth
    source_fields = ["content", "raw_content", "page_name", "chunk_id"]

    vector_response = client.search(
        index=settings.opensearch_index,
        body={
            "size": candidate_k,
            "_source": source_fields,
            "query": {
                "knn": {
                    "embedding_content_1024": {
                        "vector": query_vector,
                        "k": candidate_k,
                    }
                }
            },
        },
    )

    keyword_response = client.search(
        index=settings.opensearch_index,
        body={
            "size": candidate_k,
            "_source": source_fields,
            "query": {
                "match": {
                    "content": {
                        "query": query,
                    }
                }
            },
        },
    )

    vector_body = vector_response.body if hasattr(vector_response, "body") else vector_response
    keyword_body = keyword_response.body if hasattr(keyword_response, "body") else keyword_response

    vector_hits = vector_body.get("hits", {}).get("hits", [])
    keyword_hits = keyword_body.get("hits", {}).get("hits", [])

    print(f"[Retrieval] Vector hits={len(vector_hits)} | Keyword hits={len(keyword_hits)}")

    results = reciprocal_rank_fusion(vector_hits, keyword_hits, top_k)

    print(f"[Retrieval] After RRF merge: {len(results)} chunks")

    return results


def reciprocal_rank_fusion(
    vector_hits: list[dict],
    keyword_hits: list[dict],
    top_k: int,
    k: int = 60,
) -> list[dict]:
    scores = {}
    documents = {}

    for rank, hit in enumerate(vector_hits, start=1):
        doc_id = hit["_id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
        documents[doc_id] = hit

    for rank, hit in enumerate(keyword_hits, start=1):
        doc_id = hit["_id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
        documents[doc_id] = hit

    ranked_ids = sorted(scores, key=scores.get, reverse=True)[:top_k]

    results = []
    for doc_id in ranked_ids:
        hit = documents[doc_id].copy()
        hit["_score"] = scores[doc_id]
        results.append(hit)

    return results
