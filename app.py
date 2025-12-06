import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from textblob import TextBlob
from datetime import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Patronun Terminali v0.4", layout="wide", page_icon="🦅")

# --- STİL VE CSS ---
st.markdown("""
<style>
    .metric-card { background-color: #0e1117; border: 1px solid #303030; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
    .bullish { border-left: 4px solid #00ff00; }
    .bearish { border-left: 4px solid #ff0000; }
    .neutral { border-left: 4px solid #gray; }
    /* Grafik üzerindeki butonları düzenle */
    .modebar-btn { color: white !important; }
</style>
""", unsafe_allow_html=True)

# --- KAYNAK LİSTESİ ---
LEVEL_1_SOURCES = ['Bloomberg', 'Reuters', 'SEC', 'KAP', 'Business Wire']
LEVEL_2_SOURCES = ['WSJ', 'FT', 'CNBC', 'Barron\'s']

# --- ANALİZ FONKSİYONLARI ---
def get_sentiment(text):
    if not text: return "NÖTR", "⚪", 0
    blob = TextBlob(str(text))
    score = blob.sentiment.polarity
    if score > 0.1: return "YUKARI", "🟢", score
    elif score < -0.1: return "AŞAĞI", "🔴", score
    else: return "NÖTR", "⚪", score

def plot_ict_chart(df, ticker):
    """
    v0.4: Zoom Özellikli ICT Grafiği
    """
    fig = go.Figure()

    # Mum Grafiği
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        name=ticker
    ))

    # ICT FVG Tespiti
    for i in range(len(df)-50, len(df)-2):
        try:
            if df['High'].iloc[i] < df['Low'].iloc[i+2]: # Bullish FVG
                fig.add_shape(type="rect",
                    x0=df.index[i], x1=df.index[i+2],
                    y0=df['High'].iloc[i], y1=df['Low'].iloc[i+2],
                    fillcolor="rgba(0, 255, 0, 0.2)", line_width=0,
                )
            elif df['Low'].iloc[i] > df['High'].iloc[i+2]: # Bearish FVG
                fig.add_shape(type="rect",
                    x0=df.index[i], x1=df.index[i+2],
                    y0=df['Low'].iloc[i], y1=df['High'].iloc[i+2],
                    fillcolor="rgba(255, 0, 0, 0.2)", line_width=0,
                )
        except: continue

    # Grafik Ayarları (Zoom Açık)
    fig.update_layout(
        title=f"{ticker} - ICT Price Action & FVG Analizi",
        yaxis_title="Fiyat",
        xaxis_rangeslider_visible=True, # Slider EKLENDİ
        template="plotly_dark",
        height=700, # Grafik biraz daha büyüdü
        dragmode='pan', # Varsayılan mod kaydırma
        margin=dict(l=0, r=0, t=30, b=0)
    )
    return fig

# --- VERİ ÇEKME (CACHING EKLENDİ) ---
# Bu fonksiyon veriyi 10 dakika (600 saniye) hafızada tutar.
# Böylece sayfayı yenilesen bile Yahoo'ya tekrar sormaz, engellenmezsin.
@st.cache_data(ttl=600)
def fetch_data_cached(ticker):
    stock = yf.Ticker(ticker)
    
    # 1. Fiyat
    try:
        hist = stock.history(period="1y")
    except:
        hist = pd.DataFrame()

    # 2. Bilgi (Info)
    try:
        info = stock.info
        # Eğer sektör bilgisi boşsa manuel kontrol
        if 'sector' not in info:
            info['sector'] = "-"
    except:
        info = {'sector': '-', 'targetMeanPrice': '-'}

    # 3. Haberler
    processed_news = []
    try:
        news = stock.news
        if news:
            for item in news:
                # Başlık kontrolü (Farklı keylere bak)
                title = item.get('title') or item.get('content', {}).get('title') or "Başlık Yok"
                publisher = item.get('publisher') or "Kaynak Bilinmiyor"
                link = item.get('link') or "#"
                
                # Tarih
                try:
                    pub_time = item.get('providerPublishTime', 0)
                    date_obj = datetime.fromtimestamp(pub_time)
                except:
                    date_obj = datetime.now()
                
                sentiment, icon, score = get_sentiment(title)
                
                # Seviye
                level = 3
                pub_str = str(publisher).lower()
                if any(s.lower() in pub_str for s in LEVEL_1_SOURCES): level = 1
                elif any(s.lower() in pub_str for s in LEVEL_2_SOURCES): level = 2
                
                processed_news.append({
                    'Tarih': date_obj,
                    'Başlık': title,
                    'Kaynak': publisher,
                    'Seviye': level,
                    'Yön': sentiment,
                    'İkon': icon,
                    'Link': link
                })
    except:
        pass

    return hist, info, processed_news

# --- ARAYÜZ ---
st.title("🦅 Patronun Dijital Terminali v0.4")

with st.sidebar:
    st.header("Radar Ayarları")
    ticker_input = st.text_input("Hisse Kodu", value="AAPL").upper()
    if st.button("Verileri Yenile"):
        st.cache_data.clear() # Önbelleği temizleme butonu
        st.experimental_rerun()
    st.info("Veriler 10 dk önbellekte tutulur. Taze veri için 'Verileri Yenile' diyebilirsin.")

if ticker_input:
    hist, info, news_data = fetch_data_cached(ticker_input)
    
    if hist is not None and not hist.empty:
        # Özet Bilgiler
        last_price = hist['Close'].iloc[-1]
        try:
            prev_price = hist['Close'].iloc[-2]
            change = ((last_price - prev_price) / prev_price) * 100
        except:
            change = 0
            
        col1, col2, col3 = st.columns(3)
        col1.metric("Fiyat", f"{last_price:.2f}", f"%{change:.2f}")
        col2.metric("Sektör", info.get('sector', '-'))
        col3.metric("Hedef Fiyat", info.get('targetMeanPrice', '-'))

        # Grafik
        st.plotly_chart(plot_ict_chart(hist, ticker_input), use_container_width=True)

        # Haberler
        st.subheader(f"📡 {ticker_input} Haber Akışı")
        if news_data:
            df_news = pd.DataFrame(news_data).sort_values(by=['Seviye', 'Tarih'], ascending=[True, False])
            
            for _, row in df_news.iterrows():
                if row['Başlık'] != "Başlık Yok": # Boş haberleri filtrele
                    css = "bullish" if "YUKARI" in row['Yön'] else "bearish" if "AŞAĞI" in row['Yön'] else "neutral"
                    st.markdown(f"""
                    <div class="metric-card {css}">
                        <div style="font-size:0.8em; color:#888;">{row['Tarih'].strftime('%d %b %H:%M')} | {row['Kaynak']} (L{row['Seviye']})</div>
                        <div style="font-weight:bold; margin:5px 0;"><a href="{row['Link']}" target="_blank" style="color:white; text-decoration:none;">{row['Başlık']}</a></div>
                        <div>{row['İkon']} {row['Yön']}</div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.warning("Bu hisse için şu an haber akışı sağlanamıyor.")
            
    else:
        st.error("Veri alınamadı. Hisse kodunu kontrol edin veya biraz bekleyip 'Verileri Yenile' butonuna basın.")
