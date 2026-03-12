from __future__ import annotations

import pandas as pd


def build_daily_trend(df: pd.DataFrame, date_column: str) -> pd.DataFrame:
    if date_column not in df.columns:
        return pd.DataFrame(columns=["date", "records"])
    trend_df = df.copy()
    trend_df[date_column] = pd.to_datetime(trend_df[date_column], errors="coerce")
    trend_df = trend_df.dropna(subset=[date_column])
    if trend_df.empty:
        return pd.DataFrame(columns=["date", "records"])
    trend_df["date"] = trend_df[date_column].dt.date
    return trend_df.groupby("date").size().reset_index(name="records")
