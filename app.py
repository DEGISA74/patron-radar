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
    "GC=F", "SI=F",
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
    "S&P 500 (TOP 300)": sorted(list(set(raw_sp500))),
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
        st.session_state.category = new_cat
        st.session_state.ticker = ASSET_GROUPS[new_cat][0]
        st.session_state.scan_data = None
        st.session_state.radar2_data = None

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
        if st.button("📋 Analiz Metnini Hazırla", type="primary"):
            st.session_state.generate_prompt = True

# --- ANALİZ MOTORLARI (CACHED) ---
@st.cache_data(ttl=3600)
def analyze_market_intelligence(asset_list):
    signals = []
    try:
        data = yf.download(asset_list, period="6mo", group_by='ticker', threads=True, progress=False)
    except:
        return pd.DataFrame()
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]:
                    df = data[symbol].copy()
                else:
                    continue
            else:
                if len(asset_list) == 1:
                    df = data.copy()
                else:
                    continue
            if df.empty or 'Close' not in df.columns: continue
            df = df.dropna(subset=['Close'])
            if len(df) < 60: continue
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
            if bb_width.iloc[-1] <= bb_width.tail(60).min() * 1.1:
                score += 1; reasons.append("🚀 Squeeze")
            if daily_range.iloc[-1] == daily_range.tail(4).min() and daily_range.iloc[-1] > 0:
                score += 1; reasons.append("🔇 NR4")
            if ((ema5.iloc[-1] > ema20.iloc[-1]) and (ema5.iloc[-2] <= ema20.iloc[-2])) or ((ema5.iloc[-2] > ema20.iloc[-2]) and (ema5.iloc[-3] <= ema20.iloc[-3])):
                score += 1; reasons.append("⚡ Trend")
            if hist.iloc[-1] > hist.iloc[-2]:
                score += 1; reasons.append("🟢 MACD")
            if williams_r.iloc[-1] > -50:
                score += 1; reasons.append("🔫 W%R")
            if curr_vol > avg_vol * 1.2:
                score += 1; reasons.append("🔊 Hacim")
            if curr_c >= high.tail(20).max() * 0.98:
                score += 1; reasons.append("🔨 Breakout")
            rsi_c = rsi.iloc[-1]
            if 30 < rsi_c < 65 and rsi_c > rsi.iloc[-2]:
                score += 1; reasons.append("⚓ RSI Güçlü")
            if score > 0:
                signals.append({
                    "Sembol": symbol,
                    "Fiyat": f"{curr_c:.2f}",
                    "Skor": score,
                    "Nedenler": " | ".join(reasons)
                })
        except:
            continue
    return pd.DataFrame(signals).sort_values(by="Skor", ascending=False) if signals else pd.DataFrame()

