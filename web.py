import streamlit as st
import pandas as pd

# Sayfa genel ayarı
st.set_page_config(page_title="Dijital Sis Arayüzü", layout="wide")

# Sol Menü - Navigasyon
st.sidebar.title("DİJİTAL SİS")
sayfa = st.sidebar.radio("Görünüm Seçin:", ["1. Başlangıç (QR & İstasyon)", "2. Operatör Ekranı", "3. Yönetici Ekranı"])

# ---------------------------------------------------------
# 1. BAŞLANGIÇ EKRANI (İş Emri ve İstasyon Seçimi)
# ---------------------------------------------------------
if sayfa == "1. Başlangıç (QR & İstasyon)":
    st.title("Yeni Görev Başlat")
    
    st.info("İşe başlamak için iş emrini okutun ve istasyonu seçin.")
    st.text_input("📷 İş Emri QR Kodunu Okutun (veya manuel girin):", placeholder="Örn: WO-2024-100")
    st.selectbox("İstasyon Seçin:", ["Montaj 1", "Montaj 2", "Kalite Kontrol", "Test ve Paketleme"])
    
    st.button("İşe Başla (Operatör Ekranına Geç)", type="primary")

# ---------------------------------------------------------
# 2. OPERATÖR EKRANI
# ---------------------------------------------------------
elif sayfa == "2. Operatör Ekranı":
    st.title("İstasyon: Montaj 1 | Personel: A")
    
    # Ekranı 3 ana sütuna bölüyoruz
    sol, orta, sag = st.columns([1.5, 2.5, 1.5])

    # SOL KOLON: Durum ve Hızlı Kontrol
    with sol:
        st.subheader("Mevcut Görev")
        st.info("**İşlenecek Ürün:** SN-123456\n\n**İş Emri:** WO-2024-100")
        
        st.write("**Kontrol**")
        st.button("🟢 Devam Et", use_container_width=True)
        st.button("🔴 Dur", use_container_width=True)
        st.button("🔵 Bitir", use_container_width=True)

    # ORTA KOLON: Montaj Adımları (Tik ve Çarpı butonlu)
    with orta:
        st.subheader("Montaj Adımları")
        
        # Adım 1
        a1_c1, a1_c2, a1_c3 = st.columns([3, 1, 1])
        a1_c1.write("🛠️ **Adım 1:** Vida Sıkma (2.5 Nm)")
        a1_c2.button("✅", key="a1_ok", help="Uygulandı")
        a1_c3.button("❌", key="a1_no", help="Uygulanamadı / Hata")

        # Adım 2 ve O Adıma Özel Hata Bildirimi
        a2_c1, a2_c2, a2_c3 = st.columns([3, 1, 1])
        a2_c1.write("🔌 **Adım 2:** Kablo Bağlantısı")
        a2_c2.button("✅", key="a2_ok")
        a2_c3.button("❌", key="a2_no")
        
        # Direkt o adım seçilerek hata ekleme kısmı (Yönetici nerede hata olduğunu bilecek)
        with st.expander("📸 Adım 2 İçin Hata Bildir"):
            st.camera_input("Hata Görseli Çek")
            st.text_area("Hatanın Yazılı Açıklaması:")
            st.button("Adım 2 Hata Kaydını Yöneticye Gönder")

        # Adım 3 - Zorunlu Kalite Kontrolü (Kırmızı Uyarı)
        st.error("🔍 **Adım 3: Zorunlu Kalite Kontrolü**\n\nKALİTE BİRİMİNDEN ONAY BEKLENİYOR - İLERLEME KİLİTLİ")
        
        # Adım 4 (Kalite onayı gelmediği için pasif durumda)
        a4_c1, a4_c2, a4_c3 = st.columns([3, 1, 1])
        a4_c1.write("⚙️ **Adım 4:** Son Montaj (Şu an kilitli)")
        a4_c2.button("✅", key="a4_ok", disabled=True)
        a4_c3.button("❌", key="a4_no", disabled=True)

        st.divider()
        # Sonraki istasyon için mesaj
        st.text_input("Bir Sonraki Montaj Aşaması İçin Mesaj Bırakın:", placeholder="Örn: Gelecek istasyonda torkuna dikkat edilsin...")

    # SAĞ KOLON: Duruşlar ve Tomcad
    with sag:
        st.subheader("Duruş Al")
        st.button("☕ Mola Al", use_container_width=True)
        st.button("📦 Depodan Parça Temini", use_container_width=True)
        st.button("🔧 Makine Arızası", use_container_width=True)
        st.button("🚑 İş Kazası Bildirimi", use_container_width=True)
        
        st.divider()
        st.subheader("Uygulamalar")
        st.button("📐 Tomcad CAD - Aç / Görüntüle", use_container_width=True)

    # ALT KISIM: Yöneticiye Acil Mesaj (El altında değil, en altta)
    st.divider()
    st.write("**İletişim**")
    with st.expander("✉️ Yöneticiye Anlık Bildirim Mesajı Gönder"):
        st.text_area("Yöneticinin ekranına düşecek mesaj:")
        st.button("Mesajı İlet")

