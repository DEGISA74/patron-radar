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
import concurrent.futures
import re
import altair as alt
import random

# ==============================================================================
# 1. AYARLAR VE STİL
# ==============================================================================
st.set_page_config(
    page_title="SMART MONEY RADAR", 
    layout="wide",
    page_icon="💸"
)

# Tema Ayarları
if 'theme' not in st.session_state:
    st.session_state.theme = "Buz Mavisi"

THEMES = {
    "Beyaz": {"bg": "#FFFFFF", "box_bg": "#F8F9FA", "text": "#000000", "border": "#DEE2E6", "news_bg": "#FFFFFF"},
    "Kirli Beyaz": {"bg": "#FAF9F6", "box_bg": "#FFFFFF", "text": "#2C3E50", "border": "#E5E7EB", "news_bg": "#FFFFFF"},
    "Buz Mavisi": {"bg": "#F0F8FF", "box_bg": "#FFFFFF", "text": "#0F172A", "border": "#BFDBFE", "news_bg": "#FFFFFF"}
}

# KRİTİK: Değişkeni ÖNCE tanımlıyoruz
current_theme = THEMES[st.session_state.theme]

# 1. AYARLAR VE STİL BÖLÜMÜNDEKİ CSS BLOĞUNU BUNUNLA DEĞİŞTİR:
st.markdown(f"""
<style>
    section[data-testid="stSidebar"] {{ width: 350px !important; }}

    /* Metrik Yazı Tipleri */
    div[data-testid="stMetricValue"] {{ font-size: 0.7rem !important; }}
    div[data-testid="stMetricLabel"] {{ font-size: 0.7rem !important; font-weight: 700; }}
    div[data-testid="stMetricDelta"] {{ font-size: 0.7rem !important; }}

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght+400;700&display=swap');
    
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {current_theme['text']}; }}
    .stApp {{ background-color: {current_theme['bg']}; }}
    
    section.main > div.block-container {{ padding-top: 1rem; padding-bottom: 1rem; }}
    
    .stMetricValue, .money-text {{ font-family: 'JetBrains Mono', monospace !important; }}
    
    /* İstatistik Kutuları */
    .stat-box-small {{
        background: {current_theme['box_bg']}; border: 1px solid {current_theme['border']};
        border-radius: 4px; padding: 8px; text-align: center; margin-bottom: 10px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }}
    .stat-label-small {{ font-size: 0.6rem; color: #64748B; text-transform: uppercase; margin: 0; font-weight: 700; letter-spacing: 0.5px; }}
    .stat-value-small {{ font-size: 1.1rem; font-weight: 700; color: {current_theme['text']}; margin: 2px 0 0 0; }}
    .stat-delta-small {{ font-size: 0.8rem; margin-left: 6px; font-weight: 600; }}
    
    /* Genel Elementler */
    hr {{ margin-top: 0.2rem; margin-bottom: 0.5rem; }}
    .stSelectbox, .stTextInput {{ margin-bottom: -10px; }}
    .delta-pos {{ color: #16A34A; }} .delta-neg {{ color: #DC2626; }}
    .news-card {{ background: {current_theme['news_bg']}; border-left: 3px solid {current_theme['border']}; padding: 6px; margin-bottom: 6px; font-size: 0.78rem; }}
    
    button[data-testid="baseButton-primary"] {{ background-color: #1e40af !important; border-color: #1e40af !important; color: white !important; }}
    
    .stButton button {{ 
        width: 100%; border-radius: 4px;
        font-size: 0.75rem;
        padding: 0.1rem 0.4rem;
    }}
    
    /* Bilgi Kartları (Info Card) */
    .info-card {{
        background: {current_theme['box_bg']}; border: 1px solid {current_theme['border']};
        border-radius: 6px; 
        padding: 6px;
        margin-top: 5px; 
        margin-bottom: 5px;
        font-size: 0.8rem;
        font-family: 'Inter', sans-serif;
    }}
    .info-header {{ font-weight: 700; color: #1e3a8a; border-bottom: 1px solid {current_theme['border']}; padding-bottom: 4px; margin-bottom: 4px; }}
    .info-row {{ display: flex; align-items: flex-start; margin-bottom: 2px; }}
    
    .label-short {{ font-weight: 600; color: #64748B; width: 80px; flex-shrink: 0; }}
    .label-long {{ font-weight: 600; color: #64748B; width: 100px; flex-shrink: 0; }} 
    
    .info-val {{ color: {current_theme['text']}; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; }}
    
    /* İŞTE SENİN SEVDİĞİN SADE YAZI STİLİ BU */
    .edu-note {{
        font-size: 0.75rem;
        color: #64748B;
        font-style: italic;
        margin-top: 2px;
        margin-bottom: 6px;
        line-height: 1.3;
        padding-left: 0px;
    }}

    .tech-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4px; }}
    .tech-item {{ display: flex; align-items: center; font-size: 0.8rem; }}

    .header-container {
        margin-top: 15px;
        margin-bottom: 5px;
    }
    .header-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1e3a8a;
        display: inline-block;
    }
    .header-subtitle {
        font-size: 0.75rem;
        color: #64748B;
        font-weight: 600;
        margin-left: 8px;
        display: inline-block;
        background-color: #f1f5f9;
        padding: 2px 6px;
        border-radius: 4px;
    }
    
</style>
""", unsafe_allow_html=True)
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

init_db()

# --- VARLIK LİSTELERİ ---
priority_sp = ["^GSPC", "^DJI", "^NDX", "^IXIC", "AGNC", "ARCC", "PFE", "JEPI", "MO", "EPD", "JEPQ"]

# S&P 500'ün Tamamı (503 Hisse - Güncel)
raw_sp500_rest = [
    "A", "AAL", "AAPL", "ABBV", "ABNB", "ABT", "ACGL", "ACN", "ADBE", "ADI", "ADM", "ADP", "ADSK", "AEE", "AEP", "AES", "AFL", "AIG", "AIZ", "AJG", 
    "AKAM", "ALB", "ALGN", "ALL", "ALLE", "AMAT", "AMCR", "AMD", "AME", "AMGN", "AMP", "AMT", "AMTM", "AMZN", "ANET", "ANSS", "AON", "AOS", "APA", 
    "APD", "APH", "APTV", "ARE", "ATO", "AVB", "AVGO", "AVY", "AWK", "AXON", "AXP", "AZO", "BA", "BAC", "BALL", "BAX", "BBWI", "BBY", "BDX", "BEN", 
    "BF-B", "BG", "BIIB", "BK", "BKNG", "BKR", "BLDR", "BLK", "BMY", "BR", "BRK-B", "BRO", "BSX", "BWA", "BX", "BXP", "C", "CAG", "CAH", "CARR", 
    "CAT", "CB", "CBOE", "CBRE", "CCI", "CCL", "CDNS", "CDW", "CE", "CEG", "CF", "CFG", "CHD", "CHRW", "CHTR", "CI", "CINF", "CL", "CLX", "CMCSA", 
    "CME", "CMG", "CMI", "CMS", "CNC", "CNP", "COF", "COO", "COP", "COR", "COST", "CPAY", "CPB", "CPRT", "CPT", "CRL", "CRM", "CRWD", "CSCO", 
    "CSGP", "CSX", "CTAS", "CTRA", "CTSH", "CTVA", "CVS", "CVX", "CZR", "D", "DAL", "DAY", "DD", "DE", "DECK", "DFS", "DG", "DGX", "DHI", "DHR", 
    "DIS", "DLR", "DLTR", "DOC", "DOV", "DOW", "DPZ", "DRI", "DTE", "DUK", "DVA", "DVN", "DXCM", "EA", "EBAY", "ECL", "ED", "EFX", "EG", "EIX", 
    "EL", "ELV", "EMN", "EMR", "ENPH", "EOG", "EQIX", "EQR", "EQT", "ERIE", "ES", "ESS", "ETN", "ETR", "EVRG", "EW", "EXC", "EXPD", "EXPE", "EXR", 
    "F", "FANG", "FAST", "FCX", "FDS", "FDX", "FE", "FFIV", "FI", "FICO", "FIS", "FITB", "FMC", "FOX", "FOXA", "FRT", "FSLR", "FTNT", "FTV", "GD", 
    "GE", "GEHC", "GEN", "GEV", "GILD", "GIS", "GL", "GLW", "GM", "GNRC", "GOOG", "GOOGL", "GPC", "GPN", "GRMN", "GS", "GWW", "HAL", "HAS", "HBAN", 
    "HCA", "HD", "HES", "HIG", "HII", "HLT", "HOLX", "HON", "HPE", "HPQ", "HRL", "HSY", "HUBB", "HUM", "HWM", "IBM", "ICE", "IDXX", "IEX", "IFF", 
    "ILMN", "INCY", "INTC", "INTU", "INVH", "IP", "IPG", "IQV", "IR", "IRM", "ISRG", "IT", "ITW", "IVZ", "J", "JBHT", "JBL", "JCI", "JKHY", "JNJ", 
    "JNPR", "JPM", "K", "KDP", "KEY", "KEYS", "KHC", "KIM", "KKR", "KLAC", "KMB", "KMI", "KMX", "KO", "KR", "KVUE", "L", "LDOS", "LEN", "LH", 
    "LHX", "LIN", "LKQ", "LLY", "LMT", "LNT", "LOW", "LRCX", "LULU", "LUV", "LVS", "LW", "LYB", "LYV", "MA", "MAA", "MAR", "MAS", "MCD", "MCHP", 
    "MCK", "MCO", "MDLZ", "MDT", "MET", "META", "MGM", "MHK", "MKC", "MKTX", "MLM", "MMC", "MMM", "MNST", "MO", "MOH", "MOS", "MPC", "MPWR", "MRK", 
    "MRNA", "MS", "MSCI", "MSFT", "MSI", "MTB", "MTCH", "MTD", "MU", "NCLH", "NDSN", "NEE", "NEM", "NFLX", "NI", "NKE", "NOC", "NOW", "NRG", "NSC", 
    "NTAP", "NTRS", "NUE", "NVDA", "NVR", "NWS", "NWSA", "NXPI", "O", "ODFL", "OKE", "OMC", "ON", "ORCL", "ORLY", "OTIS", "OXY", "PANW", "PARA", 
    "PAYC", "PAYX", "PCAR", "PCG", "PEG", "PEP", "PFE", "PFG", "PG", "PGR", "PH", "PHM", "PKG", "PLD", "PLTR", "PM", "PNC", "PNR", "PNW", "POOL", 
    "PPG", "PPL", "PRU", "PSA", "PSX", "PTC", "PWR", "PYPL", "QCOM", "QQQI", "QRVO", "RCL", "REG", "REGN", "RF", "RJF", "RL", "RMD", "ROK", "ROL", "ROP", 
    "ROST", "RSG", "RTX", "RVTY", "SBAC", "SBUX", "SCHW", "SHW", "SJM", "SLB", "SMCI", "SNA", "SNPS", "SO", "SOLV", "SPG", "SPGI", "SRCL", "SRE", 
    "STE", "STLD", "STT", "STX", "STZ", "SW", "SWK", "SWKS", "SYF", "SYK", "SYY", "T", "TAP", "TDG", "TDY", "TECH", "TEL", "TER", "TFC", "TFX", 
    "TGT", "TJX", "TMO", "TMUS", "TPR", "TRGP", "TRMB", "TROW", "TRV", "TSCO", "TSLA", "TSN", "TT", "TTWO", "TXN", "TXT", "TYL", "UAL", "UBER", 
    "UDR", "UHS", "ULTA", "UNH", "UNP", "UPS", "URI", "USB", "V", "VICI", "VLO", "VLTO", "VMC", "VRSK", "VRSN", "VRTX", "VTR", "VTRS", "VZ", 
    "WAB", "WAT", "WBA", "WBD", "WDC", "WEC", "WELL", "WFC", "WM", "WMB", "WMT", "WRB", "WRK", "WST", "WTW", "WY", "WYNN", "XEL", "XOM", "XYL", 
    "YUM", "ZBH", "ZBRA", "ZTS"
]

# Kopyaları Temizle ve Birleştir
raw_sp500_rest = list(set(raw_sp500_rest) - set(priority_sp))
raw_sp500_rest.sort()
final_sp500_list = priority_sp + raw_sp500_rest

priority_crypto = ["BTC-USD", "ETH-USD"]
other_crypto = [
    "BNB-USD", "SOL-USD", "XRP-USD", "ADA-USD", "DOGE-USD", "AVAX-USD", "TRX-USD", 
    "LINK-USD", "DOT-USD", "MATIC-USD", "LTC-USD", "BCH-USD", "UNI-USD", "ATOM-USD", 
    "XLM-USD", "ETC-USD", "FIL-USD", "HBAR-USD", "APT-USD", "NEAR-USD", "VET-USD", 
    "QNT-USD", "AAVE-USD", "ALGO-USD"
]
other_crypto.sort()
final_crypto_list = priority_crypto + other_crypto

raw_nasdaq = [
    "AAPL", "MSFT", "NVDA", "AMZN", "AVGO", "META", "TSLA", "GOOGL", "GOOG", "COST", 
    "NFLX", "AMD", "PEP", "LIN", "TMUS", "CSCO", "QCOM", "INTU", "AMAT", "TXN", 
    "HON", "AMGN", "BKNG", "ISRG", "CMCSA", "SBUX", "MDLZ", "GILD", "ADP", "ADI", 
    "REGN", "VRTX", "LRCX", "PANW", "MU", "KLAC", "SNPS", "CDNS", "MELI", "MAR", 
    "ORLY", "CTAS", "NXPI", "CRWD", "CSX", "PCAR", "MNST", "WDAY", "ROP", "AEP", 
    "ROKU", "ZS", "OKTA", "TEAM", "DDOG", "MDB", "SHOP", "EA", "TTD", "DOCU", 
    "INTC", "SGEN", "ILMN", "IDXX", "ODFL", "EXC", "ADSK", "PAYX", "CHTR", "MRVL", 
    "KDP", "XEL", "LULU", "ALGN", "VRSK", "CDW", "DLTR", "SIRI", "JBHT", "WBA", 
    "PDD", "JD", "BIDU", "NTES", "NXST", "MTCH", "UAL", "SPLK", "ANSS", "SWKS", 
    "QRVO", "AVTR", "FTNT", "ENPH", "SEDG", "BIIB", "CSGP"
]
raw_nasdaq = sorted(list(set(raw_nasdaq)))

# --- BIST 100 LİSTESİ ---
priority_bist_indices = ["XU100.IS", "XU030.IS", "XBANK.IS", "EREGL.IS", "SISE.IS", "TUPRS.IS"]
raw_bist_stocks = [
    "AEFES.IS", "AGHOL.IS", "AHGAZ.IS", "AKBNK.IS", "AKCNS.IS", "AKFGY.IS", "AKFYE.IS", "AKSA.IS", 
    "AKSEN.IS", "ALARK.IS", "ALBRK.IS", "ALFAS.IS", "ANSGR.IS", "ARCLK.IS", "ASELS.IS", 
    "ASTOR.IS", "BERA.IS", "BIMAS.IS", "BIOEN.IS", "BOBET.IS", "BRSAN.IS", "BRYAT.IS", "BUCIM.IS", 
    "CANTE.IS", "CCOLA.IS", "CEMTS.IS", "CIMSA.IS", "CWENE.IS", "DOAS.IS", "DOHOL.IS", "ECILC.IS", 
    "ECZYT.IS", "EGEEN.IS", "EKGYO.IS", "ENJSA.IS", "ENKAI.IS", "EUREN.IS", 
    "EUPWR.IS", "FENER.IS", "FROTO.IS", "GARAN.IS", "GENIL.IS", "GESAN.IS", "GLYHO.IS", "GOKNR.IS", 
    "GUBRF.IS", "GWIND.IS", "HALKB.IS", "HEKTS.IS", "IPEKE.IS", "ISCTR.IS", "ISDMR.IS", 
    "ISGYO.IS", "ISMEN.IS", "IZENR.IS", "KCAER.IS", "KCHOL.IS", "KLSER.IS", "KONTR.IS", "KONYA.IS", 
    "KORDS.IS", "KOZAA.IS", "KOZAL.IS", "KRDMD.IS", "KZBGY.IS", "MAVI.IS", "MGROS.IS", 
    "MIATK.IS", "ODAS.IS", "OTKAR.IS", "OYAKC.IS", "PENTA.IS", "PETKM.IS", "PGSUS.IS", 
    "PSGYO.IS", "QUAGR.IS", "REEDR.IS", "SAHOL.IS", "SASA.IS", "SDTTR.IS", "SKBNK.IS", 
    "SMRTG.IS", "SOKM.IS", "TABGD.IS", "TAVHL.IS", "TCELL.IS", "THYAO.IS", "TKFEN.IS", "TOASO.IS", 
    "TSKB.IS", "TTKOM.IS", "TTRAK.IS", "TUKAS.IS", "TURSG.IS", "ULUUN.IS", "VAKBNK.IS", 
    "VESBE.IS", "VESTL.IS", "YEOTK.IS", "YKBNK.IS", "YLALI.IS", "ZOREN.IS"
]
# Öncelikli listede olanları ana listeden çıkar (Kopyaları engeller)
raw_bist_stocks = list(set(raw_bist_stocks) - set(priority_bist_indices))
raw_bist_stocks.sort()
final_bist100_list = priority_bist_indices + raw_bist_stocks

ASSET_GROUPS = {
    "S&P 500": final_sp500_list,
    "NASDAQ-100": raw_nasdaq,
    "BIST 100": final_bist100_list,
    "KRİPTO-TOP 25": final_crypto_list
}
INITIAL_CATEGORY = "S&P 500"

# --- STATE YÖNETİMİ ---
if 'category' not in st.session_state: st.session_state.category = INITIAL_CATEGORY
if 'ticker' not in st.session_state: st.session_state.ticker = "^GSPC"
if 'scan_data' not in st.session_state: st.session_state.scan_data = None
if 'generate_prompt' not in st.session_state: st.session_state.generate_prompt = False
if 'radar2_data' not in st.session_state: st.session_state.radar2_data = None
if 'watchlist' not in st.session_state: st.session_state.watchlist = load_watchlist_db()
if 'stp_scanned' not in st.session_state: st.session_state.stp_scanned = False
if 'stp_crosses' not in st.session_state: st.session_state.stp_crosses = []
if 'stp_trends' not in st.session_state: st.session_state.stp_trends = []
if 'stp_filtered' not in st.session_state: st.session_state.stp_filtered = []
if 'accum_data' not in st.session_state: st.session_state.accum_data = None
if 'breakout_left' not in st.session_state: st.session_state.breakout_left = None
if 'breakout_right' not in st.session_state: st.session_state.breakout_right = None

# --- CALLBACKLER ---
def on_category_change():
    new_cat = st.session_state.get("selected_category_key")
    if new_cat and new_cat in ASSET_GROUPS:
        st.session_state.category = new_cat
        st.session_state.ticker = ASSET_GROUPS[new_cat][0]
        st.session_state.scan_data = None
        st.session_state.radar2_data = None
        st.session_state.stp_scanned = False
        st.session_state.accum_data = None 
        st.session_state.breakout_left = None
        st.session_state.breakout_right = None

def on_asset_change():
    new_asset = st.session_state.get("selected_asset_key")
    if new_asset: st.session_state.ticker = new_asset

def on_manual_button_click():
    if st.session_state.manual_input_key:
        st.session_state.ticker = st.session_state.manual_input_key.upper()

def on_scan_result_click(symbol): 
    st.session_state.ticker = symbol

def toggle_watchlist(symbol):
    wl = st.session_state.watchlist
    if symbol in wl:
        remove_watchlist_db(symbol)
        wl.remove(symbol)
    else:
        add_watchlist_db(symbol)
        wl.append(symbol)
    st.session_state.watchlist = wl

# ==============================================================================
# 3. OPTİMİZE EDİLMİŞ HESAPLAMA FONKSİYONLARI (CORE LOGIC)
# ==============================================================================

