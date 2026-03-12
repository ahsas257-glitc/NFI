from __future__ import annotations

import pandas as pd


def build_count_distribution(df: pd.DataFrame, column_name: str, label: str) -> pd.DataFrame:
    if column_name not in df.columns:
        return pd.DataFrame(columns=[label, "records"])
    return (
        df[column_name]
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .rename_axis(label)
        .reset_index(name="records")
    )
