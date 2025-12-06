"""
FastAPI surface for the Competitor Analysis Engine.

Endpoints (internal/prototype):
- POST /internal/competitor-analysis/runs        -> start run (sync optional)
- GET  /internal/competitor-analysis/runs/{id}   -> get run
- GET  /internal/competitor-analysis/runs/{id}/artifacts -> list artifacts
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:  # pragma: no cover - optional dependency
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError as exc:  # pragma: no cover
    raise ImportError("fastapi and pydantic are required for competitor_analysis.api") from exc

from fastapi import Header, Depends

from . import engine, runtime
from .models import CompetitorAnalysisRunRecord, CompetitorArtifactRecord


class CompetitorInput(BaseModel):
    id: str
    name: str
    baseUrl: str
    priorityPages: List[str]


class StartRunRequest(BaseModel):
    projectId: str
    humId: str
    name: Optional[str] = None
    seriesBaseUrl: str
    competitors: List[CompetitorInput]
    settings: Optional[Dict[str, Any]] = None
    sync: bool = False


def auth_dependency(x_api_key: Optional[str] = Header(default=None)):
    expected = runtime.get_env_settings().get("api_key")
    if expected:
        if x_api_key != expected:
            raise HTTPException(status_code=401, detail="Unauthorized")
    return True


def create_app() -> FastAPI:
    app = FastAPI(title="Competitor Analysis Engine", version="0.1.0")

    @app.post("/internal/competitor-analysis/runs", response_model=Dict[str, Any], dependencies=[Depends(auth_dependency)])
    def start_run(req: StartRunRequest):
        comp_dicts = [c.dict() for c in req.competitors]
        if req.sync:
            run = engine.run_analysis_sync(
                project_id=req.projectId,
                hum_id=req.humId,
                name=req.name,
                series_base_url=req.seriesBaseUrl,
                competitors=comp_dicts,
                settings=req.settings,
            )
        else:
            run = engine.start_analysis_run_async(
                project_id=req.projectId,
                hum_id=req.humId,
                name=req.name,
                series_base_url=req.seriesBaseUrl,
                competitors=comp_dicts,
                settings=req.settings,
            )
        return {"run": run}

    @app.get("/internal/competitor-analysis/runs", response_model=Dict[str, Any], dependencies=[Depends(auth_dependency)])
    def list_runs(projectId: Optional[str] = None, humId: Optional[str] = None):
        runs = engine.list_analysis_runs(project_id=projectId, hum_id=humId)
        return {"runs": runs}

    @app.get("/internal/competitor-analysis/runs/{run_id}", response_model=Dict[str, Any], dependencies=[Depends(auth_dependency)])
    def get_run(run_id: str):
        run = engine.get_analysis_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return {"run": run}

    @app.get("/internal/competitor-analysis/runs/{run_id}/artifacts", response_model=Dict[str, Any], dependencies=[Depends(auth_dependency)])
    def get_artifacts(run_id: str):
        artifacts = engine.list_artifacts(run_id)
        return {"artifacts": artifacts}

    @app.get("/internal/competitor-analysis/runs/{run_id}/cards", response_model=Dict[str, Any], dependencies=[Depends(auth_dependency)])
    def get_cards(run_id: str):
        run = engine.get_analysis_run(run_id)
        if not run or not run.summaryJson:
            raise HTTPException(status_code=404, detail="Run not found or summary missing")
        cards = run.summaryJson._meta.get("competitorCards", [])
        return {"competitorCards": cards}

    @app.get("/internal/competitor-analysis/runs/{run_id}/landscape", response_model=Dict[str, Any], dependencies=[Depends(auth_dependency)])
    def get_landscape(run_id: str):
        run = engine.get_analysis_run(run_id)
        if not run or not run.summaryJson:
            raise HTTPException(status_code=404, detail="Run not found or summary missing")
        meta = run.summaryJson._meta or {}
        return {
            "competitorCards": meta.get("competitorCards", []),
            "positioningMap": meta.get("positioningMap", {}),
            "overlapByCompetitor": meta.get("overlapByCompetitor", {}),
            "trendsByCompetitor": meta.get("trendsByCompetitor", {}),
            "summary": run.summaryJson,
        }

    return app


# Convenience for `uvicorn competitor_analysis.api:app`
app = create_app()
