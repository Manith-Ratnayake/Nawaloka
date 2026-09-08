# Chunking

## Purpose

The chunking stage converts extracted Nawaloka website content into smaller meaningful sections that can be indexed and retrieved by the RAG system.

This stage is deterministic and uses the structure of the extracted page instead of an LLM to decide chunk boundaries.

## Process

1. Extracted HTML files are loaded from `extraction/extraction_output`.

2. The page is converted into structured content blocks.

3. Major page sections are separated using `h1` and `h2` headings.

4. Related content under each heading stays together in the same chunk.

5. FAQ sections receive special handling.

6. FAQ questions are detected from `h3` headings or accordion buttons.

7. Each FAQ question and its answer are stored as an individual FAQ chunk.

8. Empty or heading only chunks are removed.

9. Final chunks are written to `chunk_output`.

## Folder structure

```text
chunking/
    processing/      Block loading and chunk creation
    output/          Chunk output handling
    chunk_output/    Generated chunks
    config.py        Input and output paths
    main.py          Chunking entry point
```

## Setup

### 1. Install dependencies

```bash
cd chunking
pip install -r requirements.txt
```

### 2. Run chunking

To process all extracted pages:

```bash
python main.py
```

The script automatically reads from:

```text
../extraction/extraction_output
```

A specific extracted page folder or file can also be passed to `main.py`.

## Output

The generated chunk files are stored under `chunk_output`. These files are used by the ingestion stage to create embeddings and populate OpenSearch.
