"""
Report generation stubs.

These functions should create artifacts (CSV/Excel/PNG/Markdown) and return
artifact metadata. For now they only create placeholder metadata to keep the
pipeline testable without heavy dependencies or I/O.
"""

from __future__ import annotations

import os
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Dict, List

import matplotlib.pyplot as plt

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None  # type: ignore

from .models import CompetitorAnalysisRunRecord, CompetitorArtifactRecord


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def generate_csv_and_excel(
    run: CompetitorAnalysisRunRecord,
    df: "Any",  # DataFrame expected
    output_dir: str,
) -> List[CompetitorArtifactRecord]:
    if pd is None:
        return []
    run_dir = os.path.join(output_dir, run.id)
    _ensure_dir(run_dir)
    artifacts: List[CompetitorArtifactRecord] = []

    csv_path = os.path.join(run_dir, f"{run.id}_analysis.csv")
    df.to_csv(csv_path, index=False)
    artifacts.append(
        CompetitorArtifactRecord(
            id=f"artifact-{run.id}-csv",
            projectId=run.projectId,
            humId=run.humId,
            runId=run.id,
            scenarioId="run_report",
            scenarioKind="competitor_analysis",
            routeTemplate="/competitors/report",
            device="desktop",
            stateSlug="summary",
            capturedAt=_now_iso(),
            mimeType="text/csv",
            rawKey=csv_path,
            brandedKey=None,
            thumbKey=None,
            diffKey=None,
            afterUrl=None,
            beforeUrl=None,
            thumbUrl=None,
            byteSize=None,
            width=None,
            height=None,
        )
    )

    xlsx_path = os.path.join(run_dir, f"{run.id}_analysis.xlsx")
    with pd.ExcelWriter(xlsx_path) as writer:
        # Raw Data
        df.to_excel(writer, sheet_name="Raw Data", index=False)

        # Summary sheet
        summary = df.groupby("competitorId").agg(
            sentiment_mean=("sentiment", "mean"),
            sentiment_std=("sentiment", "std"),
            vader_mean=("vader_sentiment", "mean"),
            vader_std=("vader_sentiment", "std"),
            technical_sum=("technical_keywords", "sum"),
            technical_mean=("technical_keywords", "mean"),
            value_sum=("value_keywords", "sum"),
            value_mean=("value_keywords", "mean"),
        )
        summary.to_excel(writer, sheet_name="Summary")

        # Intent Distribution
        intent_dist = pd.crosstab(df["competitorId"], df["intent"])
        intent_dist.to_excel(writer, sheet_name="Intent Distribution")

        # Sentiment Analysis
        sentiment_stats = df.groupby("competitorId")["vader_sentiment"].agg(
            ["mean", "median", "std", "min", "max"]
        )
        sentiment_stats.to_excel(writer, sheet_name="Sentiment Analysis")

        # Keyword frequency sheet (stopword-filtered)
        if "cleaned_text" in df.columns:
            words = []
            for text in df["cleaned_text"].dropna().astype(str):
                words.extend([w for w in text.split() if w not in CUSTOM_STOP_WORDS])
            if words:
                freq = pd.Series(words).value_counts().reset_index()
                freq.columns = ["keyword", "count"]
                freq.to_excel(writer, sheet_name="Top Keywords", index=False)
    artifacts.append(
        CompetitorArtifactRecord(
            id=f"artifact-{run.id}-xlsx",
            projectId=run.projectId,
            humId=run.humId,
            runId=run.id,
            scenarioId="run_report",
            scenarioKind="competitor_analysis",
            routeTemplate="/competitors/report",
            device="desktop",
            stateSlug="summary",
            capturedAt=_now_iso(),
            mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            rawKey=xlsx_path,
            brandedKey=None,
            thumbKey=None,
            diffKey=None,
            afterUrl=None,
            beforeUrl=None,
            thumbUrl=None,
            byteSize=None,
            width=None,
            height=None,
        )
    )
    return artifacts


