import pandas as pd


def format_number(value) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def format_percent(value) -> str:
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return str(value)


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")
