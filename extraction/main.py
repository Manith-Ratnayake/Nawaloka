import asyncio
import sys

from config import CAPTURE_MIN_TEXT, CAPTURE_RETRY_WAIT_MS, FIRECRAWL_CONCURRENCY
from crawl.firecrawl import create_client, scrape_page
from output.debug import save_raw_html
from output.failure import save_failure
from output.success import save_success
from processing.pipeline import process_page
from text import visible_text
from urls import URLS


def _html_of(document):
    return getattr(document, "html", None) or ""


async def crawl_webpage(client, url, semaphore):
    async with semaphore:
        print(f"\nCrawling: {url}")

        try:
            document = await scrape_page(client, url)
            rendered_html = _html_of(document)
            if not rendered_html:
                raise RuntimeError("Firecrawl returned no HTML.")

            simplified_html, chunks = process_page(rendered_html, url=url)
            raw_len = len(visible_text(rendered_html))

            if not chunks and raw_len < CAPTURE_MIN_TEXT:
                print(f"  ! low text ({raw_len} chars) and 0 chunks - retrying with a longer wait")
                retry_document = await scrape_page(client, url, wait_for=CAPTURE_RETRY_WAIT_MS)
                retry_html = _html_of(retry_document)
                retry_len = len(visible_text(retry_html))
                if retry_len > raw_len:
                    rendered_html, raw_len = retry_html, retry_len
                    simplified_html, chunks = process_page(rendered_html, url=url)

            folder, saved = save_success(url, simplified_html, chunks)

            status = "ok"
            if saved == 0:
                save_raw_html(url, rendered_html)
                if raw_len < CAPTURE_MIN_TEXT:
                    status = "capture-gap"
                    print(f"  !! CAPTURE GAP: page had ~{raw_len} chars of text; content likely never rendered.")
                else:
                    status = "dropped"
                    print(f"  !! DROPPED: page had ~{raw_len} chars of text but produced 0 chunks - cleaning/chunking bug.")
                print(f"     raw HTML saved for inspection -> {folder / 'raw.html'}")

            print(f"Saved {saved} chunks -> {folder}")
            return url, saved, status
        except Exception as exc:
            save_failure(url, exc)
            print(f"  !! ERROR: {exc}")
            return url, 0, "error"


def print_summary(results):
    print("\n==================== SUMMARY ====================")
    for url, saved, status in results:
        flag = "" if status == "ok" else f"   <-- {status.upper()}"
        print(f"{saved:>4} chunks  {url}{flag}")

    problems = [result for result in results if result[2] != "ok"]
    if problems:
        print(f"\n{len(problems)} page(s) need attention: " + ", ".join(f"{url} ({status})" for url, _, status in problems))
    else:
        print("\nAll pages produced chunks.")


async def async_main():
    urls = sys.argv[1:] or URLS
    if not urls:
        raise RuntimeError("No URLs provided and URLS in urls.py is empty.")

    client = create_client()
    semaphore = asyncio.Semaphore(FIRECRAWL_CONCURRENCY)
    results = await asyncio.gather(*(crawl_webpage(client, url, semaphore) for url in urls))
    print_summary(results)


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
