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
    page_title="Patronun Terminali v5.5 (Log Panel)",
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

    .ict-bar-container {{
        width: 100%; height: 6px; background-color: #e2e8f0; border-radius: 3px; overflow: hidden; margin: 4px 0; display:flex;
    }}
    .ict-bar-fill {{ height: 100%; transition: width 0.5s ease; }}

    /* LOG PANELİ STİLİ */
    .log-container {
        max-height: 300px;
        overflow-y: auto;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        background-color: #ffffff;
    }
    .log-item {
        padding: 8px;
        border-bottom: 1px solid #f1f5f9;
        font-size: 0.8rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .log-item:last-child { border-bottom: none; }
    .log-time { font-family: 'JetBrains Mono'; color: #64748B; font-size: 0.7rem; margin-right: 10px; }
    .log-symbol { font-weight: 700; color: #1e40af; width: 60px; }
    .log-msg { flex-grow: 1; color: #334155; }
    
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

# --- HAFIZA (LOG SİSTEMİ İÇİN SHARED MEMORY) ---
class OpportunityStore:
    def __init__(self):
        self.findings = [] # Bulunan fırsatları tutacak liste
        self.lock = threading.Lock() # Çakışmayı önlemek için kilit

    def add_finding(self, symbol, message, price):
        with self.lock:
            # Timestamp ekle
            time_str = datetime.now().strftime("%H:%M")
            # En başa ekle (En yeni en üstte)
            self.findings.insert(0, {
                "time": time_str,
                "symbol": symbol,
                "msg": message,
                "price": price
            })
            # Hafıza şişmesin diye son 50 kayıt kalsın
            if len(self.findings) > 50:
                self.findings.pop()
    
    def get_findings(self):
        with self.lock:
            return list(self.findings)

# Singleton olarak Store'u oluştur (Sayfa yenilense de hafıza silinmez)
@st.cache_resource
def get_store():
    return OpportunityStore()

# --- VARLIK LİSTELERİ ---
priority_sp = ["AGNC", "ARCC", "PFE", "JEPI", "MO", "EPD"]
raw_sp500_rest = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AMD", "INTC", "QCOM", "JPM", "BAC", "WFC", "GS", "MS", "BLK", "V", "MA", "PYPL", "LLY", "UNH", "JNJ", "XOM", "CVX", "KO", "PEP", "MCD", "SBUX", "DIS", "NFLX"] # Kısaltıldı
final_sp500_list = priority_sp + raw_sp500_rest

priority_crypto = ["GC=F", "SI=F", "BTC-USD", "ETH-USD"]
other_crypto = ["BNB-USD", "SOL-USD", "XRP-USD", "ADA-USD", "DOGE-USD", "AVAX-USD"]
final_crypto_list = priority_crypto + other_crypto

raw_nasdaq = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "GOOGL", "COST", "NFLX", "AMD"]

priority_bist = ["AKBNK.IS", "BIMAS.IS", "DOHOL.IS", "FENER.IS", "KCHOL.IS", "SISE.IS", "TCELL.IS", "THYAO.IS", "TTKOM.IS", "VAKBN.IS"]
raw_bist100_rest = ["ASELS.IS", "ASTOR.IS", "EREGL.IS", "FROTO.IS", "GARAN.IS", "HEKTS.IS", "ISCTR.IS", "KOZAL.IS", "PETKM.IS", "PGSUS.IS", "SAHOL.IS", "SASA.IS", "TUPRS.IS", "YKBNK.IS"]
final_bist100_list = priority_bist + raw_bist100_rest

ASSET_GROUPS = {
    "S&P 500": final_sp500_list,
    "NASDAQ": raw_nasdaq,
    "BIST 100": final_bist100_list,
    "EMTİA & KRİPTO": final_crypto_list
}

INITIAL_CATEGORY = "S&P 500"

# --- STATE ---
if 'category' not in st.session_state: st.session_state.category = INITIAL_CATEGORY
if 'ticker' not in st.session_state: st.session_state.ticker = "AAPL"
if 'scan_data' not in st.session_state: st.session_state.scan_data = None
if 'radar2_data' not in st.session_state: st.session_state.radar2_data = None
if 'watchlist' not in st.session_state: st.session_state.watchlist = load_watchlist_db()

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
            curr_c = float(close.iloc[-1]); curr_vol = float(volume.iloc[-1])
            avg_vol = float(volume.rolling(5).mean().iloc[-1]) if len(volume) > 5 else 1.0
            
            score = 0; reasons = []
            if bb_width.iloc[-1] <= bb_width.tail(60).min() * 1.1: score += 1; reasons.append("🚀 Squeeze")
            if ((ema5.iloc[-1] > ema20.iloc[-1]) and (ema5.iloc[-2] <= ema20.iloc[-2])): score += 1; reasons.append("⚡ Trend")
            if hist.iloc[-1] > hist.iloc[-2]: score += 1; reasons.append("🟢 MACD")
            if curr_vol > avg_vol * 1.2: score += 1; reasons.append("🔊 Hacim")
            if curr_c >= high.tail(20).max() * 0.98: score += 1; reasons.append("🔨 Breakout")
            
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
            
            close = df['Close']; high = df['High']; volume = df['Volume']
            curr_c = float(close.iloc[-1])
            sma50 = close.rolling(50).mean(); sma200 = close.rolling(200).mean()
            trend = "Boğa" if curr_c > sma50.iloc[-1] > sma200.iloc[-1] else "Ayı" if curr_c < sma200.iloc[-1] else "Yatay"
            
            score = 0; setup = "-"; tags = []
            if trend == "Boğa": score += 1
            if volume.iloc[-1] > volume.rolling(20).mean().iloc[-1] * 1.3: score += 1; tags.append("Hacim+")
            
            if score > 0:
                return {"Sembol": symbol, "Fiyat": round(curr_c, 2), "Trend": trend, "Setup": setup, "Skor": score, "RS": 0, "Etiketler": " | ".join(tags)}
            return None
        except: return None

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(process_radar2, asset_list))
    results = [r for r in results if r is not None]
    return pd.DataFrame(results).sort_values(by="Skor", ascending=False).head(50) if results else pd.DataFrame()

@st.cache_data(ttl=600)
def calculate_sentiment_score(ticker):
    try:
        df = yf.download(ticker, period="6mo", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']
        rsi = 100 - (100 / (1 + (close.diff().clip(lower=0).rolling(14).mean() / close.diff().clip(upper=0).abs().rolling(14).mean())))
        score_mom = 10 if rsi.iloc[-1] > 50 else 0
        return {
            "total": 50 + score_mom, "bar": "[|||||.....]", 
            "mom": f"{score_mom}", "vol": "Nötr", "tr": "Nötr", "vola": "Nötr", "str": "Nötr",
            "raw_rsi": rsi.iloc[-1], "raw_macd": 0, "raw_obv": 0, "raw_atr": 0
        }
    except: return None

@st.cache_data(ttl=600)
def get_deep_xray_data(ticker):
    return {"mom_rsi": "✅", "mom_macd": "✅", "vol_obv": "❌", "tr_ema": "✅", "tr_adx": "❌", "vola_bb": "✅", "str_bos": "✅"}

@st.cache_data(ttl=600)
def calculate_ict_concepts(ticker):
    try:
        df = yf.download(ticker, period="1y", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']; high = df['High']; low = df['Low']
        if len(df) < 60: return {"summary": "Veri Yetersiz"}
        curr_price = float(close.iloc[-1])
        
        # 1. Swing High/Low
        sw_highs = []; sw_lows = []
        for i in range(2, len(df)-2):
            if (high.iloc[i] > high.iloc[i-1] and high.iloc[i] > high.iloc[i-2] and high.iloc[i] > high.iloc[i+1] and high.iloc[i] > high.iloc[i+2]):
                sw_highs.append((df.index[i], float(high.iloc[i])))
            if (low.iloc[i] < low.iloc[i-1] and low.iloc[i] < low.iloc[i-2] and low.iloc[i] < low.iloc[i+1] and low.iloc[i] < low.iloc[i+2]):
                sw_lows.append((df.index[i], float(low.iloc[i])))
        
        if not sw_highs or not sw_lows: return {"summary": "Swing Yok"}
        last_sh = sw_highs[-1][1]; last_sl = sw_lows[-1][1]
        
        # 2. Market Structure
        structure = "BOS (Bullish)" if curr_price > last_sh else "BOS (Bearish)" if curr_price < last_sl else "Internal Range"
        bias_color = "green" if "Bullish" in structure else "red" if "Bearish" in structure else "blue"
        
        # 3. Premium/Discount
        range_high = last_sh; range_low = last_sl
        range_size = range_high - range_low if range_high != range_low else 1
        pos_pct = ((curr_price - range_low) / range_size) * 100
        is_discount = pos_pct < 50
        is_ote = (62 < pos_pct < 79) or (21 < pos_pct < 38)
        pos_label = "Discount (Ucuz)" if is_discount else "Premium (Pahalı)"
        
        # 4. FVG & Golden
        golden_txt = "İzlemede"
        is_golden = False
        fvg_color = "gray"
        active_fvg = "Yok"
        
        # Basit Golden Setup Mantığı
        if is_discount and bias_color == "green":
            golden_txt = "🔥 LONG FIRSATI (Trend + Ucuz)"
            is_golden = True
            fvg_color = "green"
        elif not is_discount and bias_color == "red":
            golden_txt = "❄️ SHORT FIRSATI (Trend + Pahalı)"
            is_golden = True
            fvg_color = "red"

        return {
            "structure": structure, "bias_color": bias_color, "range_pos_pct": pos_pct,
            "pos_label": pos_label, "fvg": active_fvg, "fvg_color": fvg_color,
            "liquidity": "Hedef Bekleniyor", "golden_text": golden_txt, "is_golden": is_golden,
            "ote_level": is_ote
        }
    except Exception as e: return {"summary": "Hata"}

@st.cache_data(ttl=600)
def get_tech_card_data(ticker):
    try:
        df = yf.download(ticker, period="2y", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']
        return {"sma50": close.rolling(50).mean().iloc[-1], "ema144": close.ewm(span=144).mean().iloc[-1]}
    except: return None

# --- AJAN: ARKA PLAN TARAMA SERVİSİ (LOG TUTUCU) ---
def scanner_job():
    """Arka planda çalışır, bulduklarını hafızaya (Store) yazar."""
    store = get_store() # Ortak hafızayı çağır
    print("--- 🕵️ AJAN BAŞLATILDI: Sonuçlar Panele Yazılacak ---")
    
    while True:
        try:
            full_scan_list = final_bist100_list + final_sp500_list
            # Test için kısa liste: full_scan_list = full_scan_list[:10] 
            
            for symbol in full_scan_list:
                try:
                    analysis = calculate_ict_concepts(symbol)
                    
                    if analysis and analysis.get("is_golden", False):
                        price_info = fetch_stock_info(symbol)
                        price_val = f"{price_info['price']:.2f}" if price_info else "?"
                        
                        # BULUNAN FIRSATI HAFIZAYA YAZ
                        store.add_finding(
                            symbol=symbol,
                            message=f"{analysis['golden_text']} | Konum: %{analysis['range_pos_pct']:.1f}",
                            price=price_val
                        )
                        print(f"FIRSAT EKLENDİ: {symbol}")
                except: pass
                time.sleep(0.5) # Ban yememek için bekleme
                
        except Exception as e:
            print(f"Tarama hatası: {e}")
        
        time.sleep(3600) # 1 SAAT BEKLE

# Thread Wrapper
@st.cache_resource
def start_background_thread():
    t = threading.Thread(target=scanner_job, daemon=True)
    t.start()
    return t

# --- RENDER FONKSİYONLARI ---
def render_opportunity_log():
    store = get_store()
    findings = store.get_findings()
    
    st.markdown(f"""
    <div style='margin-top:20px; border:1px solid #bfdbfe; border-radius:8px; overflow:hidden;'>
        <div style='background:#eff6ff; padding:10px; border-bottom:1px solid #bfdbfe; display:flex; justify-content:space-between; align-items:center;'>
            <div style='font-weight:700; color:#1e3a8a;'>🕵️ Canlı Fırsat Günlüğü (Arka Plan Ajanı)</div>
            <div style='font-size:0.7rem; color:#64748B;'>Son 50 Kayıt • Otomatik Güncellenir</div>
        </div>
        <div class="log-container">
    """, unsafe_allow_html=True)
    
    if not findings:
        st.markdown("<div style='padding:20px; text-align:center; color:#94a3b8; font-size:0.8rem;'>Henüz kayıtlı bir fırsat yok veya ajan yeni başlatıldı.</div>", unsafe_allow_html=True)
    else:
        for f in findings:
            st.markdown(f"""
            <div class="log-item">
                <div style="display:flex; align-items:center;">
                    <span class="log-time">{f['time']}</span>
                    <span class="log-symbol">{f['symbol']}</span>
                    <span class="log-msg">{f['msg']}</span>
                </div>
                <div style="font-family:'JetBrains Mono'; font-weight:700; color:#0f172a;">{f['price']}</div>
            </div>
            """, unsafe_allow_html=True)
            
    st.markdown("</div></div>", unsafe_allow_html=True)

def render_tradingview_widget(ticker, height=650):
    tv_symbol = ticker.replace('.IS', '').strip() if ".IS" in ticker else f"FX_IDC:{ticker.replace('=X', '')}" if "=X" in ticker else ticker
    html = f"""
    <div class="tradingview-widget-container">
        <div id="tradingview_chart"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
        new TradingView.widget({{
            "width": "100%", "height": {height}, "symbol": "{tv_symbol}", "interval": "D",
            "timezone": "Etc/UTC", "theme": "light", "style": "1", "locale": "tr",
            "toolbar_bg": "#f1f3f6", "enable_publishing": false, "allow_symbol_change": true,
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
        return {
            'price': info.get('currentPrice') or info.get('regularMarketPrice'),
            'change_pct': ((info.get('currentPrice') or info.get('regularMarketPrice')) - info.get('previousClose')) / info.get('previousClose') * 100 if info.get('previousClose') else 0,
            'volume': info.get('volume', 0),
            'sector': info.get('sector', '-'),
            'target': info.get('targetMeanPrice', '-')
        }
    except: return None

# --- ARAYÜZ ---
BULL_ICON_B64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAOAAAADhCAMAAADmr0l2AAAAb1BMVEX///8AAAD8/PzNzc3y8vL39/f09PTw8PDs7Ozp6eny8vLz8/Pr6+vm5ubt7e3j4+Ph4eHf39/c3NzV1dXS0tLKyso/Pz9ERERNTU1iYmJSUlJxcXF9fX1lZWV6enp2dnZsbGxra2uDg4N0dHR/g07fAAAE70lEQVR4nO2d27qrIAyF131wRPT+z3p2tX28dE5sC4i9x3+tC0L4SAgJ3Y2Hw+FwOBwOh8PhcDgcDofD4XA4HA6Hw+H8B/DDT05v9eU/AAAAAElFTkSuQmCC"

st.markdown(f"""
<div class="header-container" style="display:flex; align-items:center;">
    <img src="{BULL_ICON_B64}" class="header-logo">
    <div>
        <div style="font-size:1.5rem; font-weight:700; color:#1e3a8a;">Patronun Terminali v5.5</div>
        <div style="font-size:0.8rem; color:#64748B;">Log Panel Edition (No Telegram)</div>
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
    st.selectbox("Varlık Listesi", opts, index=asset_idx, key="selected_asset_key", on_change=on_asset_change, label_visibility="collapsed", format_func=lambda x: x.replace(".IS", ""))
with col_search_in:
    st.text_input("Manuel", placeholder="Kod", key="manual_input_key", label_visibility="collapsed")
with col_search_btn:
    st.button("Ara", on_click=on_manual_button_click)

st.markdown("<hr style='margin-top:0.5rem; margin-bottom:0.5rem;'>", unsafe_allow_html=True)

# PROMPT
if 'generate_prompt' not in st.session_state: st.session_state.generate_prompt = False
if st.session_state.generate_prompt:
    t = st.session_state.ticker
    ict_data = calculate_ict_concepts(t) or {}
    sent_data = calculate_sentiment_score(t) or {}
    tech_data = get_tech_card_data(t) or {}
    prompt = f"Analiz: {t}. ICT Yapı: {ict_data.get('structure')}. Sentiment: {sent_data.get('total')}."
    with st.sidebar:
        st.code(prompt, language="text")
        st.success("Kopyalandı!")
    st.session_state.generate_prompt = False

# AJAN KONTROL PANELİ (SIDEBAR)
with st.sidebar:
    st.divider()
    st.markdown("### 🕵️ Arka Plan Ajanı")
    run_agent = st.toggle("Otomatik Tarama (1 Saat)", value=False)
    if run_agent:
        start_background_thread()
        st.caption("✅ Ajan aktif. Sonuçlar ana ekrandaki panele düşecek.")
        st.caption("ℹ️ Listeyi güncellemek için sayfayı yenileyin veya bir butona basın.")
    else:
        st.caption("⛔ Ajan pasif.")

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
    render_tradingview_widget(st.session_state.ticker, height=600)
    
    # --- YENİ LOG PANELİ BURAYA EKLENDİ ---
    render_opportunity_log()
    
    st.markdown(f"<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:20px;'>📡 {st.session_state.ticker} Haberleri</div>", unsafe_allow_html=True)

with col_right:
    sent_data = calculate_sentiment_score(st.session_state.ticker)
    
    # Basitleştirilmiş Sentiment Render
    if sent_data:
        st.markdown(f"""<div class="info-card"><div class="info-header">🎭 Sentiment</div><div class="info-val">Skor: {sent_data['total']}/100</div></div>""", unsafe_allow_html=True)
    
    ict_data = calculate_ict_concepts(st.session_state.ticker)
    
    # Basitleştirilmiş ICT Render
    if ict_data:
        s_color = "#166534" if ict_data['bias_color'] == "green" else "#991b1b"
        st.markdown(f"""
        <div class="info-card">
            <div class="info-header">🧠 ICT: {st.session_state.ticker}</div>
            <div style="font-weight:700; color:{s_color};">{ict_data['structure']}</div>
            <div style="margin-top:5px; font-size:0.7rem;">{ict_data['golden_text']}</div>
        </div>
        """, unsafe_allow_html=True)

    # Ortak Fırsatlar
    st.markdown(f"<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:10px; color:#1e3a8a;'>🎯 Ortak Fırsatlar</div>", unsafe_allow_html=True)
    with st.container(height=250):
        df1 = st.session_state.scan_data
        df2 = st.session_state.radar2_data
        if df1 is not None and df2 is not None and not df1.empty and not df2.empty:
            symbols = set(df1["Sembol"]).intersection(set(df2["Sembol"]))
            if symbols:
                for sym in symbols:
                    st.button(f"🥇 {sym}", key=f"common_{sym}", on_click=on_scan_result_click, args=(sym,))
            else: st.info("Kesişim yok.")
        else: st.caption("İki radar da çalıştırılmalı.")

    st.markdown("<hr>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["RADAR 1", "RADAR 2"])
    with tab1:
        if st.button(f"⚡ {st.session_state.category} Tara"):
            with st.spinner("..."): st.session_state.scan_data = analyze_market_intelligence(ASSET_GROUPS.get(st.session_state.category, []))
        if st.session_state.scan_data is not None:
             for i, row in st.session_state.scan_data.iterrows():
                 st.button(f"🔥 {row['Skor']} | {row['Sembol']}", key=f"r1_{i}", on_click=on_scan_result_click, args=(row['Sembol'],))
    with tab2:
        if st.button("🚀 RADAR 2 Tara"):
            with st.spinner("..."): st.session_state.radar2_data = radar2_scan(ASSET_GROUPS.get(st.session_state.category, []))
        if st.session_state.radar2_data is not None:
             for i, row in st.session_state.radar2_data.iterrows():
                 st.button(f"🚀 {row['Skor']} | {row['Sembol']}", key=f"r2_{i}", on_click=on_scan_result_click, args=(row['Sembol'],))
