import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px

# --- Konfigurasi Halaman Streamlit ---
st.set_page_config(
    page_title="Dashboard Pembangkit Listrik Tenaga Surya",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Judul Aplikasi ---
st.title("Dashboard Analisis Pembangkit Listrik Tenaga Surya")
st.markdown("by Kelompok 3.")

# --- Fungsi untuk Memuat dan Memproses Data ---
@st.cache_data # Cache data agar tidak dimuat ulang
def load_and_process_data(file_path):
    try:
        df = pd.read_csv(file_path)

        # Mengubah nama kolom 'Date-Hour(NMT)' menjadi 'DATE_TIME' yang lebih standar
        df.rename(columns={'Date-Hour(NMT)': 'DATE_TIME'}, inplace=True)

        # Format di data Anda adalah 'dd.mm.YYYY-HH:MM'
        df['DATE_TIME'] = pd.to_datetime(df['DATE_TIME'], format='%d.%m.%Y-%H:%M', errors='coerce')

        # Buat kolom DAY dan HOUR untuk analisis lebih lanjut
        df['DATE'] = df['DATE_TIME'].dt.date
        df['HOUR'] = df['DATE_TIME'].dt.hour

        # Atur DATE_TIME sebagai indeks untuk analisis time series
        df = df.set_index('DATE_TIME')
        return df
    except FileNotFoundError:
        st.error(f"File '{file_path}' tidak ditemukan. Pastikan file CSV ada di repository.")
        return pd.DataFrame()
    except KeyError as e:
        st.error(f"Error: Kolom yang dibutuhkan tidak ditemukan. Pastikan file CSV Anda memiliki kolom 'Date-Hour(NMT)'. Detail: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Terjadi kesalahan saat memuat atau memproses file: {e}")
        return pd.DataFrame()

# --- Memuat data langsung dari file di repository ---
file_path = "Solar Power Plant Data.csv"
df = load_and_process_data(file_path)

if not df.empty:
    st.success(f"Data dari '{file_path}' berhasil dimuat!")

    # --- Sidebar untuk Filter Data ---
    st.sidebar.header("Filter Data")
    
    min_date = df.index.min().date()
    max_date = df.index.max().date()
    date_range = st.sidebar.date_input(
        "Pilih Rentang Tanggal",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    if len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        df_filtered = df.loc[start_date:end_date]
    else:
        df_filtered = df
        st.sidebar.warning("Silakan pilih rentang dua tanggal.")

    if df_filtered.empty:
        st.warning("Tidak ada data dalam rentang tanggal yang dipilih. Silakan sesuaikan filter.")
        st.stop()

    # Menambahkan 'PRODUCTION' agar 'SystemProduction' terdeteksi
    generation_cols = [col for col in df_filtered.columns if 'GENERATION' in col.upper() or 'YIELD' in col.upper() or 'POWER' in col.upper() or 'PRODUCTION' in col.upper()]

    if not generation_cols:
        st.error("Tidak dapat menemukan kolom pembangkitan energi (misal: 'SystemProduction'). Cek kembali dataset Anda.")
        st.stop()

    selected_generation_col = st.sidebar.selectbox(
        "Pilih Kolom Pembangkitan Energi",
        generation_cols,
        index=0
    )

    if not pd.api.types.is_numeric_dtype(df_filtered[selected_generation_col]):
        st.error(f"Kolom '{selected_generation_col}' bukan data numerik.")
        st.stop()

    # --- Mulai Tampilan Dashboard ---
    st.header("1. Ringkasan Data")
    st.dataframe(df_filtered.head())

    st.header("2. Statistik Pembangkitan Energi")
    st.write(f"**Kolom yang dianalisis:** `{selected_generation_col}`")

    mean_gen, median_gen, std_dev_gen, min_gen, max_gen = (
        df_filtered[selected_generation_col].mean(),
        df_filtered[selected_generation_col].median(),
        df_filtered[selected_generation_col].std(),
        df_filtered[selected_generation_col].min(),
        df_filtered[selected_generation_col].max()
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Rata-rata Pembangkitan", f"{mean_gen:.2f}")
    col2.metric("Median Pembangkitan", f"{median_gen:.2f}")
    col3.metric("Std. Deviasi", f"{std_dev_gen:.2f}")
    col4.metric("Minimum", f"{min_gen:.2f}")
    col5.metric("Maksimum", f"{max_gen:.2f}")

    st.header("3. Tren Pembangkitan Energi dari Waktu ke Waktu")
    resample_option = st.selectbox("Agregasi Data:", ("Per Jam", "Harian", "Mingguan", "Bulanan"), index=1) # Default Harian

    resample_map = {"Harian": "D", "Mingguan": "W", "Bulanan": "M"}
    if resample_option in resample_map:
        df_resampled = df_filtered[selected_generation_col].resample(resample_map[resample_option]).sum().reset_index()
    else:
        df_resampled = df_filtered.reset_index()

    fig_trend = px.line(df_resampled, x='DATE_TIME', y=selected_generation_col,
                        title=f'Tren Pembangkitan Energi ({resample_option})',
                        labels={'DATE_TIME': 'Waktu', selected_generation_col: 'Total Pembangkitan'})
    fig_trend.update_layout(hovermode="x unified")
    st.plotly_chart(fig_trend, use_container_width=True)

    st.header("4. Distribusi Pembangkitan Energi")
    col_hist, col_box = st.columns(2)

    with col_hist:
        fig_hist, ax_hist = plt.subplots()
        sns.histplot(df_filtered[df_filtered[selected_generation_col] > 0][selected_generation_col], bins=30, kde=True, color='skyblue', ax=ax_hist)
        ax_hist.set_title(f'Histogram {selected_generation_col} (hanya saat ada produksi)')
        st.pyplot(fig_hist)

    with col_box:
        fig_box, ax_box = plt.subplots()
        sns.boxplot(y=df_filtered[selected_generation_col], color='lightcoral', ax=ax_box)
        ax_box.set_title(f'Boxplot {selected_generation_col}')
        st.pyplot(fig_box)

    st.header("5. Pola Pembangkitan Rata-rata Per Jam")
    hourly_avg = df_filtered.groupby('HOUR')[selected_generation_col].mean().reset_index()
    fig_hourly = px.line(hourly_avg, x='HOUR', y=selected_generation_col,
                         title='Rata-rata Pembangkitan Energi Per Jam',
                         labels={'HOUR': 'Jam dalam Sehari', selected_generation_col: 'Rata-rata Pembangkitan'})
    fig_hourly.update_traces(mode='lines+markers')
    st.plotly_chart(fig_hourly, use_container_width=True)

    # BONUS: Korelasi dengan Faktor Lain
    st.header("6. Analisis Korelasi")
    # Pilih kolom numerik untuk korelasi
    numeric_cols = df_filtered.select_dtypes(include=np.number).columns.tolist()
    
    # Check if 'Radiation' exists, otherwise use the first numeric column
    default_col_index = 0
    if 'Radiation' in numeric_cols:
        default_col_index = numeric_cols.index('Radiation')
    
    correlation_col = st.selectbox("Pilih variabel untuk korelasi dengan pembangkitan energi:", 
                                  numeric_cols, 
                                  index=default_col_index)

    fig_corr = px.scatter(df_filtered, x=correlation_col, y=selected_generation_col,
                          title=f'Korelasi antara {correlation_col} dan {selected_generation_col}',
                          trendline="ols") # ols = ordinary least squares, menambahkan garis tren
    st.plotly_chart(fig_corr, use_container_width=True)

else:
    st.error("❌ File 'Solar Power Plant Data.csv' tidak dapat dimuat. Pastikan file ada di repository dengan nama yang tepat.")
