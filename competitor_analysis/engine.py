"""
Public engine API for the Competitor Analysis Engine.

This layer is what the HTTP API (or CLI) should call. It delegates persistence
to `store` and leaves worker dispatch to the caller (or to a future task
queue integration).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .models import (
    ApprovalStatus,
    CompetitorAnalysisRunRecord,
    CompetitorArtifactRecord,
    CompetitorConfig,
)
from . import store, jobs, dispatcher


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def start_analysis_run(
    *,
    project_id: str,
    hum_id: str,
    name: Optional[str],
    series_base_url: str,
    competitors: List[Dict[str, Any]],
    settings: Optional[Dict[str, Any]] = None,
) -> CompetitorAnalysisRunRecord:
    """
    Create an AnalysisRun, persist it, and return the initial record.
    Actual job dispatch is left to the caller or a worker integration.
    """
    run_id = f"ar_{uuid4().hex}"
    started_at = _now_iso()
    run = CompetitorAnalysisRunRecord(
        id=run_id,
        projectId=project_id,
        humId=hum_id,
        url=series_base_url,
        devices=["desktop"],
        deviceMatrix=["desktop"],
        flowId="=competitor-analysis:v1",
        status="queued",
        approvalStatus="pending",
        startedAt=started_at,
        finishedAt=None,
        name=name,
        seriesBaseUrl=series_base_url,
    )
    store.create_run(run)
    return run


def get_analysis_run(run_id: str) -> Optional[CompetitorAnalysisRunRecord]:
    return store.get_run(run_id)


def list_analysis_runs(
    *,
    project_id: Optional[str] = None,
    hum_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[CompetitorAnalysisRunRecord]:
    runs = store.list_runs(project_id=project_id, hum_id=hum_id)
    return runs[offset : offset + limit]


def list_artifacts(run_id: str) -> List[CompetitorArtifactRecord]:
    return store.load_artifacts(run_id)


def run_analysis_sync(
    *,
    project_id: str,
    hum_id: str,
    name: Optional[str],
    series_base_url: str,
    competitors: List[Dict[str, Any]],
    settings: Optional[Dict[str, Any]] = None,
) -> CompetitorAnalysisRunRecord:
    """
    Convenience synchronous pipeline runner for local/dev.
    - Creates a run
    - Executes scrape -> analysis -> report jobs in-process
    - Returns the final run record
    """
    run = start_analysis_run(
        project_id=project_id,
        hum_id=hum_id,
        name=name,
        series_base_url=series_base_url,
        competitors=competitors,
        settings=settings,
    )
    payload = {
        "runId": run.id,
        "projectId": project_id,
        "humId": hum_id,
        "competitors": competitors,
        "settings": settings or {},
    }
    jobs.run_scrape_job(payload)
    jobs.run_analysis_job(payload)
    jobs.run_report_job(payload)
    final = store.get_run(run.id)
    return final or run


def start_analysis_run_async(
    *,
    project_id: str,
    hum_id: str,
    name: Optional[str],
    series_base_url: str,
    competitors: List[Dict[str, Any]],
    settings: Optional[Dict[str, Any]] = None,
) -> CompetitorAnalysisRunRecord:
    """
    Create a run and dispatch background thread to execute the pipeline.
    """
    run = start_analysis_run(
        project_id=project_id,
        hum_id=hum_id,
        name=name,
        series_base_url=series_base_url,
        competitors=competitors,
        settings=settings,
    )
    payload = {
        "runId": run.id,
        "projectId": project_id,
        "humId": hum_id,
        "competitors": competitors,
        "settings": settings or {},
    }
    dispatcher.start_pipeline_thread(payload)
    return run