@st.cache_data(ttl=3600)
def get_benchmark_data(category):
    """
    Seçili kategoriye göre Endeks verisini (S&P 500 veya BIST 100) çeker.
    RS (Göreceli Güç) hesaplaması için referans noktasıdır.
    """
    try:
        # Kategoriye göre sembol seçimi
        ticker = "XU100.IS" if "BIST" in category else "^GSPC"
        
        # Hisse verileriyle uyumlu olması için 1 yıllık çekiyoruz
        df = yf.download(ticker, period="1y", progress=False)
        
        if df.empty: return None
        return df['Close']
    except:
        return None

# --- GLOBAL DATA CACHE KATMANI ---
@st.cache_data(ttl=3600, show_spinner=False)
def get_batch_data_cached(asset_list, period="1y"):
    """
    Tüm listenin verisini tek seferde çeker ve önbellekte tutar.
    Tarama fonksiyonları internete değil, buraya başvurur.
    """
    if not asset_list:
        return pd.DataFrame()
    
    try:
        # Tickers listesini string'e çevir
        tickers_str = " ".join(asset_list)
        
        # Tek seferde devasa indirme (Batch Download)
        data = yf.download(
            tickers_str, 
            period=period, 
            group_by='ticker', 
            threads=True, 
            progress=False,
            auto_adjust=False 
        )
        return data
    except Exception:
        return pd.DataFrame()

# --- SINGLE STOCK CACHE (DETAY SAYFASI İÇİN) ---
@st.cache_data(ttl=300)
def get_safe_historical_data(ticker, period="1y", interval="1d"):
    try:
        clean_ticker = ticker.replace(".IS", "").replace("=F", "")
        if "BIST" in ticker or ".IS" in ticker:
            clean_ticker = ticker if ticker.endswith(".IS") else f"{ticker}.IS"
        
        df = yf.download(clean_ticker, period=period, interval=interval, progress=False)
        
        if df.empty: return None
            
        if isinstance(df.columns, pd.MultiIndex):
            try:
                if clean_ticker in df.columns.levels[1]: df = df.xs(clean_ticker, axis=1, level=1)
                else: df.columns = df.columns.get_level_values(0)
            except: df.columns = df.columns.get_level_values(0)
                
        df.columns = [c.capitalize() for c in df.columns]
        required = ['Close', 'High', 'Low', 'Open']
        if not all(col in df.columns for col in required): return None

        if 'Volume' not in df.columns: df['Volume'] = 1
        df['Volume'] = df['Volume'].replace(0, 1)
        return df

    except Exception: return None

@st.cache_data(ttl=300)
def fetch_stock_info(ticker):
    try:
        t = yf.Ticker(ticker)
        price = prev_close = volume = None
        try:
            fi = getattr(t, "fast_info", None)
            if fi:
                price = fi.get("last_price")
                prev_close = fi.get("previous_close")
                volume = fi.get("last_volume")
        except: pass

        if price is None or prev_close is None:
            df = get_safe_historical_data(ticker, period="5d")
            if df is not None and not df.empty:
                 price = float(df["Close"].iloc[-1])
                 prev_close = float(df["Close"].iloc[-2]) if len(df) > 1 else price
                 volume = float(df["Volume"].iloc[-1])
            else: return None

        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
        return { "price": price, "change_pct": change_pct, "volume": volume or 0, "sector": "-", "target": "-" }
    except: return None

@st.cache_data(ttl=600)
def get_tech_card_data(ticker):
    try:
        df = get_safe_historical_data(ticker, period="2y")
        if df is None: return None
        close = df['Close']; high = df['High']; low = df['Low']
        
        sma50 = close.rolling(50).mean().iloc[-1] if len(close) > 50 else 0
        sma100 = close.rolling(100).mean().iloc[-1] if len(close) > 100 else 0
        sma200 = close.rolling(200).mean().iloc[-1] if len(close) > 200 else 0
        ema144 = close.ewm(span=144, adjust=False).mean().iloc[-1]
        atr = (high-low).rolling(14).mean().iloc[-1]
        
        return {
            "sma50": sma50, "sma100": sma100, "sma200": sma200, "ema144": ema144,
            "stop_level": close.iloc[-1] - (2 * atr), "risk_pct": (2 * atr) / close.iloc[-1] * 100,
            "atr": atr, "close_last": close.iloc[-1]
        }
    except: return None

@st.cache_data(ttl=1200)
def fetch_google_news(ticker):
    try:
        clean = ticker.replace(".IS", "").replace("=F", "")
        rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote_plus(f'{clean} stock news site:investing.com OR site:seekingalpha.com')}&hl=tr&gl=TR&ceid=TR:tr"
        feed = feedparser.parse(rss_url)
        news = []
        for entry in feed.entries[:6]:
            try: dt = datetime(*entry.published_parsed[:6])
            except: dt = datetime.now()
            if dt < datetime.now() - timedelta(days=10): continue
            pol = TextBlob(entry.title).sentiment.polarity
            color = "#16A34A" if pol > 0.1 else "#DC2626" if pol < -0.1 else "#64748B"
            news.append({'title': entry.title, 'link': entry.link, 'date': dt.strftime('%d %b'), 'source': entry.source.title, 'color': color})
        return news
    except: return []

@st.cache_data(ttl=600)
def calculate_synthetic_sentiment(ticker):
    try:
        df = get_safe_historical_data(ticker, period="6mo")
        if df is None: return None
        
        close = df['Close']; high = df['High']; low = df['Low']; volume = df['Volume']
        
        delta = close.diff()
        force_index = delta * volume
        mf_smooth = force_index.ewm(span=5, adjust=False).mean()

        typical_price = (high + low + close) / 3
        stp = typical_price.ewm(span=6, adjust=False).mean()
        
        df = df.reset_index()
        if 'Date' not in df.columns: df['Date'] = df.index
        else: df['Date'] = pd.to_datetime(df['Date'])
        
        plot_df = pd.DataFrame({
            'Date': df['Date'], 
            'MF_Smooth': mf_smooth.values, 
            'STP': stp.values, 
            'Price': close.values
        }).tail(30).reset_index(drop=True)
        
        plot_df['Date_Str'] = plot_df['Date'].dt.strftime('%d %b')
        return plot_df
    except Exception: return None

# --- OPTİMİZE EDİLMİŞ BATCH SCANNER'LAR ---

def process_single_stock_stp(symbol, df):
    """
    Tek bir hissenin STP hesaplamasını yapar.
    """
    try:
        if df.empty or 'Close' not in df.columns: return None
        df = df.dropna(subset=['Close'])
        if len(df) < 200: return None

        close = df['Close']
        high = df['High']
        low = df['Low']
        
        typical_price = (high + low + close) / 3
        stp = typical_price.ewm(span=6, adjust=False).mean()
        sma200 = close.rolling(200).mean()
        
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        c_last = float(close.iloc[-1]); c_prev = float(close.iloc[-2])
        s_last = float(stp.iloc[-1]); s_prev = float(stp.iloc[-2])
        
        result = None
        
        if c_prev <= s_prev and c_last > s_last:
            result = {
                "type": "cross",
                "data": {"Sembol": symbol, "Fiyat": c_last, "STP": s_last, "Fark": ((c_last/s_last)-1)*100}
            }
            sma_val = float(sma200.iloc[-1])
            rsi_val = float(rsi.iloc[-1])
            if (c_last > sma_val) and (20 < rsi_val < 70):
                result["is_filtered"] = True
            else:
                result["is_filtered"] = False

        elif c_prev > s_prev and c_last > s_last:
            above = close > stp
            streak = (above != above.shift()).cumsum()
            streak_count = above.groupby(streak).sum().iloc[-1]
            
            result = {
                "type": "trend",
                "data": {
                    "Sembol": symbol, 
                    "Fiyat": c_last, 
                    "STP": s_last, 
                    "Fark": ((c_last/s_last)-1)*100,
                    "Gun": int(streak_count)
                }
            }
        return result
    except Exception: return None

@st.cache_data(ttl=900)
def scan_stp_signals(asset_list):
    """
    Optimize edilmiş STP tarayıcı.
    """
    data = get_batch_data_cached(asset_list, period="2y")
    if data.empty: return [], [], []

    cross_signals = []
    trend_signals = []
    filtered_signals = []

    stock_dfs = []
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]:
                    stock_dfs.append((symbol, data[symbol]))
            else:
                if len(asset_list) == 1:
                    stock_dfs.append((symbol, data))
        except: continue

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(process_single_stock_stp, sym, df) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                if res["type"] == "cross":
                    cross_signals.append(res["data"])
                    if res.get("is_filtered"):
                        filtered_signals.append(res["data"])
                elif res["type"] == "trend":
                    trend_signals.append(res["data"])

    trend_signals.sort(key=lambda x: x["Gun"], reverse=False)
    return cross_signals, trend_signals, filtered_signals

def process_single_accumulation(symbol, df, benchmark_series):
    try:
        if df.empty or 'Close' not in df.columns: return None
        df = df.dropna(subset=['Close'])
        # RS hesaplaması için en az 60 gün veri iyi olur (Mansfield ortalaması için)
        if len(df) < 60: return None

        close = df['Close']
        open_ = df['Open']
        high = df['High']
        low = df['Low']
        volume = df['Volume'] if 'Volume' in df.columns else pd.Series([1]*len(df), index=df.index)
        
        # --- MEVCUT MANTIK (TOPLAMA) ---
        delta = close.diff()
        force_index = delta * volume
        mf_smooth = force_index.ewm(span=5, adjust=False).mean()

        last_10_mf = mf_smooth.tail(10)
        last_10_close = close.tail(10)
        
        if len(last_10_mf) < 10: return None
        
        pos_days_count = (last_10_mf > 0).sum()
        if pos_days_count < 7: return None # İstikrar Kuralı

        price_start = float(last_10_close.iloc[0]) 
        price_now = float(last_10_close.iloc[-1])
        
        if price_start == 0: return None
        
        change_pct = (price_now - price_start) / price_start
        avg_mf = float(last_10_mf.mean())
        
        if avg_mf <= 0: return None
        if change_pct > 0.3: return None 

        # --- YENİ EKLENTİ 1: MANSFIELD RELATIVE STRENGTH (RS) ---
        rs_status = "Zayıf"
        rs_score = 0
        
        if benchmark_series is not None:
            try:
                # Tarihleri eşleştir (Reindex)
                common_idx = close.index.intersection(benchmark_series.index)
                stock_aligned = close.loc[common_idx]
                bench_aligned = benchmark_series.loc[common_idx]
                
                if len(stock_aligned) > 50:
                    # 1. Rasyo: Hisse / Endeks
                    rs_ratio = stock_aligned / bench_aligned
                    # 2. Rasyonun 50 günlük ortalaması (Standart Mansfield 52 haftadır ama 50 gün daha reaktif)
                    rs_ma = rs_ratio.rolling(50).mean()
                    # 3. Mansfield RS Değeri (Normalize)
                    mansfield = ((rs_ratio / rs_ma) - 1) * 10
                    
                    curr_rs = float(mansfield.iloc[-1])
                    
                    if curr_rs > 0: 
                        rs_status = "GÜÇLÜ (Endeks Üstü)"
                        rs_score = 1 # Puana katkı
                        if curr_rs > float(mansfield.iloc[-5]): # RS Yükseliyor mu?
                            rs_status += " 🚀"
                            rs_score = 2
                    else:
                        rs_status = "Zayıf (Endeks Altı)"
            except:
                rs_status = "Veri Yok"

        # --- YENİ EKLENTİ 2: POCKET PIVOT (Hacim Patlaması) ---
        # Mantık: Bugünkü hacim > Son 10 günün en büyük "Düşüş Günü" hacmi
        is_pocket_pivot = False
        pp_desc = "-"
        
        # 1. Düşüş günlerini bul (Kapanış < Açılış)
        is_down_day = close < open_
        # 2. Sadece düşüş günlerinin hacmini al, diğerlerini 0 yap
        down_volumes = volume.where(is_down_day, 0)
        # 3. Son 10 günün (bugün hariç) en büyük düşüş hacmi
        max_down_vol_10 = down_volumes.iloc[-11:-1].max()
        
        curr_vol = float(volume.iloc[-1])
        is_up_day = float(close.iloc[-1]) > float(open_.iloc[-1])
        
        # Pivot Kuralı: Bugün yükseliş günü + Hacim > Max Satış Hacmi
        if is_up_day and (curr_vol > max_down_vol_10):
            is_pocket_pivot = True
            pp_desc = "⚡ POCKET PIVOT (Hazır!)"
            rs_score += 3 # Pivot varsa skoru uçur

        # --- SKORLAMA VE ÇIKTI ---
        # Eski skor mantığına eklemeler yapıyoruz
        base_score = avg_mf * (10.0 if change_pct < 0 else 5.0)
        final_score = base_score * (1 + rs_score) # RS ve Pivot varsa puanı katla

        # Hacim Yazısı
        if avg_mf > 1_000_000: mf_str = f"{avg_mf/1_000_000:.1f}M"
        elif avg_mf > 1_000: mf_str = f"{avg_mf/1_000:.0f}K"
        else: mf_str = f"{int(avg_mf)}"

        squeeze_score = final_score / (abs(change_pct) + 0.02)

        return {
            "Sembol": symbol,
            "Fiyat": f"{price_now:.2f}",
            "Degisim_Raw": change_pct,
            "Degisim_Str": f"%{change_pct*100:.1f}",
            "MF_Gucu_Goster": mf_str, 
            "Gun_Sayisi": f"{pos_days_count}/10",
            "Skor": squeeze_score,
            "RS_Durumu": rs_status,      # YENİ SÜTUN
            "Pivot_Sinyali": pp_desc,    # YENİ SÜTUN
            "Pocket_Pivot": is_pocket_pivot # Sıralama/Filtre için
        }
    except Exception as e: 
        return None

@st.cache_data(ttl=900)
def scan_hidden_accumulation(asset_list):
    # 1. Önce Hisse Verilerini Çek
    data = get_batch_data_cached(asset_list, period="1y") # RS için süreyi 1y yaptım (önce 1mo idi)
    if data.empty: return pd.DataFrame()

    # 2. Endeks Verisini Çek (Sadece tek sefer)
    current_cat = st.session_state.get('category', 'S&P 500')
    benchmark = get_benchmark_data(current_cat)

    results = []
    stock_dfs = []
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]:
                    stock_dfs.append((symbol, data[symbol]))
            else:
                if len(asset_list) == 1: stock_dfs.append((symbol, data))
        except: continue

    # 3. Paralel İşlem (Benchmark'ı da gönderiyoruz)
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        # benchmark serisini her fonksiyona argüman olarak geçiyoruz
        futures = [executor.submit(process_single_accumulation, sym, df, benchmark) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: results.append(res)

    if results: 
        df_res = pd.DataFrame(results)
        # Önce Pocket Pivot olanları, sonra Skoru yüksek olanları üste al
        return df_res.sort_values(by=["Pocket_Pivot", "Skor"], ascending=[False, False])
    
    return pd.DataFrame()

def process_single_radar1(symbol, df):
    try:
        if df.empty or 'Close' not in df.columns: return None
        df = df.dropna(subset=['Close'])
        if len(df) < 60: return None
        
        close = df['Close']; high = df['High']; low = df['Low']
        volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))
        
        # Göstergeler
        ema5 = close.ewm(span=5, adjust=False).mean()
        ema20 = close.ewm(span=20, adjust=False).mean()
        sma20 = close.rolling(20).mean(); std20 = close.rolling(20).std()
        
        # Bollinger Squeeze Hesabı
        bb_width = ((sma20 + 2*std20) - (sma20 - 2*std20)) / (sma20 - 0.0001)

        # MACD Hesabı
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        hist = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()
        
        # RSI Hesabı
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain / loss)))
        
        # ADX Hesabı (Trend Gücü)
        try:
            plus_dm = high.diff(); minus_dm = low.diff()
            plus_dm[plus_dm < 0] = 0; minus_dm[minus_dm > 0] = 0
            tr1 = pd.DataFrame(high - low); tr2 = pd.DataFrame(abs(high - close.shift(1))); tr3 = pd.DataFrame(abs(low - close.shift(1)))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr_adx = tr.rolling(14).mean()
            plus_di = 100 * (plus_dm.ewm(alpha=1/14).mean() / atr_adx)
            minus_di = 100 * (abs(minus_dm).ewm(alpha=1/14).mean() / atr_adx)
            dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
            curr_adx = float(dx.rolling(14).mean().iloc[-1])
        except: curr_adx = 20

        score = 0; reasons = []; details = {}
        curr_c = float(close.iloc[-1]); curr_vol = float(volume.iloc[-1])
        avg_vol = float(volume.rolling(5).mean().iloc[-1]) if len(volume) > 5 else 1.0
        
        # --- PUANLAMA (7 MADDE) ---
        
        # 1. Squeeze (Patlama Hazırlığı)
        if bb_width.iloc[-1] <= bb_width.tail(60).min() * 1.1: score += 1; reasons.append("🚀 Squeeze"); details['Squeeze'] = True
        else: details['Squeeze'] = False
        
        # 2. Trend (Kısa Vade Yükseliş)
        if ((ema5.iloc[-1] > ema20.iloc[-1]) and (ema5.iloc[-2] <= ema20.iloc[-2])) or ((ema5.iloc[-2] > ema20.iloc[-2]) and (ema5.iloc[-3] <= ema20.iloc[-3])): score += 1; reasons.append("⚡ Trend"); details['Trend'] = True
        else: details['Trend'] = False
        
        # 3. MACD (Momentum Artışı)
        if hist.iloc[-1] > hist.iloc[-2]: score += 1; reasons.append("🟢 MACD"); details['MACD'] = True
        else: details['MACD'] = False
        
        # 4. Hacim (İlgi Var mı?)
        if curr_vol > avg_vol * 1.2: score += 1; reasons.append("🔊 Hacim"); details['Hacim'] = True
        else: details['Hacim'] = False
        
        # 5. Breakout (Zirveye Yakınlık)
        if curr_c >= high.tail(20).max() * 0.98: score += 1; reasons.append("🔨 Breakout"); details['Breakout'] = True
        else: details['Breakout'] = False
        
        # 6. RSI Güçlü (İvme)
        rsi_c = float(rsi.iloc[-1])
        if 30 < rsi_c < 65 and rsi_c > float(rsi.iloc[-2]): score += 1; reasons.append("⚓ RSI Güçlü"); details['RSI Güçlü'] = (True, rsi_c)
        else: details['RSI Güçlü'] = (False, rsi_c)
        
        # 7. ADX (Trendin Gücü Yerinde mi?)
        if curr_adx > 25: 
            score += 1; reasons.append(f"💪 Güçlü Trend"); details['ADX Durumu'] = (True, curr_adx)
        else:
            details['ADX Durumu'] = (False, curr_adx)

        return { "Sembol": symbol, "Fiyat": f"{curr_c:.2f}", "Skor": score, "Nedenler": " | ".join(reasons), "Detaylar": details }
    except: return None

@st.cache_data(ttl=3600)
def analyze_market_intelligence(asset_list):
    data = get_batch_data_cached(asset_list, period="6mo")
    if data.empty: return pd.DataFrame()

    signals = []
    stock_dfs = []
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]: stock_dfs.append((symbol, data[symbol]))
            else:
                if len(asset_list) == 1: stock_dfs.append((symbol, data))
        except: continue

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(process_single_radar1, sym, df) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: signals.append(res)

    return pd.DataFrame(signals).sort_values(by="Skor", ascending=False) if signals else pd.DataFrame()

