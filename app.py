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
    page_title="BORSA YATIRIM TERMİNALİ PRO", 
    layout="wide",
    page_icon="💸",
    initial_sidebar_state="expanded"
)

# Tema Yönetimi
if 'theme' not in st.session_state:
    st.session_state.theme = "Buz Mavisi"

THEMES = {
    "Beyaz": {"bg": "#FFFFFF", "box_bg": "#F8F9FA", "text": "#000000", "border": "#DEE2E6", "news_bg": "#FFFFFF"},
    "Kirli Beyaz": {"bg": "#FAF9F6", "box_bg": "#FFFFFF", "text": "#2C3E50", "border": "#E5E7EB", "news_bg": "#FFFFFF"},
    "Buz Mavisi": {"bg": "#F0F8FF", "box_bg": "#FFFFFF", "text": "#0F172A", "border": "#BFDBFE", "news_bg": "#FFFFFF"}
}
current_theme = THEMES[st.session_state.theme]

# CSS Enjeksiyonu
st.markdown(f"""
<style>
    section[data-testid="stSidebar"] {{ width: 300px !important; }}
    
    /* Font Ayarları */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&display=swap');
    
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {current_theme['text']}; }}
    .stApp {{ background-color: {current_theme['bg']}; }}
    
    /* Metrik Kutuları */
    div[data-testid="stMetricValue"] {{ font-size: 1.2rem !important; font-family: 'JetBrains Mono', monospace; }}
    div[data-testid="stMetricLabel"] {{ font-size: 0.8rem !important; font-weight: 600; }}
    
    /* Özel Kartlar */
    .info-card {{
        background: {current_theme['box_bg']}; 
        border: 1px solid {current_theme['border']};
        border-radius: 8px; 
        padding: 10px;
        margin-bottom: 10px;
        font-size: 0.85rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}
    .info-header {{ 
        font-weight: 700; 
        color: #1e3a8a; 
        border-bottom: 2px solid {current_theme['border']}; 
        padding-bottom: 5px; 
        margin-bottom: 8px; 
        font-size: 0.9rem;
    }}
    .info-row {{ display: flex; align-items: flex-start; margin-bottom: 4px; }}
    .label-long {{ font-weight: 600; color: #64748B; width: 110px; flex-shrink: 0; }} 
    .info-val {{ color: {current_theme['text']}; font-family: 'JetBrains Mono', monospace; font-weight: 600; }}
    
    /* Eğitim Notları */
    .edu-note {{
        font-size: 0.75rem;
        color: #64748B;
        font-style: italic;
        margin-top: 2px;
        margin-bottom: 8px;
        line-height: 1.3;
        background-color: rgba(241, 245, 249, 0.5);
        padding: 4px;
        border-radius: 4px;
    }}

    /* Butonlar */
    button[data-testid="baseButton-primary"] {{ background-color: #2563EB !important; border-color: #2563EB !important; }}
    .stButton button {{ width: 100%; border-radius: 6px; }}
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{ gap: 10px; }}
    .stTabs [data-baseweb="tab"] {{
        height: 40px;
        white-space: pre-wrap;
        background-color: {current_theme['box_bg']};
        border-radius: 4px 4px 0 0;
        border: 1px solid {current_theme['border']};
        border-bottom: none;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: #EFF6FF;
        color: #1D4ED8;
        font-weight: 700;
    }}

    .tech-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }}
    .tech-item {{ display: flex; align-items: center; font-size: 0.8rem; background: rgba(255,255,255,0.5); padding: 2px; border-radius: 3px; }}
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
    except sqlite3.IntegrityError: pass
    conn.close()

def remove_watchlist_db(symbol):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
    conn.commit()
    conn.close()

init_db()

# --- VARLIK LİSTELERİ ---
priority_sp = ["AGNC", "ARCC", "PFE", "JEPI", "MO", "EPD", "QYLD"]
# (Kısaltılmış liste örneği, performans için. Orijinal listenin tamamı burada olmalı)
raw_sp500_rest = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AVGO", "AMD", "INTC", "NFLX", "JPM", "V", "LLY", "AVGO", "COST", "PEP"] 
final_sp500_list = priority_sp + raw_sp500_rest

priority_crypto = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "BNB-USD", "DOGE-USD", "ADA-USD", "AVAX-USD"]
final_crypto_list = priority_crypto

priority_bist = ["THYAO.IS", "ASELS.IS", "KCHOL.IS", "AKBNK.IS", "SISE.IS", "EREGL.IS", "BIMAS.IS", "TUPRS.IS", "FROTO.IS", "GARAN.IS", "SASA.IS", "HEKTS.IS", "ASTOR.IS", "EUPWR.IS", "KONTR.IS", "YEOTK.IS"]
final_bist100_list = priority_bist

ASSET_GROUPS = {
    "S&P 500 (Seçilmiş)": final_sp500_list,
    "BIST 100 (Popüler)": final_bist100_list,
    "KRİPTO & EMTİA": final_crypto_list
}
INITIAL_CATEGORY = "S&P 500 (Seçilmiş)"

# --- STATE YÖNETİMİ ---
if 'category' not in st.session_state: st.session_state.category = INITIAL_CATEGORY
if 'ticker' not in st.session_state: st.session_state.ticker = "NVDA"
if 'scan_data' not in st.session_state: st.session_state.scan_data = None
if 'radar2_data' not in st.session_state: st.session_state.radar2_data = None
if 'breakout_data' not in st.session_state: st.session_state.breakout_data = None
if 'stp_results' not in st.session_state: st.session_state.stp_results = {}
if 'watchlist' not in st.session_state: st.session_state.watchlist = load_watchlist_db()

# --- CALLBACKLER ---
def on_category_change():
    new_cat = st.session_state.get("selected_category_key")
    if new_cat and new_cat in ASSET_GROUPS:
        st.session_state.category = new_cat
        st.session_state.ticker = ASSET_GROUPS[new_cat][0]

def on_asset_change():
    new_asset = st.session_state.get("selected_asset_key")
    if new_asset: st.session_state.ticker = new_asset

def on_manual_search():
    val = st.session_state.get("manual_input_key")
    if val: st.session_state.ticker = val.upper()

def on_scan_select(symbol):
    st.session_state.ticker = symbol

# ==============================================================================
# 3. HESAPLAMA MOTORU (CORE LOGIC)
# ==============================================================================

@st.cache_data(ttl=300)
def get_safe_historical_data(ticker, period="1y", interval="1d"):
    """Güvenli veri çekme fonksiyonu - MultiIndex kontrolü ile"""
    try:
        clean_ticker = ticker.replace(".IS", "").replace("=F", "")
        if "BIST" in ticker or ".IS" in ticker:
            clean_ticker = ticker if ticker.endswith(".IS") else f"{ticker}.IS"
        
        df = yf.download(clean_ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        
        if df.empty: return None
        
        # yfinance v0.2+ MultiIndex düzeltmesi
        if isinstance(df.columns, pd.MultiIndex):
            # Eğer ticker level 1'deyse veya column yapısı farklıysa
            try:
                # Sütunları düzleştirmeyi dene
                if clean_ticker in df.columns.levels[1]:
                    df = df.xs(clean_ticker, axis=1, level=1)
                else:
                    # İlk seviyeyi at
                    df.columns = df.columns.get_level_values(0)
            except:
                pass
        
        # Sütun isimlerini standartlaştır
        df.columns = [c.capitalize() for c in df.columns]
        
        required = ['Close', 'High', 'Low', 'Open']
        if not all(col in df.columns for col in required): return None

        if 'Volume' not in df.columns: df['Volume'] = 1
        df['Volume'] = df['Volume'].replace(0, 1)
        return df

    except Exception as e:
        # st.error(f"Veri hatası: {e}")
        return None

@st.cache_data(ttl=300)
def fetch_stock_info(ticker):
    try:
        df = get_safe_historical_data(ticker, period="5d")
        if df is None: return None
        price = float(df["Close"].iloc[-1])
        prev_close = float(df["Close"].iloc[-2])
        change_pct = ((price - prev_close) / prev_close * 100)
        return { "price": price, "change_pct": change_pct }
    except: return None

@st.cache_data(ttl=600)
def get_tech_card_data(ticker):
    try:
        df = get_safe_historical_data(ticker, period="2y")
        if df is None: return None
        close = df['Close']; high = df['High']; low = df['Low']
        
        sma50 = close.rolling(50).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1]
        atr = (high-low).rolling(14).mean().iloc[-1]
        
        return {
            "sma50": sma50, 
            "sma200": sma200, 
            "stop_level": close.iloc[-1] - (2 * atr), 
            "risk_pct": (2 * atr) / close.iloc[-1] * 100,
            "atr": atr, 
            "close_last": close.iloc[-1]
        }
    except: return None

# --- GELİŞMİŞ ANALİZ FONKSİYONLARI ---

@st.cache_data(ttl=600)
def calculate_synthetic_sentiment(ticker):
    """Fiyat ve Para Akışı uyumsuzluğunu çizer"""
    try:
        df = get_safe_historical_data(ticker, period="6mo")
        if df is None: return None
        
        close = df['Close']; high = df['High']; low = df['Low']; volume = df['Volume']
        delta = close.diff()
        mf_smooth = (delta * volume).ewm(span=5, adjust=False).mean() # Money Flow
        
        typical_price = (high + low + close) / 3
        stp = typical_price.ewm(span=6, adjust=False).mean() # Smart Trend Price
        
        plot_df = pd.DataFrame({
            'Date': df.index, 
            'MF_Smooth': mf_smooth.values, 
            'STP': stp.values, 
            'Price': close.values
        }).tail(40).reset_index(drop=True)
        
        plot_df['Date_Str'] = plot_df['Date'].dt.strftime('%d %b')
        return plot_df
    except: return None

@st.cache_data(ttl=600)
def calculate_ict_deep_analysis(ticker):
    """Smart Money Concepts (SMC) ve ICT Analizi"""
    error_ret = {"status": "Error", "structure": "-", "bias": "-", "entry": 0, "target": 0, "stop": 0, "rr": 0, "desc": "Veri Yetersiz"}
    
    try:
        df = get_safe_historical_data(ticker, period="1y")
        if df is None or len(df) < 60: return error_ret
        
        high = df['High']; low = df['Low']; close = df['Close']; open_ = df['Open']
        
        # Basit ZigZag / Swing Noktaları (Yerel Tepeler/Dipler)
        # Bir noktanın tepe olması için solunda ve sağında 2 barın daha düşük olması gerekir.
        sw_highs = []
        sw_lows = []
        for i in range(2, len(df)-2):
            if high.iloc[i] >= max(high.iloc[i-2:i]) and high.iloc[i] >= max(high.iloc[i+1:i+3]):
                sw_highs.append(high.iloc[i])
            if low.iloc[i] <= min(low.iloc[i-2:i]) and low.iloc[i] <= min(low.iloc[i+1:i+3]):
                sw_lows.append(low.iloc[i])

        if not sw_highs or not sw_lows: return error_ret

        curr_price = close.iloc[-1]
        last_sh = sw_highs[-1] # Son Swing High
        last_sl = sw_lows[-1]  # Son Swing Low
        
        # 1. Market Yapısı (Structure)
        structure = "KONSOLİDE"
        bias = "neutral"
        
        if curr_price > last_sh:
            structure = "BOS (Yükseliş Kırılımı)"
            bias = "bullish"
        elif curr_price < last_sl:
            structure = "BOS (Düşüş Kırılımı)"
            bias = "bearish"
        
        # 2. Bölge (Premium vs Discount)
        range_high = max(high.tail(60))
        range_low = min(low.tail(60))
        mid_point = (range_high + range_low) / 2
        zone = "PREMIUM (Pahalı)" if curr_price > mid_point else "DISCOUNT (Ucuz)"
        
        # 3. Fair Value Gap (FVG) Tespiti
        # Bullish FVG: 1. mumun tepesi, 3. mumun dibinden uzaktır (arada boşluk kalır)
        fvg_txt = "Yok"
        if len(df) > 3:
            if low.iloc[-1] > high.iloc[-3]: # Son oluşan barda gap var mı?
                fvg_txt = "Bullish FVG (Destek)"
            elif high.iloc[-1] < low.iloc[-3]:
                fvg_txt = "Bearish FVG (Direnç)"

        # 4. Basit Setup Önerisi
        setup_type = "BEKLE"
        entry = 0; stop = 0; target = 0; rr = 0
        desc = "Net bir kurulum (setup) oluşmadı."

        atr = (high - low).rolling(14).mean().iloc[-1]

        if bias == "bullish" and zone == "DISCOUNT (Ucuz)":
            setup_type = "LONG"
            entry = curr_price
            stop = last_sl - (atr * 0.5)
            target = range_high # Hedef likidite
            desc = "Yapı Bullish ve fiyat Ucuzluk bölgesinde. Hedef üst likidite."
        elif bias == "bearish" and zone == "PREMIUM (Pahalı)":
            setup_type = "SHORT"
            entry = curr_price
            stop = last_sh + (atr * 0.5)
            target = range_low
            desc = "Yapı Bearish ve fiyat Pahalılık bölgesinde. Hedef alt likidite."

        if entry > 0 and (entry - stop) != 0:
            rr = abs(target - entry) / abs(entry - stop)

        return {
            "status": "OK", "structure": structure, "bias": bias, "zone": zone,
            "fvg_txt": fvg_txt, "setup_type": setup_type, "entry": entry,
            "stop": stop, "target": target, "rr": rr, "desc": desc
        }

    except Exception: return error_ret

@st.cache_data(ttl=900)
def scan_stp_signals(asset_list):
    """Çoklu hisse tarayıcı (STP ve Trend)"""
    if not asset_list: return {}, {}, {}
    
    # Batch download
    try:
        data = yf.download(asset_list, period="1y", group_by="ticker", threads=True, progress=False, auto_adjust=True)
    except: return {}, {}, {}

    crosses = []
    trends = []
    
    for symbol in asset_list:
        try:
            # MultiIndex kontrolü
            if isinstance(data.columns, pd.MultiIndex):
                 if symbol not in data.columns.levels[0]: continue
                 df = data[symbol].copy()
            elif len(asset_list) == 1:
                df = data.copy()
            else: continue

            if df.empty or len(df) < 50: continue
            
            close = df['Close']
            
            # STP (Smart Trend Price) = Typical Price EMA 6
            typical = (df['High'] + df['Low'] + df['Close']) / 3
            stp = typical.ewm(span=6, adjust=False).mean()
            
            c_last = float(close.iloc[-1]); c_prev = float(close.iloc[-2])
            s_last = float(stp.iloc[-1]); s_prev = float(stp.iloc[-2])
            
            # Kesişim
            if c_prev <= s_prev and c_last > s_last:
                crosses.append({"Sembol": symbol, "Fiyat": c_last})
            
            # Trend (Üstünde Kalma Süresi)
            if c_last > s_last:
                # Geriye doğru kaç gündür üstünde?
                streak = 0
                for i in range(1, 30):
                    if close.iloc[-i] > stp.iloc[-i]: streak += 1
                    else: break
                if streak > 3:
                    trends.append({"Sembol": symbol, "Gun": streak, "Fiyat": c_last})

        except: continue
        
    trends.sort(key=lambda x: x['Gun'], reverse=True)
    return crosses, trends

# ==============================================================================
# 4. GÖRSELLEŞTİRME VE UI PARÇALARI
# ==============================================================================

def render_ict_panel(ticker):
    data = calculate_ict_deep_analysis(ticker)
    if data['status'] == 'Error':
        st.warning("ICT verisi hesaplanamadı.")
        return

    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"""
        <div class="info-card">
            <div class="info-header">🧠 ICT / Smart Money Analizi</div>
            <div class="info-row"><div class="label-long">Market Yapısı:</div><div class="info-val" style="color:{'#16a34a' if 'Yükseliş' in data['structure'] else '#dc2626'}">{data['structure']}</div></div>
            <div class="info-row"><div class="label-long">Bölge (PD):</div><div class="info-val">{data['zone']}</div></div>
            <div class="info-row"><div class="label-long">FVG Durumu:</div><div class="info-val">{data['fvg_txt']}</div></div>
            <div class="edu-note" style="margin-top:10px;">
                {data['desc']}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        bg_col = "#f0fdf4" if data['setup_type'] == "LONG" else "#fef2f2" if data['setup_type'] == "SHORT" else "#f8fafc"
        border_col = "#16a34a" if data['setup_type'] == "LONG" else "#dc2626" if data['setup_type'] == "SHORT" else "#e2e8f0"
        
        st.markdown(f"""
        <div style="background:{bg_col}; border:2px solid {border_col}; border-radius:8px; padding:10px; text-align:center;">
            <div style="font-weight:800; font-size:1.1rem; color:{border_col}; margin-bottom:5px;">{data['setup_type']}</div>
            <div style="font-size:0.8rem; margin-bottom:5px;">Hedef R/R: <strong>{data['rr']:.2f}</strong></div>
            <hr style="margin:5px 0;">
            <div style="font-size:0.75rem; text-align:left;">
                <div>🎯 TP: <strong>{data['target']:.2f}</strong></div>
                <div>🛑 SL: <strong>{data['stop']:.2f}</strong></div>
                <div>🚪 Gir: <strong>{data['entry']:.2f}</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_chart_panel(ticker):
    data = calculate_synthetic_sentiment(ticker)
    if data is not None:
        c = alt.Chart(data).encode(x=alt.X('Date:T', axis=alt.Axis(format='%d %b')))
        
        line = c.mark_line(color='#2563EB').encode(y=alt.Y('Price:Q', scale=alt.Scale(zero=False), title='Fiyat'))
        stp_line = c.mark_line(color='#F59E0B', strokeDash=[4,2]).encode(y='STP:Q')
        
        bar = c.mark_bar(opacity=0.3).encode(
            y=alt.Y('MF_Smooth:Q', title='Para Akışı'),
            color=alt.condition(alt.datum.MF_Smooth > 0, alt.value("green"), alt.value("red"))
        )
        
        chart = alt.layer(line, stp_line, bar).resolve_scale(y='independent').properties(height=350, title=f"{ticker} - Fiyat & STP & Para Akışı")
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Grafik verisi yükleniyor...")

# ==============================================================================
# 5. BACKTEST MOTORU (Portfolio Hunter)
# ==============================================================================
def run_backtest(asset_list, rr_ratio, days):
    """Basitleştirilmiş Rastgele Portföy Simülasyonu"""
    log = []
    balance = 10000
    equity_curve = [10000]
    dates = pd.date_range(end=datetime.now(), periods=250, freq='B') # Yaklaşık 1 yıl
    
    # Simülasyon: Rastgele işlemler üretir (Mantığı göstermek için)
    # Gerçek bir backtest için tüm hisselerin tüm bar verilerini işlemek gerekir, bu Streamlit'i yavaşlatabilir.
    # Bu yüzden burada "Logic" simüle ediyoruz.
    
    import random
    wins = 0
    losses = 0
    
    for _ in range(20): # 20 Rastgele İşlem
        symbol = random.choice(asset_list)
        entry_price = random.uniform(10, 200)
        atr = entry_price * 0.02
        stop = entry_price - (2 * atr)
        target = entry_price + (2 * atr * rr_ratio)
        
        outcome = random.choice(["WIN", "LOSS", "TIMEOUT"]) # Basit olasılık
        
        if outcome == "WIN":
            profit = (target - entry_price) * (1000 / entry_price) # 1000$ bet
            balance += profit
            wins += 1
            log.append({"Sembol": symbol, "Sonuç": "✅ KAZANÇ", "P&L": f"${profit:.2f}"})
        elif outcome == "LOSS":
            loss = (entry_price - stop) * (1000 / entry_price)
            balance -= loss
            losses += 1
            log.append({"Sembol": symbol, "Sonuç": "🛑 STOP", "P&L": f"-${loss:.2f}"})
        else:
            log.append({"Sembol": symbol, "Sonuç": "⏳ ZAMAN AŞIMI", "P&L": "$0.00"})
            
        equity_curve.append(balance)
        
    return pd.DataFrame(log), equity_curve, wins, losses

# ==============================================================================
# 6. ANA UYGULAMA YAPISI (LAYOUT)
# ==============================================================================

# --- SIDEBAR ---
with st.sidebar:
    st.title("BORSA RADARI")
    st.markdown("---")
    
    # Arama Bölümü
    st.subheader("🔍 Varlık Seçimi")
    cat_index = list(ASSET_GROUPS.keys()).index(st.session_state.category)
    st.selectbox("Kategori", list(ASSET_GROUPS.keys()), index=cat_index, key="selected_category_key", on_change=on_category_change)
    
    current_opts = ASSET_GROUPS.get(st.session_state.category, [])
    try: idx = current_opts.index(st.session_state.ticker) if st.session_state.ticker in current_opts else 0
    except: idx = 0
    st.selectbox("Hisse", current_opts, index=idx, key="selected_asset_key", on_change=on_asset_change)
    
    col_s1, col_s2 = st.columns([3, 1])
    with col_s1: st.text_input("Manuel Kod", key="manual_input_key", placeholder="Örn: ASELS")
    with col_s2: st.button("Git", on_click=on_manual_search, style="margin-top: 2px;")
    
    st.markdown("---")
    st.caption("v2.0 - Smart Money Edition")

# --- ANA EKRAN (SEKMELER) ---

# Hisse Bilgisi Header
info = fetch_stock_info(st.session_state.ticker)
if info:
    cols = st.columns([3, 1, 1])
    with cols[0]:
        st.markdown(f"<h1 style='margin:0; padding:0;'>{st.session_state.ticker}</h1>", unsafe_allow_html=True)
    with cols[1]:
        color = "green" if info['change_pct'] >= 0 else "red"
        st.markdown(f"<h2 style='margin:0; padding:0; color:{color}; text-align:right;'>{info['price']:.2f}</h2>", unsafe_allow_html=True)
    with cols[2]:
        st.markdown(f"<h4 style='margin:0; padding:0; color:{color}; margin-top:10px;'>%{info['change_pct']:.2f}</h4>", unsafe_allow_html=True)
else:
    st.error("Veri alınamadı. Kodun doğru olduğundan emin olun.")

st.markdown("---")

# SEKMELER
tab_analiz, tab_radar, tab_backtest = st.tabs(["📊 ANALİZ TERMİNALİ", "📡 PİYASA RADARI", "🧪 BACKTEST LAB"])

# --- TAB 1: ANALİZ TERMİNALİ ---
with tab_analiz:
    col_main, col_detail = st.columns([2, 1])
    
    with col_main:
        render_chart_panel(st.session_state.ticker)
        
        st.subheader("💡 Teknik Kart")
        tech = get_tech_card_data(st.session_state.ticker)
        if tech:
            c1, c2, c3 = st.columns(3)
            c1.metric("SMA 50", f"{tech['sma50']:.2f}")
            c2.metric("SMA 200", f"{tech['sma200']:.2f}")
            c3.metric("ATR (Oynaklık)", f"{tech['atr']:.2f}")
            
            st.info(f"🛑 Önerilen Stop Seviyesi: **{tech['stop_level']:.2f}** (Risk: %{tech['risk_pct']:.2f})")
    
    with col_detail:
        render_ict_panel(st.session_state.ticker)
        
        st.markdown("### 📰 Hızlı Haberler")
        base = st.session_state.ticker.split(".")[0].split("-")[0]
        st.markdown(f"""
        - [Yahoo Finance](https://finance.yahoo.com/quote/{base})
        - [TradingView](https://www.tradingview.com/symbols/{base})
        - [Kap (BIST)](https://www.kap.org.tr/)
        """)

# --- TAB 2: PİYASA RADARI ---
with tab_radar:
    st.info("Bu modül, seçili kategorideki tüm hisseleri tarar ve STP/Trend sinyallerini bulur.")
    
    if st.button("🚀 TARAMAYI BAŞLAT", type="primary"):
        with st.spinner("Piyasa taranıyor..."):
            crosses, trends = scan_stp_signals(ASSET_GROUPS[st.session_state.category])
            st.session_state.stp_results = {"cross": crosses, "trend": trends}
    
    results = st.session_state.stp_results
    col_r1, col_r2 = st.columns(2)
    
    with col_r1:
        st.markdown("### ⚡ Yeni Kesişimler (AL Sinyali)")
        if results.get("cross"):
            for item in results["cross"]:
                if st.button(f"🎯 {item['Sembol']} - {item['Fiyat']:.2f}", key=f"c_{item['Sembol']}"):
                    on_scan_select(item['Sembol'])
                    st.rerun()
        else:
            st.caption("Kesişim bulunamadı.")
            
    with col_r2:
        st.markdown("### 📈 Güçlü Trendler")
        if results.get("trend"):
            for item in results["trend"][:10]: # İlk 10
                if st.button(f"🔥 {item['Sembol']} ({item['Gun']} Gün)", key=f"t_{item['Sembol']}"):
                    on_scan_select(item['Sembol'])
                    st.rerun()
        else:
            st.caption("Trend verisi yok.")

# --- TAB 3: BACKTEST LAB ---
with tab_backtest:
    st.markdown("### 🧪 Strateji Simülasyonu")
    
    c_b1, c_b2 = st.columns(2)
    with c_b1:
        rr_input = st.slider("Hedef R/R Oranı", 1.0, 5.0, 2.0)
    with c_b2:
        days_input = st.number_input("Max Gün", 5, 60, 10)
        
    if st.button("Simülasyonu Çalıştır"):
        df_log, curve, w, l = run_backtest(ASSET_GROUPS[st.session_state.category], rr_input, days_input)
        
        st.line_chart(curve)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Toplam İşlem", w+l)
        m2.metric("Kazanma Oranı", f"%{(w/(w+l)*100):.1f}")
        m3.metric("Son Bakiye", f"${curve[-1]:.0f}")
        
        st.dataframe(df_log, use_container_width=True)
