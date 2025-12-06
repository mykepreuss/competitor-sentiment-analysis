"""
Default term lists and settings helpers.
"""

TECHNICAL_TERMS_DEFAULT = [
    "ai", "ml", "data", "model", "algorithm", "geophysics", "sensor", "api",
    "pipeline", "cloud", "inference", "training", "dataset", "analytics",
    "integration", "sdk", "platform", "inversion", "processing", "workflow",
]

VALUE_TERMS_DEFAULT = [
    "efficiency", "productivity", "optimization", "cost-effective", "accuracy",
    "reliable", "innovative", "advanced", "powerful", "intelligent", "smart",
    "automated", "streamlined", "integrated", "comprehensive", "scalable",
    "flexible", "robust", "precise", "fast", "quick", "effective", "leading",
    "state-of-the-art", "transformative", "cutting-edge",
]


def apply_default_terms(settings: dict) -> dict:
    """
    Ensure technical_terms and value_terms are populated if missing.
    """
    settings = settings or {}
    settings.setdefault("technical_terms", TECHNICAL_TERMS_DEFAULT)
    settings.setdefault("value_terms", VALUE_TERMS_DEFAULT)
    return settings


def apply_runtime_defaults(settings: dict, runtime: dict) -> dict:
    """
    Merge runtime (env) defaults into a settings dict without overwriting
    caller-provided values.
    """
    merged = apply_default_terms(settings or {})
    merged.setdefault("output_dir", runtime.get("output_dir"))
    merged.setdefault("scraper_timeout", runtime.get("scraper_timeout"))
    merged.setdefault("scraper_retries", runtime.get("scraper_retries"))
    merged.setdefault("scraper_delay", runtime.get("scraper_delay"))
    merged.setdefault("scraper_max_pages", runtime.get("scraper_max_pages"))
    merged.setdefault("scraper_max_elements", runtime.get("scraper_max_elements"))
    merged.setdefault("user_agent", runtime.get("user_agent"))
    merged.setdefault("scraper_backend", runtime.get("scraper_backend", "requests"))
    merged.setdefault("use_embeddings", runtime.get("use_embeddings", False))
    merged.setdefault("use_keybert", runtime.get("use_keybert", False))
    merged.setdefault("embedding_model", runtime.get("embedding_model", "all-MiniLM-L6-v2"))
    merged.setdefault("keybert_model", runtime.get("keybert_model", "all-MiniLM-L6-v2"))
    merged.setdefault("your_terms", runtime.get("your_terms", ""))
    # normalize your_terms to list
    if isinstance(merged["your_terms"], str):
        merged["your_terms"] = [t.strip() for t in merged["your_terms"].split(",") if t.strip()]
    return merged
