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

# ==============================================================================
# 1. AYARLAR VE STİL
# ==============================================================================
st.set_page_config(
    page_title="PATRONUN BORSA TERMİNALİ", 
    layout="wide",
    page_icon="💸"
)

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
    .stat-label-small {{ font-size: 0.5rem; color: #64748B; text-transform: uppercase; margin: 0; }}
    .stat-value-small {{ font-size: 0.9rem; font-weight: 600; color: {current_theme['text']}; margin: 0; }}
    .stat-delta-small {{ font-size: 0.8rem; margin-left: 5px; }}
    
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
    
    /* Zengin Eğitim Notu Stili */
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
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. VERİTABANI VE LİSTELER
# ==============================================================================
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

# --- VARLIK LİSTELERİ (TAM LİSTE) ---
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
    "LLY", "UNH", "JNJ", "MRK", "ABBV", "TMO", "DHR", "ABT", "BMY", "AMGN", "ISRG", 
    "SYK", "ELV", "CVS", "CI", "GILD", "REGN", "VRTX", "ZTS", "BSX", "BDX", "HCA", 
    "MCK", "COR", "CAH", "CNC", "HUM", "MOH", "DXCM", "EW", "RMD", "ALGN", "ZBH", 
    "BAX", "STE", "COO", "WAT", "MTD", "IQV", "A", "HOLX", "IDXX", "BIO", "WMT", 
    "HD", "PG", "COST", "KO", "PEP", "MCD", "SBUX", "NKE", "DIS", "TMUS", "CMCSA", 
    "NFLX", "TGT", "LOW", "TJX", "PM", "EL", "CL", "K", "GIS", "MNST", "TSCO", 
    "ROST", "FAST", "DLTR", "DG", "ORLY", "AZO", "ULTA", "BBY", "KHC", "HSY", "MKC", 
    "CLX", "KMB", "SYY", "KR", "ADM", "STZ", "TAP", "CAG", "SJM", "XOM", "CVX", 
    "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HES", "KMI", "GE", "CAT", 
    "DE", "HON", "MMM", "ETN", "ITW", "EMR", "PH", "CMI", "PCAR", "BA", "LMT", 
    "RTX", "GD", "NOC", "LHX", "TDG", "TXT", "HII", "UPS", "FDX", "UNP", "CSX", 
    "NSC", "DAL", "UAL", "AAL", "LUV", "FCX", "NEM", "NUE", "DOW", "CTVA", "LIN", 
    "SHW", "PPG", "ECL", "APD", "VMC", "MLM", "ROP", "TT", "CARR", "OTIS", "ROK", 
    "AME", "DOV", "XYL", "WAB", "NEE", "DUK", "SO", "AEP", "SRE", "D", "PEG", 
    "ED", "XEL", "PCG", "WEC", "ES", "AMT", "PLD", "CCI", "EQIX", "PSA", "O", 
    "DLR", "SPG", "VICI", "CBRE", "CSGP", "WELL", "AVB", "EQR", "EXR", "MAA", 
    "HST", "KIM", "REG", "SBAC", "WY", "PHM", "LEN", "DHI", "LVS", "MGM", "T", 
    "VZ", "BKNG", "MAR", "F", "GM", "STT", "ZBRA", "GL", "EWBC", "OHI", "EXPE", 
    "CF", "HAL", "HP", "RCL", "NCLH", "CPRT", "FANG", "PXD", "OKE", "WMB", "TRGP"
]
raw_sp500_rest = list(set(raw_sp500_rest) - set(priority_sp))
raw_sp500_rest.sort()
final_sp500_list = priority_sp + raw_sp500_rest

priority_crypto = ["GC=F", "SI=F", "BTC-USD", "ETH-USD"]
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

# --- BIST 100 LİSTESİ (ENDEKSLER + HİSSELER) ---
# 1. Önce Endeksler (Priority)
priority_bist_indices = ["XU100.IS", "XU030.IS", "XBANK.IS"]

# 2. Sonra Hisseler (Alfabetik)
raw_bist_stocks = [
    "AEFES.IS", "AGHOL.IS", "AHGAZ.IS", "AKBNK.IS", "AKCNS.IS", "AKFGY.IS", "AKFYE.IS", "AKSA.IS", 
    "AKSEN.IS", "ALARK.IS", "ALBRK.IS", "ALFAS.IS", "ANSGR.IS", "ARCLK.IS", "ASELS.IS", 
    "ASTOR.IS", "BERA.IS", "BIMAS.IS", "BIOEN.IS", "BOBET.IS", "BRSAN.IS", "BRYAT.IS", "BUCIM.IS", 
    "CANTE.IS", "CCOLA.IS", "CEMTS.IS", "CIMSA.IS", "CWENE.IS", "DOAS.IS", "DOHOL.IS", "ECILC.IS", 
    "ECZYT.IS", "EGEEN.IS", "EKGYO.IS", "ENJSA.IS", "ENKAI.IS", "EREGL.IS", "EUREN.IS", 
    "EUPWR.IS", "FENER.IS", "FROTO.IS", "GARAN.IS", "GENIL.IS", "GESAN.IS", "GLYHO.IS", "GOKNR.IS", 
    "GUBRF.IS", "GWIND.IS", "HALKB.IS", "HEKTS.IS", "IPEKE.IS", "ISCTR.IS", "ISDMR.IS", 
    "ISGYO.IS", "ISMEN.IS", "IZENR.IS", "KCAER.IS", "KCHOL.IS", "KLSER.IS", "KONTR.IS", "KONYA.IS", 
    "KORDS.IS", "KOZAA.IS", "KOZAL.IS", "KRDMD.IS", "KZBGY.IS", "MAVI.IS", "MGROS.IS", 
    "MIATK.IS", "ODAS.IS", "OTKAR.IS", "OYAKC.IS", "PENTA.IS", "PETKM.IS", "PGSUS.IS", 
    "PSGYO.IS", "QUAGR.IS", "REEDR.IS", "SAHOL.IS", "SASA.IS", "SDTTR.IS", "SISE.IS", "SKBNK.IS", 
    "SMRTG.IS", "SOKM.IS", "TABGD.IS", "TAVHL.IS", "TCELL.IS", "THYAO.IS", "TKFEN.IS", "TOASO.IS", 
    "TSKB.IS", "TTKOM.IS", "TTRAK.IS", "TUKAS.IS", "TUPRS.IS", "TURSG.IS", "ULUUN.IS", "VAKBNK.IS", 
    "VESBE.IS", "VESTL.IS", "YEOTK.IS", "YKBNK.IS", "YLALI.IS", "ZOREN.IS"
]
raw_bist_stocks.sort()

# 3. Birleştir
final_bist100_list = priority_bist_indices + raw_bist_stocks

ASSET_GROUPS = {
    "S&P 500 (TOP 300)": final_sp500_list,
    "NASDAQ (TOP 100)": raw_nasdaq,
    "BIST 100": final_bist100_list,
    "EMTİA & KRİPTO": final_crypto_list
}
INITIAL_CATEGORY = "S&P 500 (TOP 300)"

# --- STATE YÖNETİMİ ---
if 'category' not in st.session_state: st.session_state.category = INITIAL_CATEGORY
if 'ticker' not in st.session_state: st.session_state.ticker = "NVDA"
if 'scan_data' not in st.session_state: st.session_state.scan_data = None
if 'radar2_data' not in st.session_state: st.session_state.radar2_data = None
if 'agent3_data' not in st.session_state: st.session_state.agent3_data = None
if 'watchlist' not in st.session_state: st.session_state.watchlist = load_watchlist_db()
if 'stp_scanned' not in st.session_state: st.session_state.stp_scanned = False
if 'stp_crosses' not in st.session_state: st.session_state.stp_crosses = []
if 'stp_trends' not in st.session_state: st.session_state.stp_trends = []

# --- CALLBACKLER ---
def on_category_change():
    new_cat = st.session_state.get("selected_category_key")
    if new_cat and new_cat in ASSET_GROUPS:
        st.session_state.category = new_cat
        st.session_state.ticker = ASSET_GROUPS[new_cat][0]
        st.session_state.scan_data = None
        st.session_state.radar2_data = None
        st.session_state.agent3_data = None
        st.session_state.stp_scanned = False

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
# 3. HESAPLAMA FONKSİYONLARI (CORE LOGIC)
# ==============================================================================

@st.cache_data(ttl=900)
def scan_stp_signals(asset_list):
    if not asset_list: return None, None
    cross_signals = []
    trend_signals = []
    try:
        data = yf.download(asset_list, period="1mo", group_by="ticker", threads=True, progress=False)
    except:
        return [], []

    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol not in data.columns.levels[0]: continue
                df = data[symbol].copy()
            else:
                if len(asset_list) == 1: df = data.copy()
                else: continue

            if df.empty or 'Close' not in df.columns: continue
            df = df.dropna()
            if len(df) < 10: continue

            close = df['Close']; high = df['High']; low = df['Low']
            typical_price = (high + low + close) / 3
            stp = typical_price.ewm(span=6, adjust=False).mean()
            
            c_last = float(close.iloc[-1]); c_prev = float(close.iloc[-2])
            s_last = float(stp.iloc[-1]); s_prev = float(stp.iloc[-2])
            
            if c_prev <= s_prev and c_last > s_last:
                cross_signals.append({"Sembol": symbol, "Fiyat": c_last, "STP": s_last, "Fark": ((c_last/s_last)-1)*100})
            elif c_prev > s_prev and c_last > s_last:
                trend_signals.append({"Sembol": symbol, "Fiyat": c_last, "STP": s_last, "Fark": ((c_last/s_last)-1)*100})
        except:
            continue
    return cross_signals, trend_signals

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
            bb_width = ((sma20 + 2*std20) - (sma20 - 2*std20)) / (sma20 - 0.0001)
            hist = (close.ewm(span=12, adjust=False).mean() - close.ewm(span=12, adjust=False).mean()).ewm(span=9, adjust=False).mean()
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + (gain / loss)))
            williams_r = (high.rolling(14).max() - close) / (high.rolling(14).max() - low.rolling(14).min()) * -100
            daily_range = high - low
            
            score = 0; reasons = []; details = {}
            curr_c = float(close.iloc[-1]); curr_vol = float(volume.iloc[-1])
            avg_vol = float(volume.rolling(5).mean().iloc[-1]) if len(volume) > 5 else 1.0
            
            if bb_width.iloc[-1] <= bb_width.tail(60).min() * 1.1:
                score += 1; reasons.append("🚀 Squeeze"); details['Squeeze'] = True
            else: details['Squeeze'] = False
            
            if daily_range.iloc[-1] == daily_range.tail(4).min() and daily_range.iloc[-1] > 0:
                score += 1; reasons.append("🔇 NR4"); details['NR4'] = True
            else: details['NR4'] = False
            
            if ((ema5.iloc[-1] > ema20.iloc[-1]) and (ema5.iloc[-2] <= ema20.iloc[-2])) or ((ema5.iloc[-2] > ema20.iloc[-2]) and (ema5.iloc[-3] <= ema20.iloc[-3])):
                score += 1; reasons.append("⚡ Trend"); details['Trend'] = True
            else: details['Trend'] = False
            
            if hist.iloc[-1] > hist.iloc[-2]:
                score += 1; reasons.append("🟢 MACD"); details['MACD'] = True
            else: details['MACD'] = False
            
            if williams_r.iloc[-1] > -50:
                score += 1; reasons.append("🔫 W%R"); details['W%R'] = True
            else: details['W%R'] = False
            
            if curr_vol > avg_vol * 1.2:
                score += 1; reasons.append("🔊 Hacim"); details['Hacim'] = True
            else: details['Hacim'] = False
            
            if curr_c >= high.tail(20).max() * 0.98:
                score += 1; reasons.append("🔨 Breakout"); details['Breakout'] = True
            else: details['Breakout'] = False
            
            rsi_c = rsi.iloc[-1]
            if 30 < rsi_c < 65 and rsi_c > rsi.iloc[-2]:
                score += 1; reasons.append("⚓ RSI Güçlü"); details['RSI Güçlü'] = True
            else: details['RSI Güçlü'] = False
            
            if score > 0:
                return {
                    "Sembol": symbol,
                    "Fiyat": f"{curr_c:.2f}",
                    "Skor": score,
                    "Nedenler": " | ".join(reasons),
                    "Detaylar": details
                }
            return None
        except:
            return None

    signals = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(process_symbol, asset_list))
    signals = [r for r in results if r is not None]
    return pd.DataFrame(signals).sort_values(by="Skor", ascending=False) if signals else pd.DataFrame()