def process_single_radar2(symbol, df, idx, min_price, max_price, min_avg_vol_m):
    try:
        if df.empty or 'Close' not in df.columns: return None
        df = df.dropna(subset=['Close'])
        if len(df) < 120: return None
        
        close = df['Close']; high = df['High']; low = df['Low']
        volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))
        curr_c = float(close.iloc[-1])
        
        # Filtreler
        if curr_c < min_price or curr_c > max_price: return None
        avg_vol_20 = float(volume.rolling(20).mean().iloc[-1])
        if avg_vol_20 < min_avg_vol_m * 1e6: return None
        
        # Trend Ortalamaları
        sma20 = close.rolling(20).mean(); sma50 = close.rolling(50).mean()
        sma100 = close.rolling(100).mean(); sma200 = close.rolling(200).mean()
        
        trend = "Yatay"
        if not np.isnan(sma200.iloc[-1]):
            if curr_c > sma50.iloc[-1] > sma100.iloc[-1] > sma200.iloc[-1] and sma200.iloc[-1] > sma200.iloc[-20]: trend = "Boğa"
            elif curr_c < sma200.iloc[-1] and sma200.iloc[-1] < sma200.iloc[-20]: trend = "Ayı"
        
        # RSI ve MACD (Sadece Setup için histogram hesabı kalıyor, puanlamadan çıkacak)
        delta = close.diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain / loss))); rsi_c = float(rsi.iloc[-1])
        ema12 = close.ewm(span=12, adjust=False).mean(); ema26 = close.ewm(span=26, adjust=False).mean()
        hist = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()
        
        # Breakout Oranı
        recent_high_60 = float(high.rolling(60).max().iloc[-1])
        breakout_ratio = curr_c / recent_high_60 if recent_high_60 > 0 else 0
        
        # RS Skoru (Endeks)
        rs_score = 0.0
        if idx is not None and len(close) > 60 and len(idx) > 60:
            common_index = close.index.intersection(idx.index)
            if len(common_index) > 60:
                cs = close.reindex(common_index); isx = idx.reindex(common_index)
                rs_score = float((cs.iloc[-1]/cs.iloc[-60]-1) - (isx.iloc[-1]/isx.iloc[-60]-1))
        
        # --- YENİ EKLENEN: ICHIMOKU BULUTU (Kumo) ---
        # Bulut şu anki fiyatın altında mı? (Trend Desteği)
        # Ichimoku değerleri 26 periyot ileri ötelenir. Yani bugünün bulutu, 26 gün önceki verilerle çizilir.
        tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
        kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
        
        # Span A (Bugün için değeri 26 gün önceki hesaptan gelir)
        span_a_calc = (tenkan + kijun) / 2
        # Span B (Bugün için değeri 26 gün önceki hesaptan gelir)
        span_b_calc = (high.rolling(52).max() + low.rolling(52).min()) / 2
        
        # Bugünün bulut sınırları (Veri setinin sonundan 26 önceki değerler)
        cloud_a = float(span_a_calc.iloc[-26])
        cloud_b = float(span_b_calc.iloc[-26])
        is_above_cloud = curr_c > max(cloud_a, cloud_b)
        # -----------------------------------------------

        setup = "-"; tags = []; score = 0; details = {}
        avg_vol_20 = max(avg_vol_20, 1); vol_spike = volume.iloc[-1] > avg_vol_20 * 1.3
        
        # Setup Tespiti
        if trend == "Boğa" and breakout_ratio >= 0.97: setup = "Breakout"; tags.append("Zirve")
        if trend == "Boğa" and setup == "-":
            if sma20.iloc[-1] <= curr_c <= sma50.iloc[-1] * 1.02 and 40 <= rsi_c <= 55: setup = "Pullback"; tags.append("Düzeltme")
            if volume.iloc[-1] < avg_vol_20 * 0.9: score += 0; tags.append("Sığ Satış")
        if setup == "-":
            if rsi.iloc[-2] < 30 <= rsi_c and hist.iloc[-1] > hist.iloc[-2]: setup = "Dip Dönüşü"; tags.append("Dip Dönüşü")
        
        # --- PUANLAMA (7 Madde) ---
        
        # 1. Hacim Patlaması
        if vol_spike: score += 1; tags.append("Hacim+"); details['Hacim Patlaması'] = True
        else: details['Hacim Patlaması'] = False

        # 2. RS (Endeks Gücü)
        if rs_score > 0: score += 1; tags.append("RS+"); details['RS (S&P500)'] = True
        else: details['RS (S&P500)'] = False
        
        # 3. Boğa Trendi (SMA Dizilimi)
        if trend == "Boğa": score += 1; details['Boğa Trendi'] = True
        else:
            if trend == "Ayı": score -= 1
            details['Boğa Trendi'] = False
            
        # 4. Ichimoku Bulutu (YENİ - MACD YERİNE GELDİ)
        if is_above_cloud: score += 1; details['Ichimoku'] = True
        else: details['Ichimoku'] = False

        # 5. 60 Günlük Zirveye Yakınlık
        details['60G Zirve'] = breakout_ratio >= 0.90
        if details['60G Zirve']: score += 1

        # 6. RSI Uygun Bölge (Aşırı şişmemiş)
        is_rsi_suitable = (40 <= rsi_c <= 65) # Biraz genişlettim
        details['RSI Bölgesi'] = (is_rsi_suitable, rsi_c)
        if is_rsi_suitable: score += 1
        
        # 7. Setup Puanı (Yukarıda hesaplandı, max 2 puan ama biz varlığını kontrol edelim)
        # Setup varsa ekstra güvenilirdir.
        if setup != "-": score += 0
        
        return { "Sembol": symbol, "Fiyat": round(curr_c, 2), "Trend": trend, "Setup": setup, "Skor": score, "RS": round(rs_score * 100, 1), "Etiketler": " | ".join(tags), "Detaylar": details }
    except: return None

@st.cache_data(ttl=3600)
def radar2_scan(asset_list, min_price=5, max_price=5000, min_avg_vol_m=0.5):
    data = get_batch_data_cached(asset_list, period="1y")
    if data.empty: return pd.DataFrame()
    
    try: idx = yf.download("^GSPC", period="1y", progress=False)["Close"]
    except: idx = None

    results = []
    stock_dfs = []
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]: stock_dfs.append((symbol, data[symbol]))
            else:
                if len(asset_list) == 1: stock_dfs.append((symbol, data))
        except: continue

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(process_single_radar2, sym, df, idx, min_price, max_price, min_avg_vol_m) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: results.append(res)

    return pd.DataFrame(results).sort_values(by=["Skor", "RS"], ascending=False).head(50) if results else pd.DataFrame()

def process_single_breakout(symbol, df):
    try:
        if df.empty or 'Close' not in df.columns: return None
        df = df.dropna(subset=['Close']); 
        if len(df) < 60: return None

        close = df['Close']; high = df['High']; low = df['Low']; open_ = df['Open']
        volume = df['Volume'] if 'Volume' in df.columns else pd.Series([1]*len(df))
        ema5 = close.ewm(span=5, adjust=False).mean(); ema20 = close.ewm(span=20, adjust=False).mean()
        sma20 = close.rolling(20).mean(); sma50 = close.rolling(50).mean()
        std20 = close.rolling(20).std(); bb_upper = sma20 + (2 * std20); bb_lower = sma20 - (2 * std20); bb_width = (bb_upper - bb_lower) / sma20
        vol_20 = volume.rolling(20).mean().iloc[-1]; curr_vol = volume.iloc[-1]
        rvol = curr_vol / vol_20 if vol_20 != 0 else 1
        high_60 = high.rolling(60).max().iloc[-1]; curr_price = close.iloc[-1]
        delta = close.diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]
        cond_ema = ema5.iloc[-1] > ema20.iloc[-1]; cond_vol = rvol > 1.2; cond_prox = curr_price > (high_60 * 0.90); cond_rsi = rsi < 70; sma_ok = sma20.iloc[-1] > sma50.iloc[-1]
        
        if cond_ema and cond_vol and cond_prox and cond_rsi:
            is_short_signal = False; short_reason = ""
            if (close.iloc[-1] < open_.iloc[-1]) and (close.iloc[-2] < open_.iloc[-2]) and (close.iloc[-3] < open_.iloc[-3]): is_short_signal = True; short_reason = "3 Kırmızı Mum (Düşüş)"
            body_last = abs(close.iloc[-1] - open_.iloc[-1]); body_prev1 = abs(close.iloc[-2] - open_.iloc[-2]); body_prev2 = abs(close.iloc[-3] - open_.iloc[-3])
            if (close.iloc[-1] < open_.iloc[-1]) and (body_last > (body_prev1 + body_prev2)): is_short_signal = True; short_reason = "Yutan Ayı Mum (Engulfing)"
            min_bandwidth_60 = bb_width.rolling(60).min().iloc[-1]; is_squeeze = bb_width.iloc[-1] <= min_bandwidth_60 * 1.10
            prox_pct = (curr_price / high_60) * 100
            prox_str = f"💣 Bant içinde sıkışma var, patlamaya hazır" if is_squeeze else (f"%{prox_pct:.1f}" + (" (Sınıra Dayandı)" if prox_pct >= 98 else " (Hazırlanıyor)"))
            c_open = open_.iloc[-1]; c_close = close.iloc[-1]; c_high = high.iloc[-1]; body_size = abs(c_close - c_open); upper_wick = c_high - max(c_open, c_close)
            is_wick_rejected = (upper_wick > body_size * 1.5) and (upper_wick > 0)
            wick_warning = " <span style='color:#DC2626; font-weight:700; background:#fef2f2; padding:2px 4px; border-radius:4px;'>⚠️ Satış Baskısı (Uzun Fitil)</span>" if is_wick_rejected else ""
            rvol_text = "Olağanüstü para girişi 🐳" if rvol > 2.0 else ("İlgi artıyor 📈" if rvol > 1.5 else "İlgi var 👀")
            display_symbol = symbol
            if is_short_signal:
                display_symbol = f"{symbol} <span style='color:#DC2626; font-weight:800; background:#fef2f2; padding:2px 6px; border-radius:4px; font-size:0.8rem;'>🔻 SHORT FIRSATI</span>"
                trend_display = f"<span style='color:#DC2626; font-weight:700;'>{short_reason}</span>"
            else: trend_display = f"✅EMA | {'✅SMA' if sma_ok else '❌SMA'}"
            return { "Sembol_Raw": symbol, "Sembol_Display": display_symbol, "Fiyat": f"{curr_price:.2f}", "Zirveye Yakınlık": prox_str + wick_warning, "Hacim Durumu": rvol_text, "Trend Durumu": trend_display, "RSI": f"{rsi:.0f}", "SortKey": rvol }
        return None
    except: return None

@st.cache_data(ttl=3600)
def agent3_breakout_scan(asset_list):
    data = get_batch_data_cached(asset_list, period="6mo")
    if data.empty: return pd.DataFrame()

    results = []
    stock_dfs = []
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]: stock_dfs.append((symbol, data[symbol]))
            else:
                if len(asset_list) == 1: stock_dfs.append((symbol, data))
        except: continue

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(process_single_breakout, sym, df) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: results.append(res)
    
    return pd.DataFrame(results).sort_values(by="SortKey", ascending=False) if results else pd.DataFrame()

def process_single_confirmed(symbol, df):
    try:
        if df.empty or 'Close' not in df.columns: return None
        df = df.dropna(subset=['Close']); 
        if len(df) < 65: return None

        close = df['Close']; high = df['High']; volume = df['Volume'] if 'Volume' in df.columns else pd.Series([1]*len(df))
        
        high_60 = high.rolling(window=60).max().shift(1).iloc[-1]
        curr_close = float(close.iloc[-1])
        
        if curr_close <= high_60: return None 

        avg_vol_20 = volume.rolling(20).mean().shift(1).iloc[-1]
        curr_vol = float(volume.iloc[-1])
        vol_factor = curr_vol / avg_vol_20 if avg_vol_20 > 0 else 1.0
        
        if vol_factor < 1.2: return None 

        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        bb_upper = sma20 + (2 * std20); bb_lower = sma20 - (2 * std20)
        bb_width = (bb_upper - bb_lower) / sma20
        avg_width = bb_width.rolling(20).mean().iloc[-1]
        is_range_breakout = bb_width.iloc[-2] < avg_width * 0.8 
        
        breakout_type = "📦 RANGE KIRILIMI" if is_range_breakout else "🏔️ ZİRVE KIRILIMI (Fiyat son 60 günün zirvesinde)"
        
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]

        return {
            "Sembol": symbol,
            "Fiyat": f"{curr_close:.2f}",
            "Kirim_Turu": breakout_type,
            "Hacim_Kati": f"{vol_factor:.1f}x",
            "RSI": int(rsi),
            "SortKey": vol_factor 
        }
    except: return None

@st.cache_data(ttl=3600)
def scan_confirmed_breakouts(asset_list):
    data = get_batch_data_cached(asset_list, period="1y")
    if data.empty: return pd.DataFrame()

    results = []
    stock_dfs = []
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]: stock_dfs.append((symbol, data[symbol]))
            else:
                if len(asset_list) == 1: stock_dfs.append((symbol, data))
        except: continue

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(process_single_confirmed, sym, df) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: results.append(res)
    
    return pd.DataFrame(results).sort_values(by="SortKey", ascending=False).head(20) if results else pd.DataFrame()

# ==============================================================================
# MINERVINI SEPA MODÜLÜ (HEM TEKLİ ANALİZ HEM TARAMA) - GÜNCELLENMİŞ VERSİYON
# ==============================================================================

@st.cache_data(ttl=600)
def calculate_minervini_sepa(ticker, benchmark_ticker="^GSPC", provided_df=None):
    """
    GÖRSEL: Eski (Sade)
    MANTIK: Sniper (Çok Sert)
    """
    try:
        # 1. VERİ YÖNETİMİ (Batch taramadan geliyorsa provided_df kullan, yoksa indir)
        if provided_df is not None:
            df = provided_df
        else:
            df = get_safe_historical_data(ticker, period="2y")
            
        if df is None or len(df) < 260: return None
        
        # MultiIndex Temizliği
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Endeks verisi (RS için) - Eğer cache'de yoksa indir
        bench_df = get_safe_historical_data(benchmark_ticker, period="2y")
        
        close = df['Close']; volume = df['Volume']
        curr_price = float(close.iloc[-1])
        
        # ---------------------------------------------------------
        # KRİTER 1: TREND ŞABLONU (ACIMASIZ FİLTRE)
        # ---------------------------------------------------------
        sma50 = float(close.rolling(50).mean().iloc[-1])
        sma150 = float(close.rolling(150).mean().iloc[-1])
        sma200 = float(close.rolling(200).mean().iloc[-1])
        
        # Eğim Kontrolü: SMA200, 1 ay önceki değerinden yüksek olmalı
        sma200_prev = float(close.rolling(200).mean().iloc[-22])
        sma200_up = sma200 > sma200_prev
        
        year_high = float(close.rolling(250).max().iloc[-1])
        year_low = float(close.rolling(250).min().iloc[-1])
        
        # Zirveye Yakınlık: Minervini %25 der ama biz sertleşip %15 (0.85) yapıyoruz
        near_high = curr_price >= (year_high * 0.9)
        above_low = curr_price >= (year_low * 1.30)
        
        # HEPSİ DOĞRU OLMALI
        trend_ok = (curr_price > sma150 > sma200) and \
                   (sma50 > sma150) and \
                   (curr_price > sma50) and \
                   sma200_up and \
                   near_high and \
                   above_low
                   
        if not trend_ok: return None # Trend yoksa elendi.

        # ---------------------------------------------------------
        # KRİTER 2: RS KONTROLÜ (ACIMASIZ)
        # ---------------------------------------------------------
        rs_val = 0; rs_rating = "ZAYIF"
        if bench_df is not None:
            common = close.index.intersection(bench_df.index)
            if len(common) > 50:
                s_p = close.loc[common]; b_p = bench_df['Close'].loc[common]
                ratio = s_p / b_p
                rs_val = float(((ratio / ratio.rolling(50).mean()) - 1).iloc[-1] * 10)
        
        # Endeksten Zayıfsa ELE (0 altı kabul edilmez)
        if rs_val <= 1: return None
        
        rs_rating = f"GÜÇLÜ (RS: {rs_val:.1f})"

        # ---------------------------------------------------------
        # KRİTER 3: PUANLAMA (VCP + ARZ + PIVOT)
        # ---------------------------------------------------------
        raw_score = 60 # Başlangıç puanı (Trend ve RS geçtiği için)
        
        # VCP (Sertleşmiş Formül: %65 daralma)
        std_10 = close.pct_change().rolling(10).std().iloc[-1]
        std_50 = close.pct_change().rolling(50).std().iloc[-1]
        is_vcp = std_10 < (std_50 * 0.65)
        if is_vcp: raw_score += 20
        
        # Arz Kuruması (Sertleşmiş: %75 altı)
        avg_vol = volume.rolling(20).mean().iloc[-1]
        last_5 = df.tail(5)
        down_days = last_5[last_5['Close'] < last_5['Open']]
        is_dry = True if down_days.empty else (down_days['Volume'].mean() < avg_vol * 0.75)
        if is_dry: raw_score += 10
        
        # Pivot Bölgesi (Zirveye %5 kala)
        dist_high = curr_price / year_high
        in_pivot = 0.95 <= dist_high <= 1.02
        if in_pivot: raw_score += 10

        # ---------------------------------------------------------
        # ÇIKTI (ESKİ TASARIMIN ANLAYACAĞI FORMAT)
        # ---------------------------------------------------------
        # Buradaki key isimleri (Durum, Detay vs.) senin eski kodunla aynı.
        # Böylece UI bozulmayacak.
        
        status = "🔥 GÜÇLÜ TREND"
        if is_vcp and in_pivot: status = "💎 SÜPER BOĞA (VCP)"
        elif in_pivot: status = "🚀 KIRILIM EŞİĞİNDE"
        
        # Renk (Skor bazlı)
        color = "#16a34a" if raw_score >= 80 else "#ea580c"

        return {
            "Sembol": ticker,
            "Fiyat": f"{curr_price:.2f}",
            "Durum": status,
            "Detay": f"{rs_rating} | VCP: {'Sıkışmada düşük oynaklık' if is_vcp else '-'} | Arz: {'Kurudu(satıcılar yoruldu)' if is_dry else '-'}",
            "Raw_Score": raw_score,
            "score": raw_score, # UI bazen bunu arıyor
            "trend_ok": True,
            "is_vcp": is_vcp,
            "is_dry": is_dry,
            "rs_val": rs_val,
            "rs_rating": rs_rating,
            "reasons": ["Trend: Mükemmel", f"VCP: {is_vcp}", f"RS: {rs_val:.1f}"],
            "color": color,
            "sma200": sma200,
            "year_high": year_high
        }
    except Exception: return None
        
