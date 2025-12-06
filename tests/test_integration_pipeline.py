import json
import os
from pathlib import Path

import pandas as pd

from competitor_analysis.engine import run_analysis_sync


def test_run_analysis_sync_creates_artifacts_and_summary(tmp_path, monkeypatch):
    # Arrange a tiny "site" using data: URLs (avoid network)
    # We'll monkeypatch scraper.requests.get to return this HTML
    html = """
    <html><head><title>Test</title><meta name="description" content="desc"/></head>
    <body>
      <h1>AI efficiency</h1>
      <p>data model pipeline efficiency</p>
    </body>
    </html>
    """

    class DummyResp:
        status_code = 200

        def __init__(self, text):
            self.text = text

    def fake_get(url, headers=None, timeout=None):
        return DummyResp(html)

    import competitor_analysis.scraper as scraper

    monkeypatch.setattr(scraper.requests, "get", fake_get)
    # Disable robots.txt fetch
    monkeypatch.setattr(scraper.robotparser, "RobotFileParser", lambda: None)

    output_dir = tmp_path / "out"

    competitors = [
        {"id": "c1", "name": "C1", "baseUrl": "https://example.com", "priorityPages": ["/"]},
    ]

    run = run_analysis_sync(
        project_id="ws1",
        hum_id="hum1",
        name="test",
        series_base_url="https://yourapp.com",
        competitors=competitors,
        settings={"output_dir": str(output_dir)},
    )

    # Assert run completed
    assert run.status == "completed"
    assert run.summaryJson is not None
    summary = run.summaryJson
    assert summary.topKeywords  # not empty

    # Artifacts exist on disk
    run_dir = output_dir / run.id
    assert (run_dir / f"{run.id}_analysis.csv").exists()
    assert (run_dir / f"{run.id}_analysis.xlsx").exists()
    assert (run_dir / f"{run.id}_keyword_distribution.png").exists()
    assert (run_dir / f"{run.id}_report.md").exists()

