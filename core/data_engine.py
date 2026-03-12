from __future__ import annotations

import pandas as pd

from config.interviewers import APPROVED_INTERVIEWERS, ENUMERATOR_TARGETS, INTERVIEWER_NAME_MAP
from config.targets import (
    DISTRICT_ALIASES,
    DISTRICT_TARGETS,
    PROVINCE_ALIASES,
    PROVINCE_TARGETS,
)


PROVINCE_COLUMN = "A.1.2.Province"
DISTRICT_COLUMN = "A.1.3.District"
GENDER_COLUMN = "B.1.3.Respondent gender"
INTERVIEWER_COLUMN = "A.1.Interviewer name"
PDME_DATE_COLUMN = "A.3.3 Date of PDME"
SUBMISSION_DATE_COLUMN = "_submission_time"
UUID_COLUMN = "_uuid"
ID_COLUMN = "_id"

TARGET_PROVINCES = tuple(PROVINCE_TARGETS.keys())


def _clean_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).replace("\n", " ").replace('"', "").strip()


def _geo_key(value: str) -> str:
    cleaned = _clean_text(value).lower().replace("_", " ").replace("-", " ")
    return " ".join(cleaned.split())


def _normalize_name_key(value: str) -> str:
    cleaned = _clean_text(value)
    translations = str.maketrans(
        {
            "ي": "ی",
            "ى": "ی",
            "ك": "ک",
            "ة": "ه",
            "ۀ": "ه",
            "ؤ": "و",
            "إ": "ا",
            "أ": "ا",
            "آ": "ا",
            ".": "",
            "،": "",
            "؛": "",
        }
    )
    return " ".join(cleaned.translate(translations).split())


def _normalize_gender(value: str) -> str:
    cleaned = _clean_text(value).lower()
    if cleaned == "male":
        return "Male"
    if cleaned == "female":
        return "Female"
    return cleaned.title() if cleaned else "Unknown"


def _normalize_province(value: str) -> str:
    cleaned = _clean_text(value)
    province_aliases = {
        _geo_key(key): canonical
        for key, canonical in PROVINCE_ALIASES.items()
    }
    for canonical in PROVINCE_TARGETS.keys():
        province_aliases[_geo_key(canonical)] = canonical
    return province_aliases.get(_geo_key(cleaned), cleaned.title() if cleaned else "")


def _normalize_district(value: str) -> str:
    cleaned = _clean_text(value)
    district_aliases = {
        _geo_key(key): canonical
        for key, canonical in DISTRICT_ALIASES.items()
    }
    for item in DISTRICT_TARGETS:
        district_aliases[_geo_key(item["district"])] = item["district"]
    return district_aliases.get(_geo_key(cleaned), cleaned.title() if cleaned else "")


NORMALIZED_NAME_MAP = {_normalize_name_key(key): value for key, value in INTERVIEWER_NAME_MAP.items()}
NORMALIZED_APPROVED_INTERVIEWERS = {
    _normalize_name_key(name): name for name in APPROVED_INTERVIEWERS
}


def _normalize_interviewer(value: str) -> str:
    normalized_key = _normalize_name_key(value)
    if normalized_key in NORMALIZED_NAME_MAP:
        return NORMALIZED_NAME_MAP[normalized_key]
    if normalized_key in NORMALIZED_APPROVED_INTERVIEWERS:
        return NORMALIZED_APPROVED_INTERVIEWERS[normalized_key]
    return _clean_text(value)