@st.cache_data(ttl=3600)
def radar2_scan(asset_list, min_price=5, max_price=500, min_avg_vol_m=1.0):
    if not asset_list: return pd.DataFrame()
    try:
        data = yf.download(asset_list, period="1y", group_by="ticker", threads=True, progress=False)
    except:
        return pd.DataFrame()
    try:
        idx = yf.download("^GSPC", period="1y", progress=False)["Close"]
    except:
        idx = None
    results = []
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol not in data.columns.levels[0]: continue
                df = data[symbol].copy()
            else:
                if len(asset_list) == 1:
                    df = data.copy()
                else:
                    continue
            if df.empty or 'Close' not in df.columns: continue
            df = df.dropna(subset=['Close'])
            if len(df) < 120: continue
            close = df['Close']; high = df['High']; volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))
            curr_c = float(close.iloc[-1])
            if curr_c < min_price or curr_c > max_price: continue
            avg_vol_20 = float(volume.rolling(20).mean().iloc[-1])
            if avg_vol_20 < min_avg_vol_m * 1e6: continue
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
            hist = (close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()) - (close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()).ewm(span=9, adjust=False).mean()
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
            avg_vol_20 = max(avg_vol_20, 1)
            vol_spike = volume.iloc[-1] > avg_vol_20 * 1.3
            if trend == "Boğa" and breakout_ratio >= 0.97:
                setup = "Breakout"; score += 2; tags.append("Zirve")
            if vol_spike:
                score += 1; tags.append("Hacim+")
            if trend == "Boğa" and setup == "-":
                if sma20.iloc[-1] <= curr_c <= sma50.iloc[-1] * 1.02 and 40 <= rsi_c <= 55:
                    setup = "Pullback"; score += 2; tags.append("Düzeltme")
                if volume.iloc[-1] < avg_vol_20 * 0.9:
                    score += 1; tags.append("Sığ Satış")
            if setup == "-":
                if rsi.iloc[-2] < 30 <= rsi_c and hist.iloc[-1] > hist.iloc[-2]:
                    setup = "Dip Dönüşü"; score += 2; tags.append("Dip Dönüşü")
            if rs_score > 0:
                score += 1; tags.append("RS+")
            if trend == "Boğa":
                score += 1
            elif trend == "Ayı":
                score -= 1
            if score > 0:
                results.append({
                    "Sembol": symbol,
                    "Fiyat": round(curr_c, 2),
                    "Trend": trend,
                    "Setup": setup,
                    "Skor": score,
                    "RS": round(rs_score * 100, 1),
                    "Etiketler": " | ".join(tags)
                })
        except:
            continue
    return pd.DataFrame(results).sort_values(by=["Skor", "RS"], ascending=False).head(50) if results else pd.DataFrame()

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

