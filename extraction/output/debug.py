"""Persist the raw crawl HTML when a page produces no chunks, so a capture gap
can be told apart from a chunking bug by inspection."""

from config import OUTPUT_DIR
from text import page_slug


def save_raw_html(url, raw_html):
    folder = OUTPUT_DIR / page_slug(url)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "raw.html"
    path.write_text(raw_html or "", encoding="utf-8")
    return path
