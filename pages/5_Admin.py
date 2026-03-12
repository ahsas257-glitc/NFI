import pandas as pd
import streamlit as st

from config.expected_columns import EXPECTED_COLUMNS
from config.interviewers import APPROVED_INTERVIEWERS, ENUMERATOR_TARGETS
from config.settings import RAW_DATA_SHEET, SPREADSHEET_ID
from config.targets import DISTRICT_TARGETS, PROVINCE_TARGETS
from core.app_data import load_app_data
from core.data_engine import DataEngine
from design.theme import apply_liquid_glass_theme, render_page_header


st.set_page_config(page_title="Admin", layout="wide")

apply_liquid_glass_theme()
render_page_header(
    "Admin",
    "Reference controls for sheet structure, configured targets, approved interviewers, and live schema differences.",
    "Admin",
)

df = load_app_data()
engine = DataEngine(df)
clean_df = engine.get_clean_data()
quality = engine.get_quality_summary()

sheet_tab, targets_tab, columns_tab = st.tabs(["Sheet", "Targets", "Columns"])

with sheet_tab:
    st.write(f"Spreadsheet ID: `{SPREADSHEET_ID}`")
    st.write(f"Worksheet: `{RAW_DATA_SHEET}`")
    st.write(f"Loaded rows: `{len(clean_df)}`")
    if quality["unexpected_provinces"]:
        st.warning("Live data contains non-target provinces: " + ", ".join(quality["unexpected_provinces"]))

with targets_tab:
    province_targets_df = pd.DataFrame(
        [
            {
                "province": province,
                "target_total": values["total"],
                "target_male": values["male"],
                "target_female": values["female"],
            }
            for province, values in PROVINCE_TARGETS.items()
        ]
    )
    st.subheader("Province Targets")
    st.dataframe(province_targets_df, width="stretch", hide_index=True)

    st.subheader("District Targets")
    st.dataframe(pd.DataFrame(DISTRICT_TARGETS), width="stretch", hide_index=True)

    st.subheader("Approved Interviewers")
    st.dataframe(pd.DataFrame({"interviewer_name": APPROVED_INTERVIEWERS}), width="stretch", hide_index=True)

    st.subheader("Enumerator Assignments")
    st.dataframe(pd.DataFrame(ENUMERATOR_TARGETS), width="stretch", hide_index=True)

with columns_tab:
    expected_set = set(EXPECTED_COLUMNS)
    live_set = set(clean_df.columns)
    missing_in_live = sorted(expected_set - live_set)
    extra_in_live = sorted(live_set - expected_set)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Missing Expected Columns")
        st.dataframe(pd.DataFrame({"column": missing_in_live}), width="stretch", hide_index=True)
    with c2:
        st.subheader("Extra Live Columns")
        st.dataframe(pd.DataFrame({"column": extra_in_live}), width="stretch", hide_index=True)
