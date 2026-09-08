import requests

from core.settings import settings


def get_document_text(result: dict) -> str:
    source = result.get("_source", {})
    for field in ("search_text", "source_text", "content", "text", "markdown"):
        value = source.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def rerank_chunks(query: str, search_results: list[dict], top_n: int | None = None) -> list[dict]:
    if not settings.dashscope_api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is not set")

    candidates = []
    for result in search_results:
        text = get_document_text(result)
        if text:
            candidates.append({"result": result, "text": text})

    if not candidates:
        return []

    documents = [candidate["text"] for candidate in candidates]
    top_n = min(top_n or settings.rerank_top_n, len(documents))
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
        raise RuntimeError(f"Reranker failed: {response.status_code} {response.text}")

    reranked = []
    for item in response.json().get("results", []):
        index = item.get("index")
        if not isinstance(index, int) or not 0 <= index < len(candidates):
            continue
        result = dict(candidates[index]["result"])
        result["rerank_score"] = item.get("relevance_score")
        reranked.append(result)
    return reranked
