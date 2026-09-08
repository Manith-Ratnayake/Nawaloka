import asyncio
import json
import re

from mem0 import MemoryClient

from core.clients import get_dashscope_async_client, get_gateway_async_client
from core.prompts import load_prompt
from core.settings import settings
from cache.redis import seed_faqs, check_faq_cache
from database.query import execute_select, validate_select_sql
from rag.context import build_context
from rag.embedding import create_embedding
from rag.reranker import rerank_chunks
from rag.retrieval import retrieve_chunks


# ── Seed FAQ cache on startup ─────────────────────────────────────────
seed_faqs(embedder=create_embedding)

# ── mem0 client ───────────────────────────────────────────────────────
mem0 = MemoryClient()   # reads MEM0_API_KEY from env automatically
MEM0_USER_ID = "nawaloka_global"  # single shared user — good enough for now

# ── Background task registry — prevents GC from killing fire-and-forget tasks ──
_background_tasks: set[asyncio.Task] = set()


# ── LLM helpers ──────────────────────────────────────────────────────

async def llm_call(client, model: str, system: str, user_message: str) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def parse_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


# ── Step 1: Router ───────────────────────────────────────────────────

async def route_query(message: str) -> tuple[dict, dict]:
    """Returns (plan, debug_info)"""
    client = get_dashscope_async_client()
    raw_output = await llm_call(client, settings.query_agent_model, load_prompt("router.txt"), message)

    debug = {"raw_output": raw_output}

    try:
        plan = parse_json(raw_output)
        result = {
            "use_vector": bool(plan.get("use_vector", False)),
            "use_sql": bool(plan.get("use_sql", False)),
            "vector_question": str(plan.get("vector_question") or message).strip(),
            "sql_question": str(plan.get("sql_question") or message).strip(),
        }
        debug["parsed"] = result
        debug["error"] = None
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        result = {
            "use_vector": True,
            "use_sql": False,
            "vector_question": message,
            "sql_question": message,
        }
        debug["parsed"] = result
        debug["error"] = f"JSON parse failed, used fallback: {e}"

    return result, debug


# ── Step 2: Query agent ──────────────────────────────────────────────

async def prepare_vector_queries(question: str) -> tuple[list[str], dict]:
    """Returns (subqueries, debug_info)"""
    client = get_dashscope_async_client()
    raw_output = await llm_call(client, settings.query_agent_model, load_prompt("query.txt"), question)

    debug = {"raw_output": raw_output}

    try:
        data = parse_json(raw_output)
        subqueries = [str(q).strip() for q in data.get("subqueries", []) if str(q).strip()]
        result = subqueries[: settings.query_agent_max_subqueries] or [question]
        debug["subqueries"] = result
        debug["error"] = None
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        result = [question]
        debug["subqueries"] = result
        debug["error"] = f"JSON parse failed, used fallback: {e}"

    return result, debug


# ── Step 3a: Vector search ───────────────────────────────────────────

def _chunk_preview(chunk: dict) -> dict:
    """Compact, UI-friendly view of a chunk (used at retrieval and rerank stages)."""
    source = chunk.get("_source", {})
    return {
        "id": chunk.get("_id"),
        "rerank_score": chunk.get("rerank_score"),  # None if not reranked yet
        "source": source.get("url") or source.get("page") or source.get("page_name") or "",
        "content_preview": (
            source.get("source_text")
            or source.get("content")
            or source.get("text")
            or ""
        )[:200],
    }


