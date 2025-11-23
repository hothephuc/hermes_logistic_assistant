from __future__ import annotations

from functools import lru_cache

import pandas as pd
from app.ai.master_agent.agent import build_master_graph
from app.ai.master_agent.state import AgentState


@lru_cache(maxsize=1)
def _graph():
    """Instantiate the LangGraph once and reuse across requests."""

    return build_master_graph().compile()


def process_query(query: str, data: pd.DataFrame, history: list | None = None) -> str:
    state: AgentState = {
        "query": query,
        "data": data,
        "filters": {},
        "timeframe": {},
        "result": {},
        "steps": [],
        "forecast_horizon_days": 7,
        "history": history or [],
    }
    final_state = _graph().invoke(state)
    # Append conversational memory (side-effect for caller)
    if history is not None:
        try:
            import json

            payload = json.loads(final_state.get("response", "{}"))
            result = payload.get("result", {}) if isinstance(payload, dict) else {}
            summary_text = result.get("summary")
            recommendations = result.get("recommendations")
            metrics = result.get("metrics")
            insight_fragments: list[str] = []
            if summary_text:
                insight_fragments.append(summary_text)
            if recommendations:
                joined = "; ".join(recommendations)
                insight_fragments.append(f"Recommendations: {joined}")
            if metrics and isinstance(metrics, dict):
                horizon = metrics.get("forecast_horizon_days")
                if horizon:
                    insight_fragments.append(f"Forecast horizon: {horizon} days")
                ensemble = metrics.get("ensemble_estimates")
                if ensemble:
                    top = (
                        ensemble[0] if isinstance(ensemble, list) and ensemble else None
                    )
                    if top:
                        detail = (
                            f"Top scenario {top.get('route')} / {top.get('warehouse')} / "  # noqa: E501
                            f"{top.get('delay_reason')} ≈ {top.get('predicted_delay_minutes')} min"  # noqa: E501
                        )
                        insight_fragments.append(detail)
            history.append(
                {
                    "query": query,
                    "intent": payload.get("intent"),
                    "summary": summary_text,
                    "insight": " | ".join(insight_fragments)
                    if insight_fragments
                    else summary_text,
                    "recommendations": recommendations,
                }
            )
        except Exception:
            pass
    return final_state.get("response", "No response generated.")
