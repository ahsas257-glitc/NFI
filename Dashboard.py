import altair as alt
import pandas as pd
import streamlit as st

from analytics.kpi_engine import build_kpi_snapshot
from analytics.segmentation_engine import build_count_distribution
from analytics.trend_engine import build_daily_trend
from design.components import render_metric_row
from design.theme import apply_liquid_glass_theme, close_panel, open_panel, render_page_header
from core.app_data import load_app_data
from core.data_engine import DataEngine, PDME_DATE_COLUMN, SUBMISSION_DATE_COLUMN
from utils.formatters import format_number, format_percent


ASSISTANCE_COLUMN = "E.2.Which kind of assistance did your family receive?"
BENEFICIARY_COLUMN = "A.2.1.Type of beneficiary"
MODALITY_COLUMN = "I.4.What modality of assistance do you prefer?"
SATISFACTION_COLUMN = "J.1.Are you satisfied with the assistance provided by IOM?"
RAW_GENDER_COLUMN = "B.1.3.Respondent gender"


def prepare_trend_data(df: pd.DataFrame, date_column: str) -> pd.DataFrame:
    return build_daily_trend(df, date_column)


def prepare_count_df(df: pd.DataFrame, column_name: str, label: str) -> pd.DataFrame:
    return build_count_distribution(df, column_name, label)


def classify_completion_status(value: float) -> str:
    if value >= 100:
        return "On or above target"
    if value >= 70:
        return "Advancing"
    if value > 0:
        return "Behind target"
    return "No progress"


def prepare_team_view(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "province",
                "district",
                "enumerator_name",
                "target_male",
                "received_male",
                "remaining_male",
                "target_female",
                "received_female",
                "remaining_female",
                "total_target",
                "total_received",
                "completion_total",
                "team_status",
            ]
        )
    team_df = df.copy()
    team_df["district"] = team_df["district"].replace("", "Province-wide")
    team_df["completion_total"] = team_df.apply(
        lambda row: round((row["total_received"] / row["total_target"]) * 100, 1) if row["total_target"] else 0.0,
        axis=1,
    )
    team_df["team_status"] = team_df["completion_total"].map(classify_completion_status)
    return team_df.sort_values(
        ["province", "completion_total", "total_received"],
        ascending=[True, False, False],
    )


def build_status_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["team_status", "teams"])
    return df["team_status"].value_counts().rename_axis("team_status").reset_index(name="teams")


