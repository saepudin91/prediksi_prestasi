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

HEADER = ["No", "Nama", "Jenis Kelamin", "Usia", "Kelas", 
          "X1", "X2", "X3", "Verbal", "Fisik", "Sosial", "Cyber",
          "Sumber", "Prediksi Prestasi", "Kategori"]
if sheet.row_values(1) != HEADER:
    sheet.clear()
    sheet.append_row(HEADER)

# === LOAD MODEL ===
with open("model_prestasi.pkl", "rb") as f:
    model = pickle.load(f)

# === FUNGSI KATEGORI ===
def kategori(y):
    if y < 2.5:
        return "Kurang"
    elif y < 3.5:
        return "Cukup"
    elif y < 4.25:
        return "Baik"
    else:
        return "Sangat Baik"

# === FUNGSI EKSTRAK FITUR UNTUK MODEL ===
def get_model_input(df):
    df = df.rename(columns={
        "Verbal": "Bullying_Verbal",
        "Fisik": "Bullying_Fisik",
        "Sosial": "Bullying_Sosial",
        "Cyber": "Bullying_Cyber"
    })
    return df[["X1", "X2", "X3", "Bullying_Verbal", "Bullying_Fisik", "Bullying_Sosial", "Bullying_Cyber"]]

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

st.markdown("Skor Jenis Bullying (1-5)")
verbal = st.slider("Bullying Verbal", 1.0, 5.0, 3.0)
fisik = st.slider("Bullying Fisik", 1.0, 5.0, 3.0)
sosial = st.slider("Bullying Sosial", 1.0, 5.0, 3.0)
cyber = st.slider("Bullying Cyber", 1.0, 5.0, 3.0)

if st.button("Prediksi Prestasi"):
    df_input = pd.DataFrame([{
        "X1": x1,
        "X2": x2,
        "X3": x3,
        "Verbal": verbal,
        "Fisik": fisik,
        "Sosial": sosial,
        "Cyber": cyber
    }])
    prediction = model.predict(get_model_input(df_input))[0]
    kategori_hasil = kategori(prediction)

    st.success(f"Prediksi Prestasi Belajar: {prediction:.2f} ({kategori_hasil})")

    df_hasil_manual = pd.DataFrame([{
        "Nama": nama,
        "Jenis Kelamin": jenis_kelamin,
        "Usia": usia,
        "Kelas": kelas,
        "X1": x1,
        "X2": x2,
        "X3": x3,
        "Verbal": verbal,
        "Fisik": fisik,
        "Sosial": sosial,
        "Cyber": cyber,
        "Prediksi Prestasi": round(prediction, 2),
        "Kategori": kategori_hasil
    }])
    st.dataframe(df_hasil_manual)

    new_row = [
        len(sheet.get_all_values()), nama, jenis_kelamin, usia, kelas,
        x1, x2, x3, verbal, fisik, sosial, cyber, "Manual", prediction, kategori_hasil
    ]
    sheet.append_row(new_row)
    st.info("Data berhasil disimpan ke Google Sheets.")

# === UPLOAD FILE CSV ===
st.header("Upload CSV")
uploaded_file = st.file_uploader("Upload file CSV (wajib: Nama, Jenis Kelamin, Usia, Kelas, X1, X2, X3, Verbal, Fisik, Sosial, Cyber)", type=["csv"])

if uploaded_file is not None:
    df_upload = pd.read_csv(uploaded_file)

    required_columns = ["Nama", "Jenis Kelamin", "Usia", "Kelas", "X1", "X2", "X3", "Verbal", "Fisik", "Sosial", "Cyber"]
    if all(col in df_upload.columns for col in required_columns):
        df_upload["Prediksi_Y"] = model.predict(get_model_input(df_upload))
        df_upload["Kategori"] = df_upload["Prediksi_Y"].apply(kategori)

        st.subheader("Hasil Prediksi dari CSV")
        st.dataframe(df_upload)

        for idx, row in df_upload.iterrows():
            new_row = [
                len(sheet.get_all_values()),
                row["Nama"],
                row["Jenis Kelamin"],
                row["Usia"],
                row["Kelas"],
                row["X1"],
                row["X2"],
                row["X3"],
                row["Verbal"],
                row["Fisik"],
                row["Sosial"],
                row["Cyber"],
                "CSV",
                row["Prediksi_Y"],
                row["Kategori"]
            ]
            sheet.append_row(new_row)
        st.success("Semua data dari CSV berhasil diprediksi dan disimpan ke Google Sheets!")

        # Visualisasi Korelasi
        st.subheader("Visualisasi Korelasi Variabel")
        fig, ax = plt.subplots(figsize=(6, 4))
        sns.heatmap(df_upload[["X1", "X2", "X3", "Prediksi_Y"]].corr(), annot=True, cmap="coolwarm", ax=ax)
        st.pyplot(fig)

        st.subheader("Plot X vs Prediksi")
        for x_col in ["X1", "X2", "X3"]:
            fig, ax = plt.subplots()
            sns.regplot(x=df_upload[x_col], y=df_upload["Prediksi_Y"], ax=ax,
                        line_kws={"color": "red"}, scatter_kws={"s": 40, "alpha": 0.7})
            ax.set_title(f"{x_col} vs Prediksi Prestasi", fontsize=13)
            ax.set_xlabel(x_col)
            ax.set_ylabel("Prediksi Prestasi")
            ax.grid(True)
            st.pyplot(fig)

        st.markdown("""
        Keterangan Visualisasi:
        - Titik biru adalah data hasil input siswa dari CSV.
        - Garis merah adalah garis tren regresi linier.
        """)
    else:
        st.error("CSV harus memiliki kolom: Nama, Jenis Kelamin, Usia, Kelas, X1, X2, X3, Verbal, Fisik, Sosial, Cyber")
