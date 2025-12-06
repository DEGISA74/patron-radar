import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
from textblob import TextBlob
from datetime import datetime
import streamlit.components.v1 as components

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Patronun Terminali v0.8", layout="wide", page_icon="🦅")

# --- CSS TASARIM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stMetricValue { font-family: 'JetBrains Mono', monospace !important; }
    
    /* Haber Kartları */
    .news-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
        transition: transform 0.2s;
    }
    .news-card:hover { transform: translateX(5px); border-color: rgba(255, 255, 255, 0.3); }
    .news-title { color: #ECEFF1; font-weight: 600; text-decoration: none; display: block; margin-bottom: 5px; }
    .news-meta { font-size: 0.75rem; color: #90A4AE; font-family: 'JetBrains Mono'; }
    .sentiment-badge { font-size: 0.8rem; padding: 2px 6px; border-radius: 4px; font-weight: bold; }
    
    /* TradingView Widget Arka Planı */
    iframe { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- OTURUM YÖNETİMİ ---
if 'ticker' not in st.session_state:
    st.session_state.ticker = "THYAO.IS"

def set_ticker(symbol): st.session_state.ticker = symbol

# --- YARDIMCI FONKSİYONLAR ---
def get_sentiment(text):
    if not text: return "NÖTR", "#9E9E9E"
    blob = TextBlob(str(text))
    score = blob.sentiment.polarity
    if score > 0.1: return "YUKARI", "#00E676"
    elif score < -0.1: return "AŞAĞI", "#FF1744"
    else: return "NÖTR", "#9E9E9E"

# --- TRADINGVIEW WIDGET ENTEGRASYONU ---
def render_tradingview_widget(ticker):
    # Sembol Dönüşümü (Yahoo -> TradingView)
    tv_symbol = ticker
    if ".IS" in ticker:
        tv_symbol = f"BIST:{ticker.replace('.IS', '')}"
    elif ticker == "GC=F":
        tv_symbol = "TVC:GOLD"
    elif ticker == "BTC-USD":
        tv_symbol = "BINANCE:BTCUSDT"
    elif "USD/TRY" in ticker: # Örnek
        tv_symbol = "FX:USDTRY"
    # Varsayılan (NASDAQ/NYSE varsayımı)
    elif "." not in ticker and ":" not in ticker: 
        tv_symbol = f"NASDAQ:{ticker}"

    # HTML Embed Kodu
    html_code = f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_chart"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
        "width": "100%",
        "height": 600,
        "symbol": "{tv_symbol}",
        "interval": "D",
        "timezone": "Etc/UTC",
        "theme": "dark",
        "style": "1",
        "locale": "tr",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "container_id": "tradingview_chart",
        "studies": [
            "RSI@tv-basicstudies",
            "MASimple@tv-basicstudies"
        ]
      }});
      </script>
    </div>
    """
    components.html(html_code, height=600)

# --- HABER ÇEKME (GOOGLE RSS) ---
@st.cache_data(ttl=300) # 5 dakikada bir yenile
def fetch_google_news(ticker):
    # Arama terimini optimize et
    query = ticker.replace(".IS", " hisse") if ".IS" in ticker else f"{ticker} stock"
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=tr&gl=TR&ceid=TR:tr"
    
    feed = feedparser.parse(rss_url)
    news_items = []
    
    for entry in feed.entries[:10]: # Son 10 haber
        title = entry.title
        link = entry.link
        pub_date = entry.published_parsed
        source = entry.source.title if 'source' in entry else "Google News"
        
        # Tarih formatlama
        try:
            dt_object = datetime(*pub_date[:6])
            date_str = dt_object.strftime('%H:%M | %d %b')
        except:
            date_str = "Şimdi"
            
        sent_text, sent_color = get_sentiment(title)
        
        news_items.append({
            'title': title,
            'link': link,
            'date': date_str,
            'source': source,
            'sentiment': sent_text,
            'color': sent_color
        })
    return news_items

# --- ARAYÜZ ---
st.title("🦅 Patronun Terminali v0.8")

# Hızlı Erişim Butonları
cols = st.columns([1,1,1,1,1,2])
if cols[0].button("🇹🇷 THYAO"): set_ticker("THYAO.IS")
if cols[1].button("🇹🇷 GARAN"): set_ticker("GARAN.IS")
if cols[2].button("🇺🇸 AAPL"): set_ticker("AAPL")
if cols[3].button("🥇 GOLD"): set_ticker("GC=F")
if cols[4].button("₿ BTC"): set_ticker("BTC-USD")
if cols[5].button("🔄 Yenile"): st.cache_data.clear(); st.rerun()

# Arama
ticker_input = st.text_input("Hisse Kodu Girin", value=st.session_state.ticker).upper()
if ticker_input != st.session_state.ticker: st.session_state.ticker = ticker_input

current_ticker = st.session_state.ticker

# Verileri Çek
news_data = fetch_google_news(current_ticker)
try:
    stock_info = yf.Ticker(current_ticker).info
    price = stock_info.get('currentPrice') or stock_info.get('regularMarketPreviousClose')
except:
    price = None

# Üst Bilgi Paneli
if price:
    c1, c2, c3 = st.columns(3)
    c1.metric("Son Fiyat", f"{price}")
    c2.metric("Sektör", stock_info.get('sector', '-'))
    c3.metric("Hedef", stock_info.get('targetMeanPrice', '-'))

st.write("")

# --- ANA EKRAN: GRAFİK VE HABERLER ---
col_graph, col_news = st.columns([3, 1.2])

with col_graph:
    st.subheader("Global Piyasa Grafiği (TradingView)")
    # Burada TradingView Widget'ı çağırıyoruz
    render_tradingview_widget(current_ticker)
    st.caption("ℹ️ Not: Lorentzian Classification gibi özel scriptler widget'larda çalışmaz, ancak çizim araçları aktiftir.")

with col_news:
    st.subheader("Küresel Haber Akışı")
    with st.container(height=600):
        if news_data:
            for item in news_data:
                st.markdown(f"""
                <div class="news-card">
                    <a href="{item['link']}" target="_blank" class="news-title">{item['title']}</a>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                        <span class="news-meta">{item['source']} • {item['date']}</span>
                        <span class="sentiment-badge" style="color:{item['color']}; border:1px solid {item['color']}">{item['sentiment']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("Haber akışı bulunamadı.")
