import streamlit as st
import pandas as pd
import time
import json
import os
import base64
import plotly.express as px
from datetime import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Dijital Sis Arayüzü", layout="wide")

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
        
    # Eski JSON dosyasındaki eksik anahtarları otomatik tamamla
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

# --- OTURUM YÖNETİMİ ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

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

# --- GİRİŞ EKRANI ---
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; font-size: 50px; color: #333;'>DİJİTAL SİS</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            st.subheader("Sisteme Giriş Yapın")
            user_input = st.text_input("Kullanıcı Adı")
            pass_input = st.text_input("Şifre", type="password")
            if st.form_submit_button("GİRİŞ YAP", use_container_width=True):
                login(user_input, pass_input)

# --- SİSTEM UYGULAMASI ---
else:
    aktif_rol = st.session_state.role
    canli_mod = False
    
    with st.sidebar:
        st.markdown(f"<h2>👤 {aktif_rol}</h2>", unsafe_allow_html=True)
        st.divider()
        
        if aktif_rol in ["Yönetici", "Kalite"]:
            canli_mod = st.checkbox("🟢 Canlı İzleme (Oto-Yenile)", value=True)
            if canli_mod:
                st.info("💡 İşlem yaparken sayfanın yenilenmemesi için bu modu geçici kapatabilirsiniz.")
        elif aktif_rol in ["Montaj-1", "Montaj-2", "Montaj-3"]:
            durum_kontrol = db["stations"][aktif_rol]["status"]
            if durum_kontrol in ["Bekliyor", "Onay Bekliyor", "Tamamlandı"]:
                canli_mod = st.checkbox("🟢 Sistem Takibi (Oto-Yenile)", value=True)

        if st.button("🚪 Çıkış Yap", use_container_width=True):
            logout()

    # ---------------------------------------------------------
    # YÖNETİCİ EKRANI
    # ---------------------------------------------------------
    if aktif_rol == "Yönetici":
        st.title("Yönetici Kontrol Paneli")
        
        # Tamamlanan iş var mı kontrolü
        tamamlanan_istasyonlar = [ist for ist, veri in db["stations"].items() if veri["status"] == "Tamamlandı"]
        if tamamlanan_istasyonlar:
            st.success(f"🎉 DİKKAT: **{', '.join(tamamlanan_istasyonlar)}** istasyon(lar)ı mevcut iş emrini tamamladı! Yeni iş emri bekliyorlar.")

        tab1, tab2, tab3 = st.tabs(["📊 Canlı İzleme & Performans", "🚀 İş Emri Gönder", "⚠️ Hata Kayıtları"])
        
        with tab1:
            c1, c2, c3 = st.columns(3)
            istasyonlar = ["Montaj-1", "Montaj-2", "Montaj-3"]
            
            for index, istasyon in enumerate(istasyonlar):
                with [c1, c2, c3][index]:
                    veri = db["stations"][istasyon]
                    st.markdown(f"<h2 style='text-align:center;'>{istasyon}</h2>", unsafe_allow_html=True)
                    
                    if veri["status"] == "Bekliyor":
                        st.info("🟡 BOŞTA / BEKLİYOR")
                    elif veri["status"] == "Onay Bekliyor":
                        st.warning("🟠 PERSONEL ONAYI BEKLENİYOR")
                    elif veri["status"] == "Tamamlandı":
                        st.success("✅ İŞ BİTTİ (YENİ İŞ BEKLİYOR)")
                    else:
                        renk = "green" if veri["status"] == "Çalışıyor" else "red"
                        st.markdown(f"<h3 style='text-align:center; color:{renk};'>{veri['status'].upper()}</h3>", unsafe_allow_html=True)
                        if veri["status"] == "Mola":
                            st.write(f"*(Sebep: {veri.get('break_reason', 'Belirtilmedi')})*")
                            
                        st.metric("Üretim", f"{veri['current_qty']} / {veri['target_qty']}")
                        st.write(f"**İş Emri:** {veri['id']}")
                        st.write(f"**Süre:** {format_time(get_live_work_time(istasyon))}")
                        
                        if st.button(f"🚨 DURDUR", key=f"dur_{istasyon}", use_container_width=True):
                            if veri["status"] == "Çalışıyor" and veri["last_work_start"]:
                                veri["work_time"] += time.time() - veri["last_work_start"]
                                veri["last_work_start"] = None
                            veri["status"] = "Duraklatıldı"
                            save_db(db)
                            st.rerun()
                            
            st.divider()
            st.subheader("📈 Günlük & Genel Grafik Analizleri")
            
            grafik_col1, grafik_col2 = st.columns(2)
            
            with grafik_col1:
                # Plotly Üretim Grafiği
                df_uretim = pd.DataFrame([
                    {"İstasyon": ist, "Üretim (Adet)": db["performance"][ist]["toplam_uretilen_parca"]} 
                    for ist in istasyonlar
                ])
                fig_uretim = px.bar(df_uretim, x="İstasyon", y="Üretim (Adet)", text="Üretim (Adet)", 
                                    color="İstasyon", title="İstasyon Bazlı Toplam Üretim")
                fig_uretim.update_traces(textposition='outside')
                st.plotly_chart(fig_uretim, use_container_width=True)
                
            with grafik_col2:
                # Plotly Kalite Bekleme Grafiği
                qc_df = pd.DataFrame(db["qc_logs"])
                if not qc_df.empty:
                    ortalama_qc = qc_df.groupby("İstasyon", as_index=False)["Bekleme_Suresi_Sn"].mean()
                    ortalama_qc["Bekleme_Suresi_Sn"] = ortalama_qc["Bekleme_Suresi_Sn"].round(1)
                    
                    fig_qc = px.bar(ortalama_qc, x="İstasyon", y="Bekleme_Suresi_Sn", text="Bekleme_Suresi_Sn",
                                    color="İstasyon", title="Ortalama Kalite Onayı Bekleme Süresi (Saniye)",
                                    color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig_qc.update_traces(textposition='outside')
                    st.plotly_chart(fig_qc, use_container_width=True)
                else:
                    st.info("Henüz kalite onayı ölçümü bulunmuyor.")

        with tab2:
            st.subheader("Yeni İş Emri Gönder")
            col_is_1, col_is_2 = st.columns(2)
            with col_is_1:
                hedef_istasyon = st.selectbox("Gönderilecek İstasyon:", ["Montaj-1", "Montaj-2", "Montaj-3"])
                wo_id = st.text_input("İş Emri Numarası:", value="WO-2024-100")
                sn_id = st.text_input("Ürün Seri Numarası (Başlangıç):", value="SN-123456")
                hedef_sayi = st.number_input("Üretilecek Adet (Hedef):", min_value=1, value=50)
                
                if st.button("🚀 İş Emrini Gönder (Onay Bekler)", type="primary", use_container_width=True):
                    db["stations"][hedef_istasyon] = {
                        "status": "Onay Bekliyor", "id": wo_id, "sn": sn_id, "target_qty": hedef_sayi,
                        "current_qty": 1, "step": 1, "work_time": 0.0, "break_time": 0.0,
                        "last_work_start": None, "last_break_start": None, "qc_req_time": None, "break_reason": ""
                    }
                    save_db(db)
                    st.success(f"İş emri {hedef_istasyon} istasyonuna gönderildi. Personel kabul ettiğinde üretim başlayacak!")
                    st.rerun()

        with tab3:
            st.subheader("Bildirilen Hatalar ve Fotoğraflar")
            if len(db["errors"]) > 0:
                for hata in reversed(db["errors"]):
                    with st.expander(f"⚠️ {hata['Tarih/Saat']} - {hata['İstasyon']} (İş Emri: {hata['İş Emri']})"):
                        st.write(f"**Montaj Dönemi:** {hata['Montaj_Donemi']} | **Adım:** {hata['Hatali_Adim']} | **Bölge:** {hata['Bölge']}")
                        if hata['Onceden_Hatali']:
                            st.error("🚨 Parça istasyona önceden hatalı gelmiş!")
                        st.write(f"**Açıklama:** {hata['Açıklama']}")
                        if hata.get("Foto_Base64"):
                            try:
                                img_data = base64.b64decode(hata["Foto_Base64"])
                                st.image(img_data, width=400)
                            except:
                                st.warning("Görsel yüklenemedi.")
            else:
                st.write("Kayıtlı hata bulunmuyor.")

    # ---------------------------------------------------------
    # KALİTE EKRANI
    # ---------------------------------------------------------
    elif aktif_rol == "Kalite":
        st.title("🔍 Kalite Kontrol Merkezi")
        
        bekleyenler = [s for s, v in db["stations"].items() if v["step"] == 3 and v["status"] == "Çalışıyor"]
        
        if bekleyenler:
            st.markdown("<div style='padding: 20px; background-color: #ff4b4b; color: white; border-radius: 10px; font-size: 24px; text-align: center;'>"
                        f"🚨 ACİL ONAY BEKLEYEN İSTASYONLAR:<br><b>{', '.join(bekleyenler)}</b></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='padding: 20px; background-color: #00cc66; color: white; border-radius: 10px; font-size: 24px; text-align: center;'>"
                        "✅ ONAY BEKLEYEN İSTASYON YOK</div>", unsafe_allow_html=True)
            
        st.divider()
        st.subheader("Sahadaki Hata Bildirimleri")
        if len(db["errors"]) > 0:
            for hata in reversed(db["errors"]):
                with st.expander(f"⚠️ {hata['Tarih/Saat']} - {hata['İstasyon']}"):
                    st.write(f"**Bölge:** {hata['Bölge']} | **Açıklama:** {hata['Açıklama']}")
                    if hata['Onceden_Hatali']: 
                        st.error("🚨 Parça önceden hatalı.")
                    if hata.get("Foto_Base64"):
                        st.image(base64.b64decode(hata["Foto_Base64"]), width=300)

    # ---------------------------------------------------------
    # İSTASYON EKRANI
    # ---------------------------------------------------------
    elif aktif_rol in ["Montaj-1", "Montaj-2", "Montaj-3"]:
        istasyon_verisi = db["stations"][aktif_rol]
        durum = istasyon_verisi["status"]
        
        if durum == "Bekliyor":
            st.markdown("<br><br><h1 style='text-align: center; color: #ffcc00; font-size: 50px;'>⏳ YÖNETİCİDEN İŞ EMRİ BEKLENİYOR...</h1>", unsafe_allow_html=True)
        
        elif durum == "Tamamlandı":
            st.markdown("<br><br><h1 style='text-align: center; color: #00cc66; font-size: 50px;'>🎉 İŞ EMRİ TAMAMLANDI!</h1>", unsafe_allow_html=True)
            st.markdown("<h3 style='text-align: center; color: #555;'>Yöneticiye bilgi verildi. Yeni iş emri ataması bekleniyor...</h3>", unsafe_allow_html=True)

        elif durum == "Onay Bekliyor":
            st.markdown(f"<div style='background-color: #ffe6cc; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #ff9900;'>"
                        f"<h1 style='color: #ff9900; font-size: 40px;'>YENİ İŞ EMRİ GELDİ!</h1>"
                        f"<h2>İş Emri: {istasyon_verisi['id']} | Ürün: {istasyon_verisi['sn']} | Hedef: {istasyon_verisi['target_qty']} Adet</h2>"
                        f"</div><br>", unsafe_allow_html=True)
            
            col_b1, col_b2, col_b3 = st.columns([1,2,1])
            with col_b2:
                if st.button("✅ İŞİ KABUL ET VE ÜRETİME BAŞLA", type="primary", use_container_width=True):
                    istasyon_verisi["status"] = "Çalışıyor"
                    istasyon_verisi["last_work_start"] = time.time()
                    save_db(db)
                    st.rerun()
                    
        else:
            # Çalışıyor, Duraklatıldı, Mola modları
            st.markdown(f"<div style='background-color: #f0f2f6; padding: 10px; border-radius: 10px;'>"
                        f"<h1 style='text-align: center; color: #000; font-size: 45px;'>ÜRÜN: {istasyon_verisi['sn']}</h1>"
                        f"<h2 style='text-align: center; color: #555;'>Üretim No: {istasyon_verisi['current_qty']} / {istasyon_verisi['target_qty']}</h2>"
                        f"</div><br>", unsafe_allow_html=True)
            
            sol, orta, sag = st.columns([1, 2, 1.2])

            with sol:
                st.info(f"**İş Emri:** {istasyon_verisi['id']}")
                st.info(f"⏱️ **Çalışma:** {format_time(get_live_work_time(aktif_rol))}")
                
                if durum == "Duraklatıldı":
                    if st.button("▶️ İŞE DEVAM ET", use_container_width=True, type="primary"):
                        istasyon_verisi["last_work_start"] = time.time()
                        istasyon_verisi["status"] = "Çalışıyor"
                        save_db(db)
                        st.rerun()
                elif durum == "Çalışıyor":
                    if st.button("⏸️ İŞİ DURAKLAT", use_container_width=True):
                        if istasyon_verisi["last_work_start"]:
                            istasyon_verisi["work_time"] += time.time() - istasyon_verisi["last_work_start"]
                            istasyon_verisi["last_work_start"] = None
                        istasyon_verisi["status"] = "Duraklatıldı"
                        save_db(db)
                        st.rerun()

                st.divider()
                st.markdown("### ☕ Duruş / Mola İşlemleri")
                if durum != "Mola":
                    mola_sebebi = st.selectbox("Duruş Sebebi Seçiniz:", ["Mola (Yemek)", "Mola (Çay)", "Depodan Parça Temini", "Kalite Kontrol Beklemesi", "Diğer"])
                    if st.button("Duruşu Başlat", use_container_width=True):
                        if istasyon_verisi["status"] == "Çalışıyor" and istasyon_verisi["last_work_start"]:
                            istasyon_verisi["work_time"] += time.time() - istasyon_verisi["last_work_start"]
                            istasyon_verisi["last_work_start"] = None
                        istasyon_verisi["last_break_start"] = time.time()
                        istasyon_verisi["break_reason"] = mola_sebebi
                        istasyon_verisi["status"] = "Mola"
                        save_db(db)
                        st.rerun()
                else:
                    st.warning(f"Şu an **{istasyon_verisi['break_reason']}** sebebiyle duruştasınız.")
                    if st.button("Duruşu Bitir", use_container_width=True, type="primary"):
                        if istasyon_verisi["last_break_start"]:
                            istasyon_verisi["break_time"] += time.time() - istasyon_verisi["last_break_start"]
                            istasyon_verisi["last_break_start"] = None
                        
                        # Mola bitince hemen ÇALIŞIYOR olma, DURAKLATILDI ol. Kullanıcı hazır olunca İşe Devam Etsin.
                        istasyon_verisi["status"] = "Duraklatıldı"
                        istasyon_verisi["break_reason"] = ""
                        save_db(db)
                        st.rerun()

            with orta:
                st.markdown("### 📋 MONTAJ ADIMLARI")
                st.image("https://dummyimage.com/600x150/e0e0e0/000000.png&text=Yonetici+Tarafindan+Yuklenen+Montaj+Gorseli", use_container_width=True)

                if durum == "Çalışıyor":
                    step = istasyon_verisi["step"]
                    
                    st.markdown("---")
                    if st.checkbox("✅ Adım 1: Vida Sıkma (2.5 Nm)", value=(step > 1), disabled=(step != 1)) and step == 1:
                        istasyon_verisi["step"] = 2
                        save_db(db)
                        st.rerun()
                        
                    st.markdown("---")
                    if st.checkbox("✅ Adım 2: Kablo Bağlantısı", value=(step > 2), disabled=(step != 2)) and step == 2:
                        istasyon_verisi["step"] = 3
                        istasyon_verisi["qc_req_time"] = time.time()
                        save_db(db)
                        st.rerun()
                    
                    st.markdown("---")
                    if step == 3:
                        st.error("🔍 ZORUNLU KALİTE KONTROLÜ (Kalite Bekleniyor)")
                        qc_pass = st.text_input("Kalite Şifresi:", type="password")
                        if st.button("KALİTE ONAYI VER"):
                            if qc_pass == USERS["kalite1"]["pass"]:
                                if istasyon_verisi.get("qc_req_time"):
                                    gecen_sure = int(time.time() - istasyon_verisi["qc_req_time"])
                                    db["qc_logs"].append({
                                        "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                        "İstasyon": aktif_rol,
                                        "Bekleme_Suresi_Sn": gecen_sure
                                    })
                                
                                istasyon_verisi["step"] = 4
                                istasyon_verisi["qc_req_time"] = None
                                save_db(db)
                                st.rerun()
                            else:
                                st.error("Hatalı Şifre!")
                    elif step > 3:
                        st.checkbox("✅ Adım 3: Kalite Kontrol (ONAYLANDI)", value=True, disabled=True)
                    else:
                        st.checkbox("🔒 Adım 3: Kalite Kontrol (Kilitli)", value=False, disabled=True)
                        
                    st.markdown("---")
                    if st.checkbox("✅ Adım 4: Son Kontrol ve Kapatma", value=(step > 4), disabled=(step != 4)) and step == 4:
                        istasyon_verisi["step"] = 5
                        save_db(db)
                        st.rerun()
                        
                    if step > 4:
                        st.success("TÜM ADIMLAR TAMAMLANDI!")
                        if st.button("🚀 SIRADAKİ PARÇAYA GEÇ", type="primary", use_container_width=True):
                            db["performance"][aktif_rol]["toplam_uretilen_parca"] += 1
                            if istasyon_verisi["current_qty"] < istasyon_verisi["target_qty"]:
                                istasyon_verisi["current_qty"] += 1
                                istasyon_verisi["step"] = 1
                            else:
                                if istasyon_verisi["last_work_start"]:
                                    istasyon_verisi["work_time"] += time.time() - istasyon_verisi["last_work_start"]
                                    istasyon_verisi["last_work_start"] = None
                                
                                # Hedef bittiyse durum TAMAMLANDI olur
                                istasyon_verisi["status"] = "Tamamlandı"
                                db["performance"][aktif_rol]["tamamlanan_is_emri"] += 1
                            save_db(db)
                            st.rerun()
                else:
                    st.warning("Adımları görmek için İŞE DEVAM ET butonuna basınız.")

            with sag:
                with st.expander("⚠️ HATA BELİRT", expanded=True):
                    hata_donemi = st.radio("Hata Türü", ["Şu anki montajda", "Geçmiş montajdan geldi"])
                    hatali_adim = st.selectbox("Adım", ["Bilinmiyor", "Adım 1", "Adım 2", "Adım 3", "Adım 4"])
                    onceden_hatali = st.checkbox("Parça hatalı geldi")
                    
                    hata_bolgesi = st.selectbox("Bölge:", ["Seçilmedi", "Ön Yüz", "Arka Yüz", "Yan", "İç"])
                    hata_aciklama = st.text_area("Açıklama:")
                    foto_dosya = st.file_uploader("Görsel Ekle", type=["png", "jpg", "jpeg"])
                    
                    if st.button("HATAYI İLET", type="primary", use_container_width=True):
                        if hata_bolgesi != "Seçilmedi" and hata_aciklama != "":
                            foto_base64 = None
                            if foto_dosya is not None:
                                foto_base64 = base64.b64encode(foto_dosya.read()).decode("utf-8")
                                
                            db["errors"].append({
                                "Tarih/Saat": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "İstasyon": aktif_rol,
                                "İş Emri": istasyon_verisi['id'],
                                "Montaj_Donemi": hata_donemi,
                                "Hatali_Adim": hatali_adim,
                                "Onceden_Hatali": onceden_hatali,
                                "Bölge": hata_bolgesi,
                                "Açıklama": hata_aciklama,
                                "Foto_Base64": foto_base64
                            })
                            save_db(db)
                            st.success("İletildi!")
                        else:
                            st.error("Bölge ve açıklama giriniz.")
                            
    # --- CANLI OTO-YENİLEME DÖNGÜSÜ ---
    if canli_mod:
        time.sleep(3)
        st.rerun()
