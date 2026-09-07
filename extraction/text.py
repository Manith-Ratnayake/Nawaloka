import re
from urllib.parse import urlparse

from lxml import html


def normalize_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def node_text(node):
    return normalize_text(" ".join(node.itertext()))


def visible_text(raw_html):
    """Rough count of human-visible text in a raw HTML string.

    Used only to tell 'the crawl came back empty' apart from 'our pipeline
    dropped real content'. Strips script/style/noscript, keeps everything else.
    """
    if not raw_html:
        return ""
    try:
        root = html.fromstring(raw_html)
    except Exception:
        return ""
    for element in root.xpath("//script|//style|//noscript"):
        parent = element.getparent()
        if parent is not None:
            parent.remove(element)
    body = root.xpath("//body")
    node = body[0] if body else root
    return node_text(node)


def page_slug(url):
    path = urlparse(url).path.strip("/") or "home"
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", path.replace("/", "__"))
