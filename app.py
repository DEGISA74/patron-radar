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
# 1. AYARLAR VE ZENGİN STİL (ESKİ STİL KORUNDU)
# ==============================================================================
st.set_page_config(
    page_title="BORSA PRO TERMINAL", 
    layout="wide",
    page_icon="🦅"
)

if 'theme' not in st.session_state:
    st.session_state.theme = "Buz Mavisi"

THEMES = {
    "Beyaz": {"bg": "#FFFFFF", "box_bg": "#F8F9FA", "text": "#000000", "border": "#DEE2E6"},
    "Buz Mavisi": {"bg": "#F0F8FF", "box_bg": "#FFFFFF", "text": "#0F172A", "border": "#BFDBFE"}
}
current_theme = THEMES[st.session_state.theme]

st.markdown(f"""
<style>
    section[data-testid="stSidebar"] {{ width: 320px !important; }}
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
    
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {current_theme['text']}; }}
    .stApp {{ background-color: {current_theme['bg']}; }}
    
    /* ESKİ ZENGİN KART TASARIMI */
    .info-card {{
        background: {current_theme['box_bg']}; border: 1px solid {current_theme['border']};
        border-radius: 6px; padding: 8px; margin-bottom: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }}
    .info-header {{ font-weight: 800; color: #1e3a8a; border-bottom: 1px solid {current_theme['border']}; padding-bottom: 4px; margin-bottom: 6px; font-size: 0.85rem; }}
    .info-row {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 3px; border-bottom: 1px dashed #f1f5f9; padding-bottom:2px; }}
    .label-long {{ font-weight: 600; color: #64748B; font-size: 0.75rem; width: 40%; }} 
    .info-val {{ color: {current_theme['text']}; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; font-weight: 700; width: 60%; text-align:right; }}
    .edu-note {{ font-size: 0.7rem; color: #64748B; font-style: italic; margin-top: 2px; margin-bottom: 6px; line-height: 1.2; background: #f8fafc; padding: 2px; border-radius: 3px; }}
    
    /* AI KART STİLİ */
    .ai-card {{ background: linear-gradient(135deg, #ffffff 0%, #eff6ff 100%); border: 1px solid #3b82f6; border-left: 5px solid #2563eb; padding: 12px; border-radius: 8px; margin-bottom: 15px; }}
    
    .stat-box-small {{ text-align: center; padding: 5px; background: white; border-radius: 6px; border: 1px solid #cbd5e1; }}
    .stat-value-small {{ font-size: 1.1rem; font-weight: 800; font-family: 'JetBrains Mono'; }}
    .delta-pos {{ color: #16A34A; }} .delta-neg {{ color: #DC2626; }}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. VERİTABANI VE STATE
# ==============================================================================
# Varlık Listeleri (Genişletilmiş)
ASSET_GROUPS = {
    "S&P 500 (VIP)": ["NVDA", "TSLA", "AAPL", "MSFT", "AMD", "AMZN", "GOOGL", "META", "AGNC", "ARCC", "PFE", "JEPI", "MO", "EPD", "PLTR", "SOFI"],
    "BIST 100 (VIP)": ["THYAO.IS", "ASELS.IS", "GARAN.IS", "AKBNK.IS", "EREGL.IS", "SISE.IS", "BIMAS.IS", "TUPRS.IS", "KCHOL.IS", "SAHOL.IS", "HEKTS.IS", "SASA.IS", "KONTR.IS", "MIATK.IS", "ASTOR.IS", "REEDR.IS"],
    "KRİPTO & EMTİA": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "DOGE-USD", "AVAX-USD", "GC=F", "SI=F"]
}

# State Tanımları
if 'ticker' not in st.session_state: st.session_state.ticker = "NVDA"
if 'scan_data' not in st.session_state: st.session_state.scan_data = None
if 'radar2_data' not in st.session_state: st.session_state.radar2_data = None
if 'agent3_data' not in st.session_state: st.session_state.agent3_data = None
if 'stp_crosses' not in st.session_state: st.session_state.stp_crosses = []
if 'accum_data' not in st.session_state: st.session_state.accum_data = None
if 'filters' not in st.session_state: st.session_state.filters = {"trend_bull": False, "discount_only": False, "high_score": False}

# ==============================================================================
# 3. HESAPLAMA MOTORU (ESKİ KODUN GÜÇLÜ FONKSİYONLARI)
# ==============================================================================

@st.cache_data(ttl=300)
def fetch_stock_info(ticker):
    try:
        t = yf.Ticker(ticker)
        h = t.history(period="2d")
        if h.empty: return None
        return {"price": h["Close"].iloc[-1], "change_pct": ((h["Close"].iloc[-1] - h["Close"].iloc[-2])/h["Close"].iloc[-2])*100}
    except: return None

@st.cache_data(ttl=600)
def get_tech_card_data(ticker):
    try:
        df = yf.download(ticker, period="1y", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']; high = df['High']; low = df['Low']
        atr = (high-low).rolling(14).mean().iloc[-1]
        return {
            "sma50": close.rolling(50).mean().iloc[-1],
            "ema144": close.ewm(span=144, adjust=False).mean().iloc[-1],
            "stop_level": close.iloc[-1] - (2 * atr),
            "risk_pct": (2 * atr) / close.iloc[-1] * 100,
            "atr": atr, "close_last": close.iloc[-1]
        }
    except: return None

@st.cache_data(ttl=600)
def calculate_sentiment_score(ticker):
    try:
        df = yf.download(ticker, period="6mo", progress=False)
        if df.empty: return {"total": 50, "mom": "-", "vol": "-"}
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']; vol = df['Volume']
        
        # Detaylı Puanlama (Eski Koddan)
        score = 0; reasons = []
        delta = close.diff()
        gain = delta.where(delta>0,0).rolling(14).mean(); loss = -delta.where(delta<0,0).rolling(14).mean()
        rsi = 100 - (100/(1+(gain/loss))).iloc[-1]
        
        if rsi > 50 and rsi > (100 - (100/(1+(gain/loss))).iloc[-2]): score += 20; reasons.append("RSI Artıyor")
        
        ema12 = close.ewm(span=12).mean(); ema26 = close.ewm(span=26).mean(); macd = ema12-ema26
        if macd.iloc[-1] > macd.iloc[-2]: score += 20; reasons.append("MACD Güçleniyor")
        
        if vol.iloc[-1] > vol.rolling(20).mean().iloc[-1]: score += 15; reasons.append("Hacim Yüksek")
        if close.iloc[-1] > close.rolling(50).mean().iloc[-1]: score += 15; reasons.append("Trend Pozitif")
        if close.iloc[-1] > df['High'].rolling(20).max().shift(1).iloc[-1]: score += 10; reasons.append("Yeni Zirve (BOS)")
        
        return {"total": min(100, score), "mom": f"RSI: {rsi:.0f}", "vol": "Yüksek" if score > 60 else "Düşük", "reasons": reasons}
    except: return {"total": 50, "mom": "-", "vol": "-", "reasons": []}

# --- DERİN ANALİZ (X-RAY) ---
def get_deep_xray_data(ticker):
    sent = calculate_sentiment_score(ticker)
    def icon(cond): return "✅" if cond else "❌"
    r = sent.get('reasons', [])
    return {
        "mom_rsi": f"{icon('RSI Artıyor' in r)} RSI İvmesi",
        "mom_macd": f"{icon('MACD Güçleniyor' in r)} MACD Hist",
        "vol_obv": f"{icon('Hacim Yüksek' in r)} Hacim Akışı",
        "tr_ema": f"{icon('Trend Pozitif' in r)} SMA 50 Üzeri",
        "str_bos": f"{icon('Yeni Zirve (BOS)' in r)} Yapı Kırılımı"
    }

# --- ICT MODÜLÜ (ESKİ DETAYLI VERSİYON) ---
@st.cache_data(ttl=600)
def calculate_ict_deep_analysis(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty or len(df) < 60: return {"error": "Yetersiz Veri"}
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        high = df['High']; low = df['Low']; close = df['Close']; open_ = df['Open']
        curr = close.iloc[-1]
        
        # Yapı ve Bias
        sw_high = high.rolling(10).max().iloc[-2]
        sw_low = low.rolling(10).min().iloc[-2]
        structure = "YATAY"
        bias = "neutral"
        
        if curr > sw_high: structure = "BOS (Yükseliş) 🐂"; bias = "bullish"
        elif curr < sw_low: structure = "BOS (Düşüş) 🐻"; bias = "bearish"
        else: structure = "Internal Range"; bias = "bullish_retrace" if close.iloc[-1] > open_.iloc[-1] else "bearish_retrace"
        
        # Zone
        range_high = high.tail(60).max(); range_low = low.tail(60).min()
        range_loc = (curr - range_low) / (range_high - range_low)
        zone = "PREMIUM (Pahalı)" if range_loc > 0.5 else "DISCOUNT (Ucuz)"
        
        # FVG ve OB
        fvg_txt = "Yok"
        if len(df) > 3:
            if low.iloc[-1] > high.iloc[-3]: fvg_txt = f"Bullish FVG: {high.iloc[-3]:.2f}-{low.iloc[-1]:.2f}"
            elif high.iloc[-1] < low.iloc[-3]: fvg_txt = f"Bearish FVG: {low.iloc[-3]:.2f}-{high.iloc[-1]:.2f}"
            
        # Target & Setup (Risk Reward)
        target = range_high if "bullish" in bias else range_low
        entry = curr
        stop = low.tail(5).min() if "bullish" in bias else high.tail(5).max()
        risk = abs(entry - stop); reward = abs(target - entry)
        rr = reward / risk if risk > 0 else 0
        
        return {
            "structure": structure, "bias": bias, "zone": zone, "fvg_txt": fvg_txt,
            "target": target, "entry": entry, "stop": stop, "rr": rr,
            "ob_txt": "Potansiyel OB Mevcut"
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
        
        candle = "Standart Mum"
        if total > 0:
            if (h-max(c,o)) > body*2: candle = "Shooting Star 🔫 (Satış Baskısı)"
            elif (min(c,o)-l) > body*2: candle = "Hammer 🔨 (Alım İştahı)"
            elif body > total*0.8: candle = "Marubozu 🚀 (Güçlü Yön)"
            elif total < df['High'].diff().mean()*0.5: candle = "Doji ⚖️ (Kararsızlık)"

        # SFP (Swing Failure Pattern)
        sfp_txt = "Yok"
        recent_high = df['High'].iloc[-10:-1].max()
        if h > recent_high and c < recent_high: sfp_txt = "⚠️ Bearish SFP (Boğa Tuzağı)"
        
        return {"candle": candle, "sfp": sfp_txt, "vol": "Normal"}
    except: return None

# --- TARAMA FONKSİYONLARI (RADAR 1, 2, AJAN 3, STP) ---
@st.cache_data(ttl=900)
def scan_whole_market(asset_list):
    # Bu fonksiyon tüm ağır taramaları yapar
    results_a3 = []
    results_stp = []
    
    data = yf.download(asset_list, period="3mo", group_by="ticker", progress=False, threads=True)
    
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol not in data.columns.levels[0]: continue
                df = data[symbol].copy()
            else: df = data.copy()
            if df.empty: continue
            df = df.dropna()
            
            close = df['Close']
            
            # Ajan 3 (Breakout) Logic
            curr = close.iloc[-1]
            high_60 = close.rolling(60).max().iloc[-1]
            sma50 = close.rolling(50).mean().iloc[-1]
            if curr >= high_60 * 0.96:
                trend = "Yükseliş" if curr > sma50 else "Düşüş"
                results_a3.append({"Sembol": symbol, "Fiyat": f"{curr:.2f}", "Trend": trend, "Durum": "Zirveye Yakın"})
                
            # STP Logic
            typical_price = (df['High'] + df['Low'] + close) / 3
            stp = typical_price.ewm(span=6, adjust=False).mean()
            if close.iloc[-2] < stp.iloc[-2] and close.iloc[-1] > stp.iloc[-1]:
                results_stp.append({"Sembol": symbol, "Fiyat": f"{curr:.2f}", "Sinyal": "AL (Kesişim)"})
                
        except: continue
        
    return pd.DataFrame(results_a3), results_stp

# ==============================================================================
# 4. YENİ GÖRSELLEŞTİRME VE AI
# ==============================================================================

def render_pro_chart(ticker):
    df = yf.download(ticker, period="6mo", interval="1d", progress=False)
    if df.empty: return st.error("Grafik verisi alınamadı.")
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, 
                        subplot_titles=(f'{ticker} Price Action & Order Blocks', 'Hacim'), row_width=[0.2, 0.7])
    
    # Mumlar
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Fiyat'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], line=dict(color='orange', width=1), name='SMA 50'), row=1, col=1)
    
    # Hacim
    colors = ['green' if row['Open'] - row['Close'] >= 0 else 'red' for index, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, showlegend=False), row=2, col=1)
    
    # Basit OB Görselleştirmesi (Yeşil Kutular)
    shapes = []
    for i in range(len(df)-15, len(df)-2):
        if df['Close'].iloc[i] < df['Open'].iloc[i] and df['Close'].iloc[i+1] > df['Open'].iloc[i+1] and df['Close'].iloc[i+1] > df['High'].iloc[i]:
             shapes.append(dict(type="rect", xref="x", yref="y", x0=df.index[i], y0=df['Low'].iloc[i], x1=df.index[-1]+timedelta(days=5), y1=df['High'].iloc[i], fillcolor="green", opacity=0.15, line_width=0, layer="below"))

    fig.update_layout(shapes=shapes, xaxis_rangeslider_visible=False, height=500, margin=dict(l=5, r=5, t=30, b=5),
                      plot_bgcolor='white', paper_bgcolor='white', font=dict(family="Inter", size=11, color="#1e3a8a"))
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#f0f9ff')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f0f9ff')
    st.plotly_chart(fig, use_container_width=True)

def render_ai_commentary_card(ticker, ict_data, sent_data, tech_data):
    if not ict_data or "error" in ict_data: return
    
    trend = "YÜKSELİŞ" if "bullish" in ict_data.get('bias', '') else "DÜŞÜŞ"
    zone_simple = "UCUZ" if "DISCOUNT" in ict_data.get('zone', '') else "PAHALI"
    score = sent_data.get('total', 50)
    
    # Akıllı Metin Üretimi
    summary = f"**{ticker}** için yaptığım derin analizde piyasa yapısının **{trend}** yönlü olduğunu görüyorum. "
    if trend == "YÜKSELİŞ":
        if zone_simple == "UCUZ":
            summary += "Fiyat şu an 'Discount' bölgesinde, yani kurumsal alım için cazip seviyelerde. "
            if score > 60: summary += "Teknik göstergeler de bu yükselişi destekliyor. Setup: **GÜÇLÜ AL**. 🚀"
            else: summary += "Ancak momentum henüz tam güçlenmedi. Kademeli alım düşünülebilir."
        else:
            summary += "Ancak fiyat 'Premium' bölgesine çok hızlı ulaştı. Trend yukarı olsa bile buradan girmek riskli, **düzeltme bekle**. ⚠️"
    else:
        summary += "Piyasa ayların kontrolünde. Eski dipler kırılmış durumda. Yükselişler satış fırsatı olabilir. 🔻"

    st.markdown(f"""
    <div class="ai-card">
        <div style="display:flex; align-items:center; margin-bottom:8px;">
            <div style="font-size:1.8rem; margin-right:12px;">🤖</div>
            <div>
                <div style="font-weight:800; color:#1e3a8a; font-size:1.1rem;">SAVAŞ AI: PİYASA YORUMU</div>
                <div style="font-size:0.75rem; color:#64748B;">Algorithm v2.5 PRO • {datetime.now().strftime('%d %b %H:%M')}</div>
            </div>
        </div>
        <div style="font-family: 'Inter', sans-serif; font-size: 0.95rem; color: #334155; line-height: 1.6;">
            {summary}
        </div>
        <div style="margin-top:12px; display:flex; gap:10px;">
            <span style="background:#dbeafe; color:#1e40af; padding:4px 10px; border-radius:6px; font-size:0.75rem; font-weight:700;">YÖN: {trend}</span>
            <span style="background:#f3e8ff; color:#6b21a8; padding:4px 10px; border-radius:6px; font-size:0.75rem; font-weight:700;">BÖLGE: {zone_simple}</span>
            <span style="background:#fee2e2; color:#991b1b; padding:4px 10px; border-radius:6px; font-size:0.75rem; font-weight:700;">STOP: {tech_data['stop_level']:.2f}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# 5. ANA UYGULAMA (HIBRİT DÜZEN)
# ==============================================================================

# --- SIDEBAR (Filtreler + Menü) ---
with st.sidebar:
    st.markdown("### 🦅 BORSA PRO")
    st.selectbox("Kategori", list(ASSET_GROUPS.keys()), key="cat_key", 
                 on_change=lambda: st.session_state.update(ticker=ASSET_GROUPS[st.session_state.cat_key][0]))
    current_list = ASSET_GROUPS[st.session_state.cat_key]
    st.selectbox("Varlık Seç", current_list, key="ass_key", 
                 on_change=lambda: st.session_state.update(ticker=st.session_state.ass_key))
    
    st.markdown("---")
    st.markdown("### 🌪️ Akıllı Filtreler")
    f1 = st.sidebar.checkbox("Sadece Yükseliş Trendi", value=st.session_state.filters["trend_bull"])
    f2 = st.sidebar.checkbox("Sadece Ucuz Bölge", value=st.session_state.filters["discount_only"])
    st.session_state.filters = {"trend_bull": f1, "discount_only": f2, "high_score": False}
    
    st.markdown("---")
    if st.button("🚀 TÜM PİYASAYI TARA", type="primary"):
        with st.spinner("Ajanlar sahaya indi..."):
            a3_df, stp_list = scan_whole_market(current_list)
            st.session_state.agent3_data = a3_df
            st.session_state.stp_crosses = stp_list

# --- MAIN UI ---
ticker = st.session_state.ticker

# Veri Çekme
ict = calculate_ict_deep_analysis(ticker)
sent = calculate_sentiment_score(ticker)
pa = calculate_price_action_dna(ticker)
tech = get_tech_card_data(ticker)
xray = get_deep_xray_data(ticker)
info = fetch_stock_info(ticker)

# 1. ÜST BÖLÜM: AI KART + FİYAT (En Dikkat Çekici Yer)
col1, col2 = st.columns([3, 1])
with col1:
    render_ai_commentary_card(ticker, ict, sent, tech)
with col2:
    if info:
        cls = "delta-pos" if info['change_pct']>=0 else "delta-neg"
        st.markdown(f"""
        <div style="background:white; border:1px solid #cbd5e1; border-radius:8px; text-align:center; padding:15px; height:100%;">
            <div style="color:#64748B; font-size:0.8rem; font-weight:700;">ANLIK FİYAT</div>
            <div style="font-family:'JetBrains Mono'; font-size:1.8rem; font-weight:800; color:#0f172a;">{info['price']:.2f}</div>
            <div class="{cls}" style="font-weight:700;">%{info['change_pct']:.2f}</div>
        </div>
        """, unsafe_allow_html=True)

# 2. ORTA BÖLÜM: GRAFİK VE DETAYLI ANALİZ (YAN YANA)
col_chart, col_details = st.columns([2, 1])

with col_chart:
    st.markdown("### 📊 İnteraktif Analiz Grafiği")
    render_pro_chart(ticker)
    
    # Tarama Sonuçları (Grafiğin Altında)
    if st.session_state.agent3_data is not None:
        st.markdown("### 🕵️ Tarama Sonuçları")
        tab_a, tab_b = st.tabs(["🚀 Breakout Fırsatları", "⚡ STP Sinyalleri"])
        with tab_a:
            df_show = st.session_state.agent3_data
            if st.session_state.filters["trend_bull"]: df_show = df_show[df_show['Trend'] == "Yükseliş"]
            st.dataframe(df_show, use_container_width=True, hide_index=True)
        with tab_b:
            if st.session_state.stp_crosses:
                for item in st.session_state.stp_crosses:
                    st.success(f"{item['Sembol']} - {item['Sinyal']} - {item['Fiyat']}")
            else: st.info("Yeni sinyal yok.")

with col_details:
    st.markdown("### 🧠 ICT Smart Money")
    if ict and "error" not in ict:
        # Eski Zengin HTML Kartı
        bias_color = "#16a34a" if ict['bias'] == "bullish" else "#dc2626"
        st.markdown(f"""
        <div class="info-card" style="border-left: 3px solid {bias_color}">
            <div class="info-header">YAPI & BÖLGE</div>
            <div class="info-row"><span class="label-long">Market Yapısı:</span><span class="info-val" style="color:{bias_color}">{ict['structure']}</span></div>
            <div class="info-row"><span class="label-long">Konum:</span><span class="info-val">{ict['zone']}</span></div>
            <div class="edu-note">{ict['zone']} bölgesindeyiz. Kurumsal oyuncular burada aktiftir.</div>
            
            <div class="info-row"><span class="label-long">FVG (Gap):</span><span class="info-val">{ict['fvg_txt']}</span></div>
            <div class="info-row"><span class="label-long">Hedef (TP):</span><span class="info-val">{ict['target']:.2f}</span></div>
            <div class="info-row"><span class="label-long">R/R Oranı:</span><span class="info-val">{ict['rr']:.2f}R</span></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 🕯️ Price Action DNA")
    if pa:
        st.markdown(f"""
        <div class="info-card">
            <div class="info-row"><span class="label-long">Mum:</span><span class="info-val">{pa['candle']}</span></div>
            <div class="info-row"><span class="label-long">Tuzak (SFP):</span><span class="info-val">{pa['sfp']}</span></div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("### 🔍 Derin Röntgen")
    if xray:
        html_xray = ""
        for k, v in xray.items():
            html_xray += f"<div class='info-row'><span class='info-val' style='width:100%; text-align:left;'>{v}</span></div>"
        st.markdown(f"<div class='info-card'>{html_xray}</div>", unsafe_allow_html=True)
