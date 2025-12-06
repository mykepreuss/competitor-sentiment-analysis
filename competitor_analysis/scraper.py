"""
Scraper service.

Uses requests + BeautifulSoup to fetch priority pages and extract content from
H1/H2/H3/P elements. Designed to be lightweight and JSON-friendly, with polite
delays and basic robots.txt awareness. Optionally dispatches to Playwright for
JS-heavy pages when settings['scraper_backend'] == 'playwright'.
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup
from urllib import robotparser

from .models import CompetitorConfig
from .scraper_playwright import scrape_competitor_pages_playwright


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_page_content(html: str, url: str, competitor: CompetitorConfig, max_elements: int) -> List[Dict[str, Any]]:
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


def scrape_competitor_pages(
    competitor: CompetitorConfig,
    *,
    timeout_seconds: int = 20,
    max_retries: int = 2,
    delay_seconds: float = 1.0,
    max_pages: int = 50,
    max_elements: int = 2000,
    user_agent: str = "CompetitorAnalysisBot/0.1",
    backend: str = "requests",
) -> List[Dict[str, Any]]:
    if backend == "playwright":
        try:
            return scrape_competitor_pages_playwright(
                competitor,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                delay_seconds=delay_seconds,
                max_pages=max_pages,
                max_elements=max_elements,
                user_agent=user_agent,
            )
        except Exception:
            # Fallback to requests if playwright fails
            pass

    rows: List[Dict[str, Any]] = []
    pages = competitor.priorityPages[:max_pages]
    rp = robotparser.RobotFileParser()
    try:
        rp.set_url(competitor.baseUrl.rstrip("/") + "/robots.txt")
        rp.read()
    except Exception:
        rp = None

    for page in pages:
        url = competitor.baseUrl.rstrip("/") + "/" + page.lstrip("/")
        if rp and not rp.can_fetch(user_agent, url):
            continue
        attempt = 0
        while attempt < max_retries:
            attempt += 1
            try:
                resp = requests.get(url, headers={"User-Agent": user_agent}, timeout=timeout_seconds)
                if resp.status_code >= 400:
                    raise requests.HTTPError(f"{resp.status_code} for {url}")
                rows.extend(extract_page_content(resp.text, url, competitor, max_elements))
                break
            except Exception:
                if attempt >= max_retries:
                    break
                time.sleep(delay_seconds * attempt)
                continue
        time.sleep(delay_seconds)
    return rows


def scrape_all_competitors(
    competitors: List[CompetitorConfig],
    *,
    timeout_seconds: int = 20,
    max_retries: int = 2,
    delay_seconds: float = 1.0,
    max_pages: int = 50,
    max_elements: int = 2000,
    user_agent: str = "CompetitorAnalysisBot/0.1",
    backend: str = "requests",
) -> List[Dict[str, Any]]:
    """
    Aggregate content across all competitors.
    """
    all_rows: List[Dict[str, Any]] = []
    for comp in competitors:
        rows = scrape_competitor_pages(
            comp,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            delay_seconds=delay_seconds,
            max_pages=max_pages,
            max_elements=max_elements,
            user_agent=user_agent,
            backend=backend,
        )
        all_rows.extend(rows)
    return all_rows
