"""
File-backed store (JSON) with in-memory cache for the prototype.

Uses a single JSON file to persist runs, page contents, analysis results, and
artifacts. This keeps durability without requiring a full database.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import (
    CompetitorAnalysisRunRecord,
    CompetitorAnalysisSummary,
    CompetitorArtifactRecord,
    CompetitorSummary,
    SentimentBucket,
    TopicSummary,
)

STORE_PATH = os.environ.get("COMPETITOR_STORE_PATH", "competitor_content/store.json")

# In-memory "tables"
_runs: Dict[str, CompetitorAnalysisRunRecord] = {}
_page_contents: Dict[str, List[Dict[str, Any]]] = {}
_analysis_results: Dict[str, List[Dict[str, Any]]] = {}
_artifacts: Dict[str, List[CompetitorArtifactRecord]] = {}


# ---------------------- Serialization helpers ---------------------------------
def _deserialize_sentiment_bucket(data: Dict[str, Any]) -> SentimentBucket:
    return SentimentBucket(**data)


def _deserialize_competitor_summary(data: Dict[str, Any]) -> CompetitorSummary:
    data = dict(data)
    data["sentiment"] = _deserialize_sentiment_bucket(data["sentiment"])
    return CompetitorSummary(**data)


def _deserialize_topic_summary(data: Dict[str, Any]) -> TopicSummary:
    return TopicSummary(**data)


def _deserialize_summary(data: Dict[str, Any]) -> CompetitorAnalysisSummary:
    comps = [_deserialize_competitor_summary(c) for c in data.get("competitors", [])]
    topics = [_deserialize_topic_summary(t) for t in data.get("topics", [])]
    sentiment_by = {
        cid: _deserialize_sentiment_bucket(b) for cid, b in data.get("sentimentByCompetitor", {}).items()
    }
    return CompetitorAnalysisSummary(
        competitors=comps,
        topics=topics,
        sentimentByCompetitor=sentiment_by,
        valueVsTechnicalByCompetitor=data.get("valueVsTechnicalByCompetitor", {}),
        topValueProps=data.get("topValueProps", []),
        topKeywords=data.get("topKeywords", []),
        _meta=data.get("_meta", {}),
    )


def _deserialize_run(data: Dict[str, Any]) -> CompetitorAnalysisRunRecord:
    summary = data.get("summaryJson")
    if summary:
        data["summaryJson"] = _deserialize_summary(summary)
    return CompetitorAnalysisRunRecord(**data)


def _deserialize_artifact(data: Dict[str, Any]) -> CompetitorArtifactRecord:
    return CompetitorArtifactRecord(**data)


def _safe_read() -> Dict[str, Any]:
    path = Path(STORE_PATH)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _safe_write(payload: Dict[str, Any]) -> None:
    path = Path(STORE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


def _persist() -> None:
    payload = {
        "runs": {rid: asdict(run) for rid, run in _runs.items()},
        "page_contents": _page_contents,
        "analysis_results": _analysis_results,
        "artifacts": {rid: [asdict(a) for a in arts] for rid, arts in _artifacts.items()},
    }
    _safe_write(payload)


def _load_from_disk() -> None:
    data = _safe_read()
    runs_raw = data.get("runs", {})
    _runs.update({rid: _deserialize_run(r) for rid, r in runs_raw.items()})
    _page_contents.update(data.get("page_contents", {}))
    _analysis_results.update(data.get("analysis_results", {}))
    artifacts_raw = data.get("artifacts", {})
    _artifacts.update({rid: [_deserialize_artifact(a) for a in arts] for rid, arts in artifacts_raw.items()})


# Load existing state at import time
_load_from_disk()


# ---------------------- Public API --------------------------------------------
def create_run(record: CompetitorAnalysisRunRecord) -> CompetitorAnalysisRunRecord:
    _runs[record.id] = record
    _persist()
    return record


def update_run(run_id: str, *, fields: Dict[str, Any]) -> None:
    if run_id not in _runs:
        return
    current = _runs[run_id]
    for key, val in fields.items():
        setattr(current, key, val)
    _runs[run_id] = current
    _persist()


def get_run(run_id: str) -> Optional[CompetitorAnalysisRunRecord]:
    return _runs.get(run_id)


def list_runs(project_id: Optional[str] = None, hum_id: Optional[str] = None) -> List[CompetitorAnalysisRunRecord]:
    runs = list(_runs.values())
    if project_id is not None:
        runs = [r for r in runs if r.projectId == project_id]
    if hum_id is not None:
        runs = [r for r in runs if r.humId == hum_id]
    # sort by startedAt if available
    runs.sort(key=lambda r: r.startedAt or "", reverse=False)
    return runs


def save_page_contents(run_id: str, page_contents: List[Dict[str, Any]]) -> None:
    _page_contents[run_id] = page_contents
    _persist()


def load_page_contents(run_id: str) -> List[Dict[str, Any]]:
    return _page_contents.get(run_id, [])


def save_analysis_results(run_id: str, results: List[Dict[str, Any]]) -> None:
    _analysis_results[run_id] = results
    _persist()


def load_analysis_results(run_id: str) -> List[Dict[str, Any]]:
    return _analysis_results.get(run_id, [])


def save_artifacts(run_id: str, artifacts: List[CompetitorArtifactRecord]) -> None:
    _artifacts[run_id] = artifacts
    _persist()


def load_artifacts(run_id: str) -> List[CompetitorArtifactRecord]:
    return _artifacts.get(run_id, [])
