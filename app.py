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
import time
import threading
import concurrent.futures
import re
import textwrap

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Patronun Terminali v5.0 (Full Hunter)",
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
    
    section.main > div.block-container {{ padding-top: 1rem; padding-bottom: 2rem; }}
    
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

    /* AVCI GÜNLÜĞÜ STİLLERİ */
    .hunter-badge-green {{ background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 12px; font-size: 0.65rem; font-weight: 700; }}
    .hunter-badge-red {{ background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 12px; font-size: 0.65rem; font-weight: 700; }}
    .hunter-badge-blue {{ background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 12px; font-size: 0.65rem; font-weight: 700; }}

    /* ICT BAR STİLİ */
    .ict-bar-container {{
        width: 100%; height: 6px; background-color: #e2e8f0; border-radius: 3px; overflow: hidden; margin: 4px 0; display:flex;
    }}
    .ict-bar-fill {{ height: 100%; transition: width 0.5s ease; }}
    
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
raw_sp500_rest = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "AMD", "INTC", "QCOM", "TXN", "AMAT", "LRCX", "MU", "ADI", "CSCO", "ORCL", "CRM", "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "LLY", "UNH", "JNJ", "MRK", "ABBV", "WMT", "HD", "PG", "COST", "KO", "PEP", "MCD", "SBUX", "NKE", "DIS", "XOM", "CVX", "COP", "SLB", "GE", "CAT", "DE", "BA", "LMT", "UPS", "FDX"]
raw_sp500_rest = list(set(raw_sp500_rest) - set(priority_sp))
raw_sp500_rest.sort()
final_sp500_list = priority_sp + raw_sp500_rest

priority_crypto = ["GC=F", "SI=F", "BTC-USD", "ETH-USD"]
other_crypto = ["BNB-USD", "SOL-USD", "XRP-USD", "ADA-USD", "DOGE-USD", "AVAX-USD", "TRX-USD", "LINK-USD", "DOT-USD", "MATIC-USD", "LTC-USD"]
other_crypto.sort()
final_crypto_list = priority_crypto + other_crypto

raw_nasdaq = ["AAPL", "MSFT", "NVDA", "AMZN", "AVGO", "META", "TSLA", "GOOGL", "COST", "NFLX", "AMD", "PEP", "LIN", "TMUS", "CSCO", "QCOM", "INTU", "AMAT", "TXN", "HON", "AMGN", "BKNG", "ISRG", "CMCSA", "SBUX", "MDLZ", "GILD", "ADP", "ADI"]
raw_nasdaq = sorted(list(set(raw_nasdaq)))

priority_bist = ["AKBNK.IS", "BIMAS.IS", "DOHOL.IS", "FENER.IS", "KCHOL.IS", "SISE.IS", "TCELL.IS", "THYAO.IS", "TTKOM.IS", "VAKBN.IS"]
raw_bist100_rest = ["AEFES.IS", "AGHOL.IS", "ALARK.IS", "ARCLK.IS", "ASELS.IS", "ASTOR.IS", "BIOEN.IS", "CCOLA.IS", "CIMSA.IS", "DOAS.IS", "EKGYO.IS", "ENJSA.IS", "ENKAI.IS", "EREGL.IS", "EUPWR.IS", "FROTO.IS", "GARAN.IS", "GESAN.IS", "GUBRF.IS", "HALKB.IS", "HEKTS.IS", "ISCTR.IS", "ISDMR.IS", "ISGYO.IS", "ISMEN.IS", "KONTR.IS", "KOZAL.IS", "KRDMD.IS", "MGROS.IS", "ODAS.IS", "OYAKC.IS", "PETKM.IS", "PGSUS.IS", "SAHOL.IS", "SASA.IS", "SMRTG.IS", "SOKM.IS", "TAVHL.IS", "TOASO.IS", "TUPRS.IS", "YKBNK.IS"]
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

