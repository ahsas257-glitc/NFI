import pandas as pd
import streamlit as st

from config.settings import RAW_DATA_SHEET
from core.data_engine import UUID_COLUMN
from design.theme import apply_liquid_glass_theme, render_callout, render_page_header
from services.data_loader import load_google_sheet
from services.google_sheets_service import get_worksheet
from services.sheet_importer import (
    append_new_rows,
    compare_uploaded_columns,
    prepare_import_plan,
    read_uploaded_dataset,
)
from utils.formatters import format_number


def build_preview_frame(uploaded_df, import_plan):
    preview_df = uploaded_df.copy().fillna("")
    if "_uuid" in preview_df.columns:
        preview_df["_uuid"] = preview_df["_uuid"].astype(str).str.strip()
    else:
        preview_df["_uuid"] = ""
    preview_df["_import_status"] = "Ready to import"

    ignored_start = set(import_plan["ignored_by_start"].get("_uuid", pd.Series(dtype=str)).astype(str).str.strip())
    existing_raw = set(import_plan["existing_rows"].get("_uuid", pd.Series(dtype=str)).astype(str).str.strip())
    rejected_log = set(import_plan["rejected_rows"].get("_uuid", pd.Series(dtype=str)).astype(str).str.strip())
    duplicate_upload = set(import_plan["duplicate_in_upload"].get("_uuid", pd.Series(dtype=str)).astype(str).str.strip())

    def detect_status(row):
        row_uuid = str(row.get("_uuid", "")).strip()
        if row_uuid in ignored_start or str(row.get("start", "")).strip() == "":
            return "Ignored by start"
        if row_uuid in rejected_log:
            return "Rejected by log"
        if row_uuid in existing_raw:
            return "Already in raw"
        if row_uuid in duplicate_upload:
            return "Duplicate in upload"
        if not row_uuid:
            return "Missing _uuid"
        return "Ready to import"

    preview_df["_import_status"] = preview_df.apply(detect_status, axis=1)
    return preview_df


def style_preview(df):
    color_map = {
        "Ready to import": "#dcfce7",
        "Ignored by start": "#fee2e2",
        "Rejected by log": "#fde68a",
        "Already in raw": "#e5e7eb",
        "Duplicate in upload": "#fce7f3",
        "Missing _uuid": "#ffedd5",
    }

    def row_style(row):
        color = color_map.get(row["_import_status"], "")
        return [f"background-color: {color}"] * len(row)

    return df.style.apply(row_style, axis=1)


st.set_page_config(page_title="Update Data", layout="wide")

apply_liquid_glass_theme()
render_page_header(
    "Update Data",
    "Import validated records into the live raw sheet with strict UUID rules and column-safe placement.",
    "Ingestion",
)
render_callout(
    "Only labels that already exist in `Raw_Kobo_Data` are imported. Extra columns are ignored completely. Only rows with `start` in year 2026 and from month 03 onward are considered for import."
)


uploaded_file = st.file_uploader(
    "Upload dataset",
    type=["csv", "xlsx", "xls"],
    help="Upload a CSV or Excel file with the same column labels as `Raw_Kobo_Data`.",
)