def _vector_search_sync(queries: list[str]) -> tuple[str, dict]:
    """Returns (context_string, debug_info)"""
    per_query_chunks: dict[str, list[dict]] = {}
    per_query_debug = []

    for query in queries:
        query_vector = create_embedding(query)
        chunks = retrieve_chunks(query, query_vector)
        per_query_chunks[query] = chunks

        per_query_debug.append({
            "query": query,
            "chunks_retrieved": len(chunks),
            "chunks": [_chunk_preview(c) for c in chunks],
        })

    total_unique_before_rerank = len({
        chunk["_id"] for chunks in per_query_chunks.values() for chunk in chunks
    })

    debug = {
        "total_unique_chunks_before_rerank": total_unique_before_rerank,
        "per_query": per_query_debug,
    }

    if total_unique_before_rerank == 0:
        debug["reranked_chunks"] = []
        debug["context_length"] = 0
        return "", debug

    per_subquery_top_n = max(2, -(-settings.rerank_top_n // len(queries)))  # ceil, floor of 2

    best_by_id: dict[str, dict] = {}
    per_query_rerank_debug = []

    for query, chunks in per_query_chunks.items():
        if not chunks:
            per_query_rerank_debug.append({"query": query, "reranked_count": 0, "chunks": []})
            continue

        reranked_for_query = chunks[:per_subquery_top_n]

        per_query_rerank_debug.append({
            "query": query,
            "reranked_count": len(reranked_for_query),
            "chunks": [_chunk_preview(c) for c in reranked_for_query],
        })

        for chunk in reranked_for_query:
            doc_id = chunk["_id"]
            existing = best_by_id.get(doc_id)
            if existing is None or (chunk.get("rerank_score") or 0) > (existing.get("rerank_score") or 0):
                best_by_id[doc_id] = chunk

    reranked = sorted(
        best_by_id.values(),
        key=lambda c: c.get("rerank_score") or 0,
        reverse=True,
    )

    debug["per_query_rerank"] = per_query_rerank_debug
    debug["reranked_chunks"] = [_chunk_preview(r) for r in reranked]

    context = build_context(reranked) if reranked else ""
    debug["context_length"] = len(context)
    debug["context_preview"] = context[:500] if context else ""

    return context, debug


async def vector_search(queries: list[str]) -> tuple[str, dict]:
    return await asyncio.to_thread(_vector_search_sync, queries)


# ── Step 3b: SQL search ──────────────────────────────────────────────

async def _generate_sql(question: str, error_context: str = "") -> str:
    client = get_dashscope_async_client()
    prompt = question
    if error_context:
        prompt = f"{question}\n\nYour previous SQL query failed with this error:\n{error_context}\nGenerate a corrected query."

    output = await llm_call(client, settings.sql_agent_model, load_prompt("sql_agent.txt"), prompt)
    return validate_select_sql(output)


async def sql_search(question: str) -> tuple[str, dict]:
    """Returns (result_string, debug_info)"""
    debug = {"attempts": []}

    # First attempt
    try:
        sql = await _generate_sql(question)
        rows = await asyncio.to_thread(execute_select, sql)
        attempt = {"sql": sql, "error": None, "row_count": len(rows)}
        debug["attempts"].append(attempt)

        if not rows:
            debug["result"] = "empty"
            return "No matching records found in the database.", debug

        result = json.dumps(rows, default=str, ensure_ascii=False)
        debug["result"] = "success"
        debug["rows_preview"] = rows[:3]
        return result, debug

    except Exception as first_error:
        first_error_message = str(first_error)
        debug["attempts"].append({"sql": None, "error": first_error_message})

    # Retry once
    try:
        sql = await _generate_sql(question, error_context=first_error_message)
        rows = await asyncio.to_thread(execute_select, sql)
        attempt = {"sql": sql, "error": None, "row_count": len(rows)}
        debug["attempts"].append(attempt)

        if not rows:
            debug["result"] = "empty"
            return "No matching records found in the database.", debug

        result = json.dumps(rows, default=str, ensure_ascii=False)
        debug["result"] = "success_on_retry"
        debug["rows_preview"] = rows[:3]
        return result, debug

    except Exception as second_error:
        debug["attempts"].append({"sql": None, "error": str(second_error)})
        debug["result"] = "failed"
        return "Could not retrieve database information for this query.", debug


# ── Step 4: Answer ───────────────────────────────────────────────────

def _format_history(history: list[dict]) -> str:
    """Format last 4 messages as readable conversation context."""
    if not history:
        return ""
    lines = []
    for m in history[-4:]:
        role = "User" if m["role"] == "user" else "Assistant"
        lines.append(f"{role}: {m['content']}")
    return "\n".join(lines)


async def generate_answer(
    message: str,
    model_id: str,
    vector_context: str,
    sql_context: str,
    history: list[dict],
    memory_context: str,
) -> str:
    client = get_dashscope_async_client()

    evidence_parts = []
    if vector_context:
        evidence_parts.append(f"Website content:\n{vector_context}")
    if sql_context:
        evidence_parts.append(f"Database results:\n{sql_context}")

    evidence = "\n\n".join(evidence_parts) if evidence_parts else "No information was found from either source."

    # Build user input — history first so the model has full context
    sections = []

    history_text = _format_history(history)
    if history_text:
        sections.append(f"Recent conversation:\n{history_text}")

    if memory_context:
        sections.append(f"What I know about this user:\n{memory_context}")

    sections.append(f"Current question:\n{message}")
    sections.append(f"Evidence:\n{evidence}")

    user_input = "\n\n".join(sections)

    return await llm_call(client, "qwen-plus", load_prompt("answer.txt"), user_input)


# ── mem0 helpers (sync, run in thread) ───────────────────────────────

def _mem0_search(query: str, user_id: str) -> str:
    """Returns a short string of relevant memories, or empty string."""
    try:
        raw = mem0.search(query=query, user_id=user_id, limit=4)
        # mem0 SDK v1 returns a list; v2 returns {"results": [...]}
        results = raw.get("results", []) if isinstance(raw, dict) else (raw or [])
        return "\n".join(r["memory"] for r in results if r.get("memory"))
    except Exception:
        return ""  # never crash the pipeline over memory


def _mem0_add(user_message: str, assistant_message: str, user_id: str) -> None:
    """Store the turn in mem0."""
    try:
        result = mem0.add(
            messages=[
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_message},
            ],
            user_id=user_id,
        )
        print(f"[mem0] add OK for user_id={user_id} | result={result}")
    except Exception as e:
        print(f"[mem0] add FAILED for user_id={user_id} | error={e}")


# ── Pipeline ─────────────────────────────────────────────────────────

async def run_pipeline_stream(
    message: str,
    model_id: str,
    session_id: str | None = None,
    history: list[dict] | None = None,
):
    """Async generator: yields status events then a final done event."""
    message = message.strip()
    model_id = model_id.strip()
    history = history or []

    if not message:
        raise ValueError("Message cannot be empty")
    if not model_id:
        raise ValueError("Model cannot be empty")

    user_id = session_id or MEM0_USER_ID
    debug_trace = {}

    # ── Cache check ───────────────────────────────────────────────────
    query_embedding = await asyncio.to_thread(create_embedding, message)
    cached_answer = check_faq_cache(query_embedding)
    if cached_answer:
        yield {
            "phase": "done",
            "answer": cached_answer,
            "debug": {"cache": "hit"},
        }
        return

    # ── mem0 search (parallel with routing — doesn't slow things down) ─
    memory_task = asyncio.create_task(
        asyncio.to_thread(_mem0_search, message, user_id)
    )

    # Step 1: Route
    yield {
        "phase": "router",
        "message": "Deciding where to look...",
        "modelId": settings.query_agent_model,
        "modelName": "Router",
    }
    plan, router_debug = await route_query(message)
    debug_trace["step1_router"] = {"plan": plan, "debug": router_debug}

    # Step 2: Optimize vector queries
    vector_queries = []
    query_agent_debug = None
    if plan["use_vector"]:
        yield {
            "phase": "vector",
            "message": "Optimizing search queries...",
            "modelId": settings.query_agent_model,
            "modelName": "Query agent",
        }
        vector_queries, query_agent_debug = await prepare_vector_queries(plan["vector_question"])
        debug_trace["step2_query_agent"] = {"queries": vector_queries, "debug": query_agent_debug}
    else:
        debug_trace["step2_query_agent"] = {"skipped": True, "reason": "router set use_vector=false"}

    # Step 3: Fetch from sources in parallel
    tasks = {}
    if plan["use_vector"]:
        yield {
            "phase": "vector",
            "message": "Searching the website index...",
            "modelId": settings.embedding_model,
            "modelName": "Vector search",
        }
        tasks["vector"] = vector_search(vector_queries)
    if plan["use_sql"]:
        yield {
            "phase": "sql",
            "message": "Querying the hospital database...",
            "modelId": settings.sql_agent_model,
            "modelName": "SQL agent",
        }
        tasks["sql"] = sql_search(plan["sql_question"])

    # Fallback
    if not tasks:
        yield {
            "phase": "vector",
            "message": "Searching the website index...",
            "modelId": settings.embedding_model,
            "modelName": "Vector search",
        }
        tasks["vector"] = vector_search([message])
        debug_trace["step3_fallback"] = True

    gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)

    vector_context = ""
    sql_context = ""
    step3_debug = {}

    for key, result in zip(tasks.keys(), gathered):
        if isinstance(result, Exception):
            step3_debug[key] = {"error": str(result)}
            if key == "vector":
                vector_context = ""
            else:
                sql_context = ""
        else:
            context_str, search_debug = result
            step3_debug[key] = search_debug
            if key == "vector":
                vector_context = context_str
            else:
                sql_context = context_str

    debug_trace["step3_search"] = step3_debug

    # Collect memory (should be done by now — it ran in parallel with steps 1–3)
    memory_context = await memory_task
    debug_trace["mem0"] = {"memory_context": memory_context or "(none)"}

    # Step 4: Generate answer
    yield {
        "phase": "answer",
        "message": "Generating the answer...",
        "modelId": "qwen-plus",
        "modelName": "Answer agent",
    }
    answer = await generate_answer(
        message=message,
        model_id=model_id,
        vector_context=vector_context,
        sql_context=sql_context,
        history=history,
        memory_context=memory_context,
    )
    debug_trace["step4_answer"] = {
        "vector_context_chars": len(vector_context),
        "sql_context_chars": len(sql_context),
        "answer_chars": len(answer),
    }

    # Await mem0 save — must complete before we're done, demo needs this working.
    await asyncio.to_thread(_mem0_add, message, answer, user_id)

    yield {
        "phase": "done",
        "answer": answer,
        "debug": debug_trace,
    }


async def run_pipeline(message: str, model_id: str) -> dict:
    """Backward-compatible wrapper: consumes the stream and returns the final result."""
    async for event in run_pipeline_stream(message, model_id):
        if event.get("phase") == "done":
            return {"answer": event["answer"], "debug": event["debug"]}
    raise RuntimeError("Pipeline stream ended without a final result")