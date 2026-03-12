import io

import pandas as pd

from core.data_engine import UUID_COLUMN
from services.sheet_cleaner import normalize_interviewer_column
from services.xlsform_service import build_xlsform_export_pairs, load_xlsform, resolve_xlsform_path

START_COLUMN = "start"


def _drop_empty_unnamed_columns(df: pd.DataFrame) -> pd.DataFrame:
    cleaned_df = df.copy()
    unnamed_columns = [
        column
        for column in cleaned_df.columns
        if str(column).strip().lower().startswith("unnamed:")
    ]
    for column in unnamed_columns:
        series = cleaned_df[column].fillna("").astype(str).str.strip()
        if (series == "").all():
            cleaned_df = cleaned_df.drop(columns=[column])
    return cleaned_df


def read_uploaded_dataset(uploaded_file) -> pd.DataFrame:
    file_name = uploaded_file.name.lower()
    file_bytes = uploaded_file.getvalue()

    if file_name.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(file_bytes), dtype=str).fillna("")
        return _drop_empty_unnamed_columns(df)
    if file_name.endswith(".xlsx") or file_name.endswith(".xls"):
        df = pd.read_excel(io.BytesIO(file_bytes), dtype=str).fillna("")
        return _drop_empty_unnamed_columns(df)

    raise ValueError("Unsupported file format. Please upload a CSV or Excel file.")


