"""
Optional keyword/keyphrase extraction using KeyBERT.
"""

from __future__ import annotations

from typing import List, Tuple


def extract_keybert_phrases(texts: List[str], model_name: str = "all-MiniLM-L6-v2", top_n: int = 5) -> List[str]:
    try:
        from keybert import KeyBERT
    except ImportError:
        return []

    try:
        kw_model = KeyBERT(model=model_name)
        phrases: List[Tuple[str, float]] = kw_model.extract_keywords(
            texts,
            keyphrase_ngram_range=(1, 2),
            stop_words="english",
            use_maxsum=True,
            nr_candidates=20,
            top_n=top_n,
        )
        return [p for p, _ in phrases]
    except Exception:
        return []

