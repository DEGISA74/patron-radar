import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from textblob import TextBlob
from datetime import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Patronun Terminali v0.7", layout="wide", page_icon="🦅")

# --- PROFESYONEL TASARIM (CSS & FONTLAR) ---
st.markdown("""
<style>
    /* Google Fonts İçe Aktarma */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&display=swap');

    /* Genel Font Ayarları */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Rakamlar için Monospace Font */
    .stMetricValue, .money-text {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Özel İstatistik Kartları (Stat Cards) */
    .stat-box {
        background: linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        transition: all 0.3s ease;
    }
    .stat-box:hover {
        border-color: rgba(255,255,255,0.2);
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    }
    .stat-label { font-size: 0.8rem; color: #8b9bb4; text-transform: uppercase; letter-spacing: 1px; }
    .stat-value { font-size: 1.5rem; font-weight: 700; color: #e2e8f0; margin: 5px 0; }
    .stat-delta { font-size: 0.9rem; font-weight: 600; }
    .delta-pos { color: #00E676; }
    .delta-neg { color: #FF1744; }

    /* Haber Kartları - Daha Kompakt */
    .news-card {
        background-color: #131722;
        border-left: 3px solid #333;
        padding: 12px;
        margin-bottom: 8px;
        border-radius: 4px;
    }
    .news-title { color: #e0e0e0; font-weight: 600; text-decoration: none; font-size: 0.95rem; }
    .news-meta { color: #666; font-size: 0.75rem; margin-top: 4px; font-family: 'JetBrains Mono', monospace; }
    
    /* Buton Özelleştirme */
    .stButton button {
        background-color: #1e2329;
        color: white;
        border: 1px solid #2a2e39;
        border-radius: 6px;
        font-weight: 600;
    }
    .stButton button:hover {
        border-color: #4a4e69;
        color: #29B6F6;
    }
</style>
""", unsafe_allow_html=True)

# --- OTURUM ---
if 'ticker' not in st.session_state:
    st.session_state.ticker = "THYAO.IS"

def set_ticker(symbol): st.session_state.ticker = symbol

# --- FONKSİYONLAR ---
def get_sentiment(text):
    if not text: return "NÖTR", "⚪"
    blob = TextBlob(str(text))
    score = blob.sentiment.polarity
    if score > 0.1: return "YUKARI", "🟢"
    elif score < -0.1: return "AŞAĞI", "🔴"
    else: return "NÖTR", "⚪"

def plot_ict_chart(df, ticker):
    fig = go.Figure()

    # Mum Grafiği (Daha sade renkler)
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'], name=ticker,
        increasing_line_color='#00E676', increasing_fillcolor='#00E676',
        decreasing_line_color='#FF1744', decreasing_fillcolor='#FF1744'
    ))

    # ICT FVG Kutuları
    for i in range(len(df)-50, len(df)-2):
        try:
            if df['High'].iloc[i] < df['Low'].iloc[i+2]: # Bullish
                fig.add_shape(type="rect", x0=df.index[i], x1=df.index[i+2],
                    y0=df['High'].iloc[i], y1=df['Low'].iloc[i+2],
                    fillcolor="rgba(0, 230, 118, 0.15)", line_width=0)
            elif df['Low'].iloc[i] > df['High'].iloc[i+2]: # Bearish
                fig.add_shape(type="rect", x0=df.index[i], x1=df.index[i+2],
                    y0=df['Low'].iloc[i], y1=df['High'].iloc[i+2],
                    fillcolor="rgba(255, 23, 68, 0.15)", line_width=0)
        except: continue

    # Grafik Ayarları (MİNİMALİST VE TEMİZ)
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)', # Arkaplan şeffaf
        plot_bgcolor='rgba(0,0,0,0)',  # Çizim alanı şeffaf
        height=650,
        margin=dict(l=0, r=40, t=20, b=0),
        xaxis=dict(showgrid=False, rangeslider=dict(visible=False)), # Grid çizgilerini kaldır
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', side='right'), # Fiyat sağda
        dragmode='pan'
    )
    return fig

