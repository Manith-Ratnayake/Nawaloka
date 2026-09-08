import asyncio
import json
import re

from core.clients import get_dashscope_async_client, get_gateway_async_client
from core.prompts import load_prompt
from core.settings import settings
from database.query import execute_select, validate_select_sql
from rag.context import build_context
from rag.embedding import create_embedding
from rag.reranker import rerank_chunks
from rag.retrieval import retrieve_chunks


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

def _vector_search_sync(queries: list[str]) -> tuple[str, dict]:
    """Returns (context_string, debug_info)"""
    all_chunks: dict[str, dict] = {}
    per_query_debug = []

    for query in queries:
        query_vector = create_embedding(query)
        chunks = retrieve_chunks(query, query_vector)

        per_query_debug.append({
            "query": query,
            "chunks_retrieved": len(chunks),
            "chunk_ids": [c.get("_id") for c in chunks],
        })

        for chunk in chunks:
            doc_id = chunk["_id"]
            if doc_id not in all_chunks:
                all_chunks[doc_id] = chunk

    debug = {
        "total_unique_chunks_before_rerank": len(all_chunks),
        "per_query": per_query_debug,
    }

    if not all_chunks:
        debug["reranked_chunks"] = []
        debug["context_length"] = 0
        return "", debug

    combined_query = " ".join(queries)
    reranked = rerank_chunks(combined_query, list(all_chunks.values()))

    debug["reranked_chunks"] = [
        {
            "id": r.get("_id"),
            "rerank_score": r.get("rerank_score"),
            "source": r.get("_source", {}).get("url") or r.get("_source", {}).get("page") or "",
            "content_preview": (
                r.get("_source", {}).get("source_text")
                or r.get("_source", {}).get("content")
                or r.get("_source", {}).get("text")
                or ""
            )[:200],
        }
        for r in reranked
    ]

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
        debug["attempts"].append({"sql": None, "error": str(first_error)})

    # Retry once
    try:
        sql = await _generate_sql(question, error_context=str(first_error))
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
    client = get_gateway_async_client()

    evidence_parts = []
    if vector_context:
        evidence_parts.append(f"Website content:\n{vector_context}")
    if sql_context:
        evidence_parts.append(f"Database results:\n{sql_context}")

    evidence = "\n\n".join(evidence_parts) if evidence_parts else "No information was found from either source."

    user_input = f"User question:\n{message}\n\nEvidence:\n{evidence}"
    return await llm_call(client, model_id, load_prompt("answer.txt"), user_input)


# ── Pipeline ─────────────────────────────────────────────────────────

async def run_pipeline(message: str, model_id: str) -> dict:
    """Returns full debug payload instead of just the answer string."""
    message = message.strip()
    model_id = model_id.strip()
    if not message:
        raise ValueError("Message cannot be empty")
    if not model_id:
        raise ValueError("Model cannot be empty")

    debug_trace = {}

    # Step 1: Route
    plan, router_debug = await route_query(message)
    debug_trace["step1_router"] = {"plan": plan, "debug": router_debug}

    # Step 2: Optimize vector queries
    vector_queries = []
    query_agent_debug = None
    if plan["use_vector"]:
        vector_queries, query_agent_debug = await prepare_vector_queries(plan["vector_question"])
        debug_trace["step2_query_agent"] = {"queries": vector_queries, "debug": query_agent_debug}
    else:
        debug_trace["step2_query_agent"] = {"skipped": True, "reason": "router set use_vector=false"}

    # Step 3: Fetch from sources in parallel
    tasks = {}
    if plan["use_vector"]:
        tasks["vector"] = vector_search(vector_queries)
    if plan["use_sql"]:
        tasks["sql"] = sql_search(plan["sql_question"])

    # Fallback
    if not tasks:
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
    answer = await generate_answer(message, model_id, vector_context, sql_context)
    debug_trace["step4_answer"] = {
        "vector_context_chars": len(vector_context),
        "sql_context_chars": len(sql_context),
        "answer_chars": len(answer),
    }

    return {
        "answer": answer,
        "debug": debug_trace,
    }