# --- ANALİZ MOTORLARI (TAM SÜRÜM - RESTORED) ---
@st.cache_data(ttl=3600)
def analyze_market_intelligence(asset_list):
    if not asset_list: return pd.DataFrame()
    try:
        data = yf.download(asset_list, period="6mo", group_by='ticker', threads=True, progress=False)
    except: return pd.DataFrame()

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
            sma20 = close.rolling(20).mean(); std20 = close.rolling(20).std()
            bb_width = ((sma20 + 2*std20) - (sma20 - 2*std20)) / (sma20 + 0.0001)
            hist = (close.ewm(span=12).mean() - close.ewm(span=26).mean()) - (close.ewm(span=12).mean() - close.ewm(span=26).mean()).ewm(span=9).mean()
            delta = close.diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + (gain / loss)))
            williams_r = (high.rolling(14).max() - close) / (high.rolling(14).max() - low.rolling(14).min()) * -100
            daily_range = high - low
            
            score = 0; reasons = []
            curr_c = float(close.iloc[-1]); curr_vol = float(volume.iloc[-1])
            avg_vol = float(volume.rolling(5).mean().iloc[-1]) if len(volume) > 5 else 1.0
            
            if bb_width.iloc[-1] <= bb_width.tail(60).min() * 1.1: score += 1; reasons.append("🚀 Squeeze")
            if daily_range.iloc[-1] == daily_range.tail(4).min() and daily_range.iloc[-1] > 0: score += 1; reasons.append("🔇 NR4")
            if ((ema5.iloc[-1] > ema20.iloc[-1]) and (ema5.iloc[-2] <= ema20.iloc[-2])): score += 1; reasons.append("⚡ Trend")
            if hist.iloc[-1] > hist.iloc[-2]: score += 1; reasons.append("🟢 MACD")
            if williams_r.iloc[-1] > -50: score += 1; reasons.append("🔫 W%R")
            if curr_vol > avg_vol * 1.2: score += 1; reasons.append("🔊 Hacim")
            if curr_c >= high.tail(20).max() * 0.98: score += 1; reasons.append("🔨 Breakout")
            if 30 < rsi.iloc[-1] < 65 and rsi.iloc[-1] > rsi.iloc[-2]: score += 1; reasons.append("⚓ RSI Güçlü")
            
            if score > 0:
                return {"Sembol": symbol, "Fiyat": f"{curr_c:.2f}", "Skor": score, "Nedenler": " | ".join(reasons)}
            return None
        except: return None

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(process_symbol, asset_list))
    
    signals = [r for r in results if r is not None]
    return pd.DataFrame(signals).sort_values(by="Skor", ascending=False) if signals else pd.DataFrame()

@st.cache_data(ttl=3600)
def radar2_scan(asset_list):
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
            
            close = df['Close']; high = df['High']
            curr_c = float(close.iloc[-1])
            sma20 = close.rolling(20).mean(); sma50 = close.rolling(50).mean()
            sma100 = close.rolling(100).mean(); sma200 = close.rolling(200).mean()
            
            trend = "Yatay"
            if not np.isnan(sma200.iloc[-1]):
                if curr_c > sma50.iloc[-1] > sma100.iloc[-1] > sma200.iloc[-1]: trend = "Boğa"
                elif curr_c < sma200.iloc[-1]: trend = "Ayı"
            
            delta = close.diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + (gain / loss))); rsi_c = float(rsi.iloc[-1])
            hist = (close.ewm(span=12).mean() - close.ewm(span=26).mean()) - (close.ewm(span=12).mean() - close.ewm(span=26).mean()).ewm(span=9).mean()
            
            breakout_ratio = curr_c / high.rolling(60).max().iloc[-1] if high.rolling(60).max().iloc[-1] > 0 else 0
            
            rs_score = 0.0
            if idx is not None and len(close) > 60 and len(idx) > 60:
                rs_score = float((close.iloc[-1]/close.iloc[-60]-1) - (idx.iloc[-1]/idx.iloc[-60]-1))
            
            setup = "-"; tags = []; score = 0
            if trend == "Boğa" and breakout_ratio >= 0.97: setup = "Breakout"; score += 2; tags.append("Zirve")
            if trend == "Boğa" and setup == "-" and sma20.iloc[-1] <= curr_c <= sma50.iloc[-1] * 1.02: setup = "Pullback"; score += 2; tags.append("Düzeltme")
            if setup == "-" and rsi.iloc[-2] < 30 <= rsi_c and hist.iloc[-1] > hist.iloc[-2]: setup = "Dip Dönüşü"; score += 2; tags.append("Dip Dönüşü")
            
            if rs_score > 0: score += 1; tags.append("RS+")
            if trend == "Boğa": score += 1
            
            if score > 0:
                return {"Sembol": symbol, "Fiyat": round(curr_c, 2), "Trend": trend, "Setup": setup, "Skor": score, "RS": round(rs_score * 100, 1), "Etiketler": " | ".join(tags)}
            return None
        except: return None

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(process_radar2, asset_list))
    return pd.DataFrame([r for r in results if r is not None]).sort_values(by=["Skor", "RS"], ascending=False).head(50)

