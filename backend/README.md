# Backend

## Purpose

The backend handles the AI pipeline behind the Nawaloka chat assistant.

It receives a user question, decides which information source is required, retrieves the necessary evidence, and generates the final answer.

## Request flow

```text
User Question
     ↓
Query Router
     ↓
Website Search / SQL Search
     ↓
Retrieval and Reranking
     ↓
Evidence
     ↓
Answer Generation
```

## Main steps

1. The FastAPI endpoint receives the user question.

2. The router decides whether to use website retrieval, PostgreSQL, or both.

3. Website questions are rewritten into retrieval friendly subqueries when needed.

4. Each retrieval query is embedded using `text-embedding-v4`.

5. OpenSearch performs vector search and keyword search.

6. Results are combined using Reciprocal Rank Fusion.

7. Retrieved chunks are reranked using `qwen3-rerank`.

8. Database questions are converted into safe read only PostgreSQL queries.

9. Website and database evidence is combined.

10. The answer model generates the final response.

## Folder structure

```text
backend/
    api/         FastAPI endpoints
    core/        Configuration and service clients
    database/    PostgreSQL connection and query execution
    prompts/     LLM prompts
    rag/         Embedding, retrieval, reranking and context building
    scripts/     Utility scripts
    pipeline.py  Main AI pipeline
```

## Setup

### 1. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Environment variables

Copy the values required by `backend/.env.example`.

```env
AI_GATEWAY_API_KEY=
DASHSCOPE_API_KEY=
DASHSCOPE_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
DASHSCOPE_RERANK_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1/reranks
OPENSEARCH_HOST=
DATABASE_URL=
```

`DATABASE_URL` is the PostgreSQL connection string used for structured hospital data.

### 3. Run the API

```bash
uvicorn api.index:app --host 0.0.0.0 --port 8000
```

For Render deployment, use the platform provided `$PORT`.

```bash
uvicorn api.index:app --host 0.0.0.0 --port $PORT
```

## Configuration

Model names, embedding dimensions, retrieval limits, reranker settings, and OpenSearch index settings are stored in `config.yaml`.
