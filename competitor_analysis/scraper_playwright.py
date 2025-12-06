"""
Playwright-based scraper for JS-heavy pages.

This is optional and used when settings['scraper_backend'] == 'playwright'.
Requires `playwright` to be installed and browsers set up (`playwright install`).
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime
from typing import Any, Dict, List

from .models import CompetitorConfig


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def _fetch_page(context, url: str, competitor: CompetitorConfig, max_elements: int) -> List[Dict[str, Any]]:
    page = await context.new_page()
    await page.goto(url, wait_until="domcontentloaded")
    html = await page.content()
    await page.close()

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    rows: List[Dict[str, Any]] = []
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    meta_desc = ""
    md = soup.find("meta", attrs={"name": "description"})
    if md and md.get("content"):
        meta_desc = md["content"]

    for idx, tag in enumerate(soup.find_all(["h1", "h2", "h3", "p"])):
        if idx >= max_elements:
            break
        text = tag.get_text(strip=True)
        if not text:
            continue
        rows.append(
            {
                "competitorId": competitor.id,
                "competitor": competitor.name,
                "url": url,
                "elementType": tag.name,
                "rawText": text,
                "scrapeDate": datetime.utcnow().isoformat(),
                "title": title,
                "metaDescription": meta_desc,
                "contentHash": _content_hash(text),
            }
        )
    return rows


async def _scrape_competitor_async(
    competitor: CompetitorConfig,
    *,
    timeout_seconds: int,
    max_retries: int,
    delay_seconds: float,
    max_pages: int,
    max_elements: int,
    user_agent: str,
) -> List[Dict[str, Any]]:
    from playwright.async_api import async_playwright

    pages = competitor.priorityPages[:max_pages]
    results: List[Dict[str, Any]] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=user_agent)
        for page in pages:
            url = competitor.baseUrl.rstrip("/") + "/" + page.lstrip("/")
            attempt = 0
            while attempt < max_retries:
                attempt += 1
                try:
                    rows = await _fetch_page(context, url, competitor, max_elements)
                    results.extend(rows)
                    break
                except Exception:
                    if attempt >= max_retries:
                        break
                    await asyncio.sleep(delay_seconds * attempt)
            await asyncio.sleep(delay_seconds)
        await browser.close()
    return results


def scrape_competitor_pages_playwright(
    competitor: CompetitorConfig,
    *,
    timeout_seconds: int = 20,
    max_retries: int = 2,
    delay_seconds: float = 1.0,
    max_pages: int = 50,
    max_elements: int = 2000,
    user_agent: str = "CompetitorAnalysisBot/0.1",
) -> List[Dict[str, Any]]:
    try:
        return asyncio.run(
            _scrape_competitor_async(
                competitor,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                delay_seconds=delay_seconds,
                max_pages=max_pages,
                max_elements=max_elements,
                user_agent=user_agent,
            )
        )
    except Exception:
        return []

