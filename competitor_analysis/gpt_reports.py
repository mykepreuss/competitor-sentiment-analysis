"""
Optional GPT-based summaries and recommendations.

If OPENAI_API_KEY is not set or use_gpt is false, these functions return [].
"""

from __future__ import annotations

from typing import Any, Dict, List
from pathlib import Path
import os


def generate_gpt_artifacts(run, summary: Dict[str, Any], output_dir: str, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Returns list of artifact dicts {id, path, kind, scenarioId, mimeType}
    """
    if not settings.get("use_gpt"):
        return []
    api_key = settings.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return []
    try:
        from openai import OpenAI
    except Exception:
        return []

    client = OpenAI(api_key=api_key)
    run_dir = Path(output_dir) / run.id
    run_dir.mkdir(parents=True, exist_ok=True)

    def call_chat(system_prompt: str, user_prompt: str) -> str:
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
            return resp.choices[0].message.content
        except Exception:
            return ""

    summary_text = call_chat(
        "You are a concise competitive landscape analyst.",
        f"Based on this JSON, summarize the competitive landscape, clusters, and who is closest to 'us':\n\n{summary}",
    )
    playbook_text = call_chat(
        "You are a concise differentiation strategist.",
        f"Given this JSON of competitors vs us, give 3-5 differentiation moves (short bullets):\n\n{summary}",
    )

    artifacts = []
    if summary_text:
        path = run_dir / "executive_summary.md"
        path.write_text(summary_text)
        artifacts.append(
            {
                "id": f"artifact-{run.id}-gpt-summary",
                "path": str(path),
                "scenarioId": "executive_summary",
                "mimeType": "text/markdown",
            }
        )
    if playbook_text:
        path = run_dir / "differentiation_playbook.md"
        path.write_text(playbook_text)
        artifacts.append(
            {
                "id": f"artifact-{run.id}-gpt-playbook",
                "path": str(path),
                "scenarioId": "differentiation_playbook",
                "mimeType": "text/markdown",
            }
        )
    return artifacts
