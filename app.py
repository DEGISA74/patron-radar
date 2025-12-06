import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from textblob import TextBlob
from datetime import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Patronun Terminali v0.6", layout="wide", page_icon="🦅")

# --- MODERN "GLASS" TASARIM (CSS) ---
st.markdown("""
<style>
    /* Buzlu Cam (Glassmorphism) Tasarımı */
    .metric-card {
        background: rgba(255, 255, 255, 0.05); /* Şeffaf Arkaplan */
        border: 1px solid rgba(255, 255, 255, 0.1); /* İnce Çerçeve */
        backdrop-filter: blur(10px); /* Arkası bulanık */
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 10px;
        transition: transform 0.2s, border-color 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px); /* Hafif yukarı kalkma */
        border-color: rgba(255, 255, 255, 0.3);
    }
    
    /* Yön Renkleri - Daha Neon ve Parlak */
    .bullish { border-left: 4px solid #00E676; box-shadow: -2px 0 10px rgba(0, 230, 118, 0.1); } 
    .bearish { border-left: 4px solid #FF1744; box-shadow: -2px 0 10px rgba(255, 23, 68, 0.1); }
    .neutral { border-left: 4px solid #B0BEC5; }
    
    /* Metin Stilleri */
    .card-meta { font-size: 0.8rem; color: #90A4AE; margin-bottom: 5px; letter-spacing: 0.5px; }
    .card-title { font-size: 1.1rem; font-weight: 600; color: #ECEFF1; text-decoration: none; display: block; }
    .card-title:hover { color: #29B6F6; }
    .card-sentiment { font-size: 0.9rem; margin-top: 8px; font-weight: 500; }
    
    /* Butonlar */
    .stButton button { width: 100%; border-radius: 8px; border: 1px solid rgba(255,255,255,0.2); }
</style>
""", unsafe_allow_html=True)

# --- OTURUM YÖNETİMİ (Hisse Değişimi İçin) ---
if 'ticker' not in st.session_state:
    st.session_state.ticker = "THYAO.IS" # Varsayılan açılış hissesi

# --- FONKSİYONLAR ---
def set_ticker(symbol):
    st.session_state.ticker = symbol

def get_sentiment(text):
    if not text: return "NÖTR", "⚪"
    blob = TextBlob(str(text))
    score = blob.sentiment.polarity
    if score > 0.1: return "YUKARI", "🟢"
    elif score < -0.1: return "AŞAĞI", "🔴"
    else: return "NÖTR", "⚪"