@st.cache_data(ttl=900)
def scan_minervini_batch(asset_list):
    # 1. Veri İndirme (Hızlı Batch)
    data = get_batch_data_cached(asset_list, period="2y")
    if data.empty: return pd.DataFrame()
    
    # 2. Endeks Belirleme
    cat = st.session_state.get('category', 'S&P 500')
    bench = "XU100.IS" if "BIST" in cat else "^GSPC"

    results = []
    stock_dfs = []
    
    # Veriyi hazırlama (Hisselere bölme)
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]:
                    stock_dfs.append((symbol, data[symbol]))
            elif len(asset_list) == 1:
                stock_dfs.append((symbol, data))
        except: continue

    # 3. Paralel Tarama (Yukarıdaki sertleştirilmiş fonksiyonu çağırır)
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        # provided_df argümanını kullanarak internetten tekrar indirmeyi engelliyoruz
        futures = [executor.submit(calculate_minervini_sepa, sym, bench, df) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: results.append(res)
            
    # 4. Sıralama ve Kesme
    if results:
        df = pd.DataFrame(results)
        # En yüksek Puanlı ve en yüksek RS'li olanları üste al
        # Sadece ilk 30'u göster ki kullanıcı boğulmasın.
        return df.sort_values(by=["Raw_Score", "rs_val"], ascending=[False, False]).head(30)
    
    return pd.DataFrame()
    
@st.cache_data(ttl=600)
def calculate_sentiment_score(ticker):
    try:
        df = get_safe_historical_data(ticker, period="6mo")
        if df is None: return None
        
        close = df['Close']; high = df['High']; low = df['Low']; volume = df['Volume']
        
        # --- VERİ HESAPLAMALARI ---
        
        # 1. YAPI (STRUCTURE) - 25 PUAN
        score_str = 0; reasons_str = []
        recent_high = high.rolling(20).max().shift(1).iloc[-1]
        recent_low = low.rolling(20).min().shift(1).iloc[-1]
        
        if close.iloc[-1] > recent_high: 
            score_str += 15; reasons_str.append("BOS: Kırılım")
        if low.iloc[-1] > recent_low:
            score_str += 10; reasons_str.append("HL: Yükselen Dip")

        # 2. TREND - 25 PUAN
        score_tr = 0; reasons_tr = []
        sma50 = close.rolling(50).mean(); sma200 = close.rolling(200).mean()
        ema20 = close.ewm(span=20, adjust=False).mean()
        
        if close.iloc[-1] > sma200.iloc[-1]: score_tr += 10; reasons_tr.append("Ana Trend+")
        if close.iloc[-1] > ema20.iloc[-1]: score_tr += 10; reasons_tr.append("Kısa Vade+")
        if ema20.iloc[-1] > sma50.iloc[-1]: score_tr += 5; reasons_tr.append("Hizalı")

        # 3. HACİM - 25 PUAN
        score_vol = 0; reasons_vol = []
        vol_ma = volume.rolling(20).mean()
        if volume.iloc[-1] > vol_ma.iloc[-1]: score_vol += 15; reasons_vol.append("Hacim Artışı")
        
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        obv_ma = obv.rolling(10).mean()
        if obv.iloc[-1] > obv_ma.iloc[-1]: score_vol += 10; reasons_vol.append("OBV+")

        # 4. MOMENTUM - 15 PUAN
        score_mom = 0; reasons_mom = []
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs)).fillna(50)
        
        if rsi.iloc[-1] > 50: score_mom += 5; reasons_mom.append("RSI>50")
        if rsi.iloc[-1] > rsi.iloc[-5]: score_mom += 5; reasons_mom.append("RSI İvme")
        
        ema12 = close.ewm(span=12, adjust=False).mean(); ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26; signal = macd.ewm(span=9, adjust=False).mean()
        if macd.iloc[-1] > signal.iloc[-1]: score_mom += 5; reasons_mom.append("MACD Al")

        # 5. VOLATİLİTE - 10 PUAN
        score_vola = 0; reasons_vola = []
        std = close.rolling(20).std()
        upper = close.rolling(20).mean() + (2 * std)
        lower = close.rolling(20).mean() - (2 * std)
        bb_width = (upper - lower) / close.rolling(20).mean()
        
        if bb_width.iloc[-1] < bb_width.rolling(20).mean().iloc[-1]:
            score_vola += 10; reasons_vola.append("Sıkışma")
        
        total = score_str + score_tr + score_vol + score_mom + score_vola
        
        # --- GÖRSEL AYARLAR (BAR VE YAZI TİPİ DÜZELTİLDİ) ---
        bars = int(total / 5)
        # Bar: Kare bloklar
        bar_str = "【" + "█" * bars + "░" * (20 - bars) + "】"
        
        def fmt(lst): 
            if not lst: return ""
            # Her bir sebebin arasına ' + ' koyup birleştiriyoruz
            content = " + ".join(lst)
            # HTML string olarak döndürüyoruz. CSS stillerine dikkat et.
            return f"<span style='font-size:0.7rem; color:#334155; font-style:italic; font-weight:300;'>({content})</span>"
        
        return {
            "total": total, "bar": bar_str, 
            # fmt() fonksiyonunu çağırarak formatlanmış HTML stringi alıyoruz
            "mom": f"{score_mom}/15 {fmt(reasons_mom)}",
            "vol": f"{score_vol}/25 {fmt(reasons_vol)}", 
            "tr": f"{score_tr}/25 {fmt(reasons_tr)}",
            "vola": f"{score_vola}/10 {fmt(reasons_vola)}", 
            "str": f"{score_str}/25 {fmt(reasons_str)}",
            "raw_rsi": rsi.iloc[-1], "raw_macd": (macd-signal).iloc[-1], "raw_obv": obv.iloc[-1], "raw_atr": 0
        }
    except: return None

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

# --- ICT MODÜLÜ (GÜNCELLENMİŞ: Hata Korumalı) ---
@st.cache_data(ttl=600)
def calculate_ict_deep_analysis(ticker):
    error_ret = {"status": "Error", "msg": "Veri Yok", "structure": "-", "bias": "-", "entry": 0, "target": 0, "stop": 0, "rr": 0, "desc": "Veri bekleniyor", "displacement": "-", "fvg_txt": "-", "ob_txt": "-", "zone": "-", "mean_threshold": 0, "curr_price": 0, "setup_type": "BEKLE"}
    
    try:
        df = get_safe_historical_data(ticker, period="1y")
        if df is None or len(df) < 60: return error_ret
        
        high = df['High']; low = df['Low']; close = df['Close']; open_ = df['Open']
        
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        avg_body_size = abs(open_ - close).rolling(20).mean()

        sw_highs = []; sw_lows = []
        for i in range(2, len(df)-2):
            try:
                if high.iloc[i] >= max(high.iloc[i-2:i]) and high.iloc[i] >= max(high.iloc[i+1:i+3]):
                    sw_highs.append((df.index[i], high.iloc[i])) 
                if low.iloc[i] <= min(low.iloc[i-2:i]) and low.iloc[i] <= min(low.iloc[i+1:i+3]):
                    sw_lows.append((df.index[i], low.iloc[i]))
            except: continue

        if not sw_highs or not sw_lows: return error_ret

        curr_price = close.iloc[-1]
        last_sh = sw_highs[-1][1] 
        last_sl = sw_lows[-1][1]  
        
        structure = "YATAY / KONSOLİDE"
        bias = "neutral"
        displacement_txt = "Zayıf (Hacimsiz Hareket)"
        
        last_candle_body = abs(open_.iloc[-1] - close.iloc[-1])
        if last_candle_body > avg_body_size.iloc[-1] * 1.2:
             displacement_txt = "🔥 Güçlü Displacement (Hacimli Kırılım)"
        
        if curr_price > last_sh:
            structure = "BOS (Yükseliş Kırılımı) 🐂"
            bias = "bullish"
        elif curr_price < last_sl:
            structure = "BOS (Düşüş Kırılımı) 🐻"
            bias = "bearish"
        else:
            structure = "Internal Range (Düşüş/Düzeltme)"
            if close.iloc[-1] > open_.iloc[-1]: bias = "bullish_retrace" 
            else: bias = "bearish_retrace"

        next_bsl = min([h[1] for h in sw_highs if h[1] > curr_price], default=high.max())
        next_ssl = max([l[1] for l in sw_lows if l[1] < curr_price], default=low.min())

        bullish_fvgs = []; bearish_fvgs = []
        active_fvg_txt = "Yok"
        
        for i in range(len(df)-30, len(df)-1):
            if i < 2: continue
            if low.iloc[i] > high.iloc[i-2]:
                gap_size = low.iloc[i] - high.iloc[i-2]
                if gap_size > atr * 0.05:
                    bullish_fvgs.append({'top': low.iloc[i], 'bot': high.iloc[i-2], 'idx': i})
            elif high.iloc[i] < low.iloc[i-2]:
                gap_size = low.iloc[i-2] - high.iloc[i]
                if gap_size > atr * 0.05:
                    bearish_fvgs.append({'top': low.iloc[i-2], 'bot': high.iloc[i], 'idx': i})

        active_ob_txt = "Yok"
        mean_threshold = 0.0
        lookback = 20
        start_idx = max(0, len(df) - lookback)
        
        if bias == "bullish" or bias == "bullish_retrace":
            if bullish_fvgs:
                f = bullish_fvgs[-1]
                active_fvg_txt = f"Açık FVG var (Destek): {f['bot']:.2f} - {f['top']:.2f}"
            lowest_idx = df['Low'].iloc[start_idx:].idxmin()
            if isinstance(lowest_idx, pd.Timestamp): lowest_idx = df.index.get_loc(lowest_idx)
            for i in range(lowest_idx, max(0, lowest_idx-5), -1):
                if df['Close'].iloc[i] < df['Open'].iloc[i]:
                    ob_low = df['Low'].iloc[i]
                    ob_high = df['High'].iloc[i]
                    active_ob_txt = f"{ob_low:.2f} - {ob_high:.2f} (Talep Bölgesi)"
                    mean_threshold = (ob_low + ob_high) / 2
                    break
                    
        elif bias == "bearish" or bias == "bearish_retrace":
            if bearish_fvgs:
                f = bearish_fvgs[-1]
                active_fvg_txt = f"Açık FVG var (Direnç): {f['bot']:.2f} - {f['top']:.2f}"
            highest_idx = df['High'].iloc[start_idx:].idxmax()
            if isinstance(highest_idx, pd.Timestamp): highest_idx = df.index.get_loc(highest_idx)
            for i in range(highest_idx, max(0, highest_idx-5), -1):
                if df['Close'].iloc[i] > df['Open'].iloc[i]:
                    ob_low = df['Low'].iloc[i]
                    ob_high = df['High'].iloc[i]
                    active_ob_txt = f"{ob_low:.2f} - {ob_high:.2f} (Arz Bölgesi)"
                    mean_threshold = (ob_low + ob_high) / 2
                    break

        range_high = max(high.tail(60)); range_low = min(low.tail(60))
        range_loc = (curr_price - range_low) / (range_high - range_low)
        zone = "PREMIUM (Pahalı)" if range_loc > 0.5 else "DISCOUNT (Ucuz)"

        setup_type = "BEKLE"
        entry_price = 0.0; stop_loss = 0.0; take_profit = 0.0; rr_ratio = 0.0
        setup_desc = "Mantıklı bir R/R kurulumu veya Bölge uyumu bekleniyor."
        
        if bias in ["bullish", "bullish_retrace"] and zone == "DISCOUNT (Ucuz)":
            valid_fvgs = [f for f in bullish_fvgs if f['top'] < curr_price]
            if valid_fvgs and next_bsl > curr_price:
                best_fvg = valid_fvgs[-1]
                temp_entry = best_fvg['top']
                if next_bsl > temp_entry:
                    entry_price = temp_entry
                    take_profit = next_bsl
                    stop_loss = last_sl if last_sl < entry_price else best_fvg['bot'] - atr * 0.5
                    risk = entry_price - stop_loss
                    reward = take_profit - entry_price
                    if risk > 0:
                        rr_ratio = reward / risk
                        setup_type = "LONG"
                        setup_desc = "Fiyat ucuzluk bölgesinde. FVG desteğinden yukarıdaki likidite (BSL) hedefleniyor."

        elif bias in ["bearish", "bearish_retrace"] and zone == "PREMIUM (Pahalı)":
            valid_fvgs = [f for f in bearish_fvgs if f['bot'] > curr_price]
            if valid_fvgs and next_ssl < curr_price:
                best_fvg = valid_fvgs[-1]
                temp_entry = best_fvg['bot']
                if next_ssl < temp_entry:
                    entry_price = temp_entry
                    take_profit = next_ssl
                    stop_loss = last_sh if last_sh > entry_price else best_fvg['top'] + atr * 0.5
                    risk = stop_loss - entry_price
                    reward = entry_price - take_profit
                    if risk > 0:
                        rr_ratio = reward / risk
                        setup_type = "SHORT"
                        setup_desc = "Fiyat pahalılık bölgesinde. Direnç bloğundan aşağıdaki likidite (SSL) hedefleniyor."

        return {
            "status": "OK", "structure": structure, "bias": bias, "zone": zone,
            "setup_type": setup_type, "entry": entry_price, "stop": stop_loss, "target": take_profit,
            "rr": rr_ratio, "desc": setup_desc, "last_sl": last_sl, "last_sh": last_sh,
            "displacement": displacement_txt, "fvg_txt": active_fvg_txt, "ob_txt": active_ob_txt,
            "mean_threshold": mean_threshold, "curr_price": curr_price
        }

    except Exception: return error_ret
        
@st.cache_data(ttl=600)
def calculate_price_action_dna(ticker):
    try:
        df = get_safe_historical_data(ticker, period="6mo") 
        if df is None or len(df) < 50: return None
        
        o = df['Open']; h = df['High']; l = df['Low']; c = df['Close']; v = df['Volume']
        
        # --- VERİ HAZIRLIĞI (SON 3 GÜN) ---
        c1_o, c1_h, c1_l, c1_c = float(o.iloc[-1]), float(h.iloc[-1]), float(l.iloc[-1]), float(c.iloc[-1]) # Bugün
        c2_o, c2_h, c2_l, c2_c = float(o.iloc[-2]), float(h.iloc[-2]), float(l.iloc[-2]), float(c.iloc[-2]) # Dün
        c3_o, c3_h, c3_l, c3_c = float(o.iloc[-3]), float(h.iloc[-3]), float(l.iloc[-3]), float(c.iloc[-3]) # Önceki Gün
        
        c1_v = float(v.iloc[-1])
        avg_v = float(v.rolling(20).mean().iloc[-1]) 
        sma50 = c.rolling(50).mean().iloc[-1]
        
        # RSI Serisi (Uyumsuzluk için)
        delta = c.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs_calc = gain / loss
        rsi_series = 100 - (100 / (1 + rs_calc))
        rsi_val = rsi_series.iloc[-1]

        # Mum Geometrisi (Son gün)
        body = abs(c1_c - c1_o)
        total_len = c1_h - c1_l
        u_wick = c1_h - max(c1_o, c1_c)
        l_wick = min(c1_o, c1_c) - c1_l
        is_green = c1_c > c1_o
        is_red = c1_c < c1_o
        
        # Toleranslar
        wick_ratio = 2.0 
        doji_threshold = 0.15 
        tweezer_tol = c1_c * 0.001 

        bulls, bears, neutrals = [], [], []
        
        # --- BAĞLAM (CONTEXT) ANALİZİ ---
        trend_dir = "YÜKSELİŞ" if c1_c > sma50 else "DÜŞÜŞ"
        is_overbought = rsi_val > 70
        is_oversold = rsi_val < 30
        vol_confirmed = c1_v > avg_v * 1.2 

        # Sinyal Ekleme Fonksiyonu
        def add_signal(sig_list, name, is_bullish):
            prefix = ""
            if is_bullish:
                if trend_dir == "YÜKSELİŞ": prefix = "🔥 Trend Yönünde "
                elif trend_dir == "DÜŞÜŞ": prefix = "⚠️ Tepki/Dönüş "
                if is_overbought: prefix += "(Riskli Tepe) "
            else: 
                if trend_dir == "DÜŞÜŞ": prefix = "📉 Trend Yönünde "
                elif trend_dir == "YÜKSELİŞ": prefix = "⚠️ Düzeltme/Dönüş "
                if is_oversold: prefix += "(Riskli Dip) "
            suffix = " (Hacimli!)" if vol_confirmed else ""
            sig_list.append(f"{prefix}{name}{suffix}")

        # ======================================================
        # 1. TEKLİ MUM FORMASYONLARI
        # ======================================================
        if total_len > 0:
            # Hammer
            if l_wick > body * wick_ratio and u_wick < body * 0.5: 
                if trend_dir == "DÜŞÜŞ" or is_oversold: add_signal(bulls, "Hammer 🔨", True)
                else: neutrals.append("Hanging Man Potansiyeli")
            
            # Shooting Star
            if u_wick > body * wick_ratio and l_wick < body * 0.5: 
                if trend_dir == "YÜKSELİŞ" or is_overbought: add_signal(bears, "Shooting Star 🔫", False)
            
            # Stopping Volume (Smart Money İmzası)
            if (l_wick > body * 2.0) and (c1_v > avg_v * 1.5) and (c1_l < c2_l):
                bulls.append("🛑 STOPPING VOLUME (Kurumsal Alım)")
            
            # Marubozu
            if body > total_len * 0.85: 
                if is_green: add_signal(bulls, "Marubozu 🚀", True)
                else: add_signal(bears, "Marubozu 🔻", False)
            
            # Doji
            if body < total_len * doji_threshold: neutrals.append("Doji (Kararsızlık) ⚖️")

        # ======================================================
        # 2. İKİLİ MUM FORMASYONLARI
        # ======================================================
        
        # Bullish Kicker (Sert Gap Up)
        if (c2_c < c2_o) and is_green and (c1_o > c2_o): 
            add_signal(bulls, "Bullish Kicker (Sert GAP) 🦵", True)

        # Engulfing (Yutan)
        if (c2_c < c2_o) and is_green and (c1_c > c2_o) and (c1_o < c2_c): add_signal(bulls, "Bullish Engulfing 🐂", True)
        if (c2_c > c2_o) and is_red and (c1_c < c2_o) and (c1_o > c2_c): add_signal(bears, "Bearish Engulfing 🐻", False)
        
        # Piercing / Dark Cloud
        c2_mid = (c2_o + c2_c) / 2
        if (c2_c < c2_o) and is_green and (c1_o < c2_c) and (c1_c > c2_mid) and (c1_c < c2_o): add_signal(bulls, "Piercing Line 🌤️", True)
        if (c2_c > c2_o) and is_red and (c1_o > c2_c) and (c1_c < c2_mid) and (c1_c > c2_o): add_signal(bears, "Dark Cloud Cover ☁️", False)
        
        # Tweezer (Cımbız)
        if abs(c1_l - c2_l) < tweezer_tol and (c1_l < c3_l): add_signal(bulls, "Tweezer Bottom 🥢", True)
        if abs(c1_h - c2_h) < tweezer_tol and (c1_h > c3_h): add_signal(bears, "Tweezer Top 🥢", False)
        
        # Harami
        if (c1_h < c2_h) and (c1_l > c2_l): neutrals.append("Harami (Inside Bar) 🤰")

        # ======================================================
        # 3. ÜÇLÜ MUM FORMASYONLARI
        # ======================================================
        
        # Morning Star (Sabah Yıldızı - Dipten Dönüş)
        # 1. Kırmızı, 2. Küçük Gövde, 3. Yeşil (ilk mumun yarısını geçen)
        if (c3_c < c3_o) and (abs(c2_c - c2_o) < total_len * 0.3) and is_green and (c1_c > (c3_o + c3_c)/2):
             if is_oversold or trend_dir == "DÜŞÜŞ": add_signal(bulls, "Morning Star ⭐", True)

        # [EKLENEN EKSİK PARÇA] Evening Star (Akşam Yıldızı - Tepeden Dönüş)
        # 1. Yeşil, 2. Küçük Gövde, 3. Kırmızı (ilk mumun yarısını aşağı geçen)
        if (c3_c > c3_o) and (abs(c2_c - c2_o) < total_len * 0.3) and is_red and (c1_c < (c3_o + c3_c)/2):
             if is_overbought or trend_dir == "YÜKSELİŞ": add_signal(bears, "Evening Star 🌆", False)

        # 3 White Soldiers
        if (c1_c > c1_o) and (c2_c > c2_o) and (c3_c > c3_o) and (c1_c > c2_c > c3_c):
             if c1_c > c1_h * 0.95: add_signal(bulls, "3 White Soldiers ⚔️", True)

        # 3 Black Crows
        if (c1_c < c1_o) and (c2_c < c2_o) and (c3_c < c3_o) and (c1_c < c2_c < c3_c):
             if c1_c < c1_l * 1.05: add_signal(bears, "3 Black Crows 🦅", False)

        # --- ÇIKTI FORMATLAMA ---
        signal_summary = ""
        priorities = ["Bullish Kicker", "Stopping Volume", "3 White Soldiers"]
        for p in priorities:
            for b in bulls:
                if p in b: bulls.remove(b); bulls.insert(0, b); break

        if bulls: signal_summary += f"ALICI: {', '.join(bulls)} "
        if bears: signal_summary += f"SATICI: {', '.join(bears)} "
        if neutrals: signal_summary += f"NÖTR: {', '.join(neutrals)}"
        
        candle_desc = signal_summary if signal_summary else "Belirgin, güçlü bir formasyon yok."
        candle_title = "Formasyon Tespiti"

        # ======================================================
        # DİĞER GÖSTERGELER (SFP, VSA, KONUM, SIKIŞMA)
        # ======================================================
        
        # SFP
        sfp_txt, sfp_desc = "Yok", "Önemli bir tuzak tespiti yok."
        recent_highs = h.iloc[-20:-1].max(); recent_lows = l.iloc[-20:-1].min()
        if c1_h > recent_highs and c1_c < recent_highs: sfp_txt, sfp_desc = "⚠️ Bearish SFP (Boğa Tuzağı)", "Tepe temizlendi ama tutunamadı."
        elif c1_l < recent_lows and c1_c > recent_lows: sfp_txt, sfp_desc = "💎 Bullish SFP (Ayı Tuzağı)", "Dip temizlendi ve geri döndü."

        # VSA
        vol_txt, vol_desc = "Normal", "Hacim ortalama seyrediyor."
        if c1_v > avg_v * 1.5:
            if "🛑 STOPPING VOLUME" in signal_summary: vol_txt, vol_desc = "🛑 STOPPING VOLUME", "Düşüşte devasa hacimle frenleme."
            elif body < total_len * 0.3: vol_txt, vol_desc = "⚠️ Churning (Boşa Çaba)", "Yüksek hacme rağmen fiyat gidemiyor."
            else: vol_txt, vol_desc = "🔋 Trend Destekli", "Fiyat hareketi hacimle destekleniyor."

        # Konum (BOS)
        loc_txt, loc_desc = "Denge Bölgesi", "Fiyat konsolidasyon içinde."
        if c1_c > h.iloc[-20:-1].max(): loc_txt, loc_desc = "📈 Zirve Kırılımı (BOS)", "Son 20 günün zirvesi aşıldı."
        elif c1_c < l.iloc[-20:-1].min(): loc_txt, loc_desc = "📉 Dip Kırılımı (BOS)", "Son 20 günün dibi kırıldı."

        # Volatilite (Coil)
        atr = (h-l).rolling(14).mean().iloc[-1]
        range_5 = h.tail(5).max() - l.tail(5).min()
        sq_txt, sq_desc = "Normal", "Oynaklık normal seviyede."
        if range_5 < (1.5 * atr): sq_txt, sq_desc = "⏳ SÜPER SIKIŞMA (Coil)", "Fiyat yay gibi gerildi. Patlama yakın."

        # ======================================================
        # RSI UYUMSUZLUK (DIVERGENCE)
        # ======================================================
        div_txt, div_desc, div_type = "Uyumlu", "RSI ve Fiyat paralel.", "neutral"
        try:
            # Son 5 gün vs Önceki 15 gün
            current_window = c.iloc[-5:]
            prev_window = c.iloc[-20:-5]
            
            # Negatif Uyumsuzluk (Fiyat Tepe, RSI Düşük)
            p_curr_max = current_window.max(); p_prev_max = prev_window.max()
            r_curr_max = rsi_series.iloc[-5:].max(); r_prev_max = rsi_series.iloc[-20:-5].max()
            
            if (p_curr_max > p_prev_max) and (r_curr_max < r_prev_max) and (r_prev_max > 60):
                div_txt = "🐻 NEGATİF UYUMSUZLUK (Tepe Zayıflığı)"
                div_desc = "Fiyat yeni tepe yaptı ama RSI desteklemiyor. Düşüş riski!"
                div_type = "bearish"
                
            # Pozitif Uyumsuzluk (Fiyat Dip, RSI Yüksek)
            p_curr_min = current_window.min(); p_prev_min = prev_window.min()
            r_curr_min = rsi_series.iloc[-5:].min(); r_prev_min = rsi_series.iloc[-20:-5].min()
            
            if (p_curr_min < p_prev_min) and (r_curr_min > r_prev_min) and (r_prev_min < 45):
                div_txt = "💎 POZİTİF UYUMSUZLUK (Gizli Güç)"
                div_desc = "Fiyat yeni dip yaptı ama RSI yükseliyor. Toplama sinyali!"
                div_type = "bullish"     
        except: pass

        return {
            "candle": {"title": candle_title, "desc": candle_desc},
            "sfp": {"title": sfp_txt, "desc": sfp_desc},
            "vol": {"title": vol_txt, "desc": vol_desc},
            "loc": {"title": loc_txt, "desc": loc_desc},
            "sq": {"title": sq_txt, "desc": sq_desc},
            "div": {"title": div_txt, "desc": div_desc, "type": div_type}
        }
    except Exception: return None