def generate_keyword_distribution_plot(
    run: CompetitorAnalysisRunRecord,
    df: "Any",
    output_dir: str,
) -> CompetitorArtifactRecord:
    run_dir = os.path.join(output_dir, run.id)
    _ensure_dir(run_dir)
    # Expect columns: competitorId, technical_keywords, value_keywords
    grouped = df.groupby("competitorId")[["technical_keywords", "value_keywords"]].sum()
    ax = grouped.plot(kind="bar", figsize=(12, 6), stacked=True, ylabel="Keyword Count")
    ax.set_title("Keyword Distribution by Competitor")
    # annotate totals and percentages
    for idx, (comp, row) in enumerate(grouped.iterrows()):
        tech = row["technical_keywords"]
        val = row["value_keywords"]
        total = tech + val
        tech_pct = (tech / total * 100) if total else 0
        val_pct = (val / total * 100) if total else 0
        ax.text(
            idx,
            tech / 2,
            f"{int(tech)}\n({tech_pct:.1f}%)",
            ha="center",
            va="center",
            color="white",
            fontweight="bold",
        )
        ax.text(
            idx,
            tech + val / 2,
            f"{int(val)}\n({val_pct:.1f}%)",
            ha="center",
            va="center",
            color="white",
            fontweight="bold",
        )
        ax.text(
            idx,
            total + (total * 0.05),
            f"Total: {int(total)}",
            ha="center",
            va="bottom",
            fontweight="bold",
        )
    plt.tight_layout()
    plot_path = os.path.join(run_dir, f"{run.id}_keyword_distribution.png")
    plt.savefig(plot_path, dpi=200)
    plt.close()

    return CompetitorArtifactRecord(
        id=f"artifact-{run.id}-keyword-plot",
        projectId=run.projectId,
        humId=run.humId,
        runId=run.id,
        scenarioId="sentiment_overview",
        scenarioKind="competitor_analysis",
        routeTemplate="/competitors/sentiment",
        device="desktop",
        stateSlug="summary",
        capturedAt=_now_iso(),
        mimeType="image/png",
        rawKey=plot_path,
        brandedKey=None,
        thumbKey=None,
        diffKey=None,
        afterUrl=None,
        beforeUrl=None,
        thumbUrl=None,
        byteSize=None,
        width=None,
        height=None,
    )


def generate_sentiment_plot(
    run: CompetitorAnalysisRunRecord,
    df: "Any",
    output_dir: str,
) -> CompetitorArtifactRecord:
    run_dir = os.path.join(output_dir, run.id)
    _ensure_dir(run_dir)
    grouped = df.groupby("competitorId")["vader_sentiment"].mean()
    categories = grouped.apply(_sentiment_category)
    ax = grouped.plot(kind="bar", color="#2c8ef4", figsize=(12, 6))
    ax.set_ylabel("VADER Sentiment Score")
    ax.set_title("Content Sentiment Analysis by Competitor")
    # highlight very positive in green
    for idx, (comp, score) in enumerate(grouped.items()):
        color = "#2c8ef4"
        if score >= 0.5:
            color = "#2ecc71"
            ax.patches[idx].set_color(color)
        label = categories.loc[comp]
        ax.text(
            idx,
            score + 0.01,
            f"{score:.2f}\n({label})",
            ha="center",
            va="bottom",
            fontweight="bold",
        )
    plt.tight_layout()
    plot_path = os.path.join(run_dir, f"{run.id}_sentiment_analysis.png")
    plt.savefig(plot_path, dpi=200)
    plt.close()

    return CompetitorArtifactRecord(
        id=f"artifact-{run.id}-sentiment-plot",
        projectId=run.projectId,
        humId=run.humId,
        runId=run.id,
        scenarioId="sentiment_overview",
        scenarioKind="competitor_analysis",
        routeTemplate="/competitors/sentiment",
        device="desktop",
        stateSlug="sentiment",
        capturedAt=_now_iso(),
        mimeType="image/png",
        rawKey=plot_path,
        brandedKey=None,
        thumbKey=None,
        diffKey=None,
        afterUrl=None,
        beforeUrl=None,
        thumbUrl=None,
        byteSize=None,
        width=None,
        height=None,
    )


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


