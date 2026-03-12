# -*- coding: utf-8 -*-

import pandas as pd

from config.interviewers import APPROVED_INTERVIEWERS
from core.data_engine import (
    DISTRICT_COLUMN,
    INTERVIEWER_COLUMN,
    PROVINCE_COLUMN,
    UUID_COLUMN,
    _normalize_interviewer,
)
from services.data_loader import load_google_sheet
from services.google_sheets_service import get_worksheet

REJECTION_LOG_COLUMNS = [
    "_uuid",
    "A.1.Interviewer name",
    "A.1.2.Province",
    "A.1.3.District",
    "B.1.Beneficiary/Respondent name",
    "B.2.Father name",
    "B.3.Contact #",
]


def normalize_interviewer_column(df: pd.DataFrame) -> pd.DataFrame:
    updated_df = df.copy()
    if INTERVIEWER_COLUMN in updated_df.columns:
        updated_df[INTERVIEWER_COLUMN] = updated_df[INTERVIEWER_COLUMN].map(_normalize_interviewer)
    return updated_df


def split_valid_invalid_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    normalized_df = normalize_interviewer_column(df)
    valid_mask = normalized_df[INTERVIEWER_COLUMN].isin(APPROVED_INTERVIEWERS)
    valid_df = normalized_df[valid_mask].copy()
    invalid_df = normalized_df[~valid_mask].copy()
    return valid_df, invalid_df


def sync_rejection_log(rejection_ws, invalid_df: pd.DataFrame) -> int:
    if UUID_COLUMN not in invalid_df.columns:
        return 0

    for column in REJECTION_LOG_COLUMNS:
        if column not in invalid_df.columns:
            invalid_df[column] = ""

    rejection_payload = (
        invalid_df[REJECTION_LOG_COLUMNS]
        .copy()
        .fillna("")
    )
    rejection_payload[UUID_COLUMN] = rejection_payload[UUID_COLUMN].astype(str).str.strip()
    rejection_payload = rejection_payload[rejection_payload[UUID_COLUMN] != ""].drop_duplicates(subset=[UUID_COLUMN])

    if rejection_payload.empty:
        return 0

    existing_values = rejection_ws.get_all_values()
    existing_headers = existing_values[0] if existing_values else []
    if existing_headers != REJECTION_LOG_COLUMNS:
        existing_df = pd.DataFrame(existing_values[1:], columns=existing_headers) if existing_values else pd.DataFrame()
        for column in REJECTION_LOG_COLUMNS:
            if column not in existing_df.columns:
                existing_df[column] = ""
        rejection_ws.clear()
        rejection_ws.update(
            [REJECTION_LOG_COLUMNS] + existing_df[REJECTION_LOG_COLUMNS].fillna("").astype(str).values.tolist(),
            value_input_option="RAW",
        )
        existing_values = rejection_ws.get_all_values()

    existing_uuids = {row[0].strip() for row in existing_values[1:] if row and row[0].strip()}
    rows_to_add = rejection_payload[~rejection_payload[UUID_COLUMN].isin(existing_uuids)]

    if not rows_to_add.empty:
        rejection_ws.append_rows(rows_to_add[REJECTION_LOG_COLUMNS].fillna("").astype(str).values.tolist(), value_input_option="RAW")
    return len(rows_to_add)


def rewrite_raw_sheet(raw_ws, valid_df: pd.DataFrame) -> None:
    payload = [valid_df.columns.tolist()] + valid_df.fillna("").astype(str).values.tolist()
    raw_ws.clear()
    raw_ws.update(payload, value_input_option="RAW")


def clean_live_sheet(service_account, spreadsheet_id, raw_sheet_name, rejection_sheet_name) -> dict:
    raw_ws = get_worksheet(service_account, spreadsheet_id, raw_sheet_name)
    rejection_ws = get_worksheet(service_account, spreadsheet_id, rejection_sheet_name)

    raw_df = load_google_sheet(raw_ws)
    valid_df, invalid_df = split_valid_invalid_rows(raw_df)
    rejection_added = sync_rejection_log(rejection_ws, invalid_df)
    rewrite_raw_sheet(raw_ws, valid_df)

    return {
        "original_rows": int(len(raw_df)),
        "valid_rows": int(len(valid_df)),
        "rejected_rows": int(len(invalid_df)),
        "rejection_log_added": int(rejection_added),
        "invalid_names": sorted(invalid_df[INTERVIEWER_COLUMN].astype(str).str.strip().unique().tolist()),
    }
