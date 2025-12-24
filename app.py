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

# Tema seçeneği
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
    section[data-testid="stSidebar"] {{ width: 350px !important; }}
    div[data-testid="stMetricValue"] {{ font-size: 0.7rem !important; }}
    div[data-testid="stMetricLabel"] {{ font-size: 0.7rem !important; font-weight: 700; }}
    div[data-testid="stMetricDelta"] {{ font-size: 0.7rem !important; }}
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght+400;700&display=swap');
    
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {current_theme['text']}; }}
    .stApp {{ background-color: {current_theme['bg']}; }}
    
    section.main > div.block-container {{ padding-top: 1rem; padding-bottom: 1rem; }}
    
    .stMetricValue, .money-text {{ font-family: 'JetBrains Mono', monospace !important; }}
    
    .stat-box-small {{
        background: {current_theme['box_bg']}; border: 1px solid {current_theme['border']};
        border-radius: 4px; padding: 8px; text-align: center; margin-bottom: 10px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }}
    .stat-label-small {{ font-size: 0.6rem; color: #64748B; text-transform: uppercase; margin: 0; font-weight: 700; letter-spacing: 0.5px; }}
    .stat-value-small {{ font-size: 1.1rem; font-weight: 700; color: {current_theme['text']}; margin: 2px 0 0 0; }}
    .stat-delta-small {{ font-size: 0.8rem; margin-left: 6px; font-weight: 600; }}
    
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

init_db()

# --- VARLIK LİSTELERİ ---
priority_sp = ["^GSPC", "^DJI", "^NDX", "^IXIC", "AGNC", "ARCC", "PFE", "JEPI", "MO", "EPD", "JEPQ"]

raw_sp500_rest = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "LLY", "AVGO", "JPM", "V", "XOM", "UNH", "MA", "PG", "JNJ", "HD", "MRK", "COST", "ABBV", "CVX", "CRM", "AMD", "WMT", "PEP", "BAC", "ACN", "NFLX", "LIN", "ADBE", "MCD", "DIS", "CSCO", "TMO", "ABT", "INTU", "QCOM", "TXN", "DHR", "CAT", "VZ", "AMGN", "IBM", "PM", "GE", "NKE", "INTC", "LOW", "SPGI", "HON", "UPS", "COP", "RTX", "UNP", "AXP", "AMAT", "PFE", "GS", "NEE", "BA", "BLK", "BMY", "ELV", "TJX", "MDLZ", "MS", "SYK", "SBUX", "ISRG", "ADI", "ADP", "DE", "GILD", "LMT", "VRTX", "BKNG", "PLD", "LRCX", "SCHW", "MMC", "T", "C", "ZTS", "UBER", "REGN", "CI", "CVS", "MO", "PGR", "FI", "SO", "SLB", "BDX", "BSX", "KLAC", "SNPS", "EOG", "TMUS", "CME", "EQIX", "CDNS", "PANW", "ATVI", "MU", "WM", "ITW", "CSX", "CL", "SHW", "NOC", "ORCL", "CMCSA", "GWW", "MCO", "ETN", "MAR", "APH", "AON", "PYPL", "ICE", "FDX", "FCX", "TGT", "HUM", "NXPI", "MCK", "PSA", "EMR", "USB", "PNC", "DUK", "APD", "ECL", "ORLY", "MCHP", "ROP", "NSC", "GD", "PSX", "PH", "GM", "COF", "TRV", "ADSK", "AEP", "SRE", "TT", "AZO", "EW", "KMB", "MSI", "O", "AJG", "HCA", "TEL", "WELL", "MET", "AFL", "VLO", "PCAR", "D", "IDXX", "PAYX", "JCI", "CHTR", "CARR", "AIG", "ROST", "CTAS", "STZ", "FIS", "EXC", "HLT", "ALL", "TRGP", "KMI", "WMB", "YUM", "EA", "DHI", "XEL", "KDP", "PRU", "GPN", "MNST", "PEG", "IQV", "FAST", "CTVA", "BK", "ED", "OXY", "KR", "SYY", "WEC", "RSG", "ODFL", "DLTR", "LHX", "HPQ", "GEHC", "ROK", "CPRT", "KHC", "BKR", "VICI", "MPWR", "OTIS", "VMC", "COR", "CMI", "DFS", "AWK", "CSGP", "HES", "PCG", "MTD", "AMP", "ON", "ILMN", "AME", "IR", "IT", "VRSK", "WAB", "OKE", "HAL", "SBAC", "DVN", "EFX", "CTSH", "GLW", "MTB", "ULTA", "EIX", "PPG", "HIG", "FITB", "CBRE", "TSCO", "HPE", "F", "DAL", "CDW", "DOV", "KEYS", "ZBH", "WST", "STT", "XYL", "TROW", "GIB", "FSLR", "ARE", "LUV", "RJF", "EBAY", "ETR", "FE", "CAH", "NTAP", "EXR", "VTR", "BIIB", "WRB", "CMS", "RF", "MAA", "CNP", "HBAN", "ESS", "EXPE", "PFG", "PEAK", "ATO", "PKG", "TRMB", "KEY", "CF", "WAB", "LYB", "BBY", "TDG", "OMC", "MKC", "STE", "ZBRA", "HOLX", "DGX", "COO", "TXT", "DRI", "AVY", "MAS", "IEX", "EVRG", "ATO", "AKAM", "SWKS", "EXPD", "POOL", "CINF", "J", "L", "SJM", "K", "BRO", "TYL", "NDSN", "FMC", "CE", "JBHT", "LDOS", "NTRS", "SNA", "DPZ", "VRSN", "TXT", "CHRW", "IP", "SWK", "UHS", "TAP", "HST", "UDR", "CPB", "KMX", "NRG", "AES", "NI", "PNR", "HRL", "BWA", "BEN", "LNC", "L", "NWL", "DISH", "MHK", "ALK", "VNO", "RL", "FOX", "FOXA", "NWS", "NWSA", "SEE"
]

# Kopyaları Temizle ve Birleştir
raw_sp500_rest = list(set(raw_sp500_rest) - set(priority_sp))
raw_sp500_rest.sort()
final_sp500_list = priority_sp + raw_sp500_rest

priority_crypto = ["BTC-USD", "ETH-USD"]
other_crypto = ["BNB-USD", "SOL-USD", "XRP-USD", "ADA-USD", "DOGE-USD", "AVAX-USD", "TRX-USD", "LINK-USD", "DOT-USD", "MATIC-USD", "LTC-USD", "BCH-USD", "UNI-USD", "ATOM-USD", "XLM-USD", "ETC-USD", "FIL-USD", "HBAR-USD", "APT-USD", "NEAR-USD", "VET-USD", "QNT-USD", "AAVE-USD", "ALGO-USD"]
other_crypto.sort()
final_crypto_list = priority_crypto + other_crypto

raw_nasdaq = ["AAPL", "MSFT", "NVDA", "AMZN", "AVGO", "META", "TSLA", "GOOGL", "GOOG", "COST", "NFLX", "AMD", "PEP", "LIN", "TMUS", "CSCO", "QCOM", "INTU", "AMAT", "TXN", "HON", "AMGN", "BKNG", "ISRG", "CMCSA", "SBUX", "MDLZ", "GILD", "ADP", "ADI", "REGN", "VRTX", "LRCX", "PANW", "MU", "KLAC", "SNPS", "CDNS", "MELI", "MAR", "ORLY", "CTAS", "NXPI", "CRWD", "CSX", "PCAR", "MNST", "WDAY", "ROP", "AEP", "ROKU", "ZS", "OKTA", "TEAM", "DDOG", "MDB", "SHOP", "EA", "TTD", "DOCU", "INTC", "SGEN", "ILMN", "IDXX", "ODFL", "EXC", "ADSK", "PAYX", "CHTR", "MRVL", "KDP", "XEL", "LULU", "ALGN", "VRSK", "CDW", "DLTR", "SIRI", "JBHT", "WBA", "PDD", "JD", "BIDU", "NTES", "NXST", "MTCH", "UAL", "SPLK", "ANSS", "SWKS", "QRVO", "AVTR", "FTNT", "ENPH", "SEDG", "BIIB", "CSGP"]
raw_nasdaq = sorted(list(set(raw_nasdaq)))

# --- BIST 100 LİSTESİ ---
priority_bist_indices = ["XU100.IS", "XU030.IS", "XBANK.IS", "EREGL.IS", "SISE.IS", "TUPRS.IS"]
raw_bist_stocks = ["AEFES.IS", "AGHOL.IS", "AHGAZ.IS", "AKBNK.IS", "AKCNS.IS", "AKFGY.IS", "AKFYE.IS", "AKSA.IS", "AKSEN.IS", "ALARK.IS", "ALBRK.IS", "ALFAS.IS", "ANSGR.IS", "ARCLK.IS", "ASELS.IS", "ASTOR.IS", "BERA.IS", "BIMAS.IS", "BIOEN.IS", "BOBET.IS", "BRSAN.IS", "BRYAT.IS", "BUCIM.IS", "CANTE.IS", "CCOLA.IS", "CEMTS.IS", "CIMSA.IS", "CWENE.IS", "DOAS.IS", "DOHOL.IS", "ECILC.IS", "ECZYT.IS", "EGEEN.IS", "EKGYO.IS", "ENJSA.IS", "ENKAI.IS", "EUREN.IS", "EUPWR.IS", "FENER.IS", "FROTO.IS", "GARAN.IS", "GENIL.IS", "GESAN.IS", "GLYHO.IS", "GOKNR.IS", "GUBRF.IS", "GWIND.IS", "HALKB.IS", "HEKTS.IS", "IPEKE.IS", "ISCTR.IS", "ISDMR.IS", "ISGYO.IS", "ISMEN.IS", "IZENR.IS", "KCAER.IS", "KCHOL.IS", "KLSER.IS", "KONTR.IS", "KONYA.IS", "KORDS.IS", "KOZAA.IS", "KOZAL.IS", "KRDMD.IS", "KZBGY.IS", "MAVI.IS", "MGROS.IS", "MIATK.IS", "ODAS.IS", "OTKAR.IS", "OYAKC.IS", "PENTA.IS", "PETKM.IS", "PGSUS.IS", "PSGYO.IS", "QUAGR.IS", "REEDR.IS", "SAHOL.IS", "SASA.IS", "SDTTR.IS", "SKBNK.IS", "SMRTG.IS", "SOKM.IS", "TABGD.IS", "TAVHL.IS", "TCELL.IS", "THYAO.IS", "TKFEN.IS", "TOASO.IS", "TSKB.IS", "TTKOM.IS", "TTRAK.IS", "TUKAS.IS", "TURSG.IS", "ULUUN.IS", "VAKBNK.IS", "VESBE.IS", "VESTL.IS", "YEOTK.IS", "YKBNK.IS", "YLALI.IS", "ZOREN.IS"]
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
if 'agent3_data' not in st.session_state: st.session_state.agent3_data = None
if 'watchlist' not in st.session_state: st.session_state.watchlist = load_watchlist_db()
if 'stp_scanned' not in st.session_state: st.session_state.stp_scanned = False
if 'stp_crosses' not in st.session_state: st.session_state.stp_crosses = []
if 'stp_trends' not in st.session_state: st.session_state.stp_trends = []
if 'stp_filtered' not in st.session_state: st.session_state.stp_filtered = []
if 'accum_data' not in st.session_state: st.session_state.accum_data = None
if 'breakout_left' not in st.session_state: st.session_state.breakout_left = None
if 'breakout_right' not in st.session_state: st.session_state.breakout_right = None
# YENİ AJAN STATE'LERİ
if 'harsi_data' not in st.session_state: st.session_state.harsi_data = None

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
        st.session_state.accum_data = None 
        st.session_state.breakout_left = None
        st.session_state.breakout_right = None
        st.session_state.harsi_data = None

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

# --- GLOBAL DATA CACHE KATMANI ---
@st.cache_data(ttl=3600, show_spinner=False)
def get_batch_data_cached(asset_list, period="1y", interval="1d"):
    if not asset_list: return pd.DataFrame()
    try:
        tickers_str = " ".join(asset_list)
        data = yf.download(tickers_str, period=period, interval=interval, group_by='ticker', threads=True, progress=False, auto_adjust=False)
        return data
    except Exception: return pd.DataFrame()

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
    try:
        if df.empty or 'Close' not in df.columns: return None
        df = df.dropna(subset=['Close'])
        if len(df) < 200: return None

        close = df['Close']; high = df['High']; low = df['Low']
        
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

def process_single_accumulation(symbol, df):
    try:
        if df.empty or 'Close' not in df.columns: return None
        df = df.dropna(subset=['Close'])
        if len(df) < 15: return None

        close = df['Close']
        volume = df['Volume'] if 'Volume' in df.columns else pd.Series([1]*len(df), index=df.index)
        
        delta = close.diff()
        force_index = delta * volume
        mf_smooth = force_index.ewm(span=5, adjust=False).mean()

        last_10_mf = mf_smooth.tail(10)
        last_10_close = close.tail(10)
        
        if len(last_10_mf) < 10: return None
        
        pos_days_count = (last_10_mf > 0).sum()
        if pos_days_count < 7: return None

        price_start = float(last_10_close.iloc[0]) 
        price_now = float(last_10_close.iloc[-1])
        
        if price_start == 0: return None
        
        change_pct = (price_now - price_start) / price_start
        avg_mf = float(last_10_mf.mean())
        
        if avg_mf <= 0: return None
        if change_pct > 0.035: return None 

        score_multiplier = 10.0 if change_pct < 0 else 5.0 if change_pct < 0.015 else 1.0
        final_score = avg_mf * score_multiplier

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
            "Skor": squeeze_score
        }
    except: return None