def plot_ict_chart(df, ticker):
    fig = go.Figure()

    # Mum Grafiği
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'], name=ticker
    ))

    # ICT FVG Kutuları
    for i in range(len(df)-50, len(df)-2):
        try:
            if df['High'].iloc[i] < df['Low'].iloc[i+2]: # Bullish
                fig.add_shape(type="rect", x0=df.index[i], x1=df.index[i+2],
                    y0=df['High'].iloc[i], y1=df['Low'].iloc[i+2],
                    fillcolor="rgba(0, 230, 118, 0.2)", line_width=0)
            elif df['Low'].iloc[i] > df['High'].iloc[i+2]: # Bearish
                fig.add_shape(type="rect", x0=df.index[i], x1=df.index[i+2],
                    y0=df['Low'].iloc[i], y1=df['High'].iloc[i+2],
                    fillcolor="rgba(255, 23, 68, 0.2)", line_width=0)
        except: continue

    # Grafik Ayarları (FULL 2D ZOOM & PAN)
    fig.update_layout(
        title=dict(text=f"{ticker} - ICT Price Action", font=dict(size=20, color="white")),
        yaxis_title="Fiyat",
        template="plotly_dark",
        height=700,
        dragmode='pan', # Varsayılan mod: Tut ve Sürükle
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis=dict(fixedrange=False, rangeslider=dict(visible=False)), # X ekseni serbest
        yaxis=dict(fixedrange=False)  # Y ekseni serbest (Yukarı aşağı zoom)
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
                title = item.get('title') or item.get('content', {}).get('title') or "Başlık Yok"
                pub = item.get('publisher') or "Bilinmiyor"
                link = item.get('link') or "#"
                try: date = datetime.fromtimestamp(item.get('providerPublishTime', 0))
                except: date = datetime.now()
                
                sent, icon = get_sentiment(title)
                
                lvl = 3
                LEVEL_1 = ['Bloomberg', 'Reuters', 'KAP', 'SEC']
                LEVEL_2 = ['WSJ', 'CNBC', 'FT']
                
                if any(x.lower() in str(pub).lower() for x in LEVEL_1): lvl = 1
                elif any(x.lower() in str(pub).lower() for x in LEVEL_2): lvl = 2
                
                processed_news.append({'Tarih': date, 'Başlık': title, 'Kaynak': pub, 'Seviye': lvl, 'Yön': sent, 'İkon': icon, 'Link': link})
    except: pass
    
    return hist, info, processed_news

# --- ARAYÜZ ---
st.title("🦅 Patronun Dijital Terminali v0.6")

# Hızlı Erişim Butonları
c1, c2, c3, c4, c5 = st.columns(5)
if c1.button("🇹🇷 THYAO"): set_ticker("THYAO.IS")
if c2.button("🇹🇷 GARAN"): set_ticker("GARAN.IS")
if c3.button("🇺🇸 AAPL"): set_ticker("AAPL")
if c4.button("🇺🇸 TSLA"): set_ticker("TSLA")
if c5.button("🥇 GOLD"): set_ticker("GC=F")

# Arama ve Yenileme
col_input, col_refresh = st.columns([5, 1])
with col_input:
    # Text input session state'i günceller
    ticker_input = st.text_input("Hisse Kodu (Manuel Giriş)", value=st.session_state.ticker).upper()
    # Eğer input değişirse state'i güncelle
    if ticker_input != st.session_state.ticker:
        st.session_state.ticker = ticker_input
with col_refresh:
    st.write("")
    st.write("")
    if st.button("🔄 Yenile"):
        st.cache_data.clear()
        st.rerun() # GÜNCELLENDİ: st.experimental_rerun() yerine st.rerun()

# Ana Akış
ticker = st.session_state.ticker
hist, info, news_data = fetch_data_cached(ticker)

if hist is not None and not hist.empty:
    # Metrikler
    last = hist['Close'].iloc[-1]
    prev = hist['Close'].iloc[-2]
    chg = ((last - prev) / prev) * 100
    color = "normal" if chg >= 0 else "inverse"
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Fiyat", f"{last:.2f}", f"%{chg:.2f}", delta_color=color)
    m2.metric("Sektör", info.get('sector', '-'))
    m3.metric("F/K", f"{info.get('trailingPE','-')}")
    m4.metric("Hacim", f"{info.get('volume',0):,}")

    # GRAFİK (Price Action)
    st.subheader(f"📈 {ticker} - Price Action")
    # config={'scrollZoom': True} -> Mouse tekerleğiyle her yöne zoom
    st.plotly_chart(plot_ict_chart(hist, ticker), use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True})
    st.caption("🔍 **İpucu:** Grafiği mouse ile tutup sürükleyebilirsin. Tekerlek ile yakınlaşıp uzaklaşabilirsin (Hem fiyat hem zaman ekseninde).")

    # HABERLER
    st.subheader("📡 Piramit Haber Akışı")
    if news_data:
        df_news = pd.DataFrame(news_data).sort_values(by=['Seviye', 'Tarih'], ascending=[True, False])
        for _, row in df_news.iterrows():
            if row['Başlık'] != "Başlık Yok":
                css = "bullish" if "YUKARI" in row['Yön'] else "bearish" if "AŞAĞI" in row['Yön'] else "neutral"
                st.markdown(f"""
                <div class="metric-card {css}">
                    <div class="card-meta">
                        {row['Tarih'].strftime('%d %b %H:%M')} | {row['Kaynak']} (Seviye {row['Seviye']})
                    </div>
                    <a href="{row['Link']}" target="_blank" class="card-title">
                        {row['Başlık']}
                    </a>
                    <div class="card-sentiment">
                        {row['İkon']} {row['Yön']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Bu sembol için anlık haber akışı yok.")
else:
    st.error("Veri bulunamadı. BIST hisseleri için .IS eklemeyi unutma (Örn: ASELS.IS).")
