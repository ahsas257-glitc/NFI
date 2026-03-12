from __future__ import annotations

import re

import pandas as pd

from services.xlsform_service import build_question_catalog, get_choices_for_question


def _blank_mask(series: pd.Series) -> pd.Series:
    return series.astype(str).fillna("").str.strip().isin(["", "nan", "None"])


def _get_first_series(df: pd.DataFrame, column_name: str) -> pd.Series:
    selected = df.loc[:, column_name]
    if isinstance(selected, pd.DataFrame):
        return selected.iloc[:, 0]
    return selected


def _get_label_for_field(field_name: str, survey_df: pd.DataFrame) -> str:
    survey = survey_df.copy()
    survey["name"] = survey["name"].astype(str).str.strip()
    match = survey[survey["name"] == str(field_name).strip()]
    if match.empty:
        return str(field_name).strip()
    row = match.iloc[0]
    return str(row.get("label::English (en)", "")).strip() or str(field_name).strip()


def _evaluate_simple_relevant(df: pd.DataFrame, relevant_expression: str, survey_df: pd.DataFrame) -> pd.Series:
    expression = str(relevant_expression or "").strip()
    if not expression:
        return pd.Series(True, index=df.index)

    connectors = re.findall(r"\s(and|or)\s", expression)
    parts = re.split(r"\s(?:and|or)\s", expression)
    masks = []
    for part in parts:
        part = part.strip()
        equality_match = re.match(r"\$\{([^}]+)\}\s*(=|!=)\s*'([^']*)'", part)
        selected_match = re.match(r"selected\(\$\{([^}]+)\},\s*'([^']*)'\)", part)
        not_selected_match = re.match(r"not\(selected\(\$\{([^}]+)\},\s*'([^']*)'\)\)", part)

        if equality_match:
            field_name, operator, expected_value = equality_match.groups()
            label = _get_label_for_field(field_name, survey_df)
            if label not in df.columns:
                masks.append(pd.Series(False, index=df.index))
                continue
            current = _get_first_series(df, label).astype(str).fillna("").str.strip()
            if operator == "=":
                masks.append(current == expected_value)
            else:
                masks.append(current != expected_value)
            continue

        if selected_match:
            field_name, expected_value = selected_match.groups()
            label = _get_label_for_field(field_name, survey_df)
            if label not in df.columns:
                masks.append(pd.Series(False, index=df.index))
                continue
            current = _get_first_series(df, label).astype(str).fillna("").str.strip()
            masks.append(current.str.contains(rf"(?:^|[\s,]){re.escape(expected_value)}(?:$|[\s,])", regex=True))
            continue

        if not_selected_match:
            field_name, expected_value = not_selected_match.groups()
            label = _get_label_for_field(field_name, survey_df)
            if label not in df.columns:
                masks.append(pd.Series(True, index=df.index))
                continue
            current = _get_first_series(df, label).astype(str).fillna("").str.strip()
            masks.append(~current.str.contains(rf"(?:^|[\s,]){re.escape(expected_value)}(?:$|[\s,])", regex=True))
            continue

        masks.append(pd.Series(True, index=df.index))

    result = masks[0]
    for connector, mask in zip(connectors, masks[1:]):
        if connector == "and":
            result = result & mask
        else:
            result = result | mask
    return result


def build_form_quality_report(df: pd.DataFrame, survey_df: pd.DataFrame, choices_df: pd.DataFrame) -> dict:
    catalog_df = build_question_catalog(df.columns.tolist(), survey_df)

    schema_summary = {
        "raw_columns": int(len(df.columns)),
        "mapped_questions": int(len(catalog_df)),
        "unmapped_raw_columns": sorted(set(df.columns) - set(catalog_df["column_name"].tolist())),
    }

    required_rows = []
    row_issue_records = []
    for _, question in catalog_df.iterrows():
        question_type = str(question["type"]).strip()
        column_name = str(question["column_name"]).strip()
        relevant = str(question.get("relevant", "")).strip()
        applicable_mask = _evaluate_simple_relevant(df, relevant, survey_df)
        applicable_count = int(applicable_mask.sum())

        if str(question_type).startswith("select_one"):
            choices = get_choices_for_question(question.to_dict(), choices_df)
            allowed_values = set()
            for _, choice in choices.iterrows():
                for column in ["name", "label::English (en)", "label::Dari (prs)", "label::Pashto (ps)"]:
                    if column in choice:
                        value = str(choice[column]).strip()
                        if value:
                            allowed_values.add(value)
            if column_name in df.columns and allowed_values:
                series = _get_first_series(df, column_name).astype(str).fillna("").str.strip()
                invalid_mask = (~series.isin(allowed_values)) & (~_blank_mask(series))
                invalid_count = int(invalid_mask.sum())
                if invalid_count:
                    sample = (
                        df.loc[invalid_mask, ["_uuid", column_name]]
                        .rename(columns={column_name: "value"})
                        .head(25)
                        .assign(issue=f"Invalid choice in {column_name}")
                    )
                    row_issue_records.append(sample)
        required_value = question.get("required", "")
        is_required = (
            required_value is True
            or str(required_value).strip().lower() == "true"
        )
        if is_required and column_name in df.columns:
            series = _get_first_series(df, column_name)
            blank_required = applicable_mask & _blank_mask(series)
            missing_count = int(blank_required.sum())
            required_rows.append(
                {
                    "question": column_name,
                    "field_name": question["field_name"],
                    "type": question_type,
                    "applicable_rows": applicable_count,
                    "missing_required": missing_count,
                    "relevant": relevant,
                }
            )
            if missing_count:
                sample = (
                    df.loc[blank_required, ["_uuid"]]
                    .head(25)
                    .assign(value="")
                    .assign(issue=f"Missing required value in {column_name}")
                )
                row_issue_records.append(sample)

    required_df = pd.DataFrame(required_rows).sort_values("missing_required", ascending=False) if required_rows else pd.DataFrame()

    row_issues_df = (
        pd.concat(row_issue_records, ignore_index=True).drop_duplicates()
        if row_issue_records
        else pd.DataFrame(columns=["_uuid", "value", "issue"])
    )

    return {
        "schema_summary": schema_summary,
        "catalog_df": catalog_df,
        "required_df": required_df,
        "row_issues_df": row_issues_df,
    }
