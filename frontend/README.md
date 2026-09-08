# Frontend

## Purpose

The frontend provides the chat interface for the Nawaloka AI assistant.

It is built with Next.js and sends user questions to the Python backend while handling the chat experience, authentication, model selection, and conversation persistence.

## Main flow

1. The user enters a question in the chat interface.

2. The selected model and user message are handled by the Next.js chat API.

3. The frontend sends the question to the Python backend using `BACKEND_URL`.

4. The backend performs the AI retrieval or SQL pipeline.

5. The response is streamed or returned to the chat interface.

6. Chat history and user data are stored in PostgreSQL.

## Main technologies

```text
Next.js
React
TypeScript
Vercel AI SDK
Drizzle ORM
PostgreSQL
Auth.js
Tailwind CSS
```

## Setup

### 1. Install dependencies

```bash
cd frontend
pnpm install
```

### 2. Environment variables

Create `frontend/.env.local`.

```env
AUTH_SECRET=
POSTGRES_URL=
BACKEND_URL=http://localhost:8000
AI_GATEWAY_API_KEY=
REDIS_URL=
BLOB_READ_WRITE_TOKEN=
```

`POSTGRES_URL` is used for frontend chat and user persistence.

`BACKEND_URL` points to the Python backend.

### 3. Run database migrations

```bash
pnpm db:migrate
```

### 4. Start the frontend

```bash
pnpm dev
```

The application runs locally at:

```text
http://localhost:3000
```

## Production

The frontend is designed to run on Vercel. Set the same required environment variables in the Vercel project settings before deployment.
