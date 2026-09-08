from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR.parent / "extraction" / "extraction_output"
OUTPUT_DIR = BASE_DIR / "chunk_output"