def filter_allowed_start_rows(uploaded_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if START_COLUMN not in uploaded_df.columns:
        raise ValueError("The uploaded dataset must include the `start` column.")

    working_df = uploaded_df.copy()
    parsed_start = pd.to_datetime(working_df[START_COLUMN], errors="coerce")
    allowed_mask = (parsed_start.dt.year == 2026) & (parsed_start.dt.month >= 3)

    accepted_by_start_df = working_df[allowed_mask].copy()
    ignored_by_start_df = working_df[~allowed_mask].copy()
    return accepted_by_start_df, ignored_by_start_df


def _align_uploaded_to_raw_headers(uploaded_df: pd.DataFrame, raw_headers: list[str]) -> tuple[pd.DataFrame, dict]:
    survey_df, choices_df = load_xlsform(resolve_xlsform_path("."))
    pairs = build_xlsform_export_pairs(survey_df, choices_df)

    upload_headers = [str(column).strip() for column in uploaded_df.columns.tolist()]
    header_map = {}
    used_sources = set()

    for raw_header in raw_headers:
        exact_match = next(
            (header for header in upload_headers if header == raw_header and header not in used_sources),
            None,
        )
        if exact_match is not None:
            header_map[raw_header] = exact_match
            used_sources.add(exact_match)
            continue

        mapped_match = next(
            (
                pair["source"]
                for pair in pairs
                if pair["target"] == raw_header
                and pair["source"] in upload_headers
                and pair["source"] not in used_sources
            ),
            None,
        )
        if mapped_match is not None:
            header_map[raw_header] = mapped_match
            used_sources.add(mapped_match)

    aligned_df = pd.DataFrame(index=uploaded_df.index)
    for raw_header in raw_headers:
        source_column = header_map.get(raw_header)
        if source_column is None:
            aligned_df[raw_header] = ""
        else:
            aligned_df[raw_header] = uploaded_df[source_column]

    ignored_headers = [header for header in upload_headers if header not in used_sources]
    missing_headers = [header for header in raw_headers if header not in header_map]

    return aligned_df, {
        "header_map": header_map,
        "ignored_headers": ignored_headers,
        "missing_headers": missing_headers,
        "used_sources": sorted(used_sources),
        "upload_headers": upload_headers,
    }


def prepare_import_plan(
    uploaded_df: pd.DataFrame,
    raw_df: pd.DataFrame,
    rejection_df: pd.DataFrame,
) -> dict:
    raw_headers = [str(column).strip() for column in raw_df.columns.tolist()]
    aligned_uploaded_df, alignment_info = _align_uploaded_to_raw_headers(uploaded_df, raw_headers)

    if UUID_COLUMN not in aligned_uploaded_df.columns:
        raise ValueError("The uploaded dataset must include the `_uuid` column.")

    start_filtered_df, ignored_by_start_df = filter_allowed_start_rows(aligned_uploaded_df)

    candidate_df = start_filtered_df.copy().fillna("")
    candidate_df.columns = [str(column).strip() for column in candidate_df.columns]
    candidate_df = candidate_df.reindex(columns=raw_headers, fill_value="")
    candidate_df = normalize_interviewer_column(candidate_df)
    candidate_df[UUID_COLUMN] = candidate_df[UUID_COLUMN].astype(str).str.strip()

    candidate_df = candidate_df[candidate_df[UUID_COLUMN] != ""].copy()

    raw_uuid_set = set()
    if UUID_COLUMN in raw_df.columns:
        raw_uuid_set = {
            str(value).strip()
            for value in raw_df[UUID_COLUMN].astype(str).tolist()
            if str(value).strip()
        }

    rejection_uuid_set = set()
    if UUID_COLUMN in rejection_df.columns:
        rejection_uuid_set = {
            str(value).strip()
            for value in rejection_df[UUID_COLUMN].astype(str).tolist()
            if str(value).strip()
        }

    uploaded_duplicate_mask = candidate_df[UUID_COLUMN].duplicated(keep="first")
    duplicate_in_upload_df = candidate_df[uploaded_duplicate_mask].copy()
    unique_candidate_df = candidate_df[~uploaded_duplicate_mask].copy()

    rejected_df = unique_candidate_df[unique_candidate_df[UUID_COLUMN].isin(rejection_uuid_set)].copy()
    existing_df = unique_candidate_df[unique_candidate_df[UUID_COLUMN].isin(raw_uuid_set)].copy()
    accepted_df = unique_candidate_df[
        ~unique_candidate_df[UUID_COLUMN].isin(rejection_uuid_set | raw_uuid_set)
    ].copy()

    return {
        "uploaded_rows": int(len(uploaded_df)),
        "ignored_by_start": ignored_by_start_df,
        "rows_without_uuid": int((candidate_df[UUID_COLUMN].astype(str).str.strip() == "").sum()),
        "duplicate_in_upload": duplicate_in_upload_df,
        "rejected_rows": rejected_df,
        "existing_rows": existing_df,
        "accepted_rows": accepted_df,
        "alignment_info": alignment_info,
    }


def append_new_rows(raw_ws, raw_df: pd.DataFrame, accepted_df: pd.DataFrame) -> int:
    if accepted_df.empty:
        return 0

    raw_headers = raw_df.columns.tolist()
    aligned_new = accepted_df.reindex(columns=raw_headers, fill_value="")
    raw_ws.append_rows(aligned_new.fillna("").astype(str).values.tolist(), value_input_option="RAW")
    return int(len(aligned_new))


def compare_uploaded_columns(uploaded_df: pd.DataFrame, raw_df: pd.DataFrame) -> dict:
    raw_headers = [str(column).strip() for column in raw_df.columns.tolist()]
    _, alignment_info = _align_uploaded_to_raw_headers(uploaded_df, raw_headers)
    upload_headers = alignment_info["upload_headers"]
    missing_in_upload = alignment_info["missing_headers"]
    extra_in_upload = alignment_info["ignored_headers"]
    matched_upload_headers = [alignment_info["header_map"].get(header) for header in raw_headers if header in alignment_info["header_map"]]
    same_order = matched_upload_headers == raw_headers

    return {
        "raw_headers": raw_headers,
        "upload_headers": upload_headers,
        "missing_in_upload": missing_in_upload,
        "extra_in_upload": extra_in_upload,
        "same_order": same_order,
        "is_compatible": True,
        "header_map": alignment_info["header_map"],
    }
