import streamlit as st
import pandas as pd
import time
import json
import os
import base64
import plotly.express as px
from datetime import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Dijital Sis Kanban", layout="wide", initial_sidebar_state="collapsed")

# --- KANBAN ÖZEL TASARIM (CSS) ---
st.markdown("""
    <style>
    /* Üst boşluğu azalt ve modern font kullan */
    .block-container { padding-top: 2rem; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    /* Kanban Sütun Başlıkları */
    h3 { text-align: center; color: #555; font-weight: 600; padding-bottom: 10px; border-bottom: 2px solid #eee; }
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
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4)
            
    return db

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

db = load_db()

# --- OTURUM YÖNETİMİ VE HESAPLAR ---
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
    st.markdown("<h1 style='text-align: center; font-size: 50px; color: #333;'>DİJİTAL SİS KANBAN</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.container(border=True):
            st.subheader("🔑 Giriş Yap")
            user_input = st.text_input("Kullanıcı Adı")
            pass_input = st.text_input("Şifre", type="password")
            if st.button("GİRİŞ YAP", type="primary", use_container_width=True):
                login(user_input, pass_input)

# --- SİSTEM UYGULAMASI ---
else:
    aktif_rol = st.session_state.role
    canli_mod = False
    
    with st.sidebar:
        st.markdown(f"<h2>👤 {aktif_rol}</h2>", unsafe_allow_html=True)
        st.divider()
        if aktif_rol in ["Yönetici", "Kalite"]:
            canli_mod = st.checkbox("🟢 Canlı İzleme", value=True)
        elif aktif_rol in ["Montaj-1", "Montaj-2", "Montaj-3"]:
            if db["stations"][aktif_rol]["status"] in ["Bekliyor", "Onay Bekliyor", "Tamamlandı"]:
                canli_mod = st.checkbox("🟢 Sistem Takibi", value=True)
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            logout()

    # ---------------------------------------------------------
    # YÖNETİCİ EKRANI
    # ---------------------------------------------------------
    if aktif_rol == "Yönetici":
        st.title("Yönetici Kanban Panosu")
        
        tamamlanan_istasyonlar = [ist for ist, veri in db["stations"].items() if veri["status"] == "Tamamlandı"]
        if tamamlanan_istasyonlar:
            st.success(f"🎉 **{', '.join(tamamlanan_istasyonlar)}** iş emrini tamamladı. Yeni iş bekliyor.")

        tab1, tab2, tab3 = st.tabs(["📊 Canlı Üretim Panosu", "🚀 İş Emri Ata", "⚠️ Hata Kayıtları"])
        
        with tab1:
            c1, c2, c3 = st.columns(3)
            istasyonlar = ["Montaj-1", "Montaj-2", "Montaj-3"]
            
            for index, istasyon in enumerate(istasyonlar):
                with [c1, c2, c3][index]:
                    with st.container(border=True):
                        veri = db["stations"][istasyon]
                        st.markdown(f"<h2 style='text-align:center;'>{istasyon}</h2>", unsafe_allow_html=True)
                        
                        if veri["status"] == "Bekliyor":
                            st.info("🟡 BOŞTA / BEKLİYOR")
                        elif veri["status"] == "Onay Bekliyor":
                            st.warning("🟠 PERSONEL ONAYI BEKLENİYOR")
                        elif veri["status"] == "Tamamlandı":
                            st.success("✅ İŞ BİTTİ")
                        else:
                            st.metric("Üretim İlerlemesi", f"{veri['current_qty']} / {veri['target_qty']}")
                            st.markdown(f"**Durum:** {veri['status']}")
                            st.markdown(f"**İş Emri:** {veri['id']}")
                            st.markdown(f"**Süre:** {format_time(get_live_work_time(istasyon))}")
                            if st.button(f"🚨 DURDUR", key=f"dur_{istasyon}", use_container_width=True):
                                if veri["status"] == "Çalışıyor" and veri["last_work_start"]:
                                    veri["work_time"] += time.time() - veri["last_work_start"]
                                    veri["last_work_start"] = None
                                veri["status"] = "Duraklatıldı"
                                save_db(db)
                                st.rerun()
                                
            st.divider()
            grafik_col1, grafik_col2 = st.columns(2)
            
            with grafik_col1:
                df_uretim = pd.DataFrame([{"İstasyon": ist, "Üretim": db["performance"][ist]["toplam_uretilen_parca"]} for ist in istasyonlar])
                fig_uretim = px.bar(df_uretim, x="İstasyon", y="Üretim", text="Üretim", title="Toplam Üretim")
                st.plotly_chart(fig_uretim, use_container_width=True)
                
            with grafik_col2:
                qc_df = pd.DataFrame(db["qc_logs"])
                if not qc_df.empty:
                    ortalama_qc = qc_df.groupby("İstasyon", as_index=False)["Bekleme_Suresi_Sn"].mean().round(1)
                    fig_qc = px.bar(ortalama_qc, x="İstasyon", y="Bekleme_Suresi_Sn", text="Bekleme_Suresi_Sn", title="Ort. Kalite Bekleme (Sn)", color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig_qc, use_container_width=True)
                else:
                    st.info("Kalite onayı ölçümü bulunmuyor.")

        with tab2:
            with st.container(border=True):
                st.subheader("Yeni İş Kartı Oluştur")
                col_is_1, col_is_2 = st.columns(2)
                with col_is_1:
                    hedef_istasyon = st.selectbox("İstasyon Seçin:", ["Montaj-1", "Montaj-2", "Montaj-3"])
                    wo_id = st.text_input("İş Emri:", value="WO-2024-100")
                    sn_id = st.text_input("Seri No:", value="SN-123456")
                    hedef_sayi = st.number_input("Hedef Adet:", min_value=1, value=50)
                    if st.button("🚀 İş Kartını Gönder", type="primary", use_container_width=True):
                        db["stations"][hedef_istasyon] = {
                            "status": "Onay Bekliyor", "id": wo_id, "sn": sn_id, "target_qty": hedef_sayi,
                            "current_qty": 1, "step": 1, "work_time": 0.0, "break_time": 0.0,
                            "last_work_start": None, "last_break_start": None, "qc_req_time": None, "break_reason": ""
                        }
                        save_db(db)
                        st.success(f"{hedef_istasyon} panosuna iş kartı eklendi.")
                        st.rerun()

        with tab3:
            if len(db["errors"]) > 0:
                for hata in reversed(db["errors"]):
                    with st.container(border=True):
                        st.markdown(f"**{hata['İstasyon']}** | {hata['Tarih/Saat']} | Adım: {hata['Hatali_Adim']}")
                        st.write(f"**Bölge:** {hata['Bölge']} | **Açıklama:** {hata['Açıklama']}")
                        if hata.get("Foto_Base64"):
                            st.image(base64.b64decode(hata["Foto_Base64"]), width=300)
            else:
                st.write("Hata kaydı yok.")

    # ---------------------------------------------------------
    # İSTASYON EKRANI (KANBAN GÖRÜNÜMÜ)
    # ---------------------------------------------------------
    elif aktif_rol in ["Montaj-1", "Montaj-2", "Montaj-3"]:
        istasyon_verisi = db["stations"][aktif_rol]
        durum = istasyon_verisi["status"]
        
        # Pano Başlığı
        st.markdown(f"<h1 style='text-align: center; color: #333;'>{aktif_rol} PANOSU</h1>", unsafe_allow_html=True)
        
        if durum == "Bekliyor":
            st.info("Yöneticiden iş kartı bekleniyor...")
        
        elif durum == "Tamamlandı":
            st.success("Tüm hedefler tamamlandı. Yeni iş kartı bekleniyor...")

        elif durum == "Onay Bekliyor":
            with st.container(border=True):
                st.markdown(f"<h2 style='text-align:center;'>YENİ GÖREV: {istasyon_verisi['id']}</h2>", unsafe_allow_html=True)
                st.markdown(f"<h4 style='text-align:center;'>Ürün: {istasyon_verisi['sn']} | Hedef: {istasyon_verisi['target_qty']} Adet</h4>", unsafe_allow_html=True)
                if st.button("✅ İŞİ KABUL ET VE BAŞLA", type="primary", use_container_width=True):
                    istasyon_verisi["status"] = "Çalışıyor"
                    istasyon_verisi["last_work_start"] = time.time()
                    save_db(db)
                    st.rerun()
                    
        else:
            # ÜST BİLGİ KARTI
            col_info, col_btn1, col_btn2 = st.columns([2,1,1])
            with col_info:
                st.markdown(f"**İş Emri:** {istasyon_verisi['id']} | **Ürün:** {istasyon_verisi['sn']} | **Adet:** {istasyon_verisi['current_qty']}/{istasyon_verisi['target_qty']} | ⏱️ {format_time(get_live_work_time(aktif_rol))}")
            
            with col_btn1:
                if durum == "Duraklatıldı":
                    if st.button("▶️ DEVAM ET", use_container_width=True, type="primary"):
                        istasyon_verisi["last_work_start"] = time.time()
                        istasyon_verisi["status"] = "Çalışıyor"
                        save_db(db)
                        st.rerun()
                elif durum == "Çalışıyor":
                    if st.button("⏸️ DURAKLAT", use_container_width=True):
                        if istasyon_verisi["last_work_start"]:
                            istasyon_verisi["work_time"] += time.time() - istasyon_verisi["last_work_start"]
                            istasyon_verisi["last_work_start"] = None
                        istasyon_verisi["status"] = "Duraklatıldı"
                        save_db(db)
                        st.rerun()
            with col_btn2:
                with st.popover("☕ DURUŞ BİLDİR"):
                    if durum != "Mola":
                        mola_sebebi = st.selectbox("Duruş Sebebi:", ["Yemek", "Çay", "Parça Bekleme", "Arıza", "Diğer"])
                        if st.button("Duruşa Geç"):
                            if istasyon_verisi["status"] == "Çalışıyor" and istasyon_verisi["last_work_start"]:
                                istasyon_verisi["work_time"] += time.time() - istasyon_verisi["last_work_start"]
                                istasyon_verisi["last_work_start"] = None
                            istasyon_verisi["last_break_start"] = time.time()
                            istasyon_verisi["break_reason"] = mola_sebebi
                            istasyon_verisi["status"] = "Mola"
                            save_db(db)
                            st.rerun()
                    else:
                        st.warning(f"Durum: {istasyon_verisi['break_reason']}")
                        if st.button("Duruşu Bitir (Duraklat)"):
                            istasyon_verisi["last_break_start"] = None
                            istasyon_verisi["status"] = "Duraklatıldı"
                            istasyon_verisi["break_reason"] = ""
                            save_db(db)
                            st.rerun()

            st.divider()

            # KANBAN SÜTUNLARI
            step = istasyon_verisi["step"]
            col_todo, col_doing, col_done = st.columns(3)
            
            adımlar = [
                "Adım 1: Vida Sıkma (2.5 Nm)",
                "Adım 2: Kablo Bağlantısı",
                "Adım 3: Kalite Kontrol",
                "Adım 4: Kapatma"
            ]

            # 1. BEKLEYENLER SÜTUNU
            with col_todo:
                st.markdown("### 📋 Yapılacaklar")
                for i in range(step, len(adımlar)):
                    with st.container(border=True):
                        st.markdown(f"<div style='color:#999;'>{adımlar[i]}</div>", unsafe_allow_html=True)

            # 2. AKTİF İŞLEM SÜTUNU (Büyük Odak)
            with col_doing:
                st.markdown("### ⚡ Aktif İşlem")
                if durum == "Çalışıyor":
                    if step <= 4:
                        with st.container(border=True):
                            st.markdown(f"<h4 style='text-align:center; color:#0056b3;'>{adımlar[step-1]}</h4>", unsafe_allow_html=True)
                            
                            if step == 3:
                                st.error("KALİTE ONAYI BEKLENİYOR")
                                qc_pass = st.text_input("Şifre:", type="password")
                                if st.button("ONAYLA", use_container_width=True):
                                    if qc_pass == USERS["kalite1"]["pass"]:
                                        if istasyon_verisi.get("qc_req_time"):
                                            db["qc_logs"].append({
                                                "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                                "İstasyon": aktif_rol,
                                                "Bekleme_Suresi_Sn": int(time.time() - istasyon_verisi["qc_req_time"])
                                            })
                                        istasyon_verisi["step"] += 1
                                        istasyon_verisi["qc_req_time"] = None
                                        save_db(db)
                                        st.rerun()
                            else:
                                if st.button("✅ TAMAMLA", type="primary", use_container_width=True):
                                    if step == 2: # 2'den 3'e (Kaliteye) geçerken süreyi başlat
                                        istasyon_verisi["qc_req_time"] = time.time()
                                    istasyon_verisi["step"] += 1
                                    save_db(db)
                                    st.rerun()
                                    
                            with st.popover("⚠️ Hata Bildir", use_container_width=True):
                                hata_bolgesi = st.selectbox("Bölge:", ["Ön", "Arka", "Yan", "İç"])
                                hata_aciklama = st.text_area("Açıklama:")
                                if st.button("Gönder"):
                                    db["errors"].append({
                                        "Tarih/Saat": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "İstasyon": aktif_rol,
                                        "İş Emri": istasyon_verisi['id'],
                                        "Hatali_Adim": adımlar[step-1],
                                        "Bölge": hata_bolgesi,
                                        "Açıklama": hata_aciklama
                                    })
                                    save_db(db)
                                    st.success("İletildi!")
                    elif step > 4:
                        with st.container(border=True):
                            st.success("TÜM ADIMLAR BİTTİ")
                            if st.button("📦 SIRADAKİ PARÇAYI AL", type="primary", use_container_width=True):
                                db["performance"][aktif_rol]["toplam_uretilen_parca"] += 1
                                if istasyon_verisi["current_qty"] < istasyon_verisi["target_qty"]:
                                    istasyon_verisi["current_qty"] += 1
                                    istasyon_verisi["step"] = 1
                                else:
                                    if istasyon_verisi["last_work_start"]:
                                        istasyon_verisi["work_time"] += time.time() - istasyon_verisi["last_work_start"]
                                        istasyon_verisi["last_work_start"] = None
                                    istasyon_verisi["status"] = "Tamamlandı"
                                    db["performance"][aktif_rol]["tamamlanan_is_emri"] += 1
                                save_db(db)
                                st.rerun()
                else:
                    st.warning("Adımı görmek için DEVAM ET butonuna basınız.")

            # 3. TAMAMLANANLAR SÜTUNU
            with col_done:
                st.markdown("### ✅ Bitenler")
                for i in range(min(step-1, 4)):
                    with st.container(border=True):
                        st.markdown(f"<div style='color:green;'>✔️ {adımlar[i]}</div>", unsafe_allow_html=True)
                        
    # ---------------------------------------------------------
    # KALİTE EKRANI
    # ---------------------------------------------------------
    elif aktif_rol == "Kalite":
        st.title("Kalite Kanban Panosu")
        
        bekleyenler = [s for s, v in db["stations"].items() if v["step"] == 3 and v["status"] == "Çalışıyor"]
        
        with st.container(border=True):
            st.subheader("Kalite Onayı Bekleyen İşler")
            if bekleyenler:
                for b in bekleyenler:
                    st.error(f"🚨 {b} istasyonunda kalite onayı bekleniyor!")
            else:
                st.success("✅ Bekleyen kalite onayı yok.")
                
    if canli_mod:
        time.sleep(3)
        st.rerun()
