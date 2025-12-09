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

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Patronun Terminali v4.3.2",
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
    .stButton button {{ width: 100%; border-radius: 4px; font-size: 0.78rem; padding: 0.2rem 0.5rem; }}
    
    .info-card {{
        background: {current_theme['box_bg']}; border: 1px solid {current_theme['border']};
        border-radius: 6px; padding: 8px; margin-top: 5px; margin-bottom: 10px;
        font-size: 0.8rem; font-family: 'Inter', sans-serif;
    }}
    .info-header {{ font-weight: 700; color: #1e3a8a; border-bottom: 1px solid {current_theme['border']}; padding-bottom: 4px; margin-bottom: 4px; }}
    .info-row {{ display: flex; align-items: flex-start; margin-bottom: 3px; }}
    
    .label-short {{ font-weight: 600; color: #64748B; width: 80px; flex-shrink: 0; }}
    .label-long {{ font-weight: 600; color: #64748B; width: 100px; flex-shrink: 0; }} 
    
    .info-val {{ color: {current_theme['text']}; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; }}
    
    .header-logo {{ width: 40px; height: auto; margin-right: 10px; }}
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

# --- VARLIK LİSTELERİ (GÜNCELLENMİŞ VE SIRALI) ---
raw_sp500 = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "AMD",
    "INTC", "QCOM", "TXN", "AMAT", "LRCX", "MU", "ADI", "CSCO", "ORCL", "CRM",
    "ADBE", "IBM", "ACN", "NOW", "PANW", "SNPS", "CDNS", "KLAC", "NXPI", "APH",
    "MCHP", "ON", "ANET", "IT", "GLW", "HPE", "HPQ", "NTAP", "STX", "WDC", "TEL",
    "PLTR", "FTNT", "CRWD", "SMCI", "MSI", "TRMB", "TER", "PTC", "TYL", "FFIV",
    "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "AXP", "V", "MA", "PYPL", "SQ",
    "SPGI", "MCO", "CB", "MMC", "PGR", "USB", "PNC", "TFC", "COF", "BK", "SCHW",
    "ICE", "CME", "AON", "AJG", "TRV", "ALL", "AIG", "MET", "PRU", "AFL", "HIG",
    "FITB", "MTB", "HBAN", "RF", "CFG", "KEY", "SYF", "DFS", "AMP", "PFG", "CINF",
    "LLY", "UNH", "JNJ", "MRK", "ABBV", "PFE", "TMO", "DHR", "ABT", "BMY", "AMGN",
    "ISRG", "SYK", "ELV", "CVS", "CI", "GILD", "REGN", "VRTX", "ZTS", "BSX", "BDX",
    "HCA", "MCK", "COR", "CAH", "CNC", "HUM", "MOH", "DXCM", "EW", "RMD", "ALGN",
    "ZBH", "BAX", "STE", "COO", "WAT", "MTD", "IQV", "A", "HOLX", "IDXX", "BIO",
    "WMT", "HD", "PG", "COST", "KO", "PEP", "MCD", "SBUX", "NKE", "DIS", "TMUS",
    "CMCSA", "NFLX", "TGT", "LOW", "TJX", "PM", "MO", "EL", "CL", "K", "GIS", "MNST",
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
    "F", "GM", "STT", "ZBRA", "GL", "EWBC", "OHI", "EXPE", "AAL", "CF",
    "HAL", "HP", "RCL", "NCLH", "CPRT", "FANG", "PXD", "OKE", "WMB", "TRGP"
]

# Patronun Özel Hisseleri Eklendi
raw_sp500.extend(["AGNC", "ARCC", "JEPI", "EPD"])

# Kripto Listesi
raw_crypto = [
    "GC=F", "SI=F", # Altın ve Gümüş
    "BTC-USD", "ETH-USD", "XRP-USD", "BNB-USD", "AVAX-USD", "SOL-USD", 
    "DOGE-USD", "TRX-USD", "ADA-USD", "LINK-USD", "XLM-USD", "LTC-USD"
]

# Nasdaq 100
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

# Otomatik Alfabetik Sıralama (A-Z)
ASSET_GROUPS = {
    "S&P 500 (TOP 300)": sorted(list(set(raw_sp500))), # Set ile çiftleri temizledik, sorted ile sıraladık
    "NASDAQ (TOP 100)": sorted(list(set(raw_nasdaq))),
    "EMTİA & KRİPTO": sorted(list(set(raw_crypto)))
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
        st.session_state.category = new_cat; st.session_state.ticker = ASSET_GROUPS[new_cat][0]
        st.session_state.scan_data = None; st.session_state.radar2_data = None

def on_asset_change():
    new_asset = st.session_state.get("selected_asset_key")
    if new_asset: st.session_state.ticker = new_asset

def on_manual_button_click():
    if st.session_state.manual_input_key: st.session_state.ticker = st.session_state.manual_input_key.upper()

def on_scan_result_click(symbol): st.session_state.ticker = symbol

def toggle_watchlist(symbol):
    wl = st.session_state.watchlist
    if symbol in wl: remove_watchlist_db(symbol); wl.remove(symbol)
    else: add_watchlist_db(symbol); wl.append(symbol)
    st.session_state.watchlist = wl

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### ⚙️ Ayarlar")
    selected_theme_name = st.selectbox("", ["Beyaz", "Kirli Beyaz", "Buz Mavisi"], index=["Beyaz", "Kirli Beyaz", "Buz Mavisi"].index(st.session_state.theme), label_visibility="collapsed")
    if selected_theme_name != st.session_state.theme: st.session_state.theme = selected_theme_name; st.rerun()
    st.divider()
    
    with st.expander("🤖 AI Analist (Prompt)", expanded=True):
        if st.button("📋 Analiz Metnini Hazırla", type="primary"):
            st.session_state.generate_prompt = True

# --- ANALİZ MOTORLARI (CACHED) ---
@st.cache_data(ttl=3600)
def analyze_market_intelligence(asset_list):
    signals = []
    try: data = yf.download(asset_list, period="6mo", group_by='ticker', threads=True, progress=False)
    except: return pd.DataFrame()
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]: df = data[symbol].copy()
                else: continue
            else:
                if len(asset_list) == 1: df = data.copy()
                else: continue
            if df.empty or 'Close' not in df.columns: continue
            df = df.dropna(subset=['Close'])
            if len(df) < 60: continue
            close = df['Close']; high = df['High']; low = df['Low']
            volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))
            ema5 = close.ewm(span=5, adjust=False).mean(); ema20 = close.ewm(span=20, adjust=False).mean()
            sma20 = close.rolling(20).mean(); std20 = close.rolling(20).std()
            bb_width = ((sma20 + 2*std20) - (sma20 - 2*std20)) / (sma20 + 0.0001)
            hist = (close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()) - (close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()).ewm(span=9, adjust=False).mean()
            delta = close.diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + (gain / loss))); williams_r = (high.rolling(14).max() - close) / (high.rolling(14).max() - low.rolling(14).min()) * -100
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
            if score > 0: signals.append({"Sembol": symbol, "Fiyat": f"{curr_c:.2f}", "Skor": score, "Nedenler": " | ".join(reasons)})
        except: continue
    return pd.DataFrame(signals).sort_values(by="Skor", ascending=False) if signals else pd.DataFrame()

@st.cache_data(ttl=3600)
def radar2_scan(asset_list, min_price=5, max_price=500, min_avg_vol_m=1.0):
    if not asset_list: return pd.DataFrame()
    try: data = yf.download(asset_list, period="1y", group_by="ticker", threads=True, progress=False)
    except: return pd.DataFrame()
    try: idx = yf.download("^GSPC", period="1y", progress=False)["Close"]
    except: idx = None
    results = []
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol not in data.columns.levels[0]: continue
                df = data[symbol].copy()
            else:
                if len(asset_list) == 1: df = data.copy()
                else: continue
            if df.empty or 'Close' not in df.columns: continue
            df = df.dropna(subset=['Close']); 
            if len(df) < 120: continue
            close = df['Close']; high = df['High']; volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))
            curr_c = float(close.iloc[-1])
            if curr_c < min_price or curr_c > max_price: continue
            avg_vol_20 = float(volume.rolling(20).mean().iloc[-1])
            if avg_vol_20 < min_avg_vol_m * 1e6: continue
            sma20 = close.rolling(20).mean(); sma50 = close.rolling(50).mean()
            sma100 = close.rolling(100).mean(); sma200 = close.rolling(200).mean()
            trend = "Yatay"
            if not np.isnan(sma200.iloc[-1]):
                if curr_c > sma50.iloc[-1] > sma100.iloc[-1] > sma200.iloc[-1] and sma200.iloc[-1] > sma200.iloc[-20]: trend = "Boğa"
                elif curr_c < sma200.iloc[-1] and sma200.iloc[-1] < sma200.iloc[-20]: trend = "Ayı"
            delta = close.diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + (gain / loss))); rsi_c = float(rsi.iloc[-1])
            hist = (close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()) - (close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()).ewm(span=9, adjust=False).mean()
            recent_high_60 = float(high.rolling(60).max().iloc[-1])
            breakout_ratio = curr_c / recent_high_60 if recent_high_60 > 0 else 0
            rs_score = 0.0
            if idx is not None and len(close)>60 and len(idx)>60:
                common_index = close.index.intersection(idx.index)
                if len(common_index) > 60:
                    cs = close.reindex(common_index); isx = idx.reindex(common_index)
                    rs_score = float((cs.iloc[-1]/cs.iloc[-60]-1) - (isx.iloc[-1]/isx.iloc[-60]-1))
            setup = "-"; tags = []; score = 0
            avg_vol_20 = max(avg_vol_20, 1); vol_spike = volume.iloc[-1] > avg_vol_20 * 1.3
            if trend == "Boğa" and breakout_ratio >= 0.97: setup = "Breakout"; score += 2; tags.append("Zirve"); 
            if vol_spike: score += 1; tags.append("Hacim+")
            if trend == "Boğa" and setup == "-":
                if sma20.iloc[-1] <= curr_c <= sma50.iloc[-1] * 1.02 and 40 <= rsi_c <= 55: setup = "Pullback"; score += 2; tags.append("Düzeltme")
                if volume.iloc[-1] < avg_vol_20 * 0.9: score += 1; tags.append("Sığ Satış")
            if setup == "-":
                if rsi.iloc[-2] < 30 <= rsi_c and hist.iloc[-1] > hist.iloc[-2]: setup = "Dip Dönüşü"; score += 2; tags.append("Dip Dönüşü")
            if rs_score > 0: score += 1; tags.append("RS+")
            if trend == "Boğa": score += 1
            elif trend == "Ayı": score -= 1
            if score > 0: results.append({"Sembol": symbol, "Fiyat": round(curr_c, 2), "Trend": trend, "Setup": setup, "Skor": score, "RS": round(rs_score * 100, 1), "Etiketler": " | ".join(tags)})
        except: continue
    return pd.DataFrame(results).sort_values(by=["Skor", "RS"], ascending=False).head(50) if results else pd.DataFrame()

