import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import urllib.parse 
from textblob import TextBlob
from datetime import datetime
import streamlit.components.v1 as components

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Patronun Terminali v1.2.1", layout="wide", page_icon="🦅")

# --- VARLIK LİSTELERİ ---
ASSET_GROUPS = {
    "S&P 500 (Top 10)": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK.B"],
    "NASDAQ (Top 10)": ["ADBE", "CSCO", "INTC", "QCOM", "AMAT", "MU", "ISRG", "BIIB"],
    "KRİPTO (Top 5)": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD"],
    "EMTİA & DÖVİZ": ["EURUSD=X", "USDTRY=X", "EURTRY=X", "GBPTRY=X"]
}

# --- CSS TASARIM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stMetricValue, .money-text { font-family: 'JetBrains Mono', monospace !important; }

    /* Custom Stat Cards */
    .stat-box {
        background: #FFFFFF; border: 1px solid #CFD8DC; border-radius: 10px; padding: 15px; text-align: center; margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .stat-label { font-size: 0.8rem; color: #546E7A; text-transform: uppercase; letter-spacing: 1px; }
    .stat-value { font-size: 1.5rem; font-weight: 700; color: #263238; margin: 5px 0; }
    .delta-pos { color: #00C853; }
    .delta-neg { color: #D50000; }

    /* Haber Kartları */
    .news-card {
        background: #FFFFFF; border: 1px solid #CFD8DC; padding: 10px; border-radius: 8px; margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .news-title { 
        color: #263238; font-weight: 600; display: block; 
        margin-bottom: 3px; font-size: 0.9rem; line-height: 1.2;
    }
    .news-meta { font-size: 0.65rem; color: #78909c; font-family: 'JetBrains Mono'; margin-top: 5px;}
    
    /* Sidebar Butonları */
    .stButton button {
        background-color: #F5F5F5; border: 1px solid #E0E0E0;
        text-align: center; width: 100%; margin-top: 5px; font-size: 0.8rem;
    }
    h1 { padding-top: 0px; }
</style>
""", unsafe_allow_html=True)

# --- OTURUM YÖNETİMİ ---
if 'ticker' not in st.session_state:
    st.session_state.ticker = "THYAO.IS"

if 'manual_input_value' not in st.session_state:
    st.session_state.manual_input_value = st.session_state.ticker

def set_ticker(symbol): 
    st.session_state.ticker = symbol
    st.rerun() 

# --- WIDGET VE VERİ FONKSİYONLARI ---

def render_tradingview_widget(ticker):
    tv_symbol = ticker
    if ".IS" in ticker:
        tv_symbol = f"BIST:{ticker.replace('.IS', '')}"
    elif "=X" in ticker: # Döviz pariteleri
        tv_symbol = f"FX_IDC:{ticker.replace('=X', '')}"
    elif ticker in ["BTC-USD", "ETH-USD"]:
        tv_symbol = f"BINANCE:{ticker.replace('-USD', 'USDT')}"
    elif "." not in ticker and ":" not in ticker: 
        tv_symbol = f"NASDAQ:{ticker}"

    html_code = f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_chart" style="border-radius: 10px;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
        "width": "100%", "height": 600, "symbol": "{tv_symbol}", "interval": "D", "timezone": "Etc/UTC",
        "theme": "light", "style": "1", "locale": "tr", "toolbar_bg": "#f0f3f6", "enable_publishing": false,
        "allow_symbol_change": true, "container_id": "tradingview_chart"
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
        
        try: pub_date = entry.published_parsed; dt_object = datetime(*pub_date[:6])
        except: dt_object = datetime.now()
        date_str = dt_object.strftime('%H:%M | %d %b')
            
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
st.title("🦅 Patronun Terminali v1.2.1")

# --- SIDEBAR: MANUEL GİRİŞ & Varlık Seçimi ---
with st.sidebar:
    st.header("Manuel Ticker & İşlemler")
    
    # 1. MANUEL GİRİŞ (Gecikmeli Arama)
    # Gecikmeli giriş için st.session_state kullanılır.
    manual_input = st.text_input(
        "Hisse Kodu (Ara butonu gerekli)", 
        value=st.session_state.manual_input_value
    ).upper()

    if manual_input != st.session_state.manual_input_value:
        st.session_state.manual_input_value = manual_input
    
    if st.button("🔎 Ara & Yükle"):
        set_ticker(st.session_state.manual_input_value)

    st.markdown("---")
    st.header("Varlık Menüsü")
    
    # 2. Varlık Grupları (Kompakt Açılır Menüler)
    for title, symbols in ASSET_GROUPS.items():
        with st.expander(f"**{title}**"):
            # Daha kompakt görünüm için 3 sütun
            list_cols = st.columns(3)
            for i, symbol in enumerate(symbols):
                with list_cols[i % 3]: 
                    if st.button(symbol, key=f"btn_{symbol}"):
                        set_ticker(symbol)

    st.markdown("---")
    if st.button("🔄 Tam Yenile"): 
        st.cache_data.clear()
        st.rerun()

# --- ANA GÖSTERGE VE GRAFİK ---
current_ticker = st.session_state.ticker
info_data = fetch_stock_info(current_ticker)
news_data = fetch_google_news(current_ticker)

if info_data and info_data['price']:
    
    # Metrikler (Stat Cards)
    c1, c2, c3, c4 = st.columns(4)
    delta_class = "delta-pos" if info_data['change_pct'] >= 0 else "delta-neg"
    delta_sign = "+" if info_data['change_pct'] >= 0 else ""

    c1.markdown(f"""...""", unsafe_allow_html=True)
    c2.markdown(f"""...""", unsafe_allow_html=True)
    c3.markdown(f"""...""", unsafe_allow_html=True)
    c4.markdown(f"""...""", unsafe_allow_html=True)

    st.write("")

    # GRAFİK ve HABERLER (Yan Yana)
    col_chart, col_news = st.columns([3, 1.2])
    
    with col_chart:
        st.subheader(f"📈 {current_ticker} Trading Terminali")
        render_tradingview_widget(current_ticker)
    
    with col_news:
        st.subheader("📡 Küresel Haber Akışı") 
        with st.container(height=600):
            if news_data:
                for item in news_data:
                    color = item['color']
                    st.markdown(f"""
                    <div class="news-card" style="border-left-color: {color};">
                        <a href="{item['link']}" target="_blank" class="news-title">{item['title']}</a>
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span class="news-meta">{item['date']} | {item['source']} </span>
                            <span class="sentiment-badge" style="color:{color}; border:1px solid {color}">{item['sentiment']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Haber akışı bulunamadı.")
else:
    st.error("Veri bulunamadı. Lütfen hisse kodunu kontrol edin.")