# --- SUPERTREND VE FIBONACCI HESAPLAYICI ---

def calculate_supertrend(df, period=10, multiplier=3.0):
    """
    SuperTrend indikatörünü hesaplar.
    Dönüş: (SuperTrend Değeri, Trend Yönü [1: Boğa, -1: Ayı])
    """
    try:
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        # ATR Hesaplama
        tr1 = pd.DataFrame(high - low)
        tr2 = pd.DataFrame(abs(high - close.shift(1)))
        tr3 = pd.DataFrame(abs(low - close.shift(1)))
        frames = [tr1, tr2, tr3]
        tr = pd.concat(frames, axis=1, join='inner').max(axis=1)
        atr = tr.ewm(alpha=1/period, adjust=False).mean()

        # Temel Bantlar
        hl2 = (high + low) / 2
        final_upperband = hl2 + (multiplier * atr)
        final_lowerband = hl2 - (multiplier * atr)
        
        supertrend = [True] * len(df) # Başlangıç (True = Boğa varsayımı)
        st_value = [0.0] * len(df)
        
        # Döngüsel Hesaplama (SuperTrend doğası gereği önceki değere bakar)
        for i in range(1, len(df.index)):
            curr, prev = i, i-1
            
            # Üst Bant Mantığı
            if close.iloc[curr] > final_upperband.iloc[prev]:
                supertrend[curr] = True
            elif close.iloc[curr] < final_lowerband.iloc[prev]:
                supertrend[curr] = False
            else:
                supertrend[curr] = supertrend[prev]
                
                # Bantları Daraltma (Trailing Stop Mantığı)
                if supertrend[curr] == True and final_lowerband.iloc[curr] < final_lowerband.iloc[prev]:
                    final_lowerband.iloc[curr] = final_lowerband.iloc[prev]
                
                if supertrend[curr] == False and final_upperband.iloc[curr] > final_upperband.iloc[prev]:
                    final_upperband.iloc[curr] = final_upperband.iloc[prev]

            if supertrend[curr] == True:
                st_value[curr] = final_lowerband.iloc[curr]
            else:
                st_value[curr] = final_upperband.iloc[curr]
                
        return st_value[-1], (1 if supertrend[-1] else -1)
        
    except Exception:
        return 0, 0

def calculate_fib_levels(df, period=144):
    """
    Son N periyodun en yüksek ve en düşüğüne göre Fibonacci seviyelerini hesaplar.
    """
    try:
        if len(df) < period: period = len(df)
        recent_data = df.tail(period)
        
        max_h = recent_data['High'].max()
        min_l = recent_data['Low'].min()
        diff = max_h - min_l
        
        levels = {
            "0 (Tepe)": max_h,
            "0.236": max_h - (diff * 0.236),
            "0.382": max_h - (diff * 0.382),
            "0.5 (Orta)": max_h - (diff * 0.5),
            "0.618 (Golden)": max_h - (diff * 0.618),
            "0.786": max_h - (diff * 0.786),
            "1 (Dip)": min_l
        }
        return levels
    except:
        return {}

@st.cache_data(ttl=600)
def get_advanced_levels_data(ticker):
    """
    Arayüz için verileri paketler.
    """
    df = get_safe_historical_data(ticker, period="1y")
    if df is None: return None
    
    # 1. SuperTrend
    st_val, st_dir = calculate_supertrend(df)
    
    # 2. Fibonacci (Son 6 ay ~120 gün baz alınarak)
    fibs = calculate_fib_levels(df, period=120)
    
    curr_price = df['Close'].iloc[-1]
    
    # En yakın destek ve direnci bulma
    sorted_fibs = sorted(fibs.items(), key=lambda x: x[1])
    support = (None, -999999)
    resistance = (None, 999999)
    
    for label, val in sorted_fibs:
        if val < curr_price and val > support[1]:
            support = (label, val)
        if val > curr_price and val < resistance[1]:
            resistance = (label, val)
            
    return {
        "st_val": st_val,
        "st_dir": st_dir,
        "fibs": fibs,
        "nearest_sup": support,
        "nearest_res": resistance,
        "curr_price": curr_price
    }

# ==============================================================================
# 4. GÖRSELLEŞTİRME FONKSİYONLARI (EKSİK OLAN KISIM)
# ==============================================================================

def render_sentiment_card(sent):
    if not sent: return
    display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")
    
    # 1. SKOR RENKLERİ VE İKONLARI
    score = sent['total']
    if score >= 70: color = "#16a34a"; icon = "🔥"; status = "GÜÇLÜ BOĞA"
    elif score >= 50: color = "#d97706"; icon = "↔️"; status = "NÖTR / POZİTİF" # Tahteravalli (Denge)
    elif score >= 30: color = "#b91c1c"; icon = "🐻"; status = "ZAYIF / AYI"
    else: color = "#7f1d1d"; icon = "❄️"; status = "ÇÖKÜŞ"
    
    html_content = f"""
    <div class="info-card">
        <div class="info-header">🎭 Smart Money Sentiment: {display_ticker}</div>
        
        <div class="info-row" style="border-bottom: 2px solid {color}; padding-bottom:6px; margin-bottom:8px; background-color:{color}10; border-radius:4px; padding:6px;">
            <div style="font-weight:500; color:{color}; font-size:1rem;">{score}/100 {icon} {status}</div>
        </div>
        
        <div style="font-family:'Arial', sans-serif; font-size:0.8rem; color:#1e3a8a; margin-bottom:8px; text-align:center; letter-spacing:1px;">{sent['bar']}</div>
        
        <div class="info-row" style="background:#f0f9ff; padding:2px; border-radius:4px;">
            <div class="label-long" style="width:120px; color:#0369a1;">1. YAPI (25p):</div>
            <div class="info-val" style="font-weight:700;">{sent['str']}</div>
        </div>
        <div class="edu-note">Market Yapısı- Son 20 günün zirvesini yukarı kırarsa (15). Son 5 günün en düşük seviyesi, önceki 20 günün en düşük seviyesinden yukarıdaysa: HL (10)</div>

        <div class="info-row">
            <div class="label-long" style="width:120px;">2. TREND (25p):</div>
            <div class="info-val">{sent['tr']}</div>
        </div>
        <div class="edu-note">Ortalamalara bakar. Hisse fiyatı SMA200 üstünde (10). EMA20 üstünde (10). Kısa vadeli ortalama, orta vadeli ortalamanın üzerinde, yani EMA20 > SMA50 (5)</div>
        
        <div class="info-row">
            <div class="label-long" style="width:120px;">3. HACİM (25p):</div>
            <div class="info-val">{sent['vol']}</div>
        </div>
        <div class="edu-note">Hacmin 20G ortalamaya oranını ve On-Balance Volume (OBV) denetler. Bugünün hacmi son 20G ort.üstünde (15) Para girişi var: 10G ortalamanın üstünde (10)</div>

        <div class="info-row">
            <div class="label-long" style="width:120px;">4. MOMENTUM (15p):</div>
            <div class="info-val">{sent['mom']}</div>
        </div>
        <div class="edu-note">RSI ve MACD ile itki gücünü ölçer. 50 üstü RSI (5) RSI ivmesi artıyor (5). MACD sinyal çizgisi üstünde (5)</div>
        
        <div class="info-row">
            <div class="label-long" style="width:120px;">5. SIKIŞMA (10p):</div>
            <div class="info-val">{sent['vola']}</div>
        </div>
        <div class="edu-note">Bollinger Bant genişliğini inceler. Bant genişliği son 20G ortalamasından dar (10)</div>
    </div>
    """.replace("\n", "")
    
    st.markdown(html_content, unsafe_allow_html=True)

def render_deep_xray_card(xray):
    if not xray: return
    
    display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")
    
    html_icerik = f"""
    <div class="info-card">
        <div class="info-header">🔍 Derin Teknik Röntgen: {display_ticker}</div>
        
        <div class="info-row">
            <div class="label-long">1. Momentum:</div>
            <div class="info-val">{xray['mom_rsi']} | {xray['mom_macd']}</div>
        </div>
        <div class="edu-note">RSI 50 üstü ve MACD pozitif bölgedeyse ivme alıcıların kontrolündedir. RSI 50 üstünde? MACD 0'dan büyük?</div>

        <div class="info-row">
            <div class="label-long">2. Hacim Akışı:</div>
            <div class="info-val">{xray['vol_obv']}</div>
        </div>
        <div class="edu-note">Para girişinin (OBV) fiyat hareketini destekleyip desteklemediğini ölçer. OBV, 5 günlük ortalamasının üzerinde?</div>

        <div class="info-row">
            <div class="label-long">3. Trend Sağlığı:</div>
            <div class="info-val">{xray['tr_ema']} | {xray['tr_adx']}</div>
        </div>
        <div class="edu-note">Fiyatın EMA50 ve EMA200 üzerindeki kalıcılığını ve trendin gücünü denetler. 1. EMA50 EMA200'ü yukarı kesmiş? 2. Zaten üstünde?</div>

        <div class="info-row">
            <div class="label-long">4. Volatilite:</div>
            <div class="info-val">{xray['vola_bb']}</div>
        </div>
        <div class="edu-note">Bollinger Bantlarındaki daralma, yakında bir patlama olabileceğini gösterir. Fiyat üst bandı yukarı kırdı?</div>

        <div class="info-row">
            <div class="label-long">5. Piyasa Yapısı:</div>
            <div class="info-val">{xray['str_bos']}</div>
        </div>
        <div class="edu-note">Kritik direnç seviyelerinin kalıcı olarak aşılması (BOS) yükselişin devamı için şarttır. Fiyat son 20 günün en yüksek seviyesini aştı?</div>
    </div>
    """.replace("\n", "")
    
    st.markdown(html_icerik, unsafe_allow_html=True)
    
def render_detail_card_advanced(ticker):
    ACIKLAMALAR = {
        "Squeeze": "🚀 Squeeze: Bollinger Bant genişliği son 60 günün en dar aralığında (Patlama Hazır)",
        "Trend": "⚡ Trend: EMA5 > EMA20 üzerinde (Yükseliyor)",
        "MACD": "🟢 MACD: Histogram bir önceki günden yüksek (Momentum Artışı Var)",
        "Hacim": "🔊 Hacim: Son 5 günlük hacim ortalama hacmin %20 üzerinde",
        "Breakout": "🔨 Breakout: Fiyat son 20 gün zirvesinin %98 veya üzerinde",
        "RSI Güçlü": "⚓ RSI Güçlü: 30-65 arasında ve artışta",
        "Hacim Patlaması": "💥 Hacim son 20 gün ortalamanın %30 üzerinde seyrediyor",
        "RS (S&P500)": "💪 Hisse, Endeksten daha güçlü",
        "Boğa Trendi": "🐂 Boğa Trendi: Fiyat Üç Ortalamanın da (SMA50 > SMA100 > SMA200) üzerinde",
        "60G Zirve": "⛰️ Zirve: Fiyat son 60 günün tepesine %97 yakınlıkta",
        "RSI Bölgesi": "🎯 RSI Uygun: Pullback için uygun (40-55 arası)",
        "Ichimoku": "☁️ Ichimoku: Fiyat Bulutun Üzerinde (Trend Pozitif)",
        "RS": "💪 Relatif Güç (RS)",
        "Setup": "🛠️ Setup Durumu",
        "ADX Durumu": "💪 ADX Trend Gücü"
    }

    display_ticker = ticker.replace(".IS", "").replace("=F", "")
    dt = get_tech_card_data(ticker)
    info = fetch_stock_info(ticker)
    
    price_val = f"{info['price']:.2f}" if info else "Veri Yok"
    ma_vals = f"SMA50: {dt['sma50']:.0f} | SMA200: {dt['sma200']:.0f}" if dt else ""
    stop_vals = f"{dt['stop_level']:.2f} (Risk: %{dt['risk_pct']:.1f})" if dt else ""

    # RADAR 1 VERİSİ
    r1_res = {}; r1_score = 0
    if st.session_state.scan_data is not None:
        row = st.session_state.scan_data[st.session_state.scan_data["Sembol"] == ticker]
        if not row.empty and "Detaylar" in row.columns: r1_res = row.iloc[0]["Detaylar"]; r1_score = row.iloc[0]["Skor"]
    if not r1_res:
        temp_df = analyze_market_intelligence([ticker])
        if not temp_df.empty and "Detaylar" in temp_df.columns: r1_res = temp_df.iloc[0]["Detaylar"]; r1_score = temp_df.iloc[0]["Skor"]

    # RADAR 2 VERİSİ
    r2_res = {}; r2_score = 0
    if st.session_state.radar2_data is not None:
        row = st.session_state.radar2_data[st.session_state.radar2_data["Sembol"] == ticker]
        if not row.empty and "Detaylar" in row.columns: r2_res = row.iloc[0]["Detaylar"]; r2_score = row.iloc[0]["Skor"]
    if not r2_res:
        temp_df2 = radar2_scan([ticker])
        if not temp_df2.empty and "Detaylar" in temp_df2.columns: r2_res = temp_df2.iloc[0]["Detaylar"]; r2_score = temp_df2.iloc[0]["Skor"]

    r1_suffix = ""
    if r1_score < 2: r1_suffix = " <span style='color:#dc2626; font-weight:500; background:#fef2f2; padding:1px 4px; border-radius:3px; margin-left:5px; font-size:0.7rem;'>(⛔ RİSKLİ)</span>"
    elif r1_score > 5: r1_suffix = " <span style='color:#16a34a; font-weight:500; background:#f0fdf4; padding:1px 4px; border-radius:3px; margin-left:5px; font-size:0.7rem;'>(🚀 GÜÇLÜ)</span>"

    def get_icon(val): return "✅" if val else "❌"

    # RADAR 1 HTML (FİLTRELİ)
    r1_html = ""
    for k, v in r1_res.items():
        if k in ACIKLAMALAR: 
            text = ACIKLAMALAR.get(k, k); is_valid = v
            if isinstance(v, (tuple, list)): 
                is_valid = v[0]; val_num = v[1]
                if k == "RSI Güçlü": text = f"⚓ RSI Güçlü: ({int(val_num)})"
                elif k == "ADX Durumu": text = f"💪 ADX Güçlü: {int(val_num)}" if is_valid else f"⚠️ ADX Zayıf: {int(val_num)}"
            r1_html += f"<div class='tech-item' style='margin-bottom:2px;'>{get_icon(is_valid)} <span style='margin-left:4px;'>{text}</span></div>"

    # RADAR 2 HTML (FİLTRELİ ve DÜZELTİLMİŞ)
    r2_html = ""
    for k, v in r2_res.items():
        if k in ACIKLAMALAR:
            text = ACIKLAMALAR.get(k, k); is_valid = v
            
            if isinstance(v, (tuple, list)): 
                is_valid = v[0]; val_num = v[1]
                if k == "RSI Bölgesi": text = f"🎯 RSI Uygun: ({int(val_num)})"
            
            # Ichimoku Özel Kontrolü (Gerekirse)
            if k == "Ichimoku":
                # Eğer özel bir şey yapmak istersen buraya, yoksa standart metin gelir
                pass 

            r2_html += f"<div class='tech-item' style='margin-bottom:2px;'>{get_icon(is_valid)} <span style='margin-left:4px;'>{text}</span></div>"

    full_html = f"""
    <div class="info-card">
        <div class="info-header">📋 Gelişmiş Teknik Kart: {display_ticker}</div>
        <div style="display:flex; justify-content:space-between; margin-bottom:8px; border-bottom:1px solid #e5e7eb; padding-bottom:4px;">
            <div style="font-size:0.8rem; font-weight:700; color:#1e40af;">Fiyat: {price_val}</div>
            <div style="font-size:0.75rem; color:#64748B;">{ma_vals}</div>
        </div>
        <div style="font-size:0.8rem; color:#991b1b; margin-bottom:8px;">🛑 Stop: {stop_vals}</div>
        <div style="background:#f0f9ff; padding:4px; border-radius:4px; margin-bottom:4px;">
            <div style="font-weight:700; color:#0369a1; font-size:0.75rem; margin-bottom:4px;">🧠 RADAR 1 - Kısa Vade (3-12 gün): Momentum ve Hacim artışlarını yakala - Skor: {r1_score}/7{r1_suffix}</div>
            <div class="tech-grid" style="font-size:0.75rem;">{r1_html}</div>
        </div>
        <div style="background:#f0fdf4; padding:4px; border-radius:4px;">
            <div style="font-weight:700; color:#15803d; font-size:0.75rem; margin-bottom:4px;">🚀 RADAR 2 - Orta Vade (10-50 gün): Trend Takibi - Skor: {r2_score}/7</div>
            <div class="tech-grid" style="font-size:0.75rem;">{r2_html}</div>
        </div>
    </div>
    """
    st.markdown(full_html.replace("\n", " "), unsafe_allow_html=True)

