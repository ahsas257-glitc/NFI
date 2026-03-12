import pandas as pd

from core.data_engine import build_quality_summary


def check_missing_values(df: pd.DataFrame) -> pd.Series:
    return df.isna().sum().sort_values(ascending=False)


def check_duplicates(df: pd.DataFrame) -> int:
    return int(df.duplicated().sum())


def basic_summary(df: pd.DataFrame) -> dict:
    quality = build_quality_summary(df)
    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "missing_values": int(df.isna().sum().sum()),
        "duplicates": int(df.duplicated().sum()),
        "duplicate_uuid": quality["duplicate_uuid"],
        "duplicate_id": quality["duplicate_id"],
    }
