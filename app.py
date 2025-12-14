import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import urllib.parse
from textblob import TextBlob
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import numpy as np
import sqlite3
import os
import textwrap
import concurrent.futures
import re
import altair as alt # Görselleştirme için

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="PATRONUN TEKNİK BORSA TERMİNALİ", 
    layout="wide",
    page_icon="💸"
)

# --- TEMA VE CSS ---
if 'theme' not in st.session_state:
    st.session_state.theme = "Buz Mavisi"

THEMES = {
    "Beyaz": {"bg": "#FFFFFF", "box_bg": "#F8F9FA", "text": "#000000", "border": "#DEE2E6", "news_bg": "#FFFFFF"},
    "Kirli Beyaz": {"bg": "#FAF9F6", "box_bg": "#FFFFFF", "text": "#2C3E50", "border": "#E5E7EB", "news_bg": "#FFFFFF"},
    "Buz Mavisi": {"bg": "#F0F8FF", "box_bg": "#FFFFFF", "text": "#0F172A", "border": "#BFDBFE", "news_bg": "#FFFFFF"}
}
current_theme = THEMES[st.session_state.theme]

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght+400;700&display=swap');
    
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {current_theme['text']}; }}
    .stApp {{ background-color: {current_theme['bg']}; }}
    
    section.main > div.block-container {{ padding-top: 1rem; padding-bottom: 1rem; }}
    
    .stMetricValue, .money-text {{ font-family: 'JetBrains Mono', monospace !important; }}
    
    .stat-box-small {{
        background: {current_theme['box_bg']}; border: 1px solid {current_theme['border']};
        border-radius: 4px; padding: 2px 6px; text-align: center; margin-bottom: 1px;
        box-shadow: 0 1px 1px rgba(0,0,0,0.03);
    }}
    .stat-label-small {{ font-size: 0.2rem; color: #64748B; text-transform: uppercase; margin: 0; }}
    .stat-value-small {{ font-size: 0.4rem; font-weight: 400; color: {current_theme['text']}; margin: 0; }}
    
    hr {{ margin-top: 0.2rem; margin-bottom: 0.5rem; }}
    .stSelectbox, .stTextInput {{ margin-bottom: -10px; }}
    
    .delta-pos {{ color: #16A34A; }} .delta-neg {{ color: #DC2626; }}
    .news-card {{ background: {current_theme['news_bg']}; border-left: 3px solid {current_theme['border']}; padding: 6px; margin-bottom: 6px; font-size: 0.78rem; }}
    .news-title {{ color: {current_theme['text']}; font-weight: 600; text-decoration: none; display: block; margin-bottom: 2px; font-size: 0.8rem; }}
    .news-title:hover {{ text-decoration: underline; color: #2563EB; }}
    .news-meta {{ font-size: 0.63rem; color: #64748B; }}

    button[data-testid="baseButton-primary"] {{ background-color: #1e40af !important; border-color: #1e40af !important; color: white !important; }}
    
    /* ORTAK FIRSATLAR VE GENEL KOMPAKLIK AYARLARI */
    .stButton button {{ 
        width: 100%; border-radius: 4px;
        font-size: 0.75rem;
        padding: 0.1rem 0.4rem;
    }}
    
    .info-card {{
        background: {current_theme['box_bg']}; border: 1px solid {current_theme['border']};
        border-radius: 6px; 
        padding: 6px;
        margin-top: 5px; 
        margin-bottom: 5px;
        font-size: 0.7rem;
        font-family: 'Inter', sans-serif;
    }}
    .info-header {{ font-weight: 700; color: #1e3a8a; border-bottom: 1px solid {current_theme['border']}; padding-bottom: 4px; margin-bottom: 4px; }}
    .info-row {{ display: flex; align-items: flex-start; margin-bottom: 2px; }}
    
    .label-short {{ font-weight: 600; color: #64748B; width: 80px; flex-shrink: 0; }}
    .label-long {{ font-weight: 600; color: #64748B; width: 100px; flex-shrink: 0; }} 
    
    .info-val {{ color: {current_theme['text']}; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; }}
    
    .header-logo {{ width: 40px; height: auto; margin-right: 10px; }}

    /* ORTAK FIRSATLAR LİSTE SATIRLARI */
    .opportunity-item {{
        display: flex; justify-content: space-between; align-items: center;
        background: {current_theme['box_bg']}; padding: 4px 6px; 
        border: 1px solid {current_theme['border']}; border-radius: 4px;
        margin-bottom: 2px;
        cursor: pointer; transition: background 0.1s;
        font-size: 0.7rem;
    }}
    .opportunity-item:hover {{ background: #f0f4f8; }}
    .opp-score {{ font-weight: 700; color: #1e40af; font-family: 'JetBrains Mono', monospace; }}
    .opp-detail {{ font-size: 0.65rem; color: #64748B; }}
    .opp-star {{ color: #FFD700; margin-left: 8px; cursor: pointer; }}

    /* ICT BAR STİLİ */
    .ict-bar-container {{
        width: 100%; height: 6px; background-color: #e2e8f0; border-radius: 3px; overflow: hidden; margin: 4px 0; display:flex;
    }}
    .ict-bar-fill {{ height: 100%; transition: width 0.5s ease; }}
    
    /* TEKNİK KART DETAYLARI İÇİN GRID - DÜZELTİLDİ */
    .tech-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4px; }}
    .tech-item {{ display: flex; align-items: center; font-size: 0.7rem; }}
    
</style>
""", unsafe_allow_html=True)

# --- VERİTABANI ---
DB_FILE = "patron.db"
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS watchlist (symbol TEXT PRIMARY KEY)')
    conn.commit()
    conn.close()
def load_watchlist_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT symbol FROM watchlist')
    data = c.fetchall()
    conn.close()
    return [x[0] for x in data]
def add_watchlist_db(symbol):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO watchlist (symbol) VALUES (?)', (symbol,))
        conn.commit()
    except sqlite3.IntegrityError: 
        pass
    conn.close()
def remove_watchlist_db(symbol):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
    conn.commit()
    conn.close()
if not os.path.exists(DB_FILE): init_db()

# --- VARLIK LİSTELERİ ---

# 1. S&P 500 ÖZEL SIRALAMA (Öncelikliler + Alfabetik Diğerleri)
priority_sp = ["AGNC", "ARCC", "PFE", "JEPI", "MO", "EPD"]

raw_sp500_rest = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "AMD",
    "INTC", "QCOM", "TXN", "AMAT", "LRCX", "MU", "ADI", "CSCO", "ORCL", "CRM",
    "ADBE", "IBM", "ACN", "NOW", "PANW", "SNPS", "CDNS", "KLAC", "NXPI", "APH",
    "MCHP", "ON", "ANET", "IT", "GLW", "HPE", "HPQ", "NTAP", "STX", "WDC", "TEL",
    "PLTR", "FTNT", "CRWD", "SMCI", "MSI", "TRMB", "TER", "PTC", "TYL", "FFIV",
    "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "AXP", "V", "MA", "PYPL", "SQ",
    "SPGI", "MCO", "CB", "MMC", "PGR", "USB", "PNC", "TFC", "COF", "BK", "SCHW",
    "ICE", "CME", "AON", "AJG", "TRV", "ALL", "AIG", "MET", "PRU", "AFL", "HIG",
    "FITB", "MTB", "HBAN", "RF", "CFG", "KEY", "SYF", "DFS", "AMP", "PFG", "CINF",
    "LLY", "UNH", "JNJ", "MRK", "ABBV", "TMO", "DHR", "ABT", "BMY", "AMGN",
    "ISRG", "SYK", "ELV", "CVS", "CI", "GILD", "REGN", "VRTX", "ZTS", "BSX", "BDX",
    "HCA", "MCK", "COR", "CAH", "CNC", "HUM", "MOH", "DXCM", "EW", "RMD", "ALGN",
    "ZBH", "BAX", "STE", "COO", "WAT", "MTD", "IQV", "A", "HOLX", "IDXX", "BIO",
    "WMT", "HD", "PG", "COST", "KO", "PEP", "MCD", "SBUX", "NKE", "DIS", "TMUS",
    "CMCSA", "NFLX", "TGT", "LOW", "TJX", "PM", "EL", "CL", "K", "GIS", "MNST",
    "TSCO", "ROST", "FAST", "DLTR", "DG", "ORLY", "AZO", "ULTA", "BBY", "KHC",
    "HSY", "MKC", "CLX", "KMB", "SYY", "KR", "ADM", "STZ", "TAP", "CAG", "SJM",
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HES", "KMI",
    "GE", "CAT", "DE", "HON", "MMM", "ETN", "ITW", "EMR", "PH", "CMI", "PCAR",
    "BA", "LMT", "RTX", "GD", "NOC", "LHX", "TDG", "TXT", "HII",
    "UPS", "FDX", "UNP", "CSX", "NSC", "DAL", "UAL", "AAL", "LUV",
    "FCX", "NEM", "NUE", "DOW", "CTVA", "LIN", "SHW", "PPG", "ECL", "APD", "VMC",
    "MLM", "ROP", "TT", "CARR", "OTIS", "ROK", "AME", "DOV", "XYL", "WAB",
    "NEE", "DUK", "SO", "AEP", "SRE", "D", "PEG", "ED", "XEL", "PCG", "WEC", "ES",
    "AMT", "PLD", "CCI", "EQIX", "PSA", "O", "DLR", "SPG", "VICI", "CBRE", "CSGP",
    "WELL", "AVB", "EQR", "EXR", "MAA", "HST", "KIM", "REG", "SBAC", "WY",
    "PHM", "LEN", "DHI", "LVS", "MGM", "T", "VZ", "BKNG", "MAR",
    "F", "GM", "STT", "ZBRA", "GL", "EWBC", "OHI", "EXPE", "CF",
    "HAL", "HP", "RCL", "NCLH", "CPRT", "FANG", "PXD", "OKE", "WMB", "TRGP"
]

# Mantık: Öncelikli listeyi çıkar, kalanı sırala, sonra birleştir.
raw_sp500_rest = list(set(raw_sp500_rest) - set(priority_sp))
raw_sp500_rest.sort()
final_sp500_list = priority_sp + raw_sp500_rest

# 2. EMTİA & KRİPTO ÖZEL SIRALAMA (Doğru Semboller)
priority_crypto = ["GC=F", "SI=F", "BTC-USD", "ETH-USD"]

other_crypto = [
    "BNB-USD", "SOL-USD", "XRP-USD", "ADA-USD", "DOGE-USD", "AVAX-USD",
    "TRX-USD", "LINK-USD", "DOT-USD", "MATIC-USD", "LTC-USD", "BCH-USD",
    "UNI-USD", "ATOM-USD", "XLM-USD", "ETC-USD", "FIL-USD", "HBAR-USD",
    "APT-USD", "NEAR-USD", "VET-USD", "QNT-USD", "AAVE-USD", "ALGO-USD"
]
other_crypto.sort()
final_crypto_list = priority_crypto + other_crypto

# 3. NASDAQ (Alfabetik)
raw_nasdaq = [
    "AAPL", "MSFT", "NVDA", "AMZN", "AVGO", "META", "TSLA", "GOOGL", "GOOG", "COST",
    "NFLX", "AMD", "PEP", "LIN", "TMUS", "CSCO", "QCOM", "INTU", "AMAT", "TXN",
    "HON", "AMGN", "BKNG", "ISRG", "CMCSA", "SBUX", "MDLZ", "GILD", "ADP", "ADI",
    "REGN", "VRTX", "LRCX", "PANW", "MU", "KLAC", "SNPS", "CDNS", "MELI", "MAR",
    "ORLY", "CTAS", "NXPI", "CRWD", "CSX", "PCAR", "MNST", "WDAY", "ROP", "AEP",
    "ROKU", "ZS", "OKTA", "TEAM", "DDOG", "MDB", "SHOP", "EA", "TTD",
    "DOCU", "INTC", "SGEN", "ILMN", "IDXX", "ODFL", "EXC", "ADSK", "PAYX", "CHTR",
    "MRVL", "KDP", "XEL", "LULU", "ALGN", "VRSK", "CDW", "DLTR", "SIRI", "JBHT",
    "WBA", "PDD", "JD", "BIDU", "NTES", "NXST", "MTCH", "UAL", "SPLK",
    "ANSS", "SWKS", "QRVO", "AVTR", "FTNT", "ENPH", "SEDG", "BIIB", "CSGP"
]
raw_nasdaq = sorted(list(set(raw_nasdaq)))

# 4. BIST 100 LİSTESİ (SKILLING DESTEKLİLER BAŞTA)
# Senin tespit ettiğin Skilling destekli hisseler
priority_bist = [
    "AKBNK.IS", "BIMAS.IS", "DOHOL.IS", "FENER.IS", "KCHOL.IS",
    "SISE.IS", "TCELL.IS", "THYAO.IS", "TTKOM.IS", "VAKBNK.IS"
]

# Geriye kalan BIST 100 hisseleri
raw_bist100_rest = [
    "AEFES.IS", "AGHOL.IS", "AHGAZ.IS", "AKCNS.IS", "AKFGY.IS", "AKFYE.IS", "AKSA.IS", "AKSEN.IS",
    "ALARK.IS", "ALBRK.IS", "ALFAS.IS", "ANSGR.IS", "ARCLK.IS", "ASELS.IS", "ASTOR.IS", "BERA.IS",
    "BIOEN.IS", "BOBET.IS", "BRSAN.IS", "BRYAT.IS", "BUCIM.IS", "CANTE.IS", "CCOLA.IS", "CEMTS.IS", "CIMSA.IS",
    "CWENE.IS", "DOAS.IS", "ECILC.IS", "ECZYT.IS", "EGEEN.IS", "EKGYO.IS", "ENJSA.IS", "ENKAI.IS",
    "EREGL.IS", "EUREN.IS", "EUPWR.IS", "FROTO.IS", "GARAN.IS", "GENIL.IS", "GESAN.IS", "GLYHO.IS",
    "GOKNR.IS", "GUBRF.IS", "GWIND.IS", "HALKB.IS", "HEKTS.IS", "IPEKE.IS", "ISCTR.IS", "ISDMR.IS", "ISGYO.IS",
    "ISMEN.IS", "IZENR.IS", "KCAER.IS", "KLSER.IS", "KONTR.IS", "KONYA.IS", "KORDS.IS", "KOZAA.IS",
    "KOZAL.IS", "KRDMD.IS", "KZBGY.IS", "MAVI.IS", "MGROS.IS", "MIATK.IS", "ODAS.IS", "OTKAR.IS", "OYAKC.IS",
    "PENTA.IS", "PETKM.IS", "PGSUS.IS", "PSGYO.IS", "QUAGR.IS", "REEDR.IS", "SAHOL.IS", "SASA.IS", "SDTTR.IS",
    "SKBNK.IS", "SMRTG.IS", "SOKM.IS", "TABGD.IS", "TAVHL.IS", "TKFEN.IS",
    "TOASO.IS", "TSKB.IS", "TTRAK.IS", "TUKAS.IS", "TUPRS.IS", "TURSG.IS", "ULUUN.IS",
    "VESBE.IS", "VESTL.IS", "YEOTK.IS", "YKBNK.IS", "YLALI.IS", "ZOREN.IS"
]

# Mantık: Önceliklileri rest listesinden temizleyip sıralama (Güvenlik)
raw_bist100_rest = list(set(raw_bist100_rest) - set(priority_bist))
raw_bist100_rest.sort()
final_bist100_list = priority_bist + raw_bist100_rest

# --- GRUPLAMA (BIST 100 GÜNCELLENDİ) ---
ASSET_GROUPS = {
    "S&P 500 (TOP 300)": final_sp500_list,
    "NASDAQ (TOP 100)": raw_nasdaq,
    "BIST 100": final_bist100_list,
    "EMTİA & KRİPTO": final_crypto_list
}

INITIAL_CATEGORY = "S&P 500 (TOP 300)"

# --- STATE ---
if 'category' not in st.session_state: st.session_state.category = INITIAL_CATEGORY
if 'ticker' not in st.session_state: st.session_state.ticker = "AAPL"
if 'scan_data' not in st.session_state: st.session_state.scan_data = None
if 'radar2_data' not in st.session_state: st.session_state.radar2_data = None
if 'agent3_data' not in st.session_state: st.session_state.agent3_data = None
if 'watchlist' not in st.session_state: st.session_state.watchlist = load_watchlist_db()
if 'ict_analysis' not in st.session_state: st.session_state.ict_analysis = None
if 'tech_card_data' not in st.session_state: st.session_state.tech_card_data = None
if 'sentiment_deep' not in st.session_state: st.session_state.sentiment_deep = None

# --- CALLBACKLER ---
def on_category_change():
    new_cat = st.session_state.get("selected_category_key")
    if new_cat and new_cat in ASSET_GROUPS:
        st.session_state.category = new_cat
        st.session_state.ticker = ASSET_GROUPS[new_cat][0]
        st.session_state.scan_data = None
        st.session_state.radar2_data = None
        st.session_state.agent3_data = None # SIFIRLAMA

def on_asset_change():
    new_asset = st.session_state.get("selected_asset_key")
    if new_asset: st.session_state.ticker = new_asset

def on_manual_button_click():
    if st.session_state.manual_input_key:
        st.session_state.ticker = st.session_state.manual_input_key.upper()

def on_scan_result_click(symbol): st.session_state.ticker = symbol

def toggle_watchlist(symbol):
    wl = st.session_state.watchlist
    if symbol in wl:
        remove_watchlist_db(symbol)
        wl.remove(symbol)
    else:
        add_watchlist_db(symbol)
        wl.append(symbol)
    st.session_state.watchlist = wl

# --- YENİ FONKSİYON: STP SENTIMENT AJANI TARAMA MOTORU (NameError Çözümü için Buraya Alındı) ---
@st.cache_data(ttl=900)
def scan_stp_signals(asset_list):
    if not asset_list: return None, None
    
    cross_signals = []      # Yukarı Kesenler
    trend_signals = []      # Üzerinde Olanlar
    
    try:
        # Hızlı olması için son 1 aylık veriyi çekiyoruz
        data = yf.download(asset_list, period="1mo", group_by="ticker", threads=True, progress=False)
    except:
        return [], []

    for symbol in asset_list:
        try:
            # Veri ayıklama
            if isinstance(data.columns, pd.MultiIndex):
                if symbol not in data.columns.levels[0]: continue
                df = data[symbol].copy()
            else:
                if len(asset_list) == 1: df = data.copy()
                else: continue

            if df.empty or 'Close' not in df.columns: continue
            df = df.dropna()
            if len(df) < 10: continue

            # --- STP HESAPLAMASI (MEVCUT KODUNLA AYNI) ---
            close = df['Close']
            high = df['High']
            low = df['Low']
            
            typical_price = (high + low + close) / 3
            stp = typical_price.ewm(span=6, adjust=False).mean()
            
            # Son 2 günün verileri
            c_last = float(close.iloc[-1])
            c_prev = float(close.iloc[-2])
            
            s_last = float(stp.iloc[-1])
            s_prev = float(stp.iloc[-2])
            
            # 1. TARAMA: FİYAT STP'Yİ YUKARI KESEN (CROSSOVER)
            # Önceki gün fiyat STP'nin altında veya eşit, bugün üzerinde
            if c_prev <= s_prev and c_last > s_last:
                cross_signals.append({
                    "Sembol": symbol,
                    "Fiyat": c_last,
                    "STP": s_last,
                    "Fark": ((c_last/s_last)-1)*100
                })
            
            # 2. TARAMA: 2 GÜNDÜR STP ÜSTÜNDE (TREND)
            # Hem dün hem bugün fiyat STP'nin üzerinde
            elif c_prev > s_prev and c_last > s_last:
                trend_signals.append({
                    "Sembol": symbol,
                    "Fiyat": c_last,
                    "STP": s_last,
                    "Fark": ((c_last/s_last)-1)*100
                })
                
        except:
            continue
            
    return cross_signals, trend_signals

# --- SIDEBAR (YENİ BAŞLIK VE SENTIMENT AJANI BURAYA EKLENDİ) ---
with st.sidebar:
    # YENİ BAŞLIK (İstenen yerde)
    st.markdown(f"""
    <div style="font-size:1.5rem; font-weight:700; color:#1e3a8a; text-align:center; padding-top: 10px; padding-bottom: 10px;">
        PATRONUN BORSA PANELİ
    </div>
    <hr style="border:0; border-top: 1px solid #e5e7eb; margin-top:5px; margin-bottom:10px;">
    """, unsafe_allow_html=True)

    st.markdown("### ⚙️ Ayarlar")
    selected_theme_name = st.selectbox(
        "",
        ["Beyaz", "Kirli Beyaz", "Buz Mavisi"],
        index=["Beyaz", "Kirli Beyaz", "Buz Mavisi"].index(st.session_state.theme),
        label_visibility="collapsed"
    )
    if selected_theme_name != st.session_state.theme:
        st.session_state.theme = selected_theme_name
        st.rerun()
    st.divider()
    
    # GÜNCELLENEN BUTON (SADECE PROMPT OLUŞTURUR)
    with st.expander("🤖 AI Analist (Prompt)", expanded=True):
        st.caption("Verileri toplayıp ChatGPT için hazır metin oluşturur.")
        if st.button("📋 Analiz Metnini Hazırla", type="primary"):
            st.session_state.generate_prompt = True
    
    # --- BURASI YENİ EKLENEN SENTIMENT AJANI (UI KISMI) ---
    st.divider()
    with st.expander("🕵️ Sentiment Ajanı (STP)", expanded=True):
        st.caption("Fiyat Dengesi (STP) Taraması")
        
        if st.button("Kesişimleri Tara", type="secondary"):
            with st.spinner("Ajan STP izini sürüyor..."):
                # Aktif kategorideki hisseleri çek
                current_assets = ASSET_GROUPS.get(st.session_state.category, [])
                crosses, trends = scan_stp_signals(current_assets)
                
                # --- SONUÇLARI SESSION STATE'E KAYDET ---
                st.session_state.stp_crosses = crosses
                st.session_state.stp_trends = trends
                st.session_state.stp_scanned = True

        # Sonuçları Göster
        if st.session_state.get('stp_scanned'):
            # TAB 1: YENİ KESİŞİMLER (AL SİNYALİ)
            st.markdown("###### ⚡ FİYATI STP YUKARI KESEN")
            if st.session_state.stp_crosses:
                # GÜNCELLEME: Burada da scroll bar olması için container eklendi
                with st.container(height=200):
                    for item in st.session_state.stp_crosses:
                        if st.button(f"🚀 {item['Sembol']} ({item['Fiyat']:.2f})", key=f"stp_c_{item['Sembol']}"):
                            st.session_state.ticker = item['Sembol'] # Tıklayınca ana ekrana git
                            st.rerun()
            else:
                st.info("Yeni kesişim yok.")

            st.markdown("---")

            # TAB 2: GÜÇLÜ DURANLAR (2 GÜNDÜR ÜSTÜNDE)
            st.markdown("###### ✅ 2 GÜNDÜR STP ÜSTÜNDE")
            if st.session_state.stp_trends:
                # Çok fazla sonuç çıkarsa yer kaplamasın diye scroll koyuyoruz
                with st.container(height=200):
                    for item in st.session_state.stp_trends:
                        # Yeşil tonlu buton
                        if st.button(f"{item['Sembol']} | %{item['Fark']:.1f}", key=f"stp_t_{item['Sembol']}"):
                            st.session_state.ticker = item['Sembol']
                            st.rerun()
            else:
                st.info("Trend takibi yok.")

# --- ANALİZ MOTORLARI (MULTI-THREADED & CACHED) ---
@st.cache_data(ttl=3600)
def analyze_market_intelligence(asset_list):
    if not asset_list: return pd.DataFrame()
    
    # 1. Toplu Veri Çekme (I/O)
    try:
        data = yf.download(asset_list, period="6mo", group_by='ticker', threads=True, progress=False)
    except:
        return pd.DataFrame()

    # 2. İşlemci Fonksiyonu (Worker)
    def process_symbol(symbol):
        try:
            # MultiIndex kontrolü
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]:
                    df = data[symbol].copy()
                else:
                    return None
            else:
                if len(asset_list) == 1:
                    df = data.copy()
                else:
                    return None
            
            if df.empty or 'Close' not in df.columns: return None
            df = df.dropna(subset=['Close'])
            if len(df) < 60: return None
            
            close = df['Close']; high = df['High']; low = df['Low']
            volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))
            
            # Hesaplamalar
            ema5 = close.ewm(span=5, adjust=False).mean()
            ema20 = close.ewm(span=20, adjust=False).mean()
            sma20 = close.rolling(20).mean()
            std20 = close.rolling(20).std()
            bb_width = ((sma20 + 2*std20) - (sma20 - 2*std20)) / (sma20 + 0.0001)
            hist = (close.ewm(span=12, adjust=False).mean() - close.ewm(span=12, adjust=False).mean()).ewm(span=9, adjust=False).mean()
            # MACD calculation might be simplified in your original code, keeping your logic mostly
            # Standard MACD: EMA12 - EMA26
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            hist = macd_line - signal_line
            
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + (gain / loss)))
            williams_r = (high.rolling(14).max() - close) / (high.rolling(14).max() - low.rolling(14).min()) * -100
            daily_range = high - low
            
            score = 0; reasons = []
            # Detaylı Kontrol Listesi (YENİ EKLENDİ)
            details = {}

            curr_c = float(close.iloc[-1]); curr_vol = float(volume.iloc[-1])
            avg_vol = float(volume.rolling(5).mean().iloc[-1]) if len(volume) > 5 else 1.0
            
            # --- RADAR 1 MADDELERİ ---
            # 1. Squeeze
            if bb_width.iloc[-1] <= bb_width.tail(60).min() * 1.1:
                score += 1; reasons.append("🚀 Squeeze")
                details['Squeeze'] = True
            else: details['Squeeze'] = False
            
            # 2. NR4
            if daily_range.iloc[-1] == daily_range.tail(4).min() and daily_range.iloc[-1] > 0:
                score += 1; reasons.append("🔇 NR4")
                details['NR4'] = True
            else: details['NR4'] = False
            
            # 3. Trend
            if ((ema5.iloc[-1] > ema20.iloc[-1]) and (ema5.iloc[-2] <= ema20.iloc[-2])) or ((ema5.iloc[-2] > ema20.iloc[-2]) and (ema5.iloc[-3] <= ema20.iloc[-3])):
                score += 1; reasons.append("⚡ Trend")
                details['Trend'] = True
            else: details['Trend'] = False
            
            # 4. MACD
            if hist.iloc[-1] > hist.iloc[-2]:
                score += 1; reasons.append("🟢 MACD")
                details['MACD'] = True
            else: details['MACD'] = False
            
            # 5. W%R
            if williams_r.iloc[-1] > -50:
                score += 1; reasons.append("🔫 W%R")
                details['W%R'] = True
            else: details['W%R'] = False
            
            # 6. Hacim
            if curr_vol > avg_vol * 1.2:
                score += 1; reasons.append("🔊 Hacim")
                details['Hacim'] = True
            else: details['Hacim'] = False
            
            # 7. Breakout
            if curr_c >= high.tail(20).max() * 0.98:
                score += 1; reasons.append("🔨 Breakout")
                details['Breakout'] = True
            else: details['Breakout'] = False
            
            # 8. RSI
            rsi_c = rsi.iloc[-1]
            if 30 < rsi_c < 65 and rsi_c > rsi.iloc[-2]:
                score += 1; reasons.append("⚓ RSI Güçlü")
                details['RSI Güçlü'] = True
            else: details['RSI Güçlü'] = False
            
            if score > 0:
                return {
                    "Sembol": symbol,
                    "Fiyat": f"{curr_c:.2f}",
                    "Skor": score,
                    "Nedenler": " | ".join(reasons),
                    "Detaylar": details # YENİ
                }
            return None
        except:
            return None

    # 3. Paralel Çalıştırma (ThreadPoolExecutor)
    signals = []
    # CPU sayısı kadar veya biraz daha fazla thread açarak işlemi hızlandırıyoruz
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(process_symbol, asset_list))
    
    # None dönenleri temizle
    signals = [r for r in results if r is not None]

    return pd.DataFrame(signals).sort_values(by="Skor", ascending=False) if signals else pd.DataFrame()

@st.cache_data(ttl=3600)
def radar2_scan(asset_list, min_price=5, max_price=5000, min_avg_vol_m=0.5): # Fiyat ve hacim BIST için esnetildi
    if not asset_list: return pd.DataFrame()
    
    # 1. Veri İndirme (Bulk)
    try:
        data = yf.download(asset_list, period="1y", group_by="ticker", threads=True, progress=False)
    except:
        return pd.DataFrame()
    
    # Endeks verisi tek seferlik
    try:
        idx = yf.download("^GSPC", period="1y", progress=False)["Close"]
    except:
        idx = None

    # 2. Worker Fonksiyonu
    def process_radar2(symbol):
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol not in data.columns.levels[0]: return None
                df = data[symbol].copy()
            else:
                if len(asset_list) == 1: df = data.copy()
                else: return None
                
            if df.empty or 'Close' not in df.columns: return None
            df = df.dropna(subset=['Close'])
            if len(df) < 120: return None
            
            close = df['Close']; high = df['High']; volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))
            curr_c = float(close.iloc[-1])
            
            # Fiyat ve Hacim Filtresi (BIST için parametreler yukarıda biraz esnetildi)
            if curr_c < min_price or curr_c > max_price: return None
            avg_vol_20 = float(volume.rolling(20).mean().iloc[-1])
            # BIST hisseleri için hacim filtresi bazen takılabilir, bu yüzden esnek tutulabilir
            if avg_vol_20 < min_avg_vol_m * 1e6: return None
            
            sma20 = close.rolling(20).mean()
            sma50 = close.rolling(50).mean()
            sma100 = close.rolling(100).mean()
            sma200 = close.rolling(200).mean()
            
            trend = "Yatay"
            if not np.isnan(sma200.iloc[-1]):
                if curr_c > sma50.iloc[-1] > sma100.iloc[-1] > sma200.iloc[-1] and sma200.iloc[-1] > sma200.iloc[-20]:
                    trend = "Boğa"
                elif curr_c < sma200.iloc[-1] and sma200.iloc[-1] < sma200.iloc[-20]:
                    trend = "Ayı"
            
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + (gain / loss)))
            rsi_c = float(rsi.iloc[-1])
            
            # MACD
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            hist = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()
            
            recent_high_60 = float(high.rolling(60).max().iloc[-1])
            breakout_ratio = curr_c / recent_high_60 if recent_high_60 > 0 else 0
            
            rs_score = 0.0
            if idx is not None and len(close) > 60 and len(idx) > 60:
                common_index = close.index.intersection(idx.index)
                if len(common_index) > 60:
                    cs = close.reindex(common_index)
                    isx = idx.reindex(common_index)
                    rs_score = float((cs.iloc[-1]/cs.iloc[-60]-1) - (isx.iloc[-1]/isx.iloc[-60]-1))
            
            setup = "-"; tags = []; score = 0
            # Detayları Kaydet (YENİ)
            details = {}
            
            avg_vol_20 = max(avg_vol_20, 1)
            vol_spike = volume.iloc[-1] > avg_vol_20 * 1.3
            
            # 1. Zirve (Breakout)
            if trend == "Boğa" and breakout_ratio >= 0.97:
                setup = "Breakout"; score += 2; tags.append("Zirve")
            
            # 2. Hacim Patlaması
            if vol_spike:
                score += 1; tags.append("Hacim+")
                details['Hacim Patlaması'] = True
            else: details['Hacim Patlaması'] = False

            # 3. Pullback
            if trend == "Boğa" and setup == "-":
                if sma20.iloc[-1] <= curr_c <= sma50.iloc[-1] * 1.02 and 40 <= rsi_c <= 55:
                    setup = "Pullback"; score += 2; tags.append("Düzeltme")
                if volume.iloc[-1] < avg_vol_20 * 0.9:
                    score += 1; tags.append("Sığ Satış")
            
            # 4. Dip Dönüşü
            if setup == "-":
                if rsi.iloc[-2] < 30 <= rsi_c and hist.iloc[-1] > hist.iloc[-2]:
                    setup = "Dip Dönüşü"; score += 2; tags.append("Dip Dönüşü")
            
            # 5. RS
            if rs_score > 0: 
                score += 1; tags.append("RS+")
                details['RS (S&P500)'] = True
            else: details['RS (S&P500)'] = False

            # 6. Trend
            if trend == "Boğa": 
                score += 1
                details['Boğa Trendi'] = True
            else:
                if trend == "Ayı": score -= 1
                details['Boğa Trendi'] = False
                
            # Diğer Detaylar (Görsel İçin)
            details['60G Zirve'] = breakout_ratio >= 0.90
            details['RSI Bölgesi'] = (40 <= rsi_c <= 60)
            details['MACD Hist'] = hist.iloc[-1] > hist.iloc[-2]
            
            if score > 0:
                return {
                    "Sembol": symbol,
                    "Fiyat": round(curr_c, 2),
                    "Trend": trend,
                    "Setup": setup,
                    "Skor": score,
                    "RS": round(rs_score * 100, 1),
                    "Etiketler": " | ".join(tags),
                    "Detaylar": details # YENİ
                }
            return None
        except:
            return None

    # 3. Paralel Çalıştırma
    results = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(process_radar2, asset_list))
        
    results = [r for r in results if r is not None]
    
    return pd.DataFrame(results).sort_values(by=["Skor", "RS"], ascending=False).head(50) if results else pd.DataFrame()

# --- YENİ EKLENEN KISIM: AJAN 3 (BREAKOUT & PRICE ACTION SCANNER) ---
@st.cache_data(ttl=3600)
def agent3_breakout_scan(asset_list):
    if not asset_list: return pd.DataFrame()
    
    try:
        data = yf.download(asset_list, period="6mo", group_by="ticker", threads=True, progress=False)
    except:
        return pd.DataFrame()

    def process_agent3(symbol):
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol not in data.columns.levels[0]: return None
                df = data[symbol].copy()
            else:
                if len(asset_list) == 1: df = data.copy()
                else: return None

            if df.empty or 'Close' not in df.columns: return None
            df = df.dropna(subset=['Close'])
            if len(df) < 60: return None # En az 60 gün veri lazım

            close = df['Close']
            high = df['High']
            low = df['Low']
            open_ = df['Open']
            volume = df['Volume'] if 'Volume' in df.columns else pd.Series([1]*len(df))

            # 1. HESAPLAMALAR
            ema5 = close.ewm(span=5, adjust=False).mean()
            ema20 = close.ewm(span=20, adjust=False).mean()
            sma20 = close.rolling(20).mean()
            sma50 = close.rolling(50).mean()
            
            # Bollinger Bands (Sıkışma Kontrolü İçin)
            std20 = close.rolling(20).std()
            bb_upper = sma20 + (2 * std20)
            bb_lower = sma20 - (2 * std20)
            bb_width = (bb_upper - bb_lower) / sma20
            
            # RVOL (Relative Volume)
            vol_20 = volume.rolling(20).mean().iloc[-1]
            curr_vol = volume.iloc[-1]
            if vol_20 == 0: vol_20 = 1 
            rvol = curr_vol / vol_20

            high_60 = high.rolling(60).max().iloc[-1]
            curr_price = close.iloc[-1]

            # RSI Hesapla
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]

            # 2. TEMEL KOŞULLAR (FİLTRELER)
            cond_ema = ema5.iloc[-1] > ema20.iloc[-1] # Genel trend yukarı (veya yeni dönüyor)
            cond_vol = rvol > 1.2 
            cond_prox = curr_price > (high_60 * 0.90) # Zirveye yakın
            cond_rsi = rsi < 70
            sma_ok = sma20.iloc[-1] > sma50.iloc[-1]

            if cond_ema and cond_vol and cond_prox and cond_rsi:
                
                # --- PRICE ACTION ANALİZİ (YÖN TAYİNİ) ---
                is_short_signal = False
                short_reason = ""

                # 1. Üç Kara Karga (3 Consecutive Reds)
                # Son 3 mumun kapanışı açılışından düşükse
                if (close.iloc[-1] < open_.iloc[-1]) and \
                   (close.iloc[-2] < open_.iloc[-2]) and \
                   (close.iloc[-3] < open_.iloc[-3]):
                    is_short_signal = True
                    short_reason = "3 Kırmızı Mum (Düşüş)"

                # 2. Bearish Engulfing (Yutan Ayı - Güçlü Versiyon)
                # Son mum kırmızı + Gövdesi önceki iki mumun gövdesinden büyük
                body_last = abs(close.iloc[-1] - open_.iloc[-1])
                body_prev1 = abs(close.iloc[-2] - open_.iloc[-2])
                body_prev2 = abs(close.iloc[-3] - open_.iloc[-3])
                
                if (close.iloc[-1] < open_.iloc[-1]) and (body_last > (body_prev1 + body_prev2)):
                    is_short_signal = True
                    short_reason = "Yutan Ayı Mum (Engulfing)"

                # --- SIKIŞMA (SQUEEZE) KONTROLÜ ---
                min_bandwidth_60 = bb_width.rolling(60).min().iloc[-1]
                is_squeeze = bb_width.iloc[-1] <= min_bandwidth_60 * 1.10
                
                # Zirve Metni
                prox_pct = (curr_price / high_60) * 100
                if is_squeeze:
                    prox_str = f"💣 Bant içinde sıkışma var, patlamaya hazır"
                else:
                    prox_str = f"%{prox_pct:.1f}"
                    if prox_pct >= 98: prox_str += " (Sınıra Dayandı)"
                    else: prox_str += " (Hazırlanıyor)"

                # --- TUZAK (WICK) FİLTRESİ ---
                c_open = open_.iloc[-1]
                c_close = close.iloc[-1]
                c_high = high.iloc[-1]
                body_size = abs(c_close - c_open)
                upper_wick = c_high - max(c_open, c_close)
                
                # Eğer üst fitil, gövdenin 1.5 katından büyükse TUZAK UYARISI
                is_wick_rejected = (upper_wick > body_size * 1.5) and (upper_wick > 0)
                wick_warning = " <span style='color:#DC2626; font-weight:700; background:#fef2f2; padding:2px 4px; border-radius:4px;'>⚠️ Satış Baskısı (Uzun Fitil)</span>" if is_wick_rejected else ""

                # --- RVOL METNİ ---
                rvol_text = ""
                if rvol > 2.0: rvol_text = "Olağanüstü para girişi 🐳"
                elif rvol > 1.5: rvol_text = "İlgi artıyor 📈"
                else: rvol_text = "İlgi var 👀"

                # --- SONUÇ FORMATLAMA ---
                # Eğer Short Sinyali varsa sembolü ve trendi değiştir
                display_symbol = symbol
                trend_color = "#0f172a" # Siyah (Normal)
                
                if is_short_signal:
                    display_symbol = f"{symbol} <span style='color:#DC2626; font-weight:800; background:#fef2f2; padding:2px 6px; border-radius:4px; font-size:0.7rem;'>🔻 SHORT FIRSATI</span>"
                    trend_display = f"<span style='color:#DC2626; font-weight:700;'>{short_reason}</span>"
                else:
                    trend_display = f"✅EMA | {'✅SMA' if sma_ok else '❌SMA'}"

                return {
                    "Sembol_Raw": symbol, # İşlem için ham sembol
                    "Sembol_Display": display_symbol, # Ekranda görünecek (Short etiketli)
                    "Fiyat": f"{curr_price:.2f}",
                    "Zirveye Yakınlık": prox_str + wick_warning,
                    "Hacim Durumu": rvol_text,
                    "Trend Durumu": trend_display,
                    "RSI": f"{rsi:.0f}",
                    "SortKey": rvol
                }
            return None

        except:
            return None

    results = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(process_agent3, asset_list))
    
    results = [r for r in results if r is not None]
    return pd.DataFrame(results).sort_values(by="SortKey", ascending=False) if results else pd.DataFrame()

# --- SENTIMENT & DERİN RÖNTGEN ---
@st.cache_data(ttl=600)
def calculate_sentiment_score(ticker):
    try:
        df = yf.download(ticker, period="6mo", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close = df['Close']; high = df['High']; low = df['Low']; volume = df['Volume']
        
        score_mom = 0; reasons_mom = []
        rsi = 100 - (100 / (1 + (close.diff().clip(lower=0).rolling(14).mean() / close.diff().clip(upper=0).abs().rolling(14).mean())))
        if rsi.iloc[-1] > 50 and rsi.iloc[-1] > rsi.iloc[-2]:
            score_mom += 10; reasons_mom.append("RSI ↑")
        macd = close.ewm(span=12).mean() - close.ewm(span=26).mean()
        hist = macd - macd.ewm(span=9).mean()
        if hist.iloc[-1] > 0 and hist.iloc[-1] > hist.iloc[-2]:
            score_mom += 10; reasons_mom.append("MACD ↑")
        if rsi.iloc[-1] < 30:
            reasons_mom.append("OS")
        elif rsi.iloc[-1] > 70:
            reasons_mom.append("OB")
        else:
            score_mom += 10; reasons_mom.append("Stoch Stabil")
        
        score_vol = 0; reasons_vol = []
        if volume.iloc[-1] > volume.rolling(20).mean().iloc[-1]:
            score_vol += 15; reasons_vol.append("Vol ↑")
        else:
            reasons_vol.append("Vol ↓")
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        if obv.iloc[-1] > obv.rolling(5).mean().iloc[-1]:
            score_vol += 10; reasons_vol.append("OBV ↑")
        
        score_tr = 0; reasons_tr = []
        sma50 = close.rolling(50).mean()
        sma200 = close.rolling(200).mean()
        if sma50.iloc[-1] > sma200.iloc[-1]:
            score_tr += 10; reasons_tr.append("GoldCross")
        if close.iloc[-1] > sma50.iloc[-1]:
            score_tr += 10; reasons_tr.append("P > SMA50")
        
        score_vola = 0; reasons_vola = []
        std = close.rolling(20).std()
        upper = close.rolling(20).mean() + (2 * std)
        if close.iloc[-1] > upper.iloc[-1]:
            score_vola += 10; reasons_vola.append("BB Break")
        atr = (high-low).rolling(14).mean()
        if atr.iloc[-1] < atr.iloc[-5]:
            score_vola += 5; reasons_vola.append("Vola ↓")
        
        score_str = 0; reasons_str = []
        if close.iloc[-1] > high.rolling(20).max().shift(1).iloc[-1]:
            score_str += 10; reasons_str.append("Yeni Tepe (BOS)")
        
        total = score_mom + score_vol + score_tr + score_vola + score_str
        bars = int(total / 5)
        bar_str = "[" + "|" * bars + "." * (20 - bars) + "]"
        
        def fmt(lst):
            return f"<span style='font-size:0.65rem; color:#64748B;'>({' + '.join(lst)})</span>" if lst else ""
        
        return {
            "total": total, "bar": bar_str,
            "mom": f"{score_mom}/30 {fmt(reasons_mom)}",
            "vol": f"{score_vol}/25 {fmt(reasons_vol)}",
            "tr": f"{score_tr}/20 {fmt(reasons_tr)}",
            "vola": f"{score_vola}/15 {fmt(reasons_vola)}",
            "str": f"{score_str}/10 {fmt(reasons_str)}",
            "raw_rsi": rsi.iloc[-1], "raw_macd": hist.iloc[-1],
            "raw_obv": obv.iloc[-1], "raw_atr": atr.iloc[-1]
        }
    except:
        return None

def get_deep_xray_data(ticker):
    sent = calculate_sentiment_score(ticker)
    if not sent: return None
    def icon(cond): return "✅" if cond else "❌"
    return {
        "mom_rsi": f"{icon(sent['raw_rsi']>50)} RSI Trendi",
        "mom_macd": f"{icon(sent['raw_macd']>0)} MACD Hist",
        "vol_obv": f"{icon('OBV ↑' in sent['vol'])} OBV Akışı",
        "tr_ema": f"{icon('GoldCross' in sent['tr'])} EMA Dizilimi",
        "tr_adx": f"{icon('P > SMA50' in sent['tr'])} Trend Gücü",
        "vola_bb": f"{icon('BB Break' in sent['vola'])} BB Sıkışması",
        "str_bos": f"{icon('BOS ↑' in sent['str'])} Yapı Kırılımı"
    }

# --- DÜZELTİLMİŞ: SENTETİK SENTIMENT (STP = SENTETİK FİYAT MANTIĞI) ---
# YENİ CMF TABANLI VE ORDINAL DATE DÜZELTMELİ FONKSİYON
# --- GÜNCELLEME: STP MANTIĞI KORUNDU, SADECE EKSEN VE CMF EKLENDİ ---
@st.cache_data(ttl=600)
def calculate_synthetic_sentiment(ticker):
    try:
        # 1. VERİ İNDİRME
        df = yf.download(ticker, period="6mo", progress=False)
        if df.empty: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if 'Close' not in df.columns: return None
        df = df.dropna()

        close = df['Close']
        high = df['High']
        low = df['Low']
        # Hacim 0 ise 1 yap (Bölme hatası önlemi)
        volume = df['Volume'].replace(0, 1) if 'Volume' in df.columns else pd.Series([1]*len(df), index=df.index)
        
        # -----------------------------------------------------------
        # 2. HESAPLAMA: CMF TABANLI PARA AKIŞI (SOL GRAFİK İÇİN)
        # -----------------------------------------------------------
        
        # A. CLV (Close Location Value)
        # Formül: ((Close - Low) - (High - Close)) / (High - Low)
        # Alternatif: (2*Close - High - Low) / (High - Low)
        range_len = high - low
        range_len = range_len.replace(0, 0.01) # Hata önleyici
        
        clv = ((2 * close) - high - low) / range_len
        
        # B. Smart Money Volume
        money_flow_vol = clv * volume
        
        # C. Yumuşatma (Flow Smooth - 3 Günlük EMA)
        mf_smooth = money_flow_vol.ewm(span=3, adjust=False).mean()

        # D. Smart Money Tespiti (RVOL Kontrolü)
        vol_avg_20 = volume.rolling(20).mean()
        is_smart_money = volume > vol_avg_20 # Hacim ortalamanın üstünde mi?

        # E. Renk Durumu (Status)
        status = []
        for i in range(len(df)):
            val = mf_smooth.iloc[i]
            smart = is_smart_money.iloc[i]
            
            if val >= 0: # GİRİŞ
                if smart: status.append("Güçlü Giriş") # Koyu Yeşil/Mavi
                else: status.append("Zayıf Giriş")     # Açık Yeşil/Mavi
            else: # ÇIKIŞ
                if smart: status.append("Güçlü Çıkış") # Koyu Kırmızı
                else: status.append("Zayıf Çıkış")     # Açık Kırmızı

        # -----------------------------------------------------------
        # 3. HESAPLAMA: STP (SAĞ GRAFİK İÇİN - AYNEN KORUNDU)
        # -----------------------------------------------------------
        typical_price = (high + low + close) / 3
        stp = typical_price.ewm(span=6, adjust=False).mean()
        
        # 4. DATAFRAME HAZIRLIĞI (SON 40 GÜN)
        df = df.reset_index()
        if 'Date' not in df.columns: df['Date'] = df.index
        else: df['Date'] = pd.to_datetime(df['Date'])
        
        plot_df = pd.DataFrame({
            'Date': df['Date'],
            'MF_Smooth': mf_smooth.values,
            'Status': status,
            'STP': stp.values,
            'Price': close.values
        }).tail(30).reset_index(drop=True) 

        # *** KRİTİK: HAFTA SONU BOŞLUĞUNU YOK ETMEK İÇİN STRING TARİH ***
        # Altair bu sütunu görünce "Ordinal" (Sıralı) moduna geçecek.
        plot_df['Date_Str'] = plot_df['Date'].dt.strftime('%d %b')
        
        return plot_df

    except Exception as e:
        return None

# YENİ GÖRSELLEŞTİRME PANELİ (GAP-FREE)
def render_synthetic_sentiment_panel(data):
    if data is None or data.empty: return

    # --- DEĞİŞİKLİK BAŞLANGICI ---
    # Ticker adını alıp temizliyoruz (Örn: .IS veya =F uzantılarını atar)
    display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")

    st.markdown(f"""
    <div class="info-card" style="margin-bottom:10px;">
        <div class="info-header">🌊 Para Akış İvmesi & Fiyat Dengesi: {display_ticker}</div>
    </div>
    """, unsafe_allow_html=True)
    # --- DEĞİŞİKLİK BİTİŞİ ---

    c1, c2 = st.columns([1, 1])
    
    # Ortak X Ekseni (Ordinal - Sıralı - Boşluksuz)
    # sort=None: Verinin geliş sırasını korur (Kronolojik), alfabetik yapmaz.
    x_axis = alt.X('Date_Str', axis=alt.Axis(title=None, labelAngle=-45), sort=None)

    with c1:
        # SOL GRAFİK: Para Akış Barları (Smart Money Renkli)
        base = alt.Chart(data).encode(x=x_axis)
        
        # Renk Skalası (User Preference: Indigo/Red)
        color_scale = alt.Color('Status:N', scale=alt.Scale(
            domain=['Güçlü Giriş', 'Zayıf Giriş', 'Güçlü Çıkış', 'Zayıf Çıkış'],
            range=['#312e81', '#a5b4fc', '#881337', '#fca5a5'] 
            # Koyu Indigo, Açık Indigo, Koyu Kırmızı, Açık Kırmızı
        ), legend=None)

        bars = base.mark_bar(size=15, opacity=0.9).encode(
            y=alt.Y('MF_Smooth:Q', axis=alt.Axis(title='Akış Gücü', labels=False, titleColor='#4338ca')),
            color=color_scale,
            tooltip=['Date_Str', 'Price', 'Status', 'MF_Smooth']
        )
        
        # Fiyat Çizgisi (Referans)
        price_line = base.mark_line(color='#0f172a', strokeWidth=2).encode(
            y=alt.Y('Price:Q', scale=alt.Scale(zero=False), axis=alt.Axis(title='Fiyat', titleColor='#0f172a'))
        )
        
        chart_left = alt.layer(bars, price_line).resolve_scale(y='independent').properties(
            height=280, 
            title=alt.TitleParams("Sentiment Değişimi - Momentum", fontSize=11, color="#1e40af")
        )
        st.altair_chart(chart_left, use_container_width=True)

    with c2:
        # SAĞ GRAFİK: Fiyat Dengesi (STP vs Price) - AYNEN KORUNDU
        # Sadece X ekseni "Date_Str" oldu ki sol tarafla aynı boyda dursun.
        base2 = alt.Chart(data).encode(x=x_axis)
        
        # Denge Hattı (Sarı)
        line_stp = base2.mark_line(color='#fbbf24', strokeWidth=3).encode(
            y=alt.Y('STP:Q', scale=alt.Scale(zero=False), axis=alt.Axis(title='Fiyat', titleColor='#64748B')),
            tooltip=['Date_Str', 'STP', 'Price']
        )
        
        # Fiyat (Turkuaz)
        line_price = base2.mark_line(color='#2dd4bf', strokeWidth=2).encode(
            y='Price:Q'
        )
        
        # Aradaki Farkı Boya (Deviasyon Alanı)
        area = base2.mark_area(opacity=0.15, color='gray').encode(
            y='STP:Q',
            y2='Price:Q'
        )
        
        chart_right = alt.layer(area, line_stp, line_price).properties(
            height=280, 
            title=alt.TitleParams("Fiyat Dengesi (STP) Turkuaz Sarıyı Yukarı Keserse AL", fontSize=11, color="#b45309")
        )
        st.altair_chart(chart_right, use_container_width=True)


# --- ICT GELISTIRILMIS (HYBRID TERMINOLOGY + MAKYYAJ) ---
@st.cache_data(ttl=600)
def calculate_ict_concepts(ticker):
    try:
        # Veri çekme (Daha sağlıklı analiz için 1 yıllık veri)
        df = yf.download(ticker, period="1y", progress=False)
        if df.empty: return None
        
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
            
        close = df['Close']
        high = df['High']
        low = df['Low']
        open_ = df['Open'] # Order Block İçin Eklendi
        
        if len(df) < 60: return {"summary": "Veri Yetersiz"}

        curr_price = float(close.iloc[-1])
        
        # --- 1. SWING NOKTALARI (Fractals) ---
        sw_highs = []
        sw_lows = []
        
        # Son mum hariç tarıyoruz (repaint olmaması için en az 2 mum geriden gelmeli)
        for i in range(2, len(df)-2):
            # Swing High
            if (high.iloc[i] > high.iloc[i-1] and high.iloc[i] > high.iloc[i-2] and 
                high.iloc[i] > high.iloc[i+1] and high.iloc[i] > high.iloc[i+2]):
                sw_highs.append((df.index[i], float(high.iloc[i]), i))
            
            # Swing Low
            if (low.iloc[i] < low.iloc[i-1] and low.iloc[i] < low.iloc[i-2] and 
                low.iloc[i] < low.iloc[i+1] and low.iloc[i] < low.iloc[i+2]):
                sw_lows.append((df.index[i], float(low.iloc[i]), i))

        if not sw_highs or not sw_lows: return {"summary": "Swing Bulunamadı"}

        last_sh = sw_highs[-1][1]
        last_sl = sw_lows[-1][1]

        # --- 2. MARKET YAPISI & RANGE ---
        # Dealing Range: En son oluşan Swing High ile Swing Low arası
        # Son oluşan hangisi ise (High mı Low mu?) ona göre range belirlenir
        last_sh_idx = sw_highs[-1][2]
        last_sl_idx = sw_lows[-1][2]
        
        r_high = last_sh
        r_low = last_sl
        
        structure = "YATAY"
        bias_color = "gray"

        # Basit BOS Mantığı
        if curr_price > last_sh:
            structure = "BOS (Bullish - Yükseliş)"
            bias_color = "green"
        elif curr_price < last_sl:
            structure = "BOS (Bearish - Düşüş)"
            bias_color = "red"
        else:
            if last_sh_idx > last_sl_idx: # En son tepe yapmış, düşüyor veya düzeltmede
                structure = "Internal Range (Düşüş/Düzeltme)"
                bias_color = "blue"
            else: # En son dip yapmış, yükseliyor
                structure = "Internal Range (Yükseliş)"
                bias_color = "blue"

        # --- 3. PREMIUM / DISCOUNT / OTE ---
        range_size = r_high - r_low
        if range_size == 0: range_size = 1 # Sıfıra bölünme hatası önlemi
        
        range_pos_pct = ((curr_price - r_low) / range_size) * 100
        
        pos_label = "Equilibrium"
        is_discount = False
        is_ote = False
        
        if range_pos_pct > 50:
            if range_pos_pct > 62 and range_pos_pct < 79:
                pos_label = "Premium (OTE Bölgesi)"
                is_ote = True
            else:
                pos_label = "Premium (Pahalı)"
            is_discount = False
        else:
            if range_pos_pct > 21 and range_pos_pct < 38:
                pos_label = "Discount (OTE Bölgesi)"
                is_ote = True
            else:
                pos_label = "Discount (Ucuz)"
            is_discount = True

        # --- 4. GELİŞMİŞ FVG TARAMASI (Mitigation Kontrollü) ---
        active_fvg = "Yok / Dengeli"
        fvg_color = "gray"
        
        # Son 50 mumu tara
        lookback_candles = 50
        bullish_fvgs = []
        bearish_fvgs = []

        start_idx = max(0, len(df) - lookback_candles)
        
        for i in range(start_idx, len(df)-2):
            # Bullish FVG: Mum(i) Low > Mum(i-2) High
            if low.iloc[i] > high.iloc[i-2]:
                gap_top = low.iloc[i]
                gap_bot = high.iloc[i-2]
                gap_size = gap_top - gap_bot
                
                # Mitigasyon Kontrolü: Bu FVG oluştuktan sonraki mumlar içine girdi mi?
                is_mitigated = False
                for k in range(i+1, len(df)):
                    if low.iloc[k] <= gap_top: # Fiyat boşluğa girmiş
                        # Tamamen doldurulmuş mu? (Tercihe bağlı, şimdilik içine girmesi yeterli)
                        is_mitigated = True
                        break
                
                if not is_mitigated:
                    bullish_fvgs.append({'top': gap_top, 'bot': gap_bot, 'idx': i})

            # Bearish FVG: Mum(i) High < Mum(i-2) Low
            if high.iloc[i] < low.iloc[i-2]:
                gap_top = low.iloc[i-2]
                gap_bot = high.iloc[i]
                
                # Mitigasyon Kontrolü: Bu FVG oluştuktan sonraki mumlar içine girdi mi?
                is_mitigated = False
                for k in range(i+1, len(df)):
                    if high.iloc[k] >= gap_bot: # Fiyat boşluğa girmiş
                        is_mitigated = True
                        break
                
                if not is_mitigated:
                    bearish_fvgs.append({'top': gap_top, 'bot': gap_bot, 'idx': i})

        # En yakın FVG'yi seç
        # Discount bölgesindeysek Alıcı FVG'leri (Bullish), Premium'daysak Satıcı FVG'leri (Bearish) öncelikli
        
        if is_discount and bullish_fvgs:
            # En son oluşan Bullish FVG
            fvg = bullish_fvgs[-1]
            active_fvg = f"BISI (Destek): {fvg['bot']:.2f} - {fvg['top']:.2f}"
            fvg_color = "green"
        elif not is_discount and bearish_fvgs:
            # En son oluşan Bearish FVG
            fvg = bearish_fvgs[-1]
            active_fvg = f"SIBI (Direnç): {fvg['bot']:.2f} - {fvg['top']:.2f}"
            fvg_color = "red"
        else:
            # Bölgeye uymasa da en yakını göster
            if bullish_fvgs:
                active_fvg = f"Açık FVG (Destek): {bullish_fvgs[-1]['bot']:.2f}"
                fvg_color = "green"
            elif bearish_fvgs:
                active_fvg = f"Açık FVG (Direnç): {bearish_fvgs[-1]['bot']:.2f}"
                fvg_color = "red"

        # --- 5. LİKİDİTE ---
        next_bsl = min([h[1] for h in sw_highs if h[1] > curr_price], default=None)
        next_ssl = max([l[1] for l in sw_lows if l[1] < curr_price], default=None)
        
        liq_target = "Belirsiz"
        if structure.startswith("BOS (Bullish") and next_bsl:
            liq_target = f"BSL (Buy Side): {next_bsl:.2f}"
        elif structure.startswith("BOS (Bearish") and next_ssl:
            liq_target = f"SSL (Sell Side): {next_ssl:.2f}"
        else:
             # Fiyata en yakın olan
            dist_bsl = abs(next_bsl - curr_price) if next_bsl else 99999
            dist_ssl = abs(curr_price - next_ssl) if next_ssl else 99999
            liq_target = f"Hedef: {next_bsl:.2f}" if dist_bsl < dist_ssl else f"Hedef: {next_ssl:.2f}"

        # --- 6. ORDER BLOCK (YENİ) ---
        active_ob = "Yok / Uzak"
        ob_color = "gray"
        
        # Sadece Trendin Yönüne Göre OB Tara (Verimlilik İçin)
        # Sondan başa doğru (En yeni OB en değerlisidir)
        search_range = range(len(df)-3, max(0, len(df)-60), -1)
        
        found_ob = False
        
        # Bullish Senaryo: Trend Yukarı veya Discount Bölgesindeyiz -> Bullish OB Ara
        if bias_color == "green" or bias_color == "blue" or is_discount:
            for i in search_range:
                # Kırmızı Mum (Düşüş)
                if close.iloc[i] < open_.iloc[i]:
                    # Displacement Kontrolü: Sonraki mum güçlü yeşil mi?
                    # Basit kural: Sonraki mumun kapanışı, bu mumun yükseğini geçti mi?
                    if i+1 < len(df) and close.iloc[i+1] > high.iloc[i]:
                        # İhlal Kontrolü: Fiyat şu an bu OB'nin altına inmiş mi?
                        ob_low = low.iloc[i]
                        ob_high = high.iloc[i]
                        
                        if curr_price > ob_high: # Fiyat hala üzerinde (Geçerli)
                            # Mitigasyon (Test) Kontrolü
                            is_tested = False
                            for k in range(i+2, len(df)):
                                if low.iloc[k] <= ob_high:
                                    is_tested = True
                                    break
                            
                            status = "Test Edildi" if is_tested else "Taze"
                            active_ob = f"{ob_low:.2f} - {ob_high:.2f} (Bullish - {status})"
                            ob_color = "green"
                            found_ob = True
                            break # En yakınını bulduk, çık
        
        # Bearish Senaryo: Trend Aşağı veya Premium Bölgesindeyiz -> Bearish OB Ara (Eğer Bullish bulunamadıysa)
        if not found_ob and (bias_color == "red" or bias_color == "blue" or not is_discount):
            for i in search_range:
                # Yeşil Mum (Yükseliş)
                if close.iloc[i] > open_.iloc[i]:
                    # Displacement: Sonraki mum güçlü kırmızı mı?
                    if i+1 < len(df) and close.iloc[i+1] < low.iloc[i]:
                        # İhlal Kontrolü
                        ob_low = low.iloc[i]
                        ob_high = high.iloc[i]
                        
                        if curr_price < ob_low: # Fiyat hala altında (Geçerli)
                            # Mitigasyon
                            is_tested = False
                            for k in range(i+2, len(df)):
                                if high.iloc[k] >= ob_low:
                                    is_tested = True
                                    break
                                
                            status = "Test Edildi" if is_tested else "Taze"
                            active_ob = f"{ob_low:.2f} - {ob_high:.2f} (Bearish - {status})"
                            ob_color = "red"
                            found_ob = True
                            break

        # --- 7. GOLDEN SETUP KARARI ---
        golden_txt = "İzlemede (Setup Yok)"
        is_golden = False
        
        # Bullish Golden: Discount + Bullish FVG + Yükseliş Yapısı
        if is_discount and bias_color == "green" and fvg_color == "green":
            golden_txt = "🔥 LONG FIRSATI (Trend + Ucuz + FVG)"
            is_golden = True
        # Bearish Golden: Premium + Bearish FVG + Düşüş Yapısı
        elif not is_discount and bias_color == "red" and fvg_color == "red":
            golden_txt = "❄️ SHORT FIRSATI (Trend + Pahalı + FVG)"
            is_golden = True
        elif is_ote:
             golden_txt = "⚖️ OTE Bölgesi (Karar Anı)"

        return {
            "structure": structure,
            "bias_color": bias_color,
            "range_pos_pct": range_pos_pct,
            "pos_label": pos_label,
            "fvg": active_fvg,
            "fvg_color": fvg_color,
            "ob": active_ob, # Order Block Verisi
            "ob_color": ob_color,
            "liquidity": liq_target,
            "golden_text": golden_txt,
            "is_golden": is_golden,
            "ote_level": is_ote,
            "range_high": r_high,
            "range_low": r_low,
             "summary": "OK"
        }

    except Exception as e:
        return {"summary": "Hata", "err": str(e)}

# --- YENİ GELİŞMİŞ TEKNİK KART (TradingView Yerine Gelecek) ---
def render_detail_card_advanced(ticker):
    # Ticker adını alıp başlığa ekliyoruz (GÖRSEL DÜZENLEME)
    display_ticker = ticker.replace(".IS", "").replace("=F", "")
    
    # 1. TEMEL VERİLERİ ÇEK
    dt = get_tech_card_data(ticker)
    info = fetch_stock_info(ticker)
    
    ma_vals = "Veri Yok"
    stop_vals = "Veri Yok"
    price_val = "Veri Yok"
    
    if dt and info:
        price_val = f"{info['price']:.2f}"
        ma_vals = f"SMA50: {dt['sma50']:.2f} | EMA144: {dt['ema144']:.2f}"
        stop_vals = f"{dt['stop_level']:.2f} (Risk: %{dt['risk_pct']:.1f})"

    # 2. RADAR SONUÇLARINI BUL (Listeden çekip detaylarını alacağız)
    # Burada tekrar hesaplama yapmamak için session_state'deki cached result'a bakabiliriz
    # Veya tekil hisse için hızlıca hesaplatabiliriz (Daha güvenli)
    
    # Radar 1 Sonucu
    r1_res = None
    # scan_data içinde var mı diye bak
    if st.session_state.scan_data is not None:
        row = st.session_state.scan_data[st.session_state.scan_data["Sembol"] == ticker]
        if not row.empty:
            # Detaylar sütunu varsa oradan al, yoksa tekrar hesapla
            if "Detaylar" in row.columns:
                r1_res = row.iloc[0]["Detaylar"]
                r1_score = row.iloc[0]["Skor"]
    
    # Eğer session'da yoksa anlık hesapla (Sadece tek hisse için çok hızlıdır)
    if r1_res is None:
        # analyze_market_intelligence fonksiyonu dataframe dönüyor, biz içindeki process_symbol mantığını manuel çalıştıralım
        # Ama o fonksiyon iç içe, o yüzden direk listeyi verip çağıralım
        temp_df = analyze_market_intelligence([ticker])
        if not temp_df.empty and "Detaylar" in temp_df.columns:
            r1_res = temp_df.iloc[0]["Detaylar"]
            r1_score = temp_df.iloc[0]["Skor"]
        else:
            r1_res = {} # Boşsa
            r1_score = 0

    # Radar 2 Sonucu
    r2_res = None
    if st.session_state.radar2_data is not None:
        row = st.session_state.radar2_data[st.session_state.radar2_data["Sembol"] == ticker]
        if not row.empty:
            if "Detaylar" in row.columns:
                r2_res = row.iloc[0]["Detaylar"]
                r2_score = row.iloc[0]["Skor"]
                
    if r2_res is None:
        temp_df2 = radar2_scan([ticker])
        if not temp_df2.empty and "Detaylar" in temp_df2.columns:
            r2_res = temp_df2.iloc[0]["Detaylar"]
            r2_score = temp_df2.iloc[0]["Skor"]
        else:
            r2_res = {}
            r2_score = 0

    # 3. HTML OLUŞTURMA
    def get_icon(val): return "✅" if val else "❌"
    
    # Radar 1 HTML
    r1_html = ""
    if r1_res:
        items = list(r1_res.items())
        # İki sütunlu yapı
        for i in range(0, len(items), 2):
            k1, v1 = items[i]
            row_html = f"<div class='tech-item'>{get_icon(v1)} <b>{k1}</b></div>"
            if i+1 < len(items):
                k2, v2 = items[i+1]
                row_html += f"<div class='tech-item'>{get_icon(v2)} <b>{k2}</b></div>"
            r1_html += row_html

    # Radar 2 HTML
    r2_html = ""
    if r2_res:
        items = list(r2_res.items())
        for i in range(0, len(items), 2):
            k1, v1 = items[i]
            row_html = f"<div class='tech-item'>{get_icon(v1)} <b>{k1}</b></div>"
            if i+1 < len(items):
                k2, v2 = items[i+1]
                row_html += f"<div class='tech-item'>{get_icon(v2)} <b>{k2}</b></div>"
            r2_html += row_html

    # Kartın Kendisi
    st.markdown(f"""
    <div class="info-card">
        <div class="info-header">📋 Gelişmiş Teknik Kart: {display_ticker}</div>
        
        <div style="display:flex; justify-content:space-between; margin-bottom:8px; border-bottom:1px solid #e5e7eb; padding-bottom:4px;">
            <div style="font-size:0.8rem; font-weight:700; color:#1e40af;">Fiyat: {price_val}</div>
            <div style="font-size:0.7rem; color:#64748B;">{ma_vals}</div>
        </div>
        <div style="font-size:0.7rem; color:#991b1b; margin-bottom:8px;">🛑 Stop: {stop_vals}</div>

        <div style="background:#f0f9ff; padding:4px; border-radius:4px; margin-bottom:4px;">
            <div style="font-weight:700; color:#0369a1; font-size:0.75rem; margin-bottom:2px;">
                🧠 RADAR 1 (Momentum) - Skor: {r1_score}/8
            </div>
            <div class="tech-grid">
                {r1_html}
            </div>
        </div>

        <div style="background:#f0fdf4; padding:4px; border-radius:4px;">
            <div style="font-weight:700; color:#15803d; font-size:0.75rem; margin-bottom:2px;">
                🚀 RADAR 2 (Trend & Setup) - Skor: {r2_score}/6
            </div>
            <div class="tech-grid">
                {r2_html}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- ARAYÜZ (FİLTRELER YERİNDE SABİT) ---

# FILTRELER
col_cat, col_ass, col_search_in, col_search_btn = st.columns([1.5, 2, 2, 0.7])
try:
    cat_index = list(ASSET_GROUPS.keys()).index(st.session_state.category)
except ValueError:
    cat_index = 0

with col_cat:
    st.selectbox(
        "Kategori",
        list(ASSET_GROUPS.keys()),
        index=cat_index,
        key="selected_category_key",
        on_change=on_category_change,
        label_visibility="collapsed"
    )
with col_ass:
    opts = ASSET_GROUPS.get(st.session_state.category, ASSET_GROUPS[INITIAL_CATEGORY])
    try:
        asset_idx = opts.index(st.session_state.ticker)
    except ValueError:
        asset_idx = 0
    st.selectbox(
        "Varlık Listesi",
        opts,
        index=asset_idx,
        key="selected_asset_key",
        on_change=on_asset_change,
        label_visibility="collapsed",
        format_func=lambda x: x.replace(".IS", "") # BURASI: .IS'i ekranda gizler
    )
with col_search_in:
    st.text_input("Manuel", placeholder="Kod", key="manual_input_key", label_visibility="collapsed")
with col_search_btn:
    st.button("Ara", on_click=on_manual_button_click)

st.markdown("<hr style='margin-top:0.5rem; margin-bottom:0.5rem;'>", unsafe_allow_html=True)

# PROMPT TETİKLEYİCİ (GÜNCELLENMİŞ VE TEMİZLENMİŞ VERSİYON)
if 'generate_prompt' not in st.session_state:
    st.session_state.generate_prompt = False

if st.session_state.generate_prompt:
    t = st.session_state.ticker
    
    # 1. VERİLERİ SESSİZCE TOPLA (Resim çekmek yerine sayısal veriyi çekiyoruz)
    ict_data = calculate_ict_concepts(t) or {}
    sent_data = calculate_sentiment_score(t) or {}
    tech_data = get_tech_card_data(t) or {}
    
    # Radar verisini session_state'den güvenli çekelim
    radar_val = "Veri Yok"
    radar_setup = "Belirsiz"
    if st.session_state.radar2_data is not None:
        r_row = st.session_state.radar2_data[st.session_state.radar2_data['Sembol'] == t]
        if not r_row.empty:
            radar_val = f"{r_row.iloc[0]['Skor']}/8"
            radar_setup = r_row.iloc[0]['Setup']

    # HTML temizleme fonksiyonu (Prompt için)
    def clean_text(text):
        if not isinstance(text, str): return str(text)
        # Regex ile <...> arasındaki her şeyi sil
        return re.sub(r'<[^>]+>', '', text)

    # Verileri temizle
    mom_clean = clean_text(sent_data.get('mom', 'Veri Yok'))
    vol_clean = clean_text(sent_data.get('vol', 'Veri Yok'))

    # 2. DİNAMİK VE VERİ ODAKLI MEGA PROMPT
    prompt = f"""
*** SİSTEM ROLLERİ ***
Sen Dünya çapında tanınan, risk yönetimi uzmanı, ICT (Inner Circle Trader) ve Price Action ustası bir Algoritmik Tradersın.
Aşağıda {t} varlığı için terminalimden gelen HAM VERİLER var. Bunları yorumla.

*** 1. TEKNİK VERİLER (Rakamlara Güven) ***
- SMA50 Değeri: {tech_data.get('sma50', 'Bilinmiyor')}
- Teknik Stop Seviyesi (ATR): {tech_data.get('stop_level', 'Bilinmiyor')}
- Radar 2 Skoru: {radar_val}
- Radar Setup: {radar_setup}

*** 2. DUYGU VE MOMENTUM ***
- Sentiment Puanı: {sent_data.get('total', 0)}/100
- Momentum Durumu: {mom_clean}
- Hacim/Para Girişi: {vol_clean}

*** 3. ICT / KURUMSAL YAPILAR (KRİTİK) ***
- Market Yapısı: {ict_data.get('structure', 'Bilinmiyor')}
- Bölge (PD Array): {ict_data.get('pos_label', 'Bilinmiyor')} (Discount=Ucuz, Premium=Pahalı)
- Fiyatın Konumu: %{ict_data.get('range_pos_pct', 0):.1f} (0=Dip, 100=Tepe)
- Aktif FVG: {ict_data.get('fvg', 'Yok')}
- Hedef Likidite: {ict_data.get('liquidity', 'Belirsiz')}
- GOLDEN SETUP SİNYALİ: {ict_data.get('golden_text', 'Yok')}

*** GÖREVİN ***
Bu verileri analiz et. Eğer içinde çelişki varsa (Örn: Teknik AL derken Fiyat Premium'da mı?) analiz et ve işlem planı ver.
Kısa, net, maddeler halinde yaz. Yatırım tavsiyesi değildir deme, bir Swing Trader analisti gibi konuş.

ÇIKTI:
💡 ANALİZ: Yarım paragraflık Temel Analiz, P/E, PEG, 12 aylık analist beklentileri. 
🎯 YÖN: [LONG/SHORT/BEKLE]
💡 STRATEJİ: (Giriş yeri, Stop yeri, Hedef yeri)
⚠️ RİSK: (Gördüğün en büyük tehlike)
"""
    
    # Promptu Sidebar'da göster (Kopyalamaya hazır)
    with st.sidebar:
        st.code(prompt, language="text")
        st.success("Metin kopyalanmaya hazır! 📋")
    
    st.session_state.generate_prompt = False

# İÇERİK
info = fetch_stock_info(st.session_state.ticker)
col_left, col_right = st.columns([3, 1])

with col_left:
    if info and info['price']:
        sc1, sc2, sc3, sc4 = st.columns(4)
        cls = "delta-pos" if info['change_pct'] >= 0 else "delta-neg"
        sc1.markdown(
            f'<div class="stat-box-small"><p class="stat-label-small">FİYAT</p>'
            f'<p class="stat-value-small money-text">{info["price"]:.2f}'
            f'<span class="stat-delta-small {cls}">'
            f'{"+" if info["change_pct"]>=0 else ""}{info["change_pct"]:.2f}%'
            f'</span></p></div>',
            unsafe_allow_html=True
        )
        sc2.markdown(
            f'<div class="stat-box-small"><p class="stat-label-small">HACİM</p>'
            f'<p class="stat-value-small money-text">{info["volume"]/1e6:.1f}M</p></div>',
            unsafe_allow_html=True
        )
        sc3.markdown(
            f'<div class="stat-box-small"><p class="stat-label-small">HEDEF</p>'
            f'<p class="stat-value-small money-text">{info["target"]}</p></div>',
            unsafe_allow_html=True
        )
        sc4.markdown(
            f'<div class="stat-box-small"><p class="stat-label-small">SEKTÖR</p>'
            f'<p class="stat-value-small">{str(info["sector"])[:12]}</p></div>',
            unsafe_allow_html=True
        )
    
    st.write("")
    
    # --- MAKYYAJ DEĞİŞİKLİĞİ: PARA AKIŞ PANELİ YUKARI ÇEKİLDİ ---
    synth_data = calculate_synthetic_sentiment(st.session_state.ticker)
    if synth_data is not None and not synth_data.empty:
        render_synthetic_sentiment_panel(synth_data)

    # --- BURASI YENİ ALAN: TradingView Gitti, Yerine Gelişmiş Kart Geldi ---
    render_detail_card_advanced(st.session_state.ticker)
    
    # --- YENİ EKLENEN AJAN 3 ALANI (GÜNCELLENMİŞ TASARIM) ---
    st.markdown('<div class="info-header" style="margin-top: 15px; margin-bottom: 10px;">🕵️ Ajan 3: Breakout Tarayıcısı (Top 12)</div>', unsafe_allow_html=True)
    
    with st.expander("Taramayı Başlat / Sonuçları Göster", expanded=True):
        if st.button(f"⚡ {st.session_state.category} Tara", type="primary", key="a3_main_scan_btn"):
            with st.spinner("Ajan 3 piyasayı kokluyor..."):
                st.session_state.agent3_data = agent3_breakout_scan(ASSET_GROUPS.get(st.session_state.category, []))
        
        if st.session_state.agent3_data is not None and not st.session_state.agent3_data.empty:
            # LİMİT: Sadece ilk 12 hisse
            display_df = st.session_state.agent3_data.head(12)
            st.caption(f"En sıcak {len(display_df)} fırsat listeleniyor (Toplam Bulunan: {len(st.session_state.agent3_data)})")

            # IZGARA MANTIĞI: Döngüyle 3'erli satırlar oluştur
            for i, (index, row) in enumerate(display_df.iterrows()):
                # Her 3 elemanda bir yeni satır (st.columns) aç
                if i % 3 == 0:
                    cols = st.columns(3)
                
                # O anki sütunu seç (0, 1 veya 2)
                with cols[i % 3]:
                    # --- GÜVENLİ VERİ OKUMA ---
                    sym_raw = row.get("Sembol_Raw")
                    if not sym_raw:
                        sym_raw = row.get("Sembol", row.name if isinstance(row.name, str) else "Bilinmiyor")
                    
                    # --- EKSTRA ANALİZ VERİLERİNİ ÇEK ---
                    # Hız düşmemesi için sadece bu 12 hisse için anlık hesaplıyoruz
                    ict_vals = calculate_ict_concepts(sym_raw) or {}
                    tech_vals = get_tech_card_data(sym_raw) or {}

                    target_text = ict_vals.get('liquidity', 'Belirsiz')
                    stop_text = f"{tech_vals['stop_level']:.2f}" if tech_vals else "-"

                    # --- SİNYAL YÖNÜNÜ BELİRLE (RENKLENDİRME İÇİN) ---
                    # Sembol_Display veya Trend Durumu içinde "SHORT" geçiyor mu?
                    is_short = "SHORT" in str(row.get('Sembol_Display', '')) or "SHORT" in str(row.get('Trend Durumu', ''))
                    
                    if is_short:
                        # SHORT TASARIMI (Kırmızımsı)
                        card_bg = "#fef2f2" # Çok açık kırmızı
                        card_border = "#b91c1c" # Koyu kırmızı
                        btn_icon = "🔻"
                        signal_text = "SHORT"
                    else:
                        # LONG TASARIMI (Yeşilimsi)
                        card_bg = "#f0fdf4" # Çok açık yeşil
                        card_border = "#15803d" # Koyu yeşil
                        btn_icon = "🚀"
                        signal_text = "LONG"

                    # Buton Etiketi
                    btn_label = f"{btn_icon} {signal_text} | {sym_raw} | {row['Fiyat']}"

                    # Kart Başlığı (Buton Olarak)
                    if st.button(f"{btn_label}", key=f"a3_hdr_{sym_raw}_{i}", use_container_width=True):
                        on_scan_result_click(sym_raw)
                        st.rerun()

                    # Kart İçeriği (HTML - DİNAMİK RENKLENDİRME İLE)
                    # GÜNCELLEME: Burada indentation (boşluklar) temizlendi.
                    card_html = f"""
<div class="info-card" style="margin-top: 0px; height: 100%; background-color: {card_bg}; border: 1px solid {card_border}; border-top: 3px solid {card_border};">
<div class="info-row"><div class="label-short">Zirve:</div><div class="info-val">{row['Zirveye Yakınlık']}</div></div>
<div class="info-row"><div class="label-short">Hacim:</div><div class="info-val" style="color:#15803d;">{row['Hacim Durumu']}</div></div>
<div class="info-row"><div class="label-short">Trend:</div><div class="info-val">{row['Trend Durumu']}</div></div>
<div class="info-row"><div class="label-short">RSI:</div><div class="info-val">{row['RSI']}</div></div>
<div style="margin-top:8px; padding-top:4px; border-top:1px solid #e2e8f0; display:flex; justify-content:space-between; font-size:0.7rem;">
<div style="color:#166534;"><strong>🎯</strong> {target_text}</div>
<div style="color:#991b1b;"><strong>🛑 Stop:</strong> {stop_text}</div>
</div>
</div>
"""
                    st.markdown(card_html, unsafe_allow_html=True)
                
        elif st.session_state.agent3_data is not None:
            st.info("Kriterlere uyan hisse yok.")

    
    st.markdown(
        f"<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:20px;'>📡 {st.session_state.ticker} hakkında haberler ve analizler</div>",
        unsafe_allow_html=True
    )

    # --- HABER AKIŞI ---
    symbol_raw = st.session_state.ticker

    base_symbol = (
        symbol_raw.replace(".IS", "")
                  .replace("=F", "")
                  .replace("-USD", "")
    )
    lower_symbol = base_symbol.lower()

    seekingalpha_url    = f"https://seekingalpha.com/symbol/{base_symbol}/news"
    yahoo_url           = f"https://finance.yahoo.com/quote/{base_symbol}/news"
    nasdaq_url          = f"https://www.nasdaq.com/market-activity/stocks/{lower_symbol}/news-headlines"
    stockanalysis_url   = f"https://stockanalysis.com/stocks/{lower_symbol}/"
    finviz_url          = f"https://finviz.com/quote.ashx?t={base_symbol}&p=d"
    unusual_url         = f"https://unusualwhales.com/stock/{base_symbol}/overview"

    st.markdown(f"""
    <div class="news-card" style="display:flex; flex-wrap:wrap; align-items:center; gap:8px; border-left:none;">
        <a href="{seekingalpha_url}" target="_blank" style="text-decoration:none;">
            <div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.7rem; font-weight:600;">
                SeekingAlpha
            </div>
        </a>
        <a href="{yahoo_url}" target="_blank" style="text-decoration:none;">
            <div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.7rem; font-weight:600;">
                Yahoo Finance
            </div>
        </a>
        <a href="{nasdaq_url}" target="_blank" style="text-decoration:none;">
            <div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.7rem; font-weight:600;">
                Nasdaq
            </div>
        </a>
        <a href="{stockanalysis_url}" target="_blank" style="text-decoration:none;">
            <div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.7rem; font-weight:600;">
                StockAnalysis
            </div>
        </a>
        <a href="{finviz_url}" target="_blank" style="text-decoration:none;">
            <div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.7rem; font-weight:600;">
                Finviz
            </div>
        </a>
        <a href="{unusual_url}" target="_blank" style="text-decoration:none;">
            <div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.7rem; font-weight:600;">
                UnusualWhales
            </div>
        </a>
    </div>
    """, unsafe_allow_html=True)

with col_right:
    sent_data = calculate_sentiment_score(st.session_state.ticker)
    render_sentiment_card(sent_data)
    
    # ICT Panel
    ict_data = calculate_ict_concepts(st.session_state.ticker)
    render_ict_panel(ict_data)

    # --- DEĞİŞİKLİK BURADA: ÖNCE RÖNTGEN, SONRA RADAR ---
    
    # 1. Önce Derin Teknik Röntgen (Yukarı alındı)
    xray_data = get_deep_xray_data(st.session_state.ticker)
    render_deep_xray_card(xray_data)

    # 2. Sonra Radar Parametreleri (Aşağı alındı)
    render_radar_params_card() 
    
    # --- DEĞİŞİKLİK SONU ---

    st.markdown(
        f"<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:10px; color:#1e40af; background-color:{current_theme['box_bg']}; padding:5px; border-radius:5px; border:1px solid #1e40af;'>🎯 Ortak Fırsatlar</div>",
        unsafe_allow_html=True
    )
    with st.container(height=250):
        # ... (Geri kalan kodlar aynı) ...
        df1 = st.session_state.scan_data
        df2 = st.session_state.radar2_data
        
        if df1 is not None and df2 is not None and not df1.empty and not df2.empty:
            commons = []
            symbols = set(df1["Sembol"]).intersection(set(df2["Sembol"]))
            
            if symbols:
                for sym in symbols:
                    row1 = df1[df1["Sembol"] == sym].iloc[0]
                    row2 = df2[df2["Sembol"] == sym].iloc[0]
                    
                    r1_score = float(row1["Skor"])
                    r2_score = float(row2["Skor"])
                    combined_score = r1_score + r2_score
                    
                    commons.append({
                        "symbol": sym, 
                        "r1_score": r1_score,
                        "r2_score": r2_score,
                        "combined": combined_score,
                        "r1_max": 8,
                        "r2_max": 8
                    })
                
                sorted_commons = sorted(commons, key=lambda x: x["combined"], reverse=True)
                
                for i, item in enumerate(sorted_commons):
                    sym = item["symbol"]
                    
                    if i == 0: rank = "🥇"
                    elif i == 1: rank = "🥈"
                    elif i == 2: rank = "🥉"
                    else: rank = f"{i+1}."

                    score_text_safe = (
                        f"{rank} {sym} ({int(item['combined'])}/{item['r1_max'] + item['r2_max']}) | "
                        f"R1:{int(item['r1_score'])}/{item['r1_max']} | R2:{int(item['r2_score'])}/{item['r2_max']}"
                    )
                    
                    c1, c2 = st.columns([0.2, 0.8]) 
                    
                    is_watchlist = sym in st.session_state.watchlist
                    star_icon = "★" if is_watchlist else "☆"

                    if c1.button(star_icon, key=f"c_star_{sym}", help="İzleme Listesine Ekle/Kaldır"):
                        toggle_watchlist(sym)
                        st.rerun()
                    
                    if c2.button(score_text_safe, key=f"c_select_{sym}", help="Detaylar için seç"):
                        on_scan_result_click(sym)
                        st.rerun()

            else:
                st.info("Kesişim yok.")
        else:
            st.caption("İki radar da çalıştırılmalı.")

    st.markdown("<hr>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🧠 RADAR 1", "🚀 RADAR 2", "📜 İzleme"])
    
    with tab1:
        if st.button(f"⚡ {st.session_state.category} Tara", type="primary", key="r1_main_scan_btn"):
            with st.spinner("Taranıyor..."):
                st.session_state.scan_data = analyze_market_intelligence(ASSET_GROUPS.get(st.session_state.category, []))
        if st.session_state.scan_data is not None:
            with st.container(height=500):
                for i, row in st.session_state.scan_data.iterrows():
                    sym = row["Sembol"]
                    c1, c2 = st.columns([0.2, 0.8])
                    if c1.button("★", key=f"r1_{i}"):
                        toggle_watchlist(sym)
                        st.rerun()
                    if c2.button(f"🔥 {row['Skor']}/8 | {sym}", key=f"r1_b_{i}"):
                        on_scan_result_click(sym)
                        st.rerun()
                    st.caption(row['Nedenler'])

    with tab2:
        if st.button(f"🚀 RADAR 2 Tara", type="primary", key="r2_main_scan_btn"):
            with st.spinner("Taranıyor..."):
                st.session_state.radar2_data = radar2_scan(ASSET_GROUPS.get(st.session_state.category, []))
        if st.session_state.radar2_data is not None:
            with st.container(height=500):
                for i, row in st.session_state.radar2_data.iterrows():
                    sym = row["Sembol"]
                    c1, c2 = st.columns([0.2, 0.8])
                    if c1.button("★", key=f"r2_{i}"):
                        toggle_watchlist(sym)
                        st.rerun()
                    if c2.button(f"🚀 {row['Skor']}/8 | {sym} | {row['Setup']}", key=f"r2_b_{i}"):
                        on_scan_result_click(sym)
                        st.rerun()
                    st.caption(f"Trend: {row['Trend']} | RS: {row['RS']}%")

    with tab3:
        if st.button("⚡ Listeyi Tara", type="secondary", key="wl_main_scan_btn"):
            with st.spinner("..."):
                st.session_state.scan_data = analyze_market_intelligence(st.session_state.watchlist)
        for sym in st.session_state.watchlist:
            c1, c2 = st.columns([0.2, 0.8])
            if c1.button("❌", key=f"wl_d_{sym}"):
                toggle_watchlist(sym)
                st.rerun()
            if c2.button(sym, key=f"wl_g_{sym}"):
                on_scan_result_click(sym)
                st.rerun()
