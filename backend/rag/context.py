import re


def strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_best_content(source: dict) -> str:
    """Get the best available text from a document source."""
    # Try clean text fields first
    for field in ("content", "search_text", "source_text", "text", "markdown"):
        value = source.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()

    # Fallback: strip HTML from raw_content
    raw = source.get("raw_content")
    if isinstance(raw, str) and raw.strip():
        return strip_html(raw)

    return ""


def build_context(results: list[dict]) -> str:
    sources = []
    for index, result in enumerate(results, start=1):
        source = result.get("_source", {})
        content = get_best_content(source)

        if not content:
            continue

        page = source.get("page_name") or source.get("page") or source.get("page_slug") or ""
        chunk_id = source.get("chunk_id") or result.get("_id") or ""

        block = f"SOURCE {index}\nPage: {page}\nChunk: {chunk_id}\nContent:\n{content}"
        sources.append(block.strip())

    return "\n\n".join(sources)
