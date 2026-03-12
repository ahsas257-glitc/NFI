from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.data_engine import UUID_COLUMN


CORRECTION_LOG_COLUMNS = [
    "_uuid",
    "Question",
    "old_value",
    "new_value",
    "translated_by",
    "translated_at",
    "Assigned_To",
]


def build_value_mapping_frame(df: pd.DataFrame, question_column: str, choices_df: pd.DataFrame) -> pd.DataFrame:
    working = df[[UUID_COLUMN, question_column]].copy()
    working[question_column] = working[question_column].astype(str).fillna("").str.strip()
    working = working[working[question_column] != ""]

    value_counts = (
        working.groupby(question_column)
        .agg(record_count=(UUID_COLUMN, "count"))
        .reset_index()
        .rename(columns={question_column: "old_value"})
        .sort_values(["record_count", "old_value"], ascending=[False, True])
    )

    if choices_df.empty:
        value_counts["suggested_value"] = value_counts["old_value"]
    else:
        lookup = {}
        for _, row in choices_df.iterrows():
            english = str(row.get("label::English (en)", "")).strip() or str(row.get("name", "")).strip()
            for key in [
                str(row.get("name", "")).strip(),
                str(row.get("label::English (en)", "")).strip(),
                str(row.get("label::Dari (prs)", "")).strip(),
                str(row.get("label::Pashto (ps)", "")).strip(),
            ]:
                if key:
                    lookup[key] = english
        value_counts["suggested_value"] = value_counts["old_value"].map(lambda value: lookup.get(value, value))

    value_counts["new_value"] = value_counts["suggested_value"]
    return value_counts.reset_index(drop=True)


def build_correction_rows(
    df: pd.DataFrame,
    question_column: str,
    edited_mapping_df: pd.DataFrame,
    question_identifier: str | None = None,
    translated_by: str = "",
    assigned_to: str = "",
) -> pd.DataFrame:
    changes = edited_mapping_df.copy()
    changes["old_value"] = changes["old_value"].astype(str).str.strip()
    changes["new_value"] = changes["new_value"].astype(str).str.strip()
    changes = changes[
        (changes["old_value"] != "")
        & (changes["new_value"] != "")
        & (changes["old_value"] != changes["new_value"])
    ].copy()

    if changes.empty:
        return pd.DataFrame(columns=CORRECTION_LOG_COLUMNS)

    change_lookup = dict(zip(changes["old_value"], changes["new_value"]))
    source = df[[UUID_COLUMN, question_column]].copy()
    source[question_column] = source[question_column].astype(str).fillna("").str.strip()
    source = source[source[question_column].isin(change_lookup.keys())].copy()

    correction_df = pd.DataFrame(
        {
            "_uuid": source[UUID_COLUMN].astype(str).str.strip(),
            "Question": (question_identifier or question_column),
            "old_value": source[question_column],
            "new_value": source[question_column].map(change_lookup),
            "translated_by": translated_by.strip(),
            "translated_at": datetime.now().isoformat(timespec="seconds"),
            "Assigned_To": assigned_to.strip(),
        }
    )

    return correction_df[CORRECTION_LOG_COLUMNS].drop_duplicates().reset_index(drop=True)


def append_corrections(correction_ws, correction_df: pd.DataFrame) -> int:
    if correction_df.empty:
        return 0

    existing = correction_ws.get_all_values()
    existing_headers = existing[0] if existing else []

    if existing_headers != CORRECTION_LOG_COLUMNS:
        correction_ws.clear()
        correction_ws.update([CORRECTION_LOG_COLUMNS], value_input_option="RAW")

    existing_rows = correction_ws.get_all_values()
    existing_keys = {
        tuple(row[:4])
        for row in existing_rows[1:]
        if len(row) >= 4
    }

    rows_to_add = []
    for row in correction_df.fillna("").astype(str).values.tolist():
        key = tuple(row[:4])
        if key not in existing_keys:
            rows_to_add.append(row)
            existing_keys.add(key)

    if rows_to_add:
        correction_ws.append_rows(rows_to_add, value_input_option="RAW")
    return len(rows_to_add)