def render_synthetic_sentiment_panel(data):
    if data is None or data.empty: return
    display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")
    st.markdown(f"""<div class="info-card" style="margin-bottom:10px;"><div class="info-header">🌊 Para Akış İvmesi & Fiyat Dengesi: {display_ticker}</div></div>""", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1]); x_axis = alt.X('Date_Str', axis=alt.Axis(title=None, labelAngle=-45), sort=None)
    with c1:
        base = alt.Chart(data).encode(x=x_axis)
        color_condition = alt.condition(
            alt.datum.MF_Smooth > 0,
            alt.value("#3b82f6"), 
            alt.value("#ef4444")
        )
        bars = base.mark_bar(size=15, opacity=0.9).encode(
            y=alt.Y('MF_Smooth:Q', axis=alt.Axis(title='Para Akışı (Güç)', labels=False, titleColor='#4338ca')), 
            color=color_condition, 
            tooltip=['Date_Str', 'Price', 'MF_Smooth']
        )
        price_line = base.mark_line(color='#1e40af', strokeWidth=2).encode(y=alt.Y('Price:Q', scale=alt.Scale(zero=False), axis=alt.Axis(title='Fiyat', titleColor='#0f172a')))
        st.altair_chart(alt.layer(bars, price_line).resolve_scale(y='independent').properties(height=280, title=alt.TitleParams("Momentum", fontSize=14, color="#1e40af")), use_container_width=True)
    with c2:
        base2 = alt.Chart(data).encode(x=x_axis)
        line_stp = base2.mark_line(color='#fbbf24', strokeWidth=3).encode(y=alt.Y('STP:Q', scale=alt.Scale(zero=False), axis=alt.Axis(title='Fiyat', titleColor='#64748B')), tooltip=['Date_Str', 'STP', 'Price'])
        line_price = base2.mark_line(color='#2563EB', strokeWidth=2).encode(y='Price:Q')
        area = base2.mark_area(opacity=0.15, color='gray').encode(y='STP:Q', y2='Price:Q')
        st.altair_chart(alt.layer(area, line_stp, line_price).properties(height=280, title=alt.TitleParams("EMA6 Analizi: Mavi (Fiyat) Sarıyı (STP) Yukarı Keserse AL", fontSize=14, color="#1e40af")), use_container_width=True)

def render_price_action_panel(ticker):
    pa = calculate_price_action_dna(ticker)
    if not pa:
        st.info("PA verisi bekleniyor...")
        return

    display_ticker = ticker.replace(".IS", "").replace("=F", "")

    sfp_color = "#16a34a" if "Bullish" in pa['sfp']['title'] else "#dc2626" if "Bearish" in pa['sfp']['title'] else "#475569"
    sq_color = "#d97706" if "BOBİN" in pa['sq']['title'] else "#475569"
    
    # RSI DIV RENKLENDİRME
    div_data = pa.get('div', {'type': 'neutral', 'title': '-', 'desc': '-'})
    if div_data['type'] == 'bearish':
        div_style = "background:#fef2f2; border-left:3px solid #dc2626; color:#991b1b;"
    elif div_data['type'] == 'bullish':
        div_style = "background:#f0fdf4; border-left:3px solid #16a34a; color:#166534;"
    else:
        div_style = "color:#475569;"
    
    html_content = f"""
    <div class="info-card" style="border-top: 3px solid #6366f1;">
        <div class="info-header" style="color:#1e3a8a;">🕯️ Price Action Analizi: {display_ticker}</div>

        <div style="margin-bottom:8px;">
            <div style="font-weight:700; font-size:0.8rem; color:#1e3a8a;">1. MUM & FORMASYONLAR: {pa['candle']['title']}</div>
            <div class="edu-note">{pa['candle']['desc']}</div>
        </div>

        <div style="margin-bottom:8px; border-left: 2px solid {sfp_color}; padding-left:6px;">
            <div style="font-weight:700; font-size:0.8rem; color:{sfp_color};">2. TUZAK DURUMU: {pa['sfp']['title']}</div>
            <div class="edu-note">{pa['sfp']['desc']}</div>
        </div>

        <div style="margin-bottom:8px;">
            <div style="font-weight:700; font-size:0.8rem; color:#0f172a;">3. HACİM & VSA ANALİZİ: {pa['vol']['title']}</div>
            <div class="edu-note">{pa['vol']['desc']}</div>
        </div>

        <div style="margin-bottom:8px;">
            <div style="font-weight:700; font-size:0.8rem; color:#0f172a;">4. BAĞLAM & KONUM: {pa['loc']['title']}</div>
            <div class="edu-note">{pa['loc']['desc']}</div>
        </div>

        <div style="margin-bottom:8px;">
            <div style="font-weight:700; font-size:0.8rem; color:{sq_color};">5. VOLATİLİTE: {pa['sq']['title']}</div>
            <div class="edu-note">{pa['sq']['desc']}</div>
        </div>

        <div style="margin-bottom:6px; padding:4px; border-radius:4px; {div_style}">
            <div style="font-weight:700; font-size:0.8rem;">6. RSI UYUMSUZLUK: {div_data['title']}</div>
            <div class="edu-note" style="margin-bottom:0; color:inherit; opacity:0.9;">{div_data['desc']}</div>
        </div>
        
    </div>
    """
    st.markdown(html_content.replace("\n", " "), unsafe_allow_html=True)
    

def render_ict_deep_panel(ticker):
    data = calculate_ict_deep_analysis(ticker)
    
    if not data or data.get("status") == "Error":
        st.warning(f"ICT Analiz Bekleniyor... ({data.get('msg', 'Veri Yok')})")
        return
    
    struct_desc = "Piyasa kararsız."
    if "BOS (Yükseliş" in data['structure']: struct_desc = "Boğalar kontrolü elinde tutuyor. Eski tepeler aşıldı, bu da yükseliş iştahının devam ettiğini gösterir. Geri çekilmeler alım fırsatı olabilir."
    elif "BOS (Düşüş" in data['structure']: struct_desc = "Ayılar piyasaya hakim. Eski dipler kırıldı, düşüş trendi devam ediyor. Yükselişler satış fırsatı olarak görülebilir."
    elif "Internal" in data['structure']: struct_desc = "Ana trendin tersine bir düzeltme hareketi (Internal Range) yaşanıyor olabilir. Piyasada kararsızlık hakim."

    energy_desc = "Mum gövdeleri küçük, hacimsiz bir hareket. Kurumsal oyuncular henüz oyuna tam girmemiş olabilir. Kırılımlar tuzak olabilir."
    if "Güçlü" in data['displacement']: energy_desc = "Fiyat güçlü ve hacimli mumlarla hareket ediyor. Bu 'Akıllı Para'nın (Smart Money) ayak sesidir."

    zone_desc = "Fiyat 'Ucuzluk' (Discount) bölgesinde. Kurumsal yatırımcılar bu seviyelerden alım yapmayı tercih eder."
    if "PREMIUM" in data['zone']: zone_desc = "Fiyat 'Pahalılık' (Premium) bölgesinde. Kurumsal yatırımcılar bu bölgede satış yapmayı veya kar almayı sever."

    fvg_desc = "Dengesizlik Boşluğu: Yani, Fiyatın denge bulmak için bu aralığı doldurması (rebalance) beklenir. Mıknatıs etkisi yapar."
    if "Yok" in data['fvg_txt']: fvg_desc = "Yakınlarda önemli bir dengesizlik boşluğu tespit edilemedi."

    ob_desc = "Order Block: Yani Kurumsal oyuncuların son yüklü işlem yaptığı seviye. Fiyat buraya dönerse güçlü tepki alabilir."
    
    liq_desc = "Yani Fiyatın bir sonraki durağı. Stop emirlerinin (Likiditenin) biriktiği, fiyatın çekildiği hedef seviye."

    bias_color = "#16a34a" if "bullish" in data['bias'] else "#dc2626" if "bearish" in data['bias'] else "#475569"
    bg_color_old = "#f0fdf4" if "bullish" in data['bias'] else "#fef2f2" if "bearish" in data['bias'] else "#f8fafc"

    mt_html = "" 
    mt_val = data.get('mean_threshold', 0)
    curr = data.get('curr_price', 0)
    
    if mt_val > 0 and curr > 0:
        diff_pct = (curr - mt_val) / mt_val
        if abs(diff_pct) < 0.003: 
            mt_status = "⚠️ KARAR ANI (BIÇAK SIRTI)"
            mt_desc = "Fiyat, yapının tam %50 denge noktasını test ediyor. Kırılım yönü beklenmeli."
            mt_color = "#d97706"; mt_bg = "#fffbeb" 
        elif diff_pct > 0:
            mt_status = "🛡️ Alıcılar Korumada" if "bullish" in data['bias'] else "Fiyat Dengenin Üzerinde"
            mt_desc = "Fiyat kritik orta noktanın üzerinde tutunuyor. Yapı korunuyor."
            mt_color = "#15803d"; mt_bg = "#f0fdf4" 
        else:
            mt_status = "🛡️ Satıcılar Baskın" if "bearish" in data['bias'] else "💀 Savunma Çöktü"
            mt_desc = "Fiyat kritik orta noktanın altına sarktı. Yapı bozulmuş olabilir."
            mt_color = "#b91c1c"; mt_bg = "#fef2f2" 
            
        mt_html = f"""
        <div style="background:{mt_bg}; padding:6px; border-radius:5px; border-left:3px solid {mt_color}; margin-bottom:8px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:700; color:{mt_color}; font-size:0.8rem;">⚖️ {mt_status}</span>
                <span style="font-family:'JetBrains Mono'; font-size:0.8rem; font-weight:700;">{mt_val:.2f}</span>
            </div>
            <div class="edu-note" style="margin-bottom:0;">{mt_desc}</div>
        </div>
        """

    if data['setup_type'] == "LONG":
        header_color = "#166534"; bg_color = "#f0fdf4"; border_color = "#16a34a"; icon = "🚀"
    elif data['setup_type'] == "SHORT":
        header_color = "#991b1b"; bg_color = "#fef2f2"; border_color = "#ef4444"; icon = "🔻"
    else:
        header_color = "#475569"; bg_color = "#f8fafc"; border_color = "#cbd5e1"; icon = "⏳"

    rr_display = f"{data['rr']:.2f}R" if data['rr'] > 0 else "-"
    
    html_content = f"""
    <div class="info-card" style="margin-bottom:8px;">
        <div class="info-header">🧠 ICT Smart Money Analizi: {display_ticker}</div>
        
        <div style="background:{bg_color_old}; padding:6px; border-radius:5px; border-left:3px solid {bias_color}; margin-bottom:8px;">
            <div style="font-weight:700; color:{bias_color}; font-size:0.8rem; margin-bottom:2px;">{data['structure']}</div>
            <div class="edu-note">{struct_desc}</div>
            
            <div class="info-row"><div class="label-long">Enerji:</div><div class="info-val">{data['displacement']}</div></div>
            <div class="edu-note">{energy_desc}</div>
        </div>

        {mt_html}

        <div style="margin-bottom:8px;">
            <div style="font-size:0.8rem; font-weight:700; color:#1e3a8a; border-bottom:1px dashed #cbd5e1; margin-bottom:4px;">📍 Ucuz Pahalı Okları (Giriş/Çıkış Referansları)</div>
            
            <div class="info-row"><div class="label-long">Konum:</div><div class="info-val" style="font-weight:700;">{data['zone']}</div></div>
            <div class="edu-note">{zone_desc}</div>
            
            <div class="info-row"><div class="label-long">GAP (FVG):</div><div class="info-val">{data['fvg_txt']}</div></div>
            <div class="edu-note">{fvg_desc}</div>
            
            <div class="info-row"><div class="label-long">Aktif OB:</div><div class="info-val">{data['ob_txt']}</div></div>
            <div class="edu-note">{ob_desc}</div>
        </div>

        <div style="background:#f1f5f9; padding:5px; border-radius:4px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:0.8rem; font-weight:600; color:#475569;">🧲 Hedef Likidite</span>
                <span style="font-family:'JetBrains Mono'; font-weight:700; font-size:0.8rem; color:#0f172a;">{data['target']:.2f}</span>
            </div>
            <div class="edu-note" style="margin-bottom:0;">{liq_desc}</div>
        </div>
    </div>

    <div class="info-card" style="border: 2px solid {border_color}; margin-top:5px;">
        <div style="background-color:{header_color}; color:white; padding:5px 10px; font-weight:700; border-radius:3px 3px 0 0; display:flex; justify-content:space-between; align-items:center;">
            <span>{icon} ICT TRADE SET-UP</span>
            <span style="font-family:'JetBrains Mono'; background:rgba(255,255,255,0.2); padding:2px 6px; border-radius:4px;">{data['setup_type']}</span>
        </div>
        <div style="padding:10px; background-color:{bg_color};">
            <div style="font-size:0.85rem; margin-bottom:10px; font-style:italic; color:#374151;">"{data['desc']}"</div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-bottom:10px;">
                <div style="background:white; padding:5px; border:1px solid #e5e7eb; border-radius:4px; text-align:center;">
                    <div style="font-size:0.7rem; color:#6b7280; font-weight:600;">GİRİŞ (ENTRY)</div>
                    <div style="font-family:'JetBrains Mono'; font-weight:700; color:{header_color};">{data['entry']:.2f}</div>
                </div>
                <div style="background:white; padding:5px; border:1px solid #e5e7eb; border-radius:4px; text-align:center;">
                    <div style="font-size:0.7rem; color:#6b7280; font-weight:600;">HEDEF (TP)</div>
                    <div style="font-family:'JetBrains Mono'; font-weight:700; color:#16a34a;">{data['target']:.2f}</div>
                </div>
                <div style="background:white; padding:5px; border:1px solid #e5e7eb; border-radius:4px; text-align:center;">
                    <div style="font-size:0.7rem; color:#6b7280; font-weight:600;">STOP (SL)</div>
                    <div style="font-family:'JetBrains Mono'; font-weight:700; color:#dc2626;">{data['stop']:.2f}</div>
                </div>
                <div style="background:white; padding:5px; border:1px solid #e5e7eb; border-radius:4px; text-align:center;">
                    <div style="font-size:0.7rem; color:#6b7280; font-weight:600;">RİSK/GETİRİ</div>
                    <div style="font-family:'JetBrains Mono'; font-weight:800; color:#0f172a;">{rr_display}</div>
                </div>
            </div>
        </div>
    </div>
    """
    
    st.markdown(html_content.replace("\n", " "), unsafe_allow_html=True)

def render_levels_card(ticker):
    data = get_advanced_levels_data(ticker)
    if not data: return

    # Renk ve İkon Ayarları
    is_bullish = data['st_dir'] == 1
    
    st_color = "#16a34a" if is_bullish else "#dc2626"
    st_text = "YÜKSELİŞ (AL)" if is_bullish else "DÜŞÜŞ (SAT)"
    st_icon = "🐂" if is_bullish else "🐻"
    
    # --- DİNAMİK METİN AYARLARI (YENİ KISIM) ---
    if is_bullish:
        # Yükseliş Senaryosu
        st_label = "Takip Eden Stop (Stop-Loss)"
        st_desc = "⚠️ Fiyat bu seviyenin <b>altına inerse</b> trend bozulur, stop olunmalıdır."
    else:
        # Düşüş Senaryosu
        st_label = "Trend Dönüşü (Direnç)"
        st_desc = "🚀 Fiyat bu seviyenin <b>üstüne çıkarsa</b> düşüş biter, yükseliş başlar."
    # -------------------------------------------
    
    # Fibonacci Formatlama
    sup_lbl, sup_val = data['nearest_sup']
    res_lbl, res_val = data['nearest_res']
    
    html_content = f"""
    <div class="info-card" style="border-top: 3px solid #8b5cf6;">
        <div class="info-header" style="color:#4c1d95;">📐 Kritik Seviyeler & Trend</div>
        
        <div style="background:{st_color}15; padding:8px; border-radius:5px; border:1px solid {st_color}; margin-bottom:8px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:700; color:{st_color}; font-size:0.8rem;">{st_icon} SuperTrend (10,3)</span>
                <span style="font-weight:500; color:{st_color}; font-size:0.9rem;">{st_text}</span>
            </div>
            <div style="font-size:0.75rem; color:#64748B; margin-top:2px;">
                {st_label}: <strong style="color:#0f172a;">{data['st_val']:.2f}</strong>
            </div>
            <div style="font-size:0.65rem; color:#6b7280; font-style:italic; margin-top:4px; border-top:1px dashed {st_color}40; padding-top:2px;">
                {st_desc}
            </div>
        </div>

        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:6px;">
            <div style="background:#f0fdf4; padding:6px; border-radius:4px; border:1px solid #bbf7d0;">
                <div style="font-size:0.65rem; color:#166534; font-weight:700;">EN YAKIN DİRENÇ 🚧</div>
                <div style="font-family:'JetBrains Mono'; font-weight:700; color:#15803d; font-size:0.85rem;">{res_val:.2f}</div>
                <div style="font-size:0.6rem; color:#166534; margin-bottom:2px;">Fib {res_lbl}</div>
                <div style="font-size:0.6rem; color:#64748B; font-style:italic; line-height:1.1;">Zorlu tavan. Geçilirse yükseliş hızlanır.</div>
            </div>
            
            <div style="background:#fef2f2; padding:6px; border-radius:4px; border:1px solid #fecaca;">
                <div style="font-size:0.65rem; color:#991b1b; font-weight:700;">EN YAKIN DESTEK 🛡️</div>
                <div style="font-family:'JetBrains Mono'; font-weight:700; color:#b91c1c; font-size:0.85rem;">{sup_val:.2f}</div>
                <div style="font-size:0.6rem; color:#991b1b; margin-bottom:2px;">Fib {sup_lbl}</div>
                <div style="font-size:0.6rem; color:#64748B; font-style:italic; line-height:1.1;">İlk savunma hattı. Düşüşü tutmalı.</div>
            </div>
        </div>
        
        <div style="margin-top:6px;">
            <div style="font-size:0.7rem; font-weight:700; color:#6b7280; margin-bottom:2px;">⚜️ Golden Pocket (0.618 - 0.65):</div>
            <div style="display:flex; align-items:center; gap:6px;">
                <div style="font-family:'JetBrains Mono'; font-size:0.8rem; background:#fffbeb; padding:2px 6px; border-radius:4px; border:1px dashed #f59e0b;">
                    {data['fibs'].get('0.618 (Golden)', 0):.2f}
                </div>
                <div style="font-size:0.65rem; color:#92400e; font-style:italic;">
                    Kurumsal alım bölgesi (İdeal Giriş).
                </div>
            </div>
        </div>
    </div>
    """
    st.markdown(html_content.replace("\n", " "), unsafe_allow_html=True)

