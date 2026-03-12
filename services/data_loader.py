import pandas as pd

from config.settings import RAW_DATA_SHEET, SPREADSHEET_ID
from services.google_sheets_service import get_worksheet


def load_google_sheet(worksheet):
    values = worksheet.get_all_values()
    if not values:
        return pd.DataFrame()

    headers = values[0]
    rows = values[1:]
    return pd.DataFrame(rows, columns=headers)


def load_sheet(worksheet):
    return load_google_sheet(worksheet)


def load_raw_data_from_secrets(secrets):
    worksheet = get_worksheet(
        secrets["gcp_service_account"],
        secrets["app"].get("spreadsheet_id", SPREADSHEET_ID),
        RAW_DATA_SHEET,
    )
    return load_google_sheet(worksheet)
