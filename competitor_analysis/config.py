"""
Config helpers for competitor definitions.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from .models import CompetitorConfig


REQUIRED_FIELDS = {"id", "name", "baseUrl", "priorityPages"}


def _validate_competitor(raw: Dict[str, Any]) -> CompetitorConfig:
    missing = REQUIRED_FIELDS - set(raw.keys())
    if missing:
        raise ValueError(f"Missing required fields {sorted(missing)} in competitor config: {raw}")
    return CompetitorConfig(
        id=str(raw["id"]),
        name=str(raw["name"]),
        baseUrl=str(raw["baseUrl"]),
        priorityPages=list(raw.get("priorityPages", [])),
    )


def load_competitor_configs(config: Dict[str, Any]) -> List[CompetitorConfig]:
    """
    Validate and normalize competitor configs from a raw JSON payload.
    Expected shape: { "competitors": [ {id, name, baseUrl, priorityPages[]} ] }
    """
    competitors = config.get("competitors", [])
    if not isinstance(competitors, list):
        raise ValueError("config['competitors'] must be a list")
    return [_validate_competitor(raw) for raw in competitors]


def load_competitor_configs_from_file(path: str) -> List[CompetitorConfig]:
    """
    Convenience for local/testing: parse competitors_config.json into a list.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return load_competitor_configs(data)

