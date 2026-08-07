import streamlit as st
import pandas as pd
import time
from datetime import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Dijital Sis Arayüzü", layout="wide")

# --- VERİ TABANI & OTURUM YÖNETİMİ (SESSION STATE) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

# İş emri ve zamanlayıcı değişkenleri
if 'work_order' not in st.session_state:
    st.session_state.work_order = {
        "status": "Bekliyor", # Bekliyor, Çalışıyor, Duraklatıldı, Mola
        "id": "", 
        "sn": "",
        "target_qty": 0,
        "current_qty": 0
    }
    st.session_state.current_step = 1
    st.session_state.errors = []
    
    # Süre tutma değişkenleri (Saniye cinsinden)
    st.session_state.work_time = 0.0
    st.session_state.break_time = 0.0
    st.session_state.last_work_start = None
    st.session_state.last_break_start = None
    st.session_state.show_break_modal = False

# Kullanıcı Hesapları
USERS = {
    "operatör1": {"pass": "1234", "role": "Operatör"},
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

def next_step():
    st.session_state.current_step += 1
    st.rerun()

def format_time(seconds):
    # Saniyeyi SS:DD:SS formatına çevirir
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def get_live_work_time():
    t = st.session_state.work_time
    if st.session_state.work_order["status"] == "Çalışıyor" and st.session_state.last_work_start:
        t += time.time() - st.session_state.last_work_start
    return t

def get_live_break_time():
    t = st.session_state.break_time
    if st.session_state.work_order["status"] == "Mola" and st.session_state.last_break_start:
        t += time.time() - st.session_state.last_break_start
    return t

def stop_work_timer():
    if st.session_state.work_order["status"] == "Çalışıyor" and st.session_state.last_work_start:
        st.session_state.work_time += time.time() - st.session_state.last_work_start
        st.session_state.last_work_start = None

def start_work_timer():
    st.session_state.last_work_start = time.time()
    st.session_state.work_order["status"] = "Çalışıyor"

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
        st.info("**Test Hesapları:**\n- Operatör: operatör1 / 1234\n- Yönetici: admin / admin123")

# --- SİSTEM UYGULAMASI ---
else:
    with st.sidebar:
        st.write(f"👤 **Kullanıcı:** {st.session_state.username}")
        st.write(f"🏷️ **Rol:** {st.session_state.role}")
        st.write(f"⏱️ **Çalışma:** {format_time(get_live_work_time())}")
        st.write(f"☕ **Mola:** {format_time(get_live_break_time())}")
        if st.button("Sayfayı Yenile (Süreleri Güncelle)"):
            st.rerun()
        if st.button("Çıkış Yap", use_container_width=True):
            logout()

    # ---------------------------------------------------------
    # YÖNETİCİ EKRANI
    # ---------------------------------------------------------
    if st.session_state.role == "Yönetici":
        st.title("Yönetici Kontrol Paneli")
        
        col_is_1, col_is_2 = st.columns(2)
        with col_is_1:
            st.subheader("Yeni İş Emri Gönder")
            wo_id = st.text_input("İş Emri Numarası:", value="WO-2024-100")
            sn_id = st.text_input("Ürün Seri Numarası (Başlangıç):", value="SN-123456")
            hedef_sayi = st.number_input("Üretilecek Adet (Hedef):", min_value=1, value=50)
            
            if st.button("Üretime Başla (İş Emrini Gönder)", type="primary"):
                st.session_state.work_order = {
                    "status": "Çalışıyor", 
                    "id": wo_id, 
                    "sn": sn_id,
                    "target_qty": hedef_sayi,
                    "current_qty": 1
                }
                st.session_state.current_step = 1
                st.session_state.work_time = 0.0
                st.session_state.break_time = 0.0
                start_work_timer()
                st.success("İş emri operatöre gönderildi ve süre başladı!")
                st.rerun()
                
        with col_is_2:
            st.subheader("Mevcut Durum İzleme")
            durum = st.session_state.work_order["status"]
            
            if durum == "Bekliyor":
                st.warning("Şu an üretimde iş emri yok.")
            else:
                if durum == "Çalışıyor":
                    st.success(f"Durum: {durum}")
                elif durum == "Mola" or durum == "Duraklatıldı":
                    st.error(f"Durum: {durum}")
                
                st.metric("Üretim İlerlemesi", f"{st.session_state.work_order['current_qty']} / {st.session_state.work_order['target_qty']}")
                st.write(f"**Aktif İş Emri:** {st.session_state.work_order['id']} (SN: {st.session_state.work_order['sn']})")
                st.write(f"**Çalışma Süresi:** {format_time(get_live_work_time())}")
                st.write(f"**Mola Süresi:** {format_time(get_live_break_time())}")
                
                if st.button("🚨 ACİL DURDUR", type="primary"):
                    stop_work_timer()
                    if durum == "Mola" and st.session_state.last_break_start:
                        st.session_state.break_time += time.time() - st.session_state.last_break_start
                        st.session_state.last_break_start = None
                    st.session_state.work_order["status"] = "Duraklatıldı"
                    st.rerun()

    # ---------------------------------------------------------
    # OPERATÖR EKRANI
    # ---------------------------------------------------------
    elif st.session_state.role == "Operatör":
        durum = st.session_state.work_order["status"]
        
        # Dinamik Renk ve Başlık
        if durum == "Bekliyor":
            st.warning("⏳ Yöneticiden yeni iş emri bekleniyor...")
        else:
            if durum == "Çalışıyor":
                st.success(f"🟢 İSTASYON AKTİF - Üretim No: {st.session_state.work_order['current_qty']} / {st.session_state.work_order['target_qty']}")
            else:
                st.error(f"🔴 İSTASYON DURDU - Durum: {durum} - Üretim No: {st.session_state.work_order['current_qty']} / {st.session_state.work_order['target_qty']}")
            
            sol, orta, sag = st.columns([1, 2, 1])

            # SOL KOLON (Kontrol)
            with sol:
                st.subheader("Mevcut Görev")
                st.info(f"**Ürün:** {st.session_state.work_order['sn']}\n\n**İş Emri:** {st.session_state.work_order['id']}")
                
                if durum == "Duraklatıldı":
                    if st.button("▶️ İşe Devam Et", use_container_width=True):
                        start_work_timer()
                        st.rerun()
                elif durum == "Çalışıyor":
                    if st.button("⏸️ İşi Duraklat", use_container_width=True):
                        stop_work_timer()
                        st.session_state.work_order["status"] = "Duraklatıldı"
                        st.rerun()

                # Mola Pop-up Simülasyonu
                st.divider()
                if st.button("☕ Mola Menüsü", use_container_width=True):
                    st.session_state.show_break_modal = not st.session_state.show_break_modal
                    
                if st.session_state.show_break_modal:
                    with st.expander("Mola İşlemleri", expanded=True):
                        if durum != "Mola":
                            if st.button("Molaya Çık", type="primary"):
                                stop_work_timer()
                                st.session_state.last_break_start = time.time()
                                st.session_state.work_order["status"] = "Mola"
                                st.session_state.show_break_modal = False
                                st.rerun()
                        else:
                            if st.button("Moladan Dön", type="primary"):
                                if st.session_state.last_break_start:
                                    st.session_state.break_time += time.time() - st.session_state.last_break_start
                                    st.session_state.last_break_start = None
                                start_work_timer()
                                st.session_state.show_break_modal = False
                                st.rerun()

            # ORTA KOLON (Montaj Adımları)
            with orta:
                st.subheader("Montaj Adımları")
                
                if durum == "Çalışıyor":
                    step = st.session_state.current_step
                    
                    ad1 = st.checkbox("Adım 1: Vida Sıkma (2.5 Nm)", value=(step > 1), disabled=(step != 1))
                    if ad1 and step == 1: next_step()
                        
                    ad2 = st.checkbox("Adım 2: Kablo Bağlantısı", value=(step > 2), disabled=(step != 2))
                    if ad2 and step == 2: next_step()
                        
                    ad3 = st.checkbox("Adım 3: Son Kontrol", value=(step > 3), disabled=(step != 3))
                    if ad3 and step == 3: next_step()
                        
                    if step > 3:
                        st.success("Bu parçanın montajı tamamlandı!")
                        if st.button("Sıradaki Parçaya Geç (Kaydet)", type="primary"):
                            # Hedefe ulaşıldı mı?
                            if st.session_state.work_order["current_qty"] < st.session_state.work_order["target_qty"]:
                                st.session_state.work_order["current_qty"] += 1
                                st.session_state.current_step = 1
                            else:
                                stop_work_timer()
                                st.session_state.work_order["status"] = "Bekliyor"
                                st.success("Hedef üretim sayısına ulaşıldı! İş emri tamamlandı.")
                            st.rerun()
                else:
                    st.warning("Adımları görebilmek için istasyonun 'Çalışıyor' durumunda olması gerekir.")

            # SAĞ KOLON (Hata Belirt)
            with sag:
                st.subheader("Hata Bildirimi")
                with st.expander("⚠️ Hata Belirt", expanded=False):
                    hata_aciklama = st.text_area("Açıklama:")
                    hata_bolgesi = st.radio("Bölge:", ["Ön", "Arka", "Yan", "İç"])
                    if st.button("Gönder"):
                        st.success("Hata iletildi!")
