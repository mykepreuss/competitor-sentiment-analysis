from competitor_analysis.summary import build_summary_from_dataframe
from competitor_analysis.models import CompetitorConfig
import pandas as pd


def test_competitor_cards_present_and_fields():
    df = pd.DataFrame(
        [
            {"competitorId": "c1", "vader_sentiment": 0.2, "technical_keywords": 2, "value_keywords": 1, "cleaned_text": "ai data efficiency"},
            {"competitorId": "c1", "vader_sentiment": -0.3, "technical_keywords": 1, "value_keywords": 2, "cleaned_text": "model automation efficiency"},
        ]
    )
    comps = [CompetitorConfig(id="c1", name="C1", baseUrl="https://c1.com", priorityPages=[])]
    summary = build_summary_from_dataframe(df, comps, settings={"engineVersion": "test", "technical_terms": ["ai", "data", "model"], "value_terms": ["efficiency", "automation"]})
    cards = summary._meta.get("competitorCards", [])
    assert len(cards) == 1
    card = cards[0]
    assert "sentimentScore" in card
    assert "sentimentCategory" in card
    assert "techValueRatio" in card
    assert "topValueProps" in card
    assert "topTechnicalConcepts" in card
    assert card["sentimentCategory"] in {"Very Positive", "Positive", "Neutral", "Negative", "Very Negative"}
