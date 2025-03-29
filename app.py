import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# Load secrets
secrets = st.secrets["google_sheets"]

# Buat credential dari secrets
creds = Credentials.from_service_account_info(secrets, scopes=[
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
])

# Autentikasi ke Google Sheets
client = gspread.authorize(creds)

# Coba buka spreadsheet
try:
    spreadsheet = client.open("NAMA_SPREADSHEET")
    st.write(f"Berhasil terhubung ke: {spreadsheet.title}")
except Exception as e:
    st.error(f"Error: {e}")
