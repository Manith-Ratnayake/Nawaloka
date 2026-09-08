from lxml import html

from processing.cleaning.clean_page import clean_page
from processing.extraction.simplify_html import blocks_to_html, extract_semantic_blocks


def process_page(raw_html, url=""):
    root = html.fromstring(raw_html)
    clean_page(root)

    body = root.xpath("//body")
    content_root = body[0] if body else root

    blocks = extract_semantic_blocks(content_root, base_url=url)
    simplified_html = blocks_to_html(blocks)

    return simplified_html, len(blocks)
