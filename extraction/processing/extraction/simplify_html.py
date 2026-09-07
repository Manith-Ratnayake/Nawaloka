"""Flatten cleaned webpage HTML into a small semantic HTML vocabulary."""

import html as html_lib
import re
from urllib.parse import urljoin

from text import normalize_text, node_text


SKIP_TAGS = {"script", "style", "noscript", "svg", "path", "template"}
TEXT_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "figcaption", "pre", "dt", "dd", "label", "option"}
ICON_WORDS = {"icon", "arrow", "chevron", "spinner", "avatar", "social"}
# Floating chat / messaging widgets that leak in as content images.
WIDGET_WORDS = ("chat-bot", "chatbot", "whatsapp", "livechat", "live-chat", "messenger")


def _escape(value):
    return html_lib.escape(value or "", quote=True)


def _absolute_url(value, base_url):
    value = normalize_text(value)
    if not value or value.startswith(("javascript:", "mailto:", "tel:", "#")):
        return value
    return urljoin(base_url or "", value)


def _onclick_url(onclick):
    if not onclick:
        return ""

    patterns = [
        r"(?:window\.)?location\.href\s*=\s*['\"]([^'\"]+)['\"]",
        r"(?:window\.)?location\s*=\s*['\"]([^'\"]+)['\"]",
        r"window\.open\s*\(\s*['\"]([^'\"]+)['\"]",
        r"(?:window\.)?location\.(?:assign|replace)\s*\(\s*['\"]([^'\"]+)['\"]",
        r"(?:router|navigate)\.(?:push|replace)\s*\(\s*['\"]([^'\"]+)['\"]",
    ]
    for pattern in patterns:
        match = re.search(pattern, onclick, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


DATA_URL_ATTRS = (
    "data-href", "data-url", "data-link", "data-file", "data-src",
    "data-pdf", "data-document", "data-doc", "data-download", "data-report",
)


def _direct_action_url(node):
    direct = node.get("href") or node.get("formaction")
    if direct:
        return direct
    for attr in DATA_URL_ATTRS:
        value = node.get(attr)
        if value:
            return value
    return _onclick_url(node.get("onclick"))


def _action_url(node, base_url):
    value = _direct_action_url(node)
    if value:
        return _absolute_url(value, base_url)

    for descendant in node.xpath(".//a[@href]"):
        return _absolute_url(descendant.get("href"), base_url)

    parent = node.getparent()
    for _ in range(3):
        if parent is None:
            break
        value = _direct_action_url(parent)
        if value:
            return _absolute_url(value, base_url)
        parent = parent.getparent()

    return ""


def _is_button_link(node):
    if node.tag.lower() != "a":
        return False
    classes = (node.get("class") or "").lower()
    return node.get("role") == "button" or "button" in classes or "btn" in classes


def _inline_html(node, base_url):
    parts = []

    def add_text(value):
        value = normalize_text(value)
        if value:
            parts.append(_escape(value))

    def walk(element):
        add_text(element.text)
        for child in element:
            if not isinstance(child.tag, str):
                add_text(child.tail)
                continue

            tag = child.tag.lower()
            text = node_text(child)

            if tag == "br":
                parts.append("<br>")
            elif tag == "a" and text:
                href = _action_url(child, base_url)
                attr = f' href="{_escape(href)}"' if href else ""
                parts.append(f"<a{attr}>{_escape(text)}</a>")
            elif tag == "button" and text:
                href = _action_url(child, base_url)
                attr = f' href="{_escape(href)}"' if href else ""
                parts.append(f"<button{attr}>{_escape(text)}</button>")
            else:
                walk(child)

            add_text(child.tail)

    walk(node)
    return " ".join(parts).replace(" <br> ", "<br>").strip()


def _simple_text_block(node, tag):
    text = node_text(node)
    if not text:
        return None
    return {"tag": tag, "text": text, "html": f"<{tag}>{_escape(text)}</{tag}>"}


def _paragraph_block(node, base_url):
    text = node_text(node)
    if not text:
        return None
    inner = _inline_html(node, base_url)
    return {"tag": "p", "text": text, "html": f"<p>{inner}</p>"}


def _link_block(node, base_url, as_button=False):
    text = node_text(node)
    if not text:
        return None

    href = _action_url(node, base_url)
    if not href and not re.search(r"[A-Za-z0-9]", text):
        return None

    tag = "button" if as_button else "a"
    attr = f' href="{_escape(href)}"' if href else ""
    return {"tag": tag, "text": text, "html": f"<{tag}{attr}>{_escape(text)}</{tag}>"}


def _list_block(node, base_url):
    tag = node.tag.lower()
    items = []
    text_items = []

    for item in node.xpath("./li"):
        text = node_text(item)
        if not text:
            continue
        text_items.append(text)
        items.append(f"<li>{_inline_html(item, base_url)}</li>")

    if not items:
        return None
    return {"tag": tag, "text": " ".join(text_items), "html": f"<{tag}>\n" + "\n".join(items) + f"\n</{tag}>"}


def _table_block(node, base_url):
    rows = []
    text_parts = []

    for row in node.xpath(".//tr"):
        cells = []
        for cell in row.xpath("./th|./td"):
            tag = cell.tag.lower()
            text = node_text(cell)
            if not text:
                continue
            text_parts.append(text)
            cells.append(f"<{tag}>{_inline_html(cell, base_url)}</{tag}>")
        if cells:
            rows.append("<tr>" + "".join(cells) + "</tr>")

    if not rows:
        return None
    return {"tag": "table", "text": " ".join(text_parts), "html": "<table>\n" + "\n".join(rows) + "\n</table>"}


def _image_source(node):
    source = node.get("src") or node.get("data-src") or node.get("data-lazy-src") or ""
    if not source and node.get("srcset"):
        source = node.get("srcset").split(",")[0].strip().split(" ")[0]
    return source


def _dimension(node, name):
    value = normalize_text(node.get(name))
    match = re.search(r"\d+", value)
    return int(match.group()) if match else None


def _is_icon_image(node, source):
    classes = set(re.findall(r"[a-z0-9]+", (node.get("class") or "").lower()))
    source_lower = source.lower()
    width = _dimension(node, "width")
    height = _dimension(node, "height")

    if source_lower.endswith(".svg") or classes & ICON_WORDS:
        return True
    if any(f"/{word}" in source_lower or f"{word}." in source_lower for word in ICON_WORDS):
        return True
    return width is not None and height is not None and width <= 96 and height <= 96


def _is_widget_image(node, source):
    haystack = " ".join((source, node.get("alt") or "", node.get("class") or "")).lower()
    return any(word in haystack for word in WIDGET_WORDS)


def _image_block(node, base_url):
    source = _image_source(node)
    if not source or source.startswith("data:") or _is_icon_image(node, source) or _is_widget_image(node, source):
        return None

    src = _absolute_url(source, base_url)
    alt = normalize_text(node.get("alt") or node.get("title"))
    href = _action_url(node, base_url)
    attrs = [f'src="{_escape(src)}"']

    if alt:
        attrs.append(f'alt="{_escape(alt)}"')
    image_html = "<img " + " ".join(attrs) + ">"
    if href and href != src:
        image_html = f'<a href="{_escape(href)}">{image_html}</a>'

    return {"tag": "img", "text": alt, "html": image_html}


def extract_semantic_blocks(root, base_url=""):
    """Return semantic blocks in the same order they appear on the page."""
    blocks = []

    def add(block):
        if block and (block.get("text") or block.get("html")):
            blocks.append(block)

    def add_loose_text(value):
        text = normalize_text(value)
        if text:
            add({"tag": "span", "text": text, "html": f"<span>{_escape(text)}</span>"})

    def walk(node):
        if not isinstance(node.tag, str):
            return

        tag = node.tag.lower()
        if tag in SKIP_TAGS:
            return
        # Cleaning keeps aria-hidden nodes that hold real text (collapsed
        # accordion / FAQ answers). Only skip the ones that are purely
        # decorative (no readable text).
        if node.get("aria-hidden") == "true" and not node_text(node):
            return

        if tag in TEXT_TAGS:
            add(_simple_text_block(node, tag))
            return

        if tag == "p":
            add(_paragraph_block(node, base_url))
            return

        if tag in {"ul", "ol"}:
            add(_list_block(node, base_url))
            return

        if tag == "table":
            add(_table_block(node, base_url))
            return

        if tag == "img":
            add(_image_block(node, base_url))
            return

        if tag == "button":
            add(_link_block(node, base_url, as_button=True))
            return

        if tag == "a":
            images = node.xpath(".//img")
            for image in images:
                add(_image_block(image, base_url))
            add(_link_block(node, base_url, as_button=_is_button_link(node)))
            return

        if tag == "span":
            if node.xpath(".//h1|.//h2|.//h3|.//h4|.//h5|.//h6"):
                add_loose_text(node.text)
                for child in node:
                    walk(child)
                    add_loose_text(child.tail)
            else:
                add(_simple_text_block(node, "span"))
            return

        if len(node) == 0:
            add_loose_text(node.text)
            return

        add_loose_text(node.text)
        for child in node:
            walk(child)
            add_loose_text(child.tail)

    walk(root)
    return blocks


def blocks_to_html(blocks):
    return "\n".join(block["html"] for block in blocks if block.get("html")).strip()