def generate_markdown_report(
    run: CompetitorAnalysisRunRecord,
    summary: Any,
    df: "Any",
    output_dir: str,
) -> CompetitorArtifactRecord:
    run_dir = os.path.join(output_dir, run.id)
    _ensure_dir(run_dir)
    report_path = os.path.join(run_dir, f"{run.id}_report.md")
    # normalize summary to dict
    if is_dataclass(summary):
        summary = asdict(summary)
    comps = summary.get("competitors", [])
    meta = summary.get("_meta", {}) if isinstance(summary, dict) else {}
    overlap_map = meta.get("overlapByCompetitor", {})
    positioning_map = meta.get("positioningMap", {})
    cards = {c.get("competitorId"): c for c in meta.get("competitorCards", [])} if isinstance(meta.get("competitorCards", []), list) else {}
    keybert_keywords = meta.get("keybertKeywords", [])

    # Build sentiment categories and intent distributions from df if available
    intent_stats = {}
    sentiment_avg = {}
    if pd is not None and df is not None and hasattr(df, "groupby"):
        grouped = df.groupby("competitorId")
        sentiment_avg = grouped["vader_sentiment"].mean().to_dict()
        for comp_id, group in grouped:
            counts = group["intent"].value_counts(normalize=False)
            total = len(group)
            intent_stats[comp_id] = {
                intent: {"count": int(count), "percent": float(count) / total * 100 if total else 0.0}
                for intent, count in counts.items()
            }

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Competitor Analysis Report\n\n")
        for comp in comps:
            comp_id = comp.get("competitorId")
            name = comp.get("name")
            vvt = comp.get("valueVsTechnical", {})
            sentiment_bucket = comp.get("sentiment", {})
            mean_sent = sentiment_avg.get(comp_id, 0.0)
            category = _sentiment_category(mean_sent)

            f.write(f"## {name}\n")
            f.write(f"- Sentiment (avg): {mean_sent:.2f} ({category})\n")
            f.write(f"- Sentiment buckets: +{sentiment_bucket.get('positive',0)}, 0:{sentiment_bucket.get('neutral',0)}, -{sentiment_bucket.get('negative',0)}\n")
            f.write(f"- Technical keywords (sum): {vvt.get('technical', 0)}\n")
            f.write(f"- Value keywords (sum): {vvt.get('value', 0)}\n")
            f.write(f"- Top value props: {', '.join(comp.get('topProps', []))}\n")

            card = cards.get(comp_id, {})
            tvr = card.get("techValueRatio", {})
            if tvr:
                f.write(f"- Tech/Value mix: Technical {tvr.get('technical',0):.1f}%, Value {tvr.get('value',0):.1f}%\n")
            if card.get("topTechnicalConcepts"):
                f.write(f"- Top technical concepts: {', '.join(card.get('topTechnicalConcepts', []))}\n")

            if comp_id in overlap_map:
                overlap = overlap_map[comp_id]
                f.write(f"- Overlap vs your terms: {overlap.get('overlap',0):.2f}, Differentiation: {overlap.get('differentiationScore',0):.2f}\n")

            if comp_id in intent_stats:
                f.write("- Intent distribution:\n")
                for intent, stats in intent_stats[comp_id].items():
                    f.write(f"  - {intent}: {stats['count']} ({stats['percent']:.1f}%)\n")
            f.write("\n")

        # Positioning map (if available)
        if positioning_map:
            f.write("## Positioning Map (2D)\n")
            for cid, pos in positioning_map.items():
                f.write(f"- {cards.get(cid, {}).get('name', cid)}: x={pos.get('x'):.3f}, y={pos.get('y'):.3f}\n")
            f.write("\n")

        if keybert_keywords:
            f.write("## Key Phrase Highlights (KeyBERT)\n")
            f.write(", ".join(keybert_keywords))
            f.write("\n\n")

    return CompetitorArtifactRecord(
        id=f"artifact-{run.id}-markdown",
        projectId=run.projectId,
        humId=run.humId,
        runId=run.id,
        scenarioId="run_report",
        scenarioKind="competitor_analysis",
        routeTemplate="/competitors/report",
        device="desktop",
        stateSlug="summary",
        capturedAt=_now_iso(),
        mimeType="text/markdown",
        rawKey=report_path,
        brandedKey=None,
        thumbKey=None,
        diffKey=None,
        afterUrl=None,
        beforeUrl=None,
        thumbUrl=None,
        byteSize=None,
        width=None,
        height=None,
    )


def generate_per_competitor_csvs(
    run: CompetitorAnalysisRunRecord,
    df: "Any",
    output_dir: str,
) -> List[CompetitorArtifactRecord]:
    artifacts: List[CompetitorArtifactRecord] = []
    run_dir = os.path.join(output_dir, run.id)
    _ensure_dir(run_dir)
    if pd is None:
        return artifacts
    if "competitorId" not in df.columns:
        return artifacts
    for comp_id, group in df.groupby("competitorId"):
        name = group["competitor"].iloc[0] if "competitor" in group.columns else comp_id
        fname = f"{name}_content.csv".replace(" ", "_")
        path = os.path.join(run_dir, fname)
        group.to_csv(path, index=False)
        artifacts.append(
            CompetitorArtifactRecord(
                id=f"artifact-{run.id}-{comp_id}-csv",
                projectId=run.projectId,
                humId=run.humId,
                runId=run.id,
                scenarioId="run_report",
                scenarioKind="competitor_analysis",
                routeTemplate="/competitors/report",
                device="desktop",
                stateSlug=comp_id,
                capturedAt=_now_iso(),
                mimeType="text/csv",
                rawKey=path,
                brandedKey=None,
                thumbKey=None,
                diffKey=None,
                afterUrl=None,
                beforeUrl=None,
                thumbUrl=None,
                byteSize=None,
                width=None,
                height=None,
            )
        )
    return artifacts


def generate_all_reports(
    run: CompetitorAnalysisRunRecord,
    df: "Any",
    summary: Dict[str, Any],
    output_dir: str,
) -> List[CompetitorArtifactRecord]:
    artifacts: List[CompetitorArtifactRecord] = []
    artifacts.extend(generate_csv_and_excel(run, df, output_dir))
    artifacts.extend(generate_per_competitor_csvs(run, df, output_dir))
    artifacts.append(generate_keyword_distribution_plot(run, df, output_dir))
    artifacts.append(generate_sentiment_plot(run, df, output_dir))
    artifacts.append(generate_markdown_report(run, summary, df, output_dir))
    return artifacts
