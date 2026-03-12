import altair as alt
import pandas as pd
import streamlit as st

from design.theme import apply_liquid_glass_theme, close_panel, open_panel, render_page_header
from core.app_data import load_app_data
from core.data_engine import (
    PDME_DATE_COLUMN,
    SUBMISSION_DATE_COLUMN,
    UUID_COLUMN,
    DataEngine,
)
from utils.formatters import dataframe_to_csv_bytes, format_number


def build_unique_column_names(columns) -> list[str]:
    counts = {}
    unique_names = []
    for column in columns:
        label = str(column).strip()
        counts[label] = counts.get(label, 0) + 1
        if counts[label] == 1:
            unique_names.append(label)
        else:
            unique_names.append(f"{label} [{counts[label]}]")
    return unique_names


def build_display_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    display_df = df.copy()
    unique_names = build_unique_column_names(display_df.columns)
    mapping = dict(zip(unique_names, df.columns))
    display_df.columns = unique_names
    return display_df, mapping


def safe_series(df: pd.DataFrame, column_name: str) -> pd.Series:
    selected = df.loc[:, column_name]
    if isinstance(selected, pd.DataFrame):
        return selected.iloc[:, 0]
    return selected


def filter_records(
    df: pd.DataFrame,
    provinces: list[str],
    districts: list[str],
    genders: list[str],
    interviewers: list[str],
    target_scope_only: bool,
    search_text: str,
    start_date,
    end_date,
    date_field: str,
) -> pd.DataFrame:
    filtered = df.copy()

    if provinces:
        filtered = filtered[filtered["province"].isin(provinces)]
    if districts:
        filtered = filtered[filtered["district"].isin(districts)]
    if genders:
        filtered = filtered[filtered["gender"].isin(genders)]
    if interviewers:
        filtered = filtered[filtered["interviewer_name"].isin(interviewers)]
    if target_scope_only:
        filtered = filtered[filtered["is_target_province"]]

    if date_field in filtered.columns:
        date_series = pd.to_datetime(filtered[date_field], errors="coerce")
        if start_date is not None:
            filtered = filtered[date_series >= pd.Timestamp(start_date)]
            date_series = pd.to_datetime(filtered[date_field], errors="coerce")
        if end_date is not None:
            filtered = filtered[date_series <= pd.Timestamp(end_date)]

    query = (search_text or "").strip().lower()
    if query:
        searchable_columns = [
            column
            for column in [
                UUID_COLUMN,
                "A.1.Interviewer name",
                "interviewer_name",
                "B.1.Beneficiary/Respondent name",
                "B.2.Father name",
                "B.3.Contact #",
                "province",
                "district",
            ]
            if column in filtered.columns
        ]
        if searchable_columns:
            mask = pd.Series(False, index=filtered.index)
            for column in searchable_columns:
                mask = mask | safe_series(filtered, column).astype(str).str.lower().str.contains(query, na=False)
            filtered = filtered[mask]

    return filtered


st.set_page_config(page_title="Data Explorer", layout="wide")

apply_liquid_glass_theme()
render_page_header(
    "Data Explorer",
    "Interactive exploration of live Kobo records with safe duplicate-column handling and filtered exports.",
    "Explorer",
)

df = load_app_data()
engine = DataEngine(df)
clean_df = engine.get_clean_data()
display_df, _ = build_display_dataframe(clean_df)

province_options = sorted(value for value in clean_df["province"].dropna().unique().tolist() if value)
selected_provinces = st.multiselect("Province", province_options)

district_source = clean_df if not selected_provinces else clean_df[clean_df["province"].isin(selected_provinces)]
district_options = sorted(value for value in district_source["district"].dropna().unique().tolist() if value)
selected_districts = st.multiselect("District", district_options)

gender_options = sorted(value for value in clean_df["gender"].dropna().unique().tolist() if value)
selected_genders = st.multiselect("Gender", gender_options, default=gender_options)

interviewer_options = sorted(value for value in clean_df["interviewer_name"].dropna().unique().tolist() if value)
selected_interviewers = st.multiselect("Enumerator", interviewer_options)

control_col1, control_col2, control_col3 = st.columns((1.2, 1, 1))
with control_col1:
    search_text = st.text_input("Search", placeholder="Search by _uuid, name, phone, province, district")
with control_col2:
    date_field = st.selectbox(
        "Date field",
        [field for field in [SUBMISSION_DATE_COLUMN, PDME_DATE_COLUMN] if field in clean_df.columns],
    )
with control_col3:
    target_scope_only = st.checkbox("Target provinces only", value=False)

date_col1, date_col2 = st.columns(2)
date_series = pd.to_datetime(clean_df[date_field], errors="coerce") if date_field in clean_df.columns else pd.Series(dtype="datetime64[ns]")
default_min = date_series.min().date() if not date_series.dropna().empty else None
default_max = date_series.max().date() if not date_series.dropna().empty else None
with date_col1:
    start_date = st.date_input("From date", value=default_min) if default_min else None
with date_col2:
    end_date = st.date_input("To date", value=default_max) if default_max else None

filtered_clean_df = filter_records(
    clean_df,
    selected_provinces,
    selected_districts,
    selected_genders,
    selected_interviewers,
    target_scope_only,
    search_text,
    start_date,
    end_date,
    date_field,
)
filtered_display_df, _ = build_display_dataframe(filtered_clean_df)

