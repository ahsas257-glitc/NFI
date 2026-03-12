from __future__ import annotations

import streamlit as st


def render_metric_row(metrics: list[dict]) -> None:
    if not metrics:
        return
    columns = st.columns(len(metrics))
    for column, item in zip(columns, metrics):
        with column:
            st.metric(item["label"], item["value"], item.get("delta"))


def render_empty_state(message: str) -> None:
    st.info(message)
