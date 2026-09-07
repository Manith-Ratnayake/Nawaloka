import os

import boto3
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection


OPENSEARCH_INDEX = os.getenv("OPENSEARCH_INDEX", "nawaloka")
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "20"))


def get_opensearch_client() -> OpenSearch:
    host = os.getenv("OPENSEARCH_HOST")

    if not host:
        raise RuntimeError("OPENSEARCH_HOST is not set")

    host = host.removeprefix("https://").removeprefix("http://").rstrip("/")
    region = os.getenv("AWS_REGION", "ap-south-1")

    session = boto3.Session()
    credentials = session.get_credentials()

    if credentials is None:
        raise RuntimeError("AWS credentials could not be loaded")

    auth = AWSV4SignerAuth(credentials, region, "aoss")

    return OpenSearch(
        hosts=[{"host": host, "port": 443}],
        http_auth=auth,
        use_ssl=True,
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
