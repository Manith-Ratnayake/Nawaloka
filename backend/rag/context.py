def build_context(results: list[dict]) -> str:
    sources = []
    for index, result in enumerate(results, start=1):
        source = result.get("_source", {})
        content = source.get("source_text") or source.get("search_text") or source.get("content") or source.get("text") or source.get("markdown") or ""
        url = source.get("url") or source.get("source_url") or ""
        page = source.get("page") or source.get("page_name") or source.get("page_slug") or ""
        section = source.get("section") or source.get("subsection") or ""
        chunk_id = source.get("chunk_id") or result.get("_id") or ""
        sources.append("\n".join([f"SOURCE {index}", f"Page: {page}", f"Section: {section}", f"URL: {url}", f"Chunk: {chunk_id}", "Content:", str(content).strip()]).strip())
    return "\n\n".join(sources)
