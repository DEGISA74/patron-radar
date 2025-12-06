import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from textblob import TextBlob
from datetime import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Patronun Terminali v0.3", layout="wide", page_icon="🦅")

# --- STİL ---
st.markdown("""
<style>
    .metric-card { background-color: #0e1117; border: 1px solid #303030; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
    .bullish { border-left: 4px solid #00ff00; }
    .bearish { border-left: 4px solid #ff0000; }
    .neutral { border-left: 4px solid #gray; }
</style>
""", unsafe_allow_html=True)

# --- KAYNAK LİSTESİ ---
LEVEL_1_SOURCES = ['Bloomberg', 'Reuters', 'SEC', 'KAP', 'Business Wire']
LEVEL_2_SOURCES = ['WSJ', 'FT', 'CNBC', 'Barron\'s']

# --- YARDIMCI FONKSİYONLAR ---
def get_sentiment(text):
    blob = TextBlob(text)
    score = blob.sentiment.polarity
    if score > 0.1: return "YUKARI", "🟢", score
    elif score < -0.1: return "AŞAĞI", "🔴", score
    else: return "NÖTR", "⚪", score

def plot_ict_chart(df, ticker):
    """
    ICT Konseptli Mum Grafiği
    Otomatik Fair Value Gap (FVG) çizimi içerir.
    """
    fig = go.Figure()

    # 1. Mum Grafiği (Candlestick)
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        name=ticker
    ))

    # 2. ICT FVG Tespiti (Otomatik Kutular)
    # Son 50 muma bakıyoruz ki grafik çok karışmasın
    for i in range(len(df)-50, len(df)-2):
        try:
            # Bullish FVG (Yeşil Kutu): 1. Mumun Yükseği < 3. Mumun Düşüğü
            if df['High'].iloc[i] < df['Low'].iloc[i+2]:
                fig.add_shape(type="rect",
                    x0=df.index[i], x1=df.index[i+2],
                    y0=df['High'].iloc[i], y1=df['Low'].iloc[i+2],
                    fillcolor="rgba(0, 255, 0, 0.2)", line_width=0,
                )
            
            # Bearish FVG (Kırmızı Kutu): 1. Mumun Düşüğü > 3. Mumun Yükseği
            elif df['Low'].iloc[i] > df['High'].iloc[i+2]:
                fig.add_shape(type="rect",
                    x0=df.index[i], x1=df.index[i+2],
                    y0=df['Low'].iloc[i], y1=df['High'].iloc[i+2],
                    fillcolor="rgba(255, 0, 0, 0.2)", line_width=0,
                )
        except:
            continue

    fig.update_layout(
        title=f"{ticker} - ICT Price Action & FVG Analizi",
        yaxis_title="Fiyat",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=600,
        margin=dict(l=0, r=0, t=30, b=0)
    )
    return fig

# --- ANA VERİ ÇEKME FONKSİYONU ---
def fetch_data_safe(ticker):
    """
    Hata toleranslı veri çekme modülü.
    Haberler gelmezse bile grafiği çizer.
    """
    stock = yf.Ticker(ticker)
    
    # 1. Fiyat Verisi (En kritik)
    try:
        hist = stock.history(period="1y")
        if hist.empty:
            return None, None, None
    except Exception as e:
        st.error(f"Fiyat verisi hatası: {e}")
        return None, None, None

    # 2. Şirket Bilgisi
    try:
        info = stock.info
    except:
        info = {} # Bilgi gelmezse boş sözlük dön

    # 3. Haber Verisi (En sık hata veren kısım)
    processed_news = []
    try:
        news = stock.news
        if news:
            for item in news:
                title = item.get('title', 'Başlık Yok')
                publisher = item.get('publisher', 'Bilinmiyor')
                link = item.get('link', '#')
                
                # Tarih İşleme
                try:
                    pub_time = item.get('providerPublishTime', 0)
                    date_obj = datetime.fromtimestamp(pub_time)
                except:
                    date_obj = datetime.now()
                
                sentiment, icon, score = get_sentiment(title)
                
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
                    'Link': link,
                    'Skor': score
                })
    except Exception as e:
        # Haber çekilemezse programı durdurma, sadece konsola yaz
        print(f"Haber çekme hatası: {e}")

    return hist, info, processed_news

# --- ARAYÜZ (UI) ---
st.title("🦅 Patronun Dijital Terminali v0.3")

with st.sidebar:
    st.header("Kontrol Paneli")
    ticker = st.text_input("Hisse Kodu Girin", value="AAPL").upper()
    st.info("ℹ️ Mum grafikleri ve FVG (Dengesizlik) kutuları aktiftir.")

if ticker:
    with st.spinner(f'{ticker} verileri analiz ediliyor...'):
        hist, info, news_data = fetch_data_safe(ticker)
    
    if hist is not None:
        # Fiyat Kartları
        last_price = hist['Close'].iloc[-1]
        prev_price = hist['Close'].iloc[-2]
        change_pct = ((last_price - prev_price) / prev_price) * 100
        color_delta = "normal" if change_pct >= 0 else "inverse"
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Fiyat", f"{last_price:.2f}", f"%{change_pct:.2f}", delta_color=color_delta)
        c2.metric("Sektör", info.get('sector', 'Bilinmiyor'))
        c3.metric("Hedef (Analist)", info.get('targetMeanPrice', '-'))

        # Grafik Alanı (MUM GRAFİK & FVG)
        st.subheader(f"📈 {ticker} - Price Action & FVG")
        st.plotly_chart(plot_ict_chart(hist, ticker), use_container_width=True)
        
        # Haber Alanı
        st.subheader("📡 Piramit Haber Akışı")
        if news_data:
            df_news = pd.DataFrame(news_data).sort_values(by=['Seviye', 'Tarih'], ascending=[True, False])
            
            for _, row in df_news.iterrows():
                css = "bullish" if "YUKARI" in row['Yön'] else "bearish" if "AŞAĞI" in row['Yön'] else "neutral"
                
                st.markdown(f"""
                <div class="metric-card {css}">
                    <div style="display:flex; justify-content:space-between; color:#aaa; font-size:0.8em;">
                        <span>{row['Tarih'].strftime('%d %b %H:%M')}</span>
                        <span>Seviye {row['Seviye']} Kaynak</span>
                    </div>
                    <h4 style="margin:5px 0; color:white;">
                        <a href="{row['Link']}" target="_blank" style="text-decoration:none; color:white;">{row['Başlık']}</a>
                    </h4>
                    <div style="margin-top:5px;">
                        {row['İkon']} <strong>{row['Kaynak']}</strong>: {row['Yön']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Şu an için güncel haber akışı çekilemedi (Yahoo API limiti olabilir).")
            
    else:
        st.error("Veri bulunamadı. Hisse kodunu doğru girdiğinden emin ol (Örn: THYAO.IS, TSLA).")
