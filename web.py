import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import time
import json
import os
import base64
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

db = load_db()

# --- OTURUM YÖNETİMİ ---
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

# --- CANLI SAYAÇ HTML/JS ---
def render_live_timer(label, seconds, is_active):
    color = "#28a745" if is_active else "#6c757d"
    status_text = "(Aktif)" if is_active else "(Durdu)"
    
    html_code = f"""
    <div style="font-family: sans-serif; background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 5px solid {color}; margin-bottom: 10px;">
        <span style="font-size: 14px; color: #555;">{label} {status_text}</span><br>
        <span id="timer_{label.replace(' ','')}" style="font-size: 20px; font-weight: bold; color: {color};"></span>
    </div>
    <script>
    let secs_{label.replace(' ','')} = {int(seconds)};
    let isActive = {'true' if is_active else 'false'};
    
    function formatTime(s) {{
        let h = Math.floor(s / 3600).toString().padStart(2, '0');
        let m = Math.floor((s % 3600) / 60).toString().padStart(2, '0');
        let sec = Math.floor(s % 60).toString().padStart(2, '0');
        return h + ':' + m + ':' + sec;
    }}
    
    document.getElementById('timer_{label.replace(' ','')}').innerText = formatTime(secs_{label.replace(' ','')});
    
    if (isActive) {{
        setInterval(function() {{
            secs_{label.replace(' ','')}++;
            document.getElementById('timer_{label.replace(' ','')}').innerText = formatTime(secs_{label.replace(' ','')});
        }}, 1000);
    }}
    </script>
    """
    components.html(html_code, height=80)

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