# --- ICT (YENİ NESİL - PRICE ACTION ODAKLI) ---
@st.cache_data(ttl=600)
def calculate_ict_concepts_v2(ticker):
    """
    Gelişmiş ICT konseptlerini (BOS, FVG, OB, Premium/Discount) hesaplar.
    """
    try:
        # Veri İndirme (6 aylık Günlük Veri)
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df.empty: return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df['Close']; high = df['High']; low = df['Low']; open_p = df['Open']
        curr_price = float(close.iloc[-1])
        
        # Güncel Volatilite (ATR) ve Eşik Değeri
        atr = (high - low).rolling(14).mean()
        current_atr = float(atr.iloc[-1]) if not atr.empty else 1.0
        atr_thresh = current_atr * 0.2 # FVG/OB için minimum boyut eşiği (Örnek: %20 ATR)

        # 1. SWING NOKTALARI (5 mumlu)
        swing_points = {"high": [], "low": []}
        for i in range(2, len(df)-2):
            # Swing High (2 sol, 2 sağ)
            if high.iloc[i] > high.iloc[i-1] and high.iloc[i] > high.iloc[i-2] and \
               high.iloc[i] > high.iloc[i+1] and high.iloc[i] > high.iloc[i+2]:
                swing_points["high"].append((i, float(high.iloc[i])))
            # Swing Low (2 sol, 2 sağ)
            if low.iloc[i] < low.iloc[i-1] and low.iloc[i] < low.iloc[i-2] and \
               low.iloc[i] < low.iloc[i+1] and low.iloc[i] < low.iloc[i+2]:
                swing_points["low"].append((i, float(low.iloc[i])))

        # Yeterli veri yoksa erken çıkış
        if len(swing_points["high"]) < 2 or len(swing_points["low"]) < 2:
            return {"summary": "Veri/Swing Yetersiz", "structure": "Nötr", "position": "Nötr", "fvg": "Yok", "ob": "Yok", "liq": "Yok", "golden_text": "-", "golden_setup": False, "sh": "-", "sl": "-", "mid": "-"}

        # En son ve bir önceki ana swing noktaları
        last_sh_idx, last_sh_val = swing_points["high"][-1]
        last_sl_idx, last_sl_val = swing_points["low"][-1]
        
        # Major swing noktaları (genellikle sondan ikinci)
        major_sh_val = swing_points["high"][-2][1] if len(swing_points["high"]) >= 2 else last_sh_val
        major_sl_val = swing_points["low"][-2][1] if len(swing_points["low"]) >= 2 else last_sl_val

        # 2. MARKET YAPISI (BOS/CHoCH) ve BIAS
        structure_verdict = "KONSOLİDASYON"
        bias = "Nötr"
        
        if curr_price > major_sh_val:
            structure_verdict = "BULLISH (BOS-ONAY)"
            bias = "Long"
        elif curr_price < major_sl_val:
            structure_verdict = "BEARISH (BOS-ONAY)"
            bias = "Short"
        else:
            # İç Yapı Kırılımı Kontrolü
            if last_sh_val > swing_points["high"][-2][1] and last_sl_val > swing_points["low"][-2][1]:
                # Yüksek dipler ve yüksek tepeler (iç yapı)
                structure_verdict = "BULLISH (İç Yapı)"
                bias = "Long"
            elif last_sh_val < swing_points["high"][-2][1] and last_sl_val < swing_points["low"][-2][1]:
                # Alçak dipler ve alçak tepeler (iç yapı)
                structure_verdict = "BEARISH (İç Yapı)"
                bias = "Short"
            elif curr_price > last_sh_val:
                structure_verdict = "CHoCH (Bulls)" # CHoCH/Erken Yapı Değişimi
                bias = "Long"
            elif curr_price < last_sl_val:
                structure_verdict = "CHoCH (Bears)" # CHoCH/Erken Yapı Değişimi
                bias = "Short"
        
        # 3. PREMIUM / DISCOUNT (FIBO)
        range_high = last_sh_val 
        range_low = last_sl_val 
        mid_point = (range_high + range_low) / 2
        
        is_discount = curr_price < mid_point
        position_label = "DENGEDE"
        
        if curr_price < range_low:
             position_label = "DEEP DISCOUNT"
        elif curr_price < mid_point:
            position_label = "DISCOUNT (Ucuz)"
        elif curr_price > range_high:
             position_label = "PREMIUM+"
        else:
            position_label = "PREMIUM (Pahalı)"

        # 4. FVG (FAIR VALUE GAP) Tespiti (Son 30 mum)
        fvg_entry = "Belirgin Gap Yok"
        fvg_type = "-"
        
        for i in range(len(df)-2, len(df)-30, -1):
            if low.iloc[i] > high.iloc[i-2] and low.iloc[i] - high.iloc[i-2] > atr_thresh:
                # Bullish FVG (Fiyatın altına inmesi beklenen yeşil gap)
                fvg_low = high.iloc[i-2]
                fvg_high = low.iloc[i]
                if curr_price < fvg_low or curr_price > fvg_high: continue # İçi dolmuşsa veya çok uzaktaysa geç
                
                fvg_entry = f"🟢 {fvg_low:.2f}-{fvg_high:.2f}"
                fvg_type = "Bullish FVG"
                break
            elif high.iloc[i] < low.iloc[i-2] and low.iloc[i-2] - high.iloc[i] > atr_thresh:
                # Bearish FVG (Fiyatın üstüne çıkması beklenen kırmızı gap)
                fvg_low = high.iloc[i]
                fvg_high = low.iloc[i-2]
                if curr_price > fvg_high or curr_price < fvg_low: continue # İçi dolmuşsa veya çok uzaktaysa geç

                fvg_entry = f"🔴 {fvg_low:.2f}-{fvg_high:.2f}"
                fvg_type = "Bearish FVG"
                break

        # 5. ORDER BLOCK (OB) Tespiti
        ob_entry = "-"
        ob_type = "Güvenli Giriş"
        
        if bias == "Long" or structure_verdict == "CHoCH (Bulls)":
            # Bullish OB: Son SL'den önceki düşüş mumu
            if last_sl_idx > 0:
                # Son SL'nin oluşmasına neden olan mum
                ob_idx = last_sl_idx 
                ob_low_val = low.iloc[ob_idx]
                ob_high_val = max(open_p.iloc[ob_idx], close.iloc[ob_idx])
                ob_entry = f"🛡️ {ob_low_val:.2f} - {ob_high_val:.2f}$"
                ob_type = "Bullish OB"
        elif bias == "Short" or structure_verdict == "CHoCH (Bears)":
            # Bearish OB: Son SH'den önceki yükseliş mumu
            if last_sh_idx > 0:
                # Son SH'nin oluşmasına neden olan mum
                ob_idx = last_sh_idx 
                ob_high_val = high.iloc[ob_idx]
                ob_low_val = min(open_p.iloc[ob_idx], close.iloc[ob_idx])
                ob_entry = f"⚔️ {ob_low_val:.2f} - {ob_high_val:.2f}$"
                ob_type = "Bearish OB"
                
        # 6. LİKİDİTE HEDEFİ (LIQ - BSL/SSL)
        liq_target = "-"
        liq_label = "Bir Sonraki Hedef (BSL/SSL)"
        
        if bias == "Long":
             liq_target = f"BSL @ {major_sh_val:.2f}$ (Major)"
        elif bias == "Short":
             liq_target = f"SSL @ {major_sl_val:.2f}$ (Major)"
        else:
             liq_target = f"EQH @ {range_high:.2f}$ / EQL @ {range_low:.2f}$"
             liq_label = "Range Sınırları"
        
        # 7. GOLDEN SETUP (Discount'ta FVG ile Long veya Premium'da FVG ile Short)
        golden_setup = False
        golden_txt = "-"
        if bias == "Long" and is_discount and "🟢" in fvg_entry:
            golden_setup = True
            golden_txt = "🔥 GOLDEN LONG (BOS/CHoCH+Ucuz+B-FVG)"
        elif bias == "Short" and not is_discount and "🔴" in fvg_entry:
            golden_setup = True
            golden_txt = "🔥 GOLDEN SHORT (BOS/CHoCH+Pahalı+B-FVG)"

        summary_line = f"🧩 YAPI: {structure_verdict} | KONUM: {position_label}"
        
        return {
            "summary": summary_line,
            "structure": structure_verdict,
            "position": position_label,
            "fvg": fvg_entry,
            "ob": ob_entry,
            "ob_label": ob_type,
            "liquidity": liq_target,
            "liq_label": liq_label,
            "eqh": liq_target, 
            "fibo": f"EQ: {mid_point:.2f}$",
            "golden_text": golden_txt,
            "golden_setup": golden_setup,
            "sh": f"SH @ {last_sh_val:.2f}$",
            "sl": f"SL @ {last_sl_val:.2f}$",
            "mid": f"EQ @ {mid_point:.2f}$"
        }
    except Exception as e:
        # Hata durumunda bilgilendirici çıktı
        return {"summary": f"Hata: {e.__class__.__name__}", "structure": "HATA", "position": "HATA", "fvg": "HATA", "ob": "HATA", "liq": "HATA", "golden_text": "HATA", "golden_setup": False, "sh": "-", "sl": "-", "mid": "-"}


