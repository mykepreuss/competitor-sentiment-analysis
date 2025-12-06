"""
Optional embedding utilities using sentence-transformers.
"""

from __future__ import annotations

from typing import Dict, List


def _load_model(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def embed_texts(texts: List[str], model_name: str) -> List[List[float]]:
    model = _load_model(model_name)
    return model.encode(texts, convert_to_numpy=False, show_progress_bar=False)


def embed_competitors(df, model_name: str) -> Dict[str, List[float]]:
    """
    Aggregate cleaned_text per competitor and embed.
    """
    embeddings = {}
    from sentence_transformers import util

    model = _load_model(model_name)
    for competitor_id, group in df.groupby("competitorId"):
        text = " ".join(group.get("cleaned_text", "")).strip()
        if not text:
            continue
        emb = model.encode(text, convert_to_numpy=False, show_progress_bar=False)
        embeddings[competitor_id] = emb
    return embeddings


def position_competitors(embeddings: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
    """
    Reduce embeddings to 2D via PCA. Returns {competitorId: {x, y}}.
    """
    if not embeddings or len(embeddings) < 2:
        return {}
    import numpy as np
    from sklearn.decomposition import PCA

    ids = list(embeddings.keys())
    mat = np.vstack([embeddings[cid] for cid in ids])
    coords = PCA(n_components=2).fit_transform(mat)
    return {cid: {"x": float(x), "y": float(y)} for cid, (x, y) in zip(ids, coords)}