@st.cache_data(ttl=3600)
def radar2_scan(asset_list, min_price=5, max_price=5000, min_avg_vol_m=0.5):
    if not asset_list: return pd.DataFrame()
    try:
        data = yf.download(asset_list, period="1y", group_by="ticker", threads=True, progress=False)
    except:
        return pd.DataFrame()
    try:
        idx = yf.download("^GSPC", period="1y", progress=False)["Close"]
    except:
        idx = None

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
            
            sma20 = close.rolling(20).mean(); sma50 = close.rolling(50).mean(); sma100 = close.rolling(100).mean(); sma200 = close.rolling(200).mean()
            trend = "Yatay"
            if not np.isnan(sma200.iloc[-1]):
                if curr_c > sma50.iloc[-1] > sma100.iloc[-1] > sma200.iloc[-1] and sma200.iloc[-1] > sma200.iloc[-20]: trend = "Boğa"
                elif curr_c < sma200.iloc[-1] and sma200.iloc[-1] < sma200.iloc[-20]: trend = "Ayı"
            
            delta = close.diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + (gain / loss))); rsi_c = float(rsi.iloc[-1])
            ema12 = close.ewm(span=12, adjust=False).mean(); ema26 = close.ewm(span=26, adjust=False).mean()
            hist = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()
            recent_high_60 = float(high.rolling(60).max().iloc[-1])
            breakout_ratio = curr_c / recent_high_60 if recent_high_60 > 0 else 0
            
            rs_score = 0.0
            if idx is not None and len(close) > 60 and len(idx) > 60:
                common_index = close.index.intersection(idx.index)
                if len(common_index) > 60:
                    cs = close.reindex(common_index); isx = idx.reindex(common_index)
                    rs_score = float((cs.iloc[-1]/cs.iloc[-60]-1) - (isx.iloc[-1]/isx.iloc[-60]-1))
            
            setup = "-"; tags = []; score = 0; details = {}
            avg_vol_20 = max(avg_vol_20, 1); vol_spike = volume.iloc[-1] > avg_vol_20 * 1.3
            
            if trend == "Boğa" and breakout_ratio >= 0.97: setup = "Breakout"; score += 2; tags.append("Zirve")
            if vol_spike: score += 1; tags.append("Hacim+"); details['Hacim Patlaması'] = True
            else: details['Hacim Patlaması'] = False
            
            if trend == "Boğa" and setup == "-":
                if sma20.iloc[-1] <= curr_c <= sma50.iloc[-1] * 1.02 and 40 <= rsi_c <= 55: setup = "Pullback"; score += 2; tags.append("Düzeltme")
                if volume.iloc[-1] < avg_vol_20 * 0.9: score += 1; tags.append("Sığ Satış")
            if setup == "-":
                if rsi.iloc[-2] < 30 <= rsi_c and hist.iloc[-1] > hist.iloc[-2]: setup = "Dip Dönüşü"; score += 2; tags.append("Dip Dönüşü")
            
            if rs_score > 0: score += 1; tags.append("RS+"); details['RS (S&P500)'] = True
            else: details['RS (S&P500)'] = False
            
            if trend == "Boğa": score += 1; details['Boğa Trendi'] = True
            else:
                if trend == "Ayı": score -= 1
                details['Boğa Trendi'] = False
            
            details['60G Zirve'] = breakout_ratio >= 0.90; details['RSI Bölgesi'] = (40 <= rsi_c <= 60); details['MACD Hist'] = hist.iloc[-1] > hist.iloc[-2]
            
            if score > 0:
                return {
                    "Sembol": symbol, "Fiyat": round(curr_c, 2), "Trend": trend, "Setup": setup, "Skor": score,
                    "RS": round(rs_score * 100, 1), "Etiketler": " | ".join(tags), "Detaylar": details
                }
            return None
        except: return None

    results = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(process_radar2, asset_list))
    results = [r for r in results if r is not None]
    return pd.DataFrame(results).sort_values(by=["Skor", "RS"], ascending=False).head(50) if results else pd.DataFrame()

