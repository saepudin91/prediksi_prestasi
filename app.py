# --- IMPORT LIBRARY ---
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
          "Jenis Bullying", "Prediksi Prestasi", "Kategori", "Prestasi Belajar"]

# Pastikan header tersedia di Google Sheets
if sheet.row_values(1) != HEADER:
    sheet.clear()
    sheet.append_row(HEADER)

# --- LOAD MODEL ---
model_path = "model_prestasi.pkl"
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

# --- FUNGSI KATEGORI ---
def klasifikasikan_prestasi(nilai):
    if nilai < 2.5:
        return "Rendah"
    elif nilai < 3.5:
        return "Cukup"
    else:
        return "Tinggi"

# --- APLIKASI UTAMA ---
st.title("📊 Aplikasi Prediksi Prestasi Belajar")
mode = st.radio("Pilih mode input:", ("Input Manual", "Upload CSV"))

if mode == "Input Manual":
    nama = st.text_input("Nama Siswa").strip()
    jenis_kelamin = st.radio("Jenis Kelamin", ["Laki-laki", "Perempuan"], index=None)
    umur = st.number_input("Umur", min_value=5, max_value=20, step=1)
    kelas = st.number_input("Kelas", min_value=1, max_value=12, step=1)
    jenis_bullying = st.selectbox("Jenis Bullying", ["Fisik", "Verbal", "Sosial", "Cyber", "Seksual"])
    bullying = st.slider("Tingkat Bullying (1–5)", 1, 5, 3)
    sosial = st.slider("Dukungan Sosial (1–5)", 1, 5, 3)
    mental = st.slider("Kesehatan Mental (1–5)", 1, 5, 3)

    if st.button("Prediksi!"):
        if not nama or jenis_kelamin is None:
            st.error("Harap lengkapi semua field!")
        else:
            input_data = [[bullying, sosial, mental]]
            hasil_prediksi = model.predict(input_data)[0]
            kategori = klasifikasikan_prestasi(hasil_prediksi)
            st.success(f"Hasil prediksi prestasi belajar {nama}: {hasil_prediksi:.2f} ({kategori})")
            new_row = [len(sheet.get_all_values()), nama, jenis_kelamin, umur, kelas,
                       bullying, sosial, mental, jenis_bullying, hasil_prediksi, kategori, ""]
            sheet.append_row(new_row)
            st.info("Data telah disimpan ke Database!")

elif mode == "Upload CSV":
    uploaded_file = st.file_uploader("Upload file CSV", type=["csv"])
    if uploaded_file:
        df_siswa = pd.read_csv(uploaded_file)
        expected_cols = {"Nama", "Jenis Kelamin", "Umur", "Kelas", "Tingkat Bullying",
                         "Dukungan Sosial", "Kesehatan Mental", "Jenis Bullying"}
        if not expected_cols.issubset(df_siswa.columns):
            st.error("Format CSV tidak sesuai!")
        else:
            df_siswa["Prediksi Prestasi"] = model.predict(df_siswa[["Tingkat Bullying", "Dukungan Sosial", "Kesehatan Mental"]])
            df_siswa["Kategori"] = df_siswa["Prediksi Prestasi"].apply(klasifikasikan_prestasi)
            for _, row in df_siswa.iterrows():
                row_list = row[["Nama", "Jenis Kelamin", "Umur", "Kelas", "Tingkat Bullying",
                                "Dukungan Sosial", "Kesehatan Mental", "Jenis Bullying", "Prediksi Prestasi", "Kategori"]].tolist()
                row_list.insert(0, len(sheet.get_all_values()))
                row_list.append(row.get("Prestasi Belajar", ""))
                sheet.append_row(row_list)
            st.success("Data berhasil diproses dan disimpan ke Database!")
            st.dataframe(df_siswa)

# --- TAMPILKAN & HAPUS RIWAYAT ---
st.subheader("Riwayat Prediksi")
data = sheet.get_all_values()
df_riwayat = pd.DataFrame(data[1:], columns=HEADER) if len(data) > 1 else pd.DataFrame(columns=HEADER)

if not df_riwayat.empty:
    df_riwayat["Prediksi Prestasi"] = pd.to_numeric(df_riwayat["Prediksi Prestasi"], errors="coerce")
    df_riwayat["Kategori"] = df_riwayat["Prediksi Prestasi"].apply(klasifikasikan_prestasi)

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

    # Tambah Fitur: Isi Prestasi Belajar
    st.subheader("Isi Nilai Aktual Prestasi Belajar")
    data_kosong = df_riwayat[df_riwayat["Prestasi Belajar"] == ""]
    if not data_kosong.empty:
        pilihan = st.selectbox("Pilih Nama yang akan diisi Prestasi Belajar", data_kosong["Nama"].unique())
        nilai = st.slider("Nilai Prestasi Belajar (1–5)", 1, 5, 3)
        if st.button("Simpan Nilai Aktual"):
            for i, row in enumerate(sheet.get_all_values()[1:], start=2):
                if row[1] == pilihan and row[11] == "":
                    sheet.update_cell(i, 12, nilai)
                    st.success("Nilai aktual berhasil disimpan!")
                    st.rerun()

# --- ANALISIS BULLYING ---
st.subheader("📊 Analisis Jenis Bullying")
if not df_riwayat.empty:
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

    st.write(f"📌 Jenis bullying yang paling banyak terjadi: {bullying_counts.idxmax()} ({bullying_counts.max()} kasus)")
    st.write(f"📌 Jenis bullying yang paling sedikit terjadi: {bullying_counts.idxmin()} ({bullying_counts.min()} kasus)")
else:
    st.write("⚠ Tidak ada data bullying untuk dianalisis.")

# --- PIE CHART KATEGORI PRESTASI ---
st.subheader("📈 Distribusi Kategori Prediksi Prestasi Belajar")
if not df_riwayat.empty:
    kategori_counts = df_riwayat["Kategori"].value_counts()

    fig2, ax2 = plt.subplots()
    ax2.pie(kategori_counts, labels=kategori_counts.index, autopct='%1.1f%%', startangle=140,
            colors=["#FF9999", "#FFCC99", "#99CC99"])
    ax2.axis('equal')
    st.pyplot(fig2)

    img_pie = BytesIO()
    fig2.savefig(img_pie, format="png", bbox_inches="tight")
    img_pie.seek(0)
    st.download_button("📥 Download Pie Chart", data=img_pie, file_name="pie_kategori_prestasi.png", mime="image/png")
else:
    st.info("Belum ada data kategori prestasi untuk ditampilkan.")

# --- DOWNLOAD RIWAYAT ---
if not df_riwayat.empty:
    csv = df_riwayat.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Riwayat Prediksi", data=csv, file_name="riwayat_prediksi.csv", mime="text/csv")
