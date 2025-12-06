import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import urllib.parse 
from textblob import TextBlob
from datetime import datetime
import streamlit.components.v1 as components

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Patronun Terminali v1.0.3", layout="wide", page_icon="🦅")

# --- VARLIK LİSTELERİ ---
# Not: Varlıkları temsil etmek için kısa listeler kullandım. İsteklerine göre 100/20 varlığa kadar genişletebilirsin.
ASSET_LISTS = {
    "S&P 500 (TOP 10)": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK.B"],
    "NASDAQ (TOP 10)": ["ADBE", "CSCO", "INTC", "QCOM", "AMAT", "MU", "ISRG", "BIIB"],
    "KRİPTO (TOP 5)": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD"],
    "EMTİA & DÖVİZ": ["GC=F", "SI=F", "EURUSD=X", "USDTRY=X", "EURTRY=X", "GBPTRY=X"]
}

# --- CSS TASARIM & FONTLAR ---
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
        color: #263238; font-weight: 600; text-decoration: none; display: block; 
        margin-bottom: 3px; font-size: 0.9rem; line-height: 1.2;
    }
    .news-meta { font-size: 0.65rem; color: #78909c; font-family: 'JetBrains Mono'; margin-top: 5px;}
    .sentiment-badge { 
        font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; font-weight: bold; 
        display: inline-block; margin-left: 5px;
    }

    /* Menü Düzeltmesi */
    .stButton button {
        background-color: #F5F5F5;
        border: 1px solid #E0E0E0;
        text-align: center;
        width: 100%;
        margin-top: 5px;
        font-size: 0.8rem; /* Menü butonları daha küçük */
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
    """TradingView Chart Widget'ını gömer ve DÖVİZ pariteleri için formatı düzeltir."""
    tv_symbol = ticker
    if ".IS" in ticker:
        tv_symbol = f"BIST:{ticker.replace('.IS', '')}"
    # DÖVİZ DÜZELTMESİ (USDTRY=X -> FX_IDC:USDTRY)
    elif "=X" in ticker:
        tv_symbol = f"FX_IDC:{ticker.replace('=X', '')}"
    elif ticker == "GC=F":
        tv_symbol = "TVC:GOLD"
    elif ticker == "SI=F":
        tv_symbol = "COMEX:SI1!" # Gümüş future kodu
    elif ticker == "BTC-USD" or ticker == "ETH-USD" or ticker == "SOL-USD":
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
        
        try:
            pub_date = entry.published_parsed
            dt_object = datetime(*pub_date[:6])
            date_str = dt_object.strftime('%H:%M | %d %b')
        except:
            date_str = "Şimdi"
            
        # Duygu Analizi
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
st.title("🦅 Patronun Terminali v1.0.3")
st.markdown("---")

## Dinamik Menü Barı

menu_cols = st.columns(len(ASSET_LISTS) + 1)
menu_titles = list(ASSET_LISTS.keys())
menu_titles.append("Ekstra")

with st.container():
    col_index = 0
    for title in ASSET_LISTS.keys():
        with menu_cols[col_index]:
            st.markdown(f"**{title}**")
            with st.expander("Listeyi Gör"):
                # Yatay yayılmayı sağlamak için 4 sütun kullanılıyor (daha kompakt)
                list_cols = st.columns(4) 
                for i, symbol in enumerate(ASSET_LISTS[title]):
                    with list_cols[i % 4]: # 4 Sütunlu Döngü
                        if st.button(symbol, key=f"btn_{symbol}", help=f"Grafiği {symbol} ile değiştir"):
                            set_ticker(symbol)
        col_index += 1

    # Ek İşlemler
    with menu_cols[-1]:
        st.markdown(f"**İşlemler**")
        with st.expander("Yenileme & Ayar"):
            if st.button("🔄 Tam Yenile"): 
                st.cache_data.clear()
                st.rerun()

st.markdown("---")

# Arama Çubuğu
current_ticker = st.session_state.ticker if st.session_state.ticker else "AAPL"
ticker_input = st.text_input("Manuel Hisse Kodu", value=current_ticker, help="BIST için .IS, Emtia için =F, Döviz için =X ekle").upper()

# Hisse kodu değiştiyse session state'i güncelle
if ticker_input and ticker_input != st.session_state.ticker:
    st.session_state.ticker = ticker_input
    st.rerun()

# Veri Akışı
info_data = fetch_stock_info(st.session_state.ticker)
news_data = fetch_google_news(st.session_state.ticker)

# --- ANA GÖSTERGE VE GRAFİK ---
if info_data and info_data['price']:
    
    # Metrikler (Stat Cards) - HTML Geri Eklendi
    c1, c2, c3, c4 = st.columns(4)
    delta_class = "delta-pos" if info_data['change_pct'] >= 0 else "delta-neg"
    delta_sign = "+" if info_data['change_pct'] >= 0 else ""
    
    # Fiyat Metriği
    c1.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">{st.session_state.ticker} FİYAT</div>
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
                    # Haber Kartı HTML - EKSİKLER GİDERİLDİ
                    st.markdown(f"""
                    <div class="news-card">
                        <a href="{item['link']}" target="_blank" class="news-title">{item['title']}</a>
                        <div class="news-meta">
                            {item['date']} | {item['source']} 
                            <span class="sentiment-badge" style="background-color: {color}; color: white;">{item['sentiment']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Haber akışı bulunamadı.")
else:
    st.error("Veri bulunamadı. Lütfen hisse kodunu kontrol edin. Örneğin, Döviz için USDTRY=X, BIST için THYAO.IS kullanın.")