@st.cache_data(ttl=3600)
def agent3_breakout_scan(asset_list):
    if not asset_list: return pd.DataFrame()
    try: data = yf.download(asset_list, period="6mo", group_by="ticker", threads=True, progress=False)
    except: return pd.DataFrame()

    def process_agent3(symbol):
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol not in data.columns.levels[0]: return None
                df = data[symbol].copy()
            else:
                if len(asset_list) == 1: df = data.copy()
                else: return None
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
                if (close.iloc[-1] < open_.iloc[-1]) and (close.iloc[-2] < open_.iloc[-2]) and (close.iloc[-3] < open_.iloc[-3]):
                    is_short_signal = True; short_reason = "3 Kırmızı Mum (Düşüş)"
                body_last = abs(close.iloc[-1] - open_.iloc[-1]); body_prev1 = abs(close.iloc[-2] - open_.iloc[-2]); body_prev2 = abs(close.iloc[-3] - open_.iloc[-3])
                if (close.iloc[-1] < open_.iloc[-1]) and (body_last > (body_prev1 + body_prev2)):
                    is_short_signal = True; short_reason = "Yutan Ayı Mum (Engulfing)"
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
                return {
                    "Sembol_Raw": symbol, "Sembol_Display": display_symbol, "Fiyat": f"{curr_price:.2f}",
                    "Zirveye Yakınlık": prox_str + wick_warning, "Hacim Durumu": rvol_text,
                    "Trend Durumu": trend_display, "RSI": f"{rsi:.0f}", "SortKey": rvol
                }
            return None
        except: return None
    results = []
    with concurrent.futures.ThreadPoolExecutor() as executor: results = list(executor.map(process_agent3, asset_list))
    results = [r for r in results if r is not None]
    return pd.DataFrame(results).sort_values(by="SortKey", ascending=False) if results else pd.DataFrame()

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
        macd = close.ewm(span=12).mean() - close.ewm(span=26).mean(); hist = macd - macd.ewm(span=9).mean()
        if hist.iloc[-1] > 0 and hist.iloc[-1] > hist.iloc[-2]: score_mom += 10; reasons_mom.append("MACD ↑")
        if rsi.iloc[-1] < 30: reasons_mom.append("OS")
        elif rsi.iloc[-1] > 70: reasons_mom.append("OB")
        else: score_mom += 10; reasons_mom.append("Stoch Stabil")
        score_vol = 0; reasons_vol = []
        if volume.iloc[-1] > volume.rolling(20).mean().iloc[-1]: score_vol += 15; reasons_vol.append("Vol ↑")
        else: reasons_vol.append("Vol ↓")
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        if obv.iloc[-1] > obv.rolling(5).mean().iloc[-1]: score_vol += 10; reasons_vol.append("OBV ↑")
        score_tr = 0; reasons_tr = []; sma50 = close.rolling(50).mean(); sma200 = close.rolling(200).mean()
        if sma50.iloc[-1] > sma200.iloc[-1]: score_tr += 10; reasons_tr.append("GoldCross")
        if close.iloc[-1] > sma50.iloc[-1]: score_tr += 10; reasons_tr.append("P > SMA50")
        score_vola = 0; reasons_vola = []; std = close.rolling(20).std(); upper = close.rolling(20).mean() + (2 * std)
        if close.iloc[-1] > upper.iloc[-1]: score_vola += 10; reasons_vola.append("BB Break")
        atr = (high-low).rolling(14).mean(); 
        if atr.iloc[-1] < atr.iloc[-5]: score_vola += 5; reasons_vola.append("Vola ↓")
        score_str = 0; reasons_str = []
        if close.iloc[-1] > high.rolling(20).max().shift(1).iloc[-1]: score_str += 10; reasons_str.append("Yeni Tepe (BOS)")
        total = score_mom + score_vol + score_tr + score_vola + score_str
        bars = int(total / 5); bar_str = "[" + "|" * bars + "." * (20 - bars) + "]"
        def fmt(lst): return f"<span style='font-size:0.75rem; color:#64748B;'>({' + '.join(lst)})</span>" if lst else ""
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

