import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import urllib.parse 
from textblob import TextBlob
from datetime import datetime
import streamlit.components.v1 as components

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Patronun Terminali v1.1.0", layout="wide", page_icon="🦅")

# --- VARLIK LİSTELERİ ---
ASSET_LISTS = {
    "SEÇİNİZ...": [], # Varsayılan Boş Seçenek
    "S&P 500 (Top 10)": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK.B"],
    "NASDAQ (Top 10)": ["ADBE", "CSCO", "INTC", "QCOM", "AMAT", "MU", "ISRG", "BIIB"],
    "KRİPTO (Top 5)": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD"],
    "EMTİA & DÖVİZ": ["GC=F", "SI=F", "EURUSD=X", "USDTRY=X", "EURTRY=X", "GBPTRY=X"]
}
# --- YENİ: FİNANCE UZANTILARI İÇİN MAPPING ---
ASSET_TYPE_MAP = {
    "NASDAQ": "NASDAQ", "S&P 500": "NASDAQ", "KRİPTO": "BINANCE", "EMTİA": "TVC", "DÖVİZ": "FX_IDC"
}

# --- CSS TASARIM & FONTLAR ---
st.markdown("""
<style>
    /* ... (CSS Kodları) ... */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stMetricValue, .money-text { font-family: 'JetBrains Mono', monospace !important; }

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

def set_ticker(symbol): 
    st.session_state.ticker = symbol
    st.rerun() 

# --- WIDGET VE VERİ FONKSİYONLARI ---

def render_tradingview_widget(ticker):
    """TradingView Chart Widget'ını gömer ve formatı düzenler."""
    tv_symbol = ticker
    # YENİ: Birden fazla kripto/döviz formatını destekler
    if ".IS" in ticker:
        tv_symbol = f"BIST:{ticker.replace('.IS', '')}"
    elif "=X" in ticker:
        tv_symbol = f"FX_IDC:{ticker.replace('=X', '')}"
    elif ticker in ["BTC-USD", "ETH-USD"]:
        tv_symbol = f"BINANCE:{ticker.replace('-USD', 'USDT')}"
    elif ticker in ["GC=F", "SI=F"]:
        tv_symbol = f"TVC:{ticker.replace('=F', '')}"
    elif "." not in ticker and ":" not in ticker and ticker not in ["MO", "GOOGL", "AGNC"]: # NASDAQ/NYSE varsayımı
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
    """URL Encoding düzeltmesi ile Google News'ten veri çeker."""
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
st.title("🦅 Patronun Terminali v1.1.0")
st.markdown("---")

## Dinamik Filtreleme Modülü (Yeni Yapı)

# 1. Filtre Barı
filter_cols = st.columns(len(ASSET_LISTS))

selected_category = ""

for i, title in enumerate(ASSET_LISTS.keys()):
    with filter_cols[i]:
        # Açılır Menü (Dropdown)
        selected_option = st.selectbox(
            title, 
            ['Seçiniz...'] + ASSET_LISTS[title],
            key=f"filter_box_{title}"
        )
        if selected_option != 'Seçiniz...':
            selected_category = title
            # Ticker'ı otomatik güncelle
            if st.session_state.ticker != selected_option:
                 st.session_state.ticker = selected_option
                 st.rerun()

# 2. Manuel Arama ve Yenileme
col_search, col_refresh = st.columns([5, 1])

with col_search:
    current_ticker = st.session_state.ticker if st.session_state.ticker else "AAPL"
    ticker_input = st.text_input(
        "Manuel Hisse Kodu (veya Seçilen)", 
        value=current_ticker, 
        help="Sembolü girin veya üstteki filtreden seçin."
    ).upper()

# Hisse kodu değiştiyse session state'i güncelle
if ticker_input and ticker_input != st.session_state.ticker:
    st.session_state.ticker = ticker_input
    st.rerun()

with col_refresh:
    st.write("")
    st.write("")
    if st.button("🔄 Tam Yenile"): 
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# Veri Akışı
info_data = fetch_stock_info(st.session_state.ticker)
news_data = fetch_google_news(st.session_state.ticker)

# --- ANA GÖSTERGE VE GRAFİK ---
if info_data and info_data['price']:
    
    # Metrikler (Stat Cards)
    c1, c2, c3, c4 = st.columns(4)
    delta_class = "delta-pos" if info_data['change_pct'] >= 0 else "delta-neg"
    delta_sign = "+" if info_data['change_pct'] >= 0 else ""

    # Fiyat Metriği
    c1.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">Anlık Fiyat</div>
        <div class="stat-value">{info_data['price']:.2f}</div>
        <span class="{delta_class}">{delta_sign}{info_data['change_pct']:.2f}%</span>
    </div>""", unsafe_allow_html=True)
    
    # Hacim Metriği
    c2.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">GÜNLÜK HACİM</div>
        <div class="stat-value">{(info_data['volume'] / 1_000_000):.1f}M</div>
        <span style="color: #616161;">adet</span>
    </div>""", unsafe_allow_html=True)
    
    # Hedef Fiyat Metriği
    target_text = f"{info_data['target_price']:.2f}" if isinstance(info_data['target_price'], (int, float)) else info_data['target_price']
    c3.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">ANALİST HEDEF</div>
        <div class="stat-value">{target_text}</div>
        <span style="color: #616161;">Ort. Fiyat</span>
    </div>""", unsafe_allow_html=True)

    # Sektör Metriği
    c4.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">SEKTÖR / F/K</div>
        <div class="stat-value">{info_data['sector']}</div>
        <span style="color: #616161;">PE: {info_data['pe_ratio']:.1f}</span>
    </div>""", unsafe_allow_html=True)

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
                    # HABER KARTI HTML - EKSİKLER GİDERİLDİ
                    st.markdown(f"""
                    <div class="news-card">
                        <a href="{item['link']}" target="_blank" class="news-title">{item['title']}</a>
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span class="news-meta">{item['date']} | {item['source']} </span>
                            <span class="sentiment-badge" style="background-color: {color}; color: white;">{item['sentiment']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Haber akışı bulunamadı. Lütfen 'Tam Yenile' yapın.")
else:
    st.error("Veri bulunamadı. Lütfen hisse kodunu kontrol edin.")
