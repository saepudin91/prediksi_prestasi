import pandas as pd
import pickle
import streamlit as st
import matplotlib.pyplot as plt
from io import BytesIO
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURASI GOOGLE SHEETS ---
secrets = st.secrets["google_sheets"]
creds = Credentials.from_service_account_info(secrets, scopes=[
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
])
client = gspread.authorize(creds)

SPREADSHEET_NAME = "Prediksi prestasi"
sheet = client.open(SPREADSHEET_NAME).sheet1
HEADER = ["No", "Nama", "Jenis Kelamin", "Umur", "Kelas", 
          "Tingkat Bullying", "Dukungan Sosial", "Kesehatan Mental", 
          "Jenis Bullying", "Prediksi Prestasi", "Prestasi Belajar"]

# Pastikan header tersedia di Google Sheets
if sheet.row_values(1) != HEADER:
    sheet.clear()
    sheet.append_row(HEADER)

# Load model regresi
model_path = "model_regresi.pkl"
with open(model_path, "rb") as f:
    model = pickle.load(f)

# --- FITUR LOGIN ---
USER_CREDENTIALS = {"user3": "password123", "admin": "adminpass"}

def login():
    st.title("🔒 Login ke Aplikasi")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.success(f"✅ Login berhasil! Selamat datang, {username}.")
            st.rerun()
        else:
            st.error("❌ Username atau password salah!")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login()
    st.stop()

# --- APLIKASI UTAMA ---
st.title("📊 Aplikasi Prediksi Prestasi Belajar")
mode = st.radio("Pilih mode input:", ("Input Manual", "Upload CSV"))

# --- INPUT MANUAL ---
if mode == "Input Manual":
    nama = st.text_input("Nama Siswa").strip()
    jenis_kelamin = st.radio("Jenis Kelamin", ["Laki-laki", "Perempuan"], index=None)
    umur = st.number_input("Umur", min_value=5, max_value=20, step=1)
    kelas = st.number_input("Kelas", min_value=1, max_value=12, step=1)
    jenis_bullying = st.selectbox("Jenis Bullying", ["Fisik", "Verbal", "Sosial", "Cyber", "Seksual"])
    bullying = st.slider("Tingkat Bullying (1–5)", 1, 5, 3)
    sosial = st.slider("Dukungan Sosial (1–5)", 1, 5, 3)
    mental = st.slider("Kesehatan Mental (1–5)", 1, 5, 3)
    prestasi_manual = st.slider("Prestasi Belajar (1–5)", 1, 5, 3)

    if st.button("Prediksi!"):
        if not nama or jenis_kelamin is None:
            st.error("Harap lengkapi semua field!")
        else:
            input_data = [[bullying, sosial, mental]]
            hasil_prediksi = model.predict(input_data)[0]
            st.success(f"Hasil prediksi prestasi belajar {nama}: {hasil_prediksi:.2f}")
            new_row = [len(sheet.get_all_values()), nama, jenis_kelamin, umur, kelas, bullying, sosial, mental, jenis_bullying, hasil_prediksi, prestasi_manual]
            sheet.append_row(new_row)
            st.info("Data telah disimpan ke Database!")

# --- UPLOAD CSV ---
elif mode == "Upload CSV":
    uploaded_file = st.file_uploader("Upload file CSV", type=["csv"])
    if uploaded_file:
        df_siswa = pd.read_csv(uploaded_file)
        expected_cols = {"Nama", "Jenis Kelamin", "Umur", "Kelas", "Tingkat Bullying", 
                         "Dukungan Sosial", "Kesehatan Mental", "Jenis Bullying", "Prestasi Belajar"}
        if not expected_cols.issubset(df_siswa.columns):
            st.error("Format CSV tidak sesuai!")
        else:
            df_siswa["Prediksi Prestasi"] = model.predict(df_siswa[["Tingkat Bullying", "Dukungan Sosial", "Kesehatan Mental"]])
            for _, row in df_siswa.iterrows():
                row_list = row[["Nama", "Jenis Kelamin", "Umur", "Kelas", "Tingkat Bullying",
                                "Dukungan Sosial", "Kesehatan Mental", "Jenis Bullying"]].tolist()
                row_list.append(row["Prediksi Prestasi"])
                row_list.append(row["Prestasi Belajar"])  # Menyertakan "Prestasi Belajar" di Sheet
                row_list.insert(0, len(sheet.get_all_values()))
                sheet.append_row(row_list)
            st.success("Data berhasil diproses dan disimpan ke Database!")
            st.dataframe(df_siswa)

# --- TAMPILKAN & HAPUS RIWAYAT ---
st.subheader("Riwayat Prediksi")

data = sheet.get_all_values()
df_riwayat = pd.DataFrame(data[1:], columns=HEADER) if len(data) > 1 else pd.DataFrame(columns=HEADER)

if not df_riwayat.empty:
    st.dataframe(df_riwayat)

    if st.button("Hapus Semua Riwayat"):
        sheet.clear()
        sheet.append_row(HEADER)
        st.warning("Seluruh riwayat prediksi telah dihapus!")
        st.rerun()

    nama_hapus = st.selectbox("Pilih Nama yang Akan Dihapus", df_riwayat["Nama"].unique())
    if st.button("Hapus Data Ini"):
        df_riwayat = df_riwayat[df_riwayat["Nama"] != nama_hapus]
        sheet.clear()
        sheet.append_row(HEADER)
        for _, row in df_riwayat.iterrows():
            sheet.append_row(row.tolist())
        st.warning(f"Data untuk {nama_hapus} telah dihapus!")
        st.rerun()
else:
    st.write("Belum ada riwayat prediksi.")

# --- ANALISIS BULLYING ---
st.subheader("📊 Analisis Jenis Bullying")
data = sheet.get_all_values()
df_riwayat = pd.DataFrame(data[1:], columns=HEADER) if len(data) > 1 else pd.DataFrame(columns=HEADER)

if not df_riwayat.empty and "Jenis Bullying" in df_riwayat.columns:
    bullying_counts = df_riwayat["Jenis Bullying"].value_counts()

    fig, ax = plt.subplots(figsize=(8, 6))
    bullying_counts.plot(kind="bar", ax=ax, color=['blue', 'red', 'green', 'purple', 'orange'])
    ax.set_title("Jumlah Kasus Berdasarkan Jenis Bullying")
    ax.set_xlabel("Jenis Bullying")
    ax.set_ylabel("Jumlah Kasus")
    st.pyplot(fig)

    img_buffer = BytesIO()
    fig.savefig(img_buffer, format="png", bbox_inches="tight")
    img_buffer.seek(0)
    st.download_button("📥 Download Grafik", data=img_buffer, file_name="grafik_bullying.png", mime="image/png")

    if not bullying_counts.empty:
        st.write(f"📌 Jenis bullying yang paling banyak terjadi: {bullying_counts.idxmax()} ({bullying_counts.max()} kasus)")
        st.write(f"📌 Jenis bullying yang paling sedikit terjadi: {bullying_counts.idxmin()} ({bullying_counts.min()} kasus)")
else:
    st.write("⚠ Tidak ada data bullying untuk dianalisis.")

# --- DOWNLOAD RIWAYAT ---
if not df_riwayat.empty:
    csv = df_riwayat.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Riwayat Prediksi", data=csv, file_name="riwayat_prediksi.csv", mime="text/csv")
