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
    page_title="Patronun Terminali v4.1.1",
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

# DÜZELTME: CSS içindeki tüm süslü parantezler {{ }} olarak çiftlendi. Hata vermez.
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&display=swap');
    
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {current_theme['text']}; }}
    .stApp {{ background-color: {current_theme['bg']}; }}
    
    /* Layout */
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
    
    /* ORTAK KART STİLİ */
    .info-card {{
        background: {current_theme['box_bg']}; border: 1px solid {current_theme['border']};
        border-radius: 6px; padding: 8px; margin-top: 5px; margin-bottom: 10px;
        font-size: 0.8rem; font-family: 'Inter', sans-serif;
    }}
    .info-header {{ font-weight: 700; color: #1e3a8a; border-bottom: 1px solid {current_theme['border']}; padding-bottom: 4px; margin-bottom: 4px; }}
    .info-row {{ display: flex; align-items: center; margin-bottom: 3px; }}
    
    /* Etiket Genişlikleri */
    .label-short {{ font-weight: 600; color: #64748B; width: 80px; flex-shrink: 0; }}
    .label-long {{ font-weight: 600; color: #64748B; width: 165px; flex-shrink: 0; }}
    
    .info-val {{ color: {current_theme['text']}; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; }}
    
    /* LOGO STİLİ (DÜZELTİLDİ: Çift Parantez) */
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
            
            ema5 = close.ewm(span=5, adjust=False).mean()
            ema20 = close.ewm(span=20, adjust=False).mean()
            sma20 = close.rolling(20).mean(); std20 = close.rolling(20).std()
            bb_width = ((sma20 + 2*std20) - (sma20 - 2*std20)) / (sma20 + 0.0001)
            hist = (close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()) - (close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()).ewm(span=9, adjust=False).mean()
            delta = close.diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
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
            avg_vol_20 = max(avg_vol_20, 1)
            vol_spike = volume.iloc[-1] > avg_vol_20 * 1.3

            if trend == "Boğa" and breakout_ratio >= 0.97:
                setup = "Breakout"; score += 2; tags.append("Zirve")
                if vol_spike: score += 1; tags.append("Hacim+")
            if trend == "Boğa" and setup == "-":
                if sma20.iloc[-1] <= curr_c <= sma50.iloc[-1] * 1.02 and 40 <= rsi_c <= 55:
                    setup = "Pullback"; score += 2; tags.append("Düzeltme")
                    if volume.iloc[-1] < avg_vol_20 * 0.9: score += 1; tags.append("Sığ Satış")
            if setup == "-":
                if rsi.iloc[-2] < 30 <= rsi_c and hist.iloc[-1] > hist.iloc[-2]:
                    setup = "Dip Dönüşü"; score += 2; tags.append("Dip Dönüşü")

            if rs_score > 0: score += 1; tags.append("RS+")
            if trend == "Boğa": score += 1
            elif trend == "Ayı": score -= 1

            if score > 0:
                results.append({"Sembol": symbol, "Fiyat": round(curr_c, 2), "Trend": trend, "Setup": setup, "Skor": score, "RS": round(rs_score * 100, 1), "Etiketler": " | ".join(tags)})
        except: continue
    return pd.DataFrame(results).sort_values(by=["Skor", "RS"], ascending=False).head(50) if results else pd.DataFrame()

# --- ICT & PRICE ACTION HESAPLAMA ---
@st.cache_data(ttl=600)
def calculate_ict_concepts(ticker):
    try:
        df = yf.download(ticker, period="3mo", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        close = df['Close']; high = df['High']; low = df['Low']
        curr_price = close.iloc[-1]
        
        recent_high = high.tail(20).max()
        recent_low = low.tail(20).min()
        
        # 1. Market Structure
        is_bullish = False
        market_structure = "Nötr / Yatay"
        if close.iloc[-1] > high.tail(20).iloc[-5:].max():
            market_structure = "🟢 YÜKSELİŞ (Trend Güçlü)"
            is_bullish = True
        elif close.iloc[-1] < low.tail(20).iloc[-5:].min():
            market_structure = "🔴 DÜŞÜŞ (Yapı Bozuldu)"
            is_bullish = False
            
        # 2. Premium / Discount & Fibonacci
        range_high = high.tail(60).max()
        range_low = low.tail(60).min()
        mid_point = (range_high + range_low) / 2
        ote_bull = range_low + (range_high - range_low) * 0.382
        ote_bear = range_low + (range_high - range_low) * 0.618
        
        is_discount = False
        if curr_price < mid_point:
            discount_pct = 100 - ((curr_price - range_low) / (range_high - range_low) * 100)
            position_text = f"✅ UCUZ BÖLGE (Discount: %{discount_pct:.1f})"
            is_discount = True
        else:
            premium_pct = ((curr_price - range_low) / (range_high - range_low) * 100)
            position_text = f"⚠️ PAHALI BÖLGE (Premium: %{premium_pct:.1f})"
            is_discount = False
            
        # Özet Cümlesi
        summary = "Piyasa kararsız; işlem için belirgin bir kırılım bekle."
        if is_bullish and is_discount: summary = "💡 ÖZET: Rüzgar arkada (Boğa); fiyat alım için uygun ucuzlukta."
        elif not is_bullish and not is_discount: summary = "💡 ÖZET: Trend düşüşte; fiyat satış için pahalı bölgede."
        elif is_bullish and not is_discount: summary = "💡 ÖZET: Trend yukarı ama fiyat pahalı (Premium); düzeltme beklenebilir."
        elif not is_bullish and is_discount: summary = "💡 ÖZET: Fiyat ucuz ama trend düşüşte; dip dönüşü sinyali ara."

        fibo_text = f"📐 Fibo %50: {mid_point:.2f}$ | OTE (%62): {ote_bull if is_bullish else ote_bear:.2f}$"

        # 3. FVG & Golden Setup
        fvg_text = "Belirgin Gap Yok"
        golden_setup = False
        for i in range(len(df)-1, len(df)-10, -1):
            if i < 2: break
            if low.iloc[i] > high.iloc[i-2]: # Bullish FVG
                gap_low = high.iloc[i-2]; gap_high = low.iloc[i]
                if abs(curr_price - gap_high) / curr_price < 0.05:
                   fvg_text = f"🔲 {gap_low:.2f}$ - {gap_high:.2f}$"
                   if gap_low <= ote_bull <= gap_high and is_bullish: golden_setup = True
                   break
            elif high.iloc[i] < low.iloc[i-2]: # Bearish FVG
                gap_low = high.iloc[i]; gap_high = low.iloc[i-2]
                if abs(curr_price - gap_low) / curr_price < 0.05:
                   fvg_text = f"🔲 {gap_low:.2f}$ - {gap_high:.2f}$"
                   if gap_low <= ote_bear <= gap_high and not is_bullish: golden_setup = True
                   break
        
        if golden_setup: fvg_text += " 🔥 GOLDEN SETUP (FVG+OTE)"

        # 4. Breaker Block & Order Block
        ob_label = "Bullish Order Block (OB)"
        ob_level = recent_low
        if is_bullish and curr_price > range_high * 0.95:
             ob_label = "🛡️ Bullish Breaker Block (BB)"
             ob_level = high.tail(40).iloc[:-10].max() # Eski tepe
        
        ob_text = f"🛡️ {ob_level:.2f}$"

        # 5. Equal Highs/Lows
        highs = high.tail(60); max_h = highs.max()
        second_h = highs[highs < max_h].max()
        liq_label = "Liquidity Pool"; liq_val = recent_high if is_bullish else recent_low
        
        if is_bullish and second_h and abs(max_h - second_h) / max_h < 0.003:
            liq_label = "🎯 Eşit Tepeler (EQH)"; liq_val = max_h
        elif not is_bullish:
            lows = low.tail(60); min_l = lows.min()
            second_l = lows[lows > min_l].min()
            if second_l and abs(second_l - min_l) / min_l < 0.003:
                liq_label = "🎯 Eşit Dipler (EQL)"; liq_val = min_l

        liq_text = f"{liq_val:.2f}$"

        return {
            "summary": summary, "structure": market_structure, "position": position_text,
            "fvg": fvg_text, "ob": ob_text, "ob_label": ob_label,
            "liquidity": liq_text, "liq_label": liq_label, "fibo": fibo_text,
            "raw_ob": ob_level, "raw_ote": ote_bull if is_bullish else ote_bear, "range_fvg": fvg_text
        }
    except: return None

def render_ict_panel(analysis):
    if not analysis: st.info("ICT verisi hesaplanamadı."); return
    st.markdown(f"""
    <div class="info-card">
        <div class="info-header">🧠 ICT & Price Action</div>
        <div class="info-row" style="border-bottom: 1px dashed #e5e7eb; padding-bottom:4px; margin-bottom:6px;">
            <div style="font-weight:700; color:#1e40af; font-size:0.8rem;">{analysis['summary']}</div>
        </div>
        <div class="info-row"><div class="label-long">Genel Yön:</div><div class="info-val">{analysis['structure']}</div></div>
        <div class="info-row"><div class="label-long">Fiyat Konumu:</div><div class="info-val">{analysis['position']}</div></div>
        <div class="info-row"><div class="label-long">Kurumsal Ana Destek Bölgesi:</div><div class="info-val">{analysis['ob']} ({analysis['ob_label']})</div></div>
        <div class="info-row"><div class="label-long">Olası Alım Yeri:</div><div class="info-val">{analysis['fvg']} (FVG)</div></div>
        <div class="info-row"><div class="label-long">Ana Hedef:</div><div class="info-val">{analysis['liquidity']} ({analysis['liq_label']})</div></div>
        <div class="info-row"><div class="label-long">ICT Fibonacci:</div><div class="info-val">{analysis['fibo']}</div></div>
    </div>
    """, unsafe_allow_html=True)

# --- TEKNİK KART (Cached) ---
@st.cache_data(ttl=600)
def get_tech_card_data(ticker):
    try:
        df = yf.download(ticker, period="2y", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']; high = df['High']; low = df['Low']
        
        sma50 = close.rolling(50).mean().iloc[-1]; sma100 = close.rolling(100).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1]; ema144 = close.ewm(span=144, adjust=False).mean().iloc[-1]
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        return {"sma50": sma50, "sma100": sma100, "sma200": sma200, "ema144": ema144, "stop": close.iloc[-1]-2*atr, "atr": atr, "risk": (2*atr)/close.iloc[-1]*100}
    except: return None

def render_detail_card(ticker):
    r1_t = "Veri yok"; r2_t = "Veri yok"
    if st.session_state.scan_data is not None:
        row = st.session_state.scan_data[st.session_state.scan_data["Sembol"] == ticker]
        if not row.empty: r1_t = f"<b>Skor {row.iloc[0]['Skor']}/8</b> • {row.iloc[0]['Nedenler']}"
    if st.session_state.radar2_data is not None:
        row = st.session_state.radar2_data[st.session_state.radar2_data["Sembol"] == ticker]
        if not row.empty: r2_t = f"<b>Skor {row.iloc[0]['Skor']}/8</b> | {row.iloc[0]['Trend']} | {row.iloc[0]['Setup']} | RS: %{row.iloc[0]['RS']}"
    
    dt = get_tech_card_data(ticker)
    ma_t = "-"; st_t = "-"
    if dt:
        ma_t = f"SMA50: <b>{dt['sma50']:.2f}</b> | SMA100: <b>{dt['sma100']:.2f}</b> | SMA200: <b>{dt['sma200']:.2f}</b> | EMA144: <b>{dt['ema144']:.2f}</b>"
        st_t = f"ATR Stop (2x): <b style='color:#DC2626'>{dt['stop']:.2f}</b> (Risk: -{dt['risk']:.1f}%)"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-header">📋 Teknik Kart</div>
        <div class="info-row"><div class="label-short">Radar 1:</div><div class="info-val">{r1_t}</div></div>
        <div class="info-row"><div class="label-short">Radar 2:</div><div class="info-val">{r2_t}</div></div>
        <div class="info-row"><div class="label-short">Ortalama:</div><div class="info-val">{ma_t}</div></div>
        <div class="info-row"><div class="label-short">🛡️ Stop:</div><div class="info-val">{st_t}</div></div>
    </div>
    """, unsafe_allow_html=True)

# --- SIDEBAR (YENİLENMİŞ AI PROMPT) ---
with st.sidebar:
    st.markdown("### ⚙️ Ayarlar")
    selected_theme_name = st.selectbox("", ["Beyaz", "Kirli Beyaz", "Buz Mavisi"], index=["Beyaz", "Kirli Beyaz", "Buz Mavisi"].index(st.session_state.theme), label_visibility="collapsed")
    if selected_theme_name != st.session_state.theme: st.session_state.theme = selected_theme_name; st.rerun()
    st.divider()
    
    with st.expander("🤖 AI Analist (Prompt)", expanded=True):
        if st.button("📋 Analiz Metnini Hazırla", type="primary"):
            t = st.session_state.ticker
            inf = fetch_stock_info(t); ict = calculate_ict_concepts(t); tech = get_tech_card_data(t)
            price = inf['price'] if inf else "Bilinmiyor"
            
            r1_s = "Yok"; r1_n = "-"; r2_tr = "-"; r2_st = "-"; r2_rs = "0"
            if st.session_state.scan_data is not None:
                r = st.session_state.scan_data[st.session_state.scan_data["Sembol"]==t]
                if not r.empty: r1_s = r.iloc[0]['Skor']; r1_n = r.iloc[0]['Nedenler']
            if st.session_state.radar2_data is not None:
                r = st.session_state.radar2_data[st.session_state.radar2_data["Sembol"]==t]
                if not r.empty: r2_tr = r.iloc[0]['Trend']; r2_st = r.iloc[0]['Setup']; r2_rs = r.iloc[0]['RS']

            prompt = f"""Rol: Profesyonel borsa traderı.
Görev: {t} grafiğinde Teknik Analiz ve Formasyon Avcılığı.

--- VERİLER ---
Fiyat: {price} USD

Radar 1 (Momentum): Skor {r1_s}/8. Nedenler: {r1_n}
Radar 2 (Trend/Yapı): {r2_tr} Trend | {r2_st} | RS: {r2_rs}%

Ortalamalar: SMA50: {tech['sma50'] if tech else '-'}, SMA200: {tech['sma200'] if tech else '-'}, EMA144: {tech['ema144'] if tech else '-'}
Risk Yönetimi: ATR (14): {tech['atr'] if tech else '-'} (2x Stop: {tech['stop'] if tech else '-'})

ICT Seviyeleri (60 Günlük Range Analizi):
- Piyasada Gözlemlenen Fiyat Konumu: {ict['position'] if ict else '-'}
- Kurumsal Destek Bölgesi ({ict['ob_label'] if ict else 'OB'}): {ict['ob'] if ict else '-'}
- Olası Alım/Satım Bölgesi (FVG): {ict['range_fvg'] if ict else '-'}
- OTE (Optimal Trade Entry) Fibonacci Seviyesi: {ict['raw_ote'] if ict else '-'}

--- EMİRLER ---
1. "Al/Sat/Bekle" tavsiyesi VERMEKTEN ÇEKİNME. (Net duruş sergile).
2. Günlük grafikte Formasyon ara (TOBO, OBO, Bayrak, Flama, Üçgen, Kama, Consolidation, Built-up). Varsa mutlaka belirt.
3. Destek/Direnç ve Trend hakkında çok kısa, vurucu ve teknik 5 cümle kur.
4. Risk/Getiri durumunu değerlendir.
5. Ayrıca Price Action ve ICT konseptlerine (FVG, Order Block) dayalı günlük analiz yap:
   - Yön ne?
   - Alım/Satım bölgesi neresi?
   - Stop seviyesi (ATR) nedir?
   - Son Fibonacci sayımına göre OTE yeri neresi?
6. Türkçe yanıtla."""
            st.code(prompt, language="text")

# --- ANA EKRAN ---
BULL_ICON_B64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAOAAAADhCAMAAADmr0l2AAAAb1BMVEX///8AAAD8/PzNzc3y8vL39/f09PTw8PDs7Ozp6eny8vLz8/Pr6+vm5ubt7e3j4+Ph4eHf39/c3NzV1dXS0tLKyso/Pz9ERERNTU1iYmJSUlJxcXF9fX1lZWV6enp2dnZsbGxra2uDg4N0dHR/g07fAAAE70lEQVR4nO2d27qrIAyF131wRPT+z3p2tX28dE5sC4i9x3+tC0L4SAgJ3Y2Hw+FwOBwOh8PhcDgcDofD4XA4HA6Hw+FwOBwOh8PhcDj/I+7H8zz/i2E3/uI4/o1xM0L4F8d2hPA/jqsRwj84niOEf26cRgj/2HiOENZ3H/8B4/z57mP4AONqhPDnjf8E4zZC+LPGeYTwJ43rEcKfMx4jhD9lrEcIf8h4jRD+jHEaIby78RkhvLPxGiG8q3E9Qng34zNCeCfjM0J4J+MzQngn4zNCeFfjM0J4B+M1QngH4zNCeAfjOkJ4B+M2Qvhzxv+C8f+CcR0h/BnjOkJ4B+M6QngH4zZCeAdjd/9wB+MyQngH4zJCeAfjMkJ4B2N7/+B+4zpCeAfjMkJ4B+M6QngH4zJCeAfjMkJ4B+M6QngH4zpCeAfjMkJ4B+M6QngH4zpCeAfjMkJ4B+M6QngH4zJCeAdje//gfuM6QngH4zpCeAdjd//gfuMyQngH4zJCeAdjd//gfmM3QngHY3f/4H7jNkJ4B+M2QngHY3v/4H7jNkJ4B+Mdjd//gfmM3QngHY3v/4H7jNkJ4B+M7/+B+4zZCeAdjd//gfmM3QngHYzf/4H7jNkJ4B+M2QngHY3f/4H7jMkJ4B+MyQngHY3v/4H7jNkJ4B+M6QngH4zpCeAdje//gfuMyQngH4zpCeAfjOkJ4B+M6QngH4zpCeAfjMkJ4B+M6QngH4zJCeAfjOkJ4B2M3/3A/4zZCeAdje//gfuM2QngHY3f/4H7jMkJ4B+MyQngHY3v/4H7jOkJ4B+M6QngH4zpCeAfjMkJ4B+MyQngHY3f/4H7jMkJ4B+M6QngH4zpCeAdj9/+v70YI72Cs7h8ur3rVq171qle96lWvev079K8Ym/sH9xu7EcI7GLv/f303QngHY3X/cHn1m038tX/tTxhX3yO8f2w+M1b3D5c3tH4rxtaE8A7G1oTwDsbW/gE+8q8Z2xPCOxjbE8I7GNsTwjsY2xPCOxgbE8I7GNsTwjsY2/8H8O4/ZmztH9w/GNsTwjsY2xPCOxhb+wf3D8a2hPAOxrY/wHf+LWPbfxDf2R1/zdiaEN7B2JoQ3sHYmhDewdiaEN7B2JoQ3sHYmhDewdiaEN7B2JoQ3sHYmhDewdiaEN7B2JoQ3sHY/gf4zv/L2PZ/A+/8n9H/K8a2P8B3/i1jW0J4B2NrQngHY2tCeAdia0J4B2NrQngHY2tCeAdja0J4B2NbQngHY2tCeAdja0J4B2NbQngHY2tCeAdja0J4B2NbQngHY2tCeAdja0J4B2NbQngHY2tCeAdja0J4B2NrQngHY3tCeAdia0J4B2NrQngHY2tCeAdja0J4B2NrQngHY2tCeAdja0J4B2NrQngHY1tCeAdja0J4B2NbQngHY2tCeAdja0J4B2NbQngHY2tCeAdja0J4B2NrQngHY2tCeAdja0J4B2NrQngHY2tCeAdja0J4B2NbQngHY2tCeAdja0J4B2NrQngHY2tCeAdja0J4B2NbQngHY2tCeAdja0J4B2NbQngHY2tCeAdja0J4B2NrQngHY/v/B/Duf4ixNSG8g7E1IbyDsTUhvIOxNSG8g7E1IbyDsTUhvIOxNSG8g7E1IbyDsTUhvIOx/X8A7/6HGNsTwjsY2xPCOxjbE8I7GNv/B/Dup/9ijE0I72BsTgjvYMxHCA+Hw+FwOBwOh8PhcDgcDofD4XA4HA6Hw+H8B/wDUQp/j9/j9jMAAAAASUVORK5CYII="
st.markdown(f"""
<div class="header-container" style="display:flex; align-items:center;">
    <img src="{BULL_ICON_B64}" class="header-logo">
    <div>
        <div style="font-size:1.5rem; font-weight:700; color:#1e3a8a;">Patronun Terminali v4.1.1</div>
        <div style="font-size:0.8rem; color:#64748B;">Market Maker Edition (Final Fix)</div>
    </div>
</div>
<hr style="border:0; border-top: 1px solid #e5e7eb; margin-top:5px; margin-bottom:10px;">
""", unsafe_allow_html=True)

# FILTRELER (KESİN ÇÖZÜM)
col_cat, col_ass, col_search_in, col_search_btn = st.columns([1.5, 2, 2, 0.7])

# ÖNCE DEĞİŞKEN HESAPLA
try: cat_idx = list(ASSET_GROUPS.keys()).index(st.session_state.category)
except: cat_idx = 0

with col_cat:
    st.selectbox("Kategori", list(ASSET_GROUPS.keys()), index=cat_idx, key="selected_category_key", on_change=on_category_change, label_visibility="collapsed")

# ÖNCE LİSTE VE INDEX HESAPLA
opts = ASSET_GROUPS.get(st.session_state.category, ASSET_GROUPS[INITIAL_CATEGORY])
try: asset_idx = opts.index(st.session_state.ticker)
except: asset_idx = 0

with col_ass:
    st.selectbox("Varlık", opts, index=asset_idx, key="selected_asset_key", on_change=on_asset_change, label_visibility="collapsed")

with col_search_in:
    st.text_input("Manuel", placeholder="Kod", key="manual_input_key", label_visibility="collapsed")

with col_search_btn:
    st.button("Ara", on_click=on_manual_button_click)

st.markdown("<hr style='margin-top:0.5rem; margin-bottom:0.5rem;'>", unsafe_allow_html=True)

# İÇERİK
info = fetch_stock_info(st.session_state.ticker)
col_left, col_right = st.columns([3, 1])

with col_left:
    if info:
        sc1, sc2, sc3, sc4 = st.columns(4)
        cls = "delta-pos" if info['change_pct'] >= 0 else "delta-neg"
        sc1.markdown(f'<div class="stat-box-small"><p class="stat-label-small">FİYAT</p><p class="stat-value-small money-text">{info["price"]:.2f}<span class="stat-delta-small {cls}">{"+" if info["change_pct"]>=0 else ""}{info["change_pct"]:.2f}%</span></p></div>', unsafe_allow_html=True)
        sc2.markdown(f'<div class="stat-box-small"><p class="stat-label-small">HACİM</p><p class="stat-value-small money-text">{info["volume"]/1e6:.1f}M</p></div>', unsafe_allow_html=True)
        sc3.markdown(f'<div class="stat-box-small"><p class="stat-label-small">HEDEF</p><p class="stat-value-small money-text">{info["target"]}</p></div>', unsafe_allow_html=True)
        sc4.markdown(f'<div class="stat-box-small"><p class="stat-label-small">SEKTÖR</p><p class="stat-value-small">{str(info["sector"])[:12]}</p></div>', unsafe_allow_html=True)
    
    st.write("")
    render_tradingview_widget(st.session_state.ticker, height=650) # 650px Düzeltildi
    render_detail_card(st.session_state.ticker)
    
    ict = calculate_ict_concepts(st.session_state.ticker)
    render_ict_panel(ict)
    
    st.markdown("<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:20px;'>📡 Haber Akışı</div>", unsafe_allow_html=True)
    news = fetch_google_news(st.session_state.ticker)
    if news:
        cols = st.columns(2)
        for i, n in enumerate(news):
            with cols[i%2]: st.markdown(f"""<div class="news-card" style="border-left-color: {n['color']};"><a href="{n['link']}" target="_blank" class="news-title">{n['title']}</a><div class="news-meta">{n['date']} • {n['source']}</div></div>""", unsafe_allow_html=True)

with col_right:
    st.markdown(f"<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px;color:#1e3a8a; background-color:{current_theme['box_bg']}; padding:5px; border-radius:5px; border:1px solid #1e40af;'>🎯 Ortak Fırsatlar</div>", unsafe_allow_html=True)
    with st.container(height=250):
        df1 = st.session_state.scan_data
        df2 = st.session_state.radar2_data
        if df1 is not None and df2 is not None and not df1.empty and not df2.empty:
            commons = []
            symbols = set(df1["Sembol"]).intersection(set(df2["Sembol"]))
            if symbols:
                for sym in symbols:
                    row1 = df1[df1["Sembol"] == sym].iloc[0]; row2 = df2[df2["Sembol"] == sym].iloc[0]
                    commons.append({"symbol": sym, "r1": row1, "r2": row2})
                for item in commons:
                    sym = item["symbol"]
                    c1, c2 = st.columns([0.2, 0.8])
                    if c1.button("★", key=f"c_s_{sym}"): toggle_watchlist(sym); st.rerun()
                    if c2.button(f"{sym} | R1: {item['r1']['Skor']}/8 | R2: {item['r2']['Skor']}/8", key=f"c_b_{sym}"): on_scan_result_click(sym); st.rerun()
            else: st.info("Kesişim yok.")
        else: st.caption("İki radar da çalıştırılmalı.")

    st.markdown("<hr>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["🧠 Radar 1", "🚀 Radar 2", "📜 İzleme"])
    
    with tab1:
        if st.button(f"⚡ {st.session_state.category} Tara", type="primary"):
            with st.spinner("..."): st.session_state.scan_data = analyze_market_intelligence(ASSET_GROUPS.get(st.session_state.category, []))
        if st.session_state.scan_data is not None:
            # 500px Scrollbar Düzeltildi
            with st.container(height=500):
                for i, row in st.session_state.scan_data.iterrows():
                    sym = row["Sembol"]
                    c1, c2 = st.columns([0.2, 0.8])
                    if c1.button("★", key=f"r1_s_{sym}_{i}"): toggle_watchlist(sym); st.rerun()
                    if c2.button(f"🔥 {row['Skor']}/8 | {sym}", key=f"r1_b_{sym}_{i}"): on_scan_result_click(sym); st.rerun()
                    st.caption(row['Nedenler'])

    with tab2:
        if st.button(f"🚀 RADAR 2 Tara", type="primary"):
            with st.spinner("..."): st.session_state.radar2_data = radar2_scan(ASSET_GROUPS.get(st.session_state.category, []))
        if st.session_state.radar2_data is not None:
            # 500px Scrollbar Düzeltildi
            with st.container(height=500):
                for i, row in st.session_state.radar2_data.iterrows():
                    sym = row["Sembol"]
                    c1, c2 = st.columns([0.2, 0.8])
                    if c1.button("★", key=f"r2_s_{sym}_{i}"): toggle_watchlist(sym); st.rerun()
                    if c2.button(f"🚀 {row['Skor']}/8 | {sym} | {row['Setup']}", key=f"r2_b_{sym}_{i}"): on_scan_result_click(sym); st.rerun()
                    st.caption(f"Trend: {row['Trend']} | RS: {row['RS']}%")

    with tab3:
        if st.button("⚡ İzleme Listesini Tara", type="secondary"):
            with st.spinner("..."): st.session_state.scan_data = analyze_market_intelligence(st.session_state.watchlist)
        for sym in st.session_state.watchlist:
            c1, c2 = st.columns([0.2, 0.8])
            if c1.button("❌", key=f"wl_d_{sym}"): toggle_watchlist(sym); st.rerun()
            if c2.button(sym, key=f"wl_g_{sym}"): on_scan_result_click(sym); st.rerun()
