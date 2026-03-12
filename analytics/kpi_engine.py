from __future__ import annotations

import pandas as pd


def build_kpi_snapshot(
    overview: dict,
    filtered_df: pd.DataFrame,
    province_progress_df: pd.DataFrame,
) -> list[dict]:
    filtered_target = int(province_progress_df["target_total"].sum()) if not province_progress_df.empty else 0
    filtered_rate = round((len(filtered_df) / filtered_target) * 100, 1) if filtered_target else 0.0
    completion_rate = round((overview["target_scope_records"] / overview["target_total"]) * 100, 1) if overview["target_total"] else 0.0
    return [
        {"label": "Target Total", "value": overview["target_total"]},
        {"label": "Completed", "value": overview["target_scope_records"], "delta": f"{completion_rate}%"},
        {"label": "Filtered Coverage", "value": f"{filtered_rate}%"},
        {"label": "Male Gap", "value": overview["target_male"] - overview["actual_male"]},
        {"label": "Female Gap", "value": overview["target_female"] - overview["actual_female"]},
        {"label": "Outside Scope", "value": overview["extra_scope_records"]},
    ]
