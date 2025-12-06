import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import urllib.parse 
from textblob import TextBlob
from datetime import datetime
import streamlit.components.v1 as components

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Patronun Terminali v1.0", layout="wide", page_icon="🦅")

# --- VARLIK LİSTELERİ ---
# Not: Varlıkları temsil etmek için kısa listeler kullandım. İsteklerine göre 100/20 varlığa kadar genişletebilirsin.
ASSET_LISTS = {
    "S&P 500 (TOP 10)": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK.B"],
    "NASDAQ (TOP 10)": ["ADBE", "CSCO", "INTC", "QCOM", "AMAT", "MU", "ISRG", "BIIB"],
    "KRİPTO (TOP 5)": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD"],
    "EMTİA & DÖVİZ": ["GC=F", "SI=F", "EURUSD=X", "USDTRY=X", "EURTRY=X", "GBPTRY=X"]
}

# --- CSS TASARIM & FONTLAR ---
# (Önceki v0.9.2 CSS'i temiz ve stabil olduğu için korundu, sadece renk kodları light mod uyumu için düzeltildi)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stMetricValue, .money-text { font-family: 'JetBrains Mono', monospace !important; }

    /* Custom Stat Cards */
    .stat-box {
        background: #FFFFFF;
        border: 1px solid #CFD8DC;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        margin-bottom: 15px;
    }
    .stat-label { font-size: 0.8rem; color: #546E7A; text-transform: uppercase; letter-spacing: 1px; }
    .stat-value { font-size: 1.5rem; font-weight: 700; color: #263238; margin: 5px 0; }
    .delta-pos { color: #00C853; }
    .delta-neg { color: #D50000; }

    /* Haber Kartları */
    .news-card {
        background: #FFFFFF;
        border: 1px solid #CFD8DC;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .news-title { color: #263238; font-weight: 600; text-decoration: none; display: block; margin-bottom: 5px; }
    .news-meta { font-size: 0.75rem; color: #78909c; font-family: 'JetBrains Mono'; }
    .sentiment-badge { font-size: 0.8rem; padding: 2px 6px; border-radius: 4px; font-weight: bold; }
    
    /* Navigasyon Butonları (Hiyerarşik Yapı için küçültüldü) */
    .asset-button button {
        width: 100%;
        margin-bottom: 5px;
        background-color: #F5F5F5;
        border: 1px solid #E0E0E0;
        text-align: left;
        padding-left: 10px;
    }
    /* Streamlit varsayılan başlığını gizle */
    h1 { padding-top: 0px; }
</style>
""", unsafe_allow_html=True)

# --- OTURUM YÖNETİMİ ---
if 'ticker' not in st.session_state:
    st.session_state.ticker = "THYAO.IS"

def set_ticker(symbol): 
    st.session_state.ticker = symbol
    st.rerun() 

# --- FONKSİYONLAR (Aynı Kaldı) ---

def render_tradingview_widget(ticker):
    tv_symbol = ticker
    if ".IS" in ticker:
        tv_symbol = f"BIST:{ticker.replace('.IS', '')}"
    elif ticker == "GC=F":
        tv_symbol = "TVC:GOLD"
    elif ticker == "BTC-USD":
        tv_symbol = "BINANCE:BTCUSDT"
    elif "." not in ticker and ":" not in ticker: 
        tv_symbol = f"NASDAQ:{ticker}"

    html_code = f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_chart" style="border-radius: 10px;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
        "width": "100%",
        "height": 600,
        "symbol": "{tv_symbol}",
        "interval": "D",
        "timezone": "Etc/UTC",
        "theme": "light", 
        "style": "1",
        "locale": "tr",
        "toolbar_bg": "#f0f3f6",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "container_id": "tradingview_chart"
      }});
      </script>
    </div>
    """
    components.html(html_code, height=600)

@st.cache_data(ttl=300) 
def fetch_google_news(ticker):
    query = ticker.replace(".IS", " hisse") if ".IS" in ticker else f"{ticker} stock"
    encoded_query = urllib.parse.quote_plus(query) 
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=tr&gl=TR&ceid=TR:tr"
    
    feed = feedparser.parse(rss_url)
    news_items = []
    
    for entry in feed.entries[:15]: 
        title = entry.title
        link = entry.link
        source = entry.source.title if 'source' in entry else "Global News"
        
        try:
            pub_date = entry.published_parsed
            dt_object = datetime(*pub_date[:6])
            date_str = dt_object.strftime('%H:%M | %d %b')
        except:
            date_str = "Şimdi"
            
        blob = TextBlob(title)
        score = blob.sentiment.polarity
        if score > 0.1: sent_text, sent_color = "YUKARI", "#00C853"
        elif score < -0.1: sent_text, sent_color = "AŞAĞI", "#D50000"
        else: sent_text, sent_color = "NÖTR", "#616161"

        news_items.append({
            'title': title, 'link': link, 'date': date_str, 'source': source,
            'sentiment': sent_text, 'color': sent_color
        })
    return news_items

@st.cache_data(ttl=600)
def fetch_stock_info(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('ask')
        prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
        
        if current_price and prev_close:
            change_pct = ((current_price - prev_close) / prev_close) * 100
        else:
            change_pct = 0
            
        return {
            'price': current_price, 'change_pct': change_pct, 'volume': info.get('volume', 0),
            'sector': info.get('sector', '-'), 'target_price': info.get('targetMeanPrice', '-'),
            'pe_ratio': info.get('trailingPE', '-')
        }
    except:
        return None

# --- ARAYÜZ ---
st.title("🦅 Patronun Terminali")
st.markdown("---")

## Dinamik Menü Barı

menu_cols = st.columns(len(ASSET_LISTS) + 1)
menu_titles = list(ASSET_LISTS.keys())
menu_titles.append("EK İŞLEMLER") # Yenileme butonu için

# Menü Başlıkları ve Genişletilebilir Paneller
with st.container():
    col_index = 0
    for title in ASSET_LISTS.keys():
        with menu_cols[col_index]:
            st.subheader(title)
            # Genişletilebilir liste (Collapsible list)
            with st.expander("Listeyi Gör"):
                for symbol in ASSET_LISTS[title]:
                    # Tekrar kontrol: set_ticker'ı çağıran her şey ayrı bir Python komutu olmalı.
                    # CSS class'ı eklendi.
                    if st.button(symbol, key=f"btn_{symbol}", help=f"Grafiği {symbol} ile değiştir"):
                        set_ticker(symbol)
        col_index += 1

    # Ek İşlemler
    with menu_cols[-1]:
        st.subheader("İşlemler")
        with st.expander("Yenileme & Ayar"):
            if st.button("🔄 Tam Yenile"): 
                st.cache_data.clear()
                st.rerun()

st.markdown("---")

# Arama Çubuğu (Menünün Altına)
ticker_input = st.text_input("Manuel Hisse Kodu", value=st.session_state.ticker, help="BIST için .IS, Emtia için =F, Kripto için -USD ekle").upper()
if ticker_input != st.session_state.ticker: st.session_state.ticker = ticker_input

# Veri Akışı
info_data = fetch_stock_info(st.session_state.ticker)
news_data = fetch_google_news(st.session_state.ticker)

# --- ANA GÖSTERGE VE GRAFİK ---
if info_data and info_data['price']:
    # Metrikler (Stat Cards)
    c1, c2, c3, c4 = st.columns(4)
    delta_class = "delta-pos" if info_data['change_pct'] >= 0 else "delta-neg"
    delta_sign = "+" if info_data['change_pct'] >= 0 else ""

    c1.markdown(f"""... [Stat Box HTML] ...""", unsafe_allow_html=True)
    c2.markdown(f"""... [Stat Box HTML] ...""", unsafe_allow_html=True)
    c3.markdown(f"""... [Stat Box HTML] ...""", unsafe_allow_html=True)
    c4.markdown(f"""... [Stat Box HTML] ...""", unsafe_allow_html=True)
    
    st.write("")

    # GRAFİK ve HABERLER (Yan Yana)
    col_chart, col_news = st.columns([3, 1.2])
    
    with col_chart:
        st.subheader(f"📈 {st.session_state.ticker} Trading Terminali")
        render_tradingview_widget(st.session_state.ticker)
    
    with col_news:
        st.subheader("📡 Küresel Haber Akışı")
        with st.container(height=600):
            if news_data:
                for item in news_data:
                    color = item['color']
                    st.markdown(f"""... [News Card HTML] ...""", unsafe_allow_html=True)
            else:
                st.info("Haber akışı bulunamadı.")
else:
    st.error("Veri bulunamadı. Lütfen hisse kodunu kontrol edin.")
