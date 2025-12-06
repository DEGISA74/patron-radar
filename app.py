import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from textblob import TextBlob
from datetime import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Patronun Terminali v0.2", layout="wide", page_icon="🦅")

# --- STİL ---
st.markdown("""
<style>
    .metric-card { background-color: #0e1117; border: 1px solid #303030; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
    .bullish { border-left: 4px solid #00ff00; }
    .bearish { border-left: 4px solid #ff0000; }
    .neutral { border-left: 4px solid #gray; }
</style>
""", unsafe_allow_html=True)

# --- KAYNAK LİSTESİ (PİRAMİT MODELİ) ---
LEVEL_1_SOURCES = ['Bloomberg', 'Reuters', 'SEC', 'KAP', 'Business Wire']
LEVEL_2_SOURCES = ['WSJ', 'FT', 'CNBC', 'Barron\'s']

# --- ANALİZ FONKSİYONLARI ---

def get_sentiment(text):
    blob = TextBlob(text)
    score = blob.sentiment.polarity
    if score > 0.1: return "YUKARI", "🟢", score
    elif score < -0.1: return "AŞAĞI", "🔴", score
    else: return "NÖTR", "⚪", score

def fetch_data(ticker):
    stock = yf.Ticker(ticker)
    try:
        # 1 Yıllık Veri (Grafik İçin)
        hist = stock.history(period="1y")
        
        # Güncel Bilgiler
        info = stock.info
        news = stock.news
        
        # Haber İşleme
        processed_news = []
        for item in news:
            title = item.get('title', 'Başlık Yok')
            publisher = item.get('publisher', 'Bilinmiyor')
            link = item.get('link', '#')
            pub_time = item.get('providerPublishTime', 0)
            
            # Tarih formatlama
            try:
                date_obj = datetime.fromtimestamp(pub_time)
            except:
                date_obj = datetime.now()
            
            sentiment, icon, score = get_sentiment(title)
            
            # Seviye Belirleme
            level = 3
            if any(s.lower() in str(publisher).lower() for s in LEVEL_1_SOURCES): level = 1
            elif any(s.lower() in str(publisher).lower() for s in LEVEL_2_SOURCES): level = 2
            
            processed_news.append({
                'Tarih': date_obj,
                'Başlık': title,
                'Kaynak': publisher,
                'Seviye': level,
                'Yön': sentiment,
                'İkon': icon,
                'Link': link
            })
            
        return hist, info, processed_news
    except Exception as e:
        return None, None, None

def plot_ict_chart(df, ticker):
    """
    Price Action ve ICT Odaklı Grafik
    - Candlestick (Mum) Grafiği
    - Basit FVG (Fair Value Gap) Tespiti
    """
    fig = go.Figure()

    # Mum Grafiği Ekle
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        name=ticker
    ))

    # --- ICT FVG TESPİT ALGORİTMASI (Basit Versiyon) ---
    # FVG: 1. mumun yükseği ile 3. mumun düşüğü arasında boşluk kalması (Bullish FVG)
    # Son 30 mumu kontrol edelim ki grafik karışmasın
    for i in range(len(df)-30, len(df)-2):
        # Bullish FVG
        if df['High'].iloc[i] < df['Low'].iloc[i+2]:
            fig.add_shape(type="rect",
                x0=df.index[i], x1=df.index[i+2],
                y0=df['High'].iloc[i], y1=df['Low'].iloc[i+2],
                fillcolor="green", opacity=0.3, line_width=0,
            )
        # Bearish FVG
        elif df['Low'].iloc[i] > df['High'].iloc[i+2]:
            fig.add_shape(type="rect",
                x0=df.index[i], x1=df.index[i+2],
                y0=df['Low'].iloc[i], y1=df['High'].iloc[i+2],
                fillcolor="red", opacity=0.3, line_width=0,
            )

    fig.update_layout(
        title=f"{ticker} - ICT Price Action (Otomatik FVG Tespiti)",
        yaxis_title="Fiyat",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=600
    )
    return fig

# --- ARAYÜZ ---
st.title("🦅 Patronun Dijital Terminali v0.2")

with st.sidebar:
    ticker = st.text_input("Hisse Kodu", value="AAPL").upper()
    st.markdown("---")
    st.caption("Veriler: Yahoo Finance | Analiz: Price Action & Sentiment")

if ticker:
    hist, info, news_data = fetch_data(ticker)
    
    if hist is not None and not hist.empty:
        # Fiyat Bilgisi
        last_price = hist['Close'].iloc[-1]
        prev_price = hist['Close'].iloc[-2]
        change = ((last_price - prev_price) / prev_price) * 100
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Anlık Fiyat", f"{last_price:.2f}", f"%{change:.2f}")
        col2.metric("Sektör", info.get('sector', '-'))
        col3.metric("Öneri", info.get('recommendationKey', '-').upper())
        
        # Grafik Sekmesi
        st.subheader("Price Action Analizi")
        st.plotly_chart(plot_ict_chart(hist, ticker), use_container_width=True)
        st.info("💡 Grafikteki Yeşil/Kırmızı Kutular otomatik tespit edilen **Fair Value Gap (FVG)** bölgeleridir.")
        
        # Haber Sekmesi
        st.subheader("Piramit Haber Akışı")
        if news_data:
            df_news = pd.DataFrame(news_data).sort_values(by=['Seviye', 'Tarih'], ascending=[True, False])
            
            for _, row in df_news.iterrows():
                # Renk Sınıfı
                css = "bullish" if "YUKARI" in row['Yön'] else "bearish" if "AŞAĞI" in row['Yön'] else "neutral"
                
                st.markdown(f"""
                <div class="metric-card {css}">
                    <div style="display:flex; justify-content:space-between;">
                        <span style="font-size:0.8em; color:#aaa;">{row['Tarih'].strftime('%d %b %H:%M')}</span>
                        <span style="font-weight:bold; color:#fff;">{row['Kaynak']} (L{row['Seviye']})</span>
                    </div>
                    <h4 style="margin:5px 0;"><a href="{row['Link']}" target="_blank" style="text-decoration:none; color:white;">{row['Başlık']}</a></h4>
                    <div style="margin-top:5px;">
                        {row['İkon']} <strong>{row['Yön']}</strong> <span style="font-size:0.8em;">(Sentiment Skor: {row.get('Skor',0):.2f})</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("Güncel haber bulunamadı.")
            
    else:
        st.error("Veri çekilemedi. Hisse kodunu kontrol et.")
