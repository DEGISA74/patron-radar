import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from textblob import TextBlob
from datetime import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Patronun Terminali v0.5", layout="wide", page_icon="🦅")

# --- YENİ MODERN STİL (CSS) ---
st.markdown("""
<style>
    /* Daha ferah, kompakt kart tasarımı */
    .metric-card {
        background-color: #1e222d; /* Kömür grisi/Mavi ton */
        border: 1px solid #2d3342;
        padding: 12px; /* Daha az boşluk */
        border-radius: 8px;
        margin-bottom: 8px; /* Kartlar arası mesafe azaldı */
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: scale(1.01); /* Üzerine gelince hafif büyüme efekti */
        border-color: #4a4e69;
    }
    .bullish { border-left: 4px solid #00c853; } /* Daha canlı yeşil */
    .bearish { border-left: 4px solid #ff1744; } /* Daha canlı kırmızı */
    .neutral { border-left: 4px solid #9e9e9e; }
    
    /* Metin boyutları */
    .card-meta { font-size: 0.75rem; color: #a0a0a0; margin-bottom: 4px; }
    .card-title { font-size: 1rem; font-weight: 600; color: #ffffff; text-decoration: none; }
    .card-sentiment { font-size: 0.85rem; margin-top: 6px; }
    
    /* Streamlit varsayılan boşluklarını azalt */
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# --- KAYNAKLAR ---
LEVEL_1_SOURCES = ['Bloomberg', 'Reuters', 'SEC', 'KAP', 'Business Wire']
LEVEL_2_SOURCES = ['WSJ', 'FT', 'CNBC', 'Barron\'s']

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
                    fillcolor="rgba(0, 200, 83, 0.2)", line_width=0)
            elif df['Low'].iloc[i] > df['High'].iloc[i+2]: # Bearish
                fig.add_shape(type="rect", x0=df.index[i], x1=df.index[i+2],
                    y0=df['Low'].iloc[i], y1=df['High'].iloc[i+2],
                    fillcolor="rgba(255, 23, 68, 0.2)", line_width=0)
        except: continue

    # Grafik Ayarları (FULL ZOOM AKTİF)
    fig.update_layout(
        title=f"{ticker} - ICT Analizi",
        yaxis_title="Fiyat",
        xaxis_rangeslider_visible=False, # Slider'ı kaldırdım, mouse daha rahat
        template="plotly_dark",
        height=650,
        margin=dict(l=10, r=10, t=40, b=10),
        # Hem X hem Y ekseninde zoom serbest
        xaxis=dict(fixedrange=False),
        yaxis=dict(fixedrange=False) 
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
                publisher = item.get('publisher') or "Bilinmiyor"
                link = item.get('link') or "#"
                try: date_obj = datetime.fromtimestamp(item.get('providerPublishTime', 0))
                except: date_obj = datetime.now()
                
                sentiment, icon = get_sentiment(title)
                
                level = 3
                if any(s.lower() in str(publisher).lower() for s in LEVEL_1_SOURCES): level = 1
                elif any(s.lower() in str(publisher).lower() for s in LEVEL_2_SOURCES): level = 2
                
                processed_news.append({
                    'Tarih': date_obj, 'Başlık': title, 'Kaynak': publisher,
                    'Seviye': level, 'Yön': sentiment, 'İkon': icon, 'Link': link
                })
    except: pass
    
    return hist, info, processed_news

# --- ARAYÜZ ---
st.title("🦅 Patronun Dijital Terminali v0.5")

# Arama Bölümü
col_search, col_btn = st.columns([4, 1])
with col_search:
    ticker_input = st.text_input("Hisse Kodu (BIST için .IS ekle: THYAO.IS, GARAN.IS)", value="AAPL").upper()
with col_btn:
    st.write("") # Hizalama boşluğu
    st.write("") 
    if st.button("🔄 Yenile"):
        st.cache_data.clear()
        st.experimental_rerun()

if ticker_input:
    hist, info, news_data = fetch_data_cached(ticker_input)
    
    if hist is not None and not hist.empty:
        # Metrikler
        last = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        chg = ((last - prev) / prev) * 100
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Fiyat", f"{last:.2f}", f"%{chg:.2f}")
        c2.metric("Sektör", info.get('sector', '-'))
        c3.metric("F/K", f"{info.get('trailingPE','-')}")
        c4.metric("Hedef", info.get('targetMeanPrice', '-'))

        # Grafik (Scroll Zoom Aktif)
        st.subheader("Price Action")
        # config={'scrollZoom': True} -> Mouse tekerleği ile zoomu açar
        st.plotly_chart(plot_ict_chart(hist, ticker_input), use_container_width=True, config={'scrollZoom': True})
        st.caption("🔍 Mouse tekerleği ile grafiğe yaklaşabilir, sağ tık ile sürükleyebilirsin. Çift tıklama resetler.")

        # Haberler (Yeni Tasarım)
        st.subheader("Piramit Haber Akışı")
        if news_data:
            df_news = pd.DataFrame(news_data).sort_values(by=['Seviye', 'Tarih'], ascending=[True, False])
            
            for _, row in df_news.iterrows():
                if row['Başlık'] != "Başlık Yok":
                    css = "bullish" if "YUKARI" in row['Yön'] else "bearish" if "AŞAĞI" in row['Yön'] else "neutral"
                    
                    st.markdown(f"""
                    <div class="metric-card {css}">
                        <div class="card-meta">
                            {row['Tarih'].strftime('%d %b %H:%M')} | {row['Kaynak']} (L{row['Seviye']})
                        </div>
                        <a href="{row['Link']}" target="_blank" class="card-title">
                            {row['Başlık']}
                        </a>
                        <div class="card-sentiment">
                            {row['İkon']} <strong>{row['Yön']}</strong>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("Bu sembol için güncel haber akışı yok.")
    else:
        st.error("Veri bulunamadı. Türk hisseleri için sonuna .IS eklediğinden emin ol (Örn: THYAO.IS)")
