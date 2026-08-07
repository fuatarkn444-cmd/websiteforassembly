import streamlit as st
import pandas as pd
import time
import json
import os
from datetime import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Dijital Sis Arayüzü", layout="wide")

# --- VERİTABANI YÖNETİMİ (JSON DOSYASI) ---
DB_FILE = "db.json"

def load_db():
    if not os.path.exists(DB_FILE):
        default_db = {
            "stations": {
                "Montaj-1": {"status": "Bekliyor", "id": "", "sn": "", "target_qty": 0, "current_qty": 0, "step": 1, "work_time": 0.0, "break_time": 0.0, "last_work_start": None, "last_break_start": None},
                "Montaj-2": {"status": "Bekliyor", "id": "", "sn": "", "target_qty": 0, "current_qty": 0, "step": 1, "work_time": 0.0, "break_time": 0.0, "last_work_start": None, "last_break_start": None},
                "Montaj-3": {"status": "Bekliyor", "id": "", "sn": "", "target_qty": 0, "current_qty": 0, "step": 1, "work_time": 0.0, "break_time": 0.0, "last_work_start": None, "last_break_start": None}
            },
            "performance": {
                "Montaj-1": {"tamamlanan_is_emri": 0, "toplam_uretilen_parca": 0},
                "Montaj-2": {"tamamlanan_is_emri": 0, "toplam_uretilen_parca": 0},
                "Montaj-3": {"tamamlanan_is_emri": 0, "toplam_uretilen_parca": 0}
            },
            "errors": []
        }
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(default_db, f, indent=4)
            
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# Uygulama başlarken DB'yi çek
db = load_db()

# --- OTURUM YÖNETİMİ (Sadece o anki sekmeye özel veriler) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
if 'show_break_modal' not in st.session_state:
    st.session_state.show_break_modal = False

# --- KULLANICI HESAPLARI ---
USERS = {
    "m1": {"pass": "1234", "role": "Montaj-1"},
    "m2": {"pass": "1234", "role": "Montaj-2"},
    "m3": {"pass": "1234", "role": "Montaj-3"},
    "kalite1": {"pass": "kalite123", "role": "Kalite"},
    "admin": {"pass": "admin123", "role": "Yönetici"}
}

# --- YARDIMCI FONKSİYONLAR ---
def login(username, password):
    if username in USERS and USERS[username]["pass"] == password:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.role = USERS[username]["role"]
        st.rerun()
    else:
        st.error("Kullanıcı adı veya şifre hatalı!")

def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.rerun()

def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def get_live_work_time(istasyon):
    t = db["stations"][istasyon]["work_time"]
    if db["stations"][istasyon]["status"] == "Çalışıyor" and db["stations"][istasyon]["last_work_start"]:
        t += time.time() - db["stations"][istasyon]["last_work_start"]
    return t

def get_live_break_time(istasyon):
    t = db["stations"][istasyon]["break_time"]
    if db["stations"][istasyon]["status"] == "Mola" and db["stations"][istasyon]["last_break_start"]:
        t += time.time() - db["stations"][istasyon]["last_break_start"]
    return t

# --- GİRİŞ EKRANI ---
if not st.session_state.logged_in:
    st.title("DİJİTAL SİS - Giriş")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            st.subheader("Sisteme Giriş Yapın")
            user_input = st.text_input("Kullanıcı Adı")
            pass_input = st.text_input("Şifre", type="password")
            submit_btn = st.form_submit_button("Giriş", use_container_width=True)
            if submit_btn:
                login(user_input, pass_input)
        st.info("**Hesaplar:**\n- İstasyonlar: m1, m2, m3 (Şifre: 1234)\n- Kalite: kalite1 (Şifre: kalite123)\n- Yönetici: admin (Şifre: admin123)")

