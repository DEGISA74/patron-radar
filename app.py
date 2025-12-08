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

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Patronun Terminali v3.9.0",
    layout="wide",
    page_icon="🐂"
)

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

# --- TEMA MOTORU ---
if 'theme' not in st.session_state:
    st.session_state.theme = "Buz Mavisi"

THEMES = {
    "Beyaz": {"bg": "#FFFFFF", "box_bg": "#F8F9FA", "text": "#000000", "border": "#DEE2E6", "news_bg": "#FFFFFF"},
    "Kirli Beyaz": {"bg": "#FAF9F6", "box_bg": "#FFFFFF", "text": "#2C3E50", "border": "#E5E7EB", "news_bg": "#FFFFFF"},
    "Buz Mavisi": {"bg": "#F0F8FF", "box_bg": "#FFFFFF", "text": "#0F172A", "border": "#BFDBFE", "news_bg": "#FFFFFF"}
}
current_theme = THEMES[st.session_state.theme]

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

# --- DİNAMİK CSS ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&display=swap');
    
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {current_theme['text']}; }}
    .stApp {{ background-color: {current_theme['bg']}; }}
    
    /* DASHBOARD STİLİ */
    .dashboard-container {{
        display: flex; flex-wrap: wrap; gap: 10px; justify-content: space-between;
        background-color: {current_theme['box_bg']}; padding: 8px 12px;
        border-bottom: 1px solid {current_theme['border']}; margin-top: -10px; margin-bottom: 10px;
        border-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }}
    .dash-item {{ font-size: 0.8rem; font-family: 'JetBrains Mono', monospace; display: flex; align-items: center; }}
    .dash-label {{ color: #64748B; margin-right: 5px; font-weight: 600; }}
    .dash-val {{ font-weight: 700; color: {current_theme['text']}; }}
    .dash-delta {{ font-size: 0.7rem; margin-left: 3px; }}

    /* Layout Sıkılaştırma */
    section.main > div.block-container {{ padding-top: 0.5rem; padding-bottom: 2rem; }}
    .header-container {{ margin-bottom: 0.5rem; }}
    
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
    
    /* TEKNİK KART STİLİ */
    .tech-card {{
        background: {current_theme['box_bg']}; border: 1px solid {current_theme['border']};
        border-radius: 6px; padding: 8px; margin-top: 5px; margin-bottom: 10px;
        font-size: 0.8rem; font-family: 'Inter', sans-serif;
    }}
    .tech-header {{ font-weight: 700; color: #1e3a8a; border-bottom: 1px solid {current_theme['border']}; padding-bottom: 4px; margin-bottom: 4px; }}
    .tech-row {{ display: flex; align-items: center; margin-bottom: 3px; }}
    .tech-label {{ font-weight: 600; color: #64748B; width: 80px; flex-shrink: 0; }}
    .tech-val {{ color: {current_theme['text']}; }}
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR & AI ANALIST ---
with st.sidebar:
    st.markdown("### ⚙️ Ayarlar")
    selected_theme_name = st.selectbox("", ["Beyaz", "Kirli Beyaz", "Buz Mavisi"], index=["Beyaz", "Kirli Beyaz", "Buz Mavisi"].index(st.session_state.theme), label_visibility="collapsed")
    if selected_theme_name != st.session_state.theme:
        st.session_state.theme = selected_theme_name
        st.rerun()

    st.divider()
    
    with st.expander("🤖 AI Analist (Prompt Oluştur)", expanded=True):
        st.caption("Verileri otomatik toplar, ChatGPT/Gemini için metin hazırlar.")
        if st.button("📋 Analiz Metnini Hazırla", type="primary"):
            ticker = st.session_state.ticker
            info = yf.Ticker(ticker).info
            price = info.get('currentPrice', 'Bilinmiyor')
            
            r1_text = "Tarama yapılmadı"
            if st.session_state.scan_data is not None:
                row = st.session_state.scan_data[st.session_state.scan_data["Sembol"] == ticker]
                if not row.empty: r1_text = f"Skor {row.iloc[0]['Skor']}/8. Nedenler: {row.iloc[0]['Nedenler']}"
            
            r2_text = "Tarama yapılmadı"
            if st.session_state.radar2_data is not None:
                row = st.session_state.radar2_data[st.session_state.radar2_data["Sembol"] == ticker]
                if not row.empty: r2_text = f"{row.iloc[0]['Trend']} Trend | {row.iloc[0]['Setup']} | RS: {row.iloc[0]['RS']}%"
            
            tech_extra = "Veri bekleniyor..."
            atr_text = "Veri bekleniyor..."
            try:
                df = yf.download(ticker, period="2y", progress=False)
                if not df.empty:
                     if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                     close = df['Close']; high = df['High']; low = df['Low']
                     tech_extra = f"SMA50: {close.rolling(50).mean().iloc[-1]:.2f}, SMA200: {close.rolling(200).mean().iloc[-1]:.2f}, EMA144: {close.ewm(span=144, adjust=False).mean().iloc[-1]:.2f}"
                     
                     # ATR Hesaplama
                     tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
                     atr = tr.rolling(14).mean().iloc[-1]
                     atr_text = f"ATR (14): {atr:.2f} (2x Stop: {close.iloc[-1] - 2*atr:.2f})"
            except: pass

            prompt_text = f"""
            Rol: Profesyonel borsa traderı.
            Görev: {ticker} hissesi için teknik analiz yorumu yap.
            
            Veriler:
            - Fiyat: {price} USD
            - Radar 1 (Momentum): {r1_text}
            - Radar 2 (Trend/Yapı): {r2_text}
            - Ortalamalar: {tech_extra}
            - Risk Yönetimi: {atr_text}
            
            İstek:
            - Al/Sat/Bekle tavsiyesi verme.
            - Risk ve fırsat durumunu değerlendir.
            - Destek/Direnç veya trend durumu hakkında kısa, vurucu 3 cümle kur.
            - Türkçe yanıtla.
            """
            st.code(prompt_text, language="markdown")

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
    if st.session_state.manual_input_key: st.session_state.ticker = st.session_state.manual_input_key.upper()

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

# --- DASHBOARD (YENİ) ---
def render_dashboard():
    indices = {
        "Dow Jones": "^DJI", "S&P 500": "^GSPC", "NASDAQ": "^IXIC", 
        "ONS Altın": "GC=F", "BIST 100": "XU100.IS", 
        "USD/TL": "TRY=X", "EUR/TL": "EURTRY=X"
    }
    
    html_content = '<div class="dashboard-container">'
    
    try:
        data = yf.download(list(indices.values()), period="5d", progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            close = data['Close']
        else:
            close = data
            
        for name, ticker in indices.items():
            if ticker in close.columns:
                series = close[ticker].dropna()
                if len(series) >= 2:
                    curr = series.iloc[-1]
                    prev = series.iloc[-2]
                    delta = ((curr - prev) / prev) * 100
                    color_cls = "delta-pos" if delta >= 0 else "delta-neg"
                    sign = "+" if delta >= 0 else ""
                    
                    html_content += f"""
                    <div class="dash-item">
                        <span class="dash-label">{name}:</span>
                        <span class="dash-val">{curr:,.2f}</span>
                        <span class="dash-delta {color_cls}">({sign}{delta:.2f}%)</span>
                    </div>
                    """
    except:
        html_content += "<div class='dash-item'>Veri yükleniyor...</div>"
        
    html_content += '</div>'
    st.markdown(html_content, unsafe_allow_html=True)

# --- ANALİZ MOTORLARI (Daily Stable) ---
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

def radar2_scan(asset_list, min_price=5, max_price=500, min_avg_vol_m=1.0):
    if not asset_list: return pd.DataFrame()
    try: data = yf.download(asset_list, period="1y", group_by="ticker", threads=True, progress=False)
    except: return pd.DataFrame()
    try: idx = yf.download("^GSPC", period="1y", progress=False)["Close"]
    except: idx = None

    results = []
    progress_bar = st.progress(0, text=f"RADAR 2: 0/{len(asset_list)} sembol taranıyor...")

    for i, symbol in enumerate(asset_list):
        progress_val = (i + 1) / len(asset_list)
        progress_bar.progress(progress_val, text=f"RADAR 2: {i + 1}/{len(asset_list)} sembol taranıyor: {symbol}")
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol not in data.columns.levels[0]: continue
                df = data[symbol].copy()
            else:
                if len(asset_list) == 1: df = data.copy()
                else: continue

            if df.empty or 'Close' not in df.columns: continue
            df = df.dropna(subset=['Close']) 
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
    progress_bar.empty()
    return pd.DataFrame(results).sort_values(by=["Skor", "RS"], ascending=False).head(50) if results else pd.DataFrame()

# --- TEKNİK KART (GÜNCELLENDİ: 3 Satır + ATR) ---
def render_detail_card(ticker):
    # Satır 1: Radar 1
    r1_content = "<span style='color:#94a3b8; font-style:italic;'>Veri yok (Tara'ya bas)</span>"
    if st.session_state.scan_data is not None:
        row = st.session_state.scan_data[st.session_state.scan_data["Sembol"] == ticker]
        if not row.empty:
            r1_content = f"<b>Skor {row.iloc[0]['Skor']}/8</b> • {row.iloc[0]['Nedenler']}"

    # Satır 2: Radar 2
    r2_content = "<span style='color:#94a3b8; font-style:italic;'>Veri yok (Radar 2 Tara'ya bas)</span>"
    if st.session_state.radar2_data is not None:
        row = st.session_state.radar2_data[st.session_state.radar2_data["Sembol"] == ticker]
        if not row.empty:
            r2_content = f"<b>{row.iloc[0]['Trend']}</b> • {row.iloc[0]['Setup']} • Skor {row.iloc[0]['Skor']} • RS %{row.iloc[0]['RS']}"

    # Satır 3: Ortalamalar ve ATR
    ma_content = "Hesaplanıyor..."
    atr_content = ""
    try:
        df = yf.download(ticker, period="2y", progress=False)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            close = df['Close']; high = df['High']; low = df['Low']
            
            sma50 = close.rolling(50).mean().iloc[-1]
            sma100 = close.rolling(100).mean().iloc[-1]
            sma200 = close.rolling(200).mean().iloc[-1]
            ema144 = close.ewm(span=144, adjust=False).mean().iloc[-1]
            
            # ATR Hesaplama (14 Günlük)
            tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
            atr = tr.rolling(14).mean().iloc[-1]
            stop_level = close.iloc[-1] - (2 * atr)
            
            ma_content = f"SMA50: <b>{sma50:.2f}</b> | SMA100: <b>{sma100:.2f}</b> | SMA200: <b>{sma200:.2f}</b> | EMA144: <b>{ema144:.2f}</b>"
            atr_content = f"ATR Stop (2x): <b style='color:#DC2626'>{stop_level:.2f}</b> (Risk: -{(2*atr)/close.iloc[-1]*100:.1f}%)"
        else:
            ma_content = "Veri hatası."
    except Exception:
        ma_content = "Veri alınamadı."

    st.markdown(f"""
    <div class="tech-card">
        <div class="tech-header">📋 Teknik Kart</div>
        <div class="tech-row"><div class="tech-label">Radar 1:</div><div class="tech-val">{r1_content}</div></div>
        <div class="tech-row"><div class="tech-label">Radar 2:</div><div class="tech-val">{r2_content}</div></div>
        <div class="tech-row"><div class="tech-label">Ortalama:</div><div class="tech-val">{ma_content}</div></div>
        <div class="tech-row"><div class="tech-label">🛡️ Stop:</div><div class="tech-val">{atr_content}</div></div>
    </div>
    """, unsafe_allow_html=True)

def render_tradingview_widget(ticker, height=800):
    tv_symbol = ticker
    if ".IS" in ticker: tv_symbol = f"BIST:{ticker.replace('.IS', '')}"
    elif "=X" in ticker: tv_symbol = f"FX_IDC:{ticker.replace('=X', '')}"
    html = f"""<div class="tradingview-widget-container"><div id="tradingview_chart"></div><script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script><script type="text/javascript">new TradingView.widget({{"width": "100%", "height": {height}, "symbol": "{tv_symbol}", "interval": "D", "timezone": "Etc/UTC", "theme": "light", "style": "1", "locale": "tr", "toolbar_bg": "#f1f3f6", "enable_publishing": false, "allow_symbol_change": true, "container_id": "tradingview_chart"}});</script></div>"""
    components.html(html, height=height)

def fetch_stock_info(ticker):
    try:
        info = yf.Ticker(ticker).info
        return {'price': info.get('currentPrice') or info.get('regularMarketPrice'), 'change_pct': ((info.get('currentPrice') or info.get('regularMarketPrice')) - info.get('previousClose')) / info.get('previousClose') * 100 if info.get('previousClose') else 0, 'volume': info.get('volume', 0), 'sector': info.get('sector', '-'), 'target': info.get('targetMeanPrice', '-')}
    except: return None

@st.cache_data(ttl=300)
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

# --- ARAYÜZ KURULUMU ---
# 1. DASHBOARD (En Üst)
render_dashboard()

st.markdown("""
<div class="header-container" style="display:flex; align-items:center; gap:10px;">
    <div style="font-size:1.8rem;">🐂</div>
    <div>
        <div style="font-size:1.5rem; font-weight:700; color:#1e3a8a;">Patronun Terminali v3.9.0</div>
        <div style="font-size:0.8rem; color:#64748B;">Komuta Merkezi (Dashboard + ATR Stop)</div>
    </div>
</div>
<hr style="border:0; border-top: 1px solid #e5e7eb; margin-top:5px; margin-bottom:10px;">
""", unsafe_allow_html=True)

# FILTRELER
col_cat, col_ass, col_search_in, col_search_btn = st.columns([1.5, 2, 2, 0.7])
with col_cat:
    cat_index = list(ASSET_GROUPS.keys()).index(st.session_state.category) if st.session_state.category in ASSET_GROUPS else 0
    st.selectbox("Kategori", list(ASSET_GROUPS.keys()), index=cat_index, key="selected_category_key", on_change=on_category_change, label_visibility="collapsed")
with col_ass:
    opts = ASSET_GROUPS.get(st.session_state.category, ASSET_GROUPS[INITIAL_CATEGORY])
    idx = opts.index(st.session_state.ticker) if st.session_state.ticker in opts else 0
    st.selectbox("Varlık Listesi", opts, index=idx, key="selected_asset_key", on_change=on_asset_change, label_visibility="collapsed")
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
        sc1.markdown(f'<div class="stat-box-small"><p class="stat-label-small">FİYAT</p><p class="stat-value-small money-text">{info["price"]:.2f}<span class="stat-delta-small {cls}">{"+" if info["change_pct"]>=0 else ""}{info["change_pct"]:.2f}%</span></p></div>', unsafe_allow_html=True)
        sc2.markdown(f'<div class="stat-box-small"><p class="stat-label-small">HACİM</p><p class="stat-value-small money-text">{info["volume"]/1e6:.1f}M</p></div>', unsafe_allow_html=True)
        sc3.markdown(f'<div class="stat-box-small"><p class="stat-label-small">HEDEF</p><p class="stat-value-small money-text">{info["target"]}</p></div>', unsafe_allow_html=True)
        sc4.markdown(f'<div class="stat-box-small"><p class="stat-label-small">SEKTÖR</p><p class="stat-value-small">{str(info["sector"])[:12]}</p></div>', unsafe_allow_html=True)
    
    st.write("")
    # 2. TRADINGVIEW GRAFİĞİ (800PX)
    render_tradingview_widget(st.session_state.ticker)
    
    # 3. YENİ TEKNİK KART (3 Satırlı + ATR)
    render_detail_card(st.session_state.ticker)
    
    # 4. HABERLER
    st.markdown("<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:10px;'>📡 Haber Akışı</div>", unsafe_allow_html=True)
    news = fetch_google_news(st.session_state.ticker)
    if news:
        cols = st.columns(2)
        for i, n in enumerate(news):
            with cols[i%2]:
                st.markdown(f"""<div class="news-card" style="border-left-color: {n['color']};"><a href="{n['link']}" target="_blank" class="news-title">{n['title']}</a><div class="news-meta">{n['date']} • {n['source']}</div></div>""", unsafe_allow_html=True)
    else: st.info("Haber yok.")

with col_right:
    # 1. ORTAK SİNYALLER (Scrollbar ile)
    st.markdown(f"<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px;color:#1e3a8a; background-color:{current_theme['box_bg']}; padding:5px; border-radius:5px; border:1px solid #1e40af;'>🎯 Ortak Fırsatlar</div>", unsafe_allow_html=True)
    
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
                    if c1.button("★", key=f"c_s_{sym}"): toggle_watchlist(sym); st.rerun()
                    label = f"{sym} | R1:{row1['Skor']} R2:{row2['Skor']} | {row2['Setup']}"
                    if c2.button(label, key=f"c_b_{sym}"): on_scan_result_click(sym); st.rerun()
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
        
        if st.session_state.scan_data is not None and not st.session_state.scan_data.empty:
            for i, row in st.session_state.scan_data.iterrows():
                sym = row["Sembol"]; score = row['Skor']
                c1, c2 = st.columns([0.2, 0.8])
                if c1.button("★" if sym in st.session_state.watchlist else "☆", key=f"r1_s_{sym}_{i}"): toggle_watchlist(sym); st.rerun()
                if c2.button(f"{'🔥' if score>=7 else '✅'} {score}/8 | {sym}", key=f"r1_b_{sym}_{i}"): on_scan_result_click(sym); st.rerun()
                st.markdown(f"<div style='font-size:0.6rem; color:#64748B; margin-top:-8px; padding-left:5px;'>{row['Nedenler']}</div>", unsafe_allow_html=True)
        else: st.info("Sinyal yok.")

    with tab2:
        if st.button(f"🚀 RADAR 2 Tara", type="primary"):
            with st.spinner("Taranıyor..."):
                st.session_state.radar2_data = radar2_scan(ASSET_GROUPS.get(st.session_state.category, []))
        
        if st.session_state.radar2_data is not None and not st.session_state.radar2_data.empty:
            for i, row in st.session_state.radar2_data.iterrows():
                sym = row["Sembol"]
                c1, c2 = st.columns([0.2, 0.8])
                if c1.button("★" if sym in st.session_state.watchlist else "☆", key=f"r2_s_{sym}_{i}"): toggle_watchlist(sym); st.rerun()
                
                btn_label = f"🚀 {sym} | Skor: {row['Skor']} | {row['Trend']} | {row['Setup']}"
                if c2.button(btn_label, key=f"r2_b_{sym}_{i}"): on_scan_result_click(sym); st.rerun()
                st.markdown(f"<div style='font-size:0.6rem; color:#64748B; margin-top:-8px; padding-left:5px;'>Fiyat: {row['Fiyat']} • RS: {row['RS']}% • {row['Etiketler']}</div>", unsafe_allow_html=True)
        else: st.info("Sinyal yok.")

    with tab3:
        wl = st.session_state.watchlist
        if not wl: st.info("Liste boş.")
        else:
            if st.button("⚡ Listeyi Tara (R1)", type="secondary"):
                with st.spinner("..."): st.session_state.scan_data = analyze_market_intelligence(wl)
            for sym in wl:
                c1, c2 = st.columns([0.2, 0.8])
                if c1.button("❌", key=f"wl_d_{sym}"): toggle_watchlist(sym); st.rerun()
                if c2.button(sym, key=f"wl_g_{sym}"): on_scan_result_click(sym); st.rerun()
