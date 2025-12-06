"""
Analysis helpers for per-row text processing.

v1 uses NLTK VADER when available and falls back to neutral scores if not.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

try:  # pragma: no cover - external dependency
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer
except Exception:  # pragma: no cover
    nltk = None
    SentimentIntensityAnalyzer = None  # type: ignore

_vader = None


def _ensure_vader() -> None:
    global _vader
    if _vader is not None:
        return
    if SentimentIntensityAnalyzer is None or nltk is None:
        _vader = None
        return
    try:
        # Ensure lexicon is present
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        try:
            nltk.download("vader_lexicon", quiet=True)
        except Exception:
            _vader = None
            return
    try:
        _vader = SentimentIntensityAnalyzer()
    except Exception:
        _vader = None


def clean_text(text: str) -> str:
    """Lowercase, remove non-alpha, collapse spaces."""
    text = re.sub(r"[^a-zA-Z\s]", " ", str(text))
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def analyze_text_row(
    text: str,
    *,
    technical_terms: List[str],
    value_terms: List[str],
) -> Dict[str, Any]:
    """
    Analyze a single text snippet.
    Returns sentiment metrics, keyword counts, intent, and cleaned_text.
    """
    cleaned = clean_text(text)
    tokens = cleaned.split()

    tech_terms = {t.lower().strip() for t in technical_terms}
    val_terms = {t.lower().strip() for t in value_terms}

    tech_count = sum(1 for t in tokens if t in tech_terms)
    value_count = sum(1 for t in tokens if t in val_terms)

    if tech_count > value_count:
        intent = "Technical"
    elif value_count > tech_count:
        intent = "Value Proposition"
    elif tech_count == value_count and tech_count > 0:
        intent = "Balanced"
    else:
        intent = "Other"

    _ensure_vader()
    if _vader:
        scores = _vader.polarity_scores(cleaned)
        vader_compound = scores.get("compound", 0.0)
        sentiment_score = scores.get("pos", 0.0) - scores.get("neg", 0.0)
        avg_sent = (vader_compound + sentiment_score) / 2
    else:
        vader_compound = 0.0
        sentiment_score = 0.0
        avg_sent = 0.0

    return {
        "cleaned_text": cleaned,
        "sentiment": sentiment_score,
        "vader_sentiment": vader_compound,
        "average_sentiment": avg_sent,
        "technical_keywords": tech_count,
        "value_keywords": value_count,
        "intent": intent,
    }


def analyze_page_contents(
    page_contents: List[Dict[str, Any]],
    *,
    technical_terms: List[str],
    value_terms: List[str],
) -> List[Dict[str, Any]]:
    """
    Map analyze_text_row across PageContent dicts. Each result merges original
    fields with analysis metrics.
    """
    results: List[Dict[str, Any]] = []
    for row in page_contents:
        text = row.get("rawText") or row.get("text") or ""
        analysis = analyze_text_row(text, technical_terms=technical_terms, value_terms=value_terms)
        merged = {**row, **analysis}
        results.append(merged)
    return results