open_panel()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Filtered Rows", format_number(len(filtered_clean_df)))
m2.metric("Unique UUIDs", format_number(filtered_clean_df[UUID_COLUMN].nunique() if UUID_COLUMN in filtered_clean_df.columns else 0))
m3.metric("Filtered Provinces", format_number(filtered_clean_df["province"].nunique()))
m4.metric("Filtered Districts", format_number(filtered_clean_df["district"].nunique()))
close_panel()

overview_tab, records_tab, profiler_tab = st.tabs(["Overview", "Records", "Field Profiler"])

with overview_tab:
    top_left, top_right = st.columns(2)

    with top_left:
        open_panel()
        st.subheader("Province Distribution")
        province_counts = (
            filtered_clean_df["province"]
            .replace("", pd.NA)
            .dropna()
            .value_counts()
            .rename_axis("province")
            .reset_index(name="records")
        )
        if province_counts.empty:
            st.info("No province data in the current filter.")
        else:
            province_chart = (
                alt.Chart(province_counts.head(12))
                .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, color="#0f766e")
                .encode(
                    x=alt.X("records:Q", title="Records"),
                    y=alt.Y("province:N", sort="-x", title="Province"),
                    tooltip=["province", "records"],
                )
                .properties(height=340)
            )
            st.altair_chart(province_chart, width="stretch")
        close_panel()

    with top_right:
        open_panel()
        st.subheader("Enumerator Distribution")
        interviewer_counts = (
            filtered_clean_df["interviewer_name"]
            .replace("", pd.NA)
            .dropna()
            .value_counts()
            .rename_axis("interviewer_name")
            .reset_index(name="records")
        )
        if interviewer_counts.empty:
            st.info("No interviewer data in the current filter.")
        else:
            interviewer_chart = (
                alt.Chart(interviewer_counts.head(12))
                .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, color="#1d4ed8")
                .encode(
                    x=alt.X("records:Q", title="Records"),
                    y=alt.Y("interviewer_name:N", sort="-x", title="Enumerator"),
                    tooltip=["interviewer_name", "records"],
                )
                .properties(height=340)
            )
            st.altair_chart(interviewer_chart, width="stretch")
        close_panel()

    bottom_left, bottom_right = st.columns(2)

    with bottom_left:
        open_panel()
        st.subheader("District Distribution")
        district_counts = (
            filtered_clean_df.groupby(["province", "district"])
            .size()
            .reset_index(name="records")
            .sort_values(["records", "province"], ascending=[False, True])
        )
        st.dataframe(district_counts.head(25), width="stretch", hide_index=True, height=340)
        close_panel()

    with bottom_right:
        open_panel()
        st.subheader("Top Missing Fields")
        missing_df = (
            filtered_display_df.replace("", pd.NA).isna().sum().sort_values(ascending=False).reset_index()
        )
        missing_df.columns = ["field", "missing_count"]
        missing_df = missing_df[missing_df["missing_count"] > 0]
        if missing_df.empty:
            st.success("No missing values detected in the current filtered view.")
        else:
            st.dataframe(missing_df.head(25), width="stretch", hide_index=True, height=340)
        close_panel()

with records_tab:
    open_panel()
    default_columns = [
        "province",
        "district",
        "gender",
        "interviewer_name",
        "A.1.Interviewer name",
        "B.1.Beneficiary/Respondent name",
        "B.3.Contact #",
        PDME_DATE_COLUMN,
        SUBMISSION_DATE_COLUMN,
        UUID_COLUMN,
    ]
    available_defaults = [column for column in default_columns if column in filtered_display_df.columns]
    selected_columns = st.multiselect(
        "Columns to display",
        filtered_display_df.columns.tolist(),
        default=available_defaults,
    )
    records_limit = st.slider("Rows to display", 25, 500, 100, step=25)
    view_df = filtered_display_df[selected_columns] if selected_columns else filtered_display_df
    st.dataframe(view_df.head(records_limit), width="stretch", hide_index=True, height=500)
    close_panel()

with profiler_tab:
    open_panel()
    profiled_column = st.selectbox("Choose a field to profile", filtered_display_df.columns.tolist())
    profile_series = safe_series(filtered_display_df, profiled_column).astype(str).fillna("").str.strip()
    non_blank_series = profile_series[profile_series != ""]

    p1, p2, p3 = st.columns(3)
    p1.metric("Non-empty rows", format_number(len(non_blank_series)))
    p2.metric("Unique values", format_number(non_blank_series.nunique()))
    p3.metric("Missing values", format_number((profile_series == "").sum()))

    top_values = (
        non_blank_series.value_counts()
        .rename_axis("value")
        .reset_index(name="count")
        .head(40)
    )
    if top_values.empty:
        st.info("No non-empty values found for this field.")
    else:
        top_values_chart = (
            alt.Chart(top_values.head(20))
            .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, color="#a16207")
            .encode(
                x=alt.X("count:Q", title="Count"),
                y=alt.Y("value:N", sort="-x", title="Value"),
                tooltip=["value", "count"],
            )
            .properties(height=420)
        )
        left, right = st.columns((1.2, 1))
        with left:
            st.altair_chart(top_values_chart, width="stretch")
        with right:
            st.dataframe(top_values, width="stretch", hide_index=True, height=420)
    close_panel()

st.download_button(
    "Download filtered CSV",
    data=dataframe_to_csv_bytes(filtered_display_df),
    file_name="cash_for_nfi_filtered_data.csv",
    mime="text/csv",
)
