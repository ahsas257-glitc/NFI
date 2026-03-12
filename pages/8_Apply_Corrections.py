import streamlit as st

from design.theme import apply_liquid_glass_theme, render_page_header
from services.correction_apply_service import apply_corrections_to_raw, build_correction_preview
from services.data_loader import load_google_sheet
from services.google_sheets_service import get_worksheet
from utils.formatters import format_number


RAW_SHEET = "Raw_Kobo_Data"
CORRECTION_SHEET = "Correction_Log"


@st.cache_data(show_spinner=False, ttl=300)
def load_apply_context():
    raw_ws = get_worksheet(
        st.secrets["gcp_service_account"],
        st.secrets["app"]["spreadsheet_id"],
        RAW_SHEET,
    )
    correction_ws = get_worksheet(
        st.secrets["gcp_service_account"],
        st.secrets["app"]["spreadsheet_id"],
        CORRECTION_SHEET,
    )
    raw_df = load_google_sheet(raw_ws)
    correction_df = load_google_sheet(correction_ws)
    return raw_df, correction_df


st.set_page_config(page_title="Apply Corrections", layout="wide")

apply_liquid_glass_theme()
render_page_header(
    "Apply Corrections",
    "Resolve Correction Log entries back into Raw Kobo Data using XLSForm question-name mapping and UUID-safe updates.",
    "Corrections",
)

raw_df, correction_df = load_apply_context()
preview_df, applicable_df = build_correction_preview(raw_df, correction_df)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Raw rows", format_number(len(raw_df)))
c2.metric("Correction rows", format_number(len(correction_df)))
c3.metric("Ready to apply", format_number(len(applicable_df)))
c4.metric("Blocked rows", format_number(len(preview_df) - len(applicable_df)))

if preview_df.empty:
    st.info("`Correction_Log` is empty. No corrections are available to apply.")
else:
    st.subheader("Correction Status")
    status_counts = (
        preview_df["status"]
        .value_counts()
        .rename_axis("status")
        .reset_index(name="count")
    )
    st.dataframe(status_counts, width="stretch", hide_index=True)

    st.subheader("Preview")
    preview_columns = [
        "_uuid",
        "Question",
        "target_column",
        "old_value",
        "current_raw_value",
        "new_value",
        "status",
    ]
    available_preview_columns = [column for column in preview_columns if column in preview_df.columns]
    st.dataframe(preview_df[available_preview_columns], width="stretch", hide_index=True, height=420)

    if st.button("Apply ready corrections", type="primary"):
        raw_ws = get_worksheet(
            st.secrets["gcp_service_account"],
            st.secrets["app"]["spreadsheet_id"],
            RAW_SHEET,
        )
        applied = apply_corrections_to_raw(raw_ws, raw_df, applicable_df)
        load_apply_context.clear()
        st.success(f"{applied} correction rows were applied to `{RAW_SHEET}`.")
