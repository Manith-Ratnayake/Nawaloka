def build_context(results: list[dict]) -> str:
    sources = []

    for index, result in enumerate(results, start=1):
        source = result.get("_source", {})
        content = (
            source.get("source_text")
            or source.get("search_text")
            or source.get("content")
            or source.get("text")
            or source.get("markdown")
            or ""
        )

        url = source.get("url") or source.get("source_url") or ""
        page = source.get("page") or source.get("page_name") or source.get("page_slug") or ""
        section = source.get("section") or source.get("subsection") or ""
        chunk_id = source.get("chunk_id") or result.get("_id") or ""

        sources.append(
            "\n".join(
                [
                    f"SOURCE {index}",
                    f"Page: {page}",
                    f"Section: {section}",
                    f"URL: {url}",
                    f"Chunk: {chunk_id}",
                    "Content:",
                    str(content).strip(),
                ]
            ).strip()
        )

    return "\n\n".join(sources)


def build_messages(question: str, context: str) -> list[dict]:
    system_prompt = """You are the Nawaloka Hospitals website assistant.

Answer using only the retrieved Nawaloka website context supplied to you.

Rules:
1. Do not invent facts or use unsupported outside knowledge.
2. Answer the user's question directly and naturally.
3. When useful, cite the supporting retrieved source as [Source 1], [Source 2], and so on.
4. If the retrieved context is insufficient, clearly say that you could not find enough information in the retrieved Nawaloka website content.
5. Do not mention the retrieval pipeline, embeddings, vector database, reranker, or internal implementation."""

    user_prompt = f"""QUESTION

{question}

RETRIEVED CONTEXT

{context}

ANSWER"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
