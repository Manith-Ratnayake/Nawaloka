"""Split semantic blocks into major page sections, then split FAQs."""

FAQ_WORDS = ("faq", "frequently asked question")
BOUNDARY_TAGS = {"h1", "h2"}


def _heading_text(blocks):
    for block in blocks:
        if block["tag"] in BOUNDARY_TAGS:
            return block.get("text", "")
    return ""


def _is_faq_heading(text):
    lowered = (text or "").lower()
    return any(word in lowered for word in FAQ_WORDS)



def _take_heading_labels(current, next_heading):
    """Detach only blocks that clearly look like labels for the next h1/h2."""
    if not current or _is_faq_heading(_heading_text(current)):
        return []

    trailing_spans = []
    index = len(current) - 1
    while index >= 0 and current[index]["tag"] == "span":
        trailing_spans.insert(0, current[index])
        index -= 1

    if trailing_spans:
        if len(trailing_spans) <= 2:
            del current[-len(trailing_spans):]
            return trailing_spans

        last = trailing_spans[-1]
        if _is_faq_heading(next_heading) and _is_faq_heading(last.get("text", "")):
            current.pop()
            return [last]

        return []

    return []


def _make_chunk(blocks, kind="content", question=""):
    return {
        "kind": kind,
        "heading": _heading_text(blocks),
        "question": question,
        "blocks": blocks,
        "html": "\n".join(block["html"] for block in blocks if block.get("html")).strip(),
    }


def _is_toggle_button(block):
    """An accordion toggle is a button with no destination; a CTA button carries an href."""
    return block["tag"] == "button" and 'href="' not in block.get("html", "")


def _faq_question_indexes(blocks):
    """FAQ questions are h3 headings; some pages use accordion toggle buttons instead."""
    h3_indexes = [index for index, block in enumerate(blocks) if block["tag"] == "h3"]
    if h3_indexes:
        return h3_indexes
    return [index for index, block in enumerate(blocks) if _is_toggle_button(block)]


def _split_faq_chunk(chunk):
    blocks = chunk["blocks"]
    question_indexes = _faq_question_indexes(blocks)
    if not question_indexes:
        return [chunk]

    prefix = blocks[:question_indexes[0]]
    faq_chunks = []

    for number, start in enumerate(question_indexes):
        end = question_indexes[number + 1] if number + 1 < len(question_indexes) else len(blocks)
        question_blocks = prefix + blocks[start:end]
        faq_chunks.append(_make_chunk(question_blocks, kind="faq", question=blocks[start].get("text", "")))

    return faq_chunks


def _has_content_beyond_heading(chunk):
    blocks = chunk["blocks"]
    return len(blocks) > 1 or not blocks or blocks[0]["tag"] not in BOUNDARY_TAGS


def extract_chunks(blocks):
    if not blocks:
        return []

    raw_chunks = []
    current = []
    seen_boundary = False

    for block in blocks:
        if block["tag"] not in BOUNDARY_TAGS:
            current.append(block)
            continue

        if not seen_boundary:
            current.append(block)
            seen_boundary = True
            continue

        labels = _take_heading_labels(current, block.get("text", ""))
        if current:
            raw_chunks.append(_make_chunk(current))

        current = labels + [block]

    if current:
        raw_chunks.append(_make_chunk(current))

    raw_chunks = [chunk for chunk in raw_chunks if chunk["html"] and _has_content_beyond_heading(chunk)]

    chunks = []
    for chunk in raw_chunks:
        if _is_faq_heading(chunk["heading"]):
            chunks.extend(_split_faq_chunk(chunk))
        else:
            chunks.append(chunk)

    return [chunk for chunk in chunks if chunk["html"]]
