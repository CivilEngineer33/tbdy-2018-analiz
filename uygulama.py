import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from io import BytesIO
from fpdf import FPDF
import os

# Sayfa Ayarları - Ofis Modu
st.set_page_config(page_title="Ertuğrul HAN | TBDY-2018 Ofis Paneli", layout="wide")

class PDFReport(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 12)
        self.cell(0, 10, 'ERTUGRUL HAN - INSAAT MUHENDISI', ln=True, align='L')
        self.set_font('helvetica', '', 9)
        self.cell(0, 5, 'TBDY-2018 Sismik Analiz ve Spektrum Hesap Raporu', ln=True, align='L')
        self.line(10, 27, 200, 27)
        self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Sayfa {self.page_no()}', align='C')

def create_pdf(params, results, df, fig_main, fig_sve, fig_ra):
    pdf = PDFReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # SAYFA 1: PARAMETRELER VE TABLOLAR
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 16)
    pdf.cell(0, 10, 'DEPREM PARAMETRELERI HESAP RAPORU', ln=True, align='C')
    pdf.ln(5)

    pdf.set_font('helvetica', 'B', 11)
    pdf.cell(0, 8, '1. Girdi Parametreleri', ln=True)
    pdf.set_font('helvetica', '', 10)
    for k, v in [["Yerel Zemin Sinifi", params['zemin']], ["Ss (Kisa Periyot)", f"{params['Ss']:.4f}"], ["S1 (1.0 sn Periyot)", f"{params['S1']:.4f}"], ["I (Bina Onem Katsayisi)", f"{params['I']:.2f}"], ["R (Davranis Katsayisi)", f"{params['R']:.2f}"], ["D (Dayanim Fazlaligi)", f"{params['D']:.2f}"]]:
        pdf.cell(85, 7, k, border=1); pdf.cell(40, 7, v, border=1, ln=True)

    pdf.ln(5)
    pdf.set_font('helvetica', 'B', 11)
    pdf.cell(0, 8, '2. Tasarim Parametreleri', ln=True)
    pdf.set_font('helvetica', '', 10)
    for k, v in [["SDS", f"{results['SDS']:.4f}"], ["SD1", f"{results['SD1']:.4f}"], ["TA (sn)", f"{results['TA']:.4f}"], ["TB (sn)", f"{results['TB']:.4f}"], ["Fs / F1", f"{results['Fs']:.3f} / {results['F1']:.3f}"]]:
        pdf.cell(85, 7, k, border=1); pdf.cell(40, 7, v, border=1, ln=True)

    pdf.ln(5)
    pdf.set_font('helvetica', 'B', 11)
    pdf.cell(0, 8, '3. Kritik Spektrum Verileri (Ozet Tablo)', ln=True)
    pdf.set_font('helvetica', 'B', 9)
    pdf.cell(30, 8, "T(s)", border=1, align='C'); pdf.cell(40, 8, "Sae(g) [Elastik]", border=1, align='C'); pdf.cell(40, 8, "Sad(g) [Tasarim]", border=1, align='C'); pdf.cell(30, 8, "Ra(T)", border=1, align='C', ln=True)
    pdf.set_font('helvetica', '', 9)
    for p in [0, results['TA'], results['TB'], 1.0, 2.0, params['TL']]:
        idx = (df['T']-p).abs().idxmin(); row = df.loc[idx]
        pdf.cell(30, 7, f"{row['T']:.3f}", border=1, align='C'); pdf.cell(40, 7, f"{row['Sae']:.4f}", border=1, align='C'); pdf.cell(40, 7, f"{row['Sad']:.4f}", border=1, align='C'); pdf.cell(30, 7, f"{row['Ra']:.2f}", border=1, align='C', ln=True)

    # SAYFA 2: YÖNETMELİK GÖRSELLERİ (HİÇBİR ŞEY ÜST ÜSTE BİNMEZ)
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '4. TBDY-2018 HESAP ESASLARI VE SEMALAR', ln=True)
    pdf.ln(5)
    
    images = ["Resim1.png", "Resim2.png", "Resim3.png"]
    for img in images:
        if os.path.exists(img):
            # Resim eklemeden önce sayfa sonu kontrolü
            if pdf.get_y() > 180:
                pdf.add_page()
            
            pdf.image(img, x=40, y=pdf.get_y(), w=130)
            pdf.set_y(pdf.get_y() + 85) # Resim boyutu + boşluk
            pdf.ln(5)

    # SAYFA 3, 4, 5: GRAFİKLER (TEK SAYFA, TAM NETLİK)
    plots = [
        (fig_main, "GRAFIK 1: YATAY IVME SPEKTRUMLARI (Sae & Sad)"),
        (fig_sve, "GRAFIK 2: DUSEY IVME SPEKTRUMU (Sve)"),
        (fig_ra, "GRAFIK 3: DEPREM YUKU AZALTMA KATSAYISI (Ra)")
    ]
    for f, title in plots:
        pdf.add_page()
        pdf.set_font('helvetica', 'B', 20)
        pdf.cell(0, 20, title, ln=True, align='C')
        img_bytes = pio.to_image(f, format="png", width=1200, height=800, scale=3)
        pdf.image(BytesIO(img_bytes), x=10, y=40, w=190)

    return bytes(pdf.output())