def clean_raw_data(df: pd.DataFrame) -> pd.DataFrame:
    clean_df = df.copy()
    clean_df.columns = [_clean_text(column) for column in clean_df.columns]

    object_columns = clean_df.select_dtypes(include="object").columns
    for column in object_columns:
        clean_df[column] = clean_df[column].map(_clean_text)

    province_series = (
        clean_df[PROVINCE_COLUMN].map(_normalize_province)
        if PROVINCE_COLUMN in clean_df.columns
        else pd.Series("", index=clean_df.index)
    )
    district_series = (
        clean_df[DISTRICT_COLUMN].map(_normalize_district)
        if DISTRICT_COLUMN in clean_df.columns
        else pd.Series("", index=clean_df.index)
    )
    gender_series = (
        clean_df[GENDER_COLUMN].map(_normalize_gender)
        if GENDER_COLUMN in clean_df.columns
        else pd.Series("Unknown", index=clean_df.index)
    )
    interviewer_series = (
        clean_df[INTERVIEWER_COLUMN].map(_normalize_interviewer)
        if INTERVIEWER_COLUMN in clean_df.columns
        else pd.Series("", index=clean_df.index)
    )

    clean_df = clean_df.assign(
        province=province_series,
        district=district_series,
        gender=gender_series,
        interviewer_name=interviewer_series,
    )
    clean_df = clean_df.assign(
        province_district=clean_df["province"].fillna("") + " | " + clean_df["district"].fillna(""),
        is_target_province=clean_df["province"].isin(TARGET_PROVINCES),
        is_approved_interviewer=clean_df["interviewer_name"].isin(APPROVED_INTERVIEWERS),
    )

    for column in (PDME_DATE_COLUMN, SUBMISSION_DATE_COLUMN):
        if column in clean_df.columns:
            clean_df[column] = pd.to_datetime(clean_df[column], errors="coerce")

    for column in (ID_COLUMN,):
        if column in clean_df.columns:
            clean_df[column] = pd.to_numeric(clean_df[column], errors="coerce")

    return clean_df