# --- SİSTEM UYGULAMASI ---
else:
    aktif_rol = st.session_state.role
    
    with st.sidebar:
        st.write(f"👤 **Hesap:** {st.session_state.username}")
        st.write(f"🏷️ **Birim:** {aktif_rol}")
        
        # Sadece istasyonlardaysak süreleri göster
        if aktif_rol in ["Montaj-1", "Montaj-2", "Montaj-3"]:
            st.write(f"⏱️ **Çalışma:** {format_time(get_live_work_time(aktif_rol))}")
            st.write(f"☕ **Mola:** {format_time(get_live_break_time(aktif_rol))}")
            
        if st.button("🔄 Verileri Güncelle (Yenile)", use_container_width=True):
            db = load_db() # Yeni verileri dosyadan oku
            st.rerun()
            
        st.divider()
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            logout()

    # ---------------------------------------------------------
    # YÖNETİCİ EKRANI
    # ---------------------------------------------------------
    if aktif_rol == "Yönetici":
        st.title("Yönetici Kontrol Paneli")
        
        tab1, tab2, tab3 = st.tabs(["İş Emri Gönder", "Canlı İzleme", "Genel Performans (Gün Sonu)"])
        
        with tab1:
            st.subheader("Yeni İş Emri Gönder")
            col_is_1, col_is_2 = st.columns(2)
            with col_is_1:
                hedef_istasyon = st.selectbox("Gönderilecek İstasyon:", ["Montaj-1", "Montaj-2", "Montaj-3"])
                wo_id = st.text_input("İş Emri Numarası:", value="WO-2024-100")
                sn_id = st.text_input("Ürün Seri Numarası (Başlangıç):", value="SN-123456")
                hedef_sayi = st.number_input("Üretilecek Adet (Hedef):", min_value=1, value=50)
                
                if st.button("🚀 Üretime Başla (İş Emrini Gönder)", type="primary"):
                    db["stations"][hedef_istasyon] = {
                        "status": "Çalışıyor", 
                        "id": wo_id, 
                        "sn": sn_id,
                        "target_qty": hedef_sayi,
                        "current_qty": 1,
                        "step": 1,
                        "work_time": 0.0,
                        "break_time": 0.0,
                        "last_work_start": time.time(),
                        "last_break_start": None
                    }
                    save_db(db)
                    st.success(f"İş emri {hedef_istasyon} istasyonuna gönderildi ve süre başlatıldı!")
                    st.rerun()

        with tab2:
            st.subheader("İstasyonların Canlı Durumu")
            c1, c2, c3 = st.columns(3)
            istasyonlar = ["Montaj-1", "Montaj-2", "Montaj-3"]
            kolonlar = [c1, c2, c3]
            
            for index, istasyon in enumerate(istasyonlar):
                with kolonlar[index]:
                    veri = db["stations"][istasyon]
                    st.markdown(f"### {istasyon}")
                    if veri["status"] == "Bekliyor":
                        st.warning("Boşta / Bekliyor")
                    else:
                        if veri["status"] == "Çalışıyor":
                            st.success(f"Çalışıyor ({veri['current_qty']}/{veri['target_qty']})")
                        else:
                            st.error(f"{veri['status']} ({veri['current_qty']}/{veri['target_qty']})")
                        
                        st.write(f"**İş Emri:** {veri['id']}")
                        st.write(f"**Çalışma:** {format_time(get_live_work_time(istasyon))}")
                        
                        if st.button(f"🚨 {istasyon} ACİL DURDUR", key=f"dur_{istasyon}"):
                            # Süreyi durdur
                            if veri["status"] == "Çalışıyor" and veri["last_work_start"]:
                                veri["work_time"] += time.time() - veri["last_work_start"]
                                veri["last_work_start"] = None
                            if veri["status"] == "Mola" and veri["last_break_start"]:
                                veri["break_time"] += time.time() - veri["last_break_start"]
                                veri["last_break_start"] = None
                                
                            veri["status"] = "Duraklatıldı"
                            save_db(db)
                            st.rerun()
                            
        with tab3:
            st.subheader("Genel Performans ve Kalıcı Veriler")
            st.info("Bu veriler sistem kapatılıp açılsa dahi silinmez.")
            perf_df = pd.DataFrame(db["performance"]).T
            st.dataframe(perf_df, use_container_width=True)
            
            st.subheader("Bildirilen Hatalar")
            if len(db["errors"]) > 0:
                st.dataframe(pd.DataFrame(db["errors"]), use_container_width=True)
            else:
                st.write("Kayıtlı hata bulunmuyor.")

    # ---------------------------------------------------------
    # KALİTE EKRANI
    # ---------------------------------------------------------
    elif aktif_rol == "Kalite":
        st.title("Kalite Kontrol Paneli")
        st.info("Bu ekran istasyondaki hata bildirimlerini izlemek içindir. Adım onayı istasyonların tabletlerinden yapılır.")
        if len(db["errors"]) > 0:
            st.dataframe(pd.DataFrame(db["errors"]), use_container_width=True)
        else:
            st.write("Aktif bir hata kaydı bulunmuyor.")

    # ---------------------------------------------------------
    # İSTASYON EKRANI (Montaj-1, Montaj-2, Montaj-3)
    # ---------------------------------------------------------
    elif aktif_rol in ["Montaj-1", "Montaj-2", "Montaj-3"]:
        istasyon_verisi = db["stations"][aktif_rol]
        durum = istasyon_verisi["status"]
        
        if durum == "Bekliyor":
            st.warning("⏳ Yöneticiden yeni iş emri bekleniyor...")
            st.info("İş emri gönderildiğinde görmek için sol menüden 'Verileri Güncelle' butonuna basınız.")
        else:
            if durum == "Çalışıyor":
                st.success(f"🟢 {aktif_rol} AKTİF - Üretim No: {istasyon_verisi['current_qty']} / {istasyon_verisi['target_qty']}")
            else:
                st.error(f"🔴 {aktif_rol} DURDU - Durum: {durum} - Üretim No: {istasyon_verisi['current_qty']} / {istasyon_verisi['target_qty']}")
            
            sol, orta, sag = st.columns([1.2, 2, 1.2])

            # SOL KOLON (Kontrol)
            with sol:
                st.subheader("Mevcut Görev")
                st.info(f"**Ürün SN:** {istasyon_verisi['sn']}\n\n**İş Emri:** {istasyon_verisi['id']}")
                
                if durum == "Duraklatıldı":
                    if st.button("▶️ İşe Devam Et", use_container_width=True):
                        istasyon_verisi["last_work_start"] = time.time()
                        istasyon_verisi["status"] = "Çalışıyor"
                        save_db(db)
                        st.rerun()
                        
                elif durum == "Çalışıyor":
                    if st.button("⏸️ İşi Duraklat", use_container_width=True):
                        if istasyon_verisi["last_work_start"]:
                            istasyon_verisi["work_time"] += time.time() - istasyon_verisi["last_work_start"]
                            istasyon_verisi["last_work_start"] = None
                        istasyon_verisi["status"] = "Duraklatıldı"
                        save_db(db)
                        st.rerun()

                st.divider()
                if st.button("☕ Mola Menüsü", use_container_width=True):
                    st.session_state.show_break_modal = not st.session_state.show_break_modal
                    
                if st.session_state.show_break_modal:
                    with st.expander("Mola İşlemleri", expanded=True):
                        if durum != "Mola":
                            if st.button("Molaya Çık", type="primary"):
                                # Çalışmayı durdur
                                if istasyon_verisi["status"] == "Çalışıyor" and istasyon_verisi["last_work_start"]:
                                    istasyon_verisi["work_time"] += time.time() - istasyon_verisi["last_work_start"]
                                    istasyon_verisi["last_work_start"] = None
                                # Molayı başlat
                                istasyon_verisi["last_break_start"] = time.time()
                                istasyon_verisi["status"] = "Mola"
                                st.session_state.show_break_modal = False
                                save_db(db)
                                st.rerun()
                        else:
                            if st.button("Moladan Dön", type="primary"):
                                # Molayı durdur
                                if istasyon_verisi["last_break_start"]:
                                    istasyon_verisi["break_time"] += time.time() - istasyon_verisi["last_break_start"]
                                    istasyon_verisi["last_break_start"] = None
                                # Çalışmayı başlat
                                istasyon_verisi["last_work_start"] = time.time()
                                istasyon_verisi["status"] = "Çalışıyor"
                                st.session_state.show_break_modal = False
                                save_db(db)
                                st.rerun()

            # ORTA KOLON (Montaj Adımları)
            with orta:
                st.subheader("Montaj Adımları")
                
                if durum == "Çalışıyor":
                    step = istasyon_verisi["step"]
                    
                    ad1 = st.checkbox("Adım 1: Vida Sıkma (2.5 Nm)", value=(step > 1), disabled=(step != 1))
                    if ad1 and step == 1: 
                        istasyon_verisi["step"] = 2
                        save_db(db)
                        st.rerun()
                        
                    ad2 = st.checkbox("Adım 2: Kablo Bağlantısı", value=(step > 2), disabled=(step != 2))
                    if ad2 and step == 2: 
                        istasyon_verisi["step"] = 3
                        save_db(db)
                        st.rerun()
                    
                    # ADIM 3: KALİTE ONAYI
                    if step == 3:
                        st.error("🔍 Adım 3: Zorunlu Kalite Kontrolü")
                        st.write("Devam etmek için kalite yetkilisinin şifresini girin:")
                        qc_pass = st.text_input("Şifre:", type="password")
                        if st.button("Kalite Onayını Ver"):
                            if qc_pass == USERS["kalite1"]["pass"]:
                                istasyon_verisi["step"] = 4
                                save_db(db)
                                st.success("Onaylandı!")
                                st.rerun()
                            else:
                                st.error("Hatalı Şifre!")
                    elif step > 3:
                        st.checkbox("Adım 3: Kalite Kontrol (Onaylandı)", value=True, disabled=True)
                    else:
                        st.checkbox("Adım 3: Kalite Kontrol (Kilitli)", value=False, disabled=True)
                        
                    ad4 = st.checkbox("Adım 4: Son Kontrol", value=(step > 4), disabled=(step != 4))
                    if ad4 and step == 4: 
                        istasyon_verisi["step"] = 5
                        save_db(db)
                        st.rerun()
                        
                    if step > 4:
                        st.success("Bu parçanın tüm adımları tamamlandı!")
                        if st.button("✅ Sıradaki Parçaya Geç (Kaydet)", type="primary", use_container_width=True):
                            # Performans verisine 1 parça ekle
                            db["performance"][aktif_rol]["toplam_uretilen_parca"] += 1
                            
                            if istasyon_verisi["current_qty"] < istasyon_verisi["target_qty"]:
                                istasyon_verisi["current_qty"] += 1
                                istasyon_verisi["step"] = 1
                            else:
                                # Süreyi durdur
                                if istasyon_verisi["last_work_start"]:
                                    istasyon_verisi["work_time"] += time.time() - istasyon_verisi["last_work_start"]
                                    istasyon_verisi["last_work_start"] = None
                                
                                istasyon_verisi["status"] = "Bekliyor"
                                db["performance"][aktif_rol]["tamamlanan_is_emri"] += 1
                                st.success("Hedef üretime ulaşıldı! İş emri bitti.")
                                
                            save_db(db)
                            st.rerun()
                else:
                    st.warning("Adımları görebilmek için istasyonun 'Çalışıyor' durumunda olması gerekir.")

            # SAĞ KOLON (Hata Belirt)
            with sag:
                st.subheader("Bildirim")
                with st.expander("⚠️ Hata Belirt", expanded=False):
                    st.write("**Bölge Seçiniz:**")
                    hata_bolgesi = st.radio("Nerede:", ["Seçilmedi", "Ön Yüz", "Arka Yüz", "Yan", "İç"])
                    hata_aciklama = st.text_area("Açıklama:")
                    if st.button("Hatayı Gönder"):
                        if hata_bolgesi != "Seçilmedi" and hata_aciklama != "":
                            yeni_hata = {
                                "Tarih/Saat": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "İstasyon": aktif_rol,
                                "İş Emri": istasyon_verisi['id'],
                                "Bölge": hata_bolgesi,
                                "Açıklama": hata_aciklama
                            }
                            db["errors"].append(yeni_hata)
                            save_db(db)
                            st.success("Yöneticiye iletildi!")
                        else:
                            st.error("Lütfen bölge seçin ve açıklama yazın.")