# --- HESAPLAMA MOTORU ---
def get_fs(zemin, ss):
    p = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5]; t = {"ZA":[0.8]*6,"ZB":[0.9]*6,"ZC":[1.3,1.3,1.2,1.2,1.2,1.2],"ZD":[1.6,1.4,1.2,1.1,1.0,1.0],"ZE":[2.4,1.7,1.3,1.1,0.9,0.8]}
    return np.interp(ss, p, t[zemin])

def get_f1(zemin, s1):
    p = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]; t = {"ZA":[0.8]*6,"ZB":[0.8]*6,"ZC":[1.5,1.5,1.5,1.5,1.5,1.4],"ZD":[2.4,2.2,2.0,1.9,1.8,1.7],"ZE":[4.2,3.3,2.8,2.4,2.2,2.0]}
    return np.interp(s1, p, t[zemin])

# --- UI ---
with st.sidebar:
    st.header("🏢 Proje Parametreleri")
    zemin_sinifi = st.selectbox("Yerel Zemin Sınıfı", ["ZA", "ZB", "ZC", "ZD", "ZE"], index=2)
    Ss, S1 = st.number_input("Ss", 1.0540, format="%.4f"), st.number_input("S1", 0.2970, format="%.4f")
    R, D, I, TL = st.number_input("R (Davranış)", 8.0), st.number_input("D (Dayanım)", 3.0), st.number_input("I (Önem)", 1.0), st.number_input("TL", 6.0)

Fs, F1 = get_fs(zemin_sinifi, Ss), get_f1(zemin_sinifi, S1)
SDS, SD1 = Ss*Fs, S1*F1
TA, TB = 0.2*(SD1/SDS) if SDS>0 else 0, SD1/SDS if SDS>0 else 0
TAD, TBD, TLD = TA/3, TB/3, TL/2

T_vals = np.sort(np.unique(np.concatenate([np.arange(0, 8.01, 0.05), [TA, TB, TL, TAD, TBD, TLD]])))
data = [{"T":T, "Sae":(0.4+0.6*T/TA)*SDS if T<=TA else (SDS if T<=TB else (SD1/T if T<=TL else (SD1*TL)/T**2)), "Ra":D+(R/I-D)*(T/TB) if T<=TB else R/I, "Sve":(0.32+0.48*T/TAD)*SDS if T<=TAD else (0.8*SDS if T<=TBD else (0.8*SD1/T if T<=TLD else 0.8*SD1*TL/T**2))} for T in T_vals]
for d in data: d["Sad"] = d["Sae"] / d["Ra"]
df = pd.DataFrame(data)

# --- ANA EKRAN ---
tab1, tab2 = st.tabs(["📊 Analiz ve Raporlama", "📚 Yönetmelik Formülleri"])

with tab1:
    st.title("🏗️ TBDY-2018 Sismik Analiz Platformu")
    st.markdown(f"**Mühendis:** Ertuğrul HAN")
    
    # Buton Paneli (Excel Hatası Çözüldü)
    c1, c2, _ = st.columns([1,1,2])
    
    # PDF Hazırlığı
    fig_main = go.Figure(); fig_main.add_trace(go.Scatter(x=df['T'], y=df['Sae'], name='Elastik (Sae)', line=dict(color='#1f77b4', width=4))); fig_main.add_trace(go.Scatter(x=df['T'], y=df['Sad'], name='Tasarım (Sad)', line=dict(color='#d62728', dash='dash', width=4))); fig_main.update_layout(template="plotly_white", xaxis_title="T (sn)", yaxis_title="İvme (g)")
    fig_sve = go.Figure(); fig_sve.add_trace(go.Scatter(x=df['T'], y=df['Sve'], name='Düşey (Sve)', line=dict(color='#2ca02c', width=4))); fig_sve.update_layout(template="plotly_white", title="DUSEY IVME SPEKTRUMU", xaxis_title="T (sn)", yaxis_title="Sve (g)")
    fig_ra = go.Figure(); fig_ra.add_trace(go.Scatter(x=df['T'], y=df['Ra'], name='Ra(T)', line=dict(color='#ff7f0e', width=4))); fig_ra.update_layout(template="plotly_white", title="AZALTMA KATSAYISI", xaxis_title="T (sn)", yaxis_title="Ra")

    with c1:
        st.download_button("📄 PDF Raporu İndir", data=create_pdf({'zemin':zemin_sinifi,'Ss':Ss,'S1':S1,'I':I,'R':R,'D':D,'TL':TL}, {'SDS':SDS,'SD1':SD1,'TA':TA,'TB':TB,'Fs':Fs,'F1':F1}, df, fig_main, fig_sve, fig_ra), file_name="TBDY2018_Hesap_Raporu.pdf")
    
    with c2:
        # DOĞRU EXCEL YAZMA MANTIĞI
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Hesap_Verileri')
        st.download_button("📂 Excel Verilerini İndir", data=excel_buffer.getvalue(), file_name="TBDY2018_Veriler.xlsx", mime="application/vnd.ms-excel")

    st.plotly_chart(fig_main, use_container_width=True)
    st.columns(2)[0].plotly_chart(fig_sve, use_container_width=True); st.columns(2)[1].plotly_chart(fig_ra, use_container_width=True)

with tab2:
    st.header("📚 TBDY-2018 Hesap Esasları")
    for i in range(1, 4):
        img_name = f"Resim{i}.png"
        if os.path.exists(img_name):
            st.image(img_name, caption=f"TBDY-2018 Şema {i}")
            st.divider()