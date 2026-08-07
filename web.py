import streamlit as st
import pandas as pd
from datetime import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Dijital Sis Arayüzü", layout="wide")

# --- VERİ TABANI & OTURUM YÖNETİMİ (SESSION STATE) ---
# Gerçek bir veritabanı yerine geçici olarak session_state kullanıyoruz.
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

if 'work_order' not in st.session_state:
    # İş emri durumları: "Bekliyor", "Aktif", "Durduruldu"
    st.session_state.work_order = {"status": "Bekliyor", "id": "", "sn": ""}
    st.session_state.current_step = 1
    st.session_state.errors = []

# Kullanıcı Hesapları (3 Operatör, 1 Kalite, 1 Yönetici)
USERS = {
    "operatör1": {"pass": "1234", "role": "Operatör"},
    "operatör2": {"pass": "1234", "role": "Operatör"},
    "operatör3": {"pass": "1234", "role": "Operatör"},
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

def next_step():
    st.session_state.current_step += 1
    st.rerun()

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
                
        st.info("**Test Hesapları:**\n- Operatör: operatör1 / 1234\n- Kalite: kalite1 / kalite123\n- Yönetici: admin / admin123")

# --- SİSTEM UYGULAMASI (Giriş Yapıldıktan Sonra) ---
else:
    # Sol Menü (Çıkış İşlemi)
    with st.sidebar:
        st.write(f"👤 **Aktif Kullanıcı:** {st.session_state.username}")
        st.write(f"🏷️ **Rol:** {st.session_state.role}")
        if st.button("Çıkış Yap", use_container_width=True):
            logout()

    # ---------------------------------------------------------
    # YÖNETİCİ EKRANI
    # ---------------------------------------------------------
    if st.session_state.role == "Yönetici":
        st.title("Yönetici Kontrol Paneli")
        
        st.subheader("İş Emri Yönetimi")
        col_is_1, col_is_2 = st.columns(2)
        
        with col_is_1:
            st.write("**Yeni İş Emri Gönder**")
            wo_id = st.text_input("İş Emri Numarası:", value="WO-2024-100")
            sn_id = st.text_input("Ürün Seri Numarası:", value="SN-123456")
            
            if st.button("Üretime Başla (İş Emrini Gönder)", type="primary"):
                st.session_state.work_order = {"status": "Aktif", "id": wo_id, "sn": sn_id}
                st.session_state.current_step = 1 # Süreci sıfırla
                st.success("İş emri operatör ekranına gönderildi!")
                st.rerun()
                
        with col_is_2:
            st.write("**Mevcut İş Emri Durumu:**")
            if st.session_state.work_order["status"] == "Aktif":
                st.success(f"Aktif İş Emri: {st.session_state.work_order['id']} (SN: {st.session_state.work_order['sn']})")
                
                # Acil Durdurma Butonu
                if st.button("🚨 ACİL DURDUR (İş Emrini İptal Et)", type="primary"):
                    st.session_state.work_order["status"] = "Durduruldu"
                    st.rerun()
            elif st.session_state.work_order["status"] == "Durduruldu":
                st.error("Üretim ACİL DURDURULDU!")
            else:
                st.info("Şu an üretimde iş emri yok.")
                
        st.divider()
        st.subheader("Bildirilen Hatalar")
        if len(st.session_state.errors) > 0:
            err_df = pd.DataFrame(st.session_state.errors)
            st.dataframe(err_df, use_container_width=True)
        else:
            st.write("Şu an için kayıtlı hata bulunmamaktadır.")

    # ---------------------------------------------------------
    # OPERATÖR EKRANI
    # ---------------------------------------------------------
    elif st.session_state.role == "Operatör":
        st.title("İstasyon: Montaj 1")
        
        # Yönetici iş emri göndermediyse operatör işlem yapamaz
        if st.session_state.work_order["status"] == "Bekliyor":
            st.warning("⏳ Yöneticiden iş emri bekleniyor... Lütfen bekleyiniz.")
        
        elif st.session_state.work_order["status"] == "Durduruldu":
            st.error("🚨 BU İŞ EMRİ YÖNETİCİ TARAFINDAN ACİL OLARAK DURDURULMUŞTUR! LÜTFEN İŞLEM YAPMAYIN.")
            
        elif st.session_state.work_order["status"] == "Aktif":
            
            sol, orta, sag = st.columns([1, 2, 1])

            # SOL KOLON
            with sol:
                st.subheader("Mevcut Görev")
                st.info(f"**İşlenecek Ürün:** {st.session_state.work_order['sn']}\n\n**İş Emri:** {st.session_state.work_order['id']}")
                st.button("Mola Al", use_container_width=True)
                st.button("Parça Temini", use_container_width=True)

            # ORTA KOLON (Sıralı Adımlar)
            with orta:
                st.subheader("Montaj Adımları")
                step = st.session_state.current_step
                
                # ADIM 1
                ad1_checked = (step > 1)
                ad1 = st.checkbox("Adım 1: Vida Sıkma (2.5 Nm)", value=ad1_checked, disabled=(step != 1))
                if ad1 and step == 1:
                    next_step()
                    
                # ADIM 2
                ad2_checked = (step > 2)
                ad2 = st.checkbox("Adım 2: Kablo Bağlantısı", value=ad2_checked, disabled=(step != 2))
                if ad2 and step == 2:
                    next_step()
                    
                # ADIM 3 (KALİTE ONAYI - ŞİFRELİ)
                ad3_checked = (step > 3)
                if step == 3:
                    st.error("🔍 Adım 3: Zorunlu Kalite Kontrolü")
                    st.write("Devam etmek için kalite yetkilisinin şifresini girmesi gerekmektedir.")
                    qc_pass = st.text_input("Kalite Yetkilisi Şifresi:", type="password")
                    if st.button("Kalite Onayını Ver"):
                        # Kalite şifresini veritabanından(sözlükten) kontrol et
                        if qc_pass == USERS["kalite1"]["pass"]:
                            st.success("Kalite onayı alındı!")
                            next_step()
                        else:
                            st.error("Hatalı kalite şifresi!")
                elif step > 3:
                    st.checkbox("Adım 3: Zorunlu Kalite Kontrolü", value=True, disabled=True)
                else:
                    st.checkbox("Adım 3: Zorunlu Kalite Kontrolü (Kilitli)", value=False, disabled=True)
                    
                # ADIM 4
                ad4_checked = (step > 4)
                ad4 = st.checkbox("Adım 4: Son Montaj", value=ad4_checked, disabled=(step != 4))
                if ad4 and step == 4:
                    st.success("Tüm adımlar tamamlandı!")
                    st.session_state.current_step = 5 # Bitirme konumu
                    
                if step == 5:
                    if st.button("İşi Bitir ve Yeni İşe Geç", type="primary", use_container_width=True):
                        st.session_state.work_order["status"] = "Bekliyor"
                        st.session_state.current_step = 1
                        st.rerun()

            # SAĞ KOLON (Hata Belirt)
            with sag:
                st.subheader("İstasyon Bildirimleri")
                
                with st.expander("⚠️ HATA BELİRT", expanded=False):
                    hata_aciklama = st.text_area("Hatanın Tanımı:")
                    
                    # Hata Bölgesi Seçimi
                    st.write("**Hata Parçanın Neresinde?**")
                    hata_bolgesi = st.radio("Bölge Seçiniz:", ["Seçilmedi", "Ön Yüzey", "Arka Yüzey", "Sağ Kenar", "Sol Kenar", "İç Kısım"])
                    
                    if st.button("Hatayı Yöneticiye Gönder"):
                        if hata_bolgesi != "Seçilmedi" and hata_aciklama != "":
                            yeni_hata = {
                                "Zaman": datetime.now().strftime("%H:%M:%S"),
                                "Personel": st.session_state.username,
                                "Bölge": hata_bolgesi,
                                "Açıklama": hata_aciklama
                            }
                            st.session_state.errors.append(yeni_hata)
                            st.success("Hata başarıyla yöneticiye iletildi!")
                        else:
                            st.error("Lütfen hata bölgesini seçin ve açıklama yazın.")

    # ---------------------------------------------------------
    # KALİTE EKRANI (İsteğe Bağlı Görüntüleme İçin)
    # ---------------------------------------------------------
    elif st.session_state.role == "Kalite":
        st.title("Kalite Kontrol Paneli")
        st.info("Bu terminal sadece istasyonlardaki genel hataları görmek içindir. Adım onayları operatörlerin ekranlarından 'kalite123' şifresi girilerek yapılmalıdır.")
        st.write("**Son Hata Kayıtları:**")
        if len(st.session_state.errors) > 0:
            st.dataframe(pd.DataFrame(st.session_state.errors), use_container_width=True)
        else:
            st.write("Sistemde aktif hata kaydı yok.")
