import os

import requests


RERANK_MODEL = os.getenv("RERANK_MODEL", "qwen3-rerank")
RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "5"))
RERANK_URL = os.getenv(
    "DASHSCOPE_RERANK_URL",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/reranks",
)


def get_document_text(result: dict) -> str:
    source = result.get("_source", {})

    for field in ("search_text", "source_text", "content", "text", "markdown"):
        value = source.get(field)

        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def rerank_chunks(query: str, search_results: list[dict], top_n: int = RERANK_TOP_N) -> list[dict]:
    api_key = os.getenv("DASHSCOPE_API_KEY")

    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is not set")

    candidates = [
        {"result": result, "text": get_document_text(result)}
        for result in search_results
        if get_document_text(result)
    ]

    if not candidates:
        return []

    documents = [candidate["text"] for candidate in candidates]
    top_n = min(top_n, len(documents))

    response = requests.post(
        RERANK_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": RERANK_MODEL,
            "query": query.strip(),
            "documents": documents,
            "top_n": top_n,
            "instruct": "Given a web search query, retrieve relevant passages that answer the query.",
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(f"Reranker failed: {response.status_code} {response.text}")

    data = response.json()
    reranked = []

    for item in data.get("results", []):
        index = item.get("index")

        if not isinstance(index, int) or not 0 <= index < len(candidates):
            continue

        result = dict(candidates[index]["result"])
        result["rerank_score"] = item.get("relevance_score")
        reranked.append(result)

    return reranked
