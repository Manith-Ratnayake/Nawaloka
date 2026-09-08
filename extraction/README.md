# Extraction

## Purpose

The extraction stage collects content from selected Nawaloka website pages and converts the rendered pages into cleaner structured HTML for later chunking.

## Process

1. URLs are read from `urls.py` or passed through the command line.

2. Pages are fetched asynchronously using Firecrawl.

3. The crawler waits for rendered page content before processing it.

4. Navigation noise and unnecessary page elements are removed by the processing pipeline.

5. Useful page content and structural HTML are preserved.

6. Pages with very little captured text are retried with a longer wait.

7. Successful extraction results are written to `extraction_output`.

8. Failed or incomplete pages are recorded for inspection.

## Folder structure

```text
extraction/
    crawl/               Firecrawl client and page fetching
    processing/          HTML cleaning and extraction logic
    output/              Output handling
    extraction_output/   Extracted page content
    config.py            Crawl and retry settings
    main.py              Extraction entry point
    urls.py              Website URLs
```

## Setup

### 1. Install dependencies

```bash
cd extraction
pip install -r requirements.txt
```

### 2. Environment variable

```env
FIRECRAWL_API_KEY=
```

### 3. Run extraction

Run all URLs defined in `urls.py`.

```bash
python main.py
```

A specific URL can also be passed directly.

```bash
python main.py https://www.nawaloka.com/aboutus
```

## Output

Each processed page is stored under `extraction_output` and contains the extracted HTML used by the chunking stage.
