"""
Runtime configuration helpers (env-driven defaults).
"""

import os
from typing import Any, Dict


def get_env_settings() -> Dict[str, Any]:
    return {
        "store_path": os.environ.get("COMPETITOR_STORE_PATH", "competitor_content/store.json"),
        "output_dir": os.environ.get("COMPETITOR_OUTPUT_DIR", "competitor_content"),
        "api_key": os.environ.get("COMPETITOR_API_KEY"),  # optional shared-secret
        "user_agent": os.environ.get("COMPETITOR_USER_AGENT", "CompetitorAnalysisBot/0.1"),
        "scraper_timeout": float(os.environ.get("COMPETITOR_SCRAPER_TIMEOUT", "20")),
        "scraper_retries": int(os.environ.get("COMPETITOR_SCRAPER_RETRIES", "2")),
        "scraper_delay": float(os.environ.get("COMPETITOR_SCRAPER_DELAY", "1.0")),
        "scraper_max_pages": int(os.environ.get("COMPETITOR_SCRAPER_MAX_PAGES", "50")),
        "scraper_max_elements": int(os.environ.get("COMPETITOR_SCRAPER_MAX_ELEMENTS", "2000")),
        "scraper_backend": os.environ.get("COMPETITOR_SCRAPER_BACKEND", "requests"),  # requests | playwright
        "use_embeddings": os.environ.get("COMPETITOR_USE_EMBEDDINGS", "true").lower() == "true",
        "use_keybert": os.environ.get("COMPETITOR_USE_KEYBERT", "false").lower() == "true",
        "embedding_model": os.environ.get("COMPETITOR_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        "keybert_model": os.environ.get("COMPETITOR_KEYBERT_MODEL", "all-MiniLM-L6-v2"),
        "your_terms": os.environ.get("COMPETITOR_YOUR_TERMS", ""),
        "compute_trends": os.environ.get("COMPETITOR_COMPUTE_TRENDS", "true").lower() == "true",
        "use_gpt": os.environ.get("COMPETITOR_USE_GPT", "false").lower() == "true",
        "openai_api_key": os.environ.get("OPENAI_API_KEY"),
    }