@st.cache_data(ttl=600)
def fetch_data_cached(ticker):
    stock = yf.Ticker(ticker)
    try: hist = stock.history(period="1y")
    except: hist = pd.DataFrame()
    try: info = stock.info
    except: info = {}
    
    processed_news = []
    try:
        news = stock.news
        if news:
            for item in news:
                title = item.get('title') or "Başlık Yok"
                pub = item.get('publisher') or "Bilinmiyor"
                link = item.get('link') or "#"
                try: date = datetime.fromtimestamp(item.get('providerPublishTime', 0))
                except: date = datetime.now()
                sent, icon = get_sentiment(title)
                
                lvl = 3
                L1 = ['Bloomberg', 'Reuters', 'KAP', 'SEC']; L2 = ['WSJ', 'CNBC', 'FT']
                if any(x.lower() in str(pub).lower() for x in L1): lvl = 1
                elif any(x.lower() in str(pub).lower() for x in L2): lvl = 2
                processed_news.append({'Tarih': date, 'Başlık': title, 'Kaynak': pub, 'Seviye': lvl, 'Yön': sent, 'İkon': icon, 'Link': link})
    except: pass
    return hist, info, processed_news

# --- ARAYÜZ ---
st.title("🦅 Patronun Terminali")

# Üst Bar (Hızlı Erişim)
col_btns = st.columns([1,1,1,1,1,2])
with col_btns[0]: 
    if st.button("🇹🇷 THYAO"): set_ticker("THYAO.IS")
with col_btns[1]:
    if st.button("🇺🇸 AAPL"): set_ticker("AAPL")
with col_btns[2]:
    if st.button("🥇 GOLD"): set_ticker("GC=F")
with col_btns[3]:
    if st.button("₿ BTC"): set_ticker("BTC-USD")
with col_btns[4]:
     if st.button("🔄"): st.cache_data.clear(); st.rerun()

# Arama
ticker = st.text_input("", value=st.session_state.ticker, placeholder="Hisse Ara...").upper()
if ticker != st.session_state.ticker: st.session_state.ticker = ticker

# Veri Akışı
hist, info, news_data = fetch_data_cached(st.session_state.ticker)

if hist is not None and not hist.empty:
    last = hist['Close'].iloc[-1]
    prev = hist['Close'].iloc[-2]
    chg = ((last - prev) / prev) * 100
    delta_class = "delta-pos" if chg >= 0 else "delta-neg"
    delta_sign = "+" if chg >= 0 else ""
    
    # --- ÖZEL METRİK KARTLARI (HTML/CSS) ---
    c1, c2, c3, c4 = st.columns(4)
    
    c1.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">Anlık Fiyat</div>
        <div class="stat-value money-text">{last:.2f}</div>
        <div class="stat-delta {delta_class} money-text">{delta_sign}{chg:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)
    
    c2.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">Hacim</div>
        <div class="stat-value money-text">{info.get('volume', 0)/1000000:.1f}M</div>
        <div class="stat-delta" style="color:#8b9bb4">Günlük</div>
    </div>
    """, unsafe_allow_html=True)
    
    c3.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">Hedef Fiyat</div>
        <div class="stat-value money-text">{info.get('targetMeanPrice', '-')}</div>
        <div class="stat-delta" style="color:#29B6F6">Analist Ort.</div>
    </div>
    """, unsafe_allow_html=True)

    c4.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">Sektör</div>
        <div class="stat-value" style="font-size:1.1rem; margin-top:10px;">{info.get('sector', '-')}</div>
    </div>
    """, unsafe_allow_html=True)

    st.write("") # Boşluk

    # --- GRAFİK ve HABERLER (Yan Yana) ---
    col_chart, col_news = st.columns([3, 1])
    
    with col_chart:
        st.plotly_chart(plot_ict_chart(hist, st.session_state.ticker), use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})
    
    with col_news:
        st.subheader("Piyasa Akışı")
        # Scrollable Alan (Yeni Özellik)
        with st.container(height=650):
            if news_data:
                df_news = pd.DataFrame(news_data).sort_values(by=['Seviye', 'Tarih'], ascending=[True, False])
                for _, row in df_news.iterrows():
                    if row['Başlık'] != "Başlık Yok":
                        color = "#00E676" if "YUKARI" in row['Yön'] else "#FF1744" if "AŞAĞI" in row['Yön'] else "#9e9e9e"
                        st.markdown(f"""
                        <div class="news-card" style="border-left-color: {color};">
                            <a href="{row['Link']}" target="_blank" class="news-title">{row['Başlık']}</a>
                            <div class="news-meta">
                                {row['Kaynak']} • {row['Tarih'].strftime('%H:%M')}
                            </div>
                            <div style="font-size:0.8rem; margin-top:5px; color:{color}">
                                {row['İkon']} {row['Yön']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("Haber akışı sessiz.")

else:
    st.error("Veri yok.")
