from config import OUTPUT_DIR
from text import page_slug


def save_success(url, simplified_html, chunks):
    folder = OUTPUT_DIR / page_slug(url)
    folder.mkdir(parents=True, exist_ok=True)

    (folder / "extracted.html").write_text(simplified_html, encoding="utf-8")

    text_parts = []
    for chunk in chunks:
        chunk_html = chunk.get("html", "").strip()
        if not chunk_html:
            continue

        chunk_id = len(text_parts) + 1
        marker = f"==================== CHUNK {chunk_id:03d} ===================="
        text_parts.append(f"{marker}\n\n{chunk_html}")

    (folder / "chunks.txt").write_text("\n\n".join(text_parts), encoding="utf-8")

    for old_name in ("chunks.json", "meta.json"):
        old_file = folder / old_name
        if old_file.exists():
            old_file.unlink()

    return folder, len(text_parts)
