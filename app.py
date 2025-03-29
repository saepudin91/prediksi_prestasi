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
    spreadsheet = client.open("Prediksi prestasi")
    st.write(f"✅ Berhasil terhubung ke: {spreadsheet.title}")

    # Coba ambil worksheet pertama
    worksheet = spreadsheet.get_worksheet(0)
    data = worksheet.get_all_values()
    
    # Tampilkan beberapa baris pertama sebagai debug
    st.write("🔹 Data dari Google Sheets:")
    st.write(data[:5])  # Hanya tampilkan 5 baris pertama

except Exception as e:
    st.error(f"❌ Error: {e}")