def build_signal_status_counts(district_df: pd.DataFrame, team_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if not district_df.empty:
        rows.extend(
            [
                {"group": "Districts", "status": "Below 70%", "count": int((district_df["progress_total"] < 70).sum())},
                {"group": "Districts", "status": "70-99%", "count": int(((district_df["progress_total"] >= 70) & (district_df["progress_total"] < 100)).sum())},
                {"group": "Districts", "status": "100%+", "count": int((district_df["progress_total"] >= 100).sum())},
            ]
        )
    if not team_df.empty:
        rows.extend(
            [
                {"group": "Teams", "status": "No progress", "count": int((team_df["total_received"] == 0).sum())},
                {"group": "Teams", "status": "In progress", "count": int(((team_df["completion_total"] > 0) & (team_df["completion_total"] < 100)).sum())},
                {"group": "Teams", "status": "100%+", "count": int((team_df["completion_total"] >= 100).sum())},
            ]
        )
    return pd.DataFrame(rows)


def metric_card(label: str, value: str, delta: str | None = None):
    st.metric(label, value, delta=delta)


def build_volume_by_district(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["province", "district", "records"])
    return (
        df.groupby(["province", "district"])
        .size()
        .reset_index(name="records")
        .sort_values(["records", "province", "district"], ascending=[False, True, True])
    )


def build_volume_by_interviewer(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "interviewer_name" not in df.columns:
        return pd.DataFrame(columns=["interviewer_name", "records"])
    return (
        df["interviewer_name"]
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .rename_axis("interviewer_name")
        .reset_index(name="records")
    )


def build_remaining_gap_df(df: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=group_columns + ["remaining_total"])
    keep_columns = [column for column in group_columns + ["remaining_total", "progress_total", "actual_total", "target_total"] if column in df.columns]
    return df[keep_columns].sort_values(["remaining_total", "progress_total"], ascending=[False, True])


def build_district_target_delivery_table(team_df: pd.DataFrame) -> pd.DataFrame:
    if team_df.empty:
        return pd.DataFrame(
            columns=[
                "Province",
                "District",
                "Target Male",
                "Received Male",
                "Remaining Male",
                "Target Female",
                "Received Female",
                "Remaining Female",
                "Enumerator Name",
                "Data Recieved",
            ]
        )

    delivery_df = team_df.copy()
    delivery_df["District"] = delivery_df["district"].replace("Province-wide", "")
    delivery_df["Data Recieved"] = delivery_df["total_received"]
    delivery_df = delivery_df.rename(
        columns={
            "province": "Province",
            "target_male": "Target Male",
            "received_male": "Received Male",
            "remaining_male": "Remaining Male",
            "target_female": "Target Female",
            "received_female": "Received Female",
            "remaining_female": "Remaining Female",
            "enumerator_name": "Enumerator Name",
        }
    )
    selected_columns = [
        "Province",
        "District",
        "Target Male",
        "Received Male",
        "Remaining Male",
        "Target Female",
        "Received Female",
        "Remaining Female",
        "Enumerator Name",
        "Data Recieved",
    ]
    return delivery_df[selected_columns].sort_values(
        ["Province", "District", "Enumerator Name"],
        ascending=[True, True, True],
    )


def style_chart(chart: alt.Chart | alt.LayerChart | alt.HConcatChart | alt.VConcatChart):
    return (
        chart.configure(background="transparent")
        .configure_view(strokeWidth=0)
        .configure_axis(
            labelColor="#e7f1ff",
            titleColor="#e7f1ff",
            gridColor="rgba(255,255,255,0.08)",
            domainColor="rgba(255,255,255,0.12)",
            tickColor="rgba(255,255,255,0.12)",
            labelLimit=140,
            titlePadding=10,
        )
        .configure_legend(
            orient="bottom",
            direction="horizontal",
            labelColor="#e7f1ff",
            titleColor="#e7f1ff",
            symbolLimit=12,
            columns=2,
            labelLimit=180,
            padding=8,
        )
        .configure_title(color="#f8fbff")
    )


def show_altair_or_info(chart_df: pd.DataFrame, message: str, chart_builder):
    if chart_df.empty:
        st.info(message)
    else:
        st.altair_chart(style_chart(chart_builder(chart_df)), width="stretch")


st.set_page_config(page_title="Dashboard", layout="wide")

apply_liquid_glass_theme()
render_page_header(
    "Dashboard",
    "Executive monitoring across target geography, assistance composition, and team delivery performance.",
    "Executive",
)

df = load_app_data()
engine = DataEngine(df)
clean_df = engine.get_clean_data()
target_df = engine.get_target_data()

overview = engine.get_overview_metrics()
province_progress = engine.get_province_progress()
district_progress = engine.get_district_progress()
gender_summary = engine.get_gender_summary()
enumerator_progress = engine.get_enumerator_progress()

control1, control2, control3 = st.columns((1.2, 1, 1))
with control1:
    scope_mode = st.selectbox("Scope", ["Target Provinces", "All Provinces"], index=0)
with control2:
    selected_province = st.selectbox("Province", ["All"] + sorted(province_progress["province"].tolist()), index=0)
with control3:
    date_mode = st.selectbox("Trend Date", [SUBMISSION_DATE_COLUMN, PDME_DATE_COLUMN], index=0)

working_df = target_df.copy() if scope_mode == "Target Provinces" else clean_df.copy()
if selected_province != "All":
    working_df = working_df[working_df["province"] == selected_province]

working_province_progress = province_progress.copy()
working_district_progress = district_progress.copy()
working_enumerator_progress = enumerator_progress.copy()
if selected_province != "All":
    working_province_progress = working_province_progress[working_province_progress["province"] == selected_province]
    working_district_progress = working_district_progress[working_district_progress["province"] == selected_province]
    working_enumerator_progress = working_enumerator_progress[working_enumerator_progress["province"] == selected_province]

team_view = prepare_team_view(working_enumerator_progress)
team_status_df = build_status_summary(team_view)
trend_df = prepare_trend_data(working_df, date_mode)
beneficiary_df = prepare_count_df(working_df, BENEFICIARY_COLUMN, "beneficiary_type")
assistance_df = prepare_count_df(working_df, ASSISTANCE_COLUMN, "assistance_type")
modality_df = prepare_count_df(working_df, MODALITY_COLUMN, "preferred_modality")
satisfaction_df = prepare_count_df(working_df, SATISFACTION_COLUMN, "satisfaction")
response_gender_df = prepare_count_df(working_df, RAW_GENDER_COLUMN, "response_gender")

signal_status_df = build_signal_status_counts(working_district_progress, team_view)
district_volume_df = build_volume_by_district(working_df)
interviewer_volume_df = build_volume_by_interviewer(working_df)
district_gap_df = build_remaining_gap_df(working_district_progress, ["province", "district"])
province_gap_df = build_remaining_gap_df(working_province_progress, ["province"])
district_delivery_table = build_district_target_delivery_table(team_view)

kpi_snapshot = build_kpi_snapshot(overview, working_df, working_province_progress)
render_metric_row(
    [
        {
            "label": item["label"],
            "value": format_number(item["value"]) if isinstance(item["value"], int) else item["value"],
            "delta": item.get("delta"),
        }
        for item in kpi_snapshot
    ]
)

executive_tab, geography_tab, assistance_tab, target_tab, team_tab = st.tabs(
    ["Executive", "Geography", "Assistance", "Targets", "Teams"]
)

with executive_tab:
    top_left, top_right = st.columns(2)
    with top_left:
        open_panel()
        st.subheader("Province Target vs Actual")
        province_chart_data = working_province_progress.melt(
            id_vars="province",
            value_vars=["target_total", "actual_total"],
            var_name="series",
            value_name="records",
        )
        show_altair_or_info(
            province_chart_data,
            "No province progress data available.",
            lambda chart_df: (
                alt.Chart(chart_df)
                .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
                .encode(
                    x=alt.X("province:N", title="Province"),
                    y=alt.Y("records:Q", title="Interviews"),
                    xOffset="series:N",
                    color=alt.Color(
                        "series:N",
                        scale=alt.Scale(domain=["target_total", "actual_total"], range=["#c2410c", "#0f766e"]),
                        title="Series",
                    ),
                    tooltip=["province", "series", "records"],
                )
                .properties(height=340)
            ),
        )
        close_panel()
    with top_right:
        open_panel()
        st.subheader("Collection Trend")
        show_altair_or_info(
            trend_df,
            "No trend data available for the selected date field.",
            lambda chart_df: (
                alt.Chart(chart_df)
                .mark_line(point=True, strokeWidth=3, color="#1d4ed8")
                .encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y("records:Q", title="Records"),
                    tooltip=["date", "records"],
                )
                .properties(height=340)
            ),
        )
        close_panel()

    signal_left, signal_mid = st.columns(2)
    with signal_left:
        open_panel()
        st.subheader("Province Completion %")
        province_completion_df = working_province_progress[["province", "progress_total"]].copy()
        show_altair_or_info(
            province_completion_df,
            "No province completion data available.",
            lambda chart_df: (
                alt.Chart(chart_df)
                .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
                .encode(
                    x=alt.X("progress_total:Q", title="Completion %"),
                    y=alt.Y("province:N", sort="-x", title="Province"),
                    color=alt.Color(
                        "progress_total:Q",
                        scale=alt.Scale(domain=[0, 100, 130], range=["#b91c1c", "#d97706", "#15803d"]),
                        title="Completion %",
                    ),
                    tooltip=["province", "progress_total"],
                )
                .properties(height=320)
            ),
        )
        close_panel()
    with signal_mid:
        open_panel()
        st.subheader("District and Team Status")
        show_altair_or_info(
            signal_status_df,
            "No status signal data available.",
            lambda chart_df: (
                alt.Chart(chart_df)
                .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
                .encode(
                    x=alt.X("count:Q", title="Rows"),
                    y=alt.Y("status:N", title="Status", sort="-x"),
                    color=alt.Color("group:N", scale=alt.Scale(range=["#1d4ed8", "#0f766e"]), title="Group"),
                    tooltip=["group", "status", "count"],
                )
                .properties(height=320)
            ),
        )
        close_panel()

    bottom_left, bottom_right = st.columns(2)
    with bottom_left:
        open_panel()
        st.subheader("Gender Progress")
        gender_chart_data = gender_summary.melt(
            id_vars="gender",
            value_vars=["target", "actual"],
            var_name="series",
            value_name="records",
        )
        st.altair_chart(
            style_chart(
                (
                alt.Chart(gender_chart_data)
                .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
                .encode(
                    x=alt.X("gender:N", title="Gender"),
                    y=alt.Y("records:Q", title="Records"),
                    xOffset="series:N",
                    color=alt.Color(
                        "series:N",
                        scale=alt.Scale(domain=["target", "actual"], range=["#7c3aed", "#0891b2"]),
                        title="Series",
                    ),
                    tooltip=["gender", "series", "records"],
                )
                .properties(height=340)
                )
            ),
            width="stretch",
        )
        close_panel()
    with bottom_right:
        open_panel()
        st.subheader("Scope Composition")
        scope_df = pd.DataFrame(
            [
                {"segment": "Target Scope", "records": overview["target_scope_records"]},
                {"segment": "Outside Scope", "records": overview["extra_scope_records"]},
            ]
        )
        show_altair_or_info(
            scope_df,
            "No scope composition data available.",
            lambda chart_df: (
                alt.Chart(chart_df)
                .mark_arc(innerRadius=72, outerRadius=128)
                .encode(
                    theta="records:Q",
                    color=alt.Color(
                        "segment:N",
                        scale=alt.Scale(
                            domain=["Target Scope", "Outside Scope"],
                            range=["#0f766e", "#f59e0b"],
                        ),
                        title="Scope",
                    ),
                    tooltip=["segment", "records"],
                )
                .properties(height=340)
            ),
        )
        close_panel()

    extra_left, extra_right = st.columns(2)
    with extra_left:
        open_panel()
        st.subheader("Top District Volume")
        show_altair_or_info(
            district_volume_df.head(10),
            "No district volume data available.",
            lambda chart_df: (
                alt.Chart(chart_df)
                .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
                .encode(
                    x=alt.X("records:Q", title="Records"),
                    y=alt.Y("district:N", sort="-x", title="District"),
                    color=alt.Color("province:N", title="Province"),
                    tooltip=["province", "district", "records"],
                )
                .properties(height=340)
            ),
        )
        close_panel()
    with extra_right:
        open_panel()
        st.subheader("Enumerator Activity")
        show_altair_or_info(
            interviewer_volume_df.head(10),
            "No enumerator activity data available.",
            lambda chart_df: (
                alt.Chart(chart_df)
                .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8, color="#38bdf8")
                .encode(
                    x=alt.X("records:Q", title="Records"),
                    y=alt.Y("interviewer_name:N", sort="-x", title="Enumerator"),
                    tooltip=["interviewer_name", "records"],
                )
                .properties(height=340)
            ),
        )
        close_panel()