@st.cache_data(ttl=600)
def get_tech_card_data(ticker):
    try:
        df = yf.download(ticker, period="2y", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close = df['Close']; high = df['High']; low = df['Low']
        sma50 = close.rolling(50).mean().iloc[-1]
        sma100 = close.rolling(100).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1]
        ema144 = close.ewm(span=144, adjust=False).mean().iloc[-1]
        atr = (high-low).rolling(14).mean().iloc[-1]
        return {
            "sma50": sma50,
            "sma100": sma100,
            "sma200": sma200,
            "ema144": ema144,
            "stop_level": close.iloc[-1] - (2 * atr),
            "risk_pct": (2 * atr) / close.iloc[-1] * 100,
            "atr": atr
        }
    except:
        return None
    

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
    def icon(cond): return "✅" if cond else "❌" # Bu fonksiyonu da kopyaladım
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
    if not analysis: return
    
    # Golden Setup için özel stil
    golden_style = "background-color: #fef3c7; color: #b45309; border: 1px solid #f97316;" if analysis['golden_setup'] else "background-color: #f8f9fa; color: #64748B; border: 1px solid #dee2e6;"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-header">🧠 ICT & Price Action | Güncel Yapı</div>
        <div class="info-row" style="border-bottom: 1px dashed #e5e7eb; padding-bottom:4px; margin-bottom:6px;">
            <div style="font-weight:700; color:#1e40af; font-size:0.8rem;">{analysis['summary']}</div>
        </div>
        <div class="info-row"><div class="label-long">Genel Yön:</div><div class="info-val">{analysis['structure']}</div></div>
        <div class="info-row"><div class="label-long">Konum:</div><div class="info-val">{analysis['position']}</div></div>
        
        <hr style="margin-top:0.2rem; margin-bottom:0.5rem;"/>
        
        <div class="info-row"><div class="label-long">SWING HIGH:</div><div class="info-val">{analysis.get('sh', '-')}</div></div>
        <div class="info-row"><div class="label-long">SWING LOW:</div><div class="info-val">{analysis.get('sl', '-')}</div></div>
        <div class="info-row"><div class="label-long">EQUILIBRIUM:</div><div class="info-val">{analysis.get('mid', '-')}</div></div>
        
        <hr style="margin-top:0.2rem; margin-bottom:0.5rem;"/>
        
        <div class="info-row"><div class="label-long">GİRİŞ ({analysis['ob_label']}):</div><div class="info-val">{analysis['ob']}</div></div>
        <div class="info-row"><div class="label-long">FIRSAT (FVG):</div><div class="info-val">{analysis['fvg']}</div></div>
        <div class="info-row"><div class="label-long">HEDEF ({analysis['liq_label']}):</div><div class="info-val">{analysis['eqh']}</div></div>
        
        <div style="margin-top: 8px; padding: 4px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; text-align: center; {golden_style}">
            {analysis['golden_text']}
        </div>
    </div>
    """, unsafe_allow_html=True)


# --- ARAYÜZ (FİLTRELER YERİNDE SABİT) ---
BULL_ICON_B64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAOAAAADhCAMAAADmr0l2AAAAb1BMVEX///8AAAD8/PzNzc3y8vL39/f09PTw8PDs7Ozp6eny8vLz8/Pr6+vm5ubt7e3j4+Ph4eHf39/c3NzV1dXS0tLKyso/Pz9ERERNTU1iYmJSUlJxcXF9fX1lZWV6enp2dnZsbGxra2uDg4N0dHR/g07fAAAE70lEQVR4nO2d27qrIAyF131wRPT+z3p2tX28dE5sC4i9x3+tC0L4SAgJ3Y2Hw+FwOBwOh8PhcDgcDofD4XA4HA6Hw+FwOBwOh8PhcDg/I+7H8zz/i2E3/uI4/o1xM0L4F8d2hPA/jqsRwj84niOEf26cRgj/2HiOENZ3H/8B4/z57mP4AONqhPDnjf+CceOC8a2t+wfj2l+96lWvevWrX/36L8Jm3b3z/cbtxPCPi+0J4R+3d/9w++K9Y2xPCA9jrO4fbq961ate9apXvesq4+p7hPfPzWeG+5vZHr/iVzW2J4R3MLYnhHcwtifE8I7G1v4BPvKvGdsTwjsY2xPCOxjbE8I7GNsTwjsY2xPCOxjbE8I7GNsTwjsY2xPCOxjbE8I7GNsTwjsY2xPCOxjbE8I7GNv/B/Dup/9ijO2J4R2MbQjhHYytCeEdjG0J4R2MbQjhHYwtCeEdiv//gfmM2xPCOxjbE8I7GNsTwjsY2xPCOxjbE8I7GNsTwjsY2xPCOxjbE8I7GNsTwjsY2/8H8O6n/2Ls/v8Xf+3f/w/GNsTwjsY2xPCOxjbE8I7GNsTwjsY2xPCOxjbE8I7GNsTwjsY2xPCOxjbE8I7GNsTwjsY2xPCOxjbE8I7GNsTwjsY2xPCOxjbE8I7GNsTwjsY2xPCOxjbE8I7GNsTwjsY2xPCOxjbE8I7GNsTwjsY2xPCOxjbE8I7GNsTwjsY2xPCOxjbE8I7GNsTwjsY2xPCOxjbE8I7GNv/B/Duf4ixNSG8g7E1IbyDsTUhvIOxNSG8g7E1IbyDsTUhvIOxNSG8g7E1IbyDsTUhvIOx/X8A7/6HGNsTwjsY2xPCOxjbE8I7GNv/B/Dup/9ijE0I72BsTgjvYMxHCA+Hw+FwOBwOh8PhcDgcDofD4XA4HA6Hw+H8B/DDT05v9eU/AAAAAElFTkSuQmCC"

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
        label_visibility="collapsed"
    )
with col_search_in:
    st.text_input("Manuel", placeholder="Kod", key="manual_input_key", label_visibility="collapsed")
with col_search_btn:
    st.button("Ara", on_click=on_manual_button_click)

st.markdown("<hr style='margin-top:0.5rem; margin-bottom:0.5rem;'>", unsafe_allow_html=True)

# PROMPT TETİKLEYİCİ
if 'generate_prompt' not in st.session_state:
    st.session_state.generate_prompt = False
if st.session_state.generate_prompt:
    t = st.session_state.ticker
    try:
        inf = yf.Ticker(t).info
        price = inf.get('currentPrice') or inf.get('regularMarketPrice') or "Bilinmiyor"
    except:
        price = "Bilinmiyor"
    
    prompt = f"""Rol: Kıdemli Fon Yöneticisi ve Algoritmik Trader (Market Maker Bakış Açısı).

