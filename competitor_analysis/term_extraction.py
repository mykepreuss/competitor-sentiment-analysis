"""
Dynamic term extraction based on discovered content.

We derive "technical" and "value" term lists from the scraped corpus using POS
tags. Technical terms are the most frequent nouns/proper nouns; value terms are
the most frequent adjectives/adverbs/verbs. Falls back to simple frequency if
tagger resources are unavailable.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, List, Tuple

import nltk

from .stopwords import CUSTOM_STOP_WORDS
from .analysis import clean_text


def _ensure_tagger():
    try:
        nltk.data.find("taggers/averaged_perceptron_tagger")
    except LookupError:
        try:
            nltk.download("averaged_perceptron_tagger", quiet=True)
        except Exception:
            return False
    return True


def derive_dynamic_terms(page_contents: List[Dict], top_n: int = 50) -> Tuple[List[str], List[str]]:
    """
    Returns (technical_terms, value_terms) dynamically from corpus.
    """
    texts: List[str] = []
    for row in page_contents:
        txt = row.get("rawText") or row.get("text") or ""
        if txt:
            texts.append(clean_text(txt))
    tokens: List[str] = []
    for t in texts:
        tokens.extend([w for w in t.split() if w not in CUSTOM_STOP_WORDS])

    if not tokens:
        return [], []

    if _ensure_tagger():
        try:
            tagged = nltk.pos_tag(tokens)
            noun_tags = {"NN", "NNS", "NNP", "NNPS"}
            value_tags = {"JJ", "JJR", "JJS", "RB", "RBR", "RBS", "VB", "VBD", "VBG", "VBN", "VBP", "VBZ"}
            tech_counts = Counter([w for w, tag in tagged if tag in noun_tags])
            value_counts = Counter([w for w, tag in tagged if tag in value_tags])
            technical_terms = [w for w, _ in tech_counts.most_common(top_n)]
            value_terms = [w for w, _ in value_counts.most_common(top_n)]
            return technical_terms, value_terms
        except Exception:
            pass

    # Fallback: simple frequency split (first half technical, second half value)
    freq = Counter(tokens).most_common(top_n * 2)
    midpoint = len(freq) // 2 or 1
    technical_terms = [w for w, _ in freq[:midpoint]]
    value_terms = [w for w, _ in freq[midpoint:midpoint + top_n]]
    return technical_terms, value_terms

