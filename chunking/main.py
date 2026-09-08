import sys
from pathlib import Path

from config import INPUT_DIR
from output.success import save_success
from processing.chunking.create_chunks import extract_chunks
from processing.load_blocks import load_blocks


def find_input_files(arguments):
    if not arguments:
        return sorted(INPUT_DIR.glob("*/extracted.html"))

    files = []
    for value in arguments:
        path = Path(value).resolve()
        if path.is_file():
            files.append(path)
        elif path.is_dir() and (path / "extracted.html").is_file():
            files.append(path / "extracted.html")
        elif path.is_dir():
            files.extend(sorted(path.glob("*/extracted.html")))
        else:
            raise FileNotFoundError(f"Input not found: {value}")

    return files


def chunk_file(file_path):
    extracted_html = file_path.read_text(encoding="utf-8")
    blocks = load_blocks(extracted_html)
    chunks = extract_chunks(blocks)
    folder, saved = save_success(file_path.parent.name, chunks)
    print(f"Saved {saved} chunks -> {folder}")
    return file_path, saved


def main():
    files = find_input_files(sys.argv[1:])
    if not files:
        raise RuntimeError(f"No extracted.html files found in {INPUT_DIR}")

    for file_path in files:
        print(f"\nChunking: {file_path}")
        chunk_file(file_path)


if __name__ == "__main__":
    main()
