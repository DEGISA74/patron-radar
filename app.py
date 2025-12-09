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
    page_title="Patronun Terminali v4.1.0",
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

# CSS NOTU: Python f-string içinde CSS süslü parantezleri {{ ve }} olarak çiftlenmiştir.
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&display=swap');
    
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {current_theme['text']}; }}
    .stApp {{ background-color: {current_theme['bg']}; }}
    
    /* Layout Sıkılaştırma */
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
    
    /* ORTAK KART STİLİ (Hem Teknik hem ICT için) */
    .info-card {{
        background: {current_theme['box_bg']}; border: 1px solid {current_theme['border']};
        border-radius: 6px; padding: 8px; margin-top: 5px; margin-bottom: 10px;
        font-size: 0.8rem; font-family: 'Inter', sans-serif;
    }}
    .info-header {{ font-weight: 700; color: #1e3a8a; border-bottom: 1px solid {current_theme['border']}; padding-bottom: 4px; margin-bottom: 4px; }}
    .info-row {{ display: flex; align-items: center; margin-bottom: 3px; }}
    
    /* Teknik Kart Etiketleri (Kısa) */
    .label-short {{ font-weight: 600; color: #64748B; width: 80px; flex-shrink: 0; }}
    
    /* ICT Kart Etiketleri (Uzun) */
    .label-long {{ font-weight: 600; color: #64748B; width: 165px; flex-shrink: 0; }}
    
    .info-val {{ color: {current_theme['text']}; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; }}
    
    /* LOGO STİLİ */
    .header-logo {{ width: 40px; height: auto; margin-right: 10px; }}
</style>
""", unsafe_allow_html=True)

# --- VERİTABANI (SQLITE) ---
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

if not os.path.exists(DB_FILE):
    init_db()

# --- VARLIK LİSTELERİ ---
ASSET_GROUPS = {
    "S&P 500 (TOP 300)": [
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
    ],
    "NASDAQ (TOP 100)": [
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
    ],
    "EMTİA (ALTIN/GÜMÜŞ)": ["GC=F", "SI=F"]
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
        st.caption("ChatGPT/Gemini için analiz metni (ICT verileri ile):")
        if st.button("📋 Analiz Metnini Hazırla", type="primary"):
            t = st.session_state.ticker
            ict = st.session_state.get("ict_analysis")
            tech = st.session_state.get("tech_card_data") or {}
            
            lines = []
            lines.append(f"Rol: Profesyonel ICT & Price Action Trader.")
            lines.append(f"Enstrüman: {t}")
            lines.append("")
            
            if ict:
                # Üst sinyaller
                top_names = ict.get("top_signals", [])
                if top_names:
                    lines.append("Aktif ICT Parametreleri (en güçlü 3): " + ", ".join(top_names))
                    lines.append("")
                
                lines.append("Ham ICT Verileri:")
                lines.append(f"- Market Structure: {ict.get('structure', '-')}")
                lines.append(f"- Fiyat Konumu: {ict.get('position', '-')}")
                lines.append(f"- Kurumsal OB: {ict.get('ob', '-')}")
                lines.append(f"- Breaker Block (BB): {ict.get('bb', '-')}")
                
                eqh = ict.get("eqh")
                eql = ict.get("eql")
                eqh_txt = f"{eqh:.2f}$" if isinstance(eqh, (int, float, np.floating)) else "-"
                eql_txt = f"{eql:.2f}$" if isinstance(eql, (int, float, np.floating)) else "-"
                lines.append(f"- EQH (Eşit Tepeler): {eqh_txt}")
                lines.append(f"- EQL (Eşit Dipler): {eql_txt}")
                
                lines.append(f"- FVG Bölgesi: {ict.get('fvg', '-')}")
                lines.append(f"- Likidite Hedefi: {ict.get('liquidity', '-')}")
                lines.append(f"- Fibo / OTE: {ict.get('fibo', '-')}")
                
                golden_text = ict.get("golden_text", "-")
                lines.append(f"- Golden Setup: {golden_text}")
            else:
                lines.append("Not: ICT verisi henüz hesaplanmamış görünüyor. Terminalden grafiği bir kez yükleyip tekrar deneyebilirsin.")
            
            lines.append("")
            
            if tech:
                stop_level = tech.get("stop_level")
                risk_pct = tech.get("risk_pct")
                sma50 = tech.get("sma50")
                sma100 = tech.get("sma100")
                sma200 = tech.get("sma200")
                ema144 = tech.get("ema144")
                
                lines.append("Teknik Kart Özeti:")
                if sma50 is not None:
                    lines.append(f"- Ortalama Seviyeler: SMA50={sma50:.2f}, SMA100={sma100:.2f}, SMA200={sma200:.2f}, EMA144={ema144:.2f}")
                if stop_level is not None:
                    lines.append(f"- ATR Tabanlı Stop (2x): {stop_level:.2f}$ (Risk: -{risk_pct:.1f}%)")
            else:
                lines.append("Teknik kart verisi yok (henüz yüklenmemiş olabilir).")
            
            lines.append("")
            lines.append("Görev:")
            lines.append(f"- {t} için üstteki verileri kullanarak, günlük zaman diliminde Price Action + ICT temelli detaylı bir analiz yaz.")
            lines.append("- Yön (bias), olası alım/satım bölgeleri, likidite hedefleri ve stop seviyelerini açıkla.")
            lines.append("- Özellikle Breaker Block, EQH/EQL ve varsa Golden Setup bölgesini önceliklendir.")
            
            prompt_text = "\n".join(lines)
            st.code(prompt_text, language="text")

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
    if new_asset:
        st.session_state.ticker = new_asset

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

# --- ANALİZ MOTORLARI (CACHED) ---
@st.cache_data(ttl=3600)  # 1 Saatlik Cache
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

            if df.empty or 'Close' not in df.columns:
                continue
            df = df.dropna(subset=['Close'])
            if len(df) < 60:
                continue

            close = df['Close']
            high = df['High']
            low = df['Low']
            volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))
            
            ema5 = close.ewm(span=5, adjust=False).mean()
            ema20 = close.ewm(span=20, adjust=False).mean()
            sma20 = close.rolling(20).mean()
            std20 = close.rolling(20).std()
            bb_width = ((sma20 + 2*std20) - (sma20 - 2*std20)) / (sma20 + 0.0001)
            hist = (close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()) - \
                   (close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()).ewm(span=9, adjust=False).mean()
            
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + (gain / loss)))
            williams_r = (high.rolling(14).max() - close) / (high.rolling(14).max() - low.rolling(14).min()) * -100
            daily_range = high - low

            score = 0
            reasons = []
            curr_c = float(close.iloc[-1])
            curr_vol = float(volume.iloc[-1])
            avg_vol = float(volume.rolling(5).mean().iloc[-1]) if len(volume) > 5 else 1.0

            if bb_width.iloc[-1] <= bb_width.tail(60).min() * 1.1:
                score += 1
                reasons.append("🚀 Squeeze")
            if daily_range.iloc[-1] == daily_range.tail(4).min() and daily_range.iloc[-1] > 0:
                score += 1
                reasons.append("🔇 NR4")
            if ((ema5.iloc[-1] > ema20.iloc[-1]) and (ema5.iloc[-2] <= ema20.iloc[-2])) or \
               ((ema5.iloc[-2] > ema20.iloc[-2]) and (ema5.iloc[-3] <= ema20.iloc[-3])):
                score += 1
                reasons.append("⚡ Trend")
            if hist.iloc[-1] > hist.iloc[-2]:
                score += 1
                reasons.append("🟢 MACD")
            if williams_r.iloc[-1] > -50:
                score += 1
                reasons.append("🔫 W%R")
            if curr_vol > avg_vol * 1.2:
                score += 1
                reasons.append("🔊 Hacim")
            if curr_c >= high.tail(20).max() * 0.98:
                score += 1
                reasons.append("🔨 Breakout")
            rsi_c = rsi.iloc[-1]
            if 30 < rsi_c < 65 and rsi_c > rsi.iloc[-2]:
                score += 1
                reasons.append("⚓ RSI Güçlü")

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

@st.cache_data(ttl=3600)  # 1 Saatlik Cache
def radar2_scan(asset_list, min_price=5, max_price=500, min_avg_vol_m=1.0):
    if not asset_list:
        return pd.DataFrame()
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
                if symbol not in data.columns.levels[0]:
                    continue
                df = data[symbol].copy()
            else:
                if len(asset_list) == 1:
                    df = data.copy()
                else:
                    continue

            if df.empty or 'Close' not in df.columns:
                continue
            df = df.dropna(subset=['Close'])
            if len(df) < 120:
                continue

            close = df['Close']
            high = df['High']
            volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))
            curr_c = float(close.iloc[-1])
            if curr_c < min_price or curr_c > max_price:
                continue
            avg_vol_20 = float(volume.rolling(20).mean().iloc[-1])
            if avg_vol_20 < min_avg_vol_m * 1e6:
                continue

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
            
            recent_high_60 = float(high.rolling(60).max().iloc[-1])
            breakout_ratio = curr_c / recent_high_60 if recent_high_60 > 0 else 0
            
            rs_score = 0.0
            if idx is not None and len(close) > 60 and len(idx) > 60:
                common_index = close.index.intersection(idx.index)
                if len(common_index) > 60:
                    cs = close.reindex(common_index)
                    isx = idx.reindex(common_index)
                    rs_score = float((cs.iloc[-1]/cs.iloc[-60]-1) - (isx.iloc[-1]/isx.iloc[-60]-1))

            setup = "-"
            tags = []
            score = 0
            avg_vol_20 = max(avg_vol_20, 1)
            vol_spike = volume.iloc[-1] > avg_vol_20 * 1.3
            hist = (close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()) - \
                   (close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()).ewm(span=9, adjust=False).mean()

            if trend == "Boğa" and breakout_ratio >= 0.97:
                setup = "Breakout"
                score += 2
                tags.append("Zirve")
                if vol_spike:
                    score += 1
                    tags.append("Hacim+")
            
            if trend == "Boğa" and setup == "-":
                if sma20.iloc[-1] <= curr_c <= sma50.iloc[-1] * 1.02 and 40 <= rsi_c <= 55:
                    setup = "Pullback"
                    score += 2
                    tags.append("Düzeltme")
                    if volume.iloc[-1] < avg_vol_20 * 0.9:
                        score += 1
                        tags.append("Sığ Satış")

            if setup == "-":
                if rsi.iloc[-2] < 30 <= rsi_c and hist.iloc[-1] > hist.iloc[-2]:
                    setup = "Dip Dönüşü"
                    score += 2
                    tags.append("Dip Dönüşü")

            if rs_score > 0:
                score += 1
                tags.append("RS+")
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

# --- ICT ANALİZİ (GELİŞMİŞ) ---
@st.cache_data(ttl=600)  # 10 Dakikalık Cache
def calculate_ict_concepts(ticker):
    try:
        df = yf.download(ticker, period="3mo", progress=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        close = df['Close']
        high = df['High']
        low = df['Low']
        curr_price = float(close.iloc[-1])
        
        # Market Yapısı
        market_structure = "Nötr / Yatay"
        is_bullish = False
        if close.iloc[-1] > high.tail(20).iloc[-5:].max():
            market_structure = "🟢 YÜKSELİŞ (Trend Güçlü)"
            is_bullish = True
        elif close.iloc[-1] < low.tail(20).iloc[-5:].min():
            market_structure = "🔴 DÜŞÜŞ (Yapı Bozuldu)"
            is_bullish = False
            
        # Range ve Konum (Discount/Premium)
        range_high = float(high.tail(60).max())
        range_low = float(low.tail(60).min())
        mid_point = (range_high + range_low) / 2.0
        
        position_text = "Nötr Bölge"
        is_discount = False
        discount_pct = None
        premium_pct = None
        
        if curr_price < mid_point:
            discount_pct = 100 - ((curr_price - range_low) / (range_high - range_low) * 100)
            position_text = f"✅ UCUZ BÖLGE (Discount: %{discount_pct:.1f})"
            is_discount = True
        else:
            premium_pct = ((curr_price - range_low) / (range_high - range_low) * 100)
            position_text = f"⚠️ PAHALI BÖLGE (Premium: %{premium_pct:.1f})"
            is_discount = False
        
        # Fibonacci Seviyeleri / OTE
        fibo_50 = mid_point
        ote_level_bull = range_low + (range_high - range_low) * 0.382  # %61.8 retrace'e denk gelecek basit yaklaşım
        ote_level_bear = range_low + (range_high - range_low) * 0.618
        ote_level = ote_level_bull if is_bullish else ote_level_bear
        fibo_text = f"📐 Fibo %50: {fibo_50:.2f}$ | OTE (%62 civarı): {ote_level:.2f}$"
        
        # FVG (Boşluk) Tespiti
        fvg_text = "Belirgin Gap Yok"
        fvg_found = False
        gap_low = None
        gap_high = None
        
        for i in range(len(df)-1, len(df)-10, -1):
            if i < 2:
                break
            # Boşluk yukarı
            if low.iloc[i] > high.iloc[i-2]:
                gap_low = float(high.iloc[i-2])
                gap_high = float(low.iloc[i])
                if abs(curr_price - gap_high) / curr_price < 0.05:
                    fvg_text = f"🔲 {gap_low:.2f}$ - {gap_high:.2f}$"
                    fvg_found = True
                    break
            # Boşluk aşağı
            elif high.iloc[i] < low.iloc[i-2]:
                gap_low = float(high.iloc[i])
                gap_high = float(low.iloc[i-2])
                if abs(curr_price - gap_low) / curr_price < 0.05:
                    fvg_text = f"🔲 {gap_low:.2f}$ - {gap_high:.2f}$"
                    fvg_found = True
                    break
        
        # Basit OB (Kurumsal Ana Destek)
        recent_low = float(low.tail(20).min())
        ob_text = f"🛡️ {recent_low:.2f}$"
        
        # Likidite Hedefi (üst/alt)
        recent_high = float(high.tail(20).max())
        liq_text = f"🎯 {recent_high:.2f}$" if curr_price > mid_point else f"🔻 {recent_low:.2f}$"
        
        # Breaker Block (BB) Tespiti
        bb_text = "-"
        breaker_block = False
        bb_low = None
        bb_high = None
        
        if len(df) >= 60:
            last_60 = df.tail(60)
            # İlk 40 bar: potansiyel eski direnç, son 20 bar: kırılım bölgesi
            prior_segment = last_60.iloc[:-20]
            recent_segment = last_60.iloc[-20:]
            if not prior_segment.empty and not recent_segment.empty:
                prev_res = float(prior_segment['High'].max())
                # Kırılım: son 20 bar içinde kapanışların bir kısmı bu seviyenin üstüne taşmışsa
                if (recent_segment['Close'] > prev_res * 1.003).any():
                    breaker_block = True
                    # Bölgeyi dar bir bant olarak tanımla
                    bb_low = prev_res * 0.995
                    bb_high = prev_res * 1.005
                    bb_text = f"{bb_low:.2f}$ - {bb_high:.2f}$ (Bullish BB)"
        
        # EQH / EQL (Eşit Tepeler / Dipler)
        eqh_level = None
        eql_level = None
        
        if len(df) >= 20:
            last60 = df.tail(60)
            # High/Low değerlerini 2 ondalığa yuvarlayıp tekrarlara bak
            high_round = last60['High'].round(2)
            low_round = last60['Low'].round(2)
            
            high_counts = high_round.value_counts()
            low_counts = low_round.value_counts()
            
            if not high_counts.empty and high_counts.iloc[0] >= 2:
                eqh_level = float(high_counts.index[0])
            if not low_counts.empty and low_counts.iloc[0] >= 2:
                eql_level = float(low_counts.index[0])
        
        # Golden Setup (FVG + OTE Çakışması)
        golden_setup = False
        golden_text = "-"
        if fvg_found and gap_low is not None and gap_high is not None and range_high > range_low:
            gap_mid = (gap_low + gap_high) / 2.0
            if gap_mid > 0:
                # OTE seviyesi ile FVG orta noktasının birbirine yakınlığı (%2 tolerans)
                if abs(ote_level - gap_mid) / gap_mid < 0.02:
                    golden_setup = True
                    golden_text = f"🔥 GOLDEN SETUP: OTE {ote_level:.2f}$ ile FVG ({gap_low:.2f}$ - {gap_high:.2f}$) aynı bölgede."
        
        # SIGNAL ENGINE: Hangi ICT parametreleri güçlü çalışıyor?
        signals = []
        
        # Yapı
        if market_structure.startswith("🟢"):
            signals.append({"name": "Boğa Yapı", "score": 2, "detail": market_structure})
        elif market_structure.startswith("🔴"):
            signals.append({"name": "Ayı Yapı", "score": 2, "detail": market_structure})
        
        # Discount / Premium derinliği
        if is_discount and discount_pct is not None:
            if discount_pct >= 50:
                signals.append({"name": "Derin Discount Bölgesi", "score": 3, "detail": position_text})
            elif discount_pct >= 30:
                signals.append({"name": "Discount Bölgesi", "score": 2, "detail": position_text})
            else:
                signals.append({"name": "Hafif Discount", "score": 1, "detail": position_text})
        elif not is_discount and premium_pct is not None:
            if premium_pct >= 80:
                signals.append({"name": "Aşırı Premium Bölgesi", "score": 3, "detail": position_text})
            elif premium_pct >= 60:
                signals.append({"name": "Premium Bölgesi", "score": 2, "detail": position_text})
            else:
                signals.append({"name": "Hafif Premium", "score": 1, "detail": position_text})
        
        # FVG aktifliği
        if fvg_found:
            signals.append({"name": "FVG Bölgesi Aktif", "score": 2, "detail": fvg_text})
        
        # Breaker Block
        if breaker_block:
            signals.append({"name": "Breaker Block (BB)", "score": 3, "detail": bb_text})
        
        # EQH / EQL
        if eqh_level is not None:
            signals.append({"name": "EQH Likidite Tepesi", "score": 2, "detail": f"EQH ~ {eqh_level:.2f}$"})
        if eql_level is not None:
            signals.append({"name": "EQL Likidite Dibi", "score": 2, "detail": f"EQL ~ {eql_level:.2f}$"})
        
        # Golden Setup
        if golden_setup:
            signals.append({"name": "Golden Setup (FVG+OTE)", "score": 4, "detail": golden_text})
        
        signals_sorted = sorted(signals, key=lambda x: x["score"], reverse=True)
        top_signal_names = [s["name"] for s in signals_sorted[:3]] if signals_sorted else []
        
        # ÖZET: En güçlü parametrelere göre
        if golden_setup and is_bullish and is_discount:
            summary = "💥 GOLDEN SETUP ÇALIŞIYOR: Boğa yapı + Discount bölgede FVG & OTE çakışması. Agresif alım için kuvvetli bölge."
        elif golden_setup and (not is_bullish) and (not is_discount):
            summary = "⚠️ Short Golden Bölge: Ayı yapı + Premium bölgede FVG & OTE çakışması. Kısa pozisyon için fırsat bölgesi."
        elif signals_sorted:
            summary = "💡 ÖZET: Şu anda en güçlü çalışan ICT parametreleri: " + ", ".join(top_signal_names) + "."
        else:
            summary = "Piyasa kararsız; belirgin ICT set-up yok, net bir kırılım/reaksiyon bekle."
        
        return {
            "summary": summary,
            "structure": market_structure,
            "position": position_text,
            "fvg": fvg_text,
            "ob": ob_text,
            "liquidity": liq_text,
            "fibo": fibo_text,
            "bb": bb_text,
            "eqh": eqh_level,
            "eql": eql_level,
            "golden_setup": golden_setup,
            "golden_text": golden_text,
            "signals": signals_sorted,
            "top_signals": top_signal_names
        }
    except Exception:
        return None

def render_ict_panel(analysis):
    if not analysis:
        st.info("ICT verisi hesaplanamadı.")
        return

    # EQH/EQL metinleri
    eqh = analysis.get("eqh")
    eql = analysis.get("eql")
    eqh_txt = f"{eqh:.2f}$" if isinstance(eqh, (int, float, np.floating)) else "-"
    eql_txt = f"{eql:.2f}$" if isinstance(eql, (int, float, np.floating)) else "-"
    
    golden_text = analysis.get("golden_text", "-")
    bb_text = analysis.get("bb", "-")
    
    # Aktif parametrelerin kısa listesi
    sigs = analysis.get("signals", [])
    active_names = ", ".join([s["name"] for s in sigs[:3]]) if sigs else "-"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-header">🧠 ICT & Price Action</div>
        <div class="info-row" style="border-bottom: 1px dashed #e5e7eb; padding-bottom:4px; margin-bottom:6px;">
            <div style="font-weight:700; color:#1e40af; font-size:0.8rem;">{analysis['summary']}</div>
        </div>
        <div class="info-row"><div class="label-long">Genel Yön:</div><div class="info-val">{analysis['structure']}</div></div>
        <div class="info-row"><div class="label-long">Fiyat Konumu:</div><div class="info-val">{analysis['position']}</div></div>
        <div class="info-row"><div class="label-long">Kurumsal Ana Destek (OB):</div><div class="info-val">{analysis['ob']}</div></div>
        <div class="info-row"><div class="label-long">Breaker Block (BB):</div><div class="info-val">{bb_text}</div></div>
        <div class="info-row"><div class="label-long">Olası Alım Yeri (FVG):</div><div class="info-val">{analysis['fvg']}</div></div>
        <div class="info-row"><div class="label-long">EQH / EQL:</div><div class="info-val">EQH: {eqh_txt} | EQL: {eql_txt}</div></div>
        <div class="info-row"><div class="label-long">Ana Hedef (Likidite):</div><div class="info-val">{analysis['liquidity']}</div></div>
        <div class="info-row"><div class="label-long">ICT Fibonacci / OTE:</div><div class="info-val">{analysis['fibo']}</div></div>
        <div class="info-row"><div class="label-long">Golden Setup:</div><div class="info-val">{golden_text}</div></div>
        <div class="info-row"><div class="label-long">Aktif Parametreler:</div><div class="info-val">{active_names}</div></div>
    </div>
    """, unsafe_allow_html=True)

# --- TEKNİK KART (Cached) ---
@st.cache_data(ttl=600)
def get_tech_card_data(ticker):
    try:
        df = yf.download(ticker, period="2y", progress=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close = df['Close']
        high = df['High']
        low = df['Low']
        
        sma50 = close.rolling(50).mean().iloc[-1]
        sma100 = close.rolling(100).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1]
        ema144 = close.ewm(span=144, adjust=False).mean().iloc[-1]
        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        stop_level = close.iloc[-1] - (2 * atr)
        risk_pct = (2 * atr) / close.iloc[-1] * 100
        
        return {
            "sma50": sma50,
            "sma100": sma100,
            "sma200": sma200,
            "ema144": ema144,
            "stop_level": stop_level,
            "risk_pct": risk_pct
        }
    except:
        return None

def render_detail_card(ticker):
    r1_content = "<span style='color:#94a3b8; font-style:italic;'>Veri yok (Tara'ya bas)</span>"
    if st.session_state.scan_data is not None:
        row = st.session_state.scan_data[st.session_state.scan_data["Sembol"] == ticker]
        if not row.empty:
            r1_content = f"<b>Skor {row.iloc[0]['Skor']}/8</b> • {row.iloc[0]['Nedenler']}"
    
    r2_content = "<span style='color:#94a3b8; font-style:italic;'>Veri yok (Radar 2 Tara'ya bas)</span>"
    if st.session_state.radar2_data is not None:
        row = st.session_state.radar2_data[st.session_state.radar2_data["Sembol"] == ticker]
        if not row.empty:
            r2_content = f"<b>Skor {row.iloc[0]['Skor']}/8</b> | {row.iloc[0]['Trend']} | {row.iloc[0]['Setup']} | RS: %{row.iloc[0]['RS']}"
    
    data = get_tech_card_data(ticker)
    if data:
        st.session_state.tech_card_data = data  # AI prompt için sakla
        ma_content = (
            f"SMA50: <b>{data['sma50']:.2f}</b> | "
            f"SMA100: <b>{data['sma100']:.2f}</b> | "
            f"SMA200: <b>{data['sma200']:.2f}</b> | "
            f"EMA144: <b>{data['ema144']:.2f}</b>"
        )
        atr_content = (
            f"ATR Stop (2x): <b style='color:#DC2626'>{data['stop_level']:.2f}</b> "
            f"(Risk: -{data['risk_pct']:.1f}%)"
        )
    else:
        st.session_state.tech_card_data = None
        ma_content = "Veri alınamadı."
        atr_content = "-"
    
    # Teknik Kart (80px Label)
    st.markdown(f"""
    <div class="info-card">
        <div class="info-header">📋 Teknik Kart</div>
        <div class="info-row"><div class="label-short">Radar 1:</div><div class="info-val">{r1_content}</div></div>
        <div class="info-row"><div class="label-short">Radar 2:</div><div class="info-val">{r2_content}</div></div>
        <div class="info-row"><div class="label-short">Ortalama:</div><div class="info-val">{ma_content}</div></div>
        <div class="info-row"><div class="label-short">🛡️ Stop:</div><div class="info-val">{atr_content}</div></div>
    </div>
    """, unsafe_allow_html=True)

def render_tradingview_widget(ticker, height=650):
    tv_symbol = ticker
    if ".IS" in ticker:
        tv_symbol = f"BIST:{ticker.replace('.IS', '')}"
    elif "=X" in ticker:
        tv_symbol = f"FX_IDC:{ticker.replace('=X', '')}"
    html = f"""
    <div class="tradingview-widget-container">
        <div id="tradingview_chart"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
        new TradingView.widget({{
            "width": "100%",
            "height": {height},
            "symbol": "{tv_symbol}",
            "interval": "D",
            "timezone": "Etc/UTC",
            "theme": "light",
            "style": "1",
            "locale": "tr",
            "toolbar_bg": "#f1f3f6",
            "enable_publishing": false,
            "allow_symbol_change": true,
            "container_id": "tradingview_chart"
        }});
        </script>
    </div>
    """
    components.html(html, height=height)

@st.cache_data(ttl=300)
def fetch_stock_info(ticker):
    try:
        info = yf.Ticker(ticker).info
        price = info.get('currentPrice') or info.get('regularMarketPrice')
        prev_close = info.get('previousClose')
        change_pct = 0
        if price and prev_close:
            change_pct = (price - prev_close) / prev_close * 100
        return {
            'price': price,
            'change_pct': change_pct,
            'volume': info.get('volume', 0),
            'sector': info.get('sector', '-'),
            'target': info.get('targetMeanPrice', '-')
        }
    except:
        return None

@st.cache_data(ttl=1200)  # 20 Dakikalık Cache
def fetch_google_news(ticker):
    try:
        clean = ticker.replace(".IS", "").replace("=F", "")
        rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote_plus(f'{clean} stock news site:investing.com OR site:seekingalpha.com')}&hl=tr&gl=TR&ceid=TR:tr"
        feed = feedparser.parse(rss_url)
        news = []
        for entry in feed.entries[:6]:
            try:
                dt = datetime(*entry.published_parsed[:6])
            except:
                dt = datetime.now()
            if dt < datetime.now() - timedelta(days=10):
                continue
            pol = TextBlob(entry.title).sentiment.polarity
            color = "#16A34A" if pol > 0.1 else "#DC2626" if pol < -0.1 else "#64748B"
            news.append({
                'title': entry.title,
                'link': entry.link,
                'date': dt.strftime('%d %b'),
                'source': entry.source.title,
                'color': color
            })
        return news
    except:
        return []

# --- ARAYÜZ KURULUMU ---

BULL_ICON_B64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAOAAAADhCAMAAADmr0l2AAAAb1BMVEX///8AAAD8/PzNzc3y8vL39/f09PTw8PDs7Ozp6eny8vLz8/Pr6+vm5ubt7e3j4+Ph4eHf39/c3NzV1dXS0tLKyso/Pz9ERERNTU1iYmJSUlJxcXF9fX1lZWV6enp2dnZsbGxra2uDg4N0dHR/g07fAAAE70lEQVR4nO2d27qrIAyF131wRPT+z3p2tX28dE5sC4i9x3+tC0L4SAgJ3Y2Hw+FwOBwOh8PhcDgcDofD4XA4HA6Hw+FwOBwOh8PhcDj/I+7H8zz/i2E3/uI4/o1xM0L4F8d2hPA/jqsRwj84niOEf26cRgj/2HiOENZ3H/8B4/z57mP4AONqhPDnjf8E4zZC+LPGeYTwJ43rEcKfMx4jhD9lrEcIf8h4jRD+jHEaIby78RkhvLPxGiG8q3E9Qng34zNCeCfjM0J4J+MzQngn4zNCeFfjM0J4B+M1QngH4zNCeAfjOkJ4B+M2Qvhzxv+C8f+CcR0h/BnjOkJ4B+M6QngH4zZCeAdjd/9wB+MyQngH4zJCeAfjMkJ4B2N7/+B+4zpCeAfjMkJ4B+M6QngH4zJCeAfjMkJ4B+M6QngH4zpCeAfjMkJ4B+M6QngH4zpCeAfjMkJ4B+M6QngH4zJCeAdje//gfuM6QngH4zpCeAdjd//gfuMyQngH4zJCeAdjd//gfmM3QngHY3f/4H7jNkJ4B+M2QngHY3v/4H7jNkJ4B+Mdjd//gfmM3QngHY3v/4H7jNkJ4B+M7/+B+4zZCeAdjd//gfmM3QngHYzf/4H7jNkJ4B+M2QngHY3f/4H7jMkJ4B+MyQngHY3v/4H7jNkJ4B+M6QngH4zpCeAdje//gfuMyQngH4zpCeAfjOkJ4B+M6QngH4zpCeAfjMkJ4B+M6QngH4zJCeAfjOkJ4B2M3/3A/4zZCeAdje//gfuM2QngHY3f/4H7jMkJ4B+MyQngHY3v/4H7jOkJ4B+M6QngH4zpCeAfjMkJ4B+MyQngHY3f/4H7jMkJ4B+M6QngH4zpCeAdj9/+v70YI72Cs7h8ur3rVq171qle96lWvev079K8Ym/sH9xu7EcI7GLv/f303QngHY3X/cHn1m038tX/tTxhX3yO8f2w+M1b3D5c3tH4rxtaE8A7G1oTwDsbW/gE+8q8Z2xPCOxjbE8I7GNsTwjsY2xPCOxgbE8I7GNsTwjsY2/8H8O4/ZmztH9w/GNsTwjsY2xPCOxhb+wf3D8a2hPAOxrY/wHf+LWPbfxDf2R1/zdiaEN7B2JoQ3sHYmhDewdiaEN7B2JoQ3sHYmhDewdiaEN7B2JoQ3sHYmhDewdiaEN7B2JoQ3sHY/gf4zv/L2PZ/A+/8n9H/K8a2P8B3/i1jW0J4B2NrQngHY2tCeAdia0J4B2NrQngHY2tCeAdja0J4B2NbQngHY2tCeAdja0J4B2NbQngHY2tCeAdja0J4B2NbQngHY2tCeAdja0J4B2NbQngHY2tCeAdja0J4B2NbQngHY2tCeAdja0J4B2NrQngHY3tCeAdia0J4B2NrQngHY2tCeAdja0J4B2NrQngHY2tCeAdja0J4B2NrQngHY2tCeAdja0J4B2NbQngHY2tCeAdja0J4B2NrQngHY2tCeAdja0J4B2NrQngHY2tCeAdja0J4B2N7QngHYmtCeAdja0J4B2NrQngHY2tCeAdja0J4B2NrQngHY2tCeAdja0J4B2NbQngHY2tCeAdja0J4B2NbQngHY2tCeAdja0J4B2NrQngHY/v/B/Duf4ixNSG8g7E1IbyDsTUhvIOxNSG8g7E1IbyDsTUhvIOxNSG8g7E1IbyDsTUhvIOx/X8A7/6HGNsTwjsY2xPCOxjbE8I7GNv/B/Dup/9ijE0I72BsTgjvYMxHCA+Hw+FwOBwOh8PhcDgcDofD4XA4HA6Hw+H8B/wDUQp/j9/j9jMAAAAASUVORK5CYII="

st.markdown(f"""
<div class="header-container" style="display:flex; align-items:center;">
    <img src="{BULL_ICON_B64}" class="header-logo">
    <div>
        <div style="font-size:1.5rem; font-weight:700; color:#1e3a8a;">Patronun Terminali v4.1.0</div>
        <div style="font-size:0.8rem; color:#64748B;">Market Maker Edition (Standardized)</div>
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

# İÇERİK
info = fetch_stock_info(st.session_state.ticker)
col_left, col_right = st.columns([3, 1])

with col_left:
    # 1. İSTATİSTİK KUTULARI
    if info and info['price']:
        sc1, sc2, sc3, sc4 = st.columns(4)
        cls = "delta-pos" if info['change_pct'] >= 0 else "delta-neg"
        sc1.markdown(
            f'<div class="stat-box-small"><p class="stat-label-small">FİYAT</p>'
            f'<p class="stat-value-small money-text">{info["price"]:.2f}'
            f'<span class="stat-delta-small {cls}">{"+" if info["change_pct"]>=0 else ""}{info["change_pct"]:.2f}%</span>'
            f'</p></div>',
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
    # 2. TRADINGVIEW GRAFİĞİ (650PX SABİT)
    render_tradingview_widget(st.session_state.ticker, height=650)
    
    # 3. TEKNİK KART (STANDART)
    render_detail_card(st.session_state.ticker)
    
    # 4. YENİ: ICT & PRICE ACTION PUSULASI (GELİŞMİŞ)
    ict_analysis = calculate_ict_concepts(st.session_state.ticker)
    st.session_state.ict_analysis = ict_analysis
    render_ict_panel(ict_analysis)

    # 5. HABERLER (En altta)
    st.markdown(
        "<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:20px;'>📡 Haber Akışı</div>",
        unsafe_allow_html=True
    )
    news = fetch_google_news(st.session_state.ticker)
    if news:
        cols = st.columns(2)
        for i, n in enumerate(news):
            with cols[i % 2]:
                st.markdown(
                    f"""<div class="news-card" style="border-left-color: {n['color']};">
                        <a href="{n['link']}" target="_blank" class="news-title">{n['title']}</a>
                        <div class="news-meta">{n['date']} • {n['source']}</div>
                    </div>""",
                    unsafe_allow_html=True
                )
    else:
        st.info("Haber yok.")

with col_right:
    # 1. ORTAK SİNYALLER
    st.markdown(
        f"<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px;color:#1e3a8a; "
        f"background-color:{current_theme['box_bg']}; padding:5px; border-radius:5px; "
        f"border:1px solid #1e40af;'>🎯 Ortak Fırsatlar</div>",
        unsafe_allow_html=True
    )
    
    # BURASI SCROLL'LU KISIM (yükseklik sabit, içinde scroll var)
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
                    combined = float(row1["Skor"]) + float(row2["Skor"])
                    commons.append({"symbol": sym, "r1": row1, "r2": row2, "combined": combined})
                
                commons_sorted = sorted(commons, key=lambda x: x["combined"], reverse=True)
                
                for item in commons_sorted:
                    sym = item["symbol"]
                    row1 = item["r1"]; row2 = item["r2"]
                    c1, c2 = st.columns([0.2, 0.8])
                    if c1.button("★", key=f"c_s_{sym}"):
                        toggle_watchlist(sym)
                        st.rerun()
                    label = f"{sym} | R1: {row1['Skor']}/8 | R2: {row2['Skor']}/8 | {row2['Setup']}"
                    if c2.button(label, key=f"c_b_{sym}"):
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
            with st.spinner("Taranıyor... (Önbellekli)"):
                st.session_state.scan_data = analyze_market_intelligence(
                    ASSET_GROUPS.get(st.session_state.category, [])
                )
        
        if st.session_state.scan_data is not None and not st.session_state.scan_data.empty:
            for i, row in st.session_state.scan_data.iterrows():
                sym = row["Sembol"]; score = row['Skor']
                c1, c2 = st.columns([0.2, 0.8])
                if c1.button("★" if sym in st.session_state.watchlist else "☆",
                            key=f"r1_s_{sym}_{i}"):
                    toggle_watchlist(sym)
                    st.rerun()
                if c2.button(f"{'🔥' if score>=7 else '✅'} {score}/8 | {sym}",
                            key=f"r1_b_{sym}_{i}"):
                    on_scan_result_click(sym)
                    st.rerun()
                st.markdown(
                    f"<div style='font-size:0.6rem; color:#64748B; "
                    f"margin-top:-8px; padding-left:5px;'>{row['Nedenler']}</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("Sinyal yok.")

    with tab2:
        if st.button(f"🚀 RADAR 2 Tara", type="primary"):
            with st.spinner("Taranıyor... (Önbellekli)"):
                st.session_state.radar2_data = radar2_scan(
                    ASSET_GROUPS.get(st.session_state.category, [])
                )
        
        if st.session_state.radar2_data is not None and not st.session_state.radar2_data.empty:
            for i, row in st.session_state.radar2_data.iterrows():
                sym = row["Sembol"]
                c1, c2 = st.columns([0.2, 0.8])
                if c1.button("★" if sym in st.session_state.watchlist else "☆",
                            key=f"r2_s_{sym}_{i}"):
                    toggle_watchlist(sym)
                    st.rerun()
                
                # FORMAT: Skor en başta
                btn_label = f"🚀 {row['Skor']}/8 | {sym} | {row['Trend']} | {row['Setup']}"
                if c2.button(btn_label, key=f"r2_b_{sym}_{i}"):
                    on_scan_result_click(sym)
                    st.rerun()
                st.markdown(
                    f"<div style='font-size:0.6rem; color:#64748B; margin-top:-8px; "
                    f"padding-left:5px;'>Fiyat: {row['Fiyat']} • RS: {row['RS']}% • "
                    f"{row['Etiketler']}</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("Sinyal yok.")

    with tab3:
        wl = st.session_state.watchlist
        if not wl:
            st.info("Liste boş.")
        else:
            if st.button("⚡ Listeyi Tara (R1)", type="secondary"):
                with st.spinner("..."):
                    st.session_state.scan_data = analyze_market_intelligence(wl)
            for sym in wl:
                c1, c2 = st.columns([0.2, 0.8])
                if c1.button("❌", key=f"wl_d_{sym}"):
                    toggle_watchlist(sym)
                    st.rerun()
                if c2.button(sym, key=f"wl_g_{sym}"):
                    on_scan_result_click(sym)
                    st.rerun()