def render_minervini_panel_v2(ticker):
    # 1. Verileri al
    cat = st.session_state.get('category', 'S&P 500')
    bench = "XU100.IS" if "BIST" in cat else "^GSPC"
    
    data = calculate_minervini_sepa(ticker, benchmark_ticker=bench)
    
    if not data: return 

    # --- HİSSE ADINI HAZIRLA ---
    display_ticker = ticker.replace(".IS", "").replace("=F", "")

    # 2. Görsel öğeleri hazırla
    trend_icon = "✅" if data['trend_ok'] else "❌"
    vcp_icon = "✅" if data['is_vcp'] else "❌"
    vol_icon = "✅" if data['is_dry'] else "❌"
    rs_icon = "✅" if data['rs_val'] > 0 else "❌"
    
    rs_width = min(max(int(data['rs_val'] * 5 + 50), 0), 100)
    rs_color = "#16a34a" if data['rs_val'] > 0 else "#dc2626"
    
    # 3. HTML KODU (HİSSE ADI EKLENDİ)
    html_content = f"""
<div class="info-card" style="border-top: 3px solid {data['color']};">
<div class="info-header" style="display:flex; justify-content:space-between; align-items:center; color:{data['color']};">
<span>🦁 Minervini SEPA Analizi</span>
<span style="font-size:0.8rem; font-weight:800; background:{data['color']}15; padding:2px 8px; border-radius:10px;">{data['score']}/100</span>
</div>
<div style="text-align:center; margin-bottom:5px;">
<div style="font-size:0.9rem; font-weight:800; color:{data['color']}; letter-spacing:0.5px;">{display_ticker} | {data['Durum']}</div>
</div>
<div class="edu-note" style="text-align:center; margin-bottom:10px;">
"Aşama 2" yükseliş trendi ve düşük oynaklık (VCP) aranıyor.
</div>
<div style="display:grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap:4px; margin-bottom:5px; text-align:center;">
<div style="background:#f8fafc; padding:4px; border-radius:4px; border:1px solid #e2e8f0;">
<div style="font-size:0.6rem; color:#64748B; font-weight:700;">TREND</div>
<div style="font-size:1rem;">{trend_icon}</div>
</div>
<div style="background:#f8fafc; padding:4px; border-radius:4px; border:1px solid #e2e8f0;">
<div style="font-size:0.6rem; color:#64748B; font-weight:700;">VCP</div>
<div style="font-size:1rem;">{vcp_icon}</div>
</div>
<div style="background:#f8fafc; padding:4px; border-radius:4px; border:1px solid #e2e8f0;">
<div style="font-size:0.6rem; color:#64748B; font-weight:700;">ARZ</div>
<div style="font-size:1rem;">{vol_icon}</div>
</div>
<div style="background:#f8fafc; padding:4px; border-radius:4px; border:1px solid #e2e8f0;">
<div style="font-size:0.6rem; color:#64748B; font-weight:700;">RS</div>
<div style="font-size:1rem;">{rs_icon}</div>
</div>
</div>
<div class="edu-note">
1. <b>Trend:</b> Fiyat > SMA200 (Yükseliş Trendinde vs Yatayda-Düşüşte)<br>
2. <b>VCP:</b> Fiyat sıkışıyor mu? (Düşük Oynaklık vs Dalgalı-Dengesiz Yapı)<br>
3. <b>Arz:</b> Düşüş günlerinde hacim daralıyor mu? (Satıcılar yoruldu vs Düşüşlerde hacim yüksek)<br>
4. <b>RS:</b> Endeksten daha mı güçlü? (Endeks düşerken bu hisse duruyor veya yükseliyor vs Endeksle veya daha çok düşüyor)
</div>
<div style="margin-bottom:2px; margin-top:8px;">
<div style="display:flex; justify-content:space-between; font-size:0.7rem; margin-bottom:2px;">
<span style="color:#64748B; font-weight:600;">Endeks Gücü (Mansfield RS)</span>
<span style="font-weight:700; color:{rs_color};">{data['rs_rating']}</span>
</div>
<div style="width:100%; height:6px; background:#e2e8f0; border-radius:3px; overflow:hidden;">
<div style="width:{rs_width}%; height:100%; background:{rs_color};"></div>
</div>
</div>
<div class="edu-note">Bar yeşil ve doluysa hisse endeksi yeniyor (Lider).</div>
<div style="margin-top:6px; padding-top:4px; border-top:1px dashed #cbd5e1; font-size:0.7rem; color:#475569; display:flex; justify-content:space-between;">
<span>SMA200: {data['sma200']:.2f}</span>
<span>52H Zirve: {data['year_high']:.2f}</span>
</div>
<div class="edu-note">Minervini Kuralı: Fiyat 52 haftalık zirveye %25'ten fazla uzak olmamalı.</div>
</div>
"""
    
    st.markdown(html_content, unsafe_allow_html=True)
    
# ==============================================================================
# 5. SIDEBAR UI
# ==============================================================================
with st.sidebar:
    st.markdown(f"""<div style="font-size:1.5rem; font-weight:700; color:#1e3a8a; text-align:center; padding-top: 10px; padding-bottom: 10px;">SMART MONEY RADAR</div><hr style="border:0; border-top: 1px solid #e5e7eb; margin-top:5px; margin-bottom:10px;">""", unsafe_allow_html=True)
    
    # 1. PİYASA DUYGUSU (En Üstte)
    sentiment_verisi = calculate_sentiment_score(st.session_state.ticker)
    if sentiment_verisi:
        render_sentiment_card(sentiment_verisi)

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # YENİ MINERVINI PANELİ (Hatasız Versiyon)
    render_minervini_panel_v2(st.session_state.ticker)
    
    # --- YILDIZ ADAYLARI (KESİŞİM PANELİ) ---
    st.markdown(f"""
    <div style="background: linear-gradient(45deg, #4f46e5, #7c3aed); color: white; padding: 8px; border-radius: 6px; text-align: center; font-weight: 700; font-size: 0.9rem; margin-bottom: 10px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
        🌟 YILDIZ ADAYLARI
    </div>
    """, unsafe_allow_html=True)
    
    # Kesişim Mantığı
    stars_found = False
    
    # Scroll Alanı Başlatıyoruz
    with st.container(height=150):
        
        # Verilerin varlığını kontrol et
        has_accum = st.session_state.accum_data is not None and not st.session_state.accum_data.empty
        has_warm = st.session_state.breakout_left is not None and not st.session_state.breakout_left.empty
        has_break = st.session_state.breakout_right is not None and not st.session_state.breakout_right.empty
        
        if has_accum:
            # Akıllı Para listesindeki sembolleri al
            acc_df = st.session_state.accum_data
            acc_symbols = set(acc_df['Sembol'].values)
            
            # 1. SENARYO: HAREKET (Kıranlar + Akıllı Para)
            if has_break:
                bo_df = st.session_state.breakout_right
                bo_symbols = set(bo_df['Sembol'].values)
                # Kesişim Bul
                move_stars = acc_symbols.intersection(bo_symbols)
                
                for sym in move_stars:
                    stars_found = True
                    # Fiyatı Accumulation listesinden çekelim
                    price = acc_df[acc_df['Sembol'] == sym]['Fiyat'].values[0]
                    
                    # Buton Formatı: 🚀 THYAO (305.50) | HAREKET
                    label = f"🚀 {sym} ({price}) | HAREKET"
                    if st.button(label, key=f"star_mov_{sym}", use_container_width=True):
                        on_scan_result_click(sym)
                        st.rerun()

            # 2. SENARYO: HAZIRLIK (Isınanlar + Akıllı Para)
            if has_warm:
                warm_df = st.session_state.breakout_left
                # Isınanlar listesinde bazen 'Sembol_Raw' bazen 'Sembol' olabilir, kontrol edelim
                col_name = 'Sembol_Raw' if 'Sembol_Raw' in warm_df.columns else 'Sembol'
                warm_symbols = set(warm_df[col_name].values)
                # Kesişim Bul
                prep_stars = acc_symbols.intersection(warm_symbols)
                
                for sym in prep_stars:
                    stars_found = True
                    price = acc_df[acc_df['Sembol'] == sym]['Fiyat'].values[0]
                    
                    # Buton Formatı: ⏳ ASELS (60.20) | HAZIRLIK
                    label = f"⏳ {sym} ({price}) | HAZIRLIK"
                    if st.button(label, key=f"star_prep_{sym}", use_container_width=True):
                        on_scan_result_click(sym)
                        st.rerun()
        
        if not stars_found:
            if not has_accum:
                st.info("Önce 'Sentiment Ajanı' taramasını başlatın.")
            elif not (has_warm or has_break):
                st.info("Sonra 'Breakout Ajanı' taramasını başlatın.")
            else:
                st.warning("Şu an toplanan ORTAK bir hisse yok.")

    st.divider()

    # 3. AI ANALIST (En Altta)
    with st.expander("🤖 AI Analist (Prompt)", expanded=True):
        st.caption("Verileri toplayıp ChatGPT için hazır metin oluşturur.")
        if st.button("📋 Analiz Metnini Hazırla", type="primary"): 
            st.session_state.generate_prompt = True

# --- 🚦 PİYASA TRAFİK IŞIĞI & KONTROL LİSTESİ ---
    # 1. Otomatik Piyasa Analizi
    market_symbol = "XU100.IS" if "BIST" in st.session_state.category else "^GSPC"
    market_df = get_safe_historical_data(market_symbol, period="2y")
    
    is_market_safe = False
    market_txt = "Veri Yok"
    
    if market_df is not None and not market_df.empty:
        closes = market_df['Close']
        if len(closes) > 200:
            curr_val = closes.iloc[-1]
            sma200_val = closes.rolling(200).mean().iloc[-1]
            is_market_safe = curr_val > sma200_val
            diff_pct = ((curr_val / sma200_val) - 1) * 100
            market_txt = f"SMA200'den yüzde kaç yukarıda: %{diff_pct:.1f}"

    # 2. Görselleştirme (Yeşil/Kırmızı Kutu)
    if is_market_safe:
        st.markdown(f"""
        <div style="background:#ecfccb; border:2px solid #65a30d; padding:10px; border-radius:8px; text-align:center; margin-bottom:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="color:#3f6212; font-weight:900; font-size:1.1rem; letter-spacing:1px;">✅ PİYASA GÜVENLİ</div>
            <div style="color:#4d7c0f; font-size:0.75rem; font-weight:600; margin-top:4px;">Trend Yukarı ({market_symbol} > SMA200)</div>
            <div style="color:#365314; font-size:0.7rem; font-style:italic;">{market_txt} - Ava Çıkabilirsin.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:#fef2f2; border:2px solid #dc2626; padding:10px; border-radius:8px; text-align:center; margin-bottom:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="color:#991b1b; font-weight:900; font-size:1.1rem; letter-spacing:1px;">⛔ PİYASA TEHLİKELİ</div>
            <div style="color:#b91c1c; font-size:0.75rem; font-weight:600; margin-top:4px;">Trend Düşük ({market_symbol} < SMA200)</div>
            <div style="color:#7f1d1d; font-size:0.7rem; font-style:italic;">{market_txt} - Nakitte Kal / Short Bak!</div>
        </div>
        """, unsafe_allow_html=True)

    # 3. Manuel Pilot Kontrol Listesi
    with st.expander("👮 PİLOT KONTROL LİSTESİ", expanded=True):
        st.caption("Disiplin yoksa kazanç yoktur. Borsalara bakmadan önce:")
        c1 = st.checkbox("⏰ Zamanlama (16:30 sonrası mı?)")
        c2 = st.checkbox("📰 Haber Akışı (Kritik veri yok?)")
        c3 = st.checkbox("💰 Risk (Stop & Lot hesabın tamam mı?)")
        c4 = st.checkbox("🧠 Psikoloji (Sakin miyim?)")
        
        if c1 and c2 and c3 and c4:
            st.success("🚀 Tarama İzni Verildi! Başarılar.")
            
    st.markdown("<hr style='margin-top:5px; margin-bottom:15px; border-top:1px solid #e2e8f0;'>", unsafe_allow_html=True)
# ==============================================================================
# 6. ANA SAYFA (MAIN UI)
# ==============================================================================
col_cat, col_ass, col_search_in, col_search_btn = st.columns([1.5, 2, 2, 0.7])
try: cat_index = list(ASSET_GROUPS.keys()).index(st.session_state.category)
except ValueError: cat_index = 0
with col_cat: st.selectbox("Kategori", list(ASSET_GROUPS.keys()), index=cat_index, key="selected_category_key", on_change=on_category_change, label_visibility="collapsed")

with col_ass:
    current_opts = ASSET_GROUPS.get(st.session_state.category, ASSET_GROUPS[INITIAL_CATEGORY]).copy()
    active_ticker = st.session_state.ticker
    if active_ticker not in current_opts:
        current_opts.insert(0, active_ticker)
        asset_idx = 0
    else:
        try: asset_idx = current_opts.index(active_ticker)
        except ValueError: asset_idx = 0
    st.selectbox("Varlık Listesi", current_opts, index=asset_idx, key="selected_asset_key", on_change=on_asset_change, label_visibility="collapsed", format_func=lambda x: x.replace(".IS", ""))

with col_search_in: st.text_input("Manuel", placeholder="Kod", key="manual_input_key", label_visibility="collapsed")
with col_search_btn: st.button("Ara", on_click=on_manual_button_click)
st.markdown("<hr style='margin-top:0.5rem; margin-bottom:0.5rem;'>", unsafe_allow_html=True)

if st.session_state.generate_prompt:
    t = st.session_state.ticker
    
    # --- 1. TÜM VERİLERİ TOPLA ---
    info = fetch_stock_info(t)
    ict_data = calculate_ict_deep_analysis(t) or {}
    sent_data = calculate_sentiment_score(t) or {}
    tech_data = get_tech_card_data(t) or {}
    pa_data = calculate_price_action_dna(t) or {}
    levels_data = get_advanced_levels_data(t) or {}
    synth_data = calculate_synthetic_sentiment(t) # Force Index Verisi

    # Radar verisi kontrolü
    radar_val = "Veri Yok"; radar_setup = "Belirsiz"
    if st.session_state.radar2_data is not None:
        r_row = st.session_state.radar2_data[st.session_state.radar2_data['Sembol'] == t]
        if not r_row.empty:
            radar_val = f"{r_row.iloc[0]['Skor']}/7"
            radar_setup = r_row.iloc[0]['Setup']
    
    # --- 2. SENTIMENT DETAYLARINI AYIKLA ---
    def extract_reasons(raw_val):
        clean = re.sub(r'<[^>]+>', '', str(raw_val))
        if "(" in clean and ")" in clean:
            return clean.split('(')[1].split(')')[0]
        return None

    pozitif_sebepler = []
    keys_map = {'str': 'Yapı', 'tr': 'Trend', 'vol': 'Hacim', 'mom': 'Momentum', 'vola': 'Volatilite'}
    for key in keys_map:
        reason = extract_reasons(sent_data.get(key, ''))
        if reason:
            pozitif_sebepler.append(f"{keys_map[key]}: {reason}")
    sentiment_detay_str = " | ".join(pozitif_sebepler) if pozitif_sebepler else "Belirgin pozitif teknik sinyal yok."

    # --- 3. AKILLI PARA AĞIRLIKLI ANALİZ (SON 10 GÜN - WMA) ---
    para_akisi_txt = "Veri Yetersiz"
    if synth_data is not None and len(synth_data) > 15:
        # Son 10 günü al
        window = 10
        # Son 10 veriyi numpy array'e çevir
        recent_mf = synth_data['MF_Smooth'].tail(window).values
        
        # Ağırlık Dizisi: [1, 2, 3, ..., 10] (Bugüne en yüksek puan)
        weights = np.arange(1, window + 1)
        
        # Bugünün Ağırlıklı Ortalaması (WMA)
        wma_now = np.sum(recent_mf * weights) / np.sum(weights)
        
        # Dünün Ağırlıklı Ortalaması (Karşılaştırma için bir adım geri kaydırıyoruz)
        prev_mf_slice = synth_data['MF_Smooth'].iloc[-(window+1):-1].values
        wma_prev = np.sum(prev_mf_slice * weights) / np.sum(weights)
        
        # 1. RENK ANALİZİ (Ana Yön)
        ana_renk = "MAVİ (Pozitif)" if wma_now > 0 else "KIRMIZI (Negatif)"
        
        # 2. MOMENTUM ANALİZİ (Eğim)
        momentum_durumu = ""
        # Pozitif bölgedeysek (Mavi)
        if wma_now > 0:
            if wma_now > wma_prev: momentum_durumu = "GÜÇLENİYOR 🚀 (İştah Artıyor)"
            else: momentum_durumu = "ZAYIFLIYOR ⚠️ (Alıcılar Yoruldu)"
        # Negatif bölgedeysek (Kırmızı)
        else:
            if wma_now < wma_prev: momentum_durumu = "DERİNLEŞİYOR 🔻 (Satış Baskısı Artıyor)" # Daha negatif oluyor
            else: momentum_durumu = "ZAYIFLIYOR ✅ (Satışlar Kuruyor/Dönüş Sinyali)" # Sıfıra yaklaşıyor

        para_akisi_txt = f"{ana_renk} | Momentum: {momentum_durumu} (10 Günlük Ağırlıklı Analiz)"

    # --- 4. DİĞER METİNLERİ HAZIRLA ---
    def clean_text(text): return re.sub(r'<[^>]+>', '', str(text))
    mom_clean = clean_text(sent_data.get('mom', 'Veri Yok'))

    st_txt = "Veri Yok"; fib_res = "Veri Yok"; fib_sup = "Veri Yok"
    if levels_data:
        st_dir_txt = "YÜKSELİŞ (AL)" if levels_data.get('st_dir') == 1 else "DÜŞÜŞ (SAT)"
        st_txt = f"{st_dir_txt} | Seviye: {levels_data.get('st_val', 0):.2f}"
        sup_l, sup_v = levels_data.get('nearest_sup', (None, 0))
        res_l, res_v = levels_data.get('nearest_res', (None, 0))
        fib_sup = f"{sup_v:.2f} (Fib {sup_l})" if sup_l else "Bilinmiyor"
        fib_res = f"{res_v:.2f} (Fib {res_l})" if res_l else "Bilinmiyor"

    pa_div = pa_data.get('div', {}).get('title', 'Yok')
    pa_sfp = pa_data.get('sfp', {}).get('title', 'Bilinmiyor')
    pa_sq = pa_data.get('sq', {}).get('title', 'Bilinmiyor')
    
    fiyat_str = f"{info.get('price', 0):.2f}" if info else "0.00"
    sma50_str = f"{tech_data.get('sma50', 0):.2f}"
    liq_str = f"{ict_data.get('target', 0):.2f}" if ict_data.get('target', 0) > 0 else "Belirsiz / Yok"
    mum_desc = pa_data.get('candle', {}).get('desc', 'Belirgin formasyon yok')

    # --- 5. FİNAL PROMPT ---
    prompt = f"""*** SİSTEM ROLLERİ ***
Sen Dünya çapında tanınan, Price Action ve Smart Money (ICT) konseptlerinde uzmanlaşmış kıdemli bir Swing Trader'sın.
Yatırım tavsiyesi vermeden, sadece aşağıdaki TEKNİK VERİLERE dayanarak stratejik bir analiz yapacaksın.

*** VARLIK KİMLİĞİ ***
- Sembol: {t}
- GÜNCEL FİYAT: {fiyat_str}
- SMA50 (Trend Bazı): {sma50_str}

*** 1. MARKET YAPISI VE TREND ***
- SuperTrend (Ana Yön): {st_txt}
- ICT Market Yapısı: {ict_data.get('structure', 'Bilinmiyor')} ({ict_data.get('bias', 'Nötr')})
- Konum (Discount/Premium): {ict_data.get('zone', 'Bilinmiyor')}

*** 2. GİZLİ PARA AKIŞI (Momentum Index - 10 Günlük) ***
- Durum: {para_akisi_txt}
(ÇOK KRİTİK NOT: Eğer Kırmızı renkte ama "Zayıflıyor/Satışlar Kuruyor" diyorsa, bu potansiyel bir DİP dönüşü sinyalidir. Mavi renkte "Güçleniyor" diyorsa trend sağlamdır.)

*** 3. KRİTİK SEVİYELER (Trade Alanı) ***
- En Yakın Direnç (Fib): {fib_res}
- En Yakın Destek (Fib): {fib_sup}
- Hedef Likidite (Mıknatıs): {liq_str}
- Aktif FVG (Dengesizlik): {ict_data.get('fvg_txt', 'Yok')}

*** 4. PRICE ACTION & GÜÇ (Derin Analiz) ***
- Mum Formasyonu: {mum_desc}
- RSI Uyumsuzluğu: {pa_div} (Buna çok dikkat et!)
- Tuzak (SFP): {pa_sfp}
- Volatilite: {pa_sq}
- Momentum Durumu: {mom_clean}

*** 5. SENTIMENT PUAN DETAYI ***
- Toplam Puan: {sent_data.get('total', 0)}/100
- Pozitif Etkenler: {sentiment_detay_str}

*** GÖREVİN ***
Verileri sentezle ve aşağıdaki başlıkları açıp bir "Sniper" gibi işlem kurgula.
1. ANALİZ: Fiyatın market yapısına göre nerede olduğunu ve Smart Money'nin (Özellikle 10 günlük ağırlıklı para akışına bakarak) ne yapmaya çalıştığını yorumla.
2. KARAR: [Long / Short / İzle]
3. STRATEJİ:
   - Giriş Bölgesi:
   - Stop Loss:
   - Kar Al (TP):
4. UYARI: Eğer RSI uyumsuzluğu veya Trend tersliği varsa büyük harflerle uyar.
"""
    with st.sidebar:
        st.code(prompt, language="text")
        st.success("Prompt Güncellendi: 10 Günlük Ağırlıklı Smart Money Analizi Eklendi! 🧠")
    
    st.session_state.generate_prompt = False

