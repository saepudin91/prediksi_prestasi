import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import pickle
import gspread
from google.oauth2.service_account import Credentials

# === KONFIGURASI GOOGLE SHEETS ===
secrets = st.secrets["google_sheets"]
creds = Credentials.from_service_account_info(secrets, scopes=[
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
])
client = gspread.authorize(creds)

SPREADSHEET_NAME = "Prediksi prestasi"
sheet = client.open(SPREADSHEET_NAME).sheet1

# Header otomatis sesuai versi 2
HEADER = ["No", "Nama", "Jenis Kelamin", "Usia", "Kelas", 
          "X1", "X2", "X3", "Sumber", "Prediksi Prestasi", "Kategori"]

if sheet.row_values(1) != HEADER:
    sheet.clear()
    sheet.append_row(HEADER)

# === LOAD MODEL ===
with open("model_prestasi.pkl", "rb") as f:
    model = pickle.load(f)

# === JUDUL APLIKASI ===
st.title("Prediksi Pengaruh Bullying Terhadap Prestasi Belajar Siswa")

# === INPUT MANUAL ===
st.header("Input Manual Data Siswa")
nama = st.text_input("Nama")
jenis_kelamin = st.selectbox("Jenis Kelamin", ["Laki-laki", "Perempuan"])
usia = st.number_input("Usia", min_value=6, max_value=25, value=15)
kelas = st.selectbox("Kelas", ["VII", "VIII", "IX", "X", "XI", "XII"])

st.markdown("Isi Skor Kategori (Skala 1-5)")
x1 = st.slider("Pengalaman Bullying (X1)", 1.0, 5.0, 3.0)
x2 = st.slider("Dukungan Sosial (X2)", 1.0, 5.0, 3.0)
x3 = st.slider("Kesehatan Mental (X3)", 1.0, 5.0, 3.0)

def kategori(y):
    if y < 2.5:
        return "Kurang"
    elif y < 3.5:
        return "Cukup"
    elif y < 4.25:
        return "Baik"
    else:
        return "Sangat Baik"

if st.button("Prediksi Prestasi"):
    input_data = pd.DataFrame({"X1": [x1], "X2": [x2], "X3": [x3]})
    prediction = model.predict(input_data)[0]
    kategori_hasil = kategori(prediction)

    st.success(f"Prediksi Prestasi Belajar: {prediction:.2f} ({kategori_hasil})")

    st.write("Data Input:")
    st.write({
        "Nama": nama,
        "Jenis Kelamin": jenis_kelamin,
        "Usia": usia,
        "Kelas": kelas,
        "X1": x1,
        "X2": x2,
        "X3": x3,
        "Prediksi Prestasi": prediction,
        "Kategori": kategori_hasil
    })

    # Simpan ke Google Sheets
    new_row = [
        len(sheet.get_all_values()), nama, jenis_kelamin, usia, kelas,
        x1, x2, x3, "Manual", prediction, kategori_hasil
    ]
    sheet.append_row(new_row)
    st.info("Data berhasil disimpan ke Google Sheets.")

# === Upload File ===
st.header("Upload CSV")
uploaded_file = st.file_uploader("Upload file CSV (format: Nama, Jenis Kelamin, Usia, Kelas, X1, X2, X3)", type=["csv"])

if uploaded_file is not None:
    df_upload = pd.read_csv(uploaded_file)

    required_columns = ["Nama", "Jenis Kelamin", "Usia", "Kelas", "X1", "X2", "X3"]
    if all(col in df_upload.columns for col in required_columns):
        df_upload["Prediksi_Y"] = model.predict(df_upload[["X1", "X2", "X3"]])

        # Fungsi kategori
        def kategori(y):
            if y < 2.5:
                return "Kurang"
            elif y < 3.5:
                return "Cukup"
            elif y < 4.25:
                return "Baik"
            else:
                return "Sangat Baik"

        df_upload["Kategori"] = df_upload["Prediksi_Y"].apply(kategori)

        st.subheader("Hasil Prediksi:")
        st.dataframe(df_upload)

        # Simpan ke Google Sheets
        for idx, row in df_upload.iterrows():
            new_row = [
                len(sheet.get_all_values()),  # No
                row["Nama"],
                row["Jenis Kelamin"],
                row["Usia"],
                row["Kelas"],
                row["X1"],
                row["X2"],
                row["X3"],
                "N/A",  # Jenis Bullying
                row["Prediksi_Y"],
                row["Kategori"],
                ""  # Prestasi Belajar aktual (jika belum ada)
            ]
            sheet.append_row(new_row)
        st.success("Semua data dari CSV berhasil diprediksi dan disimpan ke Google Sheets!")

        # Visualisasi Korelasi
        st.subheader("Visualisasi Korelasi Variabel")
        fig, ax = plt.subplots(figsize=(6, 4))
        sns.heatmap(df_upload[["X1", "X2", "X3", "Prediksi_Y"]].corr(), annot=True, cmap="coolwarm", ax=ax)
        st.pyplot(fig)

        # Plot X vs Prediksi
st.subheader("Plot X vs Prediksi")
for x_col in ["X1", "X2", "X3"]:
    fig, ax = plt.subplots()
    sns.regplot(x=df_upload[x_col], y=df_upload["Prediksi_Y"], ax=ax, line_kws={"color": "red"})
    ax.set_title(f"{x_col} vs Prediksi Prestasi")
    ax.set_xlabel(x_col)
    ax.set_ylabel("Prediksi Prestasi")
    st.pyplot(fig)

    
