import pandas as pd
import streamlit as st

from config.interviewers import APPROVED_INTERVIEWERS, INTERVIEWER_NAME_MAP
from design.theme import apply_liquid_glass_theme, render_page_header
from services.data_loader import load_google_sheet
from services.google_sheets_service import get_worksheet
from services.raw_rejection_actions import extract_rejection_columns, move_rows_from_raw_to_rejection
from services.sheet_cleaner import REJECTION_LOG_COLUMNS, clean_live_sheet
from utils.formatters import format_number


RAW_SHEET = "Raw_Kobo_Data"
REJECTION_SHEET = "Rejection_Log"


@st.cache_data(show_spinner=False, ttl=300)
def load_rejection_context():
    raw_ws = get_worksheet(
        st.secrets["gcp_service_account"],
        st.secrets["app"]["spreadsheet_id"],
        RAW_SHEET,
    )
    rejection_ws = get_worksheet(
        st.secrets["gcp_service_account"],
        st.secrets["app"]["spreadsheet_id"],
        REJECTION_SHEET,
    )
    raw_df = load_google_sheet(raw_ws)
    rejection_df = load_google_sheet(rejection_ws)
    return raw_df, rejection_df


st.set_page_config(page_title="Rejection Log", layout="wide")

apply_liquid_glass_theme()
render_page_header(
    "Rejection Log",
    "Normalize interviewer names, reject invalid keys, and move bad records safely out of the live raw sheet.",
    "Rejection",
)

raw_df, rejection_df = load_rejection_context()

c1, c2, c3 = st.columns(3)
c1.metric("Raw rows", format_number(len(raw_df)))
c2.metric("Rejection rows", format_number(len(rejection_df)))
c3.metric("Approved names", format_number(len(APPROVED_INTERVIEWERS)))

if st.button("Run interviewer cleanup", type="primary"):
    result = clean_live_sheet(
        st.secrets["gcp_service_account"],
        st.secrets["app"]["spreadsheet_id"],
        RAW_SHEET,
        REJECTION_SHEET,
    )
    load_rejection_context.clear()
    st.success(
        f"Cleanup complete. Raw kept {result['valid_rows']} rows, rejected {result['rejected_rows']} rows, and added {result['rejection_log_added']} rows to Rejection_Log."
    )
    if result["invalid_names"]:
        st.warning("Invalid interviewer names moved to Rejection_Log: " + ", ".join(result["invalid_names"]))

st.subheader("True Name Mapping")
mapping_df = pd.DataFrame(
    [{"raw_name": raw_name, "true_name": true_name} for raw_name, true_name in INTERVIEWER_NAME_MAP.items()]
)
st.dataframe(mapping_df, width="stretch", hide_index=True, height=240)

move_tab, log_tab = st.tabs(["Move One Key", "Current Rejection Log"])

with move_tab:
    st.subheader("Move selected key to Rejection Log")
    uuid_options = raw_df["_uuid"].astype(str).str.strip().replace("", pd.NA).dropna().tolist() if "_uuid" in raw_df.columns else []
    selected_uuid = st.selectbox(
        "Search or select `_uuid`",
        uuid_options,
        index=None,
        placeholder="Type or choose one _uuid",
    )

    preview_columns = [
        "_uuid",
        "A.1.Interviewer name",
        "A.1.2.Province",
        "A.1.3.District",
        "B.1.Beneficiary/Respondent name",
        "B.2.Father name",
        "B.3.Contact #",
    ]
    preview_df = extract_rejection_columns(raw_df)

    if selected_uuid:
        selected_row = raw_df[raw_df["_uuid"].astype(str).str.strip() == str(selected_uuid).strip()].copy()
        st.dataframe(extract_rejection_columns(selected_row), width="stretch", hide_index=True, height=120)
    else:
        selected_row = pd.DataFrame(columns=REJECTION_LOG_COLUMNS)

    if st.button("Reject selected key", type="primary"):
        if not selected_uuid:
            st.warning("Select one `_uuid` first.")
            st.stop()

        raw_ws = get_worksheet(
            st.secrets["gcp_service_account"],
            st.secrets["app"]["spreadsheet_id"],
            RAW_SHEET,
        )
        rejection_ws = get_worksheet(
            st.secrets["gcp_service_account"],
            st.secrets["app"]["spreadsheet_id"],
            REJECTION_SHEET,
        )
        result = move_rows_from_raw_to_rejection(raw_ws, rejection_ws, raw_df, [selected_uuid])
        load_rejection_context.clear()
        st.success(
            f"{result['removed']} rows were removed from `Raw_Kobo_Data` and {result['moved']} rows were added to `Rejection_Log`."
        )

with log_tab:
    st.subheader("Current Rejection Log")
    st.dataframe(rejection_df, width="stretch", hide_index=True, height=320)
