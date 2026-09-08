import os
from urllib.parse import urlparse

from opensearchpy import OpenSearch, RequestsHttpConnection


OPENSEARCH_INDEX = os.getenv("OPENSEARCH_INDEX", "nawaloka")
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "20"))


def get_opensearch_client() -> OpenSearch:
    url = os.getenv("OPENSEARCH_HOST")

    if not url:
        raise RuntimeError("OPENSEARCH_HOST is not set")

    parsed = urlparse(url)

    if not parsed.hostname:
        raise RuntimeError("Invalid OPENSEARCH_HOST")

    if not parsed.username or not parsed.password:
        raise RuntimeError("OPENSEARCH_HOST must contain Bonsai username and password")

    return OpenSearch(
        hosts=[{"host": parsed.hostname, "port": parsed.port or 443}],
        http_auth=(parsed.username, parsed.password),
        use_ssl=parsed.scheme == "https",
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30,
    )


def retrieve_chunks(query_vector: list[float], top_k: int = RETRIEVAL_TOP_K) -> list[dict]:
    client = get_opensearch_client()

    response = client.search(
        index=OPENSEARCH_INDEX,
        body={
            "size": top_k,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_vector,
                        "k": top_k,
                    }
                }
            },
        },
    )

    body = response.body if hasattr(response, "body") else response
    return body.get("hits", {}).get("hits", [])