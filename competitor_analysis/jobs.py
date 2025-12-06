"""
Background job entrypoints.

These functions are meant to be called by a worker system (Celery/RQ/etc.) with
JSON payloads. For now they run synchronously and update the in-memory store.
"""

from __future__ import annotations

import traceback
from datetime import datetime
from typing import Any, Dict, List

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None  # type: ignore

import logging

from . import analysis, config, reports, scraper, store, summary, settings as default_settings, runtime
from .term_extraction import derive_dynamic_terms
from .models import CompetitorAnalysisRunRecord


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


# Simplified logger (avoid runId/humId placeholders for third-party logs)
logger = logging.getLogger("competitor_analysis")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def run_scrape_job(payload: Dict[str, Any]) -> None:
    run_id = payload["runId"]
    competitors_raw: List[Dict[str, Any]] = payload.get("competitors", [])
    rt = runtime.get_env_settings()
    settings = default_settings.apply_runtime_defaults(payload.get("settings", {}) or {}, rt)

    run = store.get_run(run_id)
    if not run:
        return

    start_time = _now_iso()
    store.update_run(run_id, fields={"status": "running", "phase": "scrape", "startedAt": start_time})

    try:
        competitors = config.load_competitor_configs({"competitors": competitors_raw})
        content_rows = scraper.scrape_all_competitors(
            competitors,
            timeout_seconds=settings.get("scraper_timeout", 20),
            max_retries=settings.get("scraper_retries", 2),
            delay_seconds=settings.get("scraper_delay", 1.0),
            max_pages=settings.get("scraper_max_pages", 50),
            max_elements=settings.get("scraper_max_elements", 2000),
            user_agent=settings.get("user_agent", "CompetitorAnalysisBot/0.1"),
            backend=settings.get("scraper_backend", "requests"),
        )
        store.save_page_contents(run_id, content_rows)
        store.update_run(run_id, fields={"phase": "analysis"})
    except Exception:
        store.update_run(run_id, fields={"status": "failed", "phase": "scrape", "finishedAt": _now_iso()})
        traceback.print_exc()


def run_analysis_job(payload: Dict[str, Any]) -> None:
    run_id = payload["runId"]
    competitors_raw: List[Dict[str, Any]] = payload.get("competitors", [])
    rt = runtime.get_env_settings()
    settings = default_settings.apply_runtime_defaults(payload.get("settings", {}) or {}, rt)
    technical_terms = settings.get("technical_terms", [])
    value_terms = settings.get("value_terms", [])

    run = store.get_run(run_id)
    if not run:
        return

    # Load previous run for trends
    prev_df = None
    runs_same_hum = store.list_runs(project_id=run.projectId, hum_id=run.humId)
    prev_ids = [r.id for r in runs_same_hum if r.id != run_id]
    if prev_ids:
        prev_run_id = prev_ids[-1]
        prev_results = store.load_analysis_results(prev_run_id)
        if prev_results and pd is not None:
            prev_df = pd.DataFrame(prev_results)

    start_time = _now_iso()
    try:
        page_contents = store.load_page_contents(run_id)

        # derive dynamic terms from corpus if not provided
        dyn_tech, dyn_value = derive_dynamic_terms(page_contents)
        if dyn_tech:
            technical_terms = dyn_tech
        if dyn_value:
            value_terms = dyn_value
        # reflect back into settings/runConfig for summary/meta
        settings["technical_terms"] = technical_terms
        settings["value_terms"] = value_terms
        analyzed = analysis.analyze_page_contents(
            page_contents, technical_terms=technical_terms, value_terms=value_terms
        )
        store.save_analysis_results(run_id, analyzed)

        if pd is None:
            raise ImportError("pandas is required for analysis job")

        df = pd.DataFrame(analyzed)
        # Ensure competitorId column exists
        if "competitorId" not in df.columns:
            if "competitor" in df.columns:
                df = df.rename(columns={"competitor": "competitorId"})
            else:
                df["competitorId"] = df.get("competitor_name", "unknown")

        competitors = config.load_competitor_configs({"competitors": competitors_raw})
        summary_json = summary.build_summary_from_dataframe(df, competitors, settings, previous_df=prev_df)
        # record timing/meta
        meta = summary_json._meta or {}
        meta["analysisStartedAt"] = start_time
        meta["analysisFinishedAt"] = _now_iso()
        summary_json._meta = meta
        store.update_run(
            run_id,
            fields={
                "summaryJson": summary_json,
                "phase": "report",
            },
        )
    except Exception:
        store.update_run(run_id, fields={"status": "failed", "phase": "analysis", "finishedAt": _now_iso()})
        traceback.print_exc()


def run_report_job(payload: Dict[str, Any]) -> None:
    run_id = payload["runId"]
    rt = runtime.get_env_settings()
    settings = default_settings.apply_runtime_defaults(payload.get("settings", {}) or {}, rt)
    output_dir = settings.get("output_dir", "competitor_content")

    run = store.get_run(run_id)
    if not run:
        return

    try:
        analysis_results = store.load_analysis_results(run_id)
        if pd is None:
            raise ImportError("pandas is required for report job")
        df = pd.DataFrame(analysis_results)

        summary_json = run.summaryJson
        artifacts = reports.generate_all_reports(run, df, summary_json, output_dir, settings=settings)
        store.save_artifacts(run_id, artifacts)
        store.update_run(
            run_id,
            fields={
                "status": "completed",
                "approvalStatus": "approved",
                "phase": "report",
                "finishedAt": _now_iso(),
            },
        )
    except Exception:
        store.update_run(run_id, fields={"status": "failed", "phase": "report", "finishedAt": _now_iso()})
        traceback.print_exc()
