import streamlit as st
import pandas as pd
import time
import json
import os
import base64
import plotly.express as px
from datetime import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Dijital Sis Kiosk", layout="wide", initial_sidebar_state="collapsed")

# --- MİNİMALİST KIOSK CSS TASARIMI ---
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; font-family: 'Helvetica Neue', sans-serif; }
    .kiosk-card { background-color: #ffffff; border-radius: 15px; padding: 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); text-align: center; margin-bottom: 20px; }
    .kiosk-title { font-size: 60px; font-weight: 800; color: #1e1e1e; margin-bottom: 10px; }
    .kiosk-subtitle { font-size: 24px; color: #666; margin-bottom: 30px; }
    </style>
""", unsafe_allow_html=True)

# --- VERİTABANI YÖNETİMİ (JSON) ---
DB_FILE = "db.json"

def load_db():
    default_db = {
        "stations": {
            "Montaj-1": {"status": "Bekliyor", "id": "", "sn": "", "target_qty": 0, "current_qty": 0, "step": 1, "work_time": 0.0, "break_time": 0.0, "last_work_start": None, "last_break_start": None, "qc_req_time": None, "break_reason": ""},
            "Montaj-2": {"status": "Bekliyor", "id": "", "sn": "", "target_qty": 0, "current_qty": 0, "step": 1, "work_time": 0.0, "break_time": 0.0, "last_work_start": None, "last_break_start": None, "qc_req_time": None, "break_reason": ""},
            "Montaj-3": {"status": "Bekliyor", "id": "", "sn": "", "target_qty": 0, "current_qty": 0, "step": 1, "work_time": 0.0, "break_time": 0.0, "last_work_start": None, "last_break_start": None, "qc_req_time": None, "break_reason": ""}
        },
        "performance": {
            "Montaj-1": {"tamamlanan_is_emri": 0, "toplam_uretilen_parca": 0},
            "Montaj-2": {"tamamlanan_is_emri": 0, "toplam_uretilen_parca": 0},
            "Montaj-3": {"tamamlanan_is_emri": 0, "toplam_uretilen_parca": 0}
        },
        "qc_logs": [], 
        "errors": []
    }
    
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(default_db, f, indent=4)
        return default_db
        
    with open(DB_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)
        
    updated = False
    for main_key in default_db:
        if main_key not in db:
            db[main_key] = default_db[main_key]
            updated = True
    for st_key in default_db["stations"]:
        if st_key not in db["stations"]:
            db["stations"][st_key] = default_db["stations"][st_key]
            updated = True
        else:
            for sub_key in default_db["stations"][st_key]:
                if sub_key not in db["stations"][st_key]:
                    db["stations"][st_key][sub_key] = default_db["stations"][st_key][sub_key]
                    updated = True
    if updated:
        save_db(db)
    return db

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

db = load_db()

# --- OTURUM YÖNETİMİ ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

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
        st.error("Hatalı giriş!")

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

# --- GİRİŞ EKRANI ---
if not st.session_state.logged_in:
    st.markdown("<br><br><h1 style='text-align: center; font-size: 70px; color: #1e1e1e;'>DİJİTAL SİS</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            user_input = st.text_input("Kullanıcı", placeholder="m1, admin, kalite1...")
            pass_input = st.text_input("Şifre", type="password")
            if st.button("SİSTEME GİR", type="primary", use_container_width=True):
                login(user_input, pass_input)

# --- SİSTEM UYGULAMASI ---
else:
    aktif_rol = st.session_state.role
    
    with st.sidebar:
        st.title(aktif_rol)
        if aktif_rol in ["Yönetici", "Kalite"]:
            canli_mod = st.checkbox("🟢 Canlı İzleme", value=True)
        elif aktif_rol in ["Montaj-1", "Montaj-2", "Montaj-3"]:
            durum_kontrol = db["stations"][aktif_rol]["status"]
            if durum_kontrol in ["Bekliyor", "Onay Bekliyor", "Tamamlandı"]:
                canli_mod = st.checkbox("🟢 Sistem Takibi", value=True)
            else:
                canli_mod = False
        st.divider()
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            logout()

    # ---------------------------------------------------------
    # YÖNETİCİ EKRANI (Aynı İşlevsellik, Düzenli Görünüm)
    # ---------------------------------------------------------
    if aktif_rol == "Yönetici":
        st.title("Yönetici Kontrol Paneli")
        
        tab1, tab2, tab3 = st.tabs(["📊 Üretim", "🚀 İş Gönder", "⚠️ Hatalar"])
        
        with tab1:
            c1, c2, c3 = st.columns(3)
            istasyonlar = ["Montaj-1", "Montaj-2", "Montaj-3"]
            
            for index, istasyon in enumerate(istasyonlar):
                with [c1, c2, c3][index]:
                    with st.container(border=True):
                        veri = db["stations"][istasyon]
                        st.markdown(f"<h3 style='text-align:center;'>{istasyon}</h3>", unsafe_allow_html=True)
                        
                        if veri["status"] == "Bekliyor":
                            st.info("Boşta")
                        elif veri["status"] == "Onay Bekliyor":
                            st.warning("Personel Bekleniyor")
                        elif veri["status"] == "Tamamlandı":
                            st.success("İş Bitti")
                        else:
                            st.metric("İlerleme", f"{veri['current_qty']} / {veri['target_qty']}")
                            st.write(f"**Durum:** {veri['status']}")
                            st.write(f"**Süre:** {format_time(get_live_work_time(istasyon))}")
                            if st.button("DURDUR", key=f"dur_{istasyon}", use_container_width=True):
                                if veri["status"] == "Çalışıyor" and veri["last_work_start"]:
                                    veri["work_time"] += time.time() - veri["last_work_start"]
                                    veri["last_work_start"] = None
                                veri["status"] = "Duraklatıldı"
                                save_db(db)
                                st.rerun()
                                
            st.divider()
            g1, g2 = st.columns(2)
            with g1:
                df_uretim = pd.DataFrame([{"İstasyon": ist, "Üretim": db["performance"][ist]["toplam_uretilen_parca"]} for ist in istasyonlar])
                st.plotly_chart(px.bar(df_uretim, x="İstasyon", y="Üretim", text="Üretim", title="Toplam Üretim"), use_container_width=True)
            with g2:
                qc_df = pd.DataFrame(db["qc_logs"])
                if not qc_df.empty:
                    ortalama_qc = qc_df.groupby("İstasyon", as_index=False)["Bekleme_Suresi_Sn"].mean().round(1)
                    st.plotly_chart(px.bar(ortalama_qc, x="İstasyon", y="Bekleme_Suresi_Sn", text="Bekleme_Suresi_Sn", title="Ort. Kalite Bekleme (Sn)"), use_container_width=True)

        with tab2:
            st.subheader("İş Emri Ata")
            c1, c2 = st.columns(2)
            with c1:
                hedef_istasyon = st.selectbox("İstasyon:", ["Montaj-1", "Montaj-2", "Montaj-3"])
                wo_id = st.text_input("İş Emri:", value="WO-2024-100")
                sn_id = st.text_input("Seri No:", value="SN-123456")
                hedef_sayi = st.number_input("Adet:", min_value=1, value=50)
                if st.button("🚀 Gönder", type="primary", use_container_width=True):
                    db["stations"][hedef_istasyon] = {
                        "status": "Onay Bekliyor", "id": wo_id, "sn": sn_id, "target_qty": hedef_sayi,
                        "current_qty": 1, "step": 1, "work_time": 0.0, "break_time": 0.0,
                        "last_work_start": None, "last_break_start": None, "qc_req_time": None, "break_reason": ""
                    }
                    save_db(db)
                    st.rerun()

        with tab3:
            if db["errors"]:
                for hata in reversed(db["errors"]):
                    with st.container(border=True):
                        st.markdown(f"**{hata['İstasyon']}** | Adım: {hata['Hatali_Adim']} | Bölge: {hata['Bölge']}")
                        st.write(hata['Açıklama'])
                        if hata.get("Foto_Base64"):
                            st.image(base64.b64decode(hata["Foto_Base64"]), width=300)

    # ---------------------------------------------------------
    # OPERATÖR EKRANI (TEK ODAK / KIOSK MODU)
    # ---------------------------------------------------------
    elif aktif_rol in ["Montaj-1", "Montaj-2", "Montaj-3"]:
        ist = db["stations"][aktif_rol]
        durum = ist["status"]
        adımlar = ["Vida Sıkma (2.5 Nm)", "Kablo Bağlantısı", "Kalite Kontrol", "Son Kapatma"]
        
        # ÜST BİLGİ BARI (Her zaman görünür ama ince)
        if durum not in ["Bekliyor", "Tamamlandı"]:
            st.markdown(f"""
                <div style='display: flex; justify-content: space-between; background-color: #f1f3f5; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
                    <strong style='font-size: 20px;'>Ürün: {ist['sn']}</strong>
                    <strong style='font-size: 20px;'>Adet: {ist['current_qty']} / {ist['target_qty']}</strong>
                    <strong style='font-size: 20px;'>⏱️ {format_time(get_live_work_time(aktif_rol))}</strong>
                </div>
            """, unsafe_allow_html=True)
        
        # ANA EKRAN DURUMLARI
        if durum == "Bekliyor":
            st.markdown("<div class='kiosk-card'><div class='kiosk-title'>☕ BEKLEMEDE</div><div class='kiosk-subtitle'>Yeni iş emri bekleniyor...</div></div>", unsafe_allow_html=True)
            
        elif durum == "Tamamlandı":
            st.markdown("<div class='kiosk-card' style='border: 3px solid #28a745;'><div class='kiosk-title' style='color:#28a745;'>✅ İŞ BİTTİ</div><div class='kiosk-subtitle'>Yöneticiye bilgi verildi.</div></div>", unsafe_allow_html=True)

        elif durum == "Onay Bekliyor":
            st.markdown(f"<div class='kiosk-card' style='border: 3px solid #ffc107;'><div class='kiosk-title'>📦 YENİ GÖREV</div><div class='kiosk-subtitle'>İş Emri: {ist['id']} | Toplam: {ist['target_qty']} Adet</div></div>", unsafe_allow_html=True)
            if st.button("🚀 GÖREVİ KABUL ET VE BAŞLA", type="primary", use_container_width=True):
                ist["status"] = "Çalışıyor"
                ist["last_work_start"] = time.time()
                save_db(db)
                st.rerun()
                
        elif durum == "Mola" or durum == "Duraklatıldı":
            mesaj = f"DURUŞTA ({ist['break_reason']})" if durum == "Mola" else "DURAKLATILDI"
            st.markdown(f"<div class='kiosk-card' style='border: 3px solid #dc3545;'><div class='kiosk-title' style='color:#dc3545;'>⏸️ {mesaj}</div></div>", unsafe_allow_html=True)
            if st.button("▶️ İŞE DEVAM ET", type="primary", use_container_width=True):
                ist["last_break_start"] = None
                ist["last_work_start"] = time.time()
                ist["status"] = "Çalışıyor"
                ist["break_reason"] = ""
                save_db(db)
                st.rerun()
                
        elif durum == "Çalışıyor":
            step = ist["step"]
            
            # --- DEVASA TEK ODAK KARTI ---
            if step <= 4:
                st.markdown(f"""
                    <div class='kiosk-card' style='border: 4px solid #007bff;'>
                        <div style='color: #007bff; font-weight: bold; font-size: 24px; margin-bottom: -10px;'>ADIM {step} / 4</div>
                        <div class='kiosk-title'>{adımlar[step-1].upper()}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Sadece mevcut adımın işlemi görünür
                c1, c2, c3 = st.columns([1, 2, 1])
                with c2:
                    if step == 3: # Kalite Adımı
                        st.error("🔒 KALİTE ONAYI GEREKİYOR")
                        qc_pass = st.text_input("Kalite Şifresi:", type="password")
                        if st.button("✔️ ONAYLA VE GEÇ", type="primary", use_container_width=True):
                            if qc_pass == USERS["kalite1"]["pass"]:
                                if ist.get("qc_req_time"):
                                    db["qc_logs"].append({
                                        "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"), "İstasyon": aktif_rol, "Bekleme_Suresi_Sn": int(time.time() - ist["qc_req_time"])
                                    })
                                ist["step"] = 4
                                ist["qc_req_time"] = None
                                save_db(db)
                                st.rerun()
                            else:
                                st.error("Şifre Hatalı!")
                    else:
                        if st.button("✅ ADIMI TAMAMLA", type="primary", use_container_width=True):
                            if step == 2: # Kaliteye geçerken sayacı başlat
                                ist["qc_req_time"] = time.time()
                            ist["step"] += 1
                            save_db(db)
                            st.rerun()
            else:
                st.markdown("<div class='kiosk-card' style='border: 4px solid #28a745;'><div class='kiosk-title' style='color:#28a745;'>🎉 PARÇA BİTTİ</div></div>", unsafe_allow_html=True)
                if st.button("📦 SIRADAKİ PARÇAYI AL", type="primary", use_container_width=True):
                    db["performance"][aktif_rol]["toplam_uretilen_parca"] += 1
                    if ist["current_qty"] < ist["target_qty"]:
                        ist["current_qty"] += 1
                        ist["step"] = 1
                    else:
                        if ist["last_work_start"]:
                            ist["work_time"] += time.time() - ist["last_work_start"]
                            ist["last_work_start"] = None
                        ist["status"] = "Tamamlandı"
                        db["performance"][aktif_rol]["tamamlanan_is_emri"] += 1
                    save_db(db)
                    st.rerun()
            
            # --- ALT MENÜ (MOLA & HATA) ---
            st.divider()
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                with st.popover("☕ DURUŞ BİLDİR", use_container_width=True):
                    mola_sebebi = st.selectbox("Sebep:", ["Yemek", "Çay", "Parça Bekleme", "Arıza", "Diğer"])
                    if st.button("Duruşa Geç"):
                        if ist["last_work_start"]:
                            ist["work_time"] += time.time() - ist["last_work_start"]
                            ist["last_work_start"] = None
                        ist["last_break_start"] = time.time()
                        ist["break_reason"] = mola_sebebi
                        ist["status"] = "Mola"
                        save_db(db)
                        st.rerun()
            with col_b2:
                with st.popover("⚠️ HATA BİLDİR", use_container_width=True):
                    hata_bolgesi = st.selectbox("Bölge:", ["Ön", "Arka", "Yan", "İç"])
                    hata_aciklama = st.text_area("Açıklama:")
                    foto = st.file_uploader("Görsel (Opsiyonel)", type=["png", "jpg"])
                    if st.button("İlet"):
                        foto_base64 = base64.b64encode(foto.read()).decode("utf-8") if foto else None
                        db["errors"].append({
                            "Tarih/Saat": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "İstasyon": aktif_rol, "İş Emri": ist['id'],
                            "Hatali_Adim": f"Adım {step}" if step<=4 else "Bitti", "Bölge": hata_bolgesi, "Açıklama": hata_aciklama, "Foto_Base64": foto_base64
                        })
                        save_db(db)
                        st.success("Hata iletildi!")

    # ---------------------------------------------------------
    # KALİTE EKRANI
    # ---------------------------------------------------------
    elif aktif_rol == "Kalite":
        st.title("Kalite Kontrol Merkezi")
        bekleyenler = [s for s, v in db["stations"].items() if v["step"] == 3 and v["status"] == "Çalışıyor"]
        if bekleyenler:
            st.error(f"🚨 ACİL ONAY BEKLEYENLER: {', '.join(bekleyenler)}")
        else:
            st.success("✅ Bekleyen onay yok.")
            
    if canli_mod:
        time.sleep(3)
        st.rerun()