if uploaded_file:
    try:
        raw_ws = get_worksheet(
            st.secrets["gcp_service_account"],
            st.secrets["app"]["spreadsheet_id"],
            RAW_DATA_SHEET,
        )
        rejection_ws = get_worksheet(
            st.secrets["gcp_service_account"],
            st.secrets["app"]["spreadsheet_id"],
            "Rejection_Log",
        )

        raw_sheet_df = load_google_sheet(raw_ws)
        rejection_df = load_google_sheet(rejection_ws)
        uploaded_df = read_uploaded_dataset(uploaded_file)
        column_check = compare_uploaded_columns(uploaded_df, raw_sheet_df)

        st.subheader("Column Validation")
        c1, c2, c3 = st.columns(3)
        c1.metric("Raw sheet columns", format_number(len(column_check["raw_headers"])))
        c2.metric("Uploaded columns", format_number(len(column_check["upload_headers"])))
        c3.metric("Exact same order", "Yes" if column_check["same_order"] else "No")

        with st.expander("Show exact Raw_Kobo_Data labels"):
            st.code("\n".join(column_check["raw_headers"]))

        with st.expander("Show detected XLSForm mapping"):
            mapping_preview = [
                {"raw_label": raw_label, "source_column": source_column}
                for raw_label, source_column in column_check.get("header_map", {}).items()
            ]
            if mapping_preview:
                st.dataframe(mapping_preview[:80], use_container_width=True, hide_index=True)
            else:
                st.caption("No XLSForm-based column mapping was detected.")

        if column_check["missing_in_upload"]:
            st.warning("Missing columns in uploaded file will be saved as blank in the raw sheet: " + ", ".join(column_check["missing_in_upload"]))
        if column_check["extra_in_upload"]:
            st.info("Extra columns in uploaded file are ignored: " + ", ".join(column_check["extra_in_upload"]))
        if not column_check["same_order"]:
            st.warning(
                "Column order is different from `Raw_Kobo_Data`, but each value will still be placed under the correct sheet label."
            )
        if column_check["same_order"]:
            st.success("Column labels and order exactly match `Raw_Kobo_Data`.")

        import_plan = prepare_import_plan(uploaded_df, raw_sheet_df, rejection_df)
        preview_df = build_preview_frame(uploaded_df, import_plan)

        st.subheader("Import Summary")
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Uploaded rows", format_number(import_plan["uploaded_rows"]))
        m2.metric("Ignored by `start`", format_number(len(import_plan["ignored_by_start"])))
        m3.metric("Without `_uuid`", format_number(import_plan["rows_without_uuid"]))
        m4.metric("Already in Raw", format_number(len(import_plan["existing_rows"])))
        m5.metric("Found in Rejection", format_number(len(import_plan["rejected_rows"])))
        m6.metric("Ready to add", format_number(len(import_plan["accepted_rows"])))

        if len(import_plan["ignored_by_start"]) > 0:
            st.warning(
                f"{format_number(len(import_plan['ignored_by_start']))} rows were ignored because `start` is before March 2026."
            )

        preview_columns = [
            "_import_status",
            "start",
            UUID_COLUMN,
            "A.1.Interviewer name",
            "A.1.2.Province",
            "A.1.3.District",
            "B.1.3.Respondent gender",
        ]
        available_preview_columns = [column for column in preview_columns if column in preview_df.columns]
        st.subheader("Import Preview")
        st.dataframe(
            style_preview(preview_df[available_preview_columns].head(100)),
            use_container_width=True,
            hide_index=True,
        )

        accepted_df = import_plan["accepted_rows"]
        if accepted_df.empty:
            st.warning("No new rows are eligible for import.")
        else:
            ready_columns = [
                UUID_COLUMN,
                "A.1.Interviewer name",
                "A.1.2.Province",
                "A.1.3.District",
                "B.1.3.Respondent gender",
            ]
            available_preview = [column for column in ready_columns if column in accepted_df.columns]
            st.subheader("Rows Ready To Import")
            st.dataframe(
                accepted_df[available_preview] if available_preview else accepted_df.head(20),
                use_container_width=True,
                hide_index=True,
            )

            if st.button("Import new rows", type="primary"):
                added_count = append_new_rows(raw_ws, raw_sheet_df, accepted_df)
                st.success(f"{added_count} new rows were added to `{RAW_DATA_SHEET}`.")

        with st.expander("Show skipped rows"):
            st.markdown("`Ignored because start is before 2026-03`")
            st.dataframe(import_plan["ignored_by_start"], use_container_width=True, hide_index=True)
            st.markdown("`Already in Raw_Kobo_Data`")
            st.dataframe(import_plan["existing_rows"], use_container_width=True, hide_index=True)
            st.markdown("`Found in Rejection_Log`")
            st.dataframe(import_plan["rejected_rows"], use_container_width=True, hide_index=True)
            st.markdown("`Duplicate inside uploaded file`")
            st.dataframe(import_plan["duplicate_in_upload"], use_container_width=True, hide_index=True)

    except Exception as exc:
        st.error(str(exc))
