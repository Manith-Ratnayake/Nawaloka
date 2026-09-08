# Chunking

## Overview

The chunking stage converts extracted Nawaloka website content into retrieval friendly chunks.

The system uses **structure aware chunking** based on the HTML structure of each page instead of fixed character or token limits.

## Chunking Strategy

### 1. H1 and H2 Section Chunking

`h1` and `h2` headings define the main section boundaries.

A new chunk starts when a new `h1` or `h2` section begins. Content under that heading remains together until the next section boundary.

why is this?
The web developer wants to show a 1 message using 1 section, this layout can be use for chunking
otherwise require an LLM to rediscover the meaning

```text
H2: Heart Centre
Paragraph
Paragraph
List

H2: Services
Paragraph
```

becomes:

```text
Chunk 1
Heart Centre
Paragraph
Paragraph
List

Chunk 2
Services
Paragraph
```

This keeps related website content together instead of splitting it based on arbitrary length.

### 2. FAQ Chunking

FAQ sections use a separate strategy.

Each individual question and its answer becomes one chunk.

Questions can be identified from `h3` headings or FAQ accordion buttons depending on the page structure.

```text
FAQ Question 1 + Answer 1 → Chunk 1
FAQ Question 2 + Answer 2 → Chunk 2
FAQ Question 3 + Answer 3 → Chunk 3
```

This allows individual FAQ answers to be retrieved directly without retrieving the entire FAQ section.

### 3. Structure Preservation

The original order of the webpage content is preserved.

Paragraphs, lists, headings, buttons, and other related elements remain with the section they belong to.

Empty chunks and sections containing only a heading are removed.

## Chunking Flow

```text
Extracted HTML
      ↓
Load HTML blocks
      ↓
Detect H1 and H2 sections
      ↓
Create section based chunks
      ↓
Apply FAQ specific chunking
      ↓
Remove empty chunks
      ↓
Save chunks.txt
```

## Folder Structure

```text
chunking/
    processing/
        load_blocks.py
        chunking/
            create_chunks.py

    output/
    chunk_output/
    config.py
    main.py
    requirements.txt
```

## Setup

```bash
cd chunking
pip install -r requirements.txt
```

## Run

Process all extracted pages:

```bash
python main.py
```

The chunker reads extracted website content from:

```text
../extraction/extraction_output
```

Generated chunks are saved to:

```text
chunk_output/
```

Each page receives a `chunks.txt` file which is later used by the ingestion pipeline to generate embeddings and index the content in OpenSearch.