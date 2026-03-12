import pandas as pd

from services.sheet_cleaner import REJECTION_LOG_COLUMNS


def normalize_rejection_entries(df: pd.DataFrame) -> pd.DataFrame:
    working_df = df.copy()
    for column in REJECTION_LOG_COLUMNS:
        if column not in working_df.columns:
            working_df[column] = ""
    working_df = working_df[REJECTION_LOG_COLUMNS].fillna("")
    working_df["_uuid"] = working_df["_uuid"].astype(str).str.strip()
    working_df = working_df[working_df["_uuid"] != ""].drop_duplicates(subset=["_uuid"])
    return working_df.reset_index(drop=True)


def append_rejection_entries(rejection_ws, entries_df: pd.DataFrame) -> int:
    normalized_df = normalize_rejection_entries(entries_df)
    if normalized_df.empty:
        return 0

    existing_values = rejection_ws.get_all_values()
    existing_headers = existing_values[0] if existing_values else []

    if existing_headers != REJECTION_LOG_COLUMNS:
        existing_df = pd.DataFrame(existing_values[1:], columns=existing_headers) if existing_values else pd.DataFrame()
        existing_df = normalize_rejection_entries(existing_df)
        rejection_ws.clear()
        rejection_ws.update(
            [REJECTION_LOG_COLUMNS] + existing_df.values.tolist(),
            value_input_option="RAW",
        )
        existing_values = rejection_ws.get_all_values()

    existing_uuids = {row[0].strip() for row in existing_values[1:] if row and row[0].strip()}
    rows_to_add = normalized_df[~normalized_df["_uuid"].isin(existing_uuids)]

    if not rows_to_add.empty:
        rejection_ws.append_rows(rows_to_add.values.tolist(), value_input_option="RAW")
    return int(len(rows_to_add))