with geography_tab:
    geo_top_left, geo_top_right = st.columns((1, 1))
    with geo_top_left:
        open_panel()
        st.subheader("District Progress Heatmap")
        heatmap_df = (
            working_district_progress[["district", "province", "progress_total"]]
            if not working_district_progress.empty
            else pd.DataFrame(columns=["district", "province", "progress_total"])
        )
        show_altair_or_info(
            heatmap_df,
            "No district progress data available.",
            lambda chart_df: (
                alt.Chart(chart_df)
                .mark_rect(cornerRadius=6)
                .encode(
                    x=alt.X("province:N", title="Province"),
                    y=alt.Y("district:N", title="District", sort="-x"),
                    color=alt.Color(
                        "progress_total:Q",
                        scale=alt.Scale(domain=[0, 100, 130], range=["#991b1b", "#d97706", "#15803d"]),
                        title="Completion %",
                    ),
                    tooltip=["province", "district", "progress_total"],
                )
                .properties(height=420)
            ),
        )
        close_panel()
    with geo_top_right:
        open_panel()
        st.subheader("Province Male vs Female Mix")
        province_gender_df = working_df.groupby(["province", "gender"]).size().reset_index(name="records")
        show_altair_or_info(
            province_gender_df,
            "No province gender mix data available.",
            lambda chart_df: (
                alt.Chart(chart_df)
                .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
                .encode(
                    x=alt.X("province:N", title="Province"),
                    y=alt.Y("records:Q", title="Records"),
                    color=alt.Color(
                        "gender:N",
                        scale=alt.Scale(range=["#2563eb", "#ec4899", "#64748b"]),
                        title="Gender",
                    ),
                    tooltip=["province", "gender", "records"],
                )
                .properties(height=420)
            ),
        )
        close_panel()
    open_panel()
    st.subheader("Province Progress Table")
    province_view = working_province_progress.copy()
    if not province_view.empty:
        province_view["progress_total"] = province_view["progress_total"].map(format_percent)
        province_view["progress_male"] = province_view["progress_male"].map(format_percent)
        province_view["progress_female"] = province_view["progress_female"].map(format_percent)
    st.dataframe(province_view, width="stretch", hide_index=True, height=320)
    close_panel()

    geo_bottom_left, geo_bottom_right = st.columns(2)
    with geo_bottom_left:
        open_panel()
        st.subheader("District Remaining Gap")
        show_altair_or_info(
            district_gap_df.head(12),
            "No district gap data available.",
            lambda chart_df: (
                alt.Chart(chart_df)
                .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8, color="#f59e0b")
                .encode(
                    x=alt.X("remaining_total:Q", title="Remaining interviews"),
                    y=alt.Y("district:N", sort="-x", title="District"),
                    tooltip=["province", "district", "remaining_total", "progress_total"],
                )
                .properties(height=360)
            ),
        )
        close_panel()
    with geo_bottom_right:
        open_panel()
        st.subheader("District Progress Table")
        st.dataframe(district_gap_df.head(15), width="stretch", hide_index=True, height=360)
        close_panel()

