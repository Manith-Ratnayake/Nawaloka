# Nawaloka AI Assistant

## Overview

This project is an AI assistant for Nawaloka Hospitals. It answers questions using information from the Nawaloka website and structured hospital database records.

The system combines Retrieval Augmented Generation, hybrid search, reranking, SQL querying, and a chat interface.

## How the project works

1. Nawaloka website pages are collected using Firecrawl.

2. The extracted HTML is cleaned while preserving useful page content and structure.

3. The cleaned content is divided into meaningful chunks based on page sections. FAQ sections are split into individual question and answer chunks.

4. Each chunk is converted into a 1024 dimensional embedding using `text-embedding-v4`.

5. The chunks and embeddings are stored in OpenSearch.

6. A user sends a question through the Next.js chat interface.

7. The backend decides whether the question needs website information, structured database information, or both.

8. Website questions use query preparation, hybrid vector and keyword search, Reciprocal Rank Fusion, and reranking.

9. Structured hospital questions use a read only SQL generation flow against PostgreSQL.

10. Retrieved evidence is sent to the answer model to generate the final response.

## Project structure

```text
Nawaloka/
    backend/       API, query routing, RAG, SQL and answer generation
    extraction/    Website crawling and content extraction
    chunking/      Section and FAQ chunk creation
    ingestion/     Embedding generation and OpenSearch indexing
    frontend/      Next.js chat application
```

## Main technologies

| Area | Technology |
| --- | --- |
| Frontend | Next.js, React, TypeScript, Vercel AI SDK |
| Backend | Python, FastAPI |
| Website extraction | Firecrawl |
| Embeddings | Qwen text-embedding-v4 |
| Vector database | OpenSearch |
| Retrieval | Vector search, keyword search, Reciprocal Rank Fusion |
| Reranking | Qwen3 Rerank |
| Structured data | PostgreSQL |
| Deployment | Vercel and Render |

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Manith-Ratnayake/Nawaloka.git
cd Nawaloka
```

### 2. Create environment variables

Create a `.env` file and provide the services used by the project.

```env
FIRECRAWL_API_KEY=
DASHSCOPE_API_KEY=
DASHSCOPE_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
OPENSEARCH_HOST=
DATABASE_URL=
AI_GATEWAY_API_KEY=
BACKEND_URL=
AUTH_SECRET=
POSTGRES_URL=
```

Do not commit real API keys or database credentials.

### 3. Prepare the website knowledge base

Run the data preparation stages in this order.

```bash
cd extraction
pip install -r requirements.txt
python main.py

cd ../chunking
pip install -r requirements.txt
python main.py
```

After chunking, run the ingestion script to create embeddings and index the chunks in OpenSearch.

### 4. Run the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn api.index:app --host 0.0.0.0 --port 8000
```

### 5. Run the frontend

```bash
cd frontend
pnpm install
pnpm db:migrate
pnpm dev
```

The local frontend runs at `http://localhost:3000`.

## Data flow

```text
Nawaloka Website
      ↓
Extraction
      ↓
Chunking
      ↓
Embedding and OpenSearch Ingestion
      ↓
Hybrid Retrieval and Reranking
      ↓
Backend AI Pipeline
      ↓
Next.js Chat Interface
```
