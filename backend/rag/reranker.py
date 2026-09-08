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

    for field in ("content", "search_text", "source_text", "text", "markdown"):
        value = source.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()

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

    documents = [{"content": c["text"]} for c in candidates]
    top_n = min(top_n or settings.rerank_top_n, len(documents))

    print(f"[Reranker] Sending {len(documents)} docs to DashScope reranker, top_n={top_n}")

    try:
        response = requests.post(
            settings.dashscope_rerank_url,
            headers={
                "Authorization": f"Bearer {settings.dashscope_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.rerank_model,
                "input": {
                    "query": query.strip(),
                    "documents": documents,
                },
                "parameters": {
                    "top_n": top_n,
                    "return_documents": False,
                },
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        results_list = data.get("output", {}).get("results", [])

        reranked = []
        for item in results_list:
            idx = item["index"]
            result = dict(candidates[idx]["result"])
            result["rerank_score"] = item["relevance_score"]
            reranked.append(result)

        print(f"[Reranker] Returned {len(reranked)} reranked chunks")
        return reranked

    except Exception as e:
        print(f"[Reranker] Exception: {e}, falling back to unranked results")
        return [c["result"] for c in candidates[:top_n]]