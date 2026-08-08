import streamlit as st
import pandas as pd
import time
import json
import os
import base64
import plotly.express as px
from datetime import datetime
import copy

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Dijital Sis - Kiosk & Dashboard", layout="wide", initial_sidebar_state="collapsed")

# --- MİNİMALİST KIOSK CSS TASARIMI ---
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; font-family: 'Helvetica Neue', sans-serif; }
    .kiosk-card { background-color: #ffffff; border-radius: 15px; padding: 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); text-align: center; margin-bottom: 20px; }
    .kiosk-title { font-size: 55px; font-weight: 800; color: #1e1e1e; margin-bottom: 10px; }
    .kiosk-subtitle { font-size: 22px; color: #666; margin-bottom: 30px; }
    .step-indicator { color: #007bff; font-weight: bold; font-size: 24px; margin-bottom: -10px; }
    .urgent-alert { background-color: #dc3545; color: white; padding: 50px; border-radius: 20px; text-align: center; border: 5px solid #8b0000; margin-top: 50px;}
    .urgent-title { font-size: 80px; font-weight: 900; margin-bottom: 20px; line-height: 1.1;}
    </style>
""", unsafe_allow_html=True)

# --- VERİTABANI YÖNETİMİ (JSON) ---
DB_FILE = "db.json"

def get_empty_station():
    return {
        "status": "Bekliyor", "id": "", "sn": "", "target_qty": 0, "current_qty": 0, "step": 1, 
        "work_time": 0.0, "break_time": 0.0, "qc_wait_time": 0.0, 
        "last_work_start": None, "last_break_start": None, "qc_req_time": None, 
        "break_reason": "", "urgent_alert": False, "suspended_job": None
    }

def load_db():
    default_db = {
        "stations": {
            "Montaj-1": get_empty_station(),
            "Montaj-2": get_empty_station(),
            "Montaj-3": get_empty_station()
        },
        "performance": {
            "Montaj-1": {"tamamlanan_is_emri": 0, "toplam_uretilen_parca": 0},
            "Montaj-2": {"tamamlanan_is_emri": 0, "toplam_uretilen_parca": 0},
            "Montaj-3": {"tamamlanan_is_emri": 0, "toplam_uretilen_parca": 0}
        },
        "completed_jobs": [], 
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

def stop_timers(istasyon_verisi):
    if istasyon_verisi["status"] == "Çalışıyor" and istasyon_verisi["last_work_start"]:
        istasyon_verisi["work_time"] += time.time() - istasyon_verisi["last_work_start"]
        istasyon_verisi["last_work_start"] = None
    if istasyon_verisi["status"] == "Mola" and istasyon_verisi["last_break_start"]:
        istasyon_verisi["break_time"] += time.time() - istasyon_verisi["last_break_start"]
        istasyon_verisi["last_break_start"] = None
    if istasyon_verisi["qc_req_time"]:
        istasyon_verisi["qc_wait_time"] += time.time() - istasyon_verisi["qc_req_time"]
        istasyon_verisi["qc_req_time"] = None

# --- GİRİŞ EKRANI ---
if not st.session_state.logged_in:
    st.markdown("<br><br><h1 style='text-align: center; font-size: 70px; color: #1e1e1e;'>DİJİTAL SİS</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            user_input = st.text_input("Kullanıcı Adı", placeholder="m1, admin, kalite1...")
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
            urgent_kontrol = db["stations"][aktif_rol]["urgent_alert"]
            if (durum_kontrol in ["Bekliyor", "Onay Bekliyor", "Tamamlandı"] or durum_kontrol == "Acil Bekliyor") and not urgent_kontrol:
                canli_mod = st.checkbox("🟢 Sistem Takibi", value=True)
            else:
                canli_mod = False
        st.divider()
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            logout()

    # ---------------------------------------------------------
    # YÖNETİCİ EKRANI
    # ---------------------------------------------------------
    if aktif_rol == "Yönetici":
        st.title("Yönetici Kontrol Paneli")
        
        tamamlanan_istasyonlar = [ist for ist, veri in db["stations"].items() if veri["status"] == "Tamamlandı"]
        if tamamlanan_istasyonlar:
            st.success(f"🎉 **{', '.join(tamamlanan_istasyonlar)}** iş emrini tamamladı! Yeni iş emri bekliyorlar.")

        tab1, tab2, tab3 = st.tabs(["📊 Canlı İzleme & Performans", "🚀 İş Emri Ata", "⚠️ Hata Kayıtları"])
        
        with tab1:
            st.subheader("İzlenebilirlik ve Canlı Takip Tablosu")
            
            # Detaylı Tablo Hazırlığı
            tablo_verisi = []
            for ist in ["Montaj-1", "Montaj-2", "Montaj-3"]:
                veri = db["stations"][ist]
                w_time = get_live_work_time(ist)
                b_time = veri["break_time"]
                q_time = veri["qc_wait_time"]
                if veri["status"] == "Mola" and veri["last_break_start"]:
                    b_time += time.time() - veri["last_break_start"]
                if veri.get("qc_req_time"):
                    q_time += time.time() - veri["qc_req_time"]
                    
                tablo_verisi.append({
                    "İstasyon": ist,
                    "Durum": veri["status"],
                    "Aktif İş Emri": veri["id"] if veri["id"] else "-",
                    "Üretim Adedi": f"{veri['current_qty']}/{veri['target_qty']}",
                    "Çalışma (Dk)": round(w_time / 60, 1),
                    "Mola/Duruş (Dk)": round(b_time / 60, 1),
                    "Kalite Bekleme (Dk)": round(q_time / 60, 1),
                    "Günlük Tamamlanan İş": db["performance"][ist]["tamamlanan_is_emri"]
                })
            
            st.dataframe(pd.DataFrame(tablo_verisi), use_container_width=True)
            st.divider()
            
            st.subheader("⏱️ İstasyon Süre Dağılımları (Pasta Grafikler)")
            pie_c1, pie_c2, pie_c3 = st.columns(3)
            
            for index, ist in enumerate(["Montaj-1", "Montaj-2", "Montaj-3"]):
                with [pie_c1, pie_c2, pie_c3][index]:
                    v = tablo_verisi[index]
                    total_time = v["Çalışma (Dk)"] + v["Mola/Duruş (Dk)"] + v["Kalite Bekleme (Dk)"]
                    if total_time > 0:
                        df_pie = pd.DataFrame({
                            "Kategori": ["Çalışma", "Mola/Duruş", "Kalite Bekleme"],
                            "Süre": [v["Çalışma (Dk)"], v["Mola/Duruş (Dk)"], v["Kalite Bekleme (Dk)"]]
                        })
                        fig = px.pie(df_pie, values="Süre", names="Kategori", title=f"{ist} Süre Dağılımı", hole=0.3,
                                     color="Kategori", color_discrete_map={"Çalışma": "#28a745", "Mola/Duruş": "#dc3545", "Kalite Bekleme": "#ffc107"})
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info(f"{ist} için henüz süre kaydı yok.")
                        
            st.divider()
            st.subheader("İstasyonları Anlık Durdurma")
            btn_c1, btn_c2, btn_c3 = st.columns(3)
            for index, istasyon in enumerate(["Montaj-1", "Montaj-2", "Montaj-3"]):
                with [btn_c1, btn_c2, btn_c3][index]:
                    if st.button(f"🚨 {istasyon} DURDUR", key=f"dur_{istasyon}", use_container_width=True):
                        stop_timers(db["stations"][istasyon])
                        db["stations"][istasyon]["status"] = "Duraklatıldı"
                        save_db(db)
                        st.rerun()

        with tab2:
            st.subheader("Yeni İş Emri Gönder")
            c1, c2 = st.columns(2)
            with c1:
                hedef_istasyon = st.selectbox("İstasyon:", ["Montaj-1", "Montaj-2", "Montaj-3"])
                wo_id = st.text_input("İş Emri Numarası:", value="WO-2024-100")
                sn_id = st.text_input("Seri No Başlangıcı:", value="SN-123456")
                hedef_sayi = st.number_input("Hedef Adet:", min_value=1, value=50)
                
                st.markdown("---")
                is_urgent = st.checkbox("🚨 ACİL İŞ EMRİ (Mevcut işi dondurur ve operatör ekranını kilitler)")
                
                if st.button("🚀 İş Emrini Gönder", type="primary", use_container_width=True):
                    hedef_veri = db["stations"][hedef_istasyon]
                    
                    if is_urgent:
                        # Eğer içeride çalışan bir iş varsa onu dondur (suspended_job'a at)
                        if hedef_veri["id"] != "":
                            stop_timers(hedef_veri)
                            hedef_veri["suspended_job"] = copy.deepcopy({
                                "id": hedef_veri["id"], "sn": hedef_veri["sn"], "target_qty": hedef_veri["target_qty"],
                                "current_qty": hedef_veri["current_qty"], "step": hedef_veri["step"], 
                                "work_time": hedef_veri["work_time"], "break_time": hedef_veri["break_time"], 
                                "qc_wait_time": hedef_veri["qc_wait_time"]
                            })
                            
                        hedef_veri["id"] = wo_id
                        hedef_veri["sn"] = sn_id
                        hedef_veri["target_qty"] = hedef_sayi
                        hedef_veri["current_qty"] = 1
                        hedef_veri["step"] = 1
                        hedef_veri["work_time"] = 0.0
                        hedef_veri["break_time"] = 0.0
                        hedef_veri["qc_wait_time"] = 0.0
                        hedef_veri["urgent_alert"] = True
                        hedef_veri["status"] = "Acil Bekliyor"
                        st.success(f"Acil İş Emri {hedef_istasyon} istasyonuna gönderildi!")
                    else:
                        db["stations"][hedef_istasyon] = {
                            "status": "Onay Bekliyor", "id": wo_id, "sn": sn_id, "target_qty": hedef_sayi,
                            "current_qty": 1, "step": 1, "work_time": 0.0, "break_time": 0.0, "qc_wait_time": 0.0,
                            "last_work_start": None, "last_break_start": None, "qc_req_time": None, "break_reason": "",
                            "urgent_alert": False, "suspended_job": None
                        }
                        st.success(f"Normal İş Emri {hedef_istasyon} istasyonuna gönderildi.")
                    
                    save_db(db)
                    st.rerun()

        with tab3:
            st.subheader("Tüm Hata Bildirimleri")
            if db["errors"]:
                for hata in reversed(db["errors"]):
                    with st.container(border=True):
                        st.markdown(f"**{hata['İstasyon']}** | {hata['Tarih/Saat']} | İş Emri: {hata['İş Emri']}")
                        st.write(f"**Hata Dönemi:** {hata['Montaj_Donemi']} | **Bölge:** {hata['Bölge']}")
                        if hata.get('Onceden_Hatali'):
                            st.error("🚨 Parça istasyona önceden hatalı gelmiş!")
                        st.write(f"**Açıklama:** {hata['Açıklama']}")
                        if hata.get("Foto_Base64"):
                            st.image(base64.b64decode(hata["Foto_Base64"]), width=350)
            else:
                st.write("Kayıtlı hata bulunmuyor.")

    # ---------------------------------------------------------
    # OPERATÖR EKRANI
    # ---------------------------------------------------------
    elif aktif_rol in ["Montaj-1", "Montaj-2", "Montaj-3"]:
        ist = db["stations"][aktif_rol]
        durum = ist["status"]
        
        # 1. ACİL DURUM (BÜYÜK EKRAN KİLİDİ)
        if ist.get("urgent_alert"):
            st.markdown(f"""
                <div class='urgent-alert'>
                    <div class='urgent-title'>🚨 ACİL İŞ EMRİ GELDİ! 🚨</div>
                    <h2 style='color: white;'>Yönetici mevcut işinizi durdurdu ve yeni bir görev atadı.</h2>
                    <h1 style='color: yellow; margin-top: 30px;'>İş Emri: {ist['id']} | Adet: {ist['target_qty']}</h1>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✅ MEVCUT İŞİ BEKLEMEYE AL & ACİL İŞE BAŞLA", type="primary", use_container_width=True):
                ist["urgent_alert"] = False
                ist["status"] = "Çalışıyor"
                ist["last_work_start"] = time.time()
                save_db(db)
                st.rerun()
                
        # 2. NORMAL AKIŞ
        else:
            # ÜST BİLGİ BARI
            if durum not in ["Bekliyor", "Tamamlandı"]:
                st.markdown(f"""
                    <div style='display: flex; justify-content: space-between; background-color: #f1f3f5; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
                        <strong style='font-size: 20px;'>Ürün: {ist['sn']}</strong>
                        <strong style='font-size: 20px;'>Adet: {ist['current_qty']} / {ist['target_qty']}</strong>
                        <strong style='font-size: 20px;'>⏱️ {format_time(get_live_work_time(aktif_rol))}</strong>
                    </div>
                """, unsafe_allow_html=True)
            
            if durum == "Bekliyor":
                st.markdown("<div class='kiosk-card'><div class='kiosk-title'>☕ BEKLEMEDE</div><div class='kiosk-subtitle'>Yeni iş emri bekleniyor...</div></div>", unsafe_allow_html=True)
                
                # Eğer askıda iş varsa geri dönebilme
                if ist.get("suspended_job"):
                    st.info("📌 Daha önceden yarım kalan (askıya alınan) bir işiniz var.")
                    if st.button("Askıdaki İşe Geri Dön", use_container_width=True):
                        sj = ist["suspended_job"]
                        ist["id"] = sj["id"]
                        ist["sn"] = sj["sn"]
                        ist["target_qty"] = sj["target_qty"]
                        ist["current_qty"] = sj["current_qty"]
                        ist["step"] = sj["step"]
                        ist["work_time"] = sj["work_time"]
                        ist["break_time"] = sj["break_time"]
                        ist["qc_wait_time"] = sj["qc_wait_time"]
                        ist["status"] = "Duraklatıldı"
                        ist["suspended_job"] = None
                        save_db(db)
                        st.rerun()
                
            elif durum == "Tamamlandı":
                st.markdown("<div class='kiosk-card' style='border: 3px solid #28a745;'><div class='kiosk-title' style='color:#28a745;'>✅ İŞ BİTTİ</div><div class='kiosk-subtitle'>Yöneticiye bilgi verildi. Yeni görev bekleniyor.</div></div>", unsafe_allow_html=True)
                if ist.get("suspended_job"):
                    if st.button("📌 Askıdaki Eski İşe Geri Dön", use_container_width=True, type="primary"):
                        sj = ist["suspended_job"]
                        ist["id"] = sj["id"]
                        ist["sn"] = sj["sn"]
                        ist["target_qty"] = sj["target_qty"]
                        ist["current_qty"] = sj["current_qty"]
                        ist["step"] = sj["step"]
                        ist["work_time"] = sj["work_time"]
                        ist["break_time"] = sj["break_time"]
                        ist["qc_wait_time"] = sj["qc_wait_time"]
                        ist["status"] = "Duraklatıldı"
                        ist["suspended_job"] = None
                        save_db(db)
                        st.rerun()

            elif durum in ["Onay Bekliyor", "Acil Bekliyor"]:
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
                    if ist["status"] == "Mola" and ist["last_break_start"]:
                        ist["break_time"] += time.time() - ist["last_break_start"]
                    ist["last_break_start"] = None
                    ist["last_work_start"] = time.time()
                    ist["status"] = "Çalışıyor"
                    ist["break_reason"] = ""
                    save_db(db)
                    st.rerun()
                    
            elif durum == "Çalışıyor":
                step = ist["step"]
                adımlar = ["Görsel Talimatlara Göre Montaj", "Ara Denetim", "Zorunlu Kalite Onayı", "Test ve Kayıt"]
                
                if step <= 4:
                    st.markdown(f"""
                        <div class='kiosk-card' style='border: 4px solid #007bff;'>
                            <div class='step-indicator'>ADIM {step} / 4</div>
                            <div class='kiosk-title'>{adımlar[step-1].upper()}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    c1, c2, c3 = st.columns([1, 2, 1])
                    with c2:
                        if step == 3: 
                            st.error("🔒 KALİTE ONAYI GEREKİYOR (Kalite birimine bildirim gitti)")
                            qc_pass = st.text_input("Kalite Şifresi:", type="password")
                            if st.button("✔️ ONAYLA VE GEÇ", type="primary", use_container_width=True):
                                if qc_pass == USERS["kalite1"]["pass"]:
                                    if ist.get("qc_req_time"):
                                        ist["qc_wait_time"] += time.time() - ist["qc_req_time"]
                                    ist["step"] = 4
                                    ist["qc_req_time"] = None
                                    save_db(db)
                                    st.rerun()
                                else:
                                    st.error("Şifre Hatalı!")
                        else:
                            if st.button("✅ ADIMI TAMAMLA", type="primary", use_container_width=True):
                                if step == 2: 
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
                            stop_timers(ist)
                            ist["status"] = "Tamamlandı"
                            db["performance"][aktif_rol]["tamamlanan_is_emri"] += 1
                            
                            # Tamamlanan işi geçmişe at
                            db["completed_jobs"].append({
                                "id": ist["id"], "sn": ist["sn"], "station": aktif_rol, "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                            })
                        save_db(db)
                        st.rerun()
                
                # --- OPERASYONEL İŞLEMLER (Aktarma, Duruş) ---
                st.divider()
                op_c1, op_c2 = st.columns(2)
                with op_c1:
                    with st.popover("☕ DURUŞ BİLDİR / İŞİ BEKLET", use_container_width=True):
                        mola_sebebi = st.selectbox("Duruş Sebebi Seçiniz:", ["Mola (Yemek)", "Mola (Çay)", "Parça Temini", "Arıza", "Diğer"])
                        if st.button("Duruşa Geç", type="primary"):
                            stop_timers(ist)
                            ist["last_break_start"] = time.time()
                            ist["break_reason"] = mola_sebebi
                            ist["status"] = "Mola"
                            save_db(db)
                            st.rerun()
                with op_c2:
                    with st.popover("🔄 İŞİ BAŞKA İSTASYONA AKTAR", use_container_width=True):
                        st.write("Yarım kalan bu işi devret:")
                        hedef = st.selectbox("Hedef İstasyon:", [s for s in ["Montaj-1", "Montaj-2", "Montaj-3"] if s != aktif_rol])
                        if st.button("İşi Aktar", type="primary"):
                            if db["stations"][hedef]["status"] in ["Bekliyor", "Tamamlandı"]:
                                stop_timers(ist)
                                db["stations"][hedef] = copy.deepcopy(ist)
                                db["stations"][hedef]["status"] = "Duraklatıldı" # Hedefte duraklatılmış başlasın
                                db["stations"][aktif_rol] = get_empty_station()
                                save_db(db)
                                st.success("Aktarıldı!")
                                st.rerun()
                            else:
                                st.error("Hedef istasyon şu an dolu!")

            # --- SADECE BİTMİŞ İŞLER İÇİN HATA BİLDİRİMİ ---
            st.divider()
            with st.expander("📝 GEÇMİŞ İŞLERDE HATA BİLDİR (Sadece Tamamlananlar)"):
                gecmis_isler = [j for j in db["completed_jobs"] if j["station"] == aktif_rol]
                if gecmis_isler:
                    secilen_is = st.selectbox("Hatalı İş Emri:", [f"{j['id']} - {j['date']}" for j in reversed(gecmis_isler)])
                    hata_bolgesi = st.selectbox("Bölge:", ["Ön Yüz", "Arka Yüz", "Yan", "İç", "Diğer"])
                    hata_aciklama = st.text_area("Açıklama:")
                    onceden_hatali = st.checkbox("Parça bana hatalı gelmişti")
                    foto = st.file_uploader("Görsel (Opsiyonel)", type=["png", "jpg", "jpeg"])
                    
                    if st.button("Geçmişe Dönük Hatayı İlet", type="primary"):
                        if hata_aciklama != "":
                            foto_base64 = base64.b64encode(foto.read()).decode("utf-8") if foto else None
                            db["errors"].append({
                                "Tarih/Saat": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "İstasyon": aktif_rol,
                                "İş Emri": secilen_is.split(" - ")[0],
                                "Montaj_Donemi": "Geçmiş İş Emri",
                                "Hatali_Adim": "Sonradan Fark Edildi",
                                "Onceden_Hatali": onceden_hatali,
                                "Bölge": hata_bolgesi,
                                "Açıklama": hata_aciklama,
                                "Foto_Base64": foto_base64
                            })
                            save_db(db)
                            st.success("Hata detaylarıyla iletildi!")
                        else:
                            st.error("Açıklama zorunludur.")
                else:
                    st.info("Henüz tamamladığınız bir iş emri bulunmuyor.")

    # ---------------------------------------------------------
    # KALİTE EKRANI
    # ---------------------------------------------------------
    elif aktif_rol == "Kalite":
        st.title("Kalite Kontrol Merkezi")
        bekleyenler = [s for s, v in db["stations"].items() if v["step"] == 3 and v["status"] == "Çalışıyor"]
        
        if bekleyenler:
            st.error(f"🚨 ACİL ONAY BEKLEYEN İSTASYONLAR: {', '.join(bekleyenler)}")
        else:
            st.success("✅ Bekleyen onay yok.")
            
        st.divider()
        st.subheader("Sahadaki Hata Bildirimleri")
        if db["errors"]:
            for hata in reversed(db["errors"]):
                with st.container(border=True):
                    st.markdown(f"**{hata['İstasyon']}** | {hata['Tarih/Saat']}")
                    st.write(f"**Bölge:** {hata['Bölge']} | **Açıklama:** {hata['Açıklama']}")
                    if hata.get("Foto_Base64"):
                        st.image(base64.b64decode(hata["Foto_Base64"]), width=300)
        else:
            st.write("Kayıtlı hata bulunmuyor.")

    if canli_mod:
        time.sleep(3)
        st.rerun()