# --- SENTIMENT & DERİN RÖNTGEN ---
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
        bars = int(total / 5); bar_str = "[" + "|" * bars + "." * (20 - bars) + "]"
        
        def fmt(lst): return f"<span style='font-size:0.65rem; color:#64748B;'>({' + '.join(lst)})</span>" if lst else ""
        
        return {
            "total": total, "bar": bar_str,
            "mom": f"{score_mom}/30 {fmt(reasons_mom)}",
            "vol": f"{score_vol}/25 {fmt(reasons_vol)}",
            "tr": f"{score_tr}/20 {fmt(reasons_tr)}",
            "vola": f"{score_vola}/15 {fmt(reasons_vola)}",
            "str": f"{score_str}/10 {fmt(reasons_str)}",
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

# --- ICT & PRICE ACTION MOTORU (GELİŞMİŞ SENARYO BAZLI) ---
@st.cache_data(ttl=300)
def calculate_ict_concepts(ticker):
    try:
        # Veri Çekme
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Temel Değişkenler
        close = df['Close']
        high = df['High']
        low = df['Low']
        curr_price = float(close.iloc[-1])
        
        # 1. Market Yapısı (Swing High/Low Tespiti)
        # Basit "son 20 gün" yerine yerel tepeleri buluyoruz
        rolling_high = high.rolling(window=20, center=False).max()
        rolling_low = low.rolling(window=20, center=False).min()
        
        structure_high = float(rolling_high.iloc[-2]) # Dünkü 20 günlük tepe
        structure_low = float(rolling_low.iloc[-2])   # Dünkü 20 günlük dip
        
        trend = "YATAY"
        trend_score = 0 # -1 Bear, +1 Bull
        
        if curr_price > structure_high:
            trend = "BULLISH"
            trend_score = 1
        elif curr_price < structure_low:
            trend = "BEARISH"
            trend_score = -1
            
        # 2. PD Arrays (Premium / Discount Hesabı)
        # Son anlamlı swing aralığını (Dealing Range) belirliyoruz
        range_high = float(high.tail(60).max())
        range_low = float(low.tail(60).min())
        range_size = range_high - range_low
        
        fibo_50 = range_low + (range_size * 0.5)
        ote_low = range_low + (range_size * 0.618) # Bearish OTE altı (Bullish için tersi)
        ote_high = range_low + (range_size * 0.79) 
        
        # Bullish senaryo için OTE (Discount bölgesindeki 62-79)
        bull_ote_entry = range_low + (range_size * 0.382) # Aslında 0.618 geri çekilme
        bull_ote_limit = range_low + (range_size * 0.21)  # 0.79 geri çekilme
        
        # Konum Belirleme
        position_pct = ((curr_price - range_low) / range_size) * 100
        position_status = "EQ (Denge)"
        if position_pct > 60: position_status = "PREMIUM (Pahalı)"
        elif position_pct < 40: position_status = "DISCOUNT (Ucuz)"
        
        # 3. Tetikleyiciler (FVG & Liquidity Sweep)
        has_fvg = False
        fvg_msg = "Gap Yok"
        # Son 5 mumda FVG var mı?
        for i in range(len(df)-1, len(df)-5, -1):
            if low.iloc[i] > high.iloc[i-2]: # Bullish FVG
                has_fvg = True
                fvg_msg = f"Bullish FVG: {high.iloc[i-2]:.2f}-{low.iloc[i]:.2f}"
                break
        
        # Sweep (Likidite Temizliği) Kontrolü
        # Fiyat bir önceki tepeyi gördü ama altında kapattı mı? (Turtle Soup)
        prev_high = float(high.iloc[-2])
        curr_high = float(high.iloc[-1])
        has_sweep = False
        if curr_high > prev_high and curr_price < prev_high:
            has_sweep = True
            
        # --- KARAR AĞACI (DECISION TREE) ---
        scenario = {}
        
        # SENARYO 1: GOLDEN LONG
        if trend == "BULLISH" and position_pct < 50:
            scenario = {
                "id": 1,
                "title": "🔥 GOLDEN LONG (Alım Fırsatı)",
                "desc": f"Fiyat yükseliş trendinde ve Discount bölgesine (%{position_pct:.1f}) indi. OTE seviyesinden tepki bekleniyor.",
                "strategy": "🛡️ GİRİŞ PLANI: Bullish Order Block veya FVG üzerinde tutunursa, hedef yukarıdaki Buy-Side Likiditesi.",
                "badge": "OTE BUY",
                "color": "#16a34a" # Yeşil
            }
            if has_fvg: scenario["desc"] += " Destekleyici FVG mevcut."

        # SENARYO 2: LİKİDİTE TUZAĞI (BEARISH REVERSAL)
        elif has_sweep and trend_score >= 0 and position_pct > 80:
             scenario = {
                "id": 2,
                "title": "🪤 LİKİDİTE TUZAĞI (Turtle Soup)",
                "desc": "Fiyat önceki tepeyi temizledi (Sweep) ancak yukarıda kalıcı olamadı. Bu bir Stop Hunt (Stop Avı) olabilir.",
                "strategy": "📉 STRATEJİ: Yükselişler satış fırsatıdır. Market yapısı bozulursa (MSB) Short aranmalı.",
                "badge": "FAKE PUMP",
                "color": "#dc2626" # Kırmızı
            }

        # SENARYO 3: YÜKSEK MOMENTUM (KAÇAN TREN)
        elif trend == "BULLISH" and position_pct > 50 and not has_sweep:
             scenario = {
                "id": 3,
                "title": "🚀 YÜKSEK MOMENTUM",
                "desc": "Boğalar çok iştahlı. Fiyat derin düzeltme yapmadan (Premium bölgede) yükselmeye devam ediyor.",
                "strategy": "🎯 GİRİŞ: OTE beklemek yerine, ilk Bullish Breaker veya sığ geri çekilmelerde (Breakout) trene atlanabilir.",
                "badge": "MOMENTUM",
                "color": "#2563eb" # Mavi
            }

        # SENARYO 4: AŞIRI PAHALI (DEEP PREMIUM)
        elif position_pct > 90:
             scenario = {
                "id": 4,
                "title": "⚠️ AŞIRI PAHALI (Deep Premium)",
                "desc": f"Trend yukarı olsa da fiyat 'Deep Premium' (%{position_pct:.1f}) bölgesinde aşırı şişti. Kurumsal satış gelebilir.",
                "strategy": "🛑 UYARI: Buradan Long açmak çok riskli. Fiyatın en azından Equilibrium (%50) seviyesine çekilmesini bekle.",
                "badge": "RISKLI",
                "color": "#ea580c" # Turuncu
            }

        # SENARYO 6: GÜÇLÜ SATIŞ (DÜŞEN BIÇAK)
        elif trend == "BEARISH":
             scenario = {
                "id": 6,
                "title": "🩸 GÜÇLÜ SATIŞ (Düşen Bıçak)",
                "desc": "Ayılar kontrolü elinde tutuyor. Yapı tamamen düşüş (Bearish) yönünde ve henüz dönüş emaresi yok.",
                "strategy": "⏳ PLAN: Düşen bıçak tutulmaz. Long denemek için acele etme, Short yönlü FVG'leri kovala.",
                "badge": "BEARISH",
                "color": "#7f1d1d" # Koyu Kırmızı
            }
            
        # SENARYO 5: KONSOLİDASYON (Default)
        else:
            scenario = {
                "id": 5,
                "title": "💤 KONSOLİDASYON (Testere)",
                "desc": f"Fiyat Equilibrium (%{position_pct:.1f}) bölgesinde kararsız. Alt ve üstte likidite birikiyor.",
                "strategy": "⏳ PLAN: İşlem yapma. Bir tarafın patlatılmasını (Likidite Avı) bekle.",
                "badge": "RANGE",
                "color": "#64748b" # Gri
            }

        return {
            "price": curr_price,
            "trend": trend,
            "position_pct": position_pct,
            "range_high": range_high,
            "range_low": range_low,
            "fvg_msg": fvg_msg,
            "scenario": scenario
        }
    except Exception as e:
        return None

@st.cache_data(ttl=600)
def get_tech_card_data(ticker):
    try:
        df = yf.download(ticker, period="2y", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']; high = df['High']; low = df['Low']
        sma50 = close.rolling(50).mean().iloc[-1]; sma100 = close.rolling(100).mean().iloc[-1]; sma200 = close.rolling(200).mean().iloc[-1]; ema144 = close.ewm(span=144, adjust=False).mean().iloc[-1]
        atr = (high-low).rolling(14).mean().iloc[-1]
        return {"sma50": sma50, "sma100": sma100, "sma200": sma200, "ema144": ema144, "stop_level": close.iloc[-1] - (2 * atr), "risk_pct": (2 * atr) / close.iloc[-1] * 100, "atr": atr}
    except: return None

# --- RENDER ---
def render_sentiment_card(sent):
    if not sent: return
    color = "🔥" if sent['total'] >= 70 else "❄️" if sent['total'] <= 30 else "⚖️"
    st.markdown(f"""
    <div class="info-card">
        <div class="info-header">🎭 Piyasa Duygusu (Sentiment)</div>
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

def render_ict_panel(analysis):
    if not analysis:
        st.info("Veri hesaplanamadı veya yetersiz.")
        return

    scen = analysis['scenario']
    pos_pct = analysis['position_pct']
    
    # Renk Teması (Dinamik)
    theme_color = scen['color']
    bg_color_light = f"{theme_color}15" # %15 opaklık
    
    # Progress Bar Hesabı (Görsel Bar)
    # 0 = Discount (Yeşil), 100 = Premium (Kırmızı)
    # CSS Gradient: Yeşilden Kırmızıya
    marker_position = min(max(pos_pct, 0), 100)
    
    # CSS Animasyonu (Golden Setup İçin Yanıp Sönme)
    animation_css = ""
    if scen['id'] == 1: # Golden Setup
        animation_css = """
        <style>
        @keyframes pulse-border {
            0% { box-shadow: 0 0 0 0 rgba(22, 163, 74, 0.4); }
            70% { box-shadow: 0 0 0 10px rgba(22, 163, 74, 0); }
            100% { box-shadow: 0 0 0 0 rgba(22, 163, 74, 0); }
        }
        .golden-box {
            animation: pulse-border 2s infinite;
            border: 2px solid #16a34a !important;
        }
        </style>
        """
        
    st.markdown(f"""
    {animation_css}
    <div class="info-card {'golden-box' if scen['id']==1 else ''}" style="border-left: 4px solid {theme_color};">
        
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <div style="font-weight:800; color:{theme_color}; font-size:1rem;">ICT ANALİZİ</div>
            <span style="background-color:{theme_color}; color:white; padding:2px 8px; border-radius:4px; font-size:0.7rem; font-weight:bold;">
                {scen['badge']}
            </span>
        </div>

        <div style="margin-bottom:15px;">
            <div style="display:flex; justify-content:space-between; font-size:0.7rem; color:#64748B; margin-bottom:2px;">
                <span>Discount (Ucuz)</span>
                <span>EQ (%50)</span>
                <span>Premium (Pahalı)</span>
            </div>
            <div style="width:100%; height:8px; background:#e2e8f0; border-radius:4px; position:relative; overflow:hidden;">
                <div style="width:100%; height:100%; background: linear-gradient(90deg, #4ade80 0%, #facc15 50%, #f87171 100%);"></div>
                <div style="position:absolute; top:-2px; left:{marker_position}%; width:4px; height:12px; background:black; border:1px solid white;"></div>
            </div>
            <div style="text-align:center; font-size:0.7rem; font-weight:bold; margin-top:2px; color:{theme_color};">
                Aktif Konum: %{pos_pct:.1f}
            </div>
        </div>

        <div style="background-color:{bg_color_light}; padding:10px; border-radius:6px; margin-bottom:8px;">
            <div style="font-weight:700; color:{theme_color}; font-size:0.9rem; margin-bottom:5px;">
                {scen['title']}
            </div>
            <div style="font-size:0.8rem; color:#334155; margin-bottom:8px; line-height:1.4;">
                {scen['desc']}
            </div>
            <div style="font-size:0.75rem; color:#0f172a; font-family:'Inter', sans-serif; background:rgba(255,255,255,0.6); padding:6px; border-radius:4px; border-left:2px solid {theme_color};">
                {scen['strategy']}
            </div>
        </div>

        <div class="info-row"><div class="label-long">Trend Yönü:</div><div class="info-val" style="color:{theme_color}; font-weight:bold;">{analysis['trend']}</div></div>
        <div class="info-row"><div class="label-long">Range:</div><div class="info-val">{analysis['range_low']:.2f} - {analysis['range_high']:.2f}</div></div>
        <div class="info-row"><div class="label-long">Yapı (FVG):</div><div class="info-val">{analysis['fvg_msg']}</div></div>

    </div>
    """, unsafe_allow_html=True)

def render_detail_card(ticker):
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
        <div class="info-header">📋 Teknik Kart</div>
        <div class="info-row"><div class="label-short">Radar 1:</div><div class="info-val">{r1_t}</div></div>
        <div class="info-row"><div class="label-short">Radar 2:</div><div class="info-val">{r2_t}</div></div>
        <div class="info-row"><div class="label-short">Ortalama:</div><div class="info-val">{ma_t}</div></div>
    </div>
    """, unsafe_allow_html=True)

def render_tradingview_widget(ticker, height=650):
    tv_symbol = ticker
    if ".IS" in ticker: tv_symbol = f"BIST:{ticker.replace('.IS', '')}"
    elif "=X" in ticker: tv_symbol = f"FX_IDC:{ticker.replace('=X', '')}"
    html = f"""<div class="tradingview-widget-container"><div id="tradingview_chart"></div><script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script><script type="text/javascript">new TradingView.widget({{"width": "100%", "height": {height}, "symbol": "{tv_symbol}", "interval": "D", "timezone": "Etc/UTC", "theme": "light", "style": "1", "locale": "tr", "toolbar_bg": "#f1f3f6", "enable_publishing": false, "allow_symbol_change": true, "container_id": "tradingview_chart"}});</script></div>"""
    components.html(html, height=height)

@st.cache_data(ttl=300)
def fetch_stock_info(ticker):
    try:
        info = yf.Ticker(ticker).info
        return {'price': info.get('currentPrice') or info.get('regularMarketPrice'), 'change_pct': ((info.get('currentPrice') or info.get('regularMarketPrice')) - info.get('previousClose')) / info.get('previousClose') * 100 if info.get('previousClose') else 0, 'volume': info.get('volume', 0), 'sector': info.get('sector', '-'), 'target': info.get('targetMeanPrice', '-')}
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

# --- ARAYÜZ (FİLTRELER YERİNDE SABİT) ---
BULL_ICON_B64 = "data:image/png;base64,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"

st.markdown(f"""
<div class="header-container" style="display:flex; align-items:center;">
    <img src="{BULL_ICON_B64}" class="header-logo">
    <div>
        <div style="font-size:1.5rem; font-weight:700; color:#1e3a8a;">Patronun Terminali v4.3.2</div>
        <div style="font-size:0.8rem; color:#64748B;">Market Maker Edition (Ordered & Expanded)</div>
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
with col_ass:
    opts = ASSET_GROUPS.get(st.session_state.category, ASSET_GROUPS[INITIAL_CATEGORY])
    try: asset_idx = opts.index(st.session_state.ticker)
    except ValueError: asset_idx = 0
    st.selectbox("Varlık Listesi", opts, index=asset_idx, key="selected_asset_key", on_change=on_asset_change, label_visibility="collapsed")
with col_search_in: st.text_input("Manuel", placeholder="Kod", key="manual_input_key", label_visibility="collapsed")
with col_search_btn: st.button("Ara", on_click=on_manual_button_click)

st.markdown("<hr style='margin-top:0.5rem; margin-bottom:0.5rem;'>", unsafe_allow_html=True)

# PROMPT TETİKLEYİCİ
if 'generate_prompt' not in st.session_state: st.session_state.generate_prompt = False
if st.session_state.generate_prompt:
    t = st.session_state.ticker
    try:
        inf = yf.Ticker(t).info
        price = inf.get('currentPrice') or inf.get('regularMarketPrice') or "Bilinmiyor"
    except: price = "Bilinmiyor"
    
    # STATİK PROMPT
    prompt = f"""Rol: Kıdemli Fon Yöneticisi ve Algoritmik Trader (Market Maker Bakış Açısı).

Bağlam: Sana "Patronun Terminali" adlı gelişmiş bir analiz panelinden alınan {t} hissesinin ekran görüntüsünü sunuyorum. Bu verilerde 4 farklı katman var:

1. Sentiment & Psikoloji: Piyasanın korku/iştah durumu (0-100 Puan).
2. Radar Sinyalleri: Momentum ve Trend algoritmalarının skorları.
3. Teknik Kart: Ortalamalar (SMA/EMA) ve ATR bazlı risk seviyeleri.
4. ICT & Price Action: Kurumsal ayak izleri (Order Block, FVG, Breaker, Likidite, Golden Setup).

GÖREVİN:
Bu 4 katmanı birleştirerek bir "Multidimensional Market Analysis" (Çok Boyutlu Piyasa Analizi) yapman gerekiyor.

ANALİZ ADIMLARI:
1. Duygu Kontrolü: Sentiment skoru ve Derin Röntgen verilerine bak. Piyasa şu an panikte mi, coşkuda mı yoksa kararsız mı? Hacim fiyatı destekliyor mu?
2. Kurumsal Tuzaklar (ICT): Fiyat şu an "Ucuz" (Discount) mu yoksa "Pahalı" (Premium) mu? Yakınlarda bir "Golden Setup" veya "Breaker Block" var mı? Likidite (EQH/EQL) nerede birikmiş?
3. Trend Teyidi: Radar puanları ve hareketli ortalamalar (SMA50/200) ana yönü destekliyor mu?
4. Çelişki Analizi: Eğer Sentiment "AL" derken, ICT "SAT" (Premium bölge) diyorsa, bu riski açıkça belirt.

ÇIKTI FORMATI (SONUÇ):
Bana hikaye anlatma, net emirler ver:
* YÖN (BIAS): (Long / Short / Nötr)
* GİRİŞ STRATEJİSİ: (Hangi FVG veya OB seviyesinden girilmeli?)
* GEÇERSİZLİK (STOP): (ATR veya Market Structure bozulma seviyesi neresi?)
* HEDEF (TP): (Hangi likidite havuzu hedeflenmeli?)"""
    
    with st.sidebar: st.code(prompt, language="text")
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
    render_ict_panel(calculate_ict_concepts(st.session_state.ticker))
    
    st.markdown("<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:20px;'>📡 Haber Akışı</div>", unsafe_allow_html=True)
    news = fetch_google_news(st.session_state.ticker)
    if news:
        cols = st.columns(2)
        for i, n in enumerate(news):
            with cols[i%2]: st.markdown(f"""<div class="news-card" style="border-left-color: {n['color']};"><a href="{n['link']}" target="_blank" class="news-title">{n['title']}</a><div class="news-meta">{n['date']} • {n['source']}</div></div>""", unsafe_allow_html=True)
    else: st.info("Haber yok.")

with col_right:
    sent_data = calculate_sentiment_score(st.session_state.ticker)
    render_sentiment_card(sent_data)
    
    render_detail_card(st.session_state.ticker)
    
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
                    row1 = df1[df1["Sembol"] == sym].iloc[0]; row2 = df2[df2["Sembol"] == sym].iloc[0]
                    commons.append({"symbol": sym, "r1": row1, "r2": row2, "combined": float(row1["Skor"]) + float(row2["Skor"])})
                for item in sorted(commons, key=lambda x: x["combined"], reverse=True):
                    sym = item["symbol"]
                    c1, c2 = st.columns([0.2, 0.8])
                    if c1.button("★", key=f"c_s_{sym}"): toggle_watchlist(sym); st.rerun()
                    if c2.button(f"{sym} | R1: {item['r1']['Skor']}/8 | R2: {item['r2']['Skor']}/8", key=f"c_b_{sym}"): on_scan_result_click(sym); st.rerun()
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
                    sym = row["Sembol"]; c1, c2 = st.columns([0.2, 0.8])
                    if c1.button("★", key=f"r1_{i}"): toggle_watchlist(sym); st.rerun()
                    if c2.button(f"🔥 {row['Skor']}/8 | {sym}", key=f"r1_b_{i}"): on_scan_result_click(sym); st.rerun()
                    st.caption(row['Nedenler'])

    with tab2:
        if st.button(f"🚀 RADAR 2 Tara", type="primary"):
            with st.spinner("Taranıyor..."): st.session_state.radar2_data = radar2_scan(ASSET_GROUPS.get(st.session_state.category, []))
        if st.session_state.radar2_data is not None:
            with st.container(height=500):
                for i, row in st.session_state.radar2_data.iterrows():
                    sym = row["Sembol"]; c1, c2 = st.columns([0.2, 0.8])
                    if c1.button("★", key=f"r2_{i}"): toggle_watchlist(sym); st.rerun()
                    if c2.button(f"🚀 {row['Skor']}/8 | {sym} | {row['Setup']}", key=f"r2_b_{i}"): on_scan_result_click(sym); st.rerun()
                    st.caption(f"Trend: {row['Trend']} | RS: {row['RS']}%")

    with tab3:
        if st.button("⚡ Listeyi Tara", type="secondary"):
            with st.spinner("..."): st.session_state.scan_data = analyze_market_intelligence(st.session_state.watchlist)
        for sym in st.session_state.watchlist:
            c1, c2 = st.columns([0.2, 0.8])
            if c1.button("❌", key=f"wl_d_{sym}"): toggle_watchlist(sym); st.rerun()
            if c2.button(sym, key=f"wl_g_{sym}"): on_scan_result_click(sym); st.rerun()
