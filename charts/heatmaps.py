from __future__ import annotations

import altair as alt
import pandas as pd


def styled_heatmap(df: pd.DataFrame, x: str, y: str, color: str, height: int = 320):
    return (
        alt.Chart(df)
        .mark_rect(cornerRadius=6)
        .encode(x=alt.X(x), y=alt.Y(y), color=alt.Color(color), tooltip=list(df.columns))
        .properties(height=height)
    )
