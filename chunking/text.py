import re

from lxml import html


def normalize_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def node_text(node):
    return normalize_text(" ".join(node.itertext()))
