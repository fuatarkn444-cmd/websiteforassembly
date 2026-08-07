import streamlit as st
import pandas as pd

# Sayfa genişliğini ayarlama
st.set_page_config(page_title="Dijital Sis", layout="wide")

# Sol menü - Sayfa geçişleri
st.sidebar.title("Menü")
sayfa = st.sidebar.radio("Görünüm Seçin:", ["Operatör Ekranı", "Yönetici Ekranı"])

# ---------------------------------------------------------
# OPERATÖR EKRANI
# ---------------------------------------------------------
if sayfa == "Operatör Ekranı":
    st.title("İstasyon: Montaj 1 - Personel A")
    
    # Ekranı 3 sütuna bölüyoruz
    sol_kolon, orta_kolon, sag_kolon = st.columns([1, 2, 1])
    
    # SOL KOLON: İşlem Kontrolü
    with sol_kolon:
        st.subheader("Mevcut Görev")
        st.info("Ürün: SN-123456 \n\n İş Emri: WO-2024-100")
        
        st.button("Devam Et", type="primary", use_container_width=True)
        st.button("Dur", use_container_width=True)
        st.button("Bitir", use_container_width=True)

    # ORTA KOLON: Montaj Adımları
    with orta_kolon:
        st.subheader("Montaj Adımları")
        
        st.checkbox("Adım 1: Vida Sıkma (2.5 Nm)")
        st.checkbox("Adım 2: Parça Yerleştirme")
        
        # Kalite kontrol gibi uyarı gerektiren durumlar için error kutusu
        st.error("Adım 3: Zorunlu Kalite Kontrolü (Onay Bekleniyor)")
        
        st.checkbox("Adım 4: Son Montaj", disabled=True) # Onay gelene kadar tıklanamaz
        
        st.text_input("Bir Sonraki Aşama İçin Mesaj:")

    # SAĞ KOLON: Duruşlar ve Uygulamalar
    with sag_kolon:
        st.subheader("Duruş Al & Uygulamalar")
        st.button("☕ Mola Al", use_container_width=True)
        st.button("⚙️ Parça Temini", use_container_width=True)
        
        st.divider() # Araya çizgi çeker
        
        # Hata bildirim formu (Genişleyebilir kutu)
        with st.expander("⚠️ Hata Bildir"):
            st.text_area("Hata Açıklaması:")
            st.file_uploader("Fotoğraf Ekle")
            st.button("Gönder")
            
        st.divider()
        st.button("📐 Tomcad CAD Aç", use_container_width=True)

# ---------------------------------------------------------
# YÖNETİCİ EKRANI
# ---------------------------------------------------------
elif sayfa == "Yönetici Ekranı":
    st.title("Yönetici Dashboard")
    
    # En üstteki özet veriler için 4'lü sütun
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(label="Günlük Üretim", value="450 / 600")
    k2.metric(label="Günlük Verim", value="%75", delta="-2%")
    k3.metric(label="Personel A Verimi", value="%82", delta="5%")
    k4.metric(label="Personel Hata Sayısı", value="3")
    
    st.divider()
    
    # Alt kısmı grafik ve tablo olarak ikiye bölüyoruz
    grafik_kolon, tablo_kolon = st.columns(2)
    
    # Grafikler
    with grafik_kolon:
        st.subheader("Duruş Süreleri (Nedenlere Göre)")
        # Örnek grafik verisi oluşturma
        grafik_verisi = pd.DataFrame({
            'Sebep': ['Malzeme', 'Kalite', 'Teknik', 'Diğer'],
            'Süre (Dk)': [45, 30, 15, 10]
        }).set_index('Sebep')
        
        st.bar_chart(grafik_verisi)
        
    # Tablolar
    with tablo_kolon:
        st.subheader("Kritik Hatalar ve Duruşlar")
        # Örnek tablo verisi oluşturma
        tablo_verisi = pd.DataFrame({
            "İş Emri": ["WO-1002", "WO-1003", "WO-1004"],
            "Seri No": ["SN-12345", "SN-54321", "SN-98765"],
            "Sorun": ["Vida Başı Hasarlı", "Kablo Koptu", "Eksik Parça"],
            "İstasyon": ["Montaj 1", "Montaj 2", "Montaj 1"]
        })
        
        st.dataframe(tablo_verisi, use_container_width=True)