# --- SİSTEM UYGULAMASI ---
else:
    aktif_rol = st.session_state.role
    
    with st.sidebar:
        st.write(f"👤 **Hesap:** {st.session_state.username}")
        st.write(f"🏷️ **Birim:** {aktif_rol}")
        
        if aktif_rol in ["Montaj-1", "Montaj-2", "Montaj-3"]:
            istasyon_verisi = db["stations"][aktif_rol]
            render_live_timer("Çalışma Süresi", get_live_work_time(aktif_rol), istasyon_verisi["status"] == "Çalışıyor")
            render_live_timer("Mola Süresi", get_live_break_time(aktif_rol), istasyon_verisi["status"] == "Mola")
            
        if st.button("🔄 Verileri Güncelle", use_container_width=True):
            db = load_db()
            st.rerun()
            
        st.divider()
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            logout()

    # ---------------------------------------------------------
    # YÖNETİCİ EKRANI
    # ---------------------------------------------------------
    if aktif_rol == "Yönetici":
        st.title("Yönetici Kontrol Paneli")
        
        tab1, tab2, tab3 = st.tabs(["Canlı İzleme & Performans", "İş Emri Gönder", "Hata Kayıtları"])
        
        with tab1:
            st.subheader("İstasyonların Canlı Durumu")
            c1, c2, c3 = st.columns(3)
            istasyonlar = ["Montaj-1", "Montaj-2", "Montaj-3"]
            
            for index, istasyon in enumerate(istasyonlar):
                with [c1, c2, c3][index]:
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
                        
                        if st.button(f"🚨 {istasyon} DURDUR", key=f"dur_{istasyon}"):
                            if veri["status"] == "Çalışıyor" and veri["last_work_start"]:
                                veri["work_time"] += time.time() - veri["last_work_start"]
                                veri["last_work_start"] = None
                            if veri["status"] == "Mola" and veri["last_break_start"]:
                                veri["break_time"] += time.time() - veri["last_break_start"]
                                veri["last_break_start"] = None
                            veri["status"] = "Duraklatıldı"
                            save_db(db)
                            st.rerun()
                            
            st.divider()
            st.subheader("📊 Performans ve Darboğaz Analizi")
            perf_data = []
            for istasyon in istasyonlar:
                veri = db["stations"][istasyon]
                gecmis_veri = db["performance"][istasyon]
                
                aktif_sure = get_live_work_time(istasyon)
                aktif_adet = veri['current_qty']
                ort_sure = aktif_sure / aktif_adet if aktif_adet > 0 else 0
                
                perf_data.append({
                    "İstasyon": istasyon,
                    "Aktif İş Emri Adedi": f"{aktif_adet} / {veri['target_qty']}",
                    "Ortalama Süre / Parça": format_time(ort_sure),
                    "Toplam Tamamlanan İş Emri": gecmis_veri["tamamlanan_is_emri"],
                    "Toplam Üretilen Parça": gecmis_veri["toplam_uretilen_parca"]
                })
            
            st.dataframe(pd.DataFrame(perf_data), use_container_width=True)

        with tab2:
            st.subheader("Yeni İş Emri Gönder")
            col_is_1, col_is_2 = st.columns(2)
            with col_is_1:
                hedef_istasyon = st.selectbox("Gönderilecek İstasyon:", ["Montaj-1", "Montaj-2", "Montaj-3"])
                wo_id = st.text_input("İş Emri Numarası:", value="WO-2024-100")
                sn_id = st.text_input("Ürün Seri Numarası (Başlangıç):", value="SN-123456")
                hedef_sayi = st.number_input("Üretilecek Adet (Hedef):", min_value=1, value=50)
                
                if st.button("🚀 Üretime Başla (İş Emrini Gönder)", type="primary"):
                    db["stations"][hedef_istasyon] = {
                        "status": "Çalışıyor", "id": wo_id, "sn": sn_id, "target_qty": hedef_sayi,
                        "current_qty": 1, "step": 1, "work_time": 0.0, "break_time": 0.0,
                        "last_work_start": time.time(), "last_break_start": None
                    }
                    save_db(db)
                    st.success(f"İş emri {hedef_istasyon} istasyonuna gönderildi!")
                    st.rerun()

        with tab3:
            st.subheader("Bildirilen Hatalar ve Fotoğraflar")
            if len(db["errors"]) > 0:
                for hata in reversed(db["errors"]):
                    with st.expander(f"⚠️ {hata['Tarih/Saat']} - {hata['İstasyon']} (İş Emri: {hata['İş Emri']})"):
                        st.write(f"**Montaj Dönemi:** {hata['Montaj_Donemi']}")
                        st.write(f"**Hatalı Adım:** {hata['Hatali_Adim']}")
                        st.write(f"**Bölge:** {hata['Bölge']}")
                        if hata['Onceden_Hatali']:
                            st.error("🚨 Bu parça istasyona önceden hatalı gelmiş!")
                        st.write(f"**Açıklama:** {hata['Açıklama']}")
                        if hata.get("Foto_Base64"):
                            try:
                                img_data = base64.b64decode(hata["Foto_Base64"])
                                st.image(img_data, caption="Yüklenen Hata Görseli", width=400)
                            except:
                                st.warning("Görsel yüklenemedi.")
            else:
                st.write("Kayıtlı hata bulunmuyor.")

    # ---------------------------------------------------------
    # KALİTE EKRANI
    # ---------------------------------------------------------
    elif aktif_rol == "Kalite":
        st.title("Kalite Kontrol Paneli")
        
        # ONAY BEKLEYENLERİ BUL
        bekleyenler = [s for s, v in db["stations"].items() if v["step"] == 3 and v["status"] == "Çalışıyor"]
        if bekleyenler:
            st.error(f"🚨 DİKKAT: Kalite Onayı Bekleyen İstasyon(lar) Var: **{', '.join(bekleyenler)}**")
        else:
            st.success("✅ Şu an kalite onayı bekleyen aktif istasyon bulunmuyor.")
            
        st.divider()
        st.subheader("Hata Bildirimleri")
        if len(db["errors"]) > 0:
            for hata in reversed(db["errors"]):
                with st.expander(f"⚠️ {hata['Tarih/Saat']} - {hata['İstasyon']}"):
                    st.write(f"**Adım:** {hata['Hatali_Adim']} | **Bölge:** {hata['Bölge']}")
                    st.write(f"**Açıklama:** {hata['Açıklama']}")
                    if hata['Onceden_Hatali']: st.error("🚨 Parça önceden hatalı.")
                    if hata.get("Foto_Base64"):
                        st.image(base64.b64decode(hata["Foto_Base64"]), width=300)
        else:
            st.write("Kayıtlı hata bulunmuyor.")

    # ---------------------------------------------------------
    # İSTASYON EKRANI
    # ---------------------------------------------------------
    elif aktif_rol in ["Montaj-1", "Montaj-2", "Montaj-3"]:
        istasyon_verisi = db["stations"][aktif_rol]
        durum = istasyon_verisi["status"]
        
        if durum == "Bekliyor":
            st.warning("⏳ Yöneticiden yeni iş emri bekleniyor...")
        else:
            if durum == "Çalışıyor":
                st.success(f"🟢 {aktif_rol} AKTİF - Üretim No: {istasyon_verisi['current_qty']} / {istasyon_verisi['target_qty']}")
            else:
                st.error(f"🔴 {aktif_rol} DURDU - Durum: {durum} - Üretim No: {istasyon_verisi['current_qty']} / {istasyon_verisi['target_qty']}")
            
            sol, orta, sag = st.columns([1.2, 2, 1.5])

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
                                if istasyon_verisi["status"] == "Çalışıyor" and istasyon_verisi["last_work_start"]:
                                    istasyon_verisi["work_time"] += time.time() - istasyon_verisi["last_work_start"]
                                    istasyon_verisi["last_work_start"] = None
                                istasyon_verisi["last_break_start"] = time.time()
                                istasyon_verisi["status"] = "Mola"
                                st.session_state.show_break_modal = False
                                save_db(db)
                                st.rerun()
                        else:
                            if st.button("Moladan Dön", type="primary"):
                                if istasyon_verisi["last_break_start"]:
                                    istasyon_verisi["break_time"] += time.time() - istasyon_verisi["last_break_start"]
                                    istasyon_verisi["last_break_start"] = None
                                istasyon_verisi["last_work_start"] = time.time()
                                istasyon_verisi["status"] = "Çalışıyor"
                                st.session_state.show_break_modal = False
                                save_db(db)
                                st.rerun()

            with orta:
                st.subheader("Montaj Adımları")
                if durum == "Çalışıyor":
                    step = istasyon_verisi["step"]
                    
                    if st.checkbox("Adım 1: Vida Sıkma (2.5 Nm)", value=(step > 1), disabled=(step != 1)) and step == 1:
                        istasyon_verisi["step"] = 2
                        save_db(db)
                        st.rerun()
                        
                    if st.checkbox("Adım 2: Kablo Bağlantısı", value=(step > 2), disabled=(step != 2)) and step == 2:
                        istasyon_verisi["step"] = 3
                        save_db(db)
                        st.rerun()
                    
                    if step == 3:
                        st.error("🔍 Adım 3: Zorunlu Kalite Kontrolü\n\n(Kalite birimine bildirim gönderildi)")
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
                        
                    if st.checkbox("Adım 4: Son Kontrol", value=(step > 4), disabled=(step != 4)) and step == 4:
                        istasyon_verisi["step"] = 5
                        save_db(db)
                        st.rerun()
                        
                    if step > 4:
                        st.success("Bu parçanın tüm adımları tamamlandı!")
                        if st.button("✅ Sıradaki Parçaya Geç", type="primary", use_container_width=True):
                            db["performance"][aktif_rol]["toplam_uretilen_parca"] += 1
                            if istasyon_verisi["current_qty"] < istasyon_verisi["target_qty"]:
                                istasyon_verisi["current_qty"] += 1
                                istasyon_verisi["step"] = 1
                            else:
                                if istasyon_verisi["last_work_start"]:
                                    istasyon_verisi["work_time"] += time.time() - istasyon_verisi["last_work_start"]
                                    istasyon_verisi["last_work_start"] = None
                                istasyon_verisi["status"] = "Bekliyor"
                                db["performance"][aktif_rol]["tamamlanan_is_emri"] += 1
                            save_db(db)
                            st.rerun()
                else:
                    st.warning("Adımları görebilmek için istasyonun 'Çalışıyor' durumunda olması gerekir.")

            with sag:
                st.subheader("Bildirim")
                with st.expander("⚠️ Detaylı Hata Belirt", expanded=False):
                    
                    hata_donemi = st.radio("Hata Hangi Montajda Oldu?", ["Mevcut Montaj (Şu anki)", "Önceki Montaj (Geçmiş Parça)"])
                    hatali_adim = st.selectbox("Hangi Adımda Hata Var?", ["Bilinmiyor", "Adım 1", "Adım 2", "Adım 3", "Adım 4"])
                    onceden_hatali = st.checkbox("Parça buraya gelmeden önce zaten hatalıydı")
                    
                    st.write("**Bölge Seçiniz:**")
                    hata_bolgesi = st.selectbox("Nerede:", ["Seçilmedi", "Ön Yüz", "Arka Yüz", "Yan", "İç"])
                    hata_aciklama = st.text_area("Açıklama:")
                    
                    foto_dosya = st.file_uploader("Fotoğraf Yükle (İsteğe Bağlı)", type=["png", "jpg", "jpeg"])
                    
                    if st.button("Hatayı Gönder", type="primary"):
                        if hata_bolgesi != "Seçilmedi" and hata_aciklama != "":
                            foto_base64 = None
                            if foto_dosya is not None:
                                foto_base64 = base64.b64encode(foto_dosya.read()).decode("utf-8")
                                
                            yeni_hata = {
                                "Tarih/Saat": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "İstasyon": aktif_rol,
                                "İş Emri": istasyon_verisi['id'],
                                "Montaj_Donemi": hata_donemi,
                                "Hatali_Adim": hatali_adim,
                                "Onceden_Hatali": onceden_hatali,
                                "Bölge": hata_bolgesi,
                                "Açıklama": hata_aciklama,
                                "Foto_Base64": foto_base64
                            }
                            db["errors"].append(yeni_hata)
                            save_db(db)
                            st.success("Hata ve görsel başarıyla iletildi!")
                        else:
                            st.error("Lütfen bölge seçin ve açıklama yazın.")