Bağlam: Sana "Patronun Terminali" adlı gelişmiş bir analiz panelinden alınan {t} hissesinin ekran görüntüsünü sunuyorum. Bu verilerde 4 farklı katman var:

1. Sentiment & Psikoloji: Piyasanın korku/iştah durumu (0-100 Puan).
2. Radar Sinyalleri: Momentum ve Trend algoritmalarının skorları.
3. Teknik Kart: Ortalamalar (SMA/EMA) ve ATR bazlı risk seviyeleri.
4. ICT & Price Action: Kurumsal ayak izleri (Order Block, FVG, Breaker, Likidite, Golden Setup). (Gelişmiş Yapı Analizi Kullanıldı).

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
    
    with st.sidebar:
        st.code(prompt, language="text")
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
    render_tradingview_widget(st.session_state.ticker, height=650)
    render_ict_panel(calculate_ict_concepts_v2(st.session_state.ticker))
    
    # --- GÜNCELLENEN HABER BAŞLIĞI ---
    st.markdown(
        f"<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:20px;'>📡 {st.session_state.ticker} hakkında haberler ve analizler</div>",
        unsafe_allow_html=True
    )

    # --- HABER AKIŞI: SABİT HABER SİTESİ LİNKLERİ (SeekingAlpha, Yahoo, Nasdaq, StockAnalysis, Finviz, UnusualWhales) ---
    symbol_raw = st.session_state.ticker

    base_symbol = (
        symbol_raw.replace(".IS", "")
                  .replace("=F", "")
                  .replace("-USD", "")
    )
    lower_symbol = base_symbol.lower()

    seekingalpha_url   = f"https://seekingalpha.com/symbol/{base_symbol}/news"
    yahoo_url          = f"https://finance.yahoo.com/quote/{base_symbol}/news"
    nasdaq_url         = f"https://www.nasdaq.com/market-activity/stocks/{lower_symbol}/news-headlines"
    stockanalysis_url  = f"https://stockanalysis.com/stocks/{lower_symbol}/"
    finviz_url         = f"https://finviz.com/quote.ashx?t={base_symbol}&p=d"
    unusual_url        = f"https://unusualwhales.com/stock/{base_symbol}/overview"

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
    
    render_detail_card(st.session_state.ticker)
    render_radar_params_card() 
    
    xray_data = get_deep_xray_data(st.session_state.ticker)
    render_deep_xray_card(xray_data)

    st.markdown(
        f"<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:10px; color:#1e3a8a; background-color:{current_theme['box_bg']}; padding:5px; border-radius:5px; border:1px solid #1e40af;'>🎯 Ortak Fırsatlar</div>",
        unsafe_allow_html=True
    )
    with st.container(height=250):
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
        if st.button(f"⚡ {st.session_state.category} Tara", type="primary"):
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
        if st.button(f"🚀 RADAR 2 Tara", type="primary"):
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
        if st.button("⚡ Listeyi Tara", type="secondary"):
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