with assistance_tab:
    assist_top_left, assist_top_right = st.columns(2)
    with assist_top_left:
        open_panel()
        st.subheader("Beneficiary Type")
        show_altair_or_info(
            beneficiary_df.head(8),
            "No beneficiary type data available.",
            lambda chart_df: (
                alt.Chart(chart_df)
                .mark_arc(innerRadius=58, outerRadius=118)
                .encode(
                    theta="records:Q",
                    color=alt.Color("beneficiary_type:N", legend=alt.Legend(title="Type")),
                    tooltip=["beneficiary_type", "records"],
                )
                .properties(height=320)
            ),
        )
        close_panel()
    with assist_top_right:
        open_panel()
        st.subheader("Assistance Type")
        show_altair_or_info(
            assistance_df.head(8),
            "No assistance type data available.",
            lambda chart_df: (
                alt.Chart(chart_df)
                .mark_arc(innerRadius=58, outerRadius=118)
                .encode(
                    theta="records:Q",
                    color=alt.Color("assistance_type:N", legend=alt.Legend(title="Assistance")),
                    tooltip=["assistance_type", "records"],
                )
                .properties(height=320)
            ),
        )
        close_panel()
    assist_mid_left, assist_mid_right = st.columns(2)
    with assist_mid_left:
        open_panel()
        st.subheader("Satisfaction")
        show_altair_or_info(
            satisfaction_df,
            "No satisfaction data available.",
            lambda chart_df: (
                alt.Chart(chart_df)
                .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8, color="#16a34a")
                .encode(
                    x=alt.X("satisfaction:N", title="Satisfaction"),
                    y=alt.Y("records:Q", title="Records"),
                    tooltip=["satisfaction", "records"],
                )
                .properties(height=320)
            ),
        )
        close_panel()
    with assist_mid_right:
        open_panel()
        st.subheader("Preferred Assistance Modality")
        show_altair_or_info(
            modality_df.head(8),
            "No preferred modality data available.",
            lambda chart_df: (
                alt.Chart(chart_df)
                .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8, color="#0f766e")
                .encode(
                    x=alt.X("records:Q", title="Records"),
                    y=alt.Y("preferred_modality:N", sort="-x", title="Preferred modality"),
                    tooltip=["preferred_modality", "records"],
                )
                .properties(height=320)
            ),
        )
        close_panel()
    assist_bottom_left, assist_bottom_right = st.columns(2)
    with assist_bottom_left:
        open_panel()
        st.subheader("Response Gender Mix")
        show_altair_or_info(
            response_gender_df,
            "No response gender data available.",
            lambda chart_df: (
                alt.Chart(chart_df)
                .mark_arc(innerRadius=60, outerRadius=122)
                .encode(
                    theta="records:Q",
                    color=alt.Color(
                        "response_gender:N",
                        scale=alt.Scale(range=["#1d4ed8", "#db2777", "#64748b"]),
                        legend=alt.Legend(title="Gender"),
                    ),
                    tooltip=["response_gender", "records"],
                )
                .properties(height=320)
            ),
        )
        close_panel()
    with assist_bottom_right:
        open_panel()
        st.subheader("Satisfaction Table")
        st.dataframe(satisfaction_df, width="stretch", hide_index=True, height=320)
        close_panel()

    assist_extra_left, assist_extra_right = st.columns(2)
    with assist_extra_left:
        open_panel()
        st.subheader("Beneficiary Distribution Table")
        st.dataframe(beneficiary_df, width="stretch", hide_index=True, height=300)
        close_panel()
    with assist_extra_right:
        open_panel()
        st.subheader("Assistance and Modality Table")
        merged_assistance_df = pd.concat(
            [
                assistance_df.rename(columns={"assistance_type": "category"}),
                modality_df.rename(columns={"preferred_modality": "category"}),
            ],
            ignore_index=True,
        )
        st.dataframe(merged_assistance_df, width="stretch", hide_index=True, height=300)
        close_panel()