# --- ICT MODÜLÜ (GÜNCELLENDİ: Hem Zengin Analiz Hem R/R Hesaplar) ---
@st.cache_data(ttl=600)
def calculate_ict_deep_analysis(ticker):
    try:
        # 1. Veri Hazırlığı
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty or len(df) < 60: return {"error": "Yetersiz Veri"}
        
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        high = df['High']; low = df['Low']; close = df['Close']; open_ = df['Open']
        
        # ATR ve Beden Boyutu
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        avg_body_size = abs(open_ - close).rolling(20).mean()

        # --- SWING NOKTALARI (Fractals) ---
        sw_highs = []; sw_lows = []
        for i in range(2, len(df)-2):
            if high.iloc[i] >= max(high.iloc[i-2:i]) and high.iloc[i] >= max(high.iloc[i+1:i+3]):
                sw_highs.append((df.index[i], high.iloc[i])) # Tarih, Fiyat
            if low.iloc[i] <= min(low.iloc[i-2:i]) and low.iloc[i] <= min(low.iloc[i+1:i+3]):
                sw_lows.append((df.index[i], low.iloc[i]))

        if not sw_highs or not sw_lows: return {"error": "Swing Yapısı Oluşmadı"}

        curr_price = close.iloc[-1]
        last_sh = sw_highs[-1][1] # Son Swing High
        last_sl = sw_lows[-1][1]  # Son Swing Low
        
        # Market Yapısı (MSS / BOS)
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

        # --- LİKİDİTE HEDEFLERİ (BSL / SSL) ---
        next_bsl = min([h[1] for h in sw_highs if h[1] > curr_price], default=None)
        next_ssl = max([l[1] for l in sw_lows if l[1] < curr_price], default=None)
        if next_bsl is None: next_bsl = high.max()
        if next_ssl is None: next_ssl = low.min()

        # --- PD ARRAYS (FVG) ---
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

        # --- OB LOGIC (Klasik ICT) ---
        active_ob_txt = "Yok"
        lookback = 20
        start_idx = max(0, len(df) - lookback)
        
        if bias == "bullish" or bias == "bullish_retrace":
            if bullish_fvgs:
                f = bullish_fvgs[-1]
                active_fvg_txt = f"Açık FVG var (Destek): {f['bot']:.2f} - {f['top']:.2f}"
            
            # Bullish OB (Son düşüş mumu)
            lowest_idx = df['Low'].iloc[start_idx:].idxmin()
            if isinstance(lowest_idx, pd.Timestamp): lowest_idx = df.index.get_loc(lowest_idx)
            for i in range(lowest_idx, max(0, lowest_idx-5), -1):
                if df['Close'].iloc[i] < df['Open'].iloc[i]: # Kırmızı
                    active_ob_txt = f"{df['Low'].iloc[i]:.2f} - {df['High'].iloc[i]:.2f} (Talep Bölgesi)"
                    break
                    
        elif bias == "bearish" or bias == "bearish_retrace":
            if bearish_fvgs:
                f = bearish_fvgs[-1]
                active_fvg_txt = f"Açık FVG var (Direnç): {f['bot']:.2f} - {f['top']:.2f}"
            
            # Bearish OB (Son yükseliş mumu)
            highest_idx = df['High'].iloc[start_idx:].idxmax()
            if isinstance(highest_idx, pd.Timestamp): highest_idx = df.index.get_loc(highest_idx)
            for i in range(highest_idx, max(0, highest_idx-5), -1):
                if df['Close'].iloc[i] > df['Open'].iloc[i]: # Yeşil
                    active_ob_txt = f"{df['Low'].iloc[i]:.2f} - {df['High'].iloc[i]:.2f} (Arz Bölgesi)"
                    break

        # --- SETUP KURULUMU (RİSK / GETİRİ HESABI) ---
        setup_type = "BEKLE"
        entry_price = 0.0; stop_loss = 0.0; take_profit = 0.0; rr_ratio = 0.0
        setup_desc = "Net bir kurulum oluşmadı."
        
        # LONG SENARYOSU
        if bias in ["bullish", "bullish_retrace"]:
            valid_fvgs = [f for f in bullish_fvgs if f['top'] < curr_price * 1.02]
            if valid_fvgs:
                best_fvg = valid_fvgs[-1]
                entry_price = best_fvg['top']
                stop_loss = last_sl if last_sl < entry_price else best_fvg['bot'] - atr * 0.5
                take_profit = next_bsl
                risk = entry_price - stop_loss; reward = take_profit - entry_price
                if risk > 0:
                    rr_ratio = reward / risk
                    setup_type = "LONG"
                    setup_desc = "Fiyat Bullish yapıda. FVG bölgesinden tepki bekleniyor."

        # SHORT SENARYOSU
        elif bias in ["bearish", "bearish_retrace"]:
            valid_fvgs = [f for f in bearish_fvgs if f['bot'] > curr_price * 0.98]
            if valid_fvgs:
                best_fvg = valid_fvgs[-1]
                entry_price = best_fvg['bot']
                stop_loss = last_sh if last_sh > entry_price else best_fvg['top'] + atr * 0.5
                take_profit = next_ssl
                risk = stop_loss - entry_price; reward = entry_price - take_profit
                if risk > 0:
                    rr_ratio = reward / risk
                    setup_type = "SHORT"
                    setup_desc = "Fiyat Bearish yapıda. Direnç bloğundan ret bekleniyor."

        # Bölge Analizi
        range_high = max(high.tail(60)); range_low = min(low.tail(60))
        range_loc = (curr_price - range_low) / (range_high - range_low)
        zone = "PREMIUM (Pahalı)" if range_loc > 0.5 else "DISCOUNT (Ucuz)"

        return {
            "status": "OK", "structure": structure, "bias": bias, "zone": zone,
            "setup_type": setup_type, "entry": entry_price, "stop": stop_loss, "target": take_profit,
            "rr": rr_ratio, "desc": setup_desc, "last_sl": last_sl, "last_sh": last_sh,
            "displacement": displacement_txt, "fvg_txt": active_fvg_txt, "ob_txt": active_ob_txt
        }
    except Exception as e:
        return {"status": "Error", "msg": str(e)}

