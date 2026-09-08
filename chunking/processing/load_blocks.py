import re

from lxml import html

from text import node_text


VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
TAG_PATTERN = re.compile(r"<\s*(/?)\s*([a-zA-Z0-9]+)\b[^>]*>")


def _split_top_level_html(source):
    parts = []
    position = 0

    while position < len(source):
        while position < len(source) and source[position].isspace():
            position += 1

        if position >= len(source):
            break

        first = TAG_PATTERN.match(source, position)
        if not first or first.group(1):
            raise ValueError(f"Invalid extracted HTML near character {position}.")

        start = position
        tag = first.group(2).lower()
        first_token = first.group(0)

        if tag in VOID_TAGS or first_token.rstrip().endswith("/>"):
            position = first.end()
            parts.append(source[start:position])
            continue

        depth = 0
        for token in TAG_PATTERN.finditer(source, position):
            closing = bool(token.group(1))
            token_tag = token.group(2).lower()
            token_text = token.group(0)

            if closing:
                depth -= 1
            elif token_tag not in VOID_TAGS and not token_text.rstrip().endswith("/>"):
                depth += 1

            if depth == 0:
                position = token.end()
                parts.append(source[start:position])
                break
        else:
            raise ValueError("Unclosed top-level element in extracted HTML.")

    return parts


def load_blocks(extracted_html):
    blocks = []

    for raw_html in _split_top_level_html(extracted_html):
        node = html.fragment_fromstring(raw_html)
        blocks.append({"tag": node.tag.lower(), "text": node_text(node), "html": raw_html})

    return blocks
