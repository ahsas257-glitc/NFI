from __future__ import annotations

import pandas as pd

from core.data_engine import UUID_COLUMN
from services.xlsform_service import (
    build_ordered_question_column_map,
    load_xlsform,
    resolve_xlsform_path,
)


def build_question_resolution_map(raw_df: pd.DataFrame) -> dict:
    survey_df, choices_df = load_xlsform(resolve_xlsform_path("."))
    raw_headers = [str(column).strip() for column in raw_df.columns.tolist()]
    ordered_map = build_ordered_question_column_map(raw_headers, survey_df, choices_df)

    resolution = {}
    for item in ordered_map:
        resolution[item["source"]] = item
        if item["target"] not in resolution:
            resolution[item["target"]] = item
    return resolution


def build_correction_preview(raw_df: pd.DataFrame, correction_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if correction_df.empty:
        empty = pd.DataFrame(columns=["_uuid", "Question", "old_value", "new_value", "status", "target_column"])
        return empty, empty

    resolution_map = build_question_resolution_map(raw_df)
    working = correction_df.copy().fillna("")
    working["_uuid"] = working["_uuid"].astype(str).str.strip()
    working["Question"] = working["Question"].astype(str).str.strip()
    working["old_value"] = working["old_value"].astype(str).str.strip()
    working["new_value"] = working["new_value"].astype(str).str.strip()

    raw_uuid_series = raw_df[UUID_COLUMN].astype(str).str.strip() if UUID_COLUMN in raw_df.columns else pd.Series(dtype=str)
    preview_rows = []

    for _, row in working.iterrows():
        question_key = row["Question"]
        resolution = resolution_map.get(question_key)
        if resolution is None:
            preview_rows.append(
                {
                    **row.to_dict(),
                    "status": "Question not mapped",
                    "target_column": "",
                    "column_index": None,
                }
            )
            continue

        uuid_mask = raw_uuid_series == row["_uuid"]
        if not uuid_mask.any():
            preview_rows.append(
                {
                    **row.to_dict(),
                    "status": "UUID not found",
                    "target_column": resolution["target"],
                    "column_index": resolution["column_index"],
                }
            )
            continue

        current_value = str(raw_df.iloc[uuid_mask[uuid_mask].index[0], resolution["column_index"]]).strip()
        status = "Ready"
        if row["old_value"] and current_value != row["old_value"]:
            status = "Old value mismatch"
        elif current_value == row["new_value"]:
            status = "Already applied"

        preview_rows.append(
            {
                **row.to_dict(),
                "status": status,
                "target_column": resolution["target"],
                "column_index": resolution["column_index"],
                "current_raw_value": current_value,
            }
        )

    preview_df = pd.DataFrame(preview_rows)
    applicable_df = preview_df[preview_df["status"] == "Ready"].copy()
    return preview_df, applicable_df


def apply_corrections_to_raw(raw_ws, raw_df: pd.DataFrame, applicable_df: pd.DataFrame) -> int:
    if applicable_df.empty:
        return 0

    updated_df = raw_df.copy()
    uuid_series = updated_df[UUID_COLUMN].astype(str).str.strip()

    applied = 0
    for _, row in applicable_df.iterrows():
        uuid_mask = uuid_series == str(row["_uuid"]).strip()
        if not uuid_mask.any():
            continue
        target_index = int(row["column_index"])
        row_index = uuid_mask[uuid_mask].index[0]
        updated_df.iat[row_index, target_index] = row["new_value"]
        applied += 1

    payload = [updated_df.columns.tolist()] + updated_df.fillna("").astype(str).values.tolist()
    raw_ws.clear()
    raw_ws.update(payload, value_input_option="RAW")
    return applied
