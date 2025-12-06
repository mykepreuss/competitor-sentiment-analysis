"""
Minimal CLI wrapper for local runs.

Usage:
    python -m competitor_analysis.cli --project ws1 --hum hum1 --name demo --base https://example.com \\
        --competitors competitors_config.json --output competitor_content
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from .engine import run_analysis_sync
from .runtime import get_env_settings
from .settings import apply_runtime_defaults


def _load_competitors(path: str) -> List[Dict[str, Any]]:
    data = json.loads(Path(path).read_text())
    return data["competitors"] if isinstance(data, dict) and "competitors" in data else data


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run competitor analysis synchronously (dev/local).")
    parser.add_argument("--project", required=True, help="projectId / workspace id")
    parser.add_argument("--hum", required=True, help="humId / stable container id")
    parser.add_argument("--name", default=None, help="optional run name")
    parser.add_argument("--base", required=True, help="series_base_url (your product URL)")
    parser.add_argument("--competitors", required=True, help="path to competitors_config.json")
    parser.add_argument("--output", default="competitor_content", help="output directory for artifacts")
    parser.add_argument("--tech-terms", default="", help="comma-separated technical terms")
    parser.add_argument("--value-terms", default="", help="comma-separated value terms")

    args = parser.parse_args(argv)

    competitors = _load_competitors(args.competitors)
    env_settings = get_env_settings()
    settings = apply_runtime_defaults(
        {
            "output_dir": args.output,
            "technical_terms": [t.strip() for t in args.tech_terms.split(",") if t.strip()],
            "value_terms": [t.strip() for t in args.value_terms.split(",") if t.strip()],
        },
        env_settings,
    )

    run = run_analysis_sync(
        project_id=args.project,
        hum_id=args.hum,
        name=args.name,
        series_base_url=args.base,
        competitors=competitors,
        settings=settings,
    )
    print(json.dumps({"runId": run.id, "status": run.status, "summary": run.summaryJson}, default=str, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
