import re

import cohere
from core.settings import settings


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_document_text(result: dict) -> str:
    source = result.get("_source", {})

    for field in ("content", "search_text", "source_text", "text", "markdown"):
        value = source.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()

    raw = source.get("raw_content")
    if isinstance(raw, str) and raw.strip():
        return strip_html(raw)

    return ""


def rerank_chunks(query: str, search_results: list[dict], top_n: int | None = None) -> list[dict]:
    print(f"[Reranker] === ENTER rerank_chunks ===")
    print(f"[Reranker] query: {query[:100]}")
    print(f"[Reranker] search_results count: {len(search_results)}")
    print(f"[Reranker] cohere_api_key exists: {bool(settings.cohere_api_key)}")
    print(f"[Reranker] cohere_api_key first 10: {str(settings.cohere_api_key)[:10] if settings.cohere_api_key else 'NONE'}")

    if not settings.cohere_api_key:
        print("[Reranker] COHERE_API_KEY not set, skipping rerank")
        return search_results

    candidates = []
    for i, result in enumerate(search_results):
        text = get_document_text(result)
        if text:
            candidates.append({"result": result, "text": text})

    print(f"[Reranker] candidates with text: {len(candidates)}")

    if not candidates:
        print("[Reranker] No candidates with text, returning empty")
        return []

    documents = [c["text"] for c in candidates]
    top_n = min(top_n or settings.rerank_top_n, len(documents))

    print(f"[Reranker] Calling Cohere rerank-v3.5, {len(documents)} docs, top_n={top_n}")

    try:
        co = cohere.ClientV2(settings.cohere_api_key)
        print("[Reranker] Cohere client created OK")

        response = co.rerank(
            model="rerank-v3.5",
            query=query.strip(),
            documents=documents,
            top_n=top_n,
        )

        print(f"[Reranker] API returned {len(response.results)} results")

        reranked = []
        for item in response.results:
            print(f"[Reranker] idx={item.index} score={item.relevance_score}")
            result = dict(candidates[item.index]["result"])
            result["rerank_score"] = item.relevance_score
            reranked.append(result)

        print(f"[Reranker] SUCCESS — {len(reranked)} chunks")
        return reranked

    except Exception as e:
        print(f"[Reranker] EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return [c["result"] for c in candidates[:top_n]]