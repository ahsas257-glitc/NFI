from __future__ import annotations

import altair as alt
import pandas as pd


def styled_bar(df: pd.DataFrame, x: str, y: str, color: str | None = None, height: int = 320):
    chart = alt.Chart(df).mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8).encode(
        x=alt.X(x),
        y=alt.Y(y),
        tooltip=list(df.columns),
    )
    if color:
        chart = chart.encode(color=alt.Color(color))
    return chart.properties(height=height)


def styled_donut(df: pd.DataFrame, theta: str, color: str, height: int = 320):
    return (
        alt.Chart(df)
        .mark_arc(innerRadius=62, outerRadius=118)
        .encode(theta=alt.Theta(theta), color=alt.Color(color), tooltip=list(df.columns))
        .properties(height=height)
    )


def styled_line(df: pd.DataFrame, x: str, y: str, height: int = 320):
    return (
        alt.Chart(df)
        .mark_line(point=True, strokeWidth=3)
        .encode(x=alt.X(x), y=alt.Y(y), tooltip=list(df.columns))
        .properties(height=height)
    )
