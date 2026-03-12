import pandas as pd
import streamlit as st

from core.data_engine import UUID_COLUMN
from design.theme import apply_liquid_glass_theme, render_page_header
from services.correction_log_service import (
    append_corrections,
    build_correction_rows,
    build_value_mapping_frame,
)
from services.data_loader import load_google_sheet
from services.google_sheets_service import get_worksheet
from services.xlsform_service import (
    build_question_catalog,
    build_relevant_question_context,
    find_question_for_column,
    get_choices_for_question,
    is_text_question,
    load_xlsform,
    resolve_xlsform_path,
)
from utils.formatters import format_number


RAW_SHEET = "Raw_Kobo_Data"
CORRECTION_SHEET = "Correction_Log"


@st.cache_data(show_spinner=False, ttl=300)
def load_translation_context():
    survey_df, choices_df = load_xlsform(resolve_xlsform_path("."))
    raw_ws = get_worksheet(
        st.secrets["gcp_service_account"],
        st.secrets["app"]["spreadsheet_id"],
        RAW_SHEET,
    )
    raw_df = load_google_sheet(raw_ws)
    catalog_df = build_question_catalog(raw_df.columns.tolist(), survey_df)
    return raw_df, survey_df, choices_df, catalog_df


def render_translation_tab(tab_key: str, question_options_df: pd.DataFrame, raw_df: pd.DataFrame, survey_df: pd.DataFrame, choices_df: pd.DataFrame):
    if question_options_df.empty:
        st.info("No questions are available in this tab.")
        return

    option_map = {
        f"{row['label_en']} [{row['field_name']}]": row["column_name"]
        for _, row in question_options_df.iterrows()
    }
    selected_label = st.selectbox(
        "Question",
        list(option_map.keys()),
        key=f"question_{tab_key}",
    )
    selected_column = option_map[selected_label]
    question = find_question_for_column(selected_column, survey_df)
    question_choices = get_choices_for_question(question, choices_df) if question else pd.DataFrame()
    relevant_context = build_relevant_question_context(question, survey_df) if question and tab_key == "general" else []

    context_col, choice_col = st.columns((1.3, 1))
    with context_col:
        st.markdown("**Question**")
        st.write(question.get("label::English (en)", selected_column))
        if question.get("label::Dari (prs)"):
            st.caption("Dari: " + str(question.get("label::Dari (prs)", "")))
        if question.get("label::Pashto (ps)"):
            st.caption("Pashto: " + str(question.get("label::Pashto (ps)", "")))
        if tab_key == "general" and question.get("relevant", ""):
                st.markdown("**Question is relevant**")
                st.dataframe(relevant_context, width="stretch", hide_index=True)

    with choice_col:
        st.markdown("**Choices**")
        if question_choices.empty:
            st.caption("No choice list")
        else:
            st.dataframe(question_choices, width="stretch", hide_index=True)

    mapping_df = build_value_mapping_frame(raw_df, selected_column, question_choices)
    if mapping_df.empty:
        st.info("No non-empty values were found for this question.")
        return

    max_rows = st.slider("Rows to review", 10, 200, 50, key=f"max_rows_{tab_key}")
    filtered_mapping_df = mapping_df.head(max_rows).copy()

    if question_choices.empty:
        editor = st.data_editor(
            filtered_mapping_df,
            width="stretch",
            hide_index=True,
            num_rows="fixed",
            key=f"editor_{tab_key}",
            column_config={
                "old_value": st.column_config.TextColumn("Current Value", disabled=True),
                "record_count": st.column_config.NumberColumn("Count", disabled=True),
                "suggested_value": st.column_config.TextColumn("Suggested", disabled=True),
                "new_value": st.column_config.TextColumn("New English Value"),
            },
        )
    else:
        choice_options = question_choices["label::English (en)"].astype(str).str.strip().tolist()
        editor = st.data_editor(
            filtered_mapping_df,
            width="stretch",
            hide_index=True,
            num_rows="fixed",
            key=f"editor_{tab_key}",
            column_config={
                "old_value": st.column_config.TextColumn("Current Value", disabled=True),
                "record_count": st.column_config.NumberColumn("Count", disabled=True),
                "suggested_value": st.column_config.TextColumn("Suggested", disabled=True),
                "new_value": st.column_config.SelectboxColumn("New English Value", options=choice_options),
            },
        )

    translated_by, assigned_to = st.columns(2)
    translated_by_value = translated_by.text_input("Translated by", key=f"translated_by_{tab_key}")


    correction_preview = build_correction_rows(
        raw_df,
        selected_column,
        editor,
        question_identifier=str(question.get("name", "")).strip() or selected_column,
        translated_by=translated_by_value,
    )

    st.caption(
        f"Pending correction log rows: {format_number(len(correction_preview))}. Changes are saved only to `Correction_Log`, not to `Raw_Kobo_Data`."
    )

    if not correction_preview.empty:
        st.dataframe(correction_preview.head(30), width="stretch", hide_index=True)

    if st.button("Save to Correction Log", type="primary", key=f"save_{tab_key}"):
        correction_ws = get_worksheet(
            st.secrets["gcp_service_account"],
            st.secrets["app"]["spreadsheet_id"],
            CORRECTION_SHEET,
        )
        added = append_corrections(correction_ws, correction_preview)
        st.success(f"{added} correction rows were added to `{CORRECTION_SHEET}`.")


st.set_page_config(page_title="Translation Studio", layout="wide")

apply_liquid_glass_theme()
render_page_header(
    "Translation Studio",
    "Review live answers, inspect XLSForm context, and write proposed translations or choice corrections into Correction Log.",
    "Translation",
)

raw_df, survey_df, choices_df, catalog_df = load_translation_context()

general_questions = catalog_df.copy()
text_questions = catalog_df[catalog_df["type"].map(is_text_question)].copy()

summary1, summary2, summary3 = st.columns(3)
summary1.metric("Raw rows", format_number(len(raw_df)))
summary2.metric("Questions in form", format_number(len(general_questions)))
summary3.metric("Text questions", format_number(len(text_questions)))

general_tab, text_tab = st.tabs(["General Questions", "Text Questions"])

with general_tab:
    render_translation_tab("general", general_questions, raw_df, survey_df, choices_df)

with text_tab:
    render_translation_tab("text", text_questions, raw_df, survey_df, choices_df)
