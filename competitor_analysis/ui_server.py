"""
Minimal FastAPI views to serve a simple HTML landscape and trends view.

This is intentionally basic: returns JSON the frontend (HTMX/React) can consume.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from .api import create_app
from .engine import get_analysis_run
from .store import load_artifacts
import plotly.graph_objects as go
import plotly.io as pio

base_app = create_app()
app = FastAPI()

# Mount API under /internal
app.mount("/internal", base_app)


@app.get("/landscape/{run_id}", response_class=HTMLResponse)
def landscape_page(run_id: str):
    run = get_analysis_run(run_id)
    if not run or not run.summaryJson:
        raise HTTPException(status_code=404, detail="Run not found")
    meta = run.summaryJson._meta or {}
    cards = meta.get("competitorCards", [])
    positioning = meta.get("positioningMap", {})
    overlap = meta.get("overlapByCompetitor", {})
    trends = meta.get("trendsByCompetitor", {})
    artifacts = load_artifacts(run_id)
    art_links = "".join(
        f"<li>{a.scenarioId}: {a.rawKey}</li>" for a in artifacts if a.rawKey
    )

    def card_html(c):
        tvr = c.get("techValueRatio", {})
        pos = c.get("position", {})
        return f"""
        <div style='border:1px solid #ccc;padding:12px;margin:8px;border-radius:8px;width:320px;display:inline-block;vertical-align:top;'>
          <h3>{c.get('name','')}</h3>
          <p>Sentiment: {c.get('sentimentScore',0):.2f} ({c.get('sentimentCategory','')})</p>
          <p>Tech/Value: {tvr.get('technical',0):.1f}% / {tvr.get('value',0):.1f}%</p>
          <p>Differentiation: {c.get('differentiationScore','')}</p>
          <p>Position: x={pos.get('x','')}, y={pos.get('y','')}</p>
          <p>Top Value Props: {', '.join(c.get('topValueProps', []))}</p>
          <p>Top Technical: {', '.join(c.get('topTechnicalConcepts', []))}</p>
        </div>
        """

    cards_html = "".join(card_html(c) for c in cards)

    overlap_html = "<ul>" + "".join(
        f"<li>{cid}: overlap {v.get('overlap',0):.2f}, diff {v.get('differentiationScore',0):.2f}</li>"
        for cid, v in overlap.items()
    ) + "</ul>"

    trends_html = "<ul>" + "".join(
        f"<li>{cid}: emerging {v.get('emergingTerms',[])}, fading {v.get('fadingTerms',[])}, sentimentΔ {v.get('sentimentDelta',0):.2f}</li>"
        for cid, v in trends.items()
    ) + "</ul>"

    # Positioning chart (if coords available)
    pos_fig_html = ""
    if positioning:
        xs = []
        ys = []
        labels = []
        colors = []
        sizes = []
        for cid, coord in positioning.items():
            xs.append(coord.get("x", 0))
            ys.append(coord.get("y", 0))
            labels.append(cid)
            colors.append("#2c8ef4" if cid != "me" else "#2ecc71")
            sizes.append(14 if cid == "me" else 11)
        fig = go.Figure(
            data=go.Scatter(
                x=xs,
                y=ys,
                mode="markers+text",
                text=labels,
                textposition="top center",
                marker=dict(color=colors, size=sizes),
            )
        )
        fig.update_layout(title="Positioning Map", xaxis_title="PC1", yaxis_title="PC2", template="plotly_white")
        pos_fig_html = pio.to_html(fig, include_plotlyjs="cdn", full_html=False)

    # Overlap bar chart
    overlap_fig_html = ""
    if overlap:
        comps = list(overlap.keys())
        ov = [overlap[c]["overlap"] for c in comps]
        diff = [overlap[c]["differentiationScore"] for c in comps]
        fig = go.Figure(data=[
            go.Bar(name="Overlap", x=comps, y=ov),
            go.Bar(name="Differentiation", x=comps, y=diff)
        ])
        fig.update_layout(barmode="group", title="Overlap vs Differentiation", template="plotly_white", yaxis=dict(range=[0,1]))
        overlap_fig_html = pio.to_html(fig, include_plotlyjs="cdn", full_html=False)

    return f"""
    <html>
    <head>
      <title>Landscape {run_id}</title>
      <style>
        body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 24px auto; }}
        h1, h2 {{ margin-bottom: 8px; }}
      </style>
    </head>
    <body>
      <h1>Landscape for Run {run_id}</h1>
      <h2>Positioning</h2>
      {pos_fig_html or '<p>No positioning data</p>'}

      <h2>Overlap vs You</h2>
      {overlap_fig_html or overlap_html}

      <h2>Competitor Cards</h2>
      {cards_html or '<p>No cards</p>'}

      <h2>Trends</h2>
      {trends_html}

      <h2>Artifacts</h2>
      <ul>{art_links}</ul>
    </body>
    </html>
    """


@app.get("/trends/{run_id}", response_class=HTMLResponse)
def trends_page(run_id: str):
    run = get_analysis_run(run_id)
    if not run or not run.summaryJson:
        raise HTTPException(status_code=404, detail="Run not found")
    meta = run.summaryJson._meta or {}
    trends = meta.get("trendsByCompetitor", {})
    cards = {c.get("competitorId"): c for c in meta.get("competitorCards", [])}
    items = []
    for cid, data in trends.items():
        name = cards.get(cid, {}).get("name", cid)
        items.append(
            f"<li><strong>{name}</strong>: emerging {data.get('emergingTerms',[])}, fading {data.get('fadingTerms',[])}, sentimentΔ {data.get('sentimentDelta',0):.2f}</li>"
        )
    trends_html = "<ul>" + "".join(items) + "</ul>"
    # Sentiment delta chart
    sent_fig_html = ""
    if trends:
        comps = list(trends.keys())
        deltas = [trends[c].get("sentimentDelta", 0) for c in comps]
        fig = go.Figure(data=go.Bar(x=comps, y=deltas))
        fig.update_layout(title="Sentiment Delta vs Previous Run", template="plotly_white", xaxis_title="Competitor", yaxis_title="Δ sentiment")
        sent_fig_html = pio.to_html(fig, include_plotlyjs="cdn", full_html=False)

    return f"""
    <html>
    <head><title>Trends {run_id}</title></head>
    <body>
      <h1>Trends for Run {run_id}</h1>
      <h2>Trends by Competitor</h2>
      {trends_html}
      <h2>Sentiment Delta</h2>
      {sent_fig_html or '<p>No sentiment delta data</p>'}
    </body>
    </html>
    """
