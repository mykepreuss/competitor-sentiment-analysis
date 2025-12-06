import pandas as pd

from competitor_analysis.summary import build_summary_from_dataframe
from competitor_analysis.models import CompetitorConfig


def test_build_summary_basic_sentiment_and_keywords():
    data = [
        {"competitorId": "c1", "vader_sentiment": 0.1, "technical_keywords": 2, "value_keywords": 1, "cleaned_text": "ai data efficiency"},
        {"competitorId": "c1", "vader_sentiment": -0.2, "technical_keywords": 1, "value_keywords": 0, "cleaned_text": "model processing"},
        {"competitorId": "c2", "vader_sentiment": 0.0, "technical_keywords": 0, "value_keywords": 2, "cleaned_text": "efficient scalable reliable"},
    ]
    df = pd.DataFrame(data)
    comps = [
        CompetitorConfig(id="c1", name="C1", baseUrl="https://c1.com", priorityPages=[]),
        CompetitorConfig(id="c2", name="C2", baseUrl="https://c2.com", priorityPages=[]),
    ]
    summary = build_summary_from_dataframe(df, comps, settings={"engineVersion": "test"})

    assert summary.sentimentByCompetitor["c1"].positive == 1
    assert summary.sentimentByCompetitor["c1"].negative == 1
    assert summary.valueVsTechnicalByCompetitor["c1"]["technical"] == 3
    assert summary.valueVsTechnicalByCompetitor["c2"]["value"] == 2
    assert len(summary.topKeywords) > 0