with target_tab:
    target_chart_tab, target_table_tab = st.tabs(["Charts", "Tables"])
    with target_chart_tab:
        left, right = st.columns(2)
        with left:
            open_panel()
            st.subheader("District Completion")
            show_altair_or_info(
                working_district_progress,
                "No district targets are configured for the selected province.",
                lambda chart_df: (
                    alt.Chart(chart_df)
                    .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
                    .encode(
                        x=alt.X("progress_total:Q", title="Completion %"),
                        y=alt.Y("district:N", sort="-x", title="District"),
                        color=alt.Color(
                            "progress_total:Q",
                            scale=alt.Scale(domain=[0, 100, 130], range=["#b91c1c", "#d97706", "#15803d"]),
                            title="Completion %",
                        ),
                        tooltip=[
                            "province",
                            "district",
                            "target_total",
                            "actual_total",
                            "remaining_total",
                            "progress_total",
                        ],
                    )
                    .properties(height=500)
                ),
            )
            close_panel()
        with right:
            open_panel()
            st.subheader("Province Remaining Gap")
            show_altair_or_info(
                province_gap_df,
                "No province gap data available.",
                lambda chart_df: (
                    alt.Chart(chart_df)
                    .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8, color="#f59e0b")
                    .encode(
                        x=alt.X("remaining_total:Q", title="Remaining interviews"),
                        y=alt.Y("province:N", sort="-x", title="Province"),
                        tooltip=["province", "remaining_total", "progress_total", "actual_total", "target_total"],
                    )
                    .properties(height=500)
                ),
            )
            close_panel()
    with target_table_tab:
        left, right = st.columns(2)
        with left:
            open_panel()
            st.subheader("Province Progress Table")
            province_table = working_province_progress.copy()
            if not province_table.empty:
                province_table["progress_total"] = province_table["progress_total"].map(format_percent)
                province_table["progress_male"] = province_table["progress_male"].map(format_percent)
                province_table["progress_female"] = province_table["progress_female"].map(format_percent)
            st.dataframe(province_table, width="stretch", hide_index=True, height=420)
            close_panel()
        with right:
            open_panel()
            st.subheader("District Target Table")
            district_table = working_district_progress.copy()
            if not district_table.empty:
                district_table["progress_total"] = district_table["progress_total"].map(format_percent)
            st.dataframe(district_table, width="stretch", hide_index=True, height=420)
            close_panel()

        open_panel()
        st.subheader("District Target vs Data Received")
        st.dataframe(district_delivery_table, width="stretch", hide_index=True, height=420)
        close_panel()

