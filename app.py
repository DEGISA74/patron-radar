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
import time
import threading

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Patronun Terminali v4.5 (ICT Hybrid)",
    layout="wide",
    page_icon="🐂"
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&display=swap');
    
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {current_theme['text']}; }}
    .stApp {{ background-color: {current_theme['bg']}; }}
    
    section.main > div.block-container {{ padding-top: 2rem; padding-bottom: 2rem; }}
    
    .stMetricValue, .money-text {{ font-family: 'JetBrains Mono', monospace !important; }}
    
    .stat-box-small {{
        background: {current_theme['box_bg']}; border: 1px solid {current_theme['border']};
        border-radius: 6px; padding: 4px 8px; text-align: center; margin-bottom: 4px;
        box-shadow: 0 1px 1px rgba(0,0,0,0.03);
    }}
    .stat-label-small {{ font-size: 0.6rem; color: #64748B; text-transform: uppercase; margin: 0; }}
    .stat-value-small {{ font-size: 0.9rem; font-weight: 700; color: {current_theme['text']}; margin: 0; }}
    
    hr {{ margin-top: 0.2rem; margin-bottom: 0.5rem; }}
    .stSelectbox, .stTextInput {{ margin-bottom: -10px; }}
    
    .delta-pos {{ color: #16A34A; }} .delta-neg {{ color: #DC2626; }}
    .news-card {{ background: {current_theme['news_bg']}; border-left: 3px solid {current_theme['border']}; padding: 6px; margin-bottom: 6px; font-size: 0.78rem; }}
    .news-title {{ color: {current_theme['text']}; font-weight: 600; text-decoration: none; display: block; margin-bottom: 2px; font-size: 0.8rem; }}
    .news-title:hover {{ text-decoration: underline; color: #2563EB; }}
    .news-meta {{ font-size: 0.63rem; color: #64748B; }}

    button[data-testid="baseButton-primary"] {{ background-color: #1e40af !important; border-color: #1e40af !important; color: white !important; }}
    
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

    .ict-bar-container {{
        width: 100%; height: 6px; background-color: #e2e8f0; border-radius: 3px; overflow: hidden; margin: 4px 0; display:flex;
    }}
    .ict-bar-fill {{ height: 100%; transition: width 0.5s ease; }}
    
    .hunter-badge-green {{ background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 12px; font-size: 0.65rem; font-weight: 700; }}
    .hunter-badge-red {{ background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 12px; font-size: 0.65rem; font-weight: 700; }}
    .hunter-badge-blue {{ background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 12px; font-size: 0.65rem; font-weight: 700; }}
    
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
    try: c.execute('INSERT INTO watchlist (symbol) VALUES (?)', (symbol,)); conn.commit()
    except sqlite3.IntegrityError: pass
    conn.close()
def remove_watchlist_db(symbol):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
    conn.commit()
    conn.close()
if not os.path.exists(DB_FILE): init_db()

# --- VARLIK LİSTELERİ ---
priority_sp = ["AGNC", "ARCC", "PFE", "JEPI", "MO", "EPD"]
raw_sp500_rest = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "AMD", "INTC", "QCOM", "TXN", "AMAT", "LRCX", "MU", "ADI", "CSCO", "ORCL", "CRM", "ADBE", "IBM", "ACN", "NOW", "PANW", "SNPS", "CDNS", "KLAC", "NXPI", "APH", "MCHP", "ON", "ANET", "IT", "GLW", "HPE", "HPQ", "NTAP", "STX", "WDC", "TEL", "PLTR", "FTNT", "CRWD", "SMCI", "MSI", "TRMB", "TER", "PTC", "TYL", "FFIV", "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "AXP", "V", "MA", "PYPL", "SQ", "SPGI", "MCO", "CB", "MMC", "PGR", "USB", "PNC", "TFC", "COF", "BK", "SCHW", "ICE", "CME", "AON", "AJG", "TRV", "ALL", "AIG", "MET", "PRU", "AFL", "HIG", "FITB", "MTB", "HBAN", "RF", "CFG", "KEY", "SYF", "DFS", "AMP", "PFG", "CINF", "LLY", "UNH", "JNJ", "MRK", "ABBV", "TMO", "DHR", "ABT", "BMY", "AMGN", "ISRG", "SYK", "ELV", "CVS", "CI", "GILD", "REGN", "VRTX", "ZTS", "BSX", "BDX", "HCA", "MCK", "COR", "CAH", "CNC", "HUM", "MOH", "DXCM", "EW", "RMD", "ALGN", "ZBH", "BAX", "STE", "COO", "WAT", "MTD", "IQV", "A", "HOLX", "IDXX", "BIO", "WMT", "HD", "PG", "COST", "KO", "PEP", "MCD", "SBUX", "NKE", "DIS", "TMUS", "CMCSA", "NFLX", "TGT", "LOW", "TJX", "PM", "EL", "CL", "K", "GIS", "MNST", "TSCO", "ROST", "FAST", "DLTR", "DG", "ORLY", "AZO", "ULTA", "BBY", "KHC", "HSY", "MKC", "CLX", "KMB", "SYY", "KR", "ADM", "STZ", "TAP", "CAG", "SJM", "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HES", "KMI", "GE", "CAT", "DE", "HON", "MMM", "ETN", "ITW", "EMR", "PH", "CMI", "PCAR", "BA", "LMT", "RTX", "GD", "NOC", "LHX", "TDG", "TXT", "HII", "UPS", "FDX", "UNP", "CSX", "NSC", "DAL", "UAL", "AAL", "LUV", "FCX", "NEM", "NUE", "DOW", "CTVA", "LIN", "SHW", "PPG", "ECL", "APD", "VMC", "MLM", "ROP", "TT", "CARR", "OTIS", "ROK", "AME", "DOV", "XYL", "WAB", "NEE", "DUK", "SO", "AEP", "SRE", "D", "PEG", "ED", "XEL", "PCG", "WEC", "ES", "AMT", "PLD", "CCI", "EQIX", "PSA", "O", "DLR", "SPG", "VICI", "CBRE", "CSGP", "WELL", "AVB", "EQR", "EXR", "MAA", "HST", "KIM", "REG", "SBAC", "WY", "PHM", "LEN", "DHI", "LVS", "MGM", "T", "VZ", "BKNG", "MAR", "F", "GM", "STT", "ZBRA", "GL", "EWBC", "OHI", "EXPE", "CF", "HAL", "HP", "RCL", "NCLH", "CPRT", "FANG", "PXD", "OKE", "WMB", "TRGP"]
raw_sp500_rest = list(set(raw_sp500_rest) - set(priority_sp))
raw_sp500_rest.sort()
final_sp500_list = priority_sp + raw_sp500_rest

priority_crypto = ["GC=F", "SI=F", "BTC-USD", "ETH-USD"]
other_crypto = ["BNB-USD", "SOL-USD", "XRP-USD", "ADA-USD", "DOGE-USD", "AVAX-USD", "TRX-USD", "LINK-USD", "DOT-USD", "MATIC-USD", "LTC-USD", "BCH-USD", "UNI-USD", "ATOM-USD", "XLM-USD", "ETC-USD", "FIL-USD", "HBAR-USD", "APT-USD", "NEAR-USD", "VET-USD", "QNT-USD", "AAVE-USD", "ALGO-USD"]
other_crypto.sort()
final_crypto_list = priority_crypto + other_crypto

raw_nasdaq = ["AAPL", "MSFT", "NVDA", "AMZN", "AVGO", "META", "TSLA", "GOOGL", "GOOG", "COST", "NFLX", "AMD", "PEP", "LIN", "TMUS", "CSCO", "QCOM", "INTU", "AMAT", "TXN", "HON", "AMGN", "BKNG", "ISRG", "CMCSA", "SBUX", "MDLZ", "GILD", "ADP", "ADI", "REGN", "VRTX", "LRCX", "PANW", "MU", "KLAC", "SNPS", "CDNS", "MELI", "MAR", "ORLY", "CTAS", "NXPI", "CRWD", "CSX", "PCAR", "MNST", "WDAY", "ROP", "AEP", "ROKU", "ZS", "OKTA", "TEAM", "DDOG", "MDB", "SHOP", "EA", "TTD", "DOCU", "INTC", "SGEN", "ILMN", "IDXX", "ODFL", "EXC", "ADSK", "PAYX", "CHTR", "MRVL", "KDP", "XEL", "LULU", "ALGN", "VRSK", "CDW", "DLTR", "SIRI", "JBHT", "WBA", "PDD", "JD", "BIDU", "NTES", "NXST", "MTCH", "UAL", "SPLK", "ANSS", "SWKS", "QRVO", "AVTR", "FTNT", "ENPH", "SEDG", "BIIB", "CSGP"]
raw_nasdaq = sorted(list(set(raw_nasdaq)))

priority_bist = ["AKBNK.IS", "BIMAS.IS", "DOHOL.IS", "FENER.IS", "KCHOL.IS", "SISE.IS", "TCELL.IS", "THYAO.IS", "TTKOM.IS", "VAKBN.IS"]
raw_bist100_rest = ["AEFES.IS", "AGHOL.IS", "AHGAZ.IS", "AKCNS.IS", "AKFGY.IS", "AKFYE.IS", "AKSA.IS", "AKSEN.IS", "ALARK.IS", "ALBRK.IS", "ALFAS.IS", "ANSGR.IS", "ARCLK.IS", "ASELS.IS", "ASTOR.IS", "BERA.IS", "BIOEN.IS", "BOBET.IS", "BRSAN.IS", "BRYAT.IS", "BUCIM.IS", "CANTE.IS", "CCOLA.IS", "CEMTS.IS", "CIMSA.IS", "CWENE.IS", "DOAS.IS", "ECILC.IS", "ECZYT.IS", "EGEEN.IS", "EKGYO.IS", "ENJSA.IS", "ENKAI.IS", "EREGL.IS", "EUREN.IS", "EUPWR.IS", "FROTO.IS", "GARAN.IS", "GENIL.IS", "GESAN.IS", "GLYHO.IS", "GOKNR.IS", "GUBRF.IS", "GWIND.IS", "HALKB.IS", "HEKTS.IS", "IPEKE.IS", "ISCTR.IS", "ISDMR.IS", "ISGYO.IS", "ISMEN.IS", "IZENR.IS", "KCAER.IS", "KLSER.IS", "KONTR.IS", "KONYA.IS", "KORDS.IS", "KOZAA.IS", "KOZAL.IS", "KRDMD.IS", "KZBGY.IS", "MAVI.IS", "MGROS.IS", "MIATK.IS", "ODAS.IS", "OTKAR.IS", "OYAKC.IS", "PENTA.IS", "PETKM.IS", "PGSUS.IS", "PSGYO.IS", "QUAGR.IS", "REEDR.IS", "SAHOL.IS", "SASA.IS", "SDTTR.IS", "SKBNK.IS", "SMRTG.IS", "SOKM.IS", "TABGD.IS", "TAVHL.IS", "TKFEN.IS", "TOASO.IS", "TSKB.IS", "TTRAK.IS", "TUKAS.IS", "TUPRS.IS", "TURSG.IS", "ULUUN.IS", "VESBE.IS", "VESTL.IS", "YEOTK.IS", "YKBNK.IS", "YLALI.IS", "ZOREN.IS"]
raw_bist100_rest = list(set(raw_bist100_rest) - set(priority_bist))
raw_bist100_rest.sort()
final_bist100_list = priority_bist + raw_bist100_rest

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
        # AJAN HEDEFİNİ GÜNCELLE
        hunter_data["target_list"] = ASSET_GROUPS[new_cat]

def on_asset_change():
    new_asset = st.session_state.get("selected_asset_key")
    if new_asset: st.session_state.ticker = new_asset

def on_manual_button_click():
    if st.session_state.manual_input_key:
        st.session_state.ticker = st.session_state.manual_input_key.upper()

def on_scan_result_click(symbol): st.session_state.ticker = symbol

def on_hunter_click(symbol): st.session_state.ticker = symbol

def toggle_watchlist(symbol):
    wl = st.session_state.watchlist
    if symbol in wl:
        remove_watchlist_db(symbol)
        wl.remove(symbol)
    else:
        add_watchlist_db(symbol)
        wl.append(symbol)
    st.session_state.watchlist = wl

# --- SIDEBAR ---
with st.sidebar:
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
    
    with st.expander("🤖 AI Analist (Prompt)", expanded=True):
        st.caption("Verileri toplayıp ChatGPT için hazır metin oluşturur.")
        if st.button("📋 Analiz Metnini Hazırla", type="primary"):
             st.session_state.generate_prompt = True

# --- ANALİZ MOTORLARI ---
@st.cache_data(ttl=3600)
def analyze_market_intelligence(asset_list):
    if not asset_list: return pd.DataFrame()
    try:
        data = yf.download(asset_list, period="6mo", group_by='ticker', threads=True, progress=False)
    except:
        return pd.DataFrame()

    def process_symbol(symbol):
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]: df = data[symbol].copy()
                else: return None
            else:
                if len(asset_list) == 1: df = data.copy()
                else: return None
            
            if df.empty or 'Close' not in df.columns: return None
            df = df.dropna(subset=['Close'])
            if len(df) < 60: return None
            
            close = df['Close']; high = df['High']; low = df['Low']
            volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))
            
            ema5 = close.ewm(span=5, adjust=False).mean()
            ema20 = close.ewm(span=20, adjust=False).mean()
            sma20 = close.rolling(20).mean()
            std20 = close.rolling(20).std()
            bb_width = ((sma20 + 2*std20) - (sma20 - 2*std20)) / (sma20 + 0.0001)
            hist = (close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()) - (close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()).ewm(span=9, adjust=False).mean()
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + (gain / loss)))
            williams_r = (high.rolling(14).max() - close) / (high.rolling(14).max() - low.rolling(14).min()) * -100
            daily_range = high - low
            
            score = 0; reasons = []
            curr_c = float(close.iloc[-1]); curr_vol = float(volume.iloc[-1])
            avg_vol = float(volume.rolling(5).mean().iloc[-1]) if len(volume) > 5 else 1.0
            
            if bb_width.iloc[-1] <= bb_width.tail(60).min() * 1.1: score += 1; reasons.append("🚀 Squeeze")
            if daily_range.iloc[-1] == daily_range.tail(4).min() and daily_range.iloc[-1] > 0: score += 1; reasons.append("🔇 NR4")
            if ((ema5.iloc[-1] > ema20.iloc[-1]) and (ema5.iloc[-2] <= ema20.iloc[-2])) or ((ema5.iloc[-2] > ema20.iloc[-2]) and (ema5.iloc[-3] <= ema20.iloc[-3])): score += 1; reasons.append("⚡ Trend")
            if hist.iloc[-1] > hist.iloc[-2]: score += 1; reasons.append("🟢 MACD")
            if williams_r.iloc[-1] > -50: score += 1; reasons.append("🔫 W%R")
            if curr_vol > avg_vol * 1.2: score += 1; reasons.append("🔊 Hacim")
            if curr_c >= high.tail(20).max() * 0.98: score += 1; reasons.append("🔨 Breakout")
            rsi_c = rsi.iloc[-1]
            if 30 < rsi_c < 65 and rsi_c > rsi.iloc[-2]: score += 1; reasons.append("⚓ RSI Güçlü")
            
            if score > 0:
                return { "Sembol": symbol, "Fiyat": f"{curr_c:.2f}", "Skor": score, "Nedenler": " | ".join(reasons) }
            return None
        except: return None

    signals = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(process_symbol, asset_list))
    signals = [r for r in results if r is not None]
    return pd.DataFrame(signals).sort_values(by="Skor", ascending=False) if signals else pd.DataFrame()

@st.cache_data(ttl=3600)
def radar2_scan(asset_list, min_price=5, max_price=5000, min_avg_vol_m=0.5):
    if not asset_list: return pd.DataFrame()
    try: data = yf.download(asset_list, period="1y", group_by="ticker", threads=True, progress=False)
    except: return pd.DataFrame()
    try: idx = yf.download("^GSPC", period="1y", progress=False)["Close"]
    except: idx = None

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
            if curr_c < min_price or curr_c > max_price: return None
            avg_vol_20 = float(volume.rolling(20).mean().iloc[-1])
            if avg_vol_20 < min_avg_vol_m * 1e6: return None
            
            sma20 = close.rolling(20).mean(); sma50 = close.rolling(50).mean()
            sma100 = close.rolling(100).mean(); sma200 = close.rolling(200).mean()
            
            trend = "Yatay"
            if not np.isnan(sma200.iloc[-1]):
                if curr_c > sma50.iloc[-1] > sma100.iloc[-1] > sma200.iloc[-1] and sma200.iloc[-1] > sma200.iloc[-20]: trend = "Boğa"
                elif curr_c < sma200.iloc[-1] and sma200.iloc[-1] < sma200.iloc[-20]: trend = "Ayı"
            
            delta = close.diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean(); rsi = 100 - (100 / (1 + (gain / loss))); rsi_c = float(rsi.iloc[-1])
            hist = (close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()) - (close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()).ewm(span=9, adjust=False).mean()
            
            recent_high_60 = float(high.rolling(60).max().iloc[-1])
            breakout_ratio = curr_c / recent_high_60 if recent_high_60 > 0 else 0
            
            rs_score = 0.0
            if idx is not None and len(close) > 60 and len(idx) > 60:
                common_index = close.index.intersection(idx.index)
                if len(common_index) > 60:
                    cs = close.reindex(common_index); isx = idx.reindex(common_index)
                    rs_score = float((cs.iloc[-1]/cs.iloc[-60]-1) - (isx.iloc[-1]/isx.iloc[-60]-1))
            
            setup = "-"; tags = []; score = 0
            avg_vol_20 = max(avg_vol_20, 1)
            vol_spike = volume.iloc[-1] > avg_vol_20 * 1.3
            
            if trend == "Boğa" and breakout_ratio >= 0.97: setup = "Breakout"; score += 2; tags.append("Zirve")
            if vol_spike: score += 1; tags.append("Hacim+")
            if trend == "Boğa" and setup == "-":
                if sma20.iloc[-1] <= curr_c <= sma50.iloc[-1] * 1.02 and 40 <= rsi_c <= 55: setup = "Pullback"; score += 2; tags.append("Düzeltme")
                if volume.iloc[-1] < avg_vol_20 * 0.9: score += 1; tags.append("Sığ Satış")
            if setup == "-":
                if rsi.iloc[-2] < 30 <= rsi_c and hist.iloc[-1] > hist.iloc[-2]: setup = "Dip Dönüşü"; score += 2; tags.append("Dip Dönüşü")
            
            if rs_score > 0: score += 1; tags.append("RS+")
            if trend == "Boğa": score += 1
            elif trend == "Ayı": score -= 1
            
            if score > 0:
                return { "Sembol": symbol, "Fiyat": round(curr_c, 2), "Trend": trend, "Setup": setup, "Skor": score, "RS": round(rs_score * 100, 1), "Etiketler": " | ".join(tags) }
            return None
        except: return None

    results = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(process_radar2, asset_list))
    results = [r for r in results if r is not None]
    return pd.DataFrame(results).sort_values(by=["Skor", "RS"], ascending=False).head(50) if results else pd.DataFrame()

@st.cache_data(ttl=600)
def calculate_sentiment_score(ticker):
    try:
        df = yf.download(ticker, period="6mo", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']; high = df['High']; low = df['Low']; volume = df['Volume']
        
        score_mom = 0; reasons_mom = []
        rsi = 100 - (100 / (1 + (close.diff().clip(lower=0).rolling(14).mean() / close.diff().clip(upper=0).abs().rolling(14).mean())))
        if rsi.iloc[-1] > 50 and rsi.iloc[-1] > rsi.iloc[-2]: score_mom += 10; reasons_mom.append("RSI ↑")
        macd = close.ewm(span=12).mean() - close.ewm(span=26).mean()
        hist = macd - macd.ewm(span=9).mean()
        if hist.iloc[-1] > 0 and hist.iloc[-1] > hist.iloc[-2]: score_mom += 10; reasons_mom.append("MACD ↑")
        if rsi.iloc[-1] < 30: reasons_mom.append("OS")
        elif rsi.iloc[-1] > 70: reasons_mom.append("OB")
        else: score_mom += 10; reasons_mom.append("Stoch Stabil")
        
        score_vol = 0; reasons_vol = []
        if volume.iloc[-1] > volume.rolling(20).mean().iloc[-1]: score_vol += 15; reasons_vol.append("Vol ↑")
        else: reasons_vol.append("Vol ↓")
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        if obv.iloc[-1] > obv.rolling(5).mean().iloc[-1]: score_vol += 10; reasons_vol.append("OBV ↑")
        
        score_tr = 0; reasons_tr = []
        sma50 = close.rolling(50).mean(); sma200 = close.rolling(200).mean()
        if sma50.iloc[-1] > sma200.iloc[-1]: score_tr += 10; reasons_tr.append("GoldCross")
        if close.iloc[-1] > sma50.iloc[-1]: score_tr += 10; reasons_tr.append("P > SMA50")
        
        score_vola = 0; reasons_vola = []
        std = close.rolling(20).std(); upper = close.rolling(20).mean() + (2 * std)
        if close.iloc[-1] > upper.iloc[-1]: score_vola += 10; reasons_vola.append("BB Break")
        atr = (high-low).rolling(14).mean()
        if atr.iloc[-1] < atr.iloc[-5]: score_vola += 5; reasons_vola.append("Vola ↓")
        
        score_str = 0; reasons_str = []
        if close.iloc[-1] > high.rolling(20).max().shift(1).iloc[-1]: score_str += 10; reasons_str.append("Yeni Tepe (BOS)")
        
        total = score_mom + score_vol + score_tr + score_vola + score_str
        bars = int(total / 5)
        bar_str = "[" + "|" * bars + "." * (20 - bars) + "]"
        
        def fmt(lst): return f"<span style='font-size:0.65rem; color:#64748B;'>({' + '.join(lst)})</span>" if lst else ""
        return {
            "total": total, "bar": bar_str, "mom": f"{score_mom}/30 {fmt(reasons_mom)}",
            "vol": f"{score_vol}/25 {fmt(reasons_vol)}", "tr": f"{score_tr}/20 {fmt(reasons_tr)}",
            "vola": f"{score_vola}/15 {fmt(reasons_vola)}", "str": f"{score_str}/10 {fmt(reasons_str)}",
            "raw_rsi": rsi.iloc[-1], "raw_macd": hist.iloc[-1], "raw_obv": obv.iloc[-1], "raw_atr": atr.iloc[-1]
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

# --- ICT GELISTIRILMIS (KARAR MANTIĞI REVİZE EDİLDİ) ---
@st.cache_data(ttl=600)
def calculate_ict_concepts(ticker):
    try:
        df = yf.download(ticker, period="1y", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        close = df['Close']; high = df['High']; low = df['Low']
        if len(df) < 60: return {"summary": "Veri Yetersiz"}
        curr_price = float(close.iloc[-1])
        
        # --- SMA 50 HESAPLAMA (YENİ: TREND FİLTRESİ İÇİN) ---
        sma50 = close.rolling(50).mean().iloc[-1] if len(close) > 50 else 0

        # --- SWING NOKTALARI ---
        sw_highs = []; sw_lows = []
        for i in range(2, len(df)-2):
            if (high.iloc[i] > high.iloc[i-1] and high.iloc[i] > high.iloc[i-2] and high.iloc[i] > high.iloc[i+1] and high.iloc[i] > high.iloc[i+2]):
                sw_highs.append((df.index[i], float(high.iloc[i]), i))
            if (low.iloc[i] < low.iloc[i-1] and low.iloc[i] < low.iloc[i-2] and low.iloc[i] < low.iloc[i+1] and low.iloc[i] < low.iloc[i+2]):
                sw_lows.append((df.index[i], float(low.iloc[i]), i))

        if not sw_highs or not sw_lows: return {"summary": "Swing Bulunamadı"}
        last_sh = sw_highs[-1][1]; last_sl = sw_lows[-1][1]
        last_sh_idx = sw_highs[-1][2]; last_sl_idx = sw_lows[-1][2]
        r_high = last_sh; r_low = last_sl
        
        # --- YAPISAL GÖRÜNÜM (UI İÇİN) ---
        structure = "YATAY"; bias_color = "gray"
        if curr_price > last_sh: structure = "BOS (Bullish - Yükseliş)"; bias_color = "green"
        elif curr_price < last_sl: structure = "BOS (Bearish - Düşüş)"; bias_color = "red"
        else:
            if last_sh_idx > last_sl_idx: structure = "Internal Range (Düşüş/Düzeltme)"; bias_color = "blue"
            else: structure = "Internal Range (Yükseliş)"; bias_color = "blue"

        # --- PREMIUM / DISCOUNT ---
        range_size = max(r_high - r_low, 1)
        range_pos_pct = ((curr_price - r_low) / range_size) * 100
        pos_label = "Equilibrium"; is_discount = False; is_ote = False
        
        if range_pos_pct > 50:
            pos_label = "Premium (OTE Bölgesi)" if 62 < range_pos_pct < 79 else "Premium (Pahalı)"
            is_ote = (62 < range_pos_pct < 79); is_discount = False
        else:
            pos_label = "Discount (OTE Bölgesi)" if 21 < range_pos_pct < 38 else "Discount (Ucuz)"
            is_ote = (21 < range_pos_pct < 38); is_discount = True

        # --- FVG TARAMASI ---
        active_fvg = "Yok / Dengeli"; fvg_color = "gray"; bullish_fvgs = []; bearish_fvgs = []
        for i in range(max(0, len(df) - 50), len(df)-2):
            if low.iloc[i] > high.iloc[i-2]: # Bullish FVG
                gap_top = low.iloc[i]; gap_bot = high.iloc[i-2]
                is_mitigated = False
                for k in range(i+1, len(df)):
                    if low.iloc[k] <= gap_top: is_mitigated = True; break
                if not is_mitigated: bullish_fvgs.append({'top': gap_top, 'bot': gap_bot, 'idx': i})

            if high.iloc[i] < low.iloc[i-2]: # Bearish FVG
                gap_top = low.iloc[i-2]; gap_bot = high.iloc[i]
                is_mitigated = False
                for k in range(i+1, len(df)):
                    if high.iloc[k] >= gap_bot: is_mitigated = True; break
                if not is_mitigated: bearish_fvgs.append({'top': gap_top, 'bot': gap_bot, 'idx': i})

        # Bölgeye uygun FVG seçimi
        selected_bull_fvg = bullish_fvgs[-1] if bullish_fvgs else None
        selected_bear_fvg = bearish_fvgs[-1] if bearish_fvgs else None

        if is_discount and selected_bull_fvg:
            active_fvg = f"BISI (Destek): {selected_bull_fvg['bot']:.2f} - {selected_bull_fvg['top']:.2f}"
            fvg_color = "green"
        elif not is_discount and selected_bear_fvg:
            active_fvg = f"SIBI (Direnç): {selected_bear_fvg['bot']:.2f} - {selected_bear_fvg['top']:.2f}"
            fvg_color = "red"
        else:
            if selected_bull_fvg: active_fvg = f"Açık FVG (Destek): {selected_bull_fvg['bot']:.2f}"; fvg_color = "green"
            elif selected_bear_fvg: active_fvg = f"Açık FVG (Direnç): {selected_bear_fvg['bot']:.2f}"; fvg_color = "red"

        # --- LİKİDİTE ---
        next_bsl = min([h[1] for h in sw_highs if h[1] > curr_price], default=None)
        next_ssl = max([l[1] for l in sw_lows if l[1] < curr_price], default=None)
        liq_target = f"BSL: {next_bsl:.2f}" if next_bsl and (not next_ssl or abs(next_bsl-curr_price) < abs(curr_price-next_ssl)) else f"SSL: {next_ssl:.2f}" if next_ssl else "Belirsiz"

        # --- YENİ GOLDEN SETUP MANTIĞI (PARADOKSU ÇÖZEN KISIM) ---
        golden_txt = "İzlemede (Setup Yok)"; is_golden = False
        
        # 1. LONG SETUP: Trend Yukarı + Fiyat Ucuz + Bullish FVG Var + Fiyat FVG'ye Değdi/İçinde
        if curr_price > sma50 and is_discount and fvg_color == "green" and selected_bull_fvg:
            # Tetikleyici Kontrol: Fiyat FVG'nin tepesinin altında mı? (Temas var mı?)
            # low[-1] <= top veya close <= top
            if low.iloc[-1] <= selected_bull_fvg['top']: 
                golden_txt = "🔥 LONG FIRSATI (SMA50 Üstü + Ucuz + FVG Teması)"
                is_golden = True
        
        # 2. SHORT SETUP: Trend Aşağı + Fiyat Pahalı + Bearish FVG Var + Fiyat FVG'ye Değdi/İçinde
        elif curr_price < sma50 and not is_discount and fvg_color == "red" and selected_bear_fvg:
            # Tetikleyici Kontrol: Fiyat FVG'nin dibinin üstünde mi?
            if high.iloc[-1] >= selected_bear_fvg['bot']:
                golden_txt = "❄️ SHORT FIRSATI (SMA50 Altı + Pahalı + FVG Teması)"
                is_golden = True
                
        elif is_ote: golden_txt = "⚖️ OTE Bölgesi (Karar Anı)"

        return {
            "structure": structure, "bias_color": bias_color, "range_pos_pct": range_pos_pct,
            "pos_label": pos_label, "fvg": active_fvg, "fvg_color": fvg_color,
            "liquidity": liq_target, "golden_text": golden_txt, "is_golden": is_golden,
            "ote_level": is_ote, "range_high": r_high, "range_low": r_low, "summary": "OK"
        }
    except Exception as e: return {"summary": "Hata", "err": str(e)}

@st.cache_data(ttl=600)
def get_tech_card_data(ticker):
    try:
        df = yf.download(ticker, period="2y", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']; high = df['High']; low = df['Low']
        sma50 = close.rolling(50).mean().iloc[-1]; sma100 = close.rolling(100).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1]; ema144 = close.ewm(span=144, adjust=False).mean().iloc[-1]
        atr = (high-low).rolling(14).mean().iloc[-1]
        return { "sma50": sma50, "sma100": sma100, "sma200": sma200, "ema144": ema144, "stop_level": close.iloc[-1] - (2 * atr), "risk_pct": (2 * atr) / close.iloc[-1] * 100, "atr": atr }
    except: return None

# ==============================================================================
# 🕵️ ARKA PLAN AJANI (BACKGROUND HUNTER AGENT)
# ==============================================================================
@st.cache_resource
def get_shared_hunter_data():
    return {"results": [], "last_run": None, "is_running": False, "target_list": []}

hunter_data = get_shared_hunter_data()

def run_background_scan():
    while True:
        # Session state thread'de yoktur, global cache'den listeyi al
        current_targets = hunter_data.get("target_list", [])
        if not current_targets: current_targets = priority_bist # Default
        
        # IP Ban Koruması: İlk 20'yi tara
        scan_list = current_targets[:20] if len(current_targets) > 20 else current_targets
        
        temp_results = []
        for ticker in scan_list:
            try:
                # Revize edilmiş mantığı kullan
                analysis = calculate_ict_concepts(ticker)
                if analysis and analysis.get("is_golden", False):
                    score = 80
                    if analysis['ote_level']: score += 10
                    if "BOS" in analysis['structure']: score += 10
                    
                    temp_results.append({
                        "symbol": ticker,
                        "time": datetime.now().strftime("%H:%M"),
                        "type": analysis['golden_text'],
                        "score": score,
                        "detail": f"{analysis['structure']} | {analysis['pos_label']}"
                    })
            except: continue
            time.sleep(1) # Nezaket
        
        hunter_data["results"] = temp_results
        hunter_data["last_run"] = datetime.now().strftime("%H:%M")
        time.sleep(60) # 1 Dakika Bekle

def start_hunter_agent():
    if not hunter_data["is_running"]:
        t = threading.Thread(target=run_background_scan, daemon=True)
        t.start()
        hunter_data["is_running"] = True

start_hunter_agent()

# --- RENDER FONKSİYONLARI ---
def render_sentiment_card(sent):
    if not sent: return
    display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")
    color = "🔥" if sent['total'] >= 70 else "❄️" if sent['total'] <= 30 else "⚖️"
    st.markdown(f"""
    <div class="info-card">
        <div class="info-header">🎭 Piyasa Duygusu (Sentiment): {display_ticker}</div>
        <div class="info-row" style="border-bottom: 1px dashed #e5e7eb; padding-bottom:4px; margin-bottom:6px;">
            <div style="font-weight:700; color:#1e40af; font-size:0.8rem;">SKOR: {sent['total']}/100 {color}</div>
        </div>
        <div style="font-family:'Courier New'; font-size:0.7rem; color:#1e3a8a; margin-bottom:5px;">{sent['bar']}</div>
        <div class="info-row"><div class="label-long">1. Momentum:</div><div class="info-val">{sent['mom']}</div></div>
        <div class="info-row"><div class="label-long">2. Hacim:</div><div class="info-val">{sent['vol']}</div></div>
        <div class="info-row"><div class="label-long">3. Trend:</div><div class="info-val">{sent['tr']}</div></div>
        <div class="info-row"><div class="label-long">4. Volatilite:</div><div class="info-val">{sent['vola']}</div></div>
        <div class="info-row"><div class="label-long">5. Yapı:</div><div class="info-val">{sent['str']}</div></div>
    </div>
    """, unsafe_allow_html=True)

def render_deep_xray_card(xray):
    if not xray: return
    st.markdown(f"""
    <div class="info-card">
        <div class="info-header">🔍 Derin Teknik Röntgen</div>
        <div class="info-row"><div class="label-long">Momentum:</div><div class="info-val">{xray['mom_rsi']} | {xray['mom_macd']}</div></div>
        <div class="info-row"><div class="label-long">Hacim Akışı:</div><div class="info-val">{xray['vol_obv']}</div></div>
        <div class="info-row"><div class="label-long">Trend Sağlığı:</div><div class="info-val">{xray['tr_ema']} | {xray['tr_adx']}</div></div>
        <div class="info-row"><div class="label-long">Volatilite:</div><div class="info-val">{xray['vola_bb']}</div></div>
        <div class="info-row"><div class="label-long">Piyasa Yapısı:</div><div class="info-val">{xray['str_bos']}</div></div>
    </div>
    """, unsafe_allow_html=True)

def render_radar_params_card():
    st.markdown(f"""
    <div class="info-card">
        <div class="info-header">🎛️ Radar Parametreleri</div>
        <div style="margin-bottom:6px;">
            <div class="label-short" style="width:100%; margin-bottom:2px; color:#1e40af;">RADAR 1 (Sinyal):</div>
            <div style="display:flex; flex-wrap:wrap; gap:3px;">
                <span style="background:#e0f2fe; color:#0369a1; padding:2px 6px; border-radius:4px; font-size:0.7rem;">RSI</span>
                <span style="background:#e0f2fe; color:#0369a1; padding:2px 6px; border-radius:4px; font-size:0.7rem;">MACD</span>
                <span style="background:#e0f2fe; color:#0369a1; padding:2px 6px; border-radius:4px; font-size:0.7rem;">W%R</span>
                <span style="background:#e0f2fe; color:#0369a1; padding:2px 6px; border-radius:4px; font-size:0.7rem;">MFI</span>
                <span style="background:#e0f2fe; color:#0369a1; padding:2px 6px; border-radius:4px; font-size:0.7rem;">CCI</span>
                <span style="background:#e0f2fe; color:#0369a1; padding:2px 6px; border-radius:4px; font-size:0.7rem;">Stoch</span>
                <span style="background:#e0f2fe; color:#0369a1; padding:2px 6px; border-radius:4px; font-size:0.7rem;">ADX</span>
                <span style="background:#e0f2fe; color:#0369a1; padding:2px 6px; border-radius:4px; font-size:0.7rem;">Mom</span>
            </div>
        </div>
        <div>
            <div class="label-short" style="width:100%; margin-bottom:2px; color:#1e40af;">RADAR 2 (Setup):</div>
            <div style="display:flex; flex-wrap:wrap; gap:3px;">
                <span style="background:#f0fdf4; color:#15803d; padding:2px 6px; border-radius:4px; font-size:0.7rem;">SMA Sıralı</span>
                <span style="background:#f0fdf4; color:#15803d; padding:2px 6px; border-radius:4px; font-size:0.7rem;">RS(S&P500)</span>
                <span style="background:#f0fdf4; color:#15803d; padding:2px 6px; border-radius:4px; font-size:0.7rem;">Hacim+</span>
                <span style="background:#f0fdf4; color:#15803d; padding:2px 6px; border-radius:4px; font-size:0.7rem;">60G Zirve</span>
                <span style="background:#f0fdf4; color:#15803d; padding:2px 6px; border-radius:4px; font-size:0.7rem;">RSI Bölgesi</span>
                <span style="background:#f0fdf4; color:#15803d; padding:2px 6px; border-radius:4px; font-size:0.7rem;">MACD Hist</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_ict_panel(analysis):
    if not analysis or "summary" in analysis and analysis["summary"] == "Hata":
        st.error("ICT Analizi yapılamadı (Veri yetersiz)"); return
    display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")
    s_color = "#166534" if analysis['bias_color'] == "green" else "#991b1b" if analysis['bias_color'] == "red" else "#854d0e"
    pos_pct = analysis['range_pos_pct']; bar_width = min(max(pos_pct, 5), 95)
    
    golden_badge = ""
    if analysis['is_golden']: golden_badge = f"<div style='margin-top:6px; background:#f0fdf4; border:1px solid #bbf7d0; color:#15803d; padding:6px; border-radius:6px; font-weight:700; text-align:center; font-size:0.75rem;'>✨ {analysis['golden_text']}</div>"
    elif analysis['ote_level']: golden_badge = f"<div style='margin-top:6px; background:#eff6ff; border:1px solid #bfdbfe; color:#1e40af; padding:6px; border-radius:6px; text-align:center; font-size:0.75rem;'>🎯 {analysis['golden_text']}</div>"
    else: golden_badge = f"<div style='margin-top:6px; background:#f8fafc; border:1px solid #e2e8f0; color:#94a3b8; padding:6px; border-radius:6px; text-align:center; font-size:0.75rem;'>{analysis['golden_text']}</div>"

    st.markdown(f"""
<div class="info-card">
<div class="info-header">🧠 ICT Smart Money Concepts: {display_ticker}</div>
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
<span style="font-size:0.65rem; color:#64748B; font-weight:600;">MARKET YAPISI</span>
<span style="font-size:0.7rem; font-weight:700; color:{s_color};">{analysis['structure']}</span>
</div>
<div style="margin: 8px 0;">
<div style="display:flex; justify-content:space-between; font-size:0.6rem; color:#64748B; margin-bottom:2px;"><span>Discount</span><span>EQ</span><span>Premium</span></div>
<div class="ict-bar-container"><div class="ict-bar-fill" style="width:{bar_width}%; background: linear-gradient(90deg, #22c55e 0%, #cbd5e1 50%, #ef4444 100%);"></div></div>
<div style="text-align:center; font-size:0.7rem; font-weight:600; color:#0f172a; margin-top:2px;">{analysis['pos_label']} <span style="color:#64748B; font-size:0.6rem;">(%{pos_pct:.1f})</span></div>
</div>
<div style="margin-top:8px;">
<div class="info-row"><div class="label-long">FVG Durumu:</div><div class="info-val" style="color:{'#166534' if analysis['fvg_color']=='green' else '#991b1b' if analysis['fvg_color']=='red' else '#64748B'}; font-weight:600;">{analysis['fvg']}</div></div>
<div class="info-row"><div class="label-long">🧲 Fiyatı Çeken Seviye:</div><div class="info-val">{analysis['liquidity']}</div></div>
</div>
{golden_badge}
</div>
""", unsafe_allow_html=True)

def render_detail_card(ticker):
    display_ticker = ticker.replace(".IS", "").replace("=F", "")
    r1_t = "Veri yok"; r2_t = "Veri yok"
    if st.session_state.scan_data is not None:
        row = st.session_state.scan_data[st.session_state.scan_data["Sembol"] == ticker]
        if not row.empty: r1_t = f"<b>Skor {row.iloc[0]['Skor']}/8</b>"
    if st.session_state.radar2_data is not None:
        row = st.session_state.radar2_data[st.session_state.radar2_data["Sembol"] == ticker]
        if not row.empty: r2_t = f"<b>Skor {row.iloc[0]['Skor']}/8</b>"
    dt = get_tech_card_data(ticker)
    ma_t = "-"
    if dt: ma_t = f"SMA50: {dt['sma50']:.1f} | EMA144: {dt['ema144']:.1f}"
    st.markdown(f"""
    <div class="info-card">
        <div class="info-header">📋 Teknik Kart: {display_ticker}</div>
        <div class="info-row"><div class="label-short">Radar 1:</div><div class="info-val">{r1_t}</div></div>
        <div class="info-row"><div class="label-short">Radar 2:</div><div class="info-val">{r2_t}</div></div>
        <div class="info-row"><div class="label-short">Ortalama:</div><div class="info-val">{ma_t}</div></div>
    </div>
    """, unsafe_allow_html=True)

def render_tradingview_widget(ticker, height=650):
    tv_symbol = ticker
    mapping = {"GC=F": "TVC:GOLD", "SI=F": "TVC:SILVER", "BTC-USD": "BINANCE:BTCUSDT", "ETH-USD": "BINANCE:ETHUSDT", "SOL-USD": "BINANCE:SOLUSDT", "XRP-USD": "BINANCE:XRPUSDT", "AVAX-USD": "BINANCE:AVAXUSDT", "DOGE-USD": "BINANCE:DOGEUSDT"}
    if ticker in mapping: tv_symbol = mapping[ticker]
    else:
        if ".IS" in ticker: tv_symbol = ticker.replace('.IS', '').strip()
        elif "=X" in ticker: tv_symbol = f"FX_IDC:{ticker.replace('=X', '')}"
        elif "-USD" in ticker: tv_symbol = f"COINBASE:{ticker.replace('-USD', 'USD')}"
    
    html = f"""<div class="tradingview-widget-container"><div id="tradingview_chart"></div><script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script><script type="text/javascript">new TradingView.widget({{"width": "100%", "height": {height}, "symbol": "{tv_symbol}", "interval": "D", "timezone": "Etc/UTC", "theme": "light", "style": "1", "locale": "tr", "toolbar_bg": "#f1f3f6", "enable_publishing": false, "allow_symbol_change": true, "container_id": "tradingview_chart"}});</script></div>"""
    components.html(html, height=height)

@st.cache_data(ttl=300)
def fetch_stock_info(ticker):
    try:
        info = yf.Ticker(ticker).info
        return {
            'price': info.get('currentPrice') or info.get('regularMarketPrice'),
            'change_pct': ((info.get('currentPrice') or info.get('regularMarketPrice')) - info.get('previousClose')) / info.get('previousClose') * 100 if info.get('previousClose') else 0,
            'volume': info.get('volume', 0),
            'sector': info.get('sector', '-'),
            'target': info.get('targetMeanPrice', '-')
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

# --- ARAYÜZ ---
BULL_ICON_B64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAOAAAADhCAMAAADmr0l2AAAAb1BMVEX///8AAAD8/PzNzc3y8vL39/f09PTw8PDs7Ozp6eny8vLz8/Pr6+vm5ubt7e3j4+Ph4eHf39/c3NzV1dXS0tLKyso/Pz9ERERNTU1iYmJSUlJxcXF9fX1lZWV6enp2dnZsbGxra2uDg4N0dHR/g07fAAAE70lEQVR4nO2d27qrIAyF131wRPT+z3p2tX28dE5sC4i9x3+tC0L4SAgJ3Y2Hw+FwOBwOh8PhcDgcDofD4XA4HA6Hw+H8B/DDT05v9eU/AAAAAElFTkSuQmCC"

st.markdown(f"""
<div class="header-container" style="display:flex; align-items:center;">
    <img src="{BULL_ICON_B64}" class="header-logo">
    <div>
        <div style="font-size:1.5rem; font-weight:700; color:#1e3a8a;">Patronun Terminali v4.5</div>
        <div style="font-size:0.8rem; color:#64748B;">Market Maker Edition (Hybrid + Hunter Agent 🟢)</div>
    </div>
</div>
<hr style="border:0; border-top: 1px solid #e5e7eb; margin-top:5px; margin-bottom:10px;">
""", unsafe_allow_html=True)

# FILTRELER
col_cat, col_ass, col_search_in, col_search_btn = st.columns([1.5, 2, 2, 0.7])
try: cat_index = list(ASSET_GROUPS.keys()).index(st.session_state.category)
except ValueError: cat_index = 0

with col_cat:
    st.selectbox("Kategori", list(ASSET_GROUPS.keys()), index=cat_index, key="selected_category_key", on_change=on_category_change, label_visibility="collapsed")
    hunter_data["target_list"] = ASSET_GROUPS[st.session_state.category]

with col_ass:
    opts = ASSET_GROUPS.get(st.session_state.category, ASSET_GROUPS[INITIAL_CATEGORY])
    try: asset_idx = opts.index(st.session_state.ticker)
    except ValueError: asset_idx = 0
    st.selectbox("Varlık Listesi", opts, index=asset_idx, key="selected_asset_key", on_change=on_asset_change, label_visibility="collapsed", format_func=lambda x: x.replace(".IS", ""))
with col_search_in:
    st.text_input("Manuel", placeholder="Kod", key="manual_input_key", label_visibility="collapsed")
with col_search_btn:
    st.button("Ara", on_click=on_manual_button_click)

# --- AVCI GÜNLÜĞÜ PANELİ ---
found_opportunities = hunter_data["results"]
found_count = len(found_opportunities)
last_scan_time = hunter_data["last_run"] if hunter_data["last_run"] else "Bekleniyor..."
expander_title = f"🕵️ Avcı Günlüğü ({found_count} Fırsat) - Son Tarama: {last_scan_time}"
if found_count > 0: expander_title = f"🚨 {expander_title}"

with st.expander(expander_title, expanded=(found_count > 0)):
    if found_count == 0:
        st.info(f"Avcı şu an **{st.session_state.category}** listesinde iz sürüyor... Henüz net bir Golden Setup düşmedi.")
    else:
        sorted_opps = sorted(found_opportunities, key=lambda x: x['score'], reverse=True)
        c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
        c1.markdown("**Sembol**"); c2.markdown("**Sinyal**"); c3.markdown("**Detay**"); c4.markdown("**Aksiyon**")
        st.markdown("<hr style='margin:2px 0;'>", unsafe_allow_html=True)
        for opp in sorted_opps:
            rc1, rc2, rc3, rc4 = st.columns([1, 2, 2, 1])
            rc1.markdown(f"**{opp['symbol']}**")
            badge_color = "hunter-badge-green" if "LONG" in opp['type'] else "hunter-badge-red" if "SHORT" in opp['type'] else "hunter-badge-blue"
            rc2.markdown(f"<span class='{badge_color}'>{opp['type']}</span>", unsafe_allow_html=True)
            rc3.caption(f"{opp['detail']} (Skor: {opp['score']})")
            if rc4.button("🔍 Git", key=f"btn_hunt_{opp['symbol']}"):
                on_hunter_click(opp['symbol'])
                st.rerun()

st.markdown("<hr style='margin-top:0.5rem; margin-bottom:0.5rem;'>", unsafe_allow_html=True)

# PROMPT TETİKLEYİCİ
if 'generate_prompt' not in st.session_state: st.session_state.generate_prompt = False
if st.session_state.generate_prompt:
    t = st.session_state.ticker
    ict_data = calculate_ict_concepts(t) or {}
    sent_data = calculate_sentiment_score(t) or {}
    tech_data = get_tech_card_data(t) or {}
    radar_val = "Veri Yok"; radar_setup = "Belirsiz"
    if st.session_state.radar2_data is not None:
        r_row = st.session_state.radar2_data[st.session_state.radar2_data['Sembol'] == t]
        if not r_row.empty: radar_val = f"{r_row.iloc[0]['Skor']}/8"; radar_setup = r_row.iloc[0]['Setup']
    
    def clean_text(text): return re.sub(r'<[^>]+>', '', str(text)) if isinstance(text, str) else str(text)
    
    prompt = f"""
*** SİSTEM ROLLERİ ***
Sen ICT (Inner Circle Trader) ve Price Action ustası bir Algoritmik Tradersın. {t} varlığını yorumla.

*** 1. TEKNİK VERİLER ***
- SMA50: {tech_data.get('sma50', 'Bilinmiyor')}
- Stop (ATR): {tech_data.get('stop_level', 'Bilinmiyor')}
- Radar 2: {radar_val} ({radar_setup})

*** 2. DUYGU ***
- Sentiment: {sent_data.get('total', 0)}/100
- Momentum: {clean_text(sent_data.get('mom', 'Veri Yok'))}

*** 3. ICT / KURUMSAL YAPILAR ***
- Yapı: {ict_data.get('structure', '-')}
- Bölge: {ict_data.get('pos_label', '-')}
- FVG: {ict_data.get('fvg', 'Yok')}
- LİKİDİTE: {ict_data.get('liquidity', 'Belirsiz')}
- GOLDEN SİNYAL: {ict_data.get('golden_text', 'Yok')}

ÇIKTI:
🎯 YÖN: [LONG/SHORT/BEKLE]
💡 STRATEJİ: (Giriş, Stop, Hedef)
⚠️ RİSK: (En büyük tehlike)
"""
    with st.sidebar: st.code(prompt, language="text"); st.success("Metin hazır! 📋")
    st.session_state.generate_prompt = False

# İÇERİK
info = fetch_stock_info(st.session_state.ticker)
col_left, col_right = st.columns([3, 1])

with col_left:
    if info and info['price']:
        sc1, sc2, sc3, sc4 = st.columns(4)
        cls = "delta-pos" if info['change_pct'] >= 0 else "delta-neg"
        sc1.markdown(f'<div class="stat-box-small"><p class="stat-label-small">FİYAT</p><p class="stat-value-small money-text">{info["price"]:.2f}<span class="stat-delta-small {cls}">{"+" if info["change_pct"]>=0 else ""}{info["change_pct"]:.2f}%</span></p></div>', unsafe_allow_html=True)
        sc2.markdown(f'<div class="stat-box-small"><p class="stat-label-small">HACİM</p><p class="stat-value-small money-text">{info["volume"]/1e6:.1f}M</p></div>', unsafe_allow_html=True)
        sc3.markdown(f'<div class="stat-box-small"><p class="stat-label-small">HEDEF</p><p class="stat-value-small money-text">{info["target"]}</p></div>', unsafe_allow_html=True)
        sc4.markdown(f'<div class="stat-box-small"><p class="stat-label-small">SEKTÖR</p><p class="stat-value-small">{str(info["sector"])[:12]}</p></div>', unsafe_allow_html=True)
    
    st.write("")
    render_tradingview_widget(st.session_state.ticker, height=650)
    
    st.markdown(f"<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:20px;'>📡 {st.session_state.ticker} hakkında haberler ve analizler</div>", unsafe_allow_html=True)
    
    symbol_raw = st.session_state.ticker
    base_symbol = symbol_raw.replace(".IS", "").replace("=F", "").replace("-USD", "")
    lower_symbol = base_symbol.lower()
    
    st.markdown(f"""
    <div class="news-card" style="display:flex; flex-wrap:wrap; align-items:center; gap:8px; border-left:none;">
        <a href="https://seekingalpha.com/symbol/{base_symbol}/news" target="_blank"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.7rem; font-weight:600;">SeekingAlpha</div></a>
        <a href="https://finance.yahoo.com/quote/{base_symbol}/news" target="_blank"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.7rem; font-weight:600;">Yahoo Finance</div></a>
        <a href="https://www.nasdaq.com/market-activity/stocks/{lower_symbol}/news-headlines" target="_blank"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.7rem; font-weight:600;">Nasdaq</div></a>
        <a href="https://stockanalysis.com/stocks/{lower_symbol}/" target="_blank"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.7rem; font-weight:600;">StockAnalysis</div></a>
        <a href="https://finviz.com/quote.ashx?t={base_symbol}&p=d" target="_blank"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.7rem; font-weight:600;">Finviz</div></a>
        <a href="https://unusualwhales.com/stock/{base_symbol}/overview" target="_blank"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.7rem; font-weight:600;">UnusualWhales</div></a>
    </div>""", unsafe_allow_html=True)

with col_right:
    sent_data = calculate_sentiment_score(st.session_state.ticker)
    render_sentiment_card(sent_data)
    ict_data = calculate_ict_concepts(st.session_state.ticker)
    render_ict_panel(ict_data)
    render_detail_card(st.session_state.ticker)
    render_radar_params_card()
    xray_data = get_deep_xray_data(st.session_state.ticker)
    render_deep_xray_card(xray_data)
    
    st.markdown(f"<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:10px; color:#1e3a8a; background-color:{current_theme['box_bg']}; padding:5px; border-radius:5px; border:1px solid #1e40af;'>🎯 Ortak Fırsatlar</div>", unsafe_allow_html=True)
    with st.container(height=250):
        df1 = st.session_state.scan_data
        df2 = st.session_state.radar2_data
        if df1 is not None and df2 is not None and not df1.empty and not df2.empty:
            commons = []
            symbols = set(df1["Sembol"]).intersection(set(df2["Sembol"]))
            if symbols:
                for sym in symbols:
                    r1 = float(df1[df1["Sembol"]==sym].iloc[0]["Skor"])
                    r2 = float(df2[df2["Sembol"]==sym].iloc[0]["Skor"])
                    commons.append({"symbol": sym, "r1": r1, "r2": r2, "total": r1+r2})
                for i, item in enumerate(sorted(commons, key=lambda x: x["total"], reverse=True)):
                    rank = "🥇" if i==0 else "🥈" if i==1 else "🥉" if i==2 else f"{i+1}."
                    c1, c2 = st.columns([0.2, 0.8])
                    star = "★" if item["symbol"] in st.session_state.watchlist else "☆"
                    if c1.button(star, key=f"c_star_{item['symbol']}"): toggle_watchlist(item["symbol"]); st.rerun()
                    if c2.button(f"{rank} {item['symbol']} ({int(item['total'])}/16)", key=f"c_sel_{item['symbol']}"): on_scan_result_click(item["symbol"]); st.rerun()
            else: st.info("Kesişim yok.")
        else: st.caption("İki radar da çalıştırılmalı.")

st.markdown("<hr>", unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["🧠 RADAR 1", "🚀 RADAR 2", "📜 İzleme"])

with tab1:
    if st.button(f"⚡ {st.session_state.category} Tara", type="primary"):
        with st.spinner("Taranıyor..."): st.session_state.scan_data = analyze_market_intelligence(ASSET_GROUPS.get(st.session_state.category, []))
    if st.session_state.scan_data is not None:
        with st.container(height=500):
            for i, row in st.session_state.scan_data.iterrows():
                c1, c2 = st.columns([0.2, 0.8])
                if c1.button("★", key=f"r1_{i}"): toggle_watchlist(row["Sembol"]); st.rerun()
                if c2.button(f"🔥 {row['Skor']}/8 | {row['Sembol']}", key=f"r1_b_{i}"): on_scan_result_click(row["Sembol"]); st.rerun()
                st.caption(row['Nedenler'])

with tab2:
    if st.button(f"🚀 RADAR 2 Tara", type="primary"):
        with st.spinner("Taranıyor..."): st.session_state.radar2_data = radar2_scan(ASSET_GROUPS.get(st.session_state.category, []))
    if st.session_state.radar2_data is not None:
        with st.container(height=500):
            for i, row in st.session_state.radar2_data.iterrows():
                c1, c2 = st.columns([0.2, 0.8])
                if c1.button("★", key=f"r2_{i}"): toggle_watchlist(row["Sembol"]); st.rerun()
                if c2.button(f"🚀 {row['Skor']}/8 | {row['Sembol']} | {row['Setup']}", key=f"r2_b_{i}"): on_scan_result_click(row["Sembol"]); st.rerun()
                st.caption(f"Trend: {row['Trend']} | RS: {row['RS']}%")

with tab3:
    if st.button("⚡ Listeyi Tara", type="secondary"):
        with st.spinner("..."): st.session_state.scan_data = analyze_market_intelligence(st.session_state.watchlist)
    for sym in st.session_state.watchlist:
        c1, c2 = st.columns([0.2, 0.8])
        if c1.button("❌", key=f"wl_d_{sym}"): toggle_watchlist(sym); st.rerun()
        if c2.button(sym, key=f"wl_g_{sym}"): on_scan_result_click(sym); st.rerun()
