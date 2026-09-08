# Nawaloka AI backend

## Request flow

UI -> FastAPI `/chat` -> query preparation agent -> main agent -> website/database tools -> final answer.

The UI-selected model is used by the main answering agent through Vercel AI Gateway. Query preparation and SQL generation use the fixed DashScope models configured in `config.yaml`.

## Required deployment environment variables

`AI_GATEWAY_API_KEY`

`DASHSCOPE_API_KEY`

`OPENSEARCH_HOST`

`DATABASE_URL`

`DATABASE_URL` should be the Neon PostgreSQL connection string. The application converts a normal `postgresql://` URL to SQLAlchemy's psycopg driver internally.

## Run on Render

Use this start command from the backend directory:

```text
uvicorn api.index:app --host 0.0.0.0 --port $PORT
```

## Chat request

POST `/chat` with JSON containing `message`, `model`, and optionally `session_id`.

```json
{
  "message": "How much is the dengue test?",
  "model": "your-selected-vercel-ai-gateway-model-id",
  "session_id": "optional-session-id"
}
```

There is no CLI test runner in this project. `scripts/seed_database.py` exists only for intentionally seeding a database and is never imported by the application runtime.
