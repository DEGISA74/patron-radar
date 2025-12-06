import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import urllib.parse 
from textblob import TextBlob
from datetime import datetime
import streamlit.components.v1 as components

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Patronun Terminali v1.5.0 (Manuel Giriş Öncelikli)", layout="wide", page_icon="🦅")

# --- VARLIK LİSTELERİ ---
ASSET_GROUPS = {
    "S&P 500 (Top 10)": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK.B"],
    "NASDAQ (Top 10)": ["ADBE", "CSCO", "INTC", "QCOM", "AMAT", "MU", "ISRG", "BIIB"],
    "KRİPTO (Top 5)": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD"],
    "EMTİA & DÖVİZ": ["EURUSD=X", "USDTRY=X", "EURTRY=X", "GBPTRY=X"],
    "TÜRK HİSSE": ["THYAO.IS", "GARAN.IS", "ASELS.IS", "TUPRS.IS"] 
}
ALL_ASSETS = [item for sublist in ASSET_GROUPS.values() for item in sublist]
INITIAL_CATEGORY = list(ASSET_GROUPS.keys())[0] # Varsayılan ilk kategori

# --- CSS TASARIM --- (Aynı Kaldı)
st.markdown("""
<style>
    /* ... (CSS Kodları V1.4.0 ile aynıdır) ... */
</style>
""", unsafe_allow_html=True) 

# --- OTURUM YÖNETİMİ ---
if 'ticker' not in st.session_state:
    st.session_state.ticker = "THYAO.IS"

if 'manual_input_value' not in st.session_state:
    st.session_state.manual_input_value = st.session_state.ticker

if 'category' not in st.session_state:
    st.session_state.category = INITIAL_CATEGORY

# Ticker değiştiğinde manuel input'u da güncelleme
def update_manual_input(new_ticker):
    st.session_state.manual_input_value = new_ticker
    st.session_state.ticker = new_ticker
    st.rerun()

# MANUEL GİRİŞ İÇİN ÖZEL CALLBACK
def handle_manual_search():
    # Manuel arama yapıldığında, kategori seçimini sıfırla
    if st.session_state.manual_ticker_input != st.session_state.ticker:
        st.session_state.category = INITIAL_CATEGORY
        st.session_state.ticker = st.session_state.manual_ticker_input
        st.session_state.manual_input_value = st.session_state.manual_ticker_input
        st.rerun()

# --- WIDGET VE VERİ FONKSİYONLARI (Aynı Kaldı) ---

def render_tradingview_widget(ticker):
    tv_symbol = ticker
    if ".IS" in ticker:
        tv_symbol = f"BIST:{ticker.replace('.IS', '')}"
    elif "=X" in ticker: 
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
st.title("🦅 Patronun Terminali v1.5.0 (V1.2.0 Geri Dönüş)")
st.markdown("---")

## Dinamik Menü Barı (HORIZONTAL DROPDOWNS)

category_list = list(ASSET_GROUPS.keys())
current_ticker = st.session_state.ticker

# Ticker'ın listede olup olmadığını kontrol et
is_in_list = current_ticker in ALL_ASSETS

# Ticker listede değilse, kategoriyi varsayılan ilk kategoriye sıfırla
if not is_in_list:
    current_category = INITIAL_CATEGORY
else:
    # Ticker listedeyse, kategori eşleştirmesi yap
    current_category = next((cat for cat, assets in ASSET_GROUPS.items() if current_ticker in assets), INITIAL_CATEGORY)


# 1. Filtreleme Alanı
col_cat, col_ass, col_search_in, col_search_btn = st.columns([1.5, 2, 2, 0.7])

with col_cat:
    # Kategori Seçimi
    selected_category = st.selectbox(
        "Kategori Seç", 
        category_list,
        index=category_list.index(current_category) 
    )

    # Kategori Değişimi Kontrolü
    if selected_category != st.session_state.category:
        st.session_state.category = selected_category
        # Kategori değişirse listedeki ilk elemanı seç
        st.session_state.manual_input_value = ASSET_GROUPS[selected_category][0]
        set_ticker(ASSET_GROUPS[selected_category][0])


# 2. Varlık Seçimi (Kategoriye Bağımlı)
asset_options = ASSET_GROUPS.get(st.session_state.category, [current_ticker])

with col_ass:
    # Eğer mevcut ticker, gösterilen listede yoksa, default index 0 olur
    default_index = asset_options.index(current_ticker) if current_ticker in asset_options else 0
    
    selected_asset = st.selectbox(
        f"{st.session_state.category} Listesi",
        asset_options,
        index=default_index
    )
    
    # EĞER TIKLANDIYSA, TİCKERI DEĞİŞTİR
    if selected_asset != current_ticker:
        update_manual_input(selected_asset)


# 3. Manuel Giriş (Gecikmeli Arama Kontrolü)
with col_search_in:
    manual_input = st.text_input(
        "Manuel Hisse Kodu (Ara Butonu gerekli)", 
        value=st.session_state.manual_input_value,
        key="manual_ticker_input" # Callback için key
    ).upper()


with col_search_btn:
    st.write("") 
    st.write("")
    if st.button("🔎 Ara"):
        handle_manual_search() # CALLBACK'i çalıştır

st.markdown("---")

# Veri Akışı
info_data = fetch_stock_info(current_ticker)
news_data = fetch_google_news(current_ticker)

# --- ANA GÖSTERGE VE GRAFİK ---
if info_data and info_data['price']:
    
    # Metrikler (Stat Cards)
    c1, c2, c3, c4 = st.columns(4)
    delta_class = "delta-pos" if info_data['change_pct'] >= 0 else "delta-neg"
    delta_sign = "+" if info_data['change_pct'] >= 0 else ""

    # Fiyat Metriği
    c1.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">{current_ticker} FİYAT</div>
        <div class="stat-value money-text">{info_data['price']:.2f}</div>
        <div class="stat-delta {delta_class} money-text">{delta_sign}{info_data['change_pct']:.2f}%</div>
    </div>""", unsafe_allow_html=True)
    
    # Hacim Metriği
    c2.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">GÜNLÜK HACİM</div>
        <div class="stat-value money-text">{(info_data['volume'] / 1_000_000):.1f}M</div>
        <span style="color: #616161;">adet</span>
    </div>""", unsafe_allow_html=True)
    
    # Hedef Fiyat Metriği
    target_text = f"{info_data['target_price']:.2f}" if isinstance(info_data['target_price'], (int, float)) else info_data['target_price']
    c3.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">ANALİST HEDEF</div>
        <div class="stat-value money-text">{target_text}</div>
        <span style="color: #616161;">Ort. Fiyat</span>
    </div>""", unsafe_allow_html=True)

    # Sektör Metriği
    pe_text = f"{info_data['pe_ratio']:.1f}" if isinstance(info_data['pe_ratio'], (int, float)) else info_data['pe_ratio']
    c4.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">SEKTÖR / F/K</div>
        <div class="stat-value">{info_data['sector']}</div>
        <span style="color: #616161;">PE: {pe_text}</span>
    </div>""", unsafe_allow_html=True)

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