@st.cache_data(ttl=900)
def scan_hidden_accumulation(asset_list):
    data = get_batch_data_cached(asset_list, period="1mo")
    if data.empty: return pd.DataFrame()

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

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(process_single_accumulation, sym, df) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: results.append(res)

    if results: return pd.DataFrame(results).sort_values(by="Skor", ascending=False)
    return pd.DataFrame()

def process_single_radar1(symbol, df):
    try:
        if df.empty or 'Close' not in df.columns: return None
        df = df.dropna(subset=['Close'])
        if len(df) < 60: return None
        
        close = df['Close']; high = df['High']; low = df['Low']
        volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))
        
        ema5 = close.ewm(span=5, adjust=False).mean()
        ema20 = close.ewm(span=20, adjust=False).mean()
        sma20 = close.rolling(20).mean(); std20 = close.rolling(20).std()
        
        bb_width = ((sma20 + 2*std20) - (sma20 - 2*std20)) / (sma20 - 0.0001)

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        hist = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()
        
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain / loss)))
        
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
        
        if bb_width.iloc[-1] <= bb_width.tail(60).min() * 1.1: score += 1; reasons.append("🚀 Squeeze"); details['Squeeze'] = True
        else: details['Squeeze'] = False
        
        if ((ema5.iloc[-1] > ema20.iloc[-1]) and (ema5.iloc[-2] <= ema20.iloc[-2])) or ((ema5.iloc[-2] > ema20.iloc[-2]) and (ema5.iloc[-3] <= ema20.iloc[-3])): score += 1; reasons.append("⚡ Trend"); details['Trend'] = True
        else: details['Trend'] = False
        
        if hist.iloc[-1] > hist.iloc[-2]: score += 1; reasons.append("🟢 MACD"); details['MACD'] = True
        else: details['MACD'] = False
        
        if curr_vol > avg_vol * 1.2: score += 1; reasons.append("🔊 Hacim"); details['Hacim'] = True
        else: details['Hacim'] = False
        
        if curr_c >= high.tail(20).max() * 0.98: score += 1; reasons.append("🔨 Breakout"); details['Breakout'] = True
        else: details['Breakout'] = False
        
        rsi_c = float(rsi.iloc[-1])
        if 30 < rsi_c < 65 and rsi_c > float(rsi.iloc[-2]): score += 1; reasons.append("⚓ RSI Güçlü"); details['RSI Güçlü'] = (True, rsi_c)
        else: details['RSI Güçlü'] = (False, rsi_c)
        
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
        
        if curr_c < min_price or curr_c > max_price: return None
        avg_vol_20 = float(volume.rolling(20).mean().iloc[-1])
        if avg_vol_20 < min_avg_vol_m * 1e6: return None
        
        sma20 = close.rolling(20).mean(); sma50 = close.rolling(50).mean()
        sma100 = close.rolling(100).mean(); sma200 = close.rolling(200).mean()
        
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
        
        tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
        kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
        span_a_calc = (tenkan + kijun) / 2
        span_b_calc = (high.rolling(52).max() + low.rolling(52).min()) / 2
        cloud_a = float(span_a_calc.iloc[-26])
        cloud_b = float(span_b_calc.iloc[-26])
        is_above_cloud = curr_c > max(cloud_a, cloud_b)

        setup = "-"; tags = []; score = 0; details = {}
        avg_vol_20 = max(avg_vol_20, 1); vol_spike = volume.iloc[-1] > avg_vol_20 * 1.3
        
        if trend == "Boğa" and breakout_ratio >= 0.97: setup = "Breakout"; tags.append("Zirve")
        if trend == "Boğa" and setup == "-":
            if sma20.iloc[-1] <= curr_c <= sma50.iloc[-1] * 1.02 and 40 <= rsi_c <= 55: setup = "Pullback"; tags.append("Düzeltme")
            if volume.iloc[-1] < avg_vol_20 * 0.9: score += 0; tags.append("Sığ Satış")
        if setup == "-":
            if rsi.iloc[-2] < 30 <= rsi_c and hist.iloc[-1] > hist.iloc[-2]: setup = "Dip Dönüşü"; tags.append("Dip Dönüşü")
        
        if vol_spike: score += 1; tags.append("Hacim+"); details['Hacim Patlaması'] = True
        else: details['Hacim Patlaması'] = False

        if rs_score > 0: score += 1; tags.append("RS+"); details['RS (S&P500)'] = True
        else: details['RS (S&P500)'] = False
        
        if trend == "Boğa": score += 1; details['Boğa Trendi'] = True
        else:
            if trend == "Ayı": score -= 1
            details['Boğa Trendi'] = False
            
        if is_above_cloud: score += 1; details['Ichimoku'] = True
        else: details['Ichimoku'] = False

        details['60G Zirve'] = breakout_ratio >= 0.90
        if details['60G Zirve']: score += 1

        is_rsi_suitable = (40 <= rsi_c <= 65)
        details['RSI Bölgesi'] = (is_rsi_suitable, rsi_c)
        if is_rsi_suitable: score += 1
        
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
# 4. GÖREV: KAMA & HARSI 3H AJANI
# ==============================================================================