with team_tab:
    if team_view.empty:
        st.info("No enumerator target rows available.")
    else:
        open_panel()
        st.subheader("Enumerator and Supervisor Progress")
        active_team_count = int((team_view["total_received"] > 0).sum())
        over_target_count = int((team_view["completion_total"] > 100).sum())
        avg_completion = round(team_view["completion_total"].mean(), 1)
        team_m1, team_m2, team_m3, team_m4, team_m5 = st.columns(5)
        with team_m1:
            metric_card("Team Rows", format_number(len(team_view)))
        with team_m2:
            metric_card("Active Teams", format_number(active_team_count))
        with team_m3:
            metric_card("Over Target", format_number(over_target_count))
        with team_m4:
            metric_card("Team Interviews", format_number(team_view["total_received"].sum()))
        with team_m5:
            metric_card("Avg Completion", format_percent(avg_completion))
        close_panel()

        team_perf_tab, team_mix_tab, team_table_tab = st.tabs(["Performance", "Composition", "Tables"])

        with team_perf_tab:
            left, right = st.columns((1.15, 1))
            with left:
                open_panel()
                st.subheader("Enumerator Completion")
                st.altair_chart(
                    style_chart(
                        (
                        alt.Chart(team_view)
                        .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
                        .encode(
                            x=alt.X("completion_total:Q", title="Completion %"),
                            y=alt.Y("enumerator_name:N", sort="-x", title="Enumerator"),
                            color=alt.Color(
                                "team_status:N",
                                scale=alt.Scale(
                                    domain=["On or above target", "Advancing", "Behind target", "No progress"],
                                    range=["#15803d", "#0ea5e9", "#f59e0b", "#94a3b8"],
                                ),
                                title="Status",
                            ),
                            tooltip=[
                                "province",
                                "district",
                                "enumerator_name",
                                "target_male",
                                "received_male",
                                "target_female",
                                "received_female",
                                "completion_total",
                            ],
                        )
                        .properties(height=500)
                        )
                    ),
                    width="stretch",
                )
                close_panel()
            with right:
                open_panel()
                st.subheader("Target vs Received Bubble")
                st.altair_chart(
                    style_chart(
                        (
                        alt.Chart(team_view)
                        .mark_circle(opacity=0.85, stroke="#0f172a", strokeWidth=0.6)
                        .encode(
                            x=alt.X("total_target:Q", title="Total target"),
                            y=alt.Y("total_received:Q", title="Total received"),
                            size=alt.Size("completion_total:Q", title="Completion %"),
                            color=alt.Color("province:N", title="Province"),
                            tooltip=[
                                "enumerator_name",
                                "province",
                                "district",
                                "total_target",
                                "total_received",
                                "completion_total",
                            ],
                        )
                        .properties(height=500)
                        )
                    ),
                    width="stretch",
                )
                close_panel()

        with team_mix_tab:
            top_left, top_right = st.columns(2)
            with top_left:
                open_panel()
                st.subheader("Enumerator Share")
                share_df = team_view[team_view["total_received"] > 0]
                show_altair_or_info(
                    share_df,
                    "No completed interviews for enumerator share chart.",
                    lambda chart_df: (
                        alt.Chart(chart_df)
                        .mark_arc(innerRadius=72, outerRadius=128)
                        .encode(
                            theta="total_received:Q",
                            color=alt.Color("enumerator_name:N", legend=alt.Legend(title="Enumerator")),
                            tooltip=["enumerator_name", "province", "district", "total_received", "completion_total"],
                        )
                        .properties(height=420)
                    ),
                )
                close_panel()
            with top_right:
                open_panel()
                st.subheader("Team Status Mix")
                show_altair_or_info(
                    team_status_df,
                    "No team status data available.",
                    lambda chart_df: (
                        alt.Chart(chart_df)
                        .mark_arc(innerRadius=72, outerRadius=128)
                        .encode(
                            theta="teams:Q",
                            color=alt.Color(
                                "team_status:N",
                                scale=alt.Scale(
                                    domain=["On or above target", "Advancing", "Behind target", "No progress"],
                                    range=["#15803d", "#0ea5e9", "#f59e0b", "#94a3b8"],
                                ),
                                legend=alt.Legend(title="Status"),
                            ),
                            tooltip=["team_status", "teams"],
                        )
                        .properties(height=420)
                    ),
                )
                close_panel()
            bottom_left, bottom_right = st.columns(2)
            with bottom_left:
                open_panel()
                st.subheader("Male vs Female Coverage")
                gender_mix_df = team_view.melt(
                    id_vars=["enumerator_name", "province", "district"],
                    value_vars=["received_male", "received_female"],
                    var_name="series",
                    value_name="records",
                )
                st.altair_chart(
                    style_chart(
                        (
                        alt.Chart(gender_mix_df)
                        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
                        .encode(
                            x=alt.X("records:Q", title="Received interviews"),
                            y=alt.Y("enumerator_name:N", sort="-x", title="Enumerator"),
                            color=alt.Color(
                                "series:N",
                                scale=alt.Scale(domain=["received_male", "received_female"], range=["#2563eb", "#ec4899"]),
                                title="Series",
                            ),
                            tooltip=["enumerator_name", "district", "series", "records"],
                        )
                        .properties(height=420)
                        )
                    ),
                    width="stretch",
                )
                close_panel()
            with bottom_right:
                open_panel()
                st.subheader("Lowest Performing Teams")
                lowest_teams = team_view.sort_values(["completion_total", "total_received"], ascending=[True, True])[
                    ["enumerator_name", "province", "district", "total_target", "total_received", "completion_total"]
                ].head(12).copy()
                lowest_teams["completion_total"] = lowest_teams["completion_total"].map(format_percent)
                st.dataframe(lowest_teams, width="stretch", hide_index=True, height=420)
                close_panel()

        with team_table_tab:
            left, right = st.columns(2)
            with left:
                open_panel()
                st.subheader("Team Progress Table")
                team_display = team_view[
                    [
                        "province",
                        "district",
                        "enumerator_name",
                        "target_male",
                        "received_male",
                        "remaining_male",
                        "target_female",
                        "received_female",
                        "remaining_female",
                        "completion_total",
                        "team_status",
                    ]
                ].copy()
                team_display["completion_total"] = team_display["completion_total"].map(format_percent)
                st.dataframe(team_display, width="stretch", hide_index=True, height=420)
                close_panel()
            with right:
                open_panel()
                st.subheader("Top Performing Enumerators")
                top_teams = team_view[
                    ["enumerator_name", "province", "district", "total_received", "completion_total", "team_status"]
                ].head(10).copy()
                top_teams["completion_total"] = top_teams["completion_total"].map(format_percent)
                st.dataframe(top_teams, width="stretch", hide_index=True, height=420)
                close_panel()
