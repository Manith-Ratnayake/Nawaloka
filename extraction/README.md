# Nawaloka Semantic HTML Chunker

The crawler keeps rendered page content, removes interface noise, simplifies the HTML, builds major sections from `h1` and `h2`, then performs final structure specific splitting such as FAQ questions.

## Pipeline

```text
Async Firecrawl HTML
  ↓
remove page noise, hidden elements and forms
  ↓
flatten layout containers while preserving semantic content
  ↓
build major h1 / h2 sections
  ↓
split FAQ questions
  ↓
assign final chunk numbers
  ↓
save output
```

## Preserved content

```html
<h1>...</h1>
<h2>...</h2>
<h3>...</h3>
<span>...</span>
<p>...</p>
<ul><li>...</li></ul>
<ol><li>...</li></ol>
<a href="...">...</a>
<button href="...">...</button>
<table>...</table>
<img src="..." alt="...">
```

Forms and their controls are removed because they are interactive UI rather than readable page knowledge.

Meaningful images are preserved. Small icons, SVG icons and common icon assets are ignored. If an image is linked, the image is kept inside its link.

Button destinations are recovered from normal links, common data URL attributes, navigation `onclick` expressions, descendant links and nearby clickable parent elements when available.

## Chunk boundaries

`h1` and `h2` create major section boundaries. `h3` and lower headings stay inside their current major section.

Only trailing `span` labels immediately associated with a following `h1` or `h2` can move with that heading. Long runs of spans remain with their current section so lists such as service names are not accidentally moved forward. Paragraphs are not moved using character count, wording similarity, or color heuristics.

FAQ content is first collected as one major section. The final chunking step then divides it by `h3` question, keeping each question with its answer. Chunk numbers are assigned only after this final split.

Heading only sections with no content are discarded.

## Output per page

```text
extracted.html
chunks.txt
```

`raw.html` is saved only when a page produces zero chunks. `error.txt` is saved when crawling or processing fails.

## Crawl behavior

Pages are scraped concurrently with `AsyncFirecrawl`. `FIRECRAWL_CONCURRENCY` controls how many pages can run at once.

The default page render wait is 12 seconds. A page that still returns very little text and zero chunks is retried once with an 18 second wait.

## Install

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your Firecrawl API key.

## Run

```bash
python main.py
python main.py https://www.nawaloka.com/aboutus
```
