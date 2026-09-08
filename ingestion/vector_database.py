import html
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from opensearchpy import OpenSearch, RequestsHttpConnection


load_dotenv()

ROOT_FOLDER = Path(__file__).resolve().parent.parent / "extraction_and_chunking" / "chunk_output"
INDEX_NAME = "nawaloka"

EMBEDDING_MODEL = "text-embedding-v4"
EMBEDDING_DIMENSION = 1024

OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL")

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url=DASHSCOPE_BASE_URL,
)


def read_chunks(file_path):
    text = Path(file_path).read_text(encoding="utf-8")
    pattern = r"=+\s*CHUNK\s+(\d+)\s*=+\s*(.*?)(?==+\s*CHUNK\s+\d+\s*=+|\Z)"
    return [(int(chunk_id), raw_content.strip()) for chunk_id, raw_content in re.findall(pattern, text, re.DOTALL)]


def clean_html(raw_content):
    soup = BeautifulSoup(raw_content, "html.parser")

    for image in soup.find_all("img"):
        alt_text = image.get("alt", "").strip()
        image.replace_with(alt_text)

    text = soup.get_text("\n")
    text = html.unescape(html.unescape(text))
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def embed_text(text):
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
        dimensions=EMBEDDING_DIMENSION,
        encoding_format="float",
    )

    return response.data[0].embedding


def create_opensearch_client():
    if not OPENSEARCH_HOST:
        raise ValueError("OPENSEARCH_HOST environment variable is not set.")

    parsed = urlparse(OPENSEARCH_HOST)

    if not parsed.hostname:
        raise ValueError("Invalid OPENSEARCH_HOST.")

    if not parsed.username or not parsed.password:
        raise ValueError("Bonsai OPENSEARCH_HOST must contain username and password.")

    return OpenSearch(
        hosts=[{"host": parsed.hostname, "port": parsed.port or 443}],
        http_auth=(unquote(parsed.username), unquote(parsed.password)),
        use_ssl=parsed.scheme == "https",
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30,
        pool_maxsize=20,
    )


def create_index(client):
    if client.indices.exists(index=INDEX_NAME):
        print(f"Index already exists: {INDEX_NAME}")
        return

    body = {
        "settings": {
            "index.knn": True
        },
        "mappings": {
            "properties": {
                "page_name": {
                    "type": "keyword"
                },
                "chunk_id": {
                    "type": "integer"
                },
                "content": {
                    "type": "text"
                },
                "raw_content": {
                    "type": "text",
                    "index": False
                },
                "embedding_content_1024": {
                    "type": "knn_vector",
                    "dimension": EMBEDDING_DIMENSION,
                    "space_type": "cosinesimil",
                    "method": {
                        "name": "hnsw"
                    }
                }
            }
        }
    }

    client.indices.create(index=INDEX_NAME, body=body)
    print(f"Created index: {INDEX_NAME}")


def index_chunk(client, page_name, chunk_id, raw_content):
    content = clean_html(raw_content)

    if not content:
        print(f"Skipped empty chunk: {page_name}/{chunk_id}")
        return

    document = {
        "page_name": page_name,
        "chunk_id": chunk_id,
        "content": content,
        "raw_content": raw_content,
        "embedding_content_1024": embed_text(content),
    }

    document_id = f"{page_name}_{chunk_id}"

    client.index(
        index=INDEX_NAME,
        id=document_id,
        body=document,
        refresh=False,
    )

    print(f"Indexed: {page_name}/{chunk_id}")


def ingest_page(client, chunks_file):
    page_name = chunks_file.parent.name
    chunks = read_chunks(chunks_file)

    print(f"\nPage: {page_name}")
    print(f"Chunks found: {len(chunks)}")

    for chunk_id, raw_content in chunks:
        index_chunk(client, page_name, chunk_id, raw_content)


def ingest_folder(root_folder):
    root = Path(root_folder)

    if not root.exists():
        raise FileNotFoundError(f"Folder not found: {root_folder}")

    chunk_files = sorted(root.rglob("chunks.txt"))

    if not chunk_files:
        raise FileNotFoundError(f"No chunks.txt files found inside: {root_folder}")

    client = create_opensearch_client()

    print("Connected to Bonsai OpenSearch.")
    create_index(client)

    for chunks_file in chunk_files:
        ingest_page(client, chunks_file)

   
    print(f"\nFinished indexing {len(chunk_files)} pages.")


if __name__ == "__main__":
    ingest_folder(ROOT_FOLDER)