def calculate_kama_pandas(series, n=20, pow1=2, pow2=30):
    """Pandas ile Kaufman Adaptive Moving Average hesaplar."""
    # Efficiency Ratio
    change = abs(series - series.shift(n))
    volatility = abs(series - series.shift(1)).rolling(n).sum()
    er = change / volatility
    # Smoothing Constant
    sc = (er * (2/(pow1+1) - 2/(pow2+1)) + 2/(pow2+1)) ** 2
    # KAMA Recurive Calculation
    kama = np.zeros_like(series)
    kama[:] = np.nan
    
    # İlk değer (n. indeks) basit SMA veya fiyat olabilir
    start_idx = n
    if start_idx >= len(series): return pd.Series(kama, index=series.index)
    
    kama[start_idx] = series.iloc[start_idx]
    
    series_values = series.values
    sc_values = sc.values
    
    # Döngüsel hesaplama (Vectorize edilemez çünkü bir önceki KAMA'ya bağlı)
    for i in range(start_idx + 1, len(series)):
        val = kama[i-1] + sc_values[i] * (series_values[i] - kama[i-1])
        if not np.isnan(val):
            kama[i] = val
        else:
            kama[i] = kama[i-1] # Fallback if NaN appears
            
    return pd.Series(kama, index=series.index)

