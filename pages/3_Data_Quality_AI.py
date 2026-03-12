import pandas as pd
import streamlit as st

from design.theme import apply_liquid_glass_theme, close_panel, open_panel, render_page_header
from core.ai_quality_engine import AIQualityEngine
from core.app_data import load_app_data
from core.data_engine import DataEngine
from services.form_quality_service import build_form_quality_report
from services.xlsform_service import load_xlsform, resolve_xlsform_path
from utils.formatters import format_number


@st.cache_data(show_spinner=False, ttl=300)
def load_form_reference():
    return load_xlsform(resolve_xlsform_path("."))


st.set_page_config(page_title="Data Quality AI", layout="wide")

apply_liquid_glass_theme()
render_page_header(
    "Data Quality AI",
    "XLSForm-aware validation for schema, requiredness, row logic, duplicates, and numeric anomalies.",
    "Quality",
)

df = load_app_data()
engine = DataEngine(df)
clean_df = engine.get_clean_data()
quality = engine.get_quality_summary()
survey_df, choices_df = load_form_reference()

numeric_candidates = [
    "B.2.1. Family size (# of Individuals)",
    "B.3.1.Number of Boys",
    "B.3.2.Number of Girls",
    "B.3.3.Number of Women",
    "B.3.4.Number of Men",
    "E.4.What amount of cash did your family receive?",
    "C.1.What is your HH average income (AFN) per month?",
]
ai_df = clean_df.copy()
for column in numeric_candidates:
    if column in ai_df.columns:
        ai_df[column] = pd.to_numeric(ai_df[column], errors="coerce")

ai_engine = AIQualityEngine(ai_df)
basic_report = ai_engine.generate_quality_report()
form_report = build_form_quality_report(clean_df, survey_df, choices_df)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows", format_number(quality["rows"]))
c2.metric("Mapped Form Questions", format_number(form_report["schema_summary"]["mapped_questions"]))
c3.metric("Duplicate UUIDs", format_number(quality["duplicate_uuid"]))
c4.metric("Form Row Issues", format_number(len(form_report["row_issues_df"])))

overview_tab, form_tab, missing_tab, issues_tab, outlier_tab = st.tabs(
    ["Overview", "Form Logic", "Requiredness", "Row Issues", "Outliers"]
)

with overview_tab:
    open_panel()
    overview_df = pd.DataFrame(
        [
            ("Raw rows", quality["rows"]),
            ("Raw columns", quality["columns"]),
            ("Mapped XLSForm questions", form_report["schema_summary"]["mapped_questions"]),
            ("Unmapped raw columns", len(form_report["schema_summary"]["unmapped_raw_columns"])),
            ("Unexpected provinces", len(quality["unexpected_provinces"])),
            ("Unexpected interviewers", len(quality["unexpected_interviewers"])),
            ("Duplicate _uuid", quality["duplicate_uuid"]),
            ("Duplicate _id", quality["duplicate_id"]),
        ],
        columns=["metric", "value"],
    )
    st.dataframe(overview_df, use_container_width=True, hide_index=True)

    if quality["unexpected_provinces"]:
        st.warning("Unexpected provinces: " + ", ".join(quality["unexpected_provinces"]))
    if quality["unexpected_interviewers"]:
        st.warning("Unexpected interviewers: " + ", ".join(quality["unexpected_interviewers"]))
    if form_report["schema_summary"]["unmapped_raw_columns"]:
        st.info(
            "Unmapped raw columns: "
            + ", ".join(form_report["schema_summary"]["unmapped_raw_columns"][:30])
        )
    close_panel()

with form_tab:
    open_panel()
    catalog_df = form_report["catalog_df"].copy()
    view_columns = [
        "column_name",
        "field_name",
        "type",
        "label_dari",
        "label_pashto",
        "relevant",
    ]
    st.dataframe(catalog_df[view_columns], width="stretch", hide_index=True, height=420)
    close_panel()

with missing_tab:
    open_panel()
    required_df = form_report["required_df"].copy()
    if required_df.empty:
        st.success("No required-question metadata was found in the XLSForm.")
    else:
        st.dataframe(required_df, width="stretch", hide_index=True, height=420)
    close_panel()

with issues_tab:
    open_panel()
    row_issues_df = form_report["row_issues_df"].copy()
    if row_issues_df.empty:
        st.success("No row-level form logic issues were detected in the current checks.")
    else:
        st.dataframe(row_issues_df, width="stretch", hide_index=True, height=420)
    close_panel()

with outlier_tab:
    open_panel()
    outlier_df = pd.DataFrame(
        [{"column": column, "outlier_count": count} for column, count in basic_report["outliers"].items()]
    ).sort_values("outlier_count", ascending=False)
    if outlier_df.empty:
        st.info("No numeric columns were available for outlier checks.")
    else:
        st.dataframe(outlier_df, width="stretch", hide_index=True)
    close_panel()
