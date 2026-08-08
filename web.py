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
    </style>
""", unsafe_allow_html=True)

# --- VERİTABANI YÖNETİMİ (JSON) ---
DB_FILE = "db.json"

def get_empty_station():
    return {
        "status": "Bekliyor", "id": "", "sn": "", "target_qty": 0, "current_qty": 0, "step": 1, 
        "work_time": 0.0, "break_time": 0.0, "qc_wait_time": 0.0, "idle_time": 0.0,
        "last_work_start": None, "last_break_start": None, "qc_req_time": None, "last_idle_start": time.time(),
        "break_reason": "", "urgent_alert": False, "suspended_jobs": [], "pending_urgent_job": None,
        "pending_jobs": [], "job_queue": []
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
            # Eski suspended_job yapısını listeye çevirme
            if "suspended_jobs" not in db["stations"][st_key]:
                db["stations"][st_key]["suspended_jobs"] = []
                old_sj = db["stations"][st_key].get("suspended_job")
                if old_sj:
                    db["stations"][st_key]["suspended_jobs"].append(old_sj)
                db["stations"][st_key]["suspended_job"] = None
                updated = True
            if "pending_jobs" not in db["stations"][st_key]:
                db["stations"][st_key]["pending_jobs"] = []
                updated = True
            if "job_queue" not in db["stations"][st_key]:
                db["stations"][st_key]["job_queue"] = []
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

def format_dk_sn(seconds):
    if seconds <= 0: return "0 dk 0 sn"
    dk = int(seconds // 60)
    sn = int(seconds % 60)
    return f"{dk} dk {sn} sn"

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
            if (durum_kontrol in ["Bekliyor", "Boşta Mola", "Tamamlandı"] or urgent_kontrol):
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
                
                anlik_mola = 0.0
                if veri["status"] in ["Mola", "Boşta Mola"] and veri.get("last_break_start"):
                    anlik_mola = time.time() - veri["last_break_start"]
                    b_time += anlik_mola
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
                    
                toplam_kuyruk = len(veri.get("pending_jobs", [])) + len(veri.get("job_queue", [])) + len(veri.get("suspended_jobs", []))
                
                tablo_verisi.append({
                    "İstasyon": ist,
                    "Anlık Durum": durum_gosterim,
                    "Aktif İş": veri["id"] if veri["id"] else "-",
                    "Bekleyen İş": toplam_kuyruk,
                    "Adet": f"{veri['current_qty']}/{veri['target_qty']}" if veri["id"] else "-",
                    "Çalışma": format_dk_sn(w_time),
                    "Toplam Duruş": format_dk_sn(b_time),
                    "Anlık Mola Süresi": format_dk_sn(anlik_mola) if anlik_mola > 0 else "-",
                    "İş Bekleme": format_dk_sn(i_time)
                })
            
            st.dataframe(pd.DataFrame(tablo_verisi), use_container_width=True)
            st.divider()
            
            st.subheader("⏱️ İstasyon Süre Dağılımları (Darboğaz Analizi)")
            pie_c1, pie_c2, pie_c3 = st.columns(3)
            
            for index, ist in enumerate(["Montaj-1", "Montaj-2", "Montaj-3"]):
                with [pie_c1, pie_c2, pie_c3][index]:
                    v = db["stations"][ist]
                    wt = get_live_work_time(ist)
                    bt = v.get("break_time", 0.0) + (time.time() - v["last_break_start"] if (v["status"] in ["Mola", "Boşta Mola"] and v.get("last_break_start")) else 0.0)
                    qt = v.get("qc_wait_time", 0.0) + (time.time() - v["qc_req_time"] if v.get("qc_req_time") else 0.0)
                    it = get_live_idle_time(ist)
                    
                    if (wt + bt + qt + it) > 0:
                        df_pie = pd.DataFrame({
                            "Kategori": ["Çalışma", "Duruş/Mola", "Kalite Bekleme", "İş Emri Bekleme"],
                            "Süre": [wt, bt, qt, it]
                        })
                        fig = px.pie(df_pie, values="Süre", names="Kategori", title=f"{ist}", hole=0.3,
                                     color="Kategori", color_discrete_map={
                                         "Çalışma": "#28a745", "Duruş/Mola": "#dc3545", 
                                         "Kalite Bekleme": "#ffc107", "İş Emri Bekleme": "#6c757d"
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
                    
                    if is_urgent:
                        hedef_veri["pending_urgent_job"] = {
                            "id": wo_id, "sn": sn_id, "target_qty": hedef_sayi,
                            "current_qty": 1, "step": 1, "work_time": 0.0, "break_time": 0.0, "qc_wait_time": 0.0
                        }
                        hedef_veri["urgent_alert"] = True
                        st.success(f"Acil İş Emri {hedef_istasyon} personeline bildirildi!")
                    else:
                        hedef_veri["pending_jobs"].append({
                            "id": wo_id, "sn": sn_id, "target_qty": hedef_sayi,
                            "current_qty": 1, "step": 1, "work_time": 0.0, "break_time": 0.0, "qc_wait_time": 0.0
                        })
                        st.success(f"İş Emri {hedef_istasyon} personeline onaya gönderildi.")
                    
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
                        ist["suspended_jobs"].append({
                            "id": ist["id"], "sn": ist["sn"], "target_qty": ist["target_qty"],
                            "current_qty": ist["current_qty"], "step": ist["step"], 
                            "work_time": ist["work_time"], "break_time": ist["break_time"], "qc_wait_time": ist["qc_wait_time"]
                        })
                    
                    p = ist["pending_urgent_job"]
                    ist["id"], ist["sn"], ist["target_qty"] = p["id"], p["sn"], p["target_qty"]
                    ist["current_qty"], ist["step"] = 1, 1
                    ist["work_time"], ist["break_time"], ist["qc_wait_time"] = 0.0, 0.0, 0.0
                    ist["status"] = "Çalışıyor"
                    ist["last_work_start"] = time.time()
                    
                    ist["urgent_alert"] = False
                    ist["pending_urgent_job"] = None
                    save_db(db)
                    st.rerun()
            with c2:
                if st.button("⏳ MEVCUT İŞİME DEVAM ET (Acil İşi Onay Kutusuna At)", use_container_width=True):
                    ist["urgent_alert"] = False
                    ist["pending_jobs"].append(ist["pending_urgent_job"])
                    ist["pending_urgent_job"] = None
                    save_db(db)
                    st.rerun()
                
        # 2. NORMAL AKIŞ 
        else:
            # Gelen (Onay Bekleyen) İşler
            if len(ist.get("pending_jobs", [])) > 0:
                st.warning(f"📩 Yöneticiden gelen onay bekleyen {len(ist['pending_jobs'])} iş emriniz var!")
                for idx, pj in enumerate(ist["pending_jobs"]):
                    col_p1, col_p2 = st.columns([4, 1])
                    col_p1.write(f"**İş Emri:** {pj['id']} | **Ürün:** {pj['sn']} | **Adet:** {pj['target_qty']}")
                    if col_p2.button("Kabul Et ve Sıraya Al", key=f"accept_{idx}", use_container_width=True):
                        ist["job_queue"].append(pj)
                        ist["pending_jobs"].pop(idx)
                        save_db(db)
                        st.rerun()
                st.divider()

            # Kuyruk ve Askıdaki İşlere Geçiş
            all_queued = ist.get("job_queue", []) + ist.get("suspended_jobs", [])
            if len(all_queued) > 0:
                with st.expander(f"📋 KUYRUKTAKİ VE ASKIDAKİ İŞLER ({len(all_queued)} Adet)"):
                    for idx, qj in enumerate(ist.get("job_queue", [])):
                        col_q1, col_q2 = st.columns([4, 1])
                        col_q1.write(f"*(Sırada)* **İş Emri:** {qj['id']} | **Adet:** {qj['target_qty']}")
                        if col_q2.button("Buna Geçiş Yap", key=f"sw_q_{idx}"):
                            if ist["id"] != "":
                                stop_timers(ist)
                                ist["suspended_jobs"].append({
                                    "id": ist["id"], "sn": ist["sn"], "target_qty": ist["target_qty"],
                                    "current_qty": ist["current_qty"], "step": ist["step"], 
                                    "work_time": ist["work_time"], "break_time": ist["break_time"], "qc_wait_time": ist["qc_wait_time"]
                                })
                            nj = ist["job_queue"].pop(idx)
                            ist["id"], ist["sn"], ist["target_qty"] = nj["id"], nj["sn"], nj["target_qty"]
                            ist["current_qty"], ist["step"] = nj["current_qty"], nj["step"]
                            ist["work_time"], ist["break_time"], ist["qc_wait_time"] = nj["work_time"], nj["break_time"], nj["qc_wait_time"]
                            ist["status"] = "Çalışıyor"
                            ist["last_work_start"] = time.time()
                            save_db(db)
                            st.rerun()
                            
                    for idx, sj in enumerate(ist.get("suspended_jobs", [])):
                        col_s1, col_s2 = st.columns([4, 1])
                        col_s1.write(f"*(Askıda)* **İş Emri:** {sj['id']} | **Kaldığı Adım:** {sj['step']}")
                        if col_s2.button("Devam Et", key=f"sw_s_{idx}"):
                            if ist["id"] != "":
                                stop_timers(ist)
                                ist["suspended_jobs"].append({
                                    "id": ist["id"], "sn": ist["sn"], "target_qty": ist["target_qty"],
                                    "current_qty": ist["current_qty"], "step": ist["step"], 
                                    "work_time": ist["work_time"], "break_time": ist["break_time"], "qc_wait_time": ist["qc_wait_time"]
                                })
                            nsj = ist["suspended_jobs"].pop(idx)
                            ist["id"], ist["sn"], ist["target_qty"] = nsj["id"], nsj["sn"], nsj["target_qty"]
                            ist["current_qty"], ist["step"] = nsj["current_qty"], nsj["step"]
                            ist["work_time"], ist["break_time"], ist["qc_wait_time"] = nsj["work_time"], nsj["break_time"], nsj["qc_wait_time"]
                            ist["status"] = "Duraklatıldı"
                            ist["last_work_start"] = None
                            save_db(db)
                            st.rerun()

            # --- SÜRE VE BİLGİ ALANI (ÇİFT SAYAÇ JS) ---
            if durum not in ["Bekliyor", "Boşta Mola", "Tamamlandı"]:
                with st.container(border=True):
                    col_i1, col_i2, col_i3 = st.columns([2,1,2])
                    col_i1.metric("📦 Ürün / İş Emri", f"{ist['sn']} | {ist['id']}")
                    col_i2.metric("🎯 İlerleme", f"{ist['current_qty']} / {ist['target_qty']}")
                    
                    with col_i3:
                        is_active_w = "true" if durum == "Çalışıyor" else "false"
                        is_active_b = "true" if durum in ["Mola", "Boşta Mola"] else "false"
                        
                        b_time = ist.get("break_time", 0.0)
                        if durum in ["Mola", "Boşta Mola"] and ist.get("last_break_start"):
                            b_time += time.time() - ist["last_break_start"]
                            
                        components.html(
                            f"""
                            <div style="font-family: 'Helvetica Neue', sans-serif; display: flex; gap: 15px; justify-content: center;">
                                <div style="text-align: center;">
                                    <div style="font-size: 14px; color: #555; margin-bottom: 5px;">⏱️ Çalışma</div>
                                    <div id="w_timer" style="font-size: 26px; font-weight: bold; color: #d9534f; background: #ffebeb; padding: 5px 10px; border-radius: 10px;">
                                        00:00:00
                                    </div>
                                </div>
                                <div style="text-align: center;">
                                    <div style="font-size: 14px; color: #555; margin-bottom: 5px;">☕ Mola</div>
                                    <div id="b_timer" style="font-size: 26px; font-weight: bold; color: #856404; background: #fff3cd; padding: 5px 10px; border-radius: 10px;">
                                        00:00:00
                                    </div>
                                </div>
                            </div>
                            <script>
                                var wSec = {int(get_live_work_time(aktif_rol))};
                                var bSec = {int(b_time)};
                                var wAct = {is_active_w};
                                var bAct = {is_active_b};
                                function fT(s) {{
                                    var h = Math.floor(s/3600).toString().padStart(2,'0');
                                    var m = Math.floor((s%3600)/60).toString().padStart(2,'0');
                                    var sec = Math.floor(s%60).toString().padStart(2,'0');
                                    return h+":"+m+":"+sec;
                                }}
                                document.getElementById('w_timer').innerHTML = fT(wSec);
                                document.getElementById('b_timer').innerHTML = fT(bSec);
                                setInterval(function(){{
                                    if(wAct){{ wSec++; document.getElementById('w_timer').innerHTML = fT(wSec); }}
                                    if(bAct){{ bSec++; document.getElementById('b_timer').innerHTML = fT(bSec); }}
                                }}, 1000);
                            </script>
                            """,
                            height=80
                        )
                st.markdown("<br>", unsafe_allow_html=True)
            
            if durum == "Bekliyor" or durum == "Boşta Mola":
                if durum == "Bekliyor":
                    st.markdown("<div class='kiosk-card'><div class='kiosk-title'>☕ BEKLEMEDE</div><div class='kiosk-subtitle'>Yeni iş emri bekleniyor...</div></div>", unsafe_allow_html=True)
                    
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
                        stop_timers(ist)
                        ist["status"] = "Bekliyor"
                        ist["last_idle_start"] = time.time()
                        ist["break_reason"] = ""
                        save_db(db)
                        st.rerun()

            elif durum == "Tamamlandı":
                st.markdown("<div class='kiosk-card' style='border: 3px solid #28a745;'><div class='kiosk-title' style='color:#28a745;'>✅ İŞ BİTTİ</div><div class='kiosk-subtitle'>Yöneticiye bilgi verildi. Yeni görev bekleniyor.</div></div>", unsafe_allow_html=True)

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
                            
                            ist["id"], ist["sn"], ist["target_qty"], ist["current_qty"], ist["work_time"], ist["break_time"], ist["qc_wait_time"] = "", "", 0, 0, 0.0, 0.0, 0.0
                            
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
            
    if canli_mod:
        time.sleep(3)
        st.rerun()
