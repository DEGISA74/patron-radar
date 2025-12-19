import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import urllib.parse
from textblob import TextBlob
from datetime import datetime, timedelta
import numpy as np
import sqlite3
import concurrent.futures
import re
import altair as alt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==============================================================================
# 1. AYARLAR VE STİL
# ==============================================================================
st.set_page_config(
    page_title="BORSA YATIRIM TERMİNALİ PRO", 
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
    section[data-testid="stSidebar"] {{ width: 300px !important; }}
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
    
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {current_theme['text']}; }}
    .stApp {{ background-color: {current_theme['bg']}; }}
    
    .info-card {{
        background: {current_theme['box_bg']}; border: 1px solid {current_theme['border']};
        border-radius: 8px; padding: 10px; margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}
    .info-header {{ font-weight: 800; color: #1e3a8a; border-bottom: 2px solid {current_theme['border']}; padding-bottom: 5px; margin-bottom: 8px; font-size: 0.9rem; }}
    .info-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; border-bottom: 1px dashed #e2e8f0; padding-bottom: 2px; }}
    .label-long {{ font-weight: 600; color: #64748B; font-size: 0.8rem; }} 
    .info-val {{ color: {current_theme['text']}; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; font-weight: 700; }}
    .edu-note {{ font-size: 0.75rem; color: #64748B; font-style: italic; margin-top: 2px; margin-bottom: 8px; line-height: 1.3; }}
    
    /* Stat Box */
    .stat-box-small {{ text-align: center; padding: 5px; background: white; border-radius: 6px; border: 1px solid #cbd5e1; }}
    .stat-value-small {{ font-size: 1.2rem; font-weight: 800; font-family: 'JetBrains Mono'; }}
    .delta-pos {{ color: #16A34A; }} .delta-neg {{ color: #DC2626; }}
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

init_db()

# --- VARLIK LİSTELERİ ---
priority_sp = ["AGNC", "ARCC", "PFE", "JEPI", "MO", "EPD", "NVDA", "TSLA", "AAPL", "MSFT", "AMD", "AMZN", "GOOGL", "META"]
final_sp500_list = sorted(list(set(priority_sp)))

priority_crypto = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "DOGE-USD", "AVAX-USD"]
final_crypto_list = sorted(list(set(priority_crypto)))

priority_bist = ["THYAO.IS", "ASELS.IS", "GARAN.IS", "AKBNK.IS", "EREGL.IS", "SISE.IS", "BIMAS.IS", "TUPRS.IS", "KCHOL.IS", "SAHOL.IS", "HEKTS.IS", "SASA.IS", "KONTR.IS", "MIATK.IS", "ASTOR.IS"]
final_bist100_list = sorted(list(set(priority_bist)))

ASSET_GROUPS = {
    "S&P 500 (VIP)": final_sp500_list,
    "BIST 100 (VIP)": final_bist100_list,
    "KRİPTO & EMTİA": final_crypto_list
}
INITIAL_CATEGORY = "S&P 500 (VIP)"

# --- STATE YÖNETİMİ ---
if 'category' not in st.session_state: st.session_state.category = INITIAL_CATEGORY
if 'ticker' not in st.session_state: st.session_state.ticker = "NVDA"
if 'agent3_data' not in st.session_state: st.session_state.agent3_data = None
if 'filters' not in st.session_state: st.session_state.filters = {"trend_bull": False, "discount_only": False, "high_score": False}

# ==============================================================================
# 3. CORE HESAPLAMA MOTORU (ANALİZ FONKSİYONLARI)
# ==============================================================================

@st.cache_data(ttl=300)
def fetch_stock_info(ticker):
    try:
        t = yf.Ticker(ticker)
        h = t.history(period="2d")
        if h.empty: return None
        price = h["Close"].iloc[-1]
        prev = h["Close"].iloc[-2]
        change = ((price - prev) / prev) * 100
        return {"price": price, "change_pct": change}
    except: return None

@st.cache_data(ttl=600)
def get_tech_card_data(ticker):
    try:
        df = yf.download(ticker, period="1y", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']; high = df['High']; low = df['Low']
        sma50 = close.rolling(50).mean().iloc[-1]
        ema144 = close.ewm(span=144, adjust=False).mean().iloc[-1]
        atr = (high-low).rolling(14).mean().iloc[-1]
        return {
            "sma50": sma50, "ema144": ema144,
            "stop_level": close.iloc[-1] - (2 * atr),
            "risk_pct": (2 * atr) / close.iloc[-1] * 100,
            "atr": atr, "close_last": close.iloc[-1]
        }
    except: return None

@st.cache_data(ttl=600)
def calculate_sentiment_score(ticker):
    try:
        df = yf.download(ticker, period="6mo", progress=False)
        if df.empty: return {"total": 50, "mom": "Nötr", "vol": "Nötr"}
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd = (ema12 - ema26).iloc[-1]
        
        score = 50
        if rsi > 50: score += 10
        if macd > 0: score += 10
        if close.iloc[-1] > close.rolling(50).mean().iloc[-1]: score += 20
        
        return {"total": min(100, score), "rsi": rsi, "macd": macd}
    except: return {"total": 50}

# --- ICT MODÜLÜ ---
@st.cache_data(ttl=600)
def calculate_ict_deep_analysis(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty or len(df) < 60: return {"error": "Yetersiz Veri"}
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        high = df['High']; low = df['Low']; close = df['Close']; open_ = df['Open']
        
        # Swing Points
        sw_high = high.rolling(5, center=True).max().iloc[-1]
        sw_low = low.rolling(5, center=True).min().iloc[-1]
        curr = close.iloc[-1]
        
        structure = "YATAY"
        bias = "neutral"
        if curr > high.rolling(20).max().iloc[-2]: structure = "BOS (Yükseliş)"; bias = "bullish"
        elif curr < low.rolling(20).min().iloc[-2]: structure = "BOS (Düşüş)"; bias = "bearish"
        
        # Zone (Premium/Discount)
        range_high = high.tail(60).max()
        range_low = low.tail(60).min()
        range_loc = (curr - range_low) / (range_high - range_low)
        zone = "PREMIUM (Pahalı)" if range_loc > 0.5 else "DISCOUNT (Ucuz)"
        
        # FVG Detection
        fvg_txt = "Yok"
        if len(df) > 3:
            if low.iloc[-1] > high.iloc[-3]: fvg_txt = "Bullish FVG (Destek)"
            elif high.iloc[-1] < low.iloc[-3]: fvg_txt = "Bearish FVG (Direnç)"
            
        target = range_high if bias == "bullish" else range_low
        
        return {
            "structure": structure, "bias": bias, "zone": zone, "fvg_txt": fvg_txt,
            "target": target, "curr_price": curr
        }
    except Exception as e: return {"error": str(e)}

# --- PRICE ACTION MODÜLÜ ---
@st.cache_data(ttl=600)
def calculate_price_action_dna(ticker):
    try:
        df = yf.download(ticker, period="3mo", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        c = df['Close'].iloc[-1]; o = df['Open'].iloc[-1]; h = df['High'].iloc[-1]; l = df['Low'].iloc[-1]
        body = abs(c-o); total = h-l
        
        candle = "Standart"
        if total > 0:
            if (h-max(c,o)) > body*2: candle = "Shooting Star 🔫"
            elif (min(c,o)-l) > body*2: candle = "Hammer 🔨"
            elif body > total*0.8: candle = "Marubozu 🚀"
        
        vol_txt = "Normal"
        if df['Volume'].iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1] * 1.5:
            vol_txt = "Hacim Patlaması 🔊"
            
        return {"candle": {"title": candle}, "vol": {"title": vol_txt}}
    except: return None

# --- BREAKOUT TARAMA AJANI ---
@st.cache_data(ttl=900)
def agent3_breakout_scan(asset_list):
    if not asset_list: return pd.DataFrame()
    data = yf.download(asset_list, period="3mo", group_by="ticker", progress=False, threads=True)
    
    results = []
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol not in data.columns.levels[0]: continue
                df = data[symbol].copy()
            else: df = data.copy()
            
            if df.empty: continue
            df = df.dropna()
            
            close = df['Close']
            high_60 = close.rolling(60).max().iloc[-1]
            curr = close.iloc[-1]
            
            status = "Nötr"
            trend_val = "Nötr"
            
            if curr >= high_60 * 0.98: status = "Zirve Zorluyor"
            
            sma50 = close.rolling(50).mean().iloc[-1]
            if curr > sma50: trend_val = "Yükseliş"
            else: trend_val = "Düşüş"
            
            results.append({
                "Sembol": symbol, "Fiyat": f"{curr:.2f}", 
                "Durum": status, "Trend": trend_val,
                "RSI": round(calculate_sentiment_score(symbol)['rsi'], 0)
            })
        except: continue
        
    return pd.DataFrame(results)

# ==============================================================================
# 4. YENİ GÖRSELLEŞTİRME VE AI MODÜLLERİ
# ==============================================================================

def render_pro_chart(ticker):
    df = yf.download(ticker, period="6mo", interval="1d", progress=False)
    if df.empty: return st.error("Grafik verisi alınamadı.")
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    
    # Basit OB Tespiti (Görsel İçin)
    shapes = []
    for i in range(len(df)-10, len(df)-1):
        if df['Close'].iloc[i] < df['Open'].iloc[i] and df['Close'].iloc[i+1] > df['Open'].iloc[i+1]: 
            shapes.append(dict(type="rect", xref="x", yref="y",
                x0=df.index[i], y0=df['Low'].iloc[i], x1=df.index[-1] + timedelta(days=5), y1=df['High'].iloc[i],
                fillcolor="green", opacity=0.2, line_width=0, layer="below"))

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, 
                        subplot_titles=(f'{ticker} Price Action & Order Blocks', 'Hacim'), row_width=[0.2, 0.7])

    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Fiyat'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], line=dict(color='orange', width=1), name='SMA 50'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='blue', width=1), name='EMA 20'), row=1, col=1)
    
    colors = ['green' if row['Open'] - row['Close'] >= 0 else 'red' for index, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, showlegend=False), row=2, col=1)

    fig.update_layout(shapes=shapes, xaxis_rangeslider_visible=False, height=500, margin=dict(l=10, r=10, t=30, b=10),
                      plot_bgcolor='white', paper_bgcolor='white', font=dict(family="Inter", size=11, color="#1e3a8a"))
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#f0f9ff')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f0f9ff')
    st.plotly_chart(fig, use_container_width=True)

def render_ai_commentary_card(ticker, ict_data, sent_data):
    if not ict_data or "error" in ict_data: return
    
    trend = "YÜKSELİŞ" if "bullish" in ict_data.get('bias', '') else "DÜŞÜŞ"
    zone = "ALIM FIRSATI (Ucuz)" if "DISCOUNT" in ict_data.get('zone', '') else "KAR ALMA (Pahalı)"
    score = sent_data.get('total', 50)
    
    summary = f"**{ticker}** analizimde ana piyasa yapısının **{trend}** yönlü olduğunu tespit ettim. "
    if trend == "YÜKSELİŞ":
        if "DISCOUNT" in ict_data.get('zone', ''):
            summary += f"Fiyat şu an kurumsal 'Ucuzluk' (**{zone}**) bölgesinde. Bu, Akıllı Para'nın oyuna girebileceği bir seviye. "
            if score > 60: summary += "Momentum da arkamızda, setup güçlü görünüyor. 🚀"
        else:
            summary += f"Ancak fiyat **{zone}** bölgesine şişmiş. Trend yukarı olsa bile buradan girmek riskli, geri çekilme bekle. ⚠️"
    else:
        summary += f"Yapı negatif. Fiyat **{zone}** bölgesinde. Yükselişler satış fırsatı olabilir. 🔻"

    st.markdown(f"""
    <div style="background: linear-gradient(90deg, #eff6ff 0%, #ffffff 100%); border: 1px solid #3b82f6; border-left: 5px solid #2563eb; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
        <div style="display:flex; align-items:center; margin-bottom:8px;">
            <div style="font-size:1.5rem; margin-right:10px;">🤖</div>
            <div><div style="font-weight:800; color:#1e3a8a;">AI PAZAR YORUMU</div><div style="font-size:0.75rem; color:#64748B;">Algorithm v2.1 • {datetime.now().strftime('%H:%M')}</div></div>
        </div>
        <div style="font-size: 0.95rem; color: #334155;">{summary}</div>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar_filters():
    st.sidebar.markdown("### 🌪️ Akıllı Filtreler")
    f1 = st.sidebar.checkbox("Sadece Yükseliş Trendi", value=st.session_state.filters["trend_bull"])
    f2 = st.sidebar.checkbox("Sadece Ucuz Bölge (Discount)", value=st.session_state.filters["discount_only"])
    f3 = st.sidebar.checkbox("Yüksek RSI (>60)", value=st.session_state.filters["high_score"])
    st.session_state.filters = {"trend_bull": f1, "discount_only": f2, "high_score": f3}
    return st.session_state.filters

# ==============================================================================
# 5. ANA UYGULAMA AKIŞI
# ==============================================================================

# SIDEBAR
with st.sidebar:
    st.title("PRO TERMINAL")
    st.selectbox("Kategori", list(ASSET_GROUPS.keys()), key="selected_category_key", 
                 on_change=lambda: st.session_state.update(ticker=ASSET_GROUPS[st.session_state.selected_category_key][0]))
    
    current_opts = ASSET_GROUPS.get(st.session_state.selected_category_key, [])
    st.selectbox("Varlık", current_opts, key="selected_asset_key",
                 on_change=lambda: st.session_state.update(ticker=st.session_state.selected_asset_key))
    
    active_filters = render_sidebar_filters()
    
    st.divider()
    if st.button("⚡ Fırsatları Tara", type="primary"):
        with st.spinner("Piyasa taranıyor..."):
            st.session_state.agent3_data = agent3_breakout_scan(current_opts)

# MAIN AREA
ticker = st.session_state.ticker
ict_vals = calculate_ict_deep_analysis(ticker)
sent_vals = calculate_sentiment_score(ticker)
pa_vals = calculate_price_action_dna(ticker)
info = fetch_stock_info(ticker)

# ÜST KISIM (AI + FİYAT)
col_ai, col_stat = st.columns([3, 1])
with col_ai:
    render_ai_commentary_card(ticker, ict_vals, sent_vals)
with col_stat:
    if info:
        cls = "delta-pos" if info['change_pct'] >= 0 else "delta-neg"
        st.markdown(f'<div class="stat-box-small"><p style="margin:0; font-size:0.8rem;">FİYAT</p><p class="stat-value-small">{info["price"]:.2f}</p><p class="{cls}">{info["change_pct"]:.2f}%</p></div>', unsafe_allow_html=True)

# ANA DÜZEN (GRAFİK + ANALİZ)
col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown("### 📊 İnteraktif Price Action Grafiği")
    render_pro_chart(ticker)
    
    if st.session_state.agent3_data is not None:
        st.markdown("### 🔍 Tarama Sonuçları")
        df = st.session_state.agent3_data.copy()
        if active_filters['trend_bull']: df = df[df['Trend'] == "Yükseliş"]
        if active_filters['high_score']: df = df[df['RSI'] > 60]
        st.dataframe(df, use_container_width=True, hide_index=True)

with col_right:
    st.markdown("### 🧠 ICT & Yapı Analizi")
    if ict_vals and "error" not in ict_vals:
        bias_color = "#16a34a" if ict_vals['bias'] == "bullish" else "#dc2626"
        st.markdown(f"""
        <div class="info-card">
            <div class="info-row"><span class="label-long">Market Yapısı:</span><span class="info-val" style="color:{bias_color}">{ict_vals['structure']}</span></div>
            <div class="info-row"><span class="label-long">Bölge:</span><span class="info-val">{ict_vals['zone']}</span></div>
            <div class="info-row"><span class="label-long">FVG Durumu:</span><span class="info-val">{ict_vals['fvg_txt']}</span></div>
            <div class="info-row"><span class="label-long">Hedef Likidite:</span><span class="info-val">{ict_vals['target']:.2f}</span></div>
            <div class="edu-note" style="margin-top:10px;">Fiyat <strong>{ict_vals['zone']}</strong> bölgesinde. {ict_vals['structure']} yapısı korunuyor.</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("### 🕯️ Mum Analizi")
    if pa_vals:
        st.markdown(f"""
        <div class="info-card">
            <div class="info-row"><span class="label-long">Formasyon:</span><span class="info-val">{pa_vals['candle']['title']}</span></div>
            <div class="info-row"><span class="label-long">Hacim:</span><span class="info-val">{pa_vals['vol']['title']}</span></div>
        </div>
        """, unsafe_allow_html=True)