def render_ict_deep_panel(ticker):
    data = calculate_ict_deep_analysis(ticker)
    if data.get("status") == "Error":
        st.error(f"ICT Analiz Hatası: {data.get('msg')}")
        return
    
    # --- DİNAMİK AÇIKLAMALAR (TRANSLATOR) ---
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

    # --- 1. ESKİ ZENGİN PANEL (RESİMDEKİ GİBİ) ---
    # --- 2. YENİ R/R PANELİ ---
    if data['setup_type'] == "LONG":
        header_color = "#166534"; bg_color = "#f0fdf4"; border_color = "#16a34a"; icon = "🚀"
    elif data['setup_type'] == "SHORT":
        header_color = "#991b1b"; bg_color = "#fef2f2"; border_color = "#ef4444"; icon = "🔻"
    else:
        header_color = "#475569"; bg_color = "#f8fafc"; border_color = "#cbd5e1"; icon = "⏳"

    rr_display = f"{data['rr']:.2f}R" if data['rr'] > 0 else "-"
    
    html_content = f"""
    <div class="info-card" style="margin-bottom:8px;">
        <div class="info-header">🧠 ICT Smart Money Analisti: {ticker}</div>
        
        <div style="background:{bg_color_old}; padding:6px; border-radius:5px; border-left:3px solid {bias_color}; margin-bottom:8px;">
            <div style="font-weight:700; color:{bias_color}; font-size:0.8rem; margin-bottom:2px;">{data['structure']}</div>
            <div class="edu-note">{struct_desc}</div>
            
            <div class="info-row"><div class="label-long">Enerji:</div><div class="info-val">{data['displacement']}</div></div>
            <div class="edu-note">{energy_desc}</div>
        </div>

        <div style="margin-bottom:8px;">
            <div style="font-size:0.8rem; font-weight:700; color:#1e3a8a; border-bottom:1px dashed #cbd5e1; margin-bottom:4px;">📍 PD ARRAYS (Giriş/Çıkış Referansları)</div>
            
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
            <span>{icon} ICT TİCARET KURULUMU</span>
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

@st.cache_data(ttl=600)
def calculate_synthetic_sentiment(ticker):
    try:
        df = yf.download(ticker, period="6mo", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        if 'Close' not in df.columns: return None
        
        # Veri temizliği
        df = df.dropna()
        close = df['Close']; high = df['High']; low = df['Low']; volume = df['Volume']
        
        # --- 1. VEKTÖREL SKORLAMA (Tüm geçmiş için puan hesabı) ---
        # A) Momentum (RSI & MACD) - Max 30 Puan
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain / loss)))
        
        macd = close.ewm(span=12).mean() - close.ewm(span=26).mean()
        hist = macd - macd.ewm(span=9).mean()
        
        score_mom = np.where((rsi > 50) & (rsi > rsi.shift(1)), 10, 0) + \
                    np.where((hist > 0) & (hist > hist.shift(1)), 10, 0) + \
                    np.where((rsi > 30) & (rsi < 70), 10, 0) # Stabil bölge bonusu

        # B) Hacim (Volume & OBV) - Max 25 Puan
        vol_ma = volume.rolling(20).mean()
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        obv_ma = obv.rolling(5).mean()
        
        score_vol = np.where(volume > vol_ma, 15, 0) + \
                    np.where(obv > obv_ma, 10, 0)

        # C) Trend (SMA & Cross) - Max 20 Puan
        sma50 = close.rolling(50).mean()
        sma200 = close.rolling(200).mean()
        
        score_tr = np.where(sma50 > sma200, 10, 0) + \
                   np.where(close > sma50, 10, 0)

        # D) Volatilite (BB & ATR) - Max 15 Puan
        std = close.rolling(20).std()
        upper = close.rolling(20).mean() + (2 * std)
        atr = (high-low).rolling(14).mean()
        
        score_vola = np.where(close > upper, 10, 0) + \
                     np.where(atr < atr.shift(5), 5, 0) # Düşük volatilite iyidir (konsolidasyon)

        # E) Yapı (BOS - Break of Structure) - Max 10 Puan
        high_roll = high.rolling(20).max().shift(1)
        score_str = np.where(close > high_roll, 10, 0)

        # TOPLAM SKOR (0 - 100 Arası)
        total_score = score_mom + score_vol + score_tr + score_vola + score_str
        
        # --- 2. DEĞİŞİM HESABI (Bugün - Dün) ---
        # İşte orijinal grafikteki o -8, +2 değerlerini veren yer burası:
        sentiment_change = pd.Series(total_score).diff().fillna(0)
        
        # STP Hesabı (Grafikteki Sarı Çizgi için)
        typical_price = (high + low + close) / 3
        stp = typical_price.ewm(span=6, adjust=False).mean()
        
        # DataFrame Hazırlığı
        df = df.reset_index()
        if 'Date' not in df.columns: df['Date'] = df.index
        else: df['Date'] = pd.to_datetime(df['Date'])
        
        plot_df = pd.DataFrame({
            'Date': df['Date'], 
            'MF_Smooth': sentiment_change.values, # Artık bu Para Akışı değil, Puan Değişimi
            'STP': stp.values, 
            'Price': close.values
        }).tail(30).reset_index(drop=True)
        
        plot_df['Date_Str'] = plot_df['Date'].dt.strftime('%d %b')
        
        return plot_df
        
    except Exception as e: return None

@st.cache_data(ttl=600)
def get_tech_card_data(ticker):
    try:
        df = yf.download(ticker, period="2y", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']; high = df['High']; low = df['Low']
        sma50 = close.rolling(50).mean().iloc[-1]
        sma100 = close.rolling(100).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1]
        ema144 = close.ewm(span=144, adjust=False).mean().iloc[-1]
        atr = (high-low).rolling(14).mean().iloc[-1]
        return {
            "sma50": sma50, "sma100": sma100, "sma200": sma200, "ema144": ema144,
            "stop_level": close.iloc[-1] - (2 * atr), "risk_pct": (2 * atr) / close.iloc[-1] * 100,
            "atr": atr, "close_last": close.iloc[-1]
        }
    except: return None

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

# ==============================================================================
# 4. GÖRSELLEŞTİRME FONKSİYONLARI
# ==============================================================================

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
        <div style="font-family:'Courier New'; font-size:0.8rem; color:#1e3a8a; margin-bottom:5px;">{sent['bar']}</div>
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

def render_detail_card_advanced(ticker):
    ACIKLAMALAR = {
        "Squeeze": "🚀 Squeeze: Bollinger Bant genişliği son 60 günün en dar aralığında (Patlama Hazır)",
        "NR4": "🔇 NR4: (Daralma) Fiyat son 4 günün en dar fiyat aralığında",
        "Trend": "⚡ Trend: EMA5 > EMA20 üzerinde (Yükseliyor)",
        "MACD": "🟢 MACD: Histogram bir önceki günden yüksek (Momentum Artışı Var)",
        "W%R": "🔫 W%R: -50 üzerinde (Aşırı satım seviyesinden kurtulmuş)",
        "Hacim": "🔊 Hacim: Son 5 günlük hacim ortalama hacmin %20 üzerinde",
        "Breakout": "🔨 Breakout: Fiyat son 20 gün zirvesinin %98 veya üzerinde",
        "RSI Güçlü": "⚓ RSI Güçlü: 30-65 arasında ve artışta",
        "Hacim Patlaması": "💥 Hacim son 20 gün ortalamanın %30 üzerinde seyrediyor",
        "RS (S&P500)": "💪 Hisse, S&P 500 endeksinden daha güçlü",
        "Boğa Trendi": "🐂 Boğa Trendi: Fiyat Üç Ortalamanın da (SMA50 > SMA100 > SMA200) üzerinde",
        "60G Zirve": "⛰️ Zirve: Fiyat son 60 günün tepesine %97 yakınlıkta",
        "RSI Bölgesi": "🎯 RSI Uygun: Pullback için uygun (40-55 arası)",
        "MACD Hist": "🔄 MACD Dönüş: Histogram artışa geçti",
        "RS": "💪 Relatif Güç (RS)",
        "Setup": "🛠️ Setup Durumu"
    }

    display_ticker = ticker.replace(".IS", "").replace("=F", "")
    dt = get_tech_card_data(ticker)
    info = fetch_stock_info(ticker)
    
    price_val = "Veri Yok"
    if info and info.get('price'):
        price_val = f"{info['price']:.2f}"
    elif dt and 'close_last' in dt:
        price_val = f"{dt['close_last']:.2f}"
        
    ma_vals = "Veri Yok"
    stop_vals = "Veri Yok"
    if dt:
        ma_vals = f"SMA50: {dt['sma50']:.2f} | EMA144: {dt['ema144']:.2f}"
        stop_vals = f"{dt['stop_level']:.2f} (Risk: %{dt['risk_pct']:.1f})"

    r1_res = {}
    r1_score = 0
    if st.session_state.scan_data is not None:
        row = st.session_state.scan_data[st.session_state.scan_data["Sembol"] == ticker]
        if not row.empty and "Detaylar" in row.columns: 
            r1_res = row.iloc[0]["Detaylar"]; r1_score = row.iloc[0]["Skor"]
    
    if not r1_res:
        temp_df = analyze_market_intelligence([ticker])
        if not temp_df.empty and "Detaylar" in temp_df.columns: 
            r1_res = temp_df.iloc[0]["Detaylar"]; r1_score = temp_df.iloc[0]["Skor"]

    r2_res = {}
    r2_score = 0
    if st.session_state.radar2_data is not None:
        row = st.session_state.radar2_data[st.session_state.radar2_data["Sembol"] == ticker]
        if not row.empty and "Detaylar" in row.columns: 
            r2_res = row.iloc[0]["Detaylar"]; r2_score = row.iloc[0]["Skor"]
    
    if not r2_res:
        temp_df2 = radar2_scan([ticker])
        if not temp_df2.empty and "Detaylar" in temp_df2.columns: 
            r2_res = temp_df2.iloc[0]["Detaylar"]; r2_score = temp_df2.iloc[0]["Skor"]

    def get_icon(val): return "✅" if val else "❌"

    r1_html = ""
    for k, v in r1_res.items():
        text = ACIKLAMALAR.get(k, k)
        r1_html += f"<div class='tech-item' style='margin-bottom:2px;'>{get_icon(v)} <span style='margin-left:4px;'>{text}</span></div>"

    r2_html = ""
    for k, v in r2_res.items():
        text = ACIKLAMALAR.get(k, k)
        r2_html += f"<div class='tech-item' style='margin-bottom:2px;'>{get_icon(v)} <span style='margin-left:4px;'>{text}</span></div>"

    full_html = f"""
    <div class="info-card">
        <div class="info-header">📋 Gelişmiş Teknik Kart: {display_ticker}</div>
        <div style="display:flex; justify-content:space-between; margin-bottom:8px; border-bottom:1px solid #e5e7eb; padding-bottom:4px;">
            <div style="font-size:0.8rem; font-weight:700; color:#1e40af;">Fiyat: {price_val}</div>
            <div style="font-size:0.8rem; color:#64748B;">{ma_vals}</div>
        </div>
        <div style="font-size:0.8rem; color:#991b1b; margin-bottom:8px;">🛑 Stop: {stop_vals}</div>
        <div style="background:#f0f9ff; padding:4px; border-radius:4px; margin-bottom:4px;">
            <div style="font-weight:700; color:#0369a1; font-size:0.75rem; margin-bottom:4px;">🧠 RADAR 1 (Momentum) - Skor: {r1_score}/8</div>
            <div class="tech-grid" style="font-size:0.75rem;">
                {r1_html}
            </div>
        </div>
        <div style="background:#f0fdf4; padding:4px; border-radius:4px;">
            <div style="font-weight:700; color:#15803d; font-size:0.75rem; margin-bottom:4px;">🚀 RADAR 2 (Trend & Setup) - Skor: {r2_score}/6</div>
            <div class="tech-grid" style="font-size:0.75rem;">
                {r2_html}
            </div>
        </div>
    </div>
    """
    clean_html = full_html.replace("\n", " ")
    st.markdown(clean_html, unsafe_allow_html=True)

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
        st.altair_chart(alt.layer(bars, price_line).resolve_scale(y='independent').properties(height=280, title=alt.TitleParams("Sentiment Değişimi", fontSize=14, color="#1e40af")), use_container_width=True)
    with c2:
        base2 = alt.Chart(data).encode(x=x_axis)
        line_stp = base2.mark_line(color='#fbbf24', strokeWidth=3).encode(y=alt.Y('STP:Q', scale=alt.Scale(zero=False), axis=alt.Axis(title='Fiyat', titleColor='#64748B')), tooltip=['Date_Str', 'STP', 'Price'])
        line_price = base2.mark_line(color='#2563EB', strokeWidth=2).encode(y='Price:Q')
        area = base2.mark_area(opacity=0.15, color='gray').encode(y='STP:Q', y2='Price:Q')
        st.altair_chart(alt.layer(area, line_stp, line_price).properties(height=280, title=alt.TitleParams("STP Analizi: Mavi (Fiyat) Sarıyı (STP) Yukarı Keserse AL", fontSize=14, color="#1e40af")), use_container_width=True)

# ==============================================================================
# 5. SIDEBAR UI
# ==============================================================================
with st.sidebar:
    st.markdown(f"""<div style="font-size:1.5rem; font-weight:700; color:#1e3a8a; text-align:center; padding-top: 10px; padding-bottom: 10px;">PATRONUN BORSA TERMİNALİ</div><hr style="border:0; border-top: 1px solid #e5e7eb; margin-top:5px; margin-bottom:10px;">""", unsafe_allow_html=True)
    st.markdown("### ⚙️ Ayarlar")
    selected_theme_name = st.selectbox("", ["Beyaz", "Kirli Beyaz", "Buz Mavisi"], index=["Beyaz", "Kirli Beyaz", "Buz Mavisi"].index(st.session_state.theme), label_visibility="collapsed")
    if selected_theme_name != st.session_state.theme: st.session_state.theme = selected_theme_name; st.rerun()
    st.divider()
    with st.expander("🤖 AI Analist (Prompt)", expanded=True):
        st.caption("Verileri toplayıp ChatGPT için hazır metin oluşturur.")
        if st.button("📋 Analiz Metnini Hazırla", type="primary"): st.session_state.generate_prompt = True

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

if 'generate_prompt' not in st.session_state: st.session_state.generate_prompt = False
if st.session_state.generate_prompt:
    t = st.session_state.ticker
    ict_data = calculate_ict_deep_analysis(t) or {}; sent_data = calculate_sentiment_score(t) or {}; tech_data = get_tech_card_data(t) or {}
    radar_val = "Veri Yok"; radar_setup = "Belirsiz"
    if st.session_state.radar2_data is not None:
        r_row = st.session_state.radar2_data[st.session_state.radar2_data['Sembol'] == t]
        if not r_row.empty: radar_val = f"{r_row.iloc[0]['Skor']}/8"; radar_setup = r_row.iloc[0]['Setup']
    def clean_text(text): return re.sub(r'<[^>]+>', '', str(text))
    mom_clean = clean_text(sent_data.get('mom', 'Veri Yok')); vol_clean = clean_text(sent_data.get('vol', 'Veri Yok'))
    prompt = f"""*** SİSTEM ROLLERİ ***\nSen Dünya çapında tanınan, risk yönetimi uzmanı, ICT (Inner Circle Trader) ve Price Action ustası bir Algoritmik Tradersın.\nAşağıda {t} varlığı için terminalimden gelen HAM VERİLER var. Bunları yorumla.\n\n*** 1. TEKNİK VERİLER (Rakamlara Güven) ***\n- SMA50 Değeri: {tech_data.get('sma50', 'Bilinmiyor')}\n- Teknik Stop Seviyesi (ATR): {tech_data.get('stop_level', 'Bilinmiyor')}\n- Radar 2 Skoru: {radar_val}\n- Radar Setup: {radar_setup}\n\n*** 2. DUYGU VE MOMENTUM ***\n- Sentiment Puanı: {sent_data.get('total', 0)}/100\n- Momentum Durumu: {mom_clean}\n- Hacim/Para Girişi: {vol_clean}\n\n*** 3. ICT / KURUMSAL YAPILAR (KRİTİK) ***\n- Market Yapısı: {ict_data.get('structure', 'Bilinmiyor')}\n- Bölge (PD Array): {ict_data.get('zone', 'Bilinmiyor')} (Discount=Ucuz, Premium=Pahalı)\n- Hedef Likidite: {ict_data.get('target', 'Belirsiz')}\n\n*** GÖREVİN ***\nBu verileri analiz et. Eğer içinde çelişki varsa (Örn: Teknik AL derken Fiyat Premium'da mı?) analiz et ve işlem planı ver.\nKısa, net, maddeler halinde yaz. Yatırım tavsiyesi değildir deme, bir Swing Trader analisti gibi konuş.\n\nÇIKTI:\n💡 ANALİZ: Yarım paragraflık Temel Analiz, P/E, PEG, 12 aylık analist beklentileri. \n🎯 YÖN: [LONG/SHORT/BEKLE]\n💡 STRATEJİ: (Giriş yeri, Stop yeri, Hedef yeri)\n⚠️ RİSK: (Gördüğün en büyük tehlike)\n"""
    with st.sidebar: st.code(prompt, language="text"); st.success("Metin kopyalanmaya hazır! 📋")
    st.session_state.generate_prompt = False

# Hisse bilgisini çekiyoruz (Hem sol hem sağ sütun kullanacak)
info = fetch_stock_info(st.session_state.ticker)

col_left, col_right = st.columns([3, 1])

# --- SOL SÜTUN (Grafikler ve Analizler) ---
with col_left:
    synth_data = calculate_synthetic_sentiment(st.session_state.ticker)
    if synth_data is not None and not synth_data.empty: render_synthetic_sentiment_panel(synth_data)
    render_detail_card_advanced(st.session_state.ticker)

    # --- SENTIMENT AJANI (STP) + SCROLLBAR ---
    st.markdown('<div class="info-header" style="margin-top: 15px; margin-bottom: 10px;">🕵️ Sentiment Ajanı (STP) Taraması</div>', unsafe_allow_html=True)
    with st.expander("STP Taramasını Başlat", expanded=True):
        if st.button(f"🔎 {st.session_state.category} İçin STP Tara", type="secondary"):
             with st.spinner("Ajan STP izini sürüyor..."):
                current_assets = ASSET_GROUPS.get(st.session_state.category, [])
                crosses, trends = scan_stp_signals(current_assets)
                st.session_state.stp_crosses = crosses; st.session_state.stp_trends = trends; st.session_state.stp_scanned = True
        
        if st.session_state.get('stp_scanned'):
            c_stp1, c_stp2 = st.columns(2)
            # --- SOL KUTU (YUKARI KESENLER) ---
            with c_stp1:
                st.markdown("###### ⚡ FİYATI STP YUKARI KESENLER")
                with st.container(height=200, border=True):
                    if st.session_state.stp_crosses:
                        cols = st.columns(3)
                        for i, item in enumerate(st.session_state.stp_crosses):
                            with cols[i % 3]:
                                if st.button(f"🚀 {item['Sembol']}\n({item['Fiyat']:.2f})", key=f"stp_c_{item['Sembol']}", use_container_width=True): 
                                    st.session_state.ticker = item['Sembol']
                                    st.rerun()
                    else: st.info("Yeni kesişim yok.")
            # --- SAĞ KUTU (TREND TAKİBİ) ---
            with c_stp2:
                st.markdown("###### ✅ 2 GÜNDÜR STP ÜSTÜNDE")
                with st.container(height=200, border=True):
                    if st.session_state.stp_trends:
                         cols = st.columns(3)
                         for i, item in enumerate(st.session_state.stp_trends):
                            with cols[i % 3]:
                                if st.button(f"📈 {item['Sembol']}\n%{item['Fark']:.1f}", key=f"stp_t_{item['Sembol']}", use_container_width=True): 
                                    st.session_state.ticker = item['Sembol']
                                    st.rerun()
                    else: st.info("Trend takibi yok.")

    # --- AJAN 3 ---
    st.markdown('<div class="info-header" style="margin-top: 15px; margin-bottom: 10px;">🕵️ Breakout Ajanı Taraması)</div>', unsafe_allow_html=True)
    with st.expander("Taramayı Başlat / Sonuçları Göster", expanded=True):
        if st.button(f"⚡ {st.session_state.category} Tara", type="primary", key="a3_main_scan_btn"):
            with st.spinner("Ajan 3 piyasayı kokluyor..."): st.session_state.agent3_data = agent3_breakout_scan(ASSET_GROUPS.get(st.session_state.category, []))
        if st.session_state.agent3_data is not None and not st.session_state.agent3_data.empty:
            display_df = st.session_state.agent3_data.head(12)
            st.caption(f"En sıcak {len(display_df)} fırsat listeleniyor (Toplam Bulunan: {len(st.session_state.agent3_data)})")
            for i, (index, row) in enumerate(display_df.iterrows()):
                if i % 3 == 0: cols = st.columns(3)
                with cols[i % 3]:
                    sym_raw = row.get("Sembol_Raw"); 
                    if not sym_raw: sym_raw = row.get("Sembol", row.name if isinstance(row.name, str) else "Bilinmiyor")
                    # ICT ve Tech verilerini çek
                    ict_vals = calculate_ict_deep_analysis(sym_raw) or {}; tech_vals = get_tech_card_data(sym_raw) or {}
                    target_text = ict_vals.get('target', 'Belirsiz'); stop_text = f"{tech_vals['stop_level']:.2f}" if tech_vals else "-"
                    is_short = "SHORT" in str(row.get('Sembol_Display', '')) or "SHORT" in str(row.get('Trend Durumu', ''))
                    if is_short: card_bg = "#fef2f2"; card_border = "#b91c1c"; btn_icon = "🔻"; signal_text = "SHORT"
                    else: card_bg = "#f0fdf4"; card_border = "#15803d"; btn_icon = "🚀"; signal_text = "LONG"
                    btn_label = f"{btn_icon} {signal_text} | {sym_raw} | {row['Fiyat']}"
                    if st.button(f"{btn_label}", key=f"a3_hdr_{sym_raw}_{i}", use_container_width=True): on_scan_result_click(sym_raw); st.rerun()
                    card_html = f"""<div class="info-card" style="margin-top: 0px; height: 100%; background-color: {card_bg}; border: 1px solid {card_border}; border-top: 3px solid {card_border};"><div class="info-row"><div class="label-short">Zirve:</div><div class="info-val">{row['Zirveye Yakınlık']}</div></div><div class="info-row"><div class="label-short">Hacim:</div><div class="info-val" style="color:#15803d;">{row['Hacim Durumu']}</div></div><div class="info-row"><div class="label-short">Trend:</div><div class="info-val">{row['Trend Durumu']}</div></div><div class="info-row"><div class="label-short">RSI:</div><div class="info-val">{row['RSI']}</div></div><div style="margin-top:8px; padding-top:4px; border-top:1px solid #e2e8f0; display:flex; justify-content:space-between; font-size:0.8rem;"><div style="color:#166534;"><strong>🎯</strong> {target_text}</div><div style="color:#991b1b;"><strong>🛑 Stop:</strong> {stop_text}</div></div></div>"""
                    st.markdown(card_html, unsafe_allow_html=True)
        elif st.session_state.agent3_data is not None: st.info("Kriterlere uyan hisse yok.")
    st.markdown(f"<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:20px;'>📡 {st.session_state.ticker} hakkında haberler ve analizler</div>", unsafe_allow_html=True)
    symbol_raw = st.session_state.ticker; base_symbol = (symbol_raw.replace(".IS", "").replace("=F", "").replace("-USD", "")); lower_symbol = base_symbol.lower()
    st.markdown(f"""<div class="news-card" style="display:flex; flex-wrap:wrap; align-items:center; gap:8px; border-left:none;"><a href="https://seekingalpha.com/symbol/{base_symbol}/news" target="_blank" style="text-decoration:none;"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.8rem; font-weight:600;">SeekingAlpha</div></a><a href="https://finance.yahoo.com/quote/{base_symbol}/news" target="_blank" style="text-decoration:none;"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.8rem; font-weight:600;">Yahoo Finance</div></a><a href="https://www.nasdaq.com/market-activity/stocks/{lower_symbol}/news-headlines" target="_blank" style="text-decoration:none;"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.8rem; font-weight:600;">Nasdaq</div></a><a href="https://stockanalysis.com/stocks/{lower_symbol}/" target="_blank" style="text-decoration:none;"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.8rem; font-weight:600;">StockAnalysis</div></a><a href="https://finviz.com/quote.ashx?t={base_symbol}&p=d" target="_blank" style="text-decoration:none;"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.8rem; font-weight:600;">Finviz</div></a><a href="https://unusualwhales.com/stock/{base_symbol}/overview" target="_blank" style="text-decoration:none;"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.7rem; font-weight:600;">UnusualWhales</div></a></div>""", unsafe_allow_html=True)

# --- SAĞ SÜTUN (Fiyat, Sentiment, ICT, Tarama) ---
with col_right:
    # FİYAT KUTUSU (GÜNCELLENDİ: Hisse Adı Eklendi)
    if info and info['price']:
        # Hisse adını temizle (örn: AKBNK.IS -> AKBNK)
        display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")
        
        cls = "delta-pos" if info['change_pct'] >= 0 else "delta-neg"
        # Label kısmına {display_ticker} ekledim
        st.markdown(f'<div class="stat-box-small" style="margin-bottom:10px;"><p class="stat-label-small">FİYAT: {display_ticker}</p><p class="stat-value-small money-text">{info["price"]:.2f}<span class="stat-delta-small {cls}">{"+" if info["change_pct"]>=0 else ""}{info["change_pct"]:.2f}%</span></p></div>', unsafe_allow_html=True)

    sent_data = calculate_sentiment_score(st.session_state.ticker)
    render_sentiment_card(sent_data)
    
    # --- YENİ ICT PANELİ BURADA ---
    render_ict_deep_panel(st.session_state.ticker)
    
    xray_data = get_deep_xray_data(st.session_state.ticker)
    render_deep_xray_card(xray_data)
    
    st.markdown(f"<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:10px; color:#1e40af; background-color:{current_theme['box_bg']}; padding:5px; border-radius:5px; border:1px solid #1e40af;'>🎯 Ortak Fırsatlar</div>", unsafe_allow_html=True)
    with st.container(height=250):
        df1 = st.session_state.scan_data; df2 = st.session_state.radar2_data
        if df1 is not None and df2 is not None and not df1.empty and not df2.empty:
            commons = []; symbols = set(df1["Sembol"]).intersection(set(df2["Sembol"]))
            if symbols:
                for sym in symbols:
                    row1 = df1[df1["Sembol"] == sym].iloc[0]; row2 = df2[df2["Sembol"] == sym].iloc[0]
                    r1_score = float(row1["Skor"]); r2_score = float(row2["Skor"]); combined_score = r1_score + r2_score
                    commons.append({"symbol": sym, "r1_score": r1_score, "r2_score": r2_score, "combined": combined_score, "r1_max": 8, "r2_max": 8})
                sorted_commons = sorted(commons, key=lambda x: x["combined"], reverse=True)
                
                # --- ORTAK FIRSATLAR GÜNCELLENDİ (2 SÜTUN, YILDIZ YOK) ---
                cols = st.columns(2) 
                for i, item in enumerate(sorted_commons):
                    sym = item["symbol"]
                    if i == 0: rank = "🥇"
                    elif i == 1: rank = "🥈"
                    elif i == 2: rank = "🥉"
                    else: rank = f"{i+1}."
                    
                    score_text_safe = f"{rank} {sym} ({int(item['combined'])})"
                    
                    with cols[i % 2]:
                        if st.button(f"{score_text_safe} | R1:{int(item['r1_score'])} R2:{int(item['r2_score'])}", key=f"c_select_{sym}", help="Detaylar için seç", use_container_width=True): 
                            on_scan_result_click(sym); st.rerun()
            else: st.info("Kesişim yok.")
        else: st.caption("İki radar da çalıştırılmalı.")
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # İki Tablo Yapısı (İzleme sekmesi kaldırıldı)
    tab1, tab2 = st.tabs(["🧠 RADAR 1", "🚀 RADAR 2"])
    
    # --- RADAR 1 ---
    with tab1:
        if st.button(f"⚡ {st.session_state.category} Tara", type="primary", key="r1_main_scan_btn"):
            with st.spinner("Taranıyor..."): st.session_state.scan_data = analyze_market_intelligence(ASSET_GROUPS.get(st.session_state.category, []))
        
        if st.session_state.scan_data is not None:
            with st.container(height=250):
                cols = st.columns(2)
                for i, (index, row) in enumerate(st.session_state.scan_data.iterrows()):
                    sym = row["Sembol"]
                    with cols[i % 2]:
                        if st.button(f"🔥 {row['Skor']}/8 | {sym}", key=f"r1_b_{i}", use_container_width=True):
                            on_scan_result_click(sym)
                            st.rerun()

    # --- RADAR 2 ---
    with tab2:
        if st.button(f"🚀 RADAR 2 Tara", type="primary", key="r2_main_scan_btn"):
            with st.spinner("Taranıyor..."): st.session_state.radar2_data = radar2_scan(ASSET_GROUPS.get(st.session_state.category, []))
        
        if st.session_state.radar2_data is not None:
            with st.container(height=250):
                cols = st.columns(2)
                for i, (index, row) in enumerate(st.session_state.radar2_data.iterrows()):
                    sym = row["Sembol"]
                    with cols[i % 2]:
                        if st.button(f"🚀 {row['Skor']}/8 | {sym} | {row['Setup']}", key=f"r2_b_{i}", use_container_width=True):
                            on_scan_result_click(sym)
                            st.rerun()



