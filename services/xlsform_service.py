from __future__ import annotations

from pathlib import Path
import re

import pandas as pd


def load_xlsform(path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    survey_df = pd.read_excel(path, sheet_name="survey").fillna("")
    choices_df = pd.read_excel(path, sheet_name="choices").fillna("")
    return survey_df, choices_df


def resolve_xlsform_path(base_dir: str | None = None) -> str:
    search_root = Path(base_dir or ".")
    candidates = []

    for pattern in ("*.xlsx", "*.xls"):
        candidates.extend(search_root.rglob(pattern))

    for candidate in candidates:
        if ".venv" in candidate.parts:
            continue
        try:
            xl = pd.ExcelFile(candidate)
            if {"survey", "choices"}.issubset(set(xl.sheet_names)):
                return str(candidate)
        except Exception:
            continue

    fallback = Path(r"data/aq5LpJwndg6AiC6Y6p8iLt.xlsx")
    if fallback.exists():
        return str(fallback)

    raise FileNotFoundError("No XLSForm with `survey` and `choices` sheets was found.")


def build_question_catalog(raw_columns: list[str], survey_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column_name in raw_columns:
        question = find_question_for_column(column_name, survey_df)
        if not question:
            continue
        rows.append(
            {
                "column_name": column_name,
                "field_name": str(question.get("name", "")).strip(),
                "type": str(question.get("type", "")).strip(),
                "label_en": str(question.get("label::English (en)", "")).strip(),
                "label_dari": str(question.get("label::Dari (prs)", "")).strip(),
                "label_pashto": str(question.get("label::Pashto (ps)", "")).strip(),
                "relevant": str(question.get("relevant", "")).strip(),
                "required": question.get("required", ""),
                "constraint": str(question.get("constraint", "")).strip(),
            }
        )
    catalog_df = pd.DataFrame(rows)
    if catalog_df.empty:
        return catalog_df
    return catalog_df.drop_duplicates(subset=["column_name", "field_name", "type", "relevant"]).reset_index(drop=True)


def find_question_for_column(column_name: str, survey_df: pd.DataFrame) -> dict:
    column_name = str(column_name).strip()
    survey = survey_df.copy()
    survey["label::English (en)"] = survey["label::English (en)"].astype(str).str.strip()
    survey["name"] = survey["name"].astype(str).str.strip()

    exact_label = survey[survey["label::English (en)"] == column_name]
    if not exact_label.empty:
        return exact_label.iloc[0].to_dict()

    exact_name = survey[survey["name"] == column_name]
    if not exact_name.empty:
        return exact_name.iloc[0].to_dict()

    prefix_match = survey[
        survey["label::English (en)"].astype(str).apply(
            lambda value: bool(value) and column_name.startswith(value + "/")
        )
    ]
    if not prefix_match.empty:
        return prefix_match.iloc[0].to_dict()

    return {}


def get_choices_for_question(question_row: dict, choices_df: pd.DataFrame) -> pd.DataFrame:
    question_type = str(question_row.get("type", "")).strip()
    if not question_type.startswith("select_one") and not question_type.startswith("select_multiple"):
        return pd.DataFrame()

    parts = question_type.split()
    if len(parts) < 2:
        return pd.DataFrame()

    list_name = parts[1].strip()
    subset = choices_df[choices_df["list_name"].astype(str).str.strip() == list_name].copy()
    if subset.empty:
        return pd.DataFrame()

    choice_columns = [
        "name",
        "label::English (en)",
        "label::Dari (prs)",
        "label::Pashto (ps)",
    ]
    available = [column for column in choice_columns if column in subset.columns]
    return subset[available].reset_index(drop=True)


def suggest_translation(value: str, choices_df: pd.DataFrame) -> str:
    value = str(value).strip()
    if not value:
        return ""

    if choices_df.empty:
        return value

    comparable_columns = [
        "name",
        "label::English (en)",
        "label::Dari (prs)",
        "label::Pashto (ps)",
    ]
    for _, row in choices_df.iterrows():
        for column in comparable_columns:
            if column in row and str(row[column]).strip() == value:
                english_label = str(row.get("label::English (en)", "")).strip()
                return english_label or str(row.get("name", "")).strip()

    return value


def is_text_question(question_type: str) -> bool:
    cleaned = str(question_type).strip().lower()
    return cleaned == "text"


def extract_relevant_field_names(relevant_expression: str) -> list[str]:
    expression = str(relevant_expression or "").strip()
    if not expression:
        return []
    return re.findall(r"\$\{([^}]+)\}", expression)


def build_relevant_question_context(question_row: dict, survey_df: pd.DataFrame) -> list[dict]:
    relevant_expression = str(question_row.get("relevant", "")).strip()
    field_names = extract_relevant_field_names(relevant_expression)
    if not field_names:
        return []

    survey = survey_df.copy()
    survey["name"] = survey["name"].astype(str).str.strip()

    context_rows = []
    for field_name in field_names:
        match = survey[survey["name"] == str(field_name).strip()]
        if match.empty:
            context_rows.append(
                {
                    "field_name": field_name,
                    "label_en": "",
                    "label_dari": "",
                    "label_pashto": "",
                }
            )
            continue

        row = match.iloc[0]
        context_rows.append(
            {
                "field_name": str(row.get("name", "")).strip(),
                "label_en": str(row.get("label::English (en)", "")).strip(),
                "label_dari": str(row.get("label::Dari (prs)", "")).strip(),
                "label_pashto": str(row.get("label::Pashto (ps)", "")).strip(),
            }
        )

    return context_rows


def build_xlsform_export_pairs(survey_df: pd.DataFrame, choices_df: pd.DataFrame) -> list[dict]:
    pairs = []
    choice_order_column = "order" if "order" in choices_df.columns else None

    for _, row in survey_df.iterrows():
        field_name = str(row.get("name", "")).strip()
        question_type = str(row.get("type", "")).strip()
        label_en = str(row.get("label::English (en)", "")).strip()

        if not field_name:
            continue

        target_label = label_en or field_name
        pairs.append({"source": field_name, "target": target_label})

        if question_type.startswith("select_multiple"):
            parts = question_type.split()
            if len(parts) < 2:
                continue
            list_name = parts[1].strip()
            subset = choices_df[choices_df["list_name"].astype(str).str.strip() == list_name].copy()
            if choice_order_column:
                subset[choice_order_column] = pd.to_numeric(subset[choice_order_column], errors="coerce")
                subset = subset.sort_values(choice_order_column, na_position="last")
            for _, choice_row in subset.iterrows():
                choice_name = str(choice_row.get("name", "")).strip()
                choice_label = str(choice_row.get("label::English (en)", "")).strip() or choice_name
                if choice_name:
                    pairs.append(
                        {
                            "source": f"{field_name}/{choice_name}",
                            "target": f"{target_label}/{choice_label}",
                        }
                    )

    return pairs


def build_ordered_question_column_map(raw_headers: list[str], survey_df: pd.DataFrame, choices_df: pd.DataFrame) -> list[dict]:
    pairs = build_xlsform_export_pairs(survey_df, choices_df)
    mapped = []
    search_start = 0

    for pair in pairs:
        target = str(pair["target"]).strip()
        match_index = None
        for idx in range(search_start, len(raw_headers)):
            if str(raw_headers[idx]).strip() == target:
                match_index = idx
                break
        if match_index is None:
            for idx, header in enumerate(raw_headers):
                if str(header).strip() == target:
                    match_index = idx
                    break
        if match_index is None:
            continue
        mapped.append(
            {
                "source": str(pair["source"]).strip(),
                "target": target,
                "column_index": match_index,
            }
        )
        search_start = match_index + 1

    return mapped
