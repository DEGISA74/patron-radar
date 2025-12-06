import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import urllib.parse 
from textblob import TextBlob
from datetime import datetime
import streamlit.components.v1 as components

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Patronun Terminali v0.9", layout="wide", page_icon="🦅")

# --- CSS TASARIM & FONTLAR ---
st.markdown("""
<style>
    /* Fontlar */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stMetricValue, .money-text { font-family: 'JetBrains Mono', monospace !important; }

    /* Custom Stat Cards (Glassmorphism) */
    .stat-box {
        background: linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        margin-bottom: 15px;
    }
    .stat-label { font-size: 0.8rem; color: #8b9bb4; text-transform: uppercase; letter-spacing: 1px; }
    .stat-value { font-size: 1.5rem; font-weight: 700; color: #e2e8f0; margin: 5px 0; }
    .delta-pos { color: #00E676; }
    .delta-neg { color: #FF1744; }

    /* Haber Kartları */
    .news-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .news-title { color: #ECEFF1; font-weight: 600; text-decoration: none; display: block; margin-bottom: 5px; }
    .news-meta { font-size: 0.75rem; color: #90A4AE; font-family: 'JetBrains Mono'; }
    .sentiment-badge { font-size: 0.8rem; padding: 2px 6px; border-radius: 4px; font-weight: bold; }
    
    /* TradingView Arkaplanı */
    iframe { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- OTURUM YÖNETİMİ ---
if 'ticker' not in st.session_state:
    st.session_state.ticker = "THYAO.IS"

def set_ticker(symbol): 
    st.session_state.ticker = symbol
    st.rerun() # Sayfa yenileme komutu düzeltildi

# --- WIDGET VE VERİ FONKSİYONLARI ---

def render_tradingview_widget(ticker):
    """TradingView Chart Widget'ını gömer."""
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
        "theme": "dark",
        "style": "1",
        "locale": "tr",
        "toolbar_bg": "#1e2329",
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
    encoded_query = urllib.parse.quote_plus(query) # HATA DÜZELTME: InvalidURL Fix
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
        if not title: continue
        blob = TextBlob(title)
        score = blob.sentiment.polarity
        if score > 0.1: sent_text, sent_color = "YUKARI", "#00E676"
        elif score < -0.1: sent_text, sent_color = "AŞAĞI", "#FF1744"
        else: sent_text, sent_color = "NÖTR", "#9E9E9E"

        news_items.append({
            'title': title, 'link': link, 'date': date_str, 'source': source,
            'sentiment': sent_text, 'color': sent_color
        })
    return news_items

@st.cache_data(ttl=600)
def fetch_stock_info(ticker):
    """Hisse fiyatı ve info'yu çeker."""
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
            'price': current_price,
            'change_pct': change_pct,
            'volume': info.get('volume', 0),
            'sector': info.get('sector', '-'),
            'target_price': info.get('targetMeanPrice', '-'),
            'pe_ratio': info.get('trailingPE', '-')
        }
    except:
        return None

# --- ARAYÜZ ---
st.title("🦅 Patronun Terminali v0.9")

# Hızlı Erişim Butonları
col_btns = st.columns([1,1,1,1,1,2])
with col_btns[0]: if st.button("🇹🇷 THYAO"): set_ticker("THYAO.IS")
with col_btns[1]: if st.button("🇺🇸 AAPL"): set_ticker("AAPL")
with col_btns[2]: if st.button("🥇 GOLD"): set_ticker("GC=F")
with col_btns[3]: if st.button("₿ BTC"): set_ticker("BTC-USD")
with col_btns[4]: if st.button("🇺🇸 TSLA"): set_ticker("TSLA")
with col_btns[5]: 
    if st.button("🔄 Tam Yenile"): 
        st.cache_data.clear()
        st.rerun()

# Arama
ticker_input = st.text_input("Hisse Kodu (Manuel Giriş)", value=st.session_state.ticker).upper()
if ticker_input != st.session_state.ticker: st.session_state.ticker = ticker_input

# Veri Akışı
info_data = fetch_stock_info(st.session_state.ticker)
news_data = fetch_google_news(st.session_state.ticker)

if info_data and info_data['price']:
    # --- ÖZEL METRİK KARTLARI ---
    c1, c2, c3, c4 = st.columns(4)
    delta_class = "delta-pos" if info_data['change_pct'] >= 0 else "delta-neg"
    delta_sign = "+" if info_data['change_pct'] >= 0 else ""

    c1.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">Anlık Fiyat</div>
        <div class="stat-value money-text">{info_data['price']:.2f}</div>
        <div class="stat-delta {delta_class} money-text">{delta_sign}{info_data['change_pct']:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)
    
    c2.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">Hacim</div>
        <div class="stat-value money-text">{info_data['volume']/1000000:.1f}M</div>
        <div class="stat-delta" style="color:#8b9bb4">GÜNLÜK</div>
    </div>
    """, unsafe_allow_html=True)

    c3.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">Hedef Fiyat</div>
        <div class="stat-value money-text">{info_data['target_price']}</div>
        <div class="stat-delta" style="color:#29B6F6">ANALİST ORT.</div>
    </div>
    """, unsafe_allow_html=True)

    c4.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">Sektör</div>
        <div class="stat-value" style="font-size:1.1rem; margin-top:10px;">{info_data['sector']}</div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    # --- GRAFİK ve HABERLER (Yan Yana) ---
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
                    st.markdown(f"""
                    <div class="news-card" style="border-left-color: {color};">
                        <a href="{item['link']}" target="_blank" class="news-title">{item['title']}</a>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                            <span class="news-meta">{item['source']} • {item['date']}</span>
                            <span class="sentiment-badge" style="color:{color}; border:1px solid {color}">{item['sentiment']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Haber akışı bulunamadı. Lütfen 'Tam Yenile' yapın.")
else:
    st.error("Veri bulunamadı. Lütfen hisse kodunu kontrol edin veya yenileme yapın.")
