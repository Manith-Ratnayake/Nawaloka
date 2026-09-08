import re

import cohere
from core.settings import settings


def strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_document_text(result: dict) -> str:
    source = result.get("_source", {})

    # Try clean text fields first, then fall back to raw_content (HTML stripped)
    for field in ("content", "search_text", "source_text", "text", "markdown"):
        value = source.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()

    # Fallback: strip HTML from raw_content
    raw = source.get("raw_content")
    if isinstance(raw, str) and raw.strip():
        return strip_html(raw)

    return ""


def rerank_chunks(query: str, search_results: list[dict], top_n: int | None = None) -> list[dict]:
    if not settings.cohere_api_key:
        print("[Reranker] COHERE_API_KEY not set, skipping rerank")
        return search_results

    candidates = []
    for result in search_results:
        text = get_document_text(result)
        if text:
            candidates.append({"result": result, "text": text})

    if not candidates:
        print("[Reranker] No candidates with text, returning empty")
        return []

    documents = [c["text"] for c in candidates]
    top_n = min(top_n or settings.rerank_top_n, len(documents))

    print(f"[Reranker] Sending {len(documents)} docs to reranker, top_n={top_n}")

    try:
        co = cohere.ClientV2(settings.cohere_api_key)
        response = co.rerank(
            model="rerank-v3.5",
            query=query.strip(),
            documents=documents,
            top_n=top_n,
        )

        reranked = []
        for item in response.results:
            result = dict(candidates[item.index]["result"])
            result["rerank_score"] = item.relevance_score
            reranked.append(result)

        print(f"[Reranker] Returned {len(reranked)} reranked chunks")
        return reranked

    except Exception as e:
        print(f"[Reranker] Exception: {e}, falling back to unranked results")
        return [c["result"] for c in candidates[:top_n]]