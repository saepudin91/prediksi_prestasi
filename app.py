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

if sheet.row_values(1) != HEADER:
    sheet.clear()
    sheet.append_row(HEADER)

# --- LOAD MODEL ---
model_path = "model_prestasi.pkl"
with open(model_path, "rb") as f:
    model = pickle.load(f)

# --- FITUR LOGIN ---
USER_CREDENTIALS = {"user3": "user123", "admin": "adminpass"}

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

# --- FUNGSI UNTUK KONVERSI KELAS ---
def konversi_kelas(kelas):
    kelas_map = {"V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12}
    kelas_str = str(kelas).replace("||", "II").replace(" ", "").upper()
    for key in kelas_map:
        if key in kelas_str:
            return kelas_map[key]
    return 0

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
    uploaded_file = st.file_uploader("Upload file CSV (Hasil Google Form)", type=["csv"], key="upload_csv")

    if uploaded_file:
        try:
            df_form = pd.read_csv(uploaded_file)
            kolom_harus_ada = ["Nama", "Jenis Kelamin", "Usia", "Kelas", 
                "1. Saya pernah dibully di sekolah.",
                "6. Keluarga saya selalu ada saat saya punya masalah.",
                "11. Saya sering merasa cemas atau khawatir.",
                "21. Pilih jenis bullying yang pernah anda alami."]
            if not all(kol in df_form.columns for kol in kolom_harus_ada):
                st.error("Format file tidak sesuai dengan hasil Google Form yang diharapkan.")
                st.stop()

            df_form = df_form.rename(columns={"Usia": "Umur"})
            bullying_cols = df_form.columns[4:9]
            sosial_cols = df_form.columns[9:14]
            mental_cols = df_form.columns[14:19]

            df_form["Tingkat Bullying"] = df_form[bullying_cols].mean(axis=1)
            df_form["Dukungan Sosial"] = df_form[sosial_cols].mean(axis=1)
            df_form["Kesehatan Mental"] = df_form[mental_cols].mean(axis=1)

            df_form["Kelas"] = df_form["Kelas"].apply(konversi_kelas)
            df_form["Prediksi Prestasi"] = model.predict(df_form[["Tingkat Bullying", "Dukungan Sosial", "Kesehatan Mental"]])
            df_form["Kategori"] = df_form["Prediksi Prestasi"].apply(klasifikasikan_prestasi)

            existing_data = sheet.get_all_values()
            existing_names = set(row[1] for row in existing_data[1:])
            new_data = []
            no = len(existing_data)

            for _, row in df_form.iterrows():
                if row["Nama"] in existing_names:
                    continue
                new_row = [no, row["Nama"], row["Jenis Kelamin"], row["Umur"], row["Kelas"],
                           row["Tingkat Bullying"], row["Dukungan Sosial"], row["Kesehatan Mental"],
                           row["21. Pilih jenis bullying yang pernah anda alami."],
                           row["Prediksi Prestasi"], row["Kategori"], ""]
                sheet.append_row(new_row)
                new_data.append(row)
                no += 1

            st.success(f"{len(new_data)} baris berhasil diproses dan disimpan!")
            st.dataframe(pd.DataFrame(new_data))

        except Exception as e:
            st.error(f"Terjadi kesalahan saat memproses file: {e}")

# --- Sisanya tetap sama seperti sebelumnya ---
# --- Tampilkan riwayat, input nilai aktual, analisis, dan grafik ---
