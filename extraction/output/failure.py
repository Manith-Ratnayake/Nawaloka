from config import OUTPUT_DIR
from text import page_slug


def save_failure(url, error):
    folder = OUTPUT_DIR / page_slug(url)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "error.txt").write_text(str(error), encoding="utf-8")

    print(f"Failed: {error}")
    print(f"Saved failure details -> {folder}")