def build_province_progress(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for province, target in PROVINCE_TARGETS.items():
        province_df = df[df["province"] == province]
        actual_total = len(province_df)
        actual_male = int((province_df["gender"] == "Male").sum())
        actual_female = int((province_df["gender"] == "Female").sum())
        total_target = target["total"]
        rows.append(
            {
                "province": province,
                "target_total": total_target,
                "actual_total": actual_total,
                "remaining_total": total_target - actual_total,
                "progress_total": round((actual_total / total_target) * 100, 1)
                if total_target
                else 0.0,
                "target_male": target["male"],
                "actual_male": actual_male,
                "remaining_male": target["male"] - actual_male,
                "progress_male": round((actual_male / target["male"]) * 100, 1)
                if target["male"]
                else 0.0,
                "target_female": target["female"],
                "actual_female": actual_female,
                "remaining_female": target["female"] - actual_female,
                "progress_female": round((actual_female / target["female"]) * 100, 1)
                if target["female"]
                else 0.0,
            }
        )

    return pd.DataFrame(rows)


def build_district_progress(df: pd.DataFrame) -> pd.DataFrame:
    district_rows = []
    for target in DISTRICT_TARGETS:
        district_df = df[
            (df["province"] == target["province"]) & (df["district"] == target["district"])
        ]
        actual_male = int((district_df["gender"] == "Male").sum())
        actual_female = int((district_df["gender"] == "Female").sum())
        total_target = target["male"] + target["female"]
        actual_total = actual_male + actual_female
        district_rows.append(
            {
                "province": target["province"],
                "district": target["district"],
                "target_total": total_target,
                "actual_total": actual_total,
                "remaining_total": total_target - actual_total,
                "progress_total": round((actual_total / total_target) * 100, 1)
                if total_target
                else 0.0,
                "target_male": target["male"],
                "actual_male": actual_male,
                "remaining_male": target["male"] - actual_male,
                "target_female": target["female"],
                "actual_female": actual_female,
                "remaining_female": target["female"] - actual_female,
            }
        )

    return pd.DataFrame(district_rows)


def build_gender_summary(df: pd.DataFrame) -> pd.DataFrame:
    actual = df[df["is_target_province"]]["gender"].value_counts()
    target_male = sum(item["male"] for item in PROVINCE_TARGETS.values())
    target_female = sum(item["female"] for item in PROVINCE_TARGETS.values())

    return pd.DataFrame(
        [
            {
                "gender": "Male",
                "target": target_male,
                "actual": int(actual.get("Male", 0)),
                "remaining": int(target_male - actual.get("Male", 0)),
            },
            {
                "gender": "Female",
                "target": target_female,
                "actual": int(actual.get("Female", 0)),
                "remaining": int(target_female - actual.get("Female", 0)),
            },
        ]
    )


def build_overview_metrics(df: pd.DataFrame) -> dict:
    target_df = df[df["is_target_province"]]
    return {
        "total_records": int(len(df)),
        "target_scope_records": int(len(target_df)),
        "target_total": int(sum(item["total"] for item in PROVINCE_TARGETS.values())),
        "target_male": int(sum(item["male"] for item in PROVINCE_TARGETS.values())),
        "target_female": int(sum(item["female"] for item in PROVINCE_TARGETS.values())),
        "actual_male": int((target_df["gender"] == "Male").sum()),
        "actual_female": int((target_df["gender"] == "Female").sum()),
        "extra_scope_records": int((~df["is_target_province"]).sum()),
        "unique_provinces": int(df["province"].nunique()),
        "unique_districts": int(df["district"].nunique()),
    }


def build_quality_summary(df: pd.DataFrame) -> dict:
    required_columns = [PROVINCE_COLUMN, DISTRICT_COLUMN, GENDER_COLUMN]
    missing_required_columns = [col for col in required_columns if col not in df.columns]

    duplicate_uuid = 0
    if UUID_COLUMN in df.columns:
        uuid_series = df[UUID_COLUMN].replace("", pd.NA).dropna()
        duplicate_uuid = int(uuid_series.duplicated().sum())

    duplicate_id = 0
    if ID_COLUMN in df.columns:
        id_series = df[ID_COLUMN].dropna()
        duplicate_id = int(id_series.duplicated().sum())

    unexpected_provinces = sorted(
        province for province in df["province"].dropna().unique() if province not in TARGET_PROVINCES
    )
    unexpected_interviewers = sorted(
        interviewer
        for interviewer in df["interviewer_name"].dropna().unique()
        if interviewer and interviewer not in APPROVED_INTERVIEWERS
    )

    return {
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "missing_required_columns": missing_required_columns,
        "duplicate_uuid": duplicate_uuid,
        "duplicate_id": duplicate_id,
        "blank_province_rows": int((df["province"] == "").sum()),
        "blank_district_rows": int((df["district"] == "").sum()),
        "blank_gender_rows": int((df["gender"].isin(["", "Unknown"])).sum()),
        "unexpected_provinces": unexpected_provinces,
        "unexpected_interviewers": unexpected_interviewers,
    }


def filter_dataframe(
    df: pd.DataFrame,
    provinces: list[str] | None = None,
    districts: list[str] | None = None,
    genders: list[str] | None = None,
) -> pd.DataFrame:
    filtered = df.copy()
    if provinces:
        filtered = filtered[filtered["province"].isin(provinces)]
    if districts:
        filtered = filtered[filtered["district"].isin(districts)]
    if genders:
        filtered = filtered[filtered["gender"].isin(genders)]
    return filtered


class DataEngine:
    def __init__(self, df: pd.DataFrame):
        self.raw_df = df
        self.df = clean_raw_data(df)

    def get_clean_data(self) -> pd.DataFrame:
        return self.df.copy()

    def get_target_data(self) -> pd.DataFrame:
        return self.df[self.df["is_target_province"]].copy()

    def get_overview_metrics(self) -> dict:
        return build_overview_metrics(self.df)

    def get_province_progress(self) -> pd.DataFrame:
        return build_province_progress(self.df)

    def get_district_progress(self) -> pd.DataFrame:
        return build_district_progress(self.df)

    def get_gender_summary(self) -> pd.DataFrame:
        return build_gender_summary(self.df)

    def get_quality_summary(self) -> dict:
        return build_quality_summary(self.df)

    def get_enumerator_progress(self) -> pd.DataFrame:
        rows = []
        for item in ENUMERATOR_TARGETS:
            scope = self.df[
                (self.df["province"] == item["province"])
                & (self.df["interviewer_name"] == item["enumerator_name"])
            ]
            if item["district"]:
                scope = scope[scope["district"] == item["district"]]

            received_male = int((scope["gender"] == "Male").sum())
            received_female = int((scope["gender"] == "Female").sum())
            rows.append(
                {
                    "province": item["province"],
                    "district": item["district"],
                    "target_male": item["target_male"],
                    "received_male": received_male,
                    "remaining_male": item["target_male"] - received_male,
                    "target_female": item["target_female"],
                    "received_female": received_female,
                    "remaining_female": item["target_female"] - received_female,
                    "enumerator_name": item["enumerator_name"],
                    "total_target": item["target_male"] + item["target_female"],
                    "total_received": received_male + received_female,
                }
            )
        return pd.DataFrame(rows)
