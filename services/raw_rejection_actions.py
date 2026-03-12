import pandas as pd

from services.rejection_log_service import append_rejection_entries
from services.sheet_cleaner import REJECTION_LOG_COLUMNS


def rewrite_raw_sheet(raw_ws, raw_df: pd.DataFrame) -> None:
    payload = [raw_df.columns.tolist()] + raw_df.fillna("").astype(str).values.tolist()
    raw_ws.clear()
    raw_ws.update(payload, value_input_option="RAW")


def extract_rejection_columns(df: pd.DataFrame) -> pd.DataFrame:
    extracted = pd.DataFrame(index=df.index)
    for column in REJECTION_LOG_COLUMNS:
        if column in df.columns:
            selected = df.loc[:, column]
            if isinstance(selected, pd.DataFrame):
                extracted[column] = selected.iloc[:, 0]
            else:
                extracted[column] = selected
        else:
            extracted[column] = ""
    return extracted.fillna("")


def move_rows_from_raw_to_rejection(raw_ws, rejection_ws, raw_df: pd.DataFrame, selected_uuids: list[str]) -> dict:
    uuid_set = {str(value).strip() for value in selected_uuids if str(value).strip()}
    if not uuid_set:
        return {"moved": 0, "removed": 0}

    working_df = raw_df.copy()
    working_df["_uuid"] = working_df["_uuid"].astype(str).str.strip()

    rows_to_move = working_df[working_df["_uuid"].isin(uuid_set)].copy()
    rows_to_keep = working_df[~working_df["_uuid"].isin(uuid_set)].copy()

    rejection_payload = extract_rejection_columns(rows_to_move)
    added_to_rejection = append_rejection_entries(rejection_ws, rejection_payload)
    rewrite_raw_sheet(raw_ws, rows_to_keep)

    return {
        "moved": int(added_to_rejection),
        "removed": int(len(rows_to_move)),
    }
