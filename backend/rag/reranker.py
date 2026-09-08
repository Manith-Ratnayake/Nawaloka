import re

import requests

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
    if not settings.dashscope_api_key:
        print("[Reranker] DASHSCOPE_API_KEY not set, skipping rerank")
        return search_results

    candidates = []
    for result in search_results:
        text = get_document_text(result)
        if text:
            candidates.append({"result": result, "text": text})

    if not candidates:
        print("[Reranker] No candidates with text, returning empty")
        return []

    documents = [candidate["text"] for candidate in candidates]
    top_n = min(top_n or settings.rerank_top_n, len(documents))

    print(f"[Reranker] Sending {len(documents)} docs to reranker, top_n={top_n}")

    try:
        response = requests.post(
            settings.dashscope_rerank_url,
            headers={"Authorization": f"Bearer {settings.dashscope_api_key}", "Content-Type": "application/json"},
            json={
                "model": settings.rerank_model,
                "query": query.strip(),
                "documents": documents,
                "top_n": top_n,
                "instruct": "Given a web search query, retrieve relevant passages that answer the query.",
            },
            timeout=30,
        )

        if not response.ok:
            print(f"[Reranker] API failed: {response.status_code} {response.text[:200]}")
            # Fallback: return candidates without reranking instead of failing
            return [c["result"] for c in candidates[:top_n]]

        reranked = []
        for item in response.json().get("results", []):
            index = item.get("index")
            if not isinstance(index, int) or not 0 <= index < len(candidates):
                continue
            result = dict(candidates[index]["result"])
            result["rerank_score"] = item.get("relevance_score")
            reranked.append(result)

        print(f"[Reranker] Returned {len(reranked)} reranked chunks")
        return reranked

    except Exception as e:
        print(f"[Reranker] Exception: {e}, falling back to unranked results")
        # Graceful fallback: return top candidates without reranking
        return [c["result"] for c in candidates[:top_n]]
