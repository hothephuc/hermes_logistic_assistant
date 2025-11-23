from __future__ import annotations

from datetime import timedelta
from typing import Dict

import numpy as np
import pandas as pd
from app.ai.master_agent.state import AgentState


def run_prediction_intent(state: AgentState) -> Dict[str, object]:
    df = _apply_filters(state)
    if df.empty:
        return {
            "summary": "Not enough data points to produce a prediction.",
            "chart": None,
            "table": None,
        }

    daily = (
        df.groupby(df["date"].dt.date)
        .agg(avg_delay=("delay_minutes", "mean"))
        .reset_index()
        .sort_values("date")
    )

    if len(daily) < 3:
        return {
            "summary": "I need at least 3 days of delay history to project forward.",
            "chart": None,
            "table": None,
        }

    # Convert to ordinal for regression
    x = np.array(
        [pd.to_datetime(day).toordinal() for day in daily["date"]], dtype=float
    )
    y = daily["avg_delay"].to_numpy(dtype=float)

    slope, intercept = np.polyfit(x, y, 1)

    # Forecast next 7 days
    last_date = pd.to_datetime(daily["date"].iloc[-1])
    forecast_points = []
    for i in range(1, 8):
        next_day = last_date + timedelta(days=i)
        prediction = slope * next_day.toordinal() + intercept
        forecast_points.append(
            {
                "date": next_day.date(),
                "predicted_avg_delay": max(prediction, 0),
            }
        )

    next_week_avg = np.mean([point["predicted_avg_delay"] for point in forecast_points])
    summary = f"Projected average delay for next week is {next_week_avg:.1f} minutes per shipment."  # noqa: E501

    chart_data = [
        {
            "label": str(row["date"]),
            "value": round(row["avg_delay"], 2),
            "isForecast": False,
        }
        for _, row in daily.iterrows()
    ] + [
        {
            "label": str(point["date"]),
            "value": round(point["predicted_avg_delay"], 2),
            "isForecast": True,
        }
        for point in forecast_points
    ]

    return {
        "summary": summary,
        "intent": "prediction",
        "chart": {
            "type": "line",
            "title": "Average Delay Forecast",
            "x_label": "Date",
            "y_label": "Avg Delay (min)",
            "data": chart_data,
            "dataset_label": "Avg Delay",
        },
        "table": {
            "columns": [
                {"key": "date", "label": "Date"},
                {"key": "avg_delay", "label": "Actual Avg Delay"},
            ],
            "rows": daily.round({"avg_delay": 2}).to_dict(orient="records"),
            "forecast": forecast_points,
        },
    }


def _apply_filters(state: AgentState) -> pd.DataFrame:
    df = state["data"].copy()

    timeframe = state.get("timeframe", {})
    if timeframe:
        start = timeframe.get("start")
        end = timeframe.get("end")
        if start is not None:
            df = df[df["date"] >= start]
        if end is not None:
            df = df[df["date"] <= end]

    df["date"] = pd.to_datetime(df["date"])
    return df