info = fetch_stock_info(st.session_state.ticker)

col_left, col_right = st.columns([4, 1])

# --- SOL SÜTUN ---
with col_left:
    synth_data = calculate_synthetic_sentiment(st.session_state.ticker)
    if synth_data is not None and not synth_data.empty: render_synthetic_sentiment_panel(synth_data)
    render_detail_card_advanced(st.session_state.ticker)

    st.markdown('<div class="info-header" style="margin-top: 15px; margin-bottom: 10px;">🕵️ Sentiment Ajanı <span style="font-size:0.7rem; color:#64748B; font-weight:400; margin-left:5px;">(Akıllı Para Topluyor: 60/100 Puan)</span></div>', unsafe_allow_html=True)
    
    if 'accum_data' not in st.session_state: st.session_state.accum_data = None
    if 'stp_scanned' not in st.session_state: st.session_state.stp_scanned = False
    if 'stp_crosses' not in st.session_state: st.session_state.stp_crosses = []
    if 'stp_trends' not in st.session_state: st.session_state.stp_trends = []
    if 'stp_filtered' not in st.session_state: st.session_state.stp_filtered = []

    with st.expander("Ajan Operasyonlarını Yönet", expanded=True):
        if st.button(f"🕵️ SENTIMENT & MOMENTUM TARAMASI BAŞLAT ({st.session_state.category})", type="primary", use_container_width=True):
            with st.spinner("Ajan piyasayı didik didik ediyor (STP + Akıllı Para Topluyor?)..."):
                current_assets = ASSET_GROUPS.get(st.session_state.category, [])
                crosses, trends, filtered = scan_stp_signals(current_assets)
                st.session_state.stp_crosses = crosses
                st.session_state.stp_trends = trends
                st.session_state.stp_filtered = filtered
                st.session_state.stp_scanned = True
                st.session_state.accum_data = scan_hidden_accumulation(current_assets)

        if st.session_state.stp_scanned or (st.session_state.accum_data is not None):

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.markdown("<div style='text-align:center; color:#1e40af; font-weight:700; font-size:0.9rem; margin-bottom:5px;'>⚡ STP KESİŞİM</div>", unsafe_allow_html=True)
                with st.container(height=200, border=True):
                    if st.session_state.stp_crosses:
                        for item in st.session_state.stp_crosses:
                            if st.button(f"🚀 {item['Sembol']} ({item['Fiyat']:.2f})", key=f"stp_c_{item['Sembol']}", use_container_width=True): 
                                st.session_state.ticker = item['Sembol']
                                st.rerun()
                    else:
                        st.caption("Kesişim yok.")
            
            with c2:
                st.markdown("<div style='text-align:center; color:#b91c1c; font-weight:700; font-size:0.8rem; margin-bottom:5px;'>🎯 MOMENTUM BAŞLANGICI?</div>", unsafe_allow_html=True)
                with st.container(height=200, border=True):
                    if st.session_state.stp_filtered:
                        for item in st.session_state.stp_filtered:
                            if st.button(f"🔥 {item['Sembol']} ({item['Fiyat']:.2f})", key=f"stp_f_{item['Sembol']}", use_container_width=True): 
                                st.session_state.ticker = item['Sembol']
                                st.rerun()
                    else:
                        st.caption("Tam eşleşme yok.")

            with c3:
                st.markdown("<div style='text-align:center; color:#15803d; font-weight:700; font-size:0.8rem; margin-bottom:5px;'>✅ STP TREND</div>", unsafe_allow_html=True)
                with st.container(height=200, border=True):
                    if st.session_state.stp_trends:
                        for item in st.session_state.stp_trends:
                            # HATA DÜZELTME: .get() kullanarak eğer 'Gun' verisi yoksa '?' koy, çökmesin.
                            gun_sayisi = item.get('Gun', '?')
                            
                            if st.button(f"📈 {item['Sembol']} ({gun_sayisi} Gün)", key=f"stp_t_{item['Sembol']}", use_container_width=True): 
                                st.session_state.ticker = item['Sembol']
                                st.rerun()
                    else:
                        st.caption("Trend yok.")

            with c4:
                st.markdown("<div style='text-align:center; color:#7c3aed; font-weight:700; font-size:0.8rem; margin-bottom:5px;'>🤫 AKILLI PARA TOPLUYOR?</div>", unsafe_allow_html=True)
                
                with st.container(height=200, border=True):
                    if st.session_state.accum_data is not None and not st.session_state.accum_data.empty:
                        for index, row in st.session_state.accum_data.iterrows():
                            
                            # İkon Belirleme (Pocket Pivot varsa Yıldırım, yoksa Şapka)
                            icon = "⚡" if row.get('Pocket_Pivot', False) else "🎩"
                            
                            # Buton Metni: "⚡ AAPL (150.20) | RS: Güçlü"
                            # RS bilgisini kısa tutuyoruz
                            rs_raw = str(row.get('RS_Durumu', 'Not Yet'))
                            rs_short = "RS+" if "GÜÇLÜ" in rs_raw else "Not Yet"
                            
                            # Buton Etiketi
                            btn_label = f"{icon} {row['Sembol']} ({row['Fiyat']}) | {rs_short}"
                            
                            # Basit ve Çalışan Buton Yapısı
                            if st.button(btn_label, key=f"btn_acc_{row['Sembol']}_{index}", use_container_width=True):
                                on_scan_result_click(row['Sembol'])
                                st.rerun()
                    else:
                        st.caption("Tespit edilemedi.")

    # --- DÜZELTİLMİŞ BREAKOUT & KIRILIM İSTİHBARATI BÖLÜMÜ ---
    # Breakout Ajanı Başlığı (Düzeltilmiş: Küçük, Gri, İtalik, Yan Yana)
    st.markdown("""
    <div style="margin-top: 15px; margin-bottom: 5px;">
        <div style="font-weight: 700; color: #1e3a8a; font-size: 1.1rem; margin-bottom: 2px;">
            🕵️ Breakout Ajanı <span style="font-size:0.75rem; background:#fffbeb; color:#d97706; padding:2px 6px; border-radius:4px; margin-left:5px; vertical-align: middle;">(Isınanlar: 78/100)</span>
        </div>
        # BUNU YAPIŞTIR:
        <div class="edu-note" style="margin-top:5px;">
        <span style="font-weight:600; color:#d97706; font-style:normal;">ZAMANLAMA USTASI:</span> "Ne Zaman?" sorusunu cevaplar. 
        🔥 <b>ISINANLAR (Sol):</b> %98-99 dirençte, "Pusuya Yat" listesidir. 
        🔨 <b>KIRANLAR (Sağ):</b> Direnç hacimli kırıldı.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Session State Tanımları (Eğer yoksa)
    if 'breakout_left' not in st.session_state: st.session_state.breakout_left = None
    if 'breakout_right' not in st.session_state: st.session_state.breakout_right = None

    with st.expander("Taramayı Başlat / Sonuçları Göster", expanded=True):
        if st.button(f"⚡ {st.session_state.category} İÇİN BREAK-OUT TARAMASI BAŞLAT", type="primary", key="dual_breakout_btn", use_container_width=True):
            with st.spinner("Ajanlar sahaya indi: Hem ısınanlar hem kıranlar taranıyor..."):
                curr_list = ASSET_GROUPS.get(st.session_state.category, [])
                # Paralel tarama simülasyonu (Sırayla çalışır ama hızlıdır)
                st.session_state.breakout_left = agent3_breakout_scan(curr_list) # Mevcut Isınanlar
                st.session_state.breakout_right = scan_confirmed_breakouts(curr_list) # Yeni Kıranlar
                st.rerun()

       # 2 Sütunlu Sade Yapı (YENİ TASARIM)
        c_left, c_right = st.columns(2)
        
        # --- SOL SÜTUN: ISINANLAR (Hazırlık) ---
        with c_left:
            st.markdown("<div style='text-align:center; color:#d97706; font-weight:700; font-size:0.9rem; margin-bottom:5px; background:#fffbeb; padding:5px; border-radius:4px; border:1px solid #fcd34d;'>🔥 ISINANLAR (Hazırlık)</div>", unsafe_allow_html=True)
            
            with st.container(height=150): # Scroll Alanı
                if st.session_state.breakout_left is not None and not st.session_state.breakout_left.empty:
                    df_left = st.session_state.breakout_left.head(20)
                    for i, (index, row) in enumerate(df_left.iterrows()):
                        sym_raw = row.get("Sembol_Raw", row.get("Sembol", "UNK"))
                        
                        # HTML etiketlerini temizle (Sadece oranı al: %98 gibi)
                        prox_clean = str(row['Zirveye Yakınlık']).split('<')[0].strip()
                        
                        # Buton Metni: 🔥 AAPL (150.20) | %98
                        btn_label = f"🔥 {sym_raw} ({row['Fiyat']}) | {prox_clean}"
                        
                        if st.button(btn_label, key=f"L_btn_new_{sym_raw}_{i}", use_container_width=True):
                            on_scan_result_click(sym_raw)
                            st.rerun()
                else:
                    st.info("Isınan hisse bulunamadı.")

        # --- SAĞ SÜTUN: KIRANLAR (Onaylı) ---
        with c_right:
            st.markdown("<div style='text-align:center; color:#16a34a; font-weight:700; font-size:0.9rem; margin-bottom:5px; background:#f0fdf4; padding:5px; border-radius:4px; border:1px solid #86efac;'>🔨 KIRANLAR (Onaylı)</div>", unsafe_allow_html=True)
            
            with st.container(height=150): # Scroll Alanı
                if st.session_state.breakout_right is not None and not st.session_state.breakout_right.empty:
                    df_right = st.session_state.breakout_right.head(20)
                    for i, (index, row) in enumerate(df_right.iterrows()):
                        sym = row['Sembol']
                        
                        # Buton Metni: 🚀 TSLA (200.50) | Hacim: 2.5x
                        btn_label = f"🚀 {sym} ({row['Fiyat']}) | Hacim: {row['Hacim_Kati']}"
                        
                        if st.button(btn_label, key=f"R_btn_new_{sym}_{i}", use_container_width=True):
                            on_scan_result_click(sym)
                            st.rerun()
                else:
                    st.info("Kırılım yapan hisse bulunamadı.")

    # ---------------------------------------------------------
    # 🦁 YENİ: MINERVINI SEPA AJANI (SOL TARAF - TARAYICI)
    # ---------------------------------------------------------
    if 'minervini_data' not in st.session_state: st.session_state.minervini_data = None

    # Minervini Başlığı (Düzeltilmiş: Küçük, Gri, İtalik, Yan Yana)
    st.markdown("""
    <div style="margin-top: 20px; margin-bottom: 5px;">
        <div style="font-weight: 700; color: #1e3a8a; font-size: 1.1rem; margin-bottom: 2px;">
            🦁 Minervini SEPA Ajanı <span style="font-size:0.75rem; background:#dcfce7; color:#16a34a; padding:2px 6px; border-radius:4px; margin-left:5px; vertical-align: middle;">(LİDER: 85/100)</span>
        </div>
        # BUNU YAPIŞTIR:
        <div class="edu-note" style="margin-top:5px;">
            <span style="font-weight:600; color:#16a34a; font-style:normal;">ANA SİLAH (Sniper):</span> 500 hisseden en iyi 20'yi seçer.
            Kriterler: Trend Şablonu • %90 Zirve Yakınlığı • RS Gücü • VCP Sıkışması.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 1. TARAMA BUTONU
    if st.button(f"🦁 SEPA TARAMASI BAŞLAT ({st.session_state.category})", type="primary", use_container_width=True, key="btn_scan_sepa"):
        with st.spinner("Aslan avda... Trend şablonu, VCP ve RS taranıyor..."):
            current_assets = ASSET_GROUPS.get(st.session_state.category, [])
            st.session_state.minervini_data = scan_minervini_batch(current_assets)
            
    # 2. SONUÇ EKRANI (Scroll Bar - 300px)
    if st.session_state.minervini_data is not None:
        count = len(st.session_state.minervini_data)
        if count > 0:
            st.success(f"🎯 Kriterlere uyan {count} hisse bulundu!")
            with st.container(height=300, border=True):
                for i, row in st.session_state.minervini_data.iterrows():
                    sym = row['Sembol']
                    icon = "💎" if "SÜPER" in row['Durum'] else "🔥"
                    label = f"{icon} {sym} ({row['Fiyat']}) | {row['Durum']} | {row['Detay']}"
                    
                    if st.button(label, key=f"sepa_{sym}_{i}", use_container_width=True):
                        on_scan_result_click(sym)
                        st.rerun()
        else:
            st.warning("Bu zorlu kriterlere uyan hisse bulunamadı.")
    # ---------------------------------------------------------
    
    st.markdown(f"<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:20px;'>📡 {st.session_state.ticker} hakkında haberler ve analizler</div>", unsafe_allow_html=True)
    symbol_raw = st.session_state.ticker; base_symbol = (symbol_raw.replace(".IS", "").replace("=F", "").replace("-USD", "")); lower_symbol = base_symbol.lower()
    st.markdown(f"""<div class="news-card" style="display:flex; flex-wrap:wrap; align-items:center; gap:8px; border-left:none;"><a href="https://seekingalpha.com/symbol/{base_symbol}/news" target="_blank" style="text-decoration:none;"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.8rem; font-weight:600;">SeekingAlpha</div></a><a href="https://finance.yahoo.com/quote/{base_symbol}/news" target="_blank" style="text-decoration:none;"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.8rem; font-weight:600;">Yahoo Finance</div></a><a href="https://www.nasdaq.com/market-activity/stocks/{lower_symbol}/news-headlines" target="_blank" style="text-decoration:none;"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.8rem; font-weight:600;">Nasdaq</div></a><a href="https://stockanalysis.com/stocks/{lower_symbol}/" target="_blank" style="text-decoration:none;"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.8rem; font-weight:600;">StockAnalysis</div></a><a href="https://finviz.com/quote.ashx?t={base_symbol}&p=d" target="_blank" style="text-decoration:none;"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.8rem; font-weight:600;">Finviz</div></a><a href="https://unusualwhales.com/stock/{base_symbol}/overview" target="_blank" style="text-decoration:none;"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.7rem; font-weight:600;">UnusualWhales</div></a></div>""", unsafe_allow_html=True)

# --- SAĞ SÜTUN ---
with col_right:
    if not info: info = fetch_stock_info(st.session_state.ticker)
    
    # 1. Fiyat
    if info and info.get('price'):
        display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")
        cls = "delta-pos" if info['change_pct'] >= 0 else "delta-neg"
        st.markdown(f'<div class="stat-box-small" style="margin-bottom:10px;"><p class="stat-label-small">FİYAT: {display_ticker}</p><p class="stat-value-small money-text">{info["price"]:.2f}<span class="stat-delta-small {cls}">{"+" if info["change_pct"]>=0 else ""}{info["change_pct"]:.2f}%</span></p></div>', unsafe_allow_html=True)
    else: st.warning("Fiyat verisi alınamadı.")

    # 2. Price Action Paneli
    render_price_action_panel(st.session_state.ticker)
    
    # 3. Kritik Seviyeler
    render_levels_card(st.session_state.ticker)
    
    # 4. ICT Paneli
    render_ict_deep_panel(st.session_state.ticker)
    
    # 5. Ortak Fırsatlar Başlığı
    st.markdown(f"<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:10px; color:#1e40af; background-color:{current_theme['box_bg']}; padding:5px; border-radius:5px; border:1px solid #1e40af;'>🎯 Ortak Fırsatlar</div>", unsafe_allow_html=True)
    
    # 6. Ortak Fırsatlar Listesi
    with st.container(height=250):
        df1 = st.session_state.scan_data; df2 = st.session_state.radar2_data
        if df1 is not None and df2 is not None and not df1.empty and not df2.empty:
            commons = []; symbols = set(df1["Sembol"]).intersection(set(df2["Sembol"]))
            if symbols:
                for sym in symbols:
                    row1 = df1[df1["Sembol"] == sym].iloc[0]; row2 = df2[df2["Sembol"] == sym].iloc[0]
                    r1_score = float(row1["Skor"]); r2_score = float(row2["Skor"]); combined_score = r1_score + r2_score
                    commons.append({"symbol": sym, "r1_score": r1_score, "r2_score": r2_score, "combined": combined_score, "r1_max": 7, "r2_max": 7})
                sorted_commons = sorted(commons, key=lambda x: x["combined"], reverse=True)
                cols = st.columns(2) 
                for i, item in enumerate(sorted_commons):
                    sym = item["symbol"]
                    score_text_safe = f"{i+1}. {sym} ({int(item['combined'])})"
                    with cols[i % 2]:
                        if st.button(f"{score_text_safe} | R1:{int(item['r1_score'])} R2:{int(item['r2_score'])}", key=f"c_select_{sym}", help="Detaylar için seç", use_container_width=True): 
                            on_scan_result_click(sym); st.rerun()
            else: st.info("Kesişim yok.")
        else: st.caption("İki radar da çalıştırılmalı.")
   
    tab1, tab2 = st.tabs(["🧠 RADAR 1", "🚀 RADAR 2"])
    with tab1:
        if st.button(f"⚡ {st.session_state.category} Tara", type="primary", key="r1_main_scan_btn"):
            with st.spinner("Taranıyor..."): st.session_state.scan_data = analyze_market_intelligence(ASSET_GROUPS.get(st.session_state.category, []))
        if st.session_state.scan_data is not None:
            with st.container(height=250):
                cols = st.columns(2)
                for i, (index, row) in enumerate(st.session_state.scan_data.iterrows()):
                    sym = row["Sembol"]
                    with cols[i % 2]:
                        if st.button(f"🔥 {row['Skor']}/7 | {row['Sembol']}", key=f"r1_b_{i}", use_container_width=True): on_scan_result_click(row['Sembol']); st.rerun()
    with tab2:
        if st.button(f"🚀 RADAR 2 Tara", type="primary", key="r2_main_scan_btn"):
            with st.spinner("Taranıyor..."): st.session_state.radar2_data = radar2_scan(ASSET_GROUPS.get(st.session_state.category, []))
        if st.session_state.radar2_data is not None:
            with st.container(height=250):
                cols = st.columns(2)
                for i, (index, row) in enumerate(st.session_state.radar2_data.iterrows()):
                    sym = row["Sembol"]
                    with cols[i % 2]:
                        if st.button(f"🚀 {row['Skor']}/7 | {row['Sembol']} | {row['Setup']}", key=f"r2_b_{i}", use_container_width=True): on_scan_result_click(row['Sembol']); st.rerun()











































