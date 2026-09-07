import os

from dotenv import load_dotenv
from firecrawl import AsyncFirecrawl

from config import FIRECRAWL_BACKOFF_FACTOR, FIRECRAWL_CLIENT_TIMEOUT_SECONDS, FIRECRAWL_MAX_AGE_MS, FIRECRAWL_MAX_RETRIES, FIRECRAWL_PAGE_TIMEOUT_MS, FIRECRAWL_WAIT_FOR_MS


def create_client():
    load_dotenv()
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise RuntimeError("FIRECRAWL_API_KEY is missing. Add it to .env or your environment.")

    return AsyncFirecrawl(api_key=api_key, timeout=FIRECRAWL_CLIENT_TIMEOUT_SECONDS, max_retries=FIRECRAWL_MAX_RETRIES, backoff_factor=FIRECRAWL_BACKOFF_FACTOR)


async def scrape_page(client, url, wait_for=FIRECRAWL_WAIT_FOR_MS):
    return await client.scrape(url, formats=["html"], only_main_content=False, timeout=FIRECRAWL_PAGE_TIMEOUT_MS, wait_for=wait_for, mobile=False, remove_base64_images=False, fast_mode=False, block_ads=False, max_age=FIRECRAWL_MAX_AGE_MS)
