"""
Summary builder for v1.

Transforms a combined DataFrame of analyzed content into the
CompetitorAnalysisSummary shape defined in models.py and README section 8.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .models import (
    CompetitorAnalysisSummary,
    CompetitorConfig,
    CompetitorSummary,
    SentimentBucket,
    TopicSummary,
)
from .stopwords import CUSTOM_STOP_WORDS
from .embeddings import embed_competitors, position_competitors
from .keywords import extract_keybert_phrases
from .stopwords import CUSTOM_STOP_WORDS

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None  # type: ignore


VADER_POS_THRESHOLD = 0.05
VADER_NEG_THRESHOLD = -0.05


def _sentiment_category(mean_compound: float) -> str:
    if mean_compound >= 0.5:
        return "Very Positive"
    if mean_compound > 0:
        return "Positive"
    if mean_compound == 0:
        return "Neutral"
    if mean_compound > -0.5:
        return "Negative"
    return "Very Negative"


def build_sentiment_buckets(df: "pd.DataFrame") -> Dict[str, SentimentBucket]:
    """
    Build sentiment buckets per competitor using VADER compound score thresholds.
    """
    buckets: Dict[str, SentimentBucket] = {}
    for competitor_id, group in df.groupby("competitorId"):
        pos = int((group["vader_sentiment"] >= VADER_POS_THRESHOLD).sum())
        neu = int(((group["vader_sentiment"] > VADER_NEG_THRESHOLD) & (group["vader_sentiment"] < VADER_POS_THRESHOLD)).sum())
        neg = int((group["vader_sentiment"] <= VADER_NEG_THRESHOLD).sum())
        buckets[competitor_id] = SentimentBucket(positive=pos, neutral=neu, negative=neg)
    return buckets


def _extract_top_terms(text_series: "pd.Series", *, top_n: int, stopwords: List[str] | None = None) -> List[str]:
    tokens: Counter[str] = Counter()
    stopset = set(stopwords or [])
    for text in text_series.dropna().astype(str):
        tokens.update([w for w in text.split() if w not in stopset])
    return [w for w, _ in tokens.most_common(top_n)]


def build_summary_from_dataframe(
    df: "pd.DataFrame",
    competitors: List[CompetitorConfig],
    settings: Dict[str, Any],
) -> CompetitorAnalysisSummary:
    """
    Core v1 summary builder.

    Expected df columns:
      - competitorId (or competitor)
      - name (optional)
      - baseUrl (optional)
      - vader_sentiment
      - technical_keywords
      - value_keywords
      - cleaned_text
    """
    if pd is None:
        raise ImportError("pandas is required for build_summary_from_dataframe")

    # Normalize competitorId column
    if "competitorId" not in df.columns:
        if "competitor" in df.columns:
            df = df.rename(columns={"competitor": "competitorId"})
        else:
            raise ValueError("DataFrame must have 'competitorId' or 'competitor' column")

    # Attach competitor metadata
    comp_map = {c.id: c for c in competitors}
    df["name"] = df["competitorId"].map(lambda cid: comp_map.get(cid).name if comp_map.get(cid) else cid)
    df["baseUrl"] = df["competitorId"].map(lambda cid: comp_map.get(cid).baseUrl if comp_map.get(cid) else "")

    sentiment_by_comp = build_sentiment_buckets(df)

    # Aggregate keyword counts
    value_vs_tech: Dict[str, Dict[str, float]] = {}
    sentiment_mean: Dict[str, float] = {}
    for competitor_id, group in df.groupby("competitorId"):
        value_total = float(group["value_keywords"].sum())
        tech_total = float(group["technical_keywords"].sum())
        value_vs_tech[competitor_id] = {"value": value_total, "technical": tech_total}
        sentiment_mean[competitor_id] = float(group["vader_sentiment"].mean())

    # Competitor summaries
    competitor_summaries: List[CompetitorSummary] = []
    for competitor_id, group in df.groupby("competitorId"):
        top_props = _extract_top_terms(group.get("cleaned_text", pd.Series(dtype=str)), top_n=5, stopwords=CUSTOM_STOP_WORDS)
        comp = comp_map.get(competitor_id)
        competitor_summaries.append(
            CompetitorSummary(
                competitorId=competitor_id,
                name=comp.name if comp else competitor_id,
                baseUrl=comp.baseUrl if comp else "",
                sentiment=sentiment_by_comp.get(
                    competitor_id, SentimentBucket(positive=0, neutral=0, negative=0)
                ),
                valueVsTechnical=value_vs_tech.get(competitor_id, {"value": 0.0, "technical": 0.0}),
                topProps=top_props,
            )
        )

    # Global top lists
    top_value_props = _extract_top_terms(df.get("cleaned_text", pd.Series(dtype=str)), top_n=10, stopwords=CUSTOM_STOP_WORDS)
    top_keywords = _extract_top_terms(df.get("cleaned_text", pd.Series(dtype=str)), top_n=25, stopwords=CUSTOM_STOP_WORDS)

    # Build card-friendly meta view
    competitor_cards: List[Dict[str, Any]] = []
    tech_terms = set(t.lower() for t in settings.get("technical_terms", []))
    value_terms = set(t.lower() for t in settings.get("value_terms", []))

    for competitor_id, group in df.groupby("competitorId"):
        total_kw = value_vs_tech[competitor_id]["value"] + value_vs_tech[competitor_id]["technical"]
        value_share = (value_vs_tech[competitor_id]["value"] / total_kw * 100) if total_kw else 0.0
        tech_share = (value_vs_tech[competitor_id]["technical"] / total_kw * 100) if total_kw else 0.0

        # top technical concepts (frequency of technical terms)
        words = []
        for text in group.get("cleaned_text", pd.Series(dtype=str)).dropna().astype(str):
            words.extend(text.split())
        tech_counts = pd.Series(words).loc[lambda s: s.isin(tech_terms)].value_counts()
        top_tech = list(tech_counts.head(5).index)

        sentiment_score = sentiment_mean.get(competitor_id, 0.0)
        competitor_cards.append(
            {
                "competitorId": competitor_id,
                "name": comp_map.get(competitor_id).name if comp_map.get(competitor_id) else competitor_id,
                "baseUrl": comp_map.get(competitor_id).baseUrl if comp_map.get(competitor_id) else "",
                "sentimentScore": sentiment_score,
                "sentimentCategory": _sentiment_category(sentiment_score),
                "techValueRatio": {"value": value_share, "technical": tech_share},
                "topValueProps": list(_extract_top_terms(group.get("cleaned_text", pd.Series(dtype=str)), top_n=5)),
                "topTechnicalConcepts": top_tech,
            }
        )

    summary = CompetitorAnalysisSummary(
        competitors=competitor_summaries,
        topics=[],  # v1 defers topic modeling
        sentimentByCompetitor=sentiment_by_comp,
        valueVsTechnicalByCompetitor=value_vs_tech,
        topValueProps=top_value_props,
        topKeywords=top_keywords,
        _meta={
            "seriesKind": "competitor_analysis",
            "engineVersion": settings.get("engineVersion", "v1.0.0"),
            "runConfig": settings,
            "competitorCards": competitor_cards,
        },
    )

    # Optional: embeddings for positioning map
    if settings.get("use_embeddings"):
        try:
            comp_embeddings = embed_competitors(df, settings.get("embedding_model", "all-MiniLM-L6-v2"))
            summary._meta["positioningMap"] = position_competitors(comp_embeddings)
        except Exception:
            summary._meta["positioningMap"] = {}

    # Optional: keybert phrases
    if settings.get("use_keybert"):
        try:
            phrases = extract_keybert_phrases(
                [" ".join(df.get("cleaned_text", pd.Series(dtype=str)).dropna().astype(str))],
                model_name=settings.get("keybert_model", "all-MiniLM-L6-v2"),
                top_n=10,
            )
            summary._meta["keybertKeywords"] = phrases
        except Exception:
            summary._meta["keybertKeywords"] = []

    # Optional: overlap/differentiation vs your terms
    your_terms = set(t.lower() for t in settings.get("your_terms", []) if t)
    if your_terms:
        overlap_map: Dict[str, Dict[str, float]] = {}
        for competitor_id, group in df.groupby("competitorId"):
            words = set()
            for text in group.get("cleaned_text", pd.Series(dtype=str)).dropna().astype(str):
                words.update([w for w in text.split() if w not in CUSTOM_STOP_WORDS])
            overlap = len(words & your_terms) / len(words | your_terms) if words else 0.0
            overlap_map[competitor_id] = {
                "overlap": overlap,
                "differentiationScore": 1 - overlap,
            }
        summary._meta["overlapByCompetitor"] = overlap_map

    return summary
