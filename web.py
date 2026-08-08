import streamlit as st
import streamlit.components.v1 as components
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
    .block-container { padding-top: 4rem; font-family: 'Helvetica Neue', sans-serif; }
    .kiosk-card { border-radius: 15px; padding: 40px; text-align: center; margin-bottom: 20px; border: 2px solid rgba(128, 128, 128, 0.2); }
    .kiosk-title { font-size: 55px; font-weight: 800; margin-bottom: 10px; }
    .kiosk-subtitle { font-size: 22px; opacity: 0.7; margin-bottom: 30px; }
    .step-indicator { color: #007bff; font-weight: bold; font-size: 24px; margin-bottom: -10px; }
    .urgent-alert { background-color: #dc3545; color: white; padding: 40px; border-radius: 20px; text-align: center; border: 5px solid #8b0000; margin-top: 20px;}
    .urgent-title { font-size: 60px; font-weight: 900; margin-bottom: 20px; line-height: 1.1;}
    .new-error-alert { background-color: #fff3cd; color: #856404; padding: 20px; border-left: 10px solid #ffeeba; border-radius: 5px; margin-bottom: 20px; font-size: 20px;}
    .timer-box { font-size: 35px; font-weight: bold; color: #d9534f; background: #ffebeb; padding: 10px 20px; border-radius: 10px; display: inline-block; }
    </style>
""", unsafe_allow_html=True)

# --- VERİTABANI YÖNETİMİ (JSON) ---
DB_FILE = "db.json"

def get_empty_station():
    return {
        "status": "Bekliyor", "id": "", "sn": "", "target_qty": 0, "current_qty": 0, "step": 1, 
        "work_time": 0.0, "break_time": 0.0, "qc_wait_time": 0.0, "idle_time": 0.0,
        "last_work_start": None, "last_break_start": None, "qc_req_time": None, "last_idle_start": time.time(),
        "break_reason": "", "urgent_alert": False, "suspended_job": None, "pending_urgent_job": None,
        "job_queue": [] # YENİ: Arkada bekletilen işler listesi
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
        "errors": [],
        "work_order_templates": [] 
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
    t = db["stations"][istasyon].get("work_time", 0.0)
    if db["stations"][istasyon]["status"] == "Çalışıyor" and db["stations"][istasyon].get("last_work_start"):
        t += time.time() - db["stations"][istasyon]["last_work_start"]
    return t

def get_live_idle_time(istasyon):
    t = db["stations"][istasyon].get("idle_time", 0.0)
    if db["stations"][istasyon]["status"] in ["Bekliyor", "Tamamlandı"] and db["stations"][istasyon].get("last_idle_start"):
        t += time.time() - db["stations"][istasyon]["last_idle_start"]
    return t

def stop_timers(istasyon_verisi):
    if istasyon_verisi["status"] == "Çalışıyor" and istasyon_verisi.get("last_work_start"):
        istasyon_verisi["work_time"] = istasyon_verisi.get("work_time", 0.0) + (time.time() - istasyon_verisi["last_work_start"])
        istasyon_verisi["last_work_start"] = None
    if istasyon_verisi["status"] in ["Mola", "Boşta Mola"] and istasyon_verisi.get("last_break_start"):
        istasyon_verisi["break_time"] = istasyon_verisi.get("break_time", 0.0) + (time.time() - istasyon_verisi["last_break_start"])
        istasyon_verisi["last_break_start"] = None
    if istasyon_verisi.get("qc_req_time"):
        istasyon_verisi["qc_wait_time"] = istasyon_verisi.get("qc_wait_time", 0.0) + (time.time() - istasyon_verisi["qc_req_time"])
        istasyon_verisi["qc_req_time"] = None
    if istasyon_verisi["status"] in ["Bekliyor", "Tamamlandı"] and istasyon_verisi.get("last_idle_start"):
        istasyon_verisi["idle_time"] = istasyon_verisi.get("idle_time", 0.0) + (time.time() - istasyon_verisi["last_idle_start"])
        istasyon_verisi["last_idle_start"] = None

# --- GİRİŞ EKRANI ---
if not st.session_state.logged_in:
    st.markdown("<br><br><h1 style='text-align: center; font-size: 70px;'>DİJİTAL SİS</h1>", unsafe_allow_html=True)
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
            if (durum_kontrol in ["Bekliyor", "Boşta Mola", "Onay Bekliyor", "Tamamlandı"] or durum_kontrol == "Acil Bekliyor") and not urgent_kontrol:
                canli_mod = st.checkbox("🟢 Sistem Takibi", value=True)
            else:
                canli_mod = st.checkbox("🟢 Çalışma Modu (Süreyi İzle)", value=True)
        st.divider()
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            logout()

    # ---------------------------------------------------------
    # YÖNETİCİ EKRANI
    # ---------------------------------------------------------
    if aktif_rol == "Yönetici":
        st.title("Yönetici Kontrol Paneli")
        
        yeni_hatalar = [h for h in db["errors"] if h.get("is_new", True)]
        if yeni_hatalar:
            st.error("🚨 DİKKAT: YENİ HATA BİLDİRİMLERİ VAR!")
            for i, h in enumerate(yeni_hatalar):
                with st.container(border=True):
                    col_err1, col_err2 = st.columns([4, 1])
                    with col_err1:
                        st.markdown(f"**{h['İstasyon']}** - {h['Hatali_Adim']} adımında hata bildirdi! (Bölge: {h['Bölge']})")
                        st.write(f"**Açıklama:** {h['Açıklama']}")
                    with col_err2:
                        if st.button("Görüldü / Kapat", key=f"ok_{i}", type="primary"):
                            h["is_new"] = False
                            save_db(db)
                            st.rerun()
            st.divider()
        
        tamamlanan_istasyonlar = [ist for ist, veri in db["stations"].items() if veri["status"] == "Tamamlandı"]
        if tamamlanan_istasyonlar:
            st.success(f"🎉 **{', '.join(tamamlanan_istasyonlar)}** iş emrini tamamladı! Yeni iş emri bekliyorlar.")

        tab1, tab2, tab3, tab4 = st.tabs(["📊 Canlı İzleme & Performans", "🚀 İş Emri Ata", "⚠️ Tüm Hata Kayıtları", "🗂️ Geçmiş İşler & Sicil"])
        
        with tab1:
            st.subheader("İzlenebilirlik ve Canlı Takip Tablosu")
            
            tablo_verisi = []
            adim_isimleri = ["Adım 1", "Adım 2", "Kalite Onayı", "Kapatma"]
            
            for ist in ["Montaj-1", "Montaj-2", "Montaj-3"]:
                veri = db["stations"][ist]
                w_time = get_live_work_time(ist)
                i_time = get_live_idle_time(ist)
                b_time = veri.get("break_time", 0.0)
                q_time = veri.get("qc_wait_time", 0.0)
                kuyruk_sayisi = len(veri.get("job_queue", []))
                
                if veri["status"] in ["Mola", "Boşta Mola"] and veri.get("last_break_start"):
                    b_time += time.time() - veri["last_break_start"]
                if veri.get("qc_req_time"):
                    q_time += time.time() - veri["qc_req_time"]
                    
                step_idx = veri.get("step", 1) - 1
                adim_str = adim_isimleri[step_idx] if step_idx < 4 else "Bitti"
                
                durum_gosterim = veri["status"]
                if veri["status"] == "Çalışıyor":
                    durum_gosterim = f"🟢 Çalışıyor ({adim_str})"
                elif veri["status"] == "Boşta Mola":
                    durum_gosterim = f"☕ Mola ({veri.get('break_reason', '')}) - İşsiz"
                elif veri["status"] == "Mola":
                    durum_gosterim = f"🔴 Duruş ({veri.get('break_reason', '')})"
                elif veri["status"] == "Bekliyor":
                    durum_gosterim = "🟡 İş Emri Bekliyor"
                elif veri["status"] == "Tamamlandı":
                    durum_gosterim = "✅ İş Bitti (Yeni İş Bekliyor)"
                elif veri["status"] in ["Onay Bekliyor", "Acil Bekliyor"]:
                    durum_gosterim = "🟠 Operatör Onayı Bekliyor"
                elif veri["status"] == "Duraklatıldı":
                    durum_gosterim = "⏸️ Duraklatıldı"
                    
                tablo_verisi.append({
                    "İstasyon": ist,
                    "Anlık Durum": durum_gosterim,
                    "Aktif İş": veri["id"] if veri["id"] else "-",
                    "Kuyruktaki İş": kuyruk_sayisi,
                    "Adet": f"{veri['current_qty']}/{veri['target_qty']}" if veri["id"] else "-",
                    "Çalışma (Dk)": round(w_time / 60, 1),
                    "Duruş/Mola (Dk)": round(b_time / 60, 1),
                    "Kalite Bekleme (Dk)": round(q_time / 60, 1),
                    "İş Emri Bekleme (Dk)": round(i_time / 60, 1)
                })
            
            st.dataframe(pd.DataFrame(tablo_verisi), use_container_width=True)
            st.divider()
            
            st.subheader("⏱️ İstasyon Süre Dağılımları (Darboğaz Analizi)")
            st.write("*Not: 'İş Emri Bekleme' yöneticinin veya planlamanın darboğazını gösterir.*")
            pie_c1, pie_c2, pie_c3 = st.columns(3)
            
            for index, ist in enumerate(["Montaj-1", "Montaj-2", "Montaj-3"]):
                with [pie_c1, pie_c2, pie_c3][index]:
                    v = tablo_verisi[index]
                    total_time = v["Çalışma (Dk)"] + v["Duruş/Mola (Dk)"] + v["Kalite Bekleme (Dk)"] + v["İş Emri Bekleme (Dk)"]
                    if total_time > 0:
                        df_pie = pd.DataFrame({
                            "Kategori": ["Çalışma", "Duruş/Mola", "Kalite Bekleme", "İş Emri Bekleme"],
                            "Süre": [v["Çalışma (Dk)"], v["Duruş/Mola (Dk)"], v["Kalite Bekleme (Dk)"], v["İş Emri Bekleme (Dk)"]]
                        })
                        fig = px.pie(df_pie, values="Süre", names="Kategori", title=f"{ist}", hole=0.3,
                                     color="Kategori", color_discrete_map={
                                         "Çalışma": "#28a745", 
                                         "Duruş/Mola": "#dc3545", 
                                         "Kalite Bekleme": "#ffc107",
                                         "İş Emri Bekleme": "#6c757d"
                                     })
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info(f"{ist} süre kaydı yok.")
                        
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
            
            sablonlar = ["-- Yeni (Boş) Form --"] + [f"{t['wo_id']} (SN: {t['sn_id']})" for t in db.get("work_order_templates", [])]
            secilen_sablon = st.selectbox("Geçmiş İş Emirlerinden Seç (Hızlı Doldur):", sablonlar)
            
            def_wo = ""
            def_sn = ""
            if secilen_sablon != "-- Yeni (Boş) Form --":
                for t in db["work_order_templates"]:
                    if f"{t['wo_id']} (SN: {t['sn_id']})" == secilen_sablon:
                        def_wo = t['wo_id']
                        def_sn = t['sn_id']
                        break
            
            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                hedef_istasyon = st.selectbox("İstasyon Seçiniz:", ["Montaj-1", "Montaj-2", "Montaj-3"])
                wo_id = st.text_input("İş Emri Numarası:", value=def_wo, placeholder="Örn: WO-2026-101")
                sn_id = st.text_input("Seri No Başlangıcı:", value=def_sn, placeholder="Örn: SN-001")
                hedef_sayi = st.number_input("Hedef Adet:", min_value=1, value=1)
                
                st.markdown("---")
                is_urgent = st.checkbox("🚨 ACİL İŞ EMRİ (Operatöre uyarı gider, mevcut iş askıya alınır)")
                
                if st.button("🚀 İş Emrini Gönder", type="primary", use_container_width=True):
                    if wo_id != "" and not any(t["wo_id"] == wo_id for t in db["work_order_templates"]):
                        db["work_order_templates"].append({"wo_id": wo_id, "sn_id": sn_id})

                    hedef_veri = db["stations"][hedef_istasyon]
                    yeni_is_paketi = {
                        "id": wo_id, "sn": sn_id, "target_qty": hedef_sayi,
                        "current_qty": 1, "step": 1, "work_time": 0.0, "break_time": 0.0, "qc_wait_time": 0.0
                    }
                    
                    if is_urgent:
                        hedef_veri["pending_urgent_job"] = yeni_is_paketi
                        hedef_veri["pending_urgent_job"]["status"] = "Acil Bekliyor"
                        hedef_veri["urgent_alert"] = True
                        st.success(f"Acil İş Emri {hedef_istasyon} personeline bildirildi!")
                    else:
                        # Eğer istasyon boşsa direkt ata
                        if hedef_veri["id"] == "" or hedef_veri["status"] in ["Bekliyor", "Tamamlandı"]:
                            stop_timers(hedef_veri)
                            hedef_veri["status"] = "Onay Bekliyor"
                            hedef_veri["id"] = wo_id
                            hedef_veri["sn"] = sn_id
                            hedef_veri["target_qty"] = hedef_sayi
                            hedef_veri["current_qty"] = 1
                            hedef_veri["step"] = 1
                            hedef_veri["work_time"] = 0.0
                            hedef_veri["break_time"] = 0.0
                            hedef_veri["qc_wait_time"] = 0.0
                            hedef_veri["last_work_start"] = None
                            hedef_veri["last_break_start"] = None
                            st.success(f"Normal İş Emri {hedef_istasyon} istasyonuna gönderildi.")
                        else:
                            # İstasyon dolu, KUYRUĞA EKLE
                            hedef_veri["job_queue"].append(yeni_is_paketi)
                            st.info(f"Personel şu an meşgul. İş emri {hedef_istasyon} kuyruğuna eklendi.")
                    
                    save_db(db)
                    st.rerun()

        with tab3:
            st.subheader("Geçmiş ve Okunmuş Hata Kayıtları")
            if db["errors"]:
                for hata in reversed(db["errors"]):
                    with st.container(border=True):
                        st.markdown(f"**{hata['İstasyon']}** | {hata['Tarih/Saat']} | İş Emri: {hata['İş Emri']}")
                        st.write(f"**Montaj Dönemi:** {hata['Montaj_Donemi']} | **Bölge:** {hata['Bölge']}")
                        if hata.get('Onceden_Hatali'):
                            st.error("🚨 Parça istasyona önceden hatalı gelmiş!")
                        st.write(f"**Açıklama:** {hata['Açıklama']}")
                        if hata.get("Foto_Base64"):
                            st.image(base64.b64decode(hata["Foto_Base64"]), width=350)
            else:
                st.write("Kayıtlı hata bulunmuyor.")
                
        with tab4:
            st.subheader("Geçmiş İşler ve Personel Sicili")
            if db["completed_jobs"]:
                sicil_data = []
                for job in reversed(db["completed_jobs"]):
                    hatalar = [e for e in db["errors"] if e["İş Emri"] == job["id"] and e["İstasyon"] == job["station"]]
                    hata_durumu = "VAR ⚠️" if hatalar else "Yok ✅"
                    hata_notu = " | ".join([e["Açıklama"] for e in hatalar]) if hatalar else "-"
                    
                    sicil_data.append({
                        "Tarih": job["date"],
                        "İstasyon (Personel)": job["station"],
                        "İş Emri": job["id"],
                        "Ürün SN": job["sn"],
                        "Tamamlanan": f"{job.get('target_qty', 'Bilinmiyor')} Adet",
                        "Hata Kaydı": hata_durumu,
                        "Hata Açıklaması": hata_notu
                    })
                st.dataframe(pd.DataFrame(sicil_data), use_container_width=True)
            else:
                st.info("Henüz tamamlanmış bir iş emri bulunmuyor.")

    # ---------------------------------------------------------
    # OPERATÖR EKRANI
    # ---------------------------------------------------------
    elif aktif_rol in ["Montaj-1", "Montaj-2", "Montaj-3"]:
        ist = db["stations"][aktif_rol]
        durum = ist["status"]
        
        # 1. ACİL DURUM UYARISI (TAM EKRAN KİLİT)
        if ist.get("urgent_alert"):
            st.markdown(f"""
                <div class='urgent-alert'>
                    <div class='urgent-title'>🚨 DİKKAT: ACİL İŞ EMRİ GELDİ!</div>
                    <h2 style='color: white;'>Yöneticiden yeni bir acil görev ataması var.</h2>
                    <h1 style='color: yellow; margin-top: 10px;'>İş Emri: {ist['pending_urgent_job']['id']} | Adet: {ist['pending_urgent_job']['target_qty']}</h1>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("⚡ HEMEN GEÇ (Mevcut İşi Askıya Al)", type="primary", use_container_width=True):
                    if ist["id"] != "":
                        stop_timers(ist)
                        ist["suspended_job"] = {
                            "id": ist["id"], "sn": ist["sn"], "target_qty": ist["target_qty"],
                            "current_qty": ist["current_qty"], "step": ist["step"], 
                            "work_time": ist["work_time"], "break_time": ist["break_time"], 
                            "qc_wait_time": ist["qc_wait_time"]
                        }
                    
                    p = ist["pending_urgent_job"]
                    ist["id"], ist["sn"], ist["target_qty"] = p["id"], p["sn"], p["target_qty"]
                    ist["current_qty"], ist["step"] = 1, 1
                    ist["work_time"], ist["break_time"], ist["qc_wait_time"] = 0.0, 0.0, 0.0
                    ist["status"] = "Onay Bekliyor"
                    ist["last_work_start"] = None
                    
                    ist["urgent_alert"] = False
                    ist["pending_urgent_job"] = None
                    save_db(db)
                    st.rerun()
            with c2:
                if st.button("⏳ MEVCUT İŞİME DEVAM ET (Acil İşi Kenarda Beklet)", use_container_width=True):
                    ist["urgent_alert"] = False
                    save_db(db)
                    st.rerun()
                
        # 2. NORMAL AKIŞ 
        else:
            if ist.get("pending_urgent_job"):
                st.error("🚨 KENARDA BEKLEYEN ACİL BİR İŞİNİZ VAR!")
                if st.button("Geçiş Yapmak İçin Tıkla (Mevcut İş Askıya Alınır)", use_container_width=True):
                    if ist["id"] != "":
                        stop_timers(ist)
                        ist["suspended_job"] = {
                            "id": ist["id"], "sn": ist["sn"], "target_qty": ist["target_qty"],
                            "current_qty": ist["current_qty"], "step": ist["step"], 
                            "work_time": ist["work_time"], "break_time": ist["break_time"], 
                            "qc_wait_time": ist["qc_wait_time"]
                        }
                    p = ist["pending_urgent_job"]
                    ist["id"], ist["sn"], ist["target_qty"] = p["id"], p["sn"], p["target_qty"]
                    ist["current_qty"], ist["step"] = 1, 1
                    ist["work_time"], ist["break_time"], ist["qc_wait_time"] = 0.0, 0.0, 0.0
                    ist["status"] = "Onay Bekliyor"
                    ist["last_work_start"] = None
                    ist["pending_urgent_job"] = None
                    save_db(db)
                    st.rerun()
                st.divider()

            # --- SÜRE VE BİLGİ ALANI (CANLI JS SAYAÇ İLE) ---
            if durum not in ["Bekliyor", "Boşta Mola", "Tamamlandı", "Onay Bekliyor"]:
                with st.container(border=True):
                    col_i1, col_i2, col_i3, col_i4 = st.columns([2,2,1,1])
                    col_i1.metric("📦 Ürün / İş Emri", f"{ist['sn']} | {ist['id']}")
                    col_i2.metric("🎯 Adet İlerlemesi", f"{ist['current_qty']} / {ist['target_qty']}")
                    
                    if len(ist.get("job_queue", [])) > 0:
                        col_i3.metric("📥 Kuyruktaki İşler", f"{len(ist['job_queue'])} Adet")
                    
                    with col_i4:
                        is_active = "true" if durum == "Çalışıyor" else "false"
                        components.html(
                            f"""
                            <div style="font-family: 'Helvetica Neue', sans-serif; text-align: center;">
                                <div style="font-size: 14px; color: #555; margin-bottom: 5px;">⏱️ Çalışma Süresi</div>
                                <div id="timer" style="font-size: 30px; font-weight: bold; color: #d9534f; background: #ffebeb; padding: 5px 10px; border-radius: 10px; display: inline-block;">
                                    00:00:00
                                </div>
                            </div>
                            <script>
                                var totalSeconds = {int(get_live_work_time(aktif_rol))};
                                var isActive = {is_active};
                                function formatTime(sec) {{
                                    var h = Math.floor(sec / 3600).toString().padStart(2, '0');
                                    var m = Math.floor((sec % 3600) / 60).toString().padStart(2, '0');
                                    var s = Math.floor(sec % 60).toString().padStart(2, '0');
                                    return h + ":" + m + ":" + s;
                                }}
                                document.getElementById('timer').innerHTML = formatTime(totalSeconds);
                                if (isActive) {{
                                    setInterval(function() {{
                                        totalSeconds++;
                                        document.getElementById('timer').innerHTML = formatTime(totalSeconds);
                                    }}, 1000);
                                }}
                            </script>
                            """,
                            height=80
                        )
                st.markdown("<br>", unsafe_allow_html=True)
            
            if durum == "Bekliyor" or durum == "Boşta Mola":
                if durum == "Bekliyor":
                    st.markdown("<div class='kiosk-card'><div class='kiosk-title'>☕ BEKLEMEDE</div><div class='kiosk-subtitle'>Yeni iş emri bekleniyor...</div></div>", unsafe_allow_html=True)
                    
                    # KUYRUKTA İŞ VARSA
                    if len(ist.get("job_queue", [])) > 0:
                        st.info(f"📥 Arka planda bekleyen {len(ist['job_queue'])} adet yeni işiniz var.")
                        if st.button("🚀 SIRADAKİ İŞİ AL VE BAŞLA", type="primary", use_container_width=True):
                            nj = ist["job_queue"].pop(0)
                            ist["id"], ist["sn"], ist["target_qty"] = nj["id"], nj["sn"], nj["target_qty"]
                            ist["current_qty"], ist["step"] = 1, 1
                            ist["work_time"], ist["break_time"], ist["qc_wait_time"] = 0.0, 0.0, 0.0
                            ist["status"] = "Onay Bekliyor"
                            stop_timers(ist) # Idle sayacını sıfırla
                            save_db(db)
                            st.rerun()

                    st.divider()
                    with st.popover("☕ DURUŞ / MOLA BİLDİR (İşsiz)", use_container_width=True):
                        mola_sebebi = st.selectbox("Duruş Sebebi Seçiniz:", ["Mola (Yemek)", "Mola (Çay)", "Toplantı", "Diğer"])
                        if st.button("Duruşa Geç", type="primary"):
                            stop_timers(ist)
                            ist["last_break_start"] = time.time()
                            ist["break_reason"] = mola_sebebi
                            ist["status"] = "Boşta Mola"
                            save_db(db)
                            st.rerun()
                else: 
                    st.markdown(f"<div class='kiosk-card' style='border: 3px solid #dc3545;'><div class='kiosk-title' style='color:#dc3545;'>⏸️ DURUŞTA ({ist['break_reason']})</div><div class='kiosk-subtitle'>Süreniz sayılıyor. İş emri bekleniyor...</div></div>", unsafe_allow_html=True)
                    if st.button("▶️ MOLAYI BİTİR (Beklemeye Dön)", type="primary", use_container_width=True):
                        if ist["last_break_start"]:
                            ist["break_time"] += time.time() - ist["last_break_start"]
                        ist["last_break_start"] = None
                        ist["status"] = "Bekliyor"
                        ist["last_idle_start"] = time.time()
                        ist["break_reason"] = ""
                        save_db(db)
                        st.rerun()

                if ist.get("suspended_job"):
                    st.info("📌 Daha önceden yarım kalan (askıya alınan) bir işiniz var.")
                    if st.button("Askıdaki İşe Geri Dön", use_container_width=True):
                        sj = ist["suspended_job"]
                        ist["id"], ist["sn"], ist["target_qty"] = sj["id"], sj["sn"], sj["target_qty"]
                        ist["current_qty"], ist["step"] = sj["current_qty"], sj["step"]
                        ist["work_time"], ist["break_time"], ist["qc_wait_time"] = sj["work_time"], sj["break_time"], sj["qc_wait_time"]
                        ist["status"] = "Duraklatıldı"
                        ist["suspended_job"] = None
                        stop_timers(ist) 
                        save_db(db)
                        st.rerun()
                
            elif durum == "Tamamlandı":
                st.markdown("<div class='kiosk-card' style='border: 3px solid #28a745;'><div class='kiosk-title' style='color:#28a745;'>✅ İŞ BİTTİ</div><div class='kiosk-subtitle'>Yöneticiye bilgi verildi. Yeni görev bekleniyor.</div></div>", unsafe_allow_html=True)
                
                if len(ist.get("job_queue", [])) > 0:
                    st.info(f"📥 Arka planda bekleyen {len(ist['job_queue'])} adet yeni işiniz var.")
                    if st.button("🚀 SIRADAKİ İŞİ AL VE BAŞLA", type="primary", use_container_width=True):
                        nj = ist["job_queue"].pop(0)
                        ist["id"], ist["sn"], ist["target_qty"] = nj["id"], nj["sn"], nj["target_qty"]
                        ist["current_qty"], ist["step"] = 1, 1
                        ist["work_time"], ist["break_time"], ist["qc_wait_time"] = 0.0, 0.0, 0.0
                        ist["status"] = "Onay Bekliyor"
                        stop_timers(ist)
                        save_db(db)
                        st.rerun()

                if ist.get("suspended_job"):
                    if st.button("📌 Askıdaki Eski İşe Geri Dön", use_container_width=True, type="primary"):
                        sj = ist["suspended_job"]
                        ist["id"], ist["sn"], ist["target_qty"] = sj["id"], sj["sn"], sj["target_qty"]
                        ist["current_qty"], ist["step"] = sj["current_qty"], sj["step"]
                        ist["work_time"], ist["break_time"], ist["qc_wait_time"] = sj["work_time"], sj["break_time"], sj["qc_wait_time"]
                        ist["status"] = "Duraklatıldı"
                        ist["suspended_job"] = None
                        stop_timers(ist)
                        save_db(db)
                        st.rerun()

            elif durum in ["Onay Bekliyor", "Acil Bekliyor"]:
                st.markdown(f"<div class='kiosk-card' style='border: 3px solid #ffc107;'><div class='kiosk-title'>📦 YENİ GÖREV</div><div class='kiosk-subtitle'>İş Emri: {ist['id']} | Toplam: {ist['target_qty']} Adet</div></div>", unsafe_allow_html=True)
                if st.button("🚀 GÖREVİ KABUL ET VE BAŞLA", type="primary", use_container_width=True):
                    stop_timers(ist) 
                    ist["status"] = "Çalışıyor"
                    ist["last_work_start"] = time.time()
                    save_db(db)
                    st.rerun()
                    
            elif durum == "Mola" or durum == "Duraklatıldı":
                mesaj = f"DURUŞTA ({ist['break_reason']})" if durum == "Mola" else "DURAKLATILDI"
                st.markdown(f"<div class='kiosk-card' style='border: 3px solid #dc3545;'><div class='kiosk-title' style='color:#dc3545;'>⏸️ {mesaj}</div></div>", unsafe_allow_html=True)
                if st.button("▶️ İŞE DEVAM ET", type="primary", use_container_width=True):
                    stop_timers(ist)
                    ist["last_work_start"] = time.time()
                    ist["status"] = "Çalışıyor"
                    ist["break_reason"] = ""
                    save_db(db)
                    st.rerun()
                    
            elif durum == "Çalışıyor":
                step = ist.get("step", 1)
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
                                        ist["qc_wait_time"] = ist.get("qc_wait_time", 0.0) + (time.time() - ist["qc_req_time"])
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
                            ist["last_idle_start"] = time.time()
                            db["performance"][aktif_rol]["tamamlanan_is_emri"] += 1
                            
                            db["completed_jobs"].append({
                                "id": ist["id"], "sn": ist["sn"], "station": aktif_rol, 
                                "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "target_qty": ist["target_qty"]
                            })
                        save_db(db)
                        st.rerun()
                
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
                                stop_timers(db["stations"][hedef])
                                db["stations"][hedef] = copy.deepcopy(ist)
                                db["stations"][hedef]["status"] = "Duraklatıldı"
                                db["stations"][aktif_rol] = get_empty_station()
                                save_db(db)
                                st.success("Aktarıldı!")
                                st.rerun()
                            else:
                                st.error("Hedef istasyon şu an dolu!")

            st.divider()
            with st.expander("⚠️ HATA BİLDİR (Aktif veya Geçmiş Montajlar İçin)"):
                aktif_is_secenegi = f"Aktif İş: {ist['id']} (SN: {ist['sn']})" if ist['id'] != "" else None
                gecmis_isler = [f"Geçmiş İş: {j['id']} - {j['date']}" for j in db["completed_jobs"] if j["station"] == aktif_rol]
                
                secenekler = []
                if aktif_is_secenegi:
                    secenekler.append(aktif_is_secenegi)
                secenekler.extend(reversed(gecmis_isler))
                
                if secenekler:
                    secilen_is_emri = st.selectbox("Hatanın Ait Olduğu İş:", secenekler)
                    hata_donemi = "Şu anki (Yeni) Montaj" if secilen_is_emri == aktif_is_secenegi else "Geçmiş Montaj"
                    
                    hatali_adim = st.selectbox("Hatalı Adım:", ["Adım 1", "Adım 2", "Adım 3", "Adım 4", "Genel"])
                    onceden_hatali = st.checkbox("Parça buraya gelmeden önce zaten hatalıydı")
                    hata_bolgesi = st.selectbox("Hata Bölgesi:", ["Seçilmedi", "Ön Yüz", "Arka Yüz", "Yan", "İç", "Diğer"])
                    hata_aciklama = st.text_area("Hata Açıklaması:")
                    foto = st.file_uploader("Görsel Ekle (Opsiyonel)", type=["png", "jpg", "jpeg"])
                    
                    if st.button("Hatayı Yöneticiye Gönder", type="primary", use_container_width=True):
                        if hata_bolgesi != "Seçilmedi" and hata_aciklama != "":
                            foto_base64 = base64.b64encode(foto.read()).decode("utf-8") if foto else None
                            hedef_is_id = secilen_is_emri.split(":")[1].split(" ")[1] if "Aktif" in secilen_is_emri else secilen_is_emri.split(":")[1].split(" - ")[0].strip()
                            
                            db["errors"].append({
                                "Tarih/Saat": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "İstasyon": aktif_rol,
                                "İş Emri": hedef_is_id,
                                "Montaj_Donemi": hata_donemi,
                                "Hatali_Adim": hatali_adim,
                                "Onceden_Hatali": onceden_hatali,
                                "Bölge": hata_bolgesi,
                                "Açıklama": hata_aciklama,
                                "Foto_Base64": foto_base64,
                                "is_new": True 
                            })
                            save_db(db)
                            st.success("Hata ve detaylar başarıyla yöneticiye iletildi!")
                        else:
                            st.error("Lütfen hata bölgesini seçin ve açıklama yazın.")
                else:
                    st.info("Şu an üzerinde aktif bir iş veya geçmişte tamamlanmış bir iş bulunmuyor.")

    # ---------------------------------------------------------
    # KALİTE EKRANI
    # ---------------------------------------------------------
    elif aktif_rol == "Kalite":
        st.title("Kalite Kontrol Merkezi")
        bekleyenler = [s for s, v in db["stations"].items() if v.get("step") == 3 and v["status"] == "Çalışıyor"]
        
        if bekleyenler:
            st.error(f"🚨 ACİL ONAY BEKLEYEN İSTASYONLAR: {', '.join(bekleyenler)}")
        else:
            st.success("✅ Bekleyen onay yok.")
            
        st.divider()
        st.subheader("Sahadaki Hata Bildirimleri")
        if db["errors"]:
            for hata in reversed(db["errors"]):
                with st.container(border=True):
                    st.markdown(f"**{hata['İstasyon']}** | İş Emri: {hata['İş Emri']} | {hata['Tarih/Saat']}")
                    st.write(f"**Tür:** {hata['Montaj_Donemi']} | **Adım:** {hata['Hatali_Adim']} | **Bölge:** {hata['Bölge']}")
                    if hata.get('Onceden_Hatali'):
                        st.error("🚨 Parça önceden hatalı gelmiş.")
                    st.write(f"**Açıklama:** {hata['Açıklama']}")
                    if hata.get("Foto_Base64"):
                        st.image(base64.b64decode(hata["Foto_Base64"]), width=300)
        else:
            st.write("Kayıtlı hata bulunmuyor.")

    if canli_mod:
        time.sleep(3)
        st.rerun()
