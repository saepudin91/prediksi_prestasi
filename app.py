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

# --- KONVERSI KUALITATIF ---
def konversi_kualitatif(df):
    bullying_map = {"Tidak Pernah": 1, "Jarang": 2, "Kadang-kadang": 3, "Sering": 4, "Sangat Sering": 5}
    sosial_map = {"Sangat Rendah": 1, "Rendah": 2, "Sedang": 3, "Tinggi": 4, "Sangat Tinggi": 5}
    mental_map = {"Sangat Buruk": 1, "Buruk": 2, "Sedang": 3, "Baik": 4, "Sangat Baik": 5}
    df["Tingkat Bullying"] = df["Tingkat Bullying"].map(bullying_map)
    df["Dukungan Sosial"] = df["Dukungan Sosial"].map(sosial_map)
    df["Kesehatan Mental"] = df["Kesehatan Mental"].map(mental_map)
    return df

# --- APLIKASI UTAMA ---
st.title("📊 Aplikasi Prediksi Prestasi Belajar")
mode = st.radio("Pilih mode input:", ("Input Manual", "Upload CSV", "Google Form"))

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
    uploaded_file = st.file_uploader("Upload file CSV", type=["csv"], key="upload_csv")

    if uploaded_file:
        if "df_csv" not in st.session_state:
            try:
                df_temp = pd.read_csv(uploaded_file)
                expected_cols = {"Nama", "Jenis Kelamin", "Umur", "Kelas", "Tingkat Bullying",
                                 "Dukungan Sosial", "Kesehatan Mental", "Jenis Bullying"}

                if not expected_cols.issubset(df_temp.columns):
                    st.error("Format CSV tidak sesuai!")
                else:
                    st.session_state.df_csv = df_temp
                    st.session_state.prediksi_dijalankan = False
                    st.success("File berhasil diunggah! Klik tombol di bawah untuk memproses prediksi.")
            except Exception as e:
                st.error(f"Gagal membaca file CSV: {e}")
                st.stop()

    if "df_csv" in st.session_state:
        st.dataframe(st.session_state.df_csv)

        if st.button("Prediksi CSV"):
            st.session_state.prediksi_dijalankan = True
            st.rerun()

        if st.session_state.get("prediksi_dijalankan", False):
            df_siswa = st.session_state.df_csv.copy()
            df_siswa["Prediksi Prestasi"] = model.predict(
                df_siswa[["Tingkat Bullying", "Dukungan Sosial", "Kesehatan Mental"]]
            )
            df_siswa["Kategori"] = df_siswa["Prediksi Prestasi"].apply(klasifikasikan_prestasi)

            existing_data = sheet.get_all_values()
            existing_len = len(existing_data)
            existing_names = set(row[1] for row in existing_data[1:])

            new_data = []
            for _, row in df_siswa.iterrows():
                if row["Nama"] in existing_names:
                    continue
                row_list = row[[ "Nama", "Jenis Kelamin", "Umur", "Kelas", "Tingkat Bullying",
                                 "Dukungan Sosial", "Kesehatan Mental", "Jenis Bullying",
                                 "Prediksi Prestasi", "Kategori"]].tolist()
                row_list.insert(0, existing_len)
                row_list.append(row.get("Prestasi Belajar", ""))
                sheet.append_row(row_list)
                existing_len += 1
                new_data.append(row)

            if new_data:
                st.success(f"{len(new_data)} baris data berhasil diproses dan disimpan ke Database!")
                st.dataframe(pd.DataFrame(new_data))
            else:
                st.info("Tidak ada data baru yang ditambahkan. Semua siswa sudah ada di database.")

            st.session_state.prediksi_dijalankan = False

        if st.button("Reset Upload CSV"):
            del st.session_state["df_csv"]
            st.session_state.prediksi_dijalankan = False
            st.rerun()

elif mode == "Google Form":
    st.info("🔄 Mengambil data dari hasil Google Form...")
    try:
        sheet_form = client.open("Hasil Google Form").sheet1
        df_form = pd.DataFrame(sheet_form.get_all_records())
        df_form = konversi_kualitatif(df_form)

        if not {"Nama", "Jenis Kelamin", "Umur", "Kelas", "Tingkat Bullying",
                "Dukungan Sosial", "Kesehatan Mental", "Jenis Bullying"}.issubset(df_form.columns):
            st.error("Kolom dalam Google Form belum lengkap atau tidak sesuai.")
        else:
            st.success("Data berhasil diambil dari Google Form!")
            df_form["Prediksi Prestasi"] = model.predict(
                df_form[["Tingkat Bullying", "Dukungan Sosial", "Kesehatan Mental"]]
            )
            df_form["Kategori"] = df_form["Prediksi Prestasi"].apply(klasifikasikan_prestasi)

            existing_data = sheet.get_all_values()
            existing_len = len(existing_data)
            existing_names = set(row[1] for row in existing_data[1:])

            added = 0
            for _, row in df_form.iterrows():
                if row["Nama"] in existing_names:
                    continue
                new_row = [existing_len, row["Nama"], row["Jenis Kelamin"], row["Umur"], row["Kelas"],
                           row["Tingkat Bullying"], row["Dukungan Sosial"], row["Kesehatan Mental"],
                           row["Jenis Bullying"], row["Prediksi Prestasi"], row["Kategori"], ""]
                sheet.append_row(new_row)
                existing_len += 1
                added += 1

            if added:
                st.success(f"Berhasil menambahkan {added} data dari Google Form!")
                st.dataframe(df_form)
            else:
                st.info("Tidak ada data baru dari Google Form.")
    except Exception as e:
        st.error(f"Gagal mengakses Google Form: {e}")
