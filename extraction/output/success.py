from config import OUTPUT_DIR
from text import page_slug


def save_success(url, simplified_html):
    folder = OUTPUT_DIR / page_slug(url)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "extracted.html").write_text(simplified_html, encoding="utf-8")
    return folder