@st.cache_data(ttl=600)
def calculate_sentiment_score(ticker):
    try:
        df = yf.download(ticker, period="6mo", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']; high = df['High']; low = df['Low']; volume = df['Volume']
        
        score_mom = 0; reasons_mom = []
        rsi = 100 - (100 / (1 + (close.diff().clip(lower=0).rolling(14).mean() / close.diff().clip(upper=0).abs().rolling(14).mean())))
        if rsi.iloc[-1] > 50: score_mom += 10; reasons_mom.append("RSI ↑")
        
        score_vol = 0; reasons_vol = []
        if volume.iloc[-1] > volume.rolling(20).mean().iloc[-1]: score_vol += 15; reasons_vol.append("Vol ↑")
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        if obv.iloc[-1] > obv.rolling(5).mean().iloc[-1]: score_vol += 10; reasons_vol.append("OBV ↑")
        
        score_tr = 0; reasons_tr = []
        sma50 = close.rolling(50).mean()
        if close.iloc[-1] > sma50.iloc[-1]: score_tr += 10; reasons_tr.append("P > SMA50")
        
        score_vola = 0; reasons_vola = []
        std = close.rolling(20).std(); upper = close.rolling(20).mean() + (2 * std)
        if close.iloc[-1] > upper.iloc[-1]: score_vola += 10; reasons_vola.append("BB Break")
        
        score_str = 0; reasons_str = []
        if close.iloc[-1] > high.rolling(20).max().shift(1).iloc[-1]: score_str += 10; reasons_str.append("BOS")
        
        total = score_mom + score_vol + score_tr + score_vola + score_str
        bars = int(total / 5)
        bar_str = "[" + "|" * bars + "." * (20 - bars) + "]"
        
        return {
            "total": total, "bar": bar_str,
            "mom": f"{score_mom}/30 ({'+'.join(reasons_mom)})",
            "vol": f"{score_vol}/25 ({'+'.join(reasons_vol)})",
            "tr": f"{score_tr}/20 ({'+'.join(reasons_tr)})",
            "vola": f"{score_vola}/15 ({'+'.join(reasons_vola)})",
            "str": f"{score_str}/10 ({'+'.join(reasons_str)})",
            "raw_rsi": rsi.iloc[-1], "raw_obv": obv.iloc[-1]
        }
    except: return None

@st.cache_data(ttl=600)
def calculate_ict_concepts(ticker):
    try:
        df = yf.download(ticker, period="1y", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']; high = df['High']; low = df['Low']
        if len(df) < 60: return {"summary": "Veri Yetersiz"}
        curr_price = float(close.iloc[-1])
        
        sw_highs = []; sw_lows = []
        for i in range(2, len(df)-2):
            if (high.iloc[i] > high.iloc[i-1] and high.iloc[i] > high.iloc[i-2] and high.iloc[i] > high.iloc[i+1] and high.iloc[i] > high.iloc[i+2]):
                sw_highs.append((df.index[i], float(high.iloc[i]), i))
            if (low.iloc[i] < low.iloc[i-1] and low.iloc[i] < low.iloc[i-2] and low.iloc[i] < low.iloc[i+1] and low.iloc[i] < low.iloc[i+2]):
                sw_lows.append((df.index[i], float(low.iloc[i]), i))

        if not sw_highs or not sw_lows: return {"summary": "Swing Bulunamadı"}
        last_sh = sw_highs[-1][1]; last_sl = sw_lows[-1][1]; last_sh_idx = sw_highs[-1][2]; last_sl_idx = sw_lows[-1][2]
        r_high = last_sh; r_low = last_sl
        
        structure = "YATAY"; bias_color = "gray"
        if curr_price > last_sh: structure = "BOS (Bullish)"; bias_color = "green"
        elif curr_price < last_sl: structure = "BOS (Bearish)"; bias_color = "red"
        else:
            if last_sh_idx > last_sl_idx: structure = "Internal (Düşüş)"; bias_color = "blue"
            else: structure = "Internal (Yükseliş)"; bias_color = "blue"

        range_size = max(r_high - r_low, 1)
        range_pos_pct = ((curr_price - r_low) / range_size) * 100
        pos_label = "Equilibrium"; is_discount = False; is_ote = False
        
        if range_pos_pct > 50:
            pos_label = "Premium (OTE)" if 62 < range_pos_pct < 79 else "Premium"
            is_ote = (62 < range_pos_pct < 79)
        else:
            pos_label = "Discount (OTE)" if 21 < range_pos_pct < 38 else "Discount"
            is_discount = True; is_ote = (21 < range_pos_pct < 38)

        active_fvg = "Yok"; fvg_color = "gray"; bullish_fvgs = []; bearish_fvgs = []
        for i in range(max(0, len(df)-50), len(df)-2):
            if low.iloc[i] > high.iloc[i-2]: bullish_fvgs.append({'top': low.iloc[i], 'bot': high.iloc[i-2]})
            if high.iloc[i] < low.iloc[i-2]: bearish_fvgs.append({'top': low.iloc[i-2], 'bot': high.iloc[i]})
        
        if is_discount and bullish_fvgs:
            fvg = bullish_fvgs[-1]; active_fvg = f"BISI: {fvg['bot']:.2f}-{fvg['top']:.2f}"; fvg_color = "green"
        elif not is_discount and bearish_fvgs:
            fvg = bearish_fvgs[-1]; active_fvg = f"SIBI: {fvg['bot']:.2f}-{fvg['top']:.2f}"; fvg_color = "red"

        next_bsl = min([h[1] for h in sw_highs if h[1] > curr_price], default=None)
        next_ssl = max([l[1] for l in sw_lows if l[1] < curr_price], default=None)
        liq_target = f"BSL: {next_bsl:.2f}" if next_bsl and (not next_ssl or abs(next_bsl-curr_price) < abs(curr_price-next_ssl)) else f"SSL: {next_ssl:.2f}" if next_ssl else "Belirsiz"

        golden_txt = "İzlemede"; is_golden = False
        if is_discount and bias_color == "green" and fvg_color == "green":
            golden_txt = "🔥 LONG FIRSATI"; is_golden = True
        elif not is_discount and bias_color == "red" and fvg_color == "red":
            golden_txt = "❄️ SHORT FIRSATI"; is_golden = True
        elif is_ote: golden_txt = "⚖️ OTE Bölgesi"

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
        sma50 = close.rolling(50).mean().iloc[-1]; ema144 = close.ewm(span=144, adjust=False).mean().iloc[-1]
        atr = (high-low).rolling(14).mean().iloc[-1]
        return {"sma50": sma50, "ema144": ema144, "stop_level": close.iloc[-1] - (2 * atr), "risk_pct": (2 * atr) / close.iloc[-1] * 100, "atr": atr}
    except: return None

@st.cache_data(ttl=1200)
def fetch_google_news(ticker):
    try:
        clean = ticker.replace(".IS", "").replace("=F", "")
        rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote_plus(f'{clean} stock news')}&hl=tr&gl=TR&ceid=TR:tr"
        feed = feedparser.parse(rss_url)
        news = []
        for entry in feed.entries[:6]:
            dt = datetime.now() 
            try: dt = datetime(*entry.published_parsed[:6])
            except: pass
            if dt < datetime.now() - timedelta(days=10): continue
            pol = TextBlob(entry.title).sentiment.polarity
            color = "#16A34A" if pol > 0.1 else "#DC2626" if pol < -0.1 else "#64748B"
            news.append({'title': entry.title, 'link': entry.link, 'date': dt.strftime('%d %b'), 'source': entry.source.title, 'color': color})
        return news
    except: return []

def get_deep_xray_data(ticker):
    sent = calculate_sentiment_score(ticker)
    if not sent: return None
    def icon(cond): return "✅" if cond else "❌"
    return {
        "mom_rsi": f"{icon(sent['raw_rsi']>50)} RSI Trendi",
        "vol_obv": f"{icon('OBV ↑' in sent['vol'])} OBV Akışı",
        "tr_ema": f"{icon('GoldCross' in sent['tr'])} Trend",
        "vola_bb": f"{icon('BB Break' in sent['vola'])} BB Volatilite",
        "str_bos": f"{icon('BOS' in sent['str'])} Market Yapısı"
    }

# --- ARKA PLAN AJANI (BACKGROUND SCANNER) ---
@st.cache_resource
def get_shared_hunter_data():
    return {"results": [], "last_run": None, "is_running": False, "target_list": []}

hunter_data = get_shared_hunter_data()

def run_background_scan():
    """Arka plan tarama döngüsü."""
    while True:
        # Hangi listeyi tarayacak? (Session state yok, hunter_data'dan okur)
        current_targets = hunter_data.get("target_list", [])
        if not current_targets:
             # Varsayılan olarak BIST önceliklileri tara
            current_targets = priority_bist 
        
        # Tarama limiti (IP Ban koruması)
        scan_list = current_targets[:20] if len(current_targets) > 20 else current_targets
        
        temp_results = []
        for ticker in scan_list:
            try:
                # Burası thread içinde, yfinance cache kullanabilir
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
            time.sleep(0.5)
        
        hunter_data["results"] = temp_results
        hunter_data["last_run"] = datetime.now().strftime("%H:%M")
        
        # 60 Saniye Bekle
        time.sleep(60)

def start_hunter_agent():
    if not hunter_data["is_running"]:
        t = threading.Thread(target=run_background_scan, daemon=True)
        t.start()
        hunter_data["is_running"] = True

start_hunter_agent()

# --- RENDER FONKSİYONLARI ---
def render_ict_panel(analysis):
    if not analysis or "summary" in analysis and analysis["summary"] == "Hata":
        st.error("ICT Analizi yapılamadı"); return
    display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")
    s_color = "#166534" if analysis['bias_color'] == "green" else "#991b1b" if analysis['bias_color'] == "red" else "#854d0e"
    pos_pct = analysis['range_pos_pct']
    bar_width = min(max(pos_pct, 5), 95)
    
    golden_badge = f"<div style='margin-top:6px; background:#f0fdf4; border:1px solid #bbf7d0; color:#15803d; padding:6px; border-radius:6px; font-weight:700; text-align:center; font-size:0.75rem;'>✨ {analysis['golden_text']}</div>" if analysis['is_golden'] else f"<div style='margin-top:6px; background:#eff6ff; border:1px solid #bfdbfe; color:#1e40af; padding:6px; border-radius:6px; text-align:center; font-size:0.75rem;'>🎯 {analysis['golden_text']}</div>" if analysis['ote_level'] else f"<div style='margin-top:6px; background:#f8fafc; border:1px solid #e2e8f0; color:#94a3b8; padding:6px; border-radius:6px; text-align:center; font-size:0.75rem;'>{analysis['golden_text']}</div>"

    st.markdown(f"""
<div class="info-card">
<div class="info-header">🧠 ICT Smart Money: {display_ticker}</div>
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
<span style="font-size:0.65rem; color:#64748B;">MARKET YAPISI</span>
<span style="font-size:0.7rem; font-weight:700; color:{s_color};">{analysis['structure']}</span>
</div>
<div style="margin: 8px 0;">
<div style="display:flex; justify-content:space-between; font-size:0.6rem; color:#64748B;"><span>Discount</span><span>EQ</span><span>Premium</span></div>
<div class="ict-bar-container"><div class="ict-bar-fill" style="width:{bar_width}%; background: linear-gradient(90deg, #22c55e 0%, #cbd5e1 50%, #ef4444 100%);"></div></div>
<div style="text-align:center; font-size:0.7rem; font-weight:600; color:#0f172a;">{analysis['pos_label']} <span style="color:#64748B;">(%{pos_pct:.1f})</span></div>
</div>
<div class="info-row"><div class="label-long">FVG:</div><div class="info-val" style="color:{'#166534' if analysis['fvg_color']=='green' else '#991b1b' if analysis['fvg_color']=='red' else '#64748B'}; font-weight:600;">{analysis['fvg']}</div></div>
<div class="info-row"><div class="label-long">Hedef Likidite:</div><div class="info-val">{analysis['liquidity']}</div></div>
{golden_badge}
</div>
""", unsafe_allow_html=True)

def render_sentiment_card(sent):
    if not sent: return
    color = "🔥" if sent['total'] >= 70 else "❄️" if sent['total'] <= 30 else "⚖️"
    st.markdown(f"""
    <div class="info-card">
        <div class="info-header">🎭 Sentiment Analizi</div>
        <div style="font-weight:700; color:#1e40af; font-size:0.8rem; margin-bottom:4px;">SKOR: {sent['total']}/100 {color}</div>
        <div style="font-family:'Courier New'; font-size:0.7rem; color:#1e3a8a; margin-bottom:4px;">{sent['bar']}</div>
        <div class="info-row"><div class="label-long">Momentum:</div><div class="info-val">{sent['mom']}</div></div>
        <div class="info-row"><div class="label-long">Hacim:</div><div class="info-val">{sent['vol']}</div></div>
        <div class="info-row"><div class="label-long">Trend:</div><div class="info-val">{sent['tr']}</div></div>
        <div class="info-row"><div class="label-long">Volatilite:</div><div class="info-val">{sent['vola']}</div></div>
    </div>
    """, unsafe_allow_html=True)

def render_tech_card(ticker):
    dt = get_tech_card_data(ticker)
    if not dt: return
    st.markdown(f"""
    <div class="info-card">
        <div class="info-header">📋 Teknik Kart</div>
        <div class="info-row"><div class="label-long">SMA50:</div><div class="info-val">{dt['sma50']:.2f}</div></div>
        <div class="info-row"><div class="label-long">EMA144:</div><div class="info-val">{dt['ema144']:.2f}</div></div>
        <div class="info-row"><div class="label-long">ATR (Risk):</div><div class="info-val">{dt['atr']:.2f} (%{dt['risk_pct']:.1f})</div></div>
        <div class="info-row"><div class="label-long">Stop Seviyesi:</div><div class="info-val">{dt['stop_level']:.2f}</div></div>
    </div>
    """, unsafe_allow_html=True)

def render_deep_xray(xray):
    if not xray: return
    st.markdown(f"""
    <div class="info-card">
        <div class="info-header">🔍 Derin Röntgen</div>
        <div class="info-row"><div class="label-long">Trend Gücü:</div><div class="info-val">{xray['mom_rsi']}</div></div>
        <div class="info-row"><div class="label-long">Akıllı Para:</div><div class="info-val">{xray['vol_obv']}</div></div>
        <div class="info-row"><div class="label-long">Ortalamalar:</div><div class="info-val">{xray['tr_ema']}</div></div>
        <div class="info-row"><div class="label-long">Kırılım:</div><div class="info-val">{xray['str_bos']}</div></div>
    </div>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=300)
def fetch_stock_info(ticker):
    try:
        info = yf.Ticker(ticker).info
        return {
            'price': info.get('currentPrice') or info.get('regularMarketPrice', 0),
            'change_pct': ((info.get('currentPrice', 0) or info.get('regularMarketPrice', 1)) - info.get('previousClose', 1)) / info.get('previousClose', 1) * 100,
            'volume': info.get('volume', 0),
            'sector': info.get('sector', '-'),
            'target': info.get('targetMeanPrice', '-')
        }
    except: return None

# --- CALLBACKLER ---
def on_category_change():
    new_cat = st.session_state.get("selected_category_key")
    if new_cat and new_cat in ASSET_GROUPS:
        st.session_state.category = new_cat
        st.session_state.ticker = ASSET_GROUPS[new_cat][0]
        # AJAN HEDEFİNİ GÜNCELLE
        hunter_data["target_list"] = ASSET_GROUPS[new_cat]
        st.session_state.scan_data = None
        st.session_state.radar2_data = None

def on_asset_change():
    new_asset = st.session_state.get("selected_asset_key")
    if new_asset: st.session_state.ticker = new_asset

def on_hunter_click(symbol):
    st.session_state.ticker = symbol

def toggle_watchlist(symbol):
    wl = st.session_state.watchlist
    if symbol in wl: remove_watchlist_db(symbol); wl.remove(symbol)
    else: add_watchlist_db(symbol); wl.append(symbol)
    st.session_state.watchlist = wl

# --- HEADER ---
st.markdown(f"""
<div class="header-container" style="display:flex; align-items:center;">
    <div style="font-size:2rem; margin-right:10px;">🐂</div>
    <div>
        <div style="font-size:1.5rem; font-weight:700; color:#1e3a8a;">Patronun Terminali v5.0</div>
        <div style="font-size:0.8rem; color:#64748B;">Full Hunter Edition (Background Agent Active 🟢)</div>
    </div>
</div>
<hr style="border:0; border-top: 1px solid #e5e7eb; margin-top:5px; margin-bottom:10px;">
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### ⚙️ Ayarlar")
    selected_theme_name = st.selectbox("", ["Beyaz", "Kirli Beyaz", "Buz Mavisi"], index=["Beyaz", "Kirli Beyaz", "Buz Mavisi"].index(st.session_state.theme), label_visibility="collapsed")
    if selected_theme_name != st.session_state.theme:
        st.session_state.theme = selected_theme_name
        st.rerun()
    st.divider()
    with st.expander("🤖 AI Analist (Prompt)", expanded=True):
        if st.button("📋 Analiz Metnini Hazırla", type="primary"):
            st.session_state.generate_prompt = True

# --- FİLTRELER ---
col_cat, col_ass, col_search_in, col_search_btn = st.columns([1.5, 2, 2, 0.7])
try: cat_index = list(ASSET_GROUPS.keys()).index(st.session_state.category)
except ValueError: cat_index = 0

with col_cat:
    st.selectbox("Kategori", list(ASSET_GROUPS.keys()), index=cat_index, key="selected_category_key", on_change=on_category_change, label_visibility="collapsed")
    # Ajanın hedef listesini senkronize et (Sayfa her yenilendiğinde)
    hunter_data["target_list"] = ASSET_GROUPS[st.session_state.category]

with col_ass:
    opts = ASSET_GROUPS.get(st.session_state.category, ASSET_GROUPS[INITIAL_CATEGORY])
    try: asset_idx = opts.index(st.session_state.ticker)
    except ValueError: asset_idx = 0
    st.selectbox("Varlık Listesi", opts, index=asset_idx, key="selected_asset_key", on_change=on_asset_change, label_visibility="collapsed")
with col_search_in:
    st.text_input("Manuel", placeholder="Kod", key="manual_input_key", label_visibility="collapsed")
with col_search_btn:
    if st.button("Ara"): st.session_state.ticker = st.session_state.manual_input_key.upper()

# --- AVCI GÜNLÜĞÜ (HUNTER PANEL) ---
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
            rc3.caption(f"{opp['detail']} (S:{opp['score']})")
            if rc4.button("🔍 Git", key=f"btn_hunt_{opp['symbol']}"):
                on_hunter_click(opp['symbol']); st.rerun()

# --- ANA EKRAN ---
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
    tv_symbol = st.session_state.ticker.replace('.IS', '').strip()
    if "=F" in tv_symbol: tv_symbol = "TVC:GOLD" if "GC" in tv_symbol else "TVC:SILVER"
    elif "-USD" in tv_symbol: tv_symbol = f"BINANCE:{tv_symbol.replace('-USD','USDT')}"
    
    components.html(f"""
    <div class="tradingview-widget-container">
        <div id="tradingview_chart"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
        new TradingView.widget({{
            "width": "100%", "height": 500, "symbol": "{tv_symbol}", "interval": "D", "timezone": "Etc/UTC", "theme": "light", "style": "1", "locale": "tr", "toolbar_bg": "#f1f3f6", "enable_publishing": false, "allow_symbol_change": true, "container_id": "tradingview_chart"
        }});
        </script>
    </div>
    """, height=500)
    
    # HABERLERİ GERİ GETİRDİM
    st.markdown("### 📰 Son Dakika Haberler")
    news = fetch_google_news(st.session_state.ticker)
    if news:
        for n in news:
            st.markdown(f"<div class='news-card'><a href='{n['link']}' class='news-title' target='_blank'>{n['title']}</a><div class='news-meta'>{n['source']} • {n['date']}</div></div>", unsafe_allow_html=True)
    else:
        st.caption("Haber bulunamadı.")

with col_right:
    ict_data = calculate_ict_concepts(st.session_state.ticker)
    render_ict_panel(ict_data)
    
    sent_data = calculate_sentiment_score(st.session_state.ticker)
    render_sentiment_card(sent_data)
    
    render_tech_card(st.session_state.ticker)
    
    xray_data = get_deep_xray_data(st.session_state.ticker)
    render_deep_xray(xray_data)

# --- ALT TABLAR (RADARLAR GERİ DÖNDÜ) ---
st.markdown("<hr>", unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["🧠 RADAR 1 (Sinyal)", "🚀 RADAR 2 (Setup)", "📜 İzleme"])

with tab1:
    if st.button(f"⚡ {st.session_state.category} Tara (Radar 1)", type="primary"):
        with st.spinner("Sinyaller taranıyor..."):
            st.session_state.scan_data = analyze_market_intelligence(ASSET_GROUPS.get(st.session_state.category, []))
    if st.session_state.scan_data is not None:
        st.dataframe(st.session_state.scan_data, use_container_width=True)

with tab2:
    if st.button(f"🚀 {st.session_state.category} Tara (Radar 2)", type="primary"):
        with st.spinner("Setuplar taranıyor..."):
            st.session_state.radar2_data = radar2_scan(ASSET_GROUPS.get(st.session_state.category, []))
    if st.session_state.radar2_data is not None:
        st.dataframe(st.session_state.radar2_data, use_container_width=True)

with tab3:
    wl = st.session_state.watchlist
    if not wl: st.info("İzleme listesi boş.")
    else:
        for sym in wl:
            c1, c2 = st.columns([0.1, 0.9])
            if c1.button("❌", key=f"del_{sym}"): toggle_watchlist(sym); st.rerun()
            if c2.button(sym, key=f"go_{sym}"): on_hunter_click(sym); st.rerun()

# --- PROMPT ---
if st.session_state.get('generate_prompt'):
    t = st.session_state.ticker
    ict = calculate_ict_concepts(t) or {}
    sent = calculate_sentiment_score(t) or {}
    radar_val = "Veri Yok"
    if st.session_state.radar2_data is not None:
        row = st.session_state.radar2_data[st.session_state.radar2_data['Sembol'] == t]
        if not row.empty: radar_val = f"{row.iloc[0]['Skor']}/8"
    
    prompt = f"""
*** PATRON TERMİNALİ ANALİZ RAPORU: {t} ***
TEKNİK DURUM:
- Fiyat: {info['price'] if info else 'Yok'}
- Radar Skoru: {radar_val}
- Sentiment: {sent.get('total', 0)}/100
ICT ANALİZİ:
- Yapı: {ict.get('structure', '-')}
- Bölge: {ict.get('pos_label', '-')}
- FVG: {ict.get('fvg', '-')}
- GOLDEN SİNYAL: {ict.get('golden_text', 'Yok')}
    """
    with st.sidebar:
        st.code(prompt, language="text")
        st.success("Kopyala ve AI'ya yapıştır!")
    st.session_state.generate_prompt = False
