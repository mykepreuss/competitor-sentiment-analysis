"""
Lightweight dispatcher for the prototype.

Uses Python threads to run scrape -> analysis -> report jobs sequentially for a
given run. This is intentionally simple for local/dev; swap with Celery/RQ in
production.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List

from . import jobs


def start_pipeline_thread(payload: Dict[str, Any]) -> threading.Thread:
    """
    Spawn a background thread to execute scrape -> analysis -> report in order.
    Returns the thread object (already started).
    """
    def _runner():
        jobs.run_scrape_job(payload)
        jobs.run_analysis_job(payload)
        jobs.run_report_job(payload)

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    return t

