import asyncio
import json
import re

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

    # Rerank each subquery's chunks against ITS OWN query text, not a
    # pooled set scored against every subquery's terms mashed together.
    # Otherwise one subquery's language can dilute relevance scoring for
    # chunks that only answer a different subquery, and that subquery's
    # best chunks get pushed out of the final top-N entirely.
    per_subquery_top_n = max(2, -(-settings.rerank_top_n // len(queries)))  # ceil, floor of 2

    best_by_id: dict[str, dict] = {}
    per_query_rerank_debug = []

    for query, chunks in per_query_chunks.items():
        if not chunks:
            per_query_rerank_debug.append({"query": query, "reranked_count": 0, "chunks": []})
            continue

        reranked_for_query = rerank_chunks(query, chunks, top_n=per_subquery_top_n)

        per_query_rerank_debug.append({
            "query": query,
            "reranked_count": len(reranked_for_query),
            "chunks": [_chunk_preview(c) for c in reranked_for_query],
        })

        for chunk in reranked_for_query:
            doc_id = chunk["_id"]
            existing = best_by_id.get(doc_id)
            # A chunk can win for more than one subquery — keep its best score.
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

async def generate_answer(message: str, model_id: str, vector_context: str, sql_context: str) -> str:
    client = get_dashscope_async_client()  # was get_gateway_async_client()

    evidence_parts = []
    if vector_context:
        evidence_parts.append(f"Website content:\n{vector_context}")
    if sql_context:
        evidence_parts.append(f"Database results:\n{sql_context}")

    evidence = "\n\n".join(evidence_parts) if evidence_parts else "No information was found from either source."

    user_input = f"User question:\n{message}\n\nEvidence:\n{evidence}"
    return await llm_call(client, "qwen-plus", load_prompt("answer.txt"), user_input)


# ── Pipeline ─────────────────────────────────────────────────────────

async def run_pipeline_stream(message: str, model_id: str):
    """Async generator: yields a status dict before each phase runs, then a
    final {"phase": "done", "answer": ..., "debug": ...} event.

    Callers that just want the final result can consume this to completion
    and take the last "done" event (see run_pipeline below).
    """
    message = message.strip()
    model_id = model_id.strip()
    if not message:
        raise ValueError("Message cannot be empty")
    if not model_id:
        raise ValueError("Model cannot be empty")

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
    # ── End cache check ───────────────────────────────────────────────

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

    # Step 4: Generate answer
    yield {
        "phase": "answer",
        "message": "Generating the answer...",
        "modelId": "qwen-plus",
        "modelName": "Answer agent",
    }
    answer = await generate_answer(message, model_id, vector_context, sql_context)
    debug_trace["step4_answer"] = {
        "vector_context_chars": len(vector_context),
        "sql_context_chars": len(sql_context),
        "answer_chars": len(answer),
    }

    yield {
        "phase": "done",
        "answer": answer,
        "debug": debug_trace,
    }


async def run_pipeline(message: str, model_id: str) -> dict:
    """Backward-compatible wrapper (used by scripts/tests): consumes the
    stream and returns just the final result."""
    async for event in run_pipeline_stream(message, model_id):
        if event.get("phase") == "done":
            return {"answer": event["answer"], "debug": event["debug"]}
    raise RuntimeError("Pipeline stream ended without a final result")