def calculate_heikin_ashi(df):
    """Standart Heikin Ashi Mumları Hesaplar."""
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = np.zeros_like(ha_close)
    ha_open[0] = df['Open'].iloc[0] # İlk değer
    
    # HA Open Recurive
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
        
    ha_open = pd.Series(ha_open, index=df.index)
    ha_high = pd.concat([df['High'], ha_open, ha_close], axis=1).max(axis=1)
    ha_low = pd.concat([df['Low'], ha_open, ha_close], axis=1).min(axis=1)
    
    return pd.DataFrame({'Open': ha_open, 'High': ha_high, 'Low': ha_low, 'Close': ha_close})

def process_single_harsi_agent(symbol, df_1h):
    try:
        # 1. 1h Veriyi 3h'a Resample Et (Aggregasyon)
        # yfinance verisi DatetimeIndex olmalı
        if df_1h.empty: return None
        
        # Resample işlemi
        df_3h = df_1h.resample('3h').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
        if len(df_3h) < 60: return None # Yeterli veri yoksa
        
        close = df_3h['Close']
        
        # 2. İndikatörler
        # EMA9
        ema9 = close.ewm(span=9, adjust=False).mean()
        
        # KAMA (20-2-30)
        kama = calculate_kama_pandas(close, n=20, pow1=2, pow2=30)
        
        # RSI 14
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # RSI SMA 50 (RSI'ın 50'lik ortalaması)
        rsi_sma50 = rsi.rolling(50).mean()
        
        # HARSI (RSI Değerlerinden HA Mumu Üretme)
        # RSI serisini bir DataFrame gibi düşünüp HA hesaplayacağız.
        # Open, High, Low, Close hepsi RSI değeri gibi davranır.
        # Standart HARSI hesaplaması:
        # HA_Close = RSI
        # HA_Open = (Prev_HA_Open + Prev_HA_Close) / 2
        # HA_High = Max(RSI, HA_Open, HA_Close)
        # HA_Low = Min(RSI, HA_Open, HA_Close)
        # Basitlik için RSI serisini alıp HA fonksiyonuna sokamayız çünkü OHLC yok.
        # Bu yüzden manuel hesaplıyoruz:
        
        harsi_close = rsi
        harsi_open = np.zeros_like(rsi)
        harsi_open[0] = rsi.iloc[0]
        # RSI array
        rsi_vals = rsi.values
        
        for i in range(1, len(rsi)):
            harsi_open[i] = (harsi_open[i-1] + rsi_vals[i-1]) / 2
            
        harsi_open_s = pd.Series(harsi_open, index=rsi.index)
        
        # HARSI Mum Renkleri (Yeşil: Close > Open)
        harsi_green = harsi_close > harsi_open_s
        
        # 3. KONTROLLER (Son Mumlar)
        # İndeksler: -1 (Son Mum), -2 (Önceki), -3 (Daha Önceki)
        
        c_last = close.iloc[-1]; c_prev = close.iloc[-2]
        ema9_last = ema9.iloc[-1]; ema9_prev = ema9.iloc[-2]
        kama_last = kama.iloc[-1]; kama_prev = kama.iloc[-2]
        
        # Şart 1: Fiyat EMA9 üstüne atmış ve 2 kapanış üstünde
        # Yorum: Son 2 mumun kapanışı EMA9 üzerinde olmalı.
        cond1 = (c_last > ema9_last) and (c_prev > ema9_prev)
        
        # Şart 2: 2 kapanış KAMA (20-2-30) üzerinde
        cond2 = (c_last > kama_last) and (c_prev > kama_prev)
        
        # Şart 3: RSI 14 > RSI SMA 50
        cond3 = rsi.iloc[-1] > rsi_sma50.iloc[-1]
        
        # Şart 4: HARSI mumları 3 kez üst üste yeşil
        cond4 = harsi_green.iloc[-1] and harsi_green.iloc[-2] and harsi_green.iloc[-3]
        
        # Şart 5: RSI 14 mumların üzerinde (RSI Line > HARSI Open/Close/High? Genelde RSI > HARSI Open denir veya RSI line kendisi zaten HA Close'dur.)
        # Kullanıcının talebi: "RSI 14 mumların üzerindeyse" -> RSI çizgisinin HA gövdesinin üstünde olması.
        # HARSI Close zaten RSI'dır. O yüzden bu koşul genelde "RSI > HA Open" demektir (Yeşil mum teyidi).
        # Ya da RSI > RSI_SMA ile benzerdir. Biz direkt talebi uygulayalım: RSI > HARSI Open.
        cond5 = rsi.iloc[-1] > harsi_open_s.iloc[-1]
        
        if cond1 and cond2 and cond3 and cond4 and cond5:
            return {
                "Sembol": symbol,
                "Fiyat": f"{c_last:.2f}",
                "RSI": f"{rsi.iloc[-1]:.1f}",
                "HARSI": "3x🟢",
                "KAMA": f"{kama_last:.2f}",
                "EMA9": f"{ema9_last:.2f}"
            }
        
        return None
        
    except Exception: return None