# ---------------------------------------------------------
# 3. YÖNETİCİ EKRANI (Detaylı Takip ve Analiz)
# ---------------------------------------------------------
elif sayfa == "3. Yönetici Ekranı":
    st.title("Yönetici Dashboard - Canlı Takip")
    
    # 1. BÖLÜM: Üst KPI Kartları
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Günlük Üretim Adedi", "450 / 600")
    k2.metric("Günlük Verim", "%75")
    k3.metric("Personel Verimi (Ort.)", "%82")
    k4.metric("Personel Hata Geçmişi (Toplam)", "7 Hata")

    st.divider()

    # 2. BÖLÜM: Canlı Takip ve Duruş Analizi
    col_canli, col_durus = st.columns(2)
    
    with col_canli:
        st.subheader("📍 Hangi İstasyonda Çalışma Var? (Canlı)")
        st.success("**Montaj 1:** Çalışıyor (Personel A) - SN: 123456")
        st.warning("**Montaj 2:** Malzeme Bekliyor (Depo Onayı)")
        st.error("**Kalite İstasyonu:** Teknik Destek Bekliyor / Sistem Arızası")
        
        st.subheader("⚠️ Acil Bilgilendirme (Kırmızı Bayrak)")
        st.error("Montaj 1'den Acil Mesaj: Tork anahtarı kalibrasyonu bozuldu!")

    with col_durus:
        st.subheader("⏱️ Toplam Duruş Süresi ve Nedenleri")
        # Basit bir bar grafiği
        durus_veri = pd.DataFrame({
            'Neden': ['Malzeme Bekleme', 'Kalite Bekleme', 'Teknik Destek', 'Mola'],
            'Süre (Dakika)': [45, 30, 15, 20]
        }).set_index('Neden')
        st.bar_chart(durus_veri)

    st.divider()

    # 3. BÖLÜM: İzlenebilirlik (Montaj Geçmişi ve Operasyon Zamanları)
    st.subheader("🔍 İzlenebilirlik ve Üretim Geçmişi")
    st.text_input("Seri Numarası ile Geçmiş Ara:", placeholder="Örn: SN-123456")
    
    # Operasyon başlangıç/bitiş, personel geçmişi ve adıma özel hata tablosu
    tablo_gecmis = pd.DataFrame({
        "İşlem Zamanı": ["08:00 - 08:15", "08:15 - 08:20", "08:20 - Bekliyor"],
        "Operatör": ["Personel A", "Personel A", "Kalite Uzmanı"],
        "İstasyon": ["Montaj 1", "Montaj 1", "Montaj 1"],
        "Adım": ["Adım 1: Vida Sıkma", "Adım 2: Kablo Bağlantısı", "Adım 3: Kalite Kontrol"],
        "Durum": ["Başarılı (✅)", "Hatalı (❌)", "Onay Bekliyor"],
        "Yazılı & Görsel Hata Detayı": ["-", "Görsel Var: Kablo ucu koptu.", "-"]
    })
    st.dataframe(tablo_gecmis, use_container_width=True)

    # 4. BÖLÜM: Test ve Ölçüm Sonuçları
    st.subheader("📊 Test ve Anlık Ölçüm Sonuçları Kaydı")
    test_veri = pd.DataFrame({
        "Seri No": ["SN-123454", "SN-123455"],
        "Tork Değeri (Montaj 1)": ["2.4 Nm", "2.5 Nm"],
        "Elektrik Testi": ["Geçti", "Kaldı (Kısa Devre)"],
        "Son Karar": ["ONAY", "RED (Yeniden İşlem)"]
    })
    st.dataframe(test_veri, use_container_width=True)
