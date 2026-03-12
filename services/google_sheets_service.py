import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_worksheet(service_account, spreadsheet_id, sheet_name):

    creds = Credentials.from_service_account_info(
        service_account,
        scopes=SCOPES
    )

    client = gspread.authorize(creds)

    spreadsheet = client.open_by_key(spreadsheet_id)

    return spreadsheet.worksheet(sheet_name)