@st.cache_data(ttl=900)
def scan_agent3_harsi(asset_list):
    # 1h Veri çekiyoruz (3h oluşturmak için)
    # 730 gün (2 yıl) saatlik veri limiti
    data = get_batch_data_cached(asset_list, period="730d", interval="1h")
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
        futures = [executor.submit(process_single_harsi_agent, sym, df) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: results.append(res)
            
    return pd.DataFrame(results)

# ==============================================================================
# Diğer Helper Fonksiyonlar (Sentiment vb.)
# ==============================================================================

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
        
        bars = int(total / 5)
        bar_str = "【" + "█" * bars + "░" * (20 - bars) + "】"
        
        def fmt(lst): 
            if not lst: return ""
            content = " + ".join(lst)
            return f"<span style='font-size:0.7rem; color:#334155; font-style:italic; font-weight:300;'>({content})</span>"
        
        return {
            "total": total, "bar": bar_str, 
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

# ==============================================================================
# 5. GÖRSELLEŞTİRME
# ==============================================================================

def render_sentiment_card(sent):
    if not sent: return
    display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")
    
    score = sent['total']
    if score >= 70: color = "#16a34a"; icon = "🔥"; status = "GÜÇLÜ BOĞA"
    elif score >= 50: color = "#d97706"; icon = "↔️"; status = "NÖTR / POZİTİF"
    elif score >= 30: color = "#b91c1c"; icon = "🐻"; status = "ZAYIF / AYI"
    else: color = "#7f1d1d"; icon = "❄️"; status = "ÇÖKÜŞ"
    
    html_content = f"""
    <div class="info-card">
        <div class="info-header">🎭 Smart Money Duygusu: {display_ticker}</div>
        
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
        <div class="info-row"><div class="label-long">1. Momentum:</div><div class="info-val">{xray['mom_rsi']} | {xray['mom_macd']}</div></div>
        <div class="info-row"><div class="label-long">2. Hacim Akışı:</div><div class="info-val">{xray['vol_obv']}</div></div>
        <div class="info-row"><div class="label-long">3. Trend Sağlığı:</div><div class="info-val">{xray['tr_ema']} | {xray['tr_adx']}</div></div>
        <div class="info-row"><div class="label-long">4. Volatilite:</div><div class="info-val">{xray['vola_bb']}</div></div>
        <div class="info-row"><div class="label-long">5. Piyasa Yapısı:</div><div class="info-val">{xray['str_bos']}</div></div>
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

    r1_res = {}; r1_score = 0
    if st.session_state.scan_data is not None:
        row = st.session_state.scan_data[st.session_state.scan_data["Sembol"] == ticker]
        if not row.empty and "Detaylar" in row.columns: r1_res = row.iloc[0]["Detaylar"]; r1_score = row.iloc[0]["Skor"]
    if not r1_res:
        temp_df = analyze_market_intelligence([ticker])
        if not temp_df.empty and "Detaylar" in temp_df.columns: r1_res = temp_df.iloc[0]["Detaylar"]; r1_score = temp_df.iloc[0]["Skor"]

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

    r1_html = ""
    for k, v in r1_res.items():
        if k in ACIKLAMALAR: 
            text = ACIKLAMALAR.get(k, k); is_valid = v
            if isinstance(v, (tuple, list)): 
                is_valid = v[0]; val_num = v[1]
                if k == "RSI Güçlü": text = f"⚓ RSI Güçlü: ({int(val_num)})"
                elif k == "ADX Durumu": text = f"💪 ADX Güçlü: {int(val_num)}" if is_valid else f"⚠️ ADX Zayıf: {int(val_num)}"
            r1_html += f"<div class='tech-item' style='margin-bottom:2px;'>{get_icon(is_valid)} <span style='margin-left:4px;'>{text}</span></div>"

    r2_html = ""
    for k, v in r2_res.items():
        if k in ACIKLAMALAR:
            text = ACIKLAMALAR.get(k, k); is_valid = v
            if isinstance(v, (tuple, list)): 
                is_valid = v[0]; val_num = v[1]
                if k == "RSI Bölgesi": text = f"🎯 RSI Uygun: ({int(val_num)})"
            if k == "Ichimoku": pass 
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
            <div style="font-weight:700; color:#0369a1; font-size:0.75rem; margin-bottom:4px;">🧠 RADAR 1 Kısa Vade - Skor: {r1_score}/7{r1_suffix}</div>
            <div class="tech-grid" style="font-size:0.75rem;">{r1_html}</div>
        </div>
        <div style="background:#f0fdf4; padding:4px; border-radius:4px;">
            <div style="font-weight:700; color:#15803d; font-size:0.75rem; margin-bottom:4px;">🚀 RADAR 2 Orta Vade - Skor: {r2_score}/7</div>
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
        color_condition = alt.condition(alt.datum.MF_Smooth > 0, alt.value("#3b82f6"), alt.value("#ef4444"))
        bars = base.mark_bar(size=15, opacity=0.9).encode(y=alt.Y('MF_Smooth:Q', axis=alt.Axis(title='Para Akışı (Güç)', labels=False, titleColor='#4338ca')), color=color_condition, tooltip=['Date_Str', 'Price', 'MF_Smooth'])
        price_line = base.mark_line(color='#1e40af', strokeWidth=2).encode(y=alt.Y('Price:Q', scale=alt.Scale(zero=False), axis=alt.Axis(title='Fiyat', titleColor='#0f172a')))
        st.altair_chart(alt.layer(bars, price_line).resolve_scale(y='independent').properties(height=280, title=alt.TitleParams("Momentum", fontSize=14, color="#1e40af")), use_container_width=True)
    with c2:
        base2 = alt.Chart(data).encode(x=x_axis)
        line_stp = base2.mark_line(color='#fbbf24', strokeWidth=3).encode(y=alt.Y('STP:Q', scale=alt.Scale(zero=False), axis=alt.Axis(title='Fiyat', titleColor='#64748B')), tooltip=['Date_Str', 'STP', 'Price'])
        line_price = base2.mark_line(color='#2563EB', strokeWidth=2).encode(y='Price:Q')
        area = base2.mark_area(opacity=0.15, color='gray').encode(y='STP:Q', y2='Price:Q')
        st.altair_chart(alt.layer(area, line_stp, line_price).properties(height=280, title=alt.TitleParams("EMA6 Analizi: Mavi (Fiyat) Sarıyı (STP) Yukarı Keserse AL", fontSize=14, color="#1e40af")), use_container_width=True)

# ==============================================================================
# 6. SIDEBAR UI
# ==============================================================================
with st.sidebar:
    st.markdown(f"""<div style="font-size:1.5rem; font-weight:700; color:#1e3a8a; text-align:center; padding-top: 10px; padding-bottom: 10px;">SMART MONEY RADAR</div><hr style="border:0; border-top: 1px solid #e5e7eb; margin-top:5px; margin-bottom:10px;">""", unsafe_allow_html=True)
    
    sentiment_verisi = calculate_sentiment_score(st.session_state.ticker)
    if sentiment_verisi:
        render_sentiment_card(sentiment_verisi)

    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    
    xray_verisi = get_deep_xray_data(st.session_state.ticker)
    if xray_verisi:
        render_deep_xray_card(xray_verisi)
    else:
        st.caption("Röntgen verisi şu an hazırlanamıyor.")

    st.divider()
    with st.expander("🤖 AI Analist (Prompt)", expanded=True):
        st.caption("Verileri toplayıp ChatGPT için hazır metin oluşturur.")
        if st.button("📋 Analiz Metnini Hazırla", type="primary"): 
            st.session_state.generate_prompt = True

# ==============================================================================
# 7. ANA SAYFA (MAIN UI)
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
    sent_data = calculate_sentiment_score(t) or {}
    radar_val = "Veri Yok"
    if st.session_state.radar2_data is not None:
        r_row = st.session_state.radar2_data[st.session_state.radar2_data['Sembol'] == t]
        if not r_row.empty: radar_val = f"{r_row.iloc[0]['Skor']}/8"
    
    prompt = f"Analiz: {t}. Sentiment: {sent_data.get('total', 0)}/100. Radar2: {radar_val}. Lütfen bu hisse için 3-20 gün vadeli teknik analiz yap."
    with st.sidebar:
        st.code(prompt, language="text")
        st.success("Metin kopyalanmaya hazır! 📋")
    st.session_state.generate_prompt = False

info = fetch_stock_info(st.session_state.ticker)

col_left, col_right = st.columns([4, 1])

with col_left:
    synth_data = calculate_synthetic_sentiment(st.session_state.ticker)
    if synth_data is not None and not synth_data.empty: render_synthetic_sentiment_panel(synth_data)
    render_detail_card_advanced(st.session_state.ticker)

    st.markdown('<div class="info-header" style="margin-top: 15px; margin-bottom: 10px;">🕵️ Sentiment Ajanı</div>', unsafe_allow_html=True)
    
    with st.expander("Ajan Operasyonlarını Yönet", expanded=True):
        # AJAN 1: SENTIMENT
        if st.button(f"🕵️ SENTIMENT & MOMENTUM TARAMASI ({st.session_state.category})", type="primary", use_container_width=True):
            with st.spinner("Ajan piyasayı didik didik ediyor..."):
                current_assets = ASSET_GROUPS.get(st.session_state.category, [])
                crosses, trends, filtered = scan_stp_signals(current_assets)
                st.session_state.stp_crosses = crosses; st.session_state.stp_trends = trends; st.session_state.stp_filtered = filtered
                st.session_state.stp_scanned = True
                st.session_state.accum_data = scan_hidden_accumulation(current_assets)

        if st.session_state.stp_scanned or (st.session_state.accum_data is not None):
            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown("<div style='text-align:center; color:#1e40af; font-weight:700; font-size:0.9rem; margin-bottom:5px;'>⚡ STP KESİŞİM</div>", unsafe_allow_html=True)
                with st.container(height=200, border=True):
                    for item in st.session_state.stp_crosses:
                        if st.button(f"🚀 {item['Sembol']} ({item['Fiyat']:.2f})", key=f"stp_c_{item['Sembol']}", use_container_width=True): 
                            st.session_state.ticker = item['Sembol']; st.rerun()
            with c2:
                st.markdown("<div style='text-align:center; color:#b91c1c; font-weight:700; font-size:0.8rem; margin-bottom:5px;'>🎯 MOMENTUM?</div>", unsafe_allow_html=True)
                with st.container(height=200, border=True):
                    for item in st.session_state.stp_filtered:
                        if st.button(f"🔥 {item['Sembol']} ({item['Fiyat']:.2f})", key=f"stp_f_{item['Sembol']}", use_container_width=True): 
                            st.session_state.ticker = item['Sembol']; st.rerun()
            with c3:
                st.markdown("<div style='text-align:center; color:#15803d; font-weight:700; font-size:0.8rem; margin-bottom:5px;'>✅ STP TREND</div>", unsafe_allow_html=True)
                with st.container(height=200, border=True):
                    for item in st.session_state.stp_trends:
                        gun_sayisi = item.get('Gun', '?')
                        if st.button(f"📈 {item['Sembol']} ({gun_sayisi} Gün)", key=f"stp_t_{item['Sembol']}", use_container_width=True): 
                            st.session_state.ticker = item['Sembol']; st.rerun()
            with c4:
                st.markdown("<div style='text-align:center; color:#7c3aed; font-weight:700; font-size:0.8rem; margin-bottom:5px;'>🤫 SESSİZ TOPLAMA</div>", unsafe_allow_html=True)
                with st.container(height=200, border=True):
                    if st.session_state.accum_data is not None and not st.session_state.accum_data.empty:
                        for index, row in st.session_state.accum_data.iterrows():
                             if st.button(f"🔍 {row['Sembol']} (Güç:{row['MF_Gucu_Goster']})", key=f"btn_acc_{row['Sembol']}", use_container_width=True):
                                on_scan_result_click(row['Sembol']); st.rerun()

        st.divider()

        # AJAN 2: BREAKOUT
        if st.button(f"⚡ BREAK-OUT TARAMASI", type="secondary", key="dual_breakout_btn", use_container_width=True):
            with st.spinner("Breakout Ajanı çalışıyor..."):
                curr_list = ASSET_GROUPS.get(st.session_state.category, [])
                st.session_state.breakout_left = agent3_breakout_scan(curr_list)
                st.session_state.breakout_right = scan_confirmed_breakouts(curr_list)
                st.rerun()

        c_left, c_right = st.columns(2)
        with c_left:
            if st.session_state.breakout_left is not None and not st.session_state.breakout_left.empty:
                st.caption("🔥 ISINANLAR")
                df_left = st.session_state.breakout_left.head(10)
                for i, (index, row) in enumerate(df_left.iterrows()):
                    if st.button(f"{row['Sembol_Raw']} | {row['Zirveye Yakınlık']}", key=f"L_btn_{i}", use_container_width=True):
                        on_scan_result_click(row['Sembol_Raw']); st.rerun()
        with c_right:
            if st.session_state.breakout_right is not None and not st.session_state.breakout_right.empty:
                st.caption("🔨 KIRANLAR")
                df_right = st.session_state.breakout_right.head(10)
                for i, (index, row) in enumerate(df_right.iterrows()):
                    if st.button(f"{row['Sembol']} | {row['Hacim_Kati']}", key=f"R_btn_{i}", use_container_width=True):
                        on_scan_result_click(row['Sembol']); st.rerun()
        
        st.divider()

        # AJAN 3: KAMA & HARSI 3H (YENİ)
        st.markdown("<div style='color:#0369a1; font-weight:700; margin-bottom:5px;'>🕵️ 3. AJAN: KAMA & HARSI (3 Saatlik - Trend Takip)</div>", unsafe_allow_html=True)
        st.caption("Şartlar: Fiyat > EMA9 (Onaylı), Fiyat > KAMA(20-2-30) (Onaylı), RSI > SMA50, HARSI 3 Mum Yeşil.")
        
        if st.button(f"🌊 3H TREND TARAMASI BAŞLAT ({st.session_state.category})", type="primary", use_container_width=True):
            with st.spinner("3. Ajan hisseleri 3 saatlik dilimlerde analiz ediyor..."):
                current_assets = ASSET_GROUPS.get(st.session_state.category, [])
                st.session_state.harsi_data = scan_agent3_harsi(current_assets)
        
        if st.session_state.harsi_data is not None:
            if not st.session_state.harsi_data.empty:
                st.success(f"{len(st.session_state.harsi_data)} adet hisse trend şartlarını sağlıyor!")
                
                # Sonuçları Göster
                cols = st.columns(3)
                for i, (index, row) in enumerate(st.session_state.harsi_data.iterrows()):
                    with cols[i % 3]:
                        # Kart Tasarımı
                        html_card = f"""
                        <div style="background:#f0f9ff; border:1px solid #bae6fd; border-radius:6px; padding:8px; margin-bottom:8px; text-align:center;">
                            <div style="font-weight:800; color:#0369a1; font-size:1rem; margin-bottom:4px;">{row['Sembol']}</div>
                            <div style="font-size:0.8rem; color:#334155; margin-bottom:4px;">Fiyat: <b>{row['Fiyat']}</b></div>
                            <div style="display:flex; justify-content:center; gap:5px; font-size:0.7rem;">
                                <span style="background:#dcfce7; color:#166534; padding:2px 4px; border-radius:3px;">RSI: {row['RSI']}</span>
                                <span style="background:#dbeafe; color:#1e40af; padding:2px 4px; border-radius:3px;">{row['HARSI']}</span>
                            </div>
                        </div>
                        """
                        st.markdown(html_card, unsafe_allow_html=True)
                        if st.button("İncele", key=f"btn_harsi_{row['Sembol']}", use_container_width=True):
                            on_scan_result_click(row['Sembol']); st.rerun()
            else:
                st.warning("Bu kriterlere uyan hisse bulunamadı.")

    st.markdown(f"<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:20px;'>📡 {st.session_state.ticker} Haberleri</div>", unsafe_allow_html=True)
    # Haber linkleri (değişmedi, yer tutucu)
    st.info("Haber paneli aktif.")

with col_right:
    if info and info.get('price'):
        display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")
        cls = "delta-pos" if info['change_pct'] >= 0 else "delta-neg"
        st.markdown(f'<div class="stat-box-small" style="margin-bottom:10px;"><p class="stat-label-small">FİYAT: {display_ticker}</p><p class="stat-value-small money-text">{info["price"]:.2f}<span class="stat-delta-small {cls}">{"+" if info["change_pct"]>=0 else ""}{info["change_pct"]:.2f}%</span></p></div>', unsafe_allow_html=True)
    else: st.warning("Fiyat verisi alınamadı.")
    
    st.markdown(f"<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:10px; color:#1e40af; background-color:{current_theme['box_bg']}; padding:5px; border-radius:5px; border:1px solid #1e40af;'>🎯 Ortak Fırsatlar</div>", unsafe_allow_html=True)
    with st.container(height=250):
        df1 = st.session_state.scan_data; df2 = st.session_state.radar2_data
        if df1 is not None and df2 is not None and not df1.empty and not df2.empty:
            commons = []; symbols = set(df1["Sembol"]).intersection(set(df2["Sembol"]))
            for sym in symbols:
                r1 = df1[df1["Sembol"]==sym].iloc[0]; r2 = df2[df2["Sembol"]==sym].iloc[0]
                commons.append({"symbol": sym, "score": float(r1["Skor"])+float(r2["Skor"])})
            sorted_c = sorted(commons, key=lambda x: x["score"], reverse=True)
            for item in sorted_c:
                if st.button(f"{item['symbol']} (Top:{int(item['score'])})", key=f"common_{item['symbol']}", use_container_width=True):
                    on_scan_result_click(item['symbol']); st.rerun()
        else: st.caption("İki radar da çalıştırılmalı.")
   
    tab1, tab2 = st.tabs(["🧠 RADAR 1", "🚀 RADAR 2"])
    with tab1:
        if st.button(f"⚡ {st.session_state.category} Tara", type="primary", key="r1_main_scan_btn"):
            with st.spinner("Taranıyor..."): st.session_state.scan_data = analyze_market_intelligence(ASSET_GROUPS.get(st.session_state.category, []))
        if st.session_state.scan_data is not None:
             for i, r in st.session_state.scan_data.iterrows():
                 if st.button(f"🔥 {r['Skor']}/7 | {r['Sembol']}", key=f"r1_b_{i}", use_container_width=True): on_scan_result_click(r['Sembol']); st.rerun()
    with tab2:
        if st.button(f"🚀 RADAR 2 Tara", type="primary", key="r2_main_scan_btn"):
            with st.spinner("Taranıyor..."): st.session_state.radar2_data = radar2_scan(ASSET_GROUPS.get(st.session_state.category, []))
        if st.session_state.radar2_data is not None:
             for i, r in st.session_state.radar2_data.iterrows():
                 if st.button(f"🚀 {r['Skor']}/7 | {r['Sembol']}", key=f"r2_b_{i}", use_container_width=True): on_scan_result_click(r['Sembol']); st.rerun()
