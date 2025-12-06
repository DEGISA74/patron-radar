import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import urllib.parse 
from textblob import TextBlob
from datetime import datetime
import streamlit.components.v1 as components

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Patronun Terminali v2.0.1", layout="wide", page_icon="🦅")

# --- VARLIK LİSTELERİ ---
ASSET_GROUPS = {
    "S&P 500 (Top 10)": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK.B"],
    "NASDAQ (Top 10)": ["ADBE", "CSCO", "INTC", "QCOM", "AMAT", "MU", "ISRG", "BIIB"],
    "KRİPTO (Top 5)": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD"],
    "EMTİA & DÖVİZ": ["EURUSD=X", "USDTRY=X", "EURTRY=X", "GBPTRY=X"],
    "TÜRK HİSSE": ["THYAO.IS", "GARAN.IS", "ASELS.IS", "TUPRS.IS"] 
}
ALL_ASSETS = [item for sublist in ASSET_GROUPS.values() for item in sublist]
INITIAL_CATEGORY = "TÜRK HİSSE"

# --- CSS TASARIM ---
st.markdown("""
<style>
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

if 'category' not in st.session_state:
    st.session_state.category = INITIAL_CATEGORY

if 'run_scan' not in st.session_state: 
    st.session_state.run_scan = False

# --- CALLBACK FONKSİYONLARI ---
# Bu fonksiyonlar kullanıcı bir şeye tıkladığında çalışır, böylece loop (döngü) oluşmaz.

def on_category_change():
    """Kategori değiştiğinde o kategorinin ilk hissesini yükle."""
    new_cat = st.session_state.selected_category_key
    st.session_state.category = new_cat
    st.session_state.ticker = ASSET_GROUPS[new_cat][0]

def on_asset_change():
    """Listeden hisse seçildiğinde ticker'ı güncelle."""
    new_asset = st.session_state.selected_asset_key
    st.session_state.ticker = new_asset

def on_manual_input_change():
    """Manuel giriş yapıldığında ticker'ı güncelle."""
    input_val = st.session_state.manual_input_key
    if input_val:
        st.session_state.ticker = input_val.upper()

def on_manual_button_click():
    """Ara butonuna basıldığında ticker'ı güncelle."""
    input_val = st.session_state.manual_input_key
    if input_val:
        st.session_state.ticker = input_val.upper()

# --- WIDGET VE VERİ FONKSİYONLARI ---

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
st.title("🦅 Patronun Terminali v2.0.1")
st.markdown("---")

## Dinamik Menü Barı (V1.2.0 Estetiği + Callback Kontrolü)

current_ticker = st.session_state.ticker
current_category = st.session_state.category

# 1. Filtreleme Alanı
col_cat, col_ass, col_search_in, col_search_btn = st.columns([1.5, 2, 2, 0.7])

with col_cat:
    # Kategori Seçimi
    # Kullanıcı değiştirdiğinde on_category_change çalışır
    st.selectbox(
        "Kategori Seç", 
        list(ASSET_GROUPS.keys()),
        index=list(ASSET_GROUPS.keys()).index(current_category) if current_category in ASSET_GROUPS else 0,
        key="selected_category_key",
        on_change=on_category_change 
    )

with col_ass:
    # Varlık Seçimi
    asset_options = ASSET_GROUPS[current_category]
    
    # Mevcut ticker listede varsa o seçili gelir, yoksa listedeki ilk eleman (0) görsel olarak seçili durur.
    # ÖNEMLİ: Ancak 'on_change' sadece kullanıcı elle değiştirirse tetiklenir.
    # Bu sayede PFE yazılıyken, selectbox AAPL gösterse bile kodu PFE olarak kalır ve değiştirmez.
    try:
        default_index = asset_options.index(current_ticker)
    except ValueError:
        default_index = 0
    
    st.selectbox(
        f"{current_category} Listesi",
        asset_options,
        index=default_index,
        key="selected_asset_key",
        on_change=on_asset_change 
    )

# 2. Manuel Giriş
with col_search_in:
    # Placeholder içine mevcut ticker'ı yazıyoruz ki kullanıcı neye baktığını bilsin
    st.text_input(
        "Manuel Hisse Kodu (Örn: PFE, THYAO.IS)", 
        value="", 
        placeholder=f"Şu anki hisse: {current_ticker}",
        key="manual_input_key",
        on_change=on_manual_input_change # Enter'a basınca çalışır
    )

with col_search_btn:
    st.write("") 
    st.write("")
    st.button("🔎 Ara", on_click=on_manual_button_click)

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

    c1.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">{current_ticker} FİYAT</div>
        <div class="stat-value money-text">{info_data['price']:.2f}</div>
        <div class="stat-delta {delta_class} money-text">{delta_sign}{info_data['change_pct']:.2f}%</div>
    </div>""", unsafe_allow_html=True)
    
    c2.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">GÜNLÜK HACİM</div>
        <div class="stat-value money-text">{(info_data['volume'] / 1_000_000):.1f}M</div>
        <span style="color: #616161;">adet</span>
    </div>""", unsafe_allow_html=True)
    
    target_text = f"{info_data['target_price']:.2f}" if isinstance(info_data['target_price'], (int, float)) else info_data['target_price']
    c3.markdown(f"""
    <div class="stat-box">
        <div class="stat-label">ANALİST HEDEF</div>
        <div class="stat-value money-text">{target_text}</div>
        <span style="color: #616161;">Ort. Fiyat</span>
    </div>""", unsafe_allow_html=True)

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
    
    # --- TARAMA MOTORU (V2.0) ---
    st.markdown("---")
    
    col_refresh = st.columns([6,1])
    with col_refresh[1]:
        if st.button("🔄 Tam Yenile"): 
            st.cache_data.clear()
            st.rerun()

    st.header("🔍 V2.0: Finansal İstihbarat & Tarama Motoru")
    st.info("Bu modül, hisse listelerimizdeki (S&P/NASDAQ Top 100) varlıkları, belirlediğiniz teknik ve duygu kriterlerine göre tarar.")

    with st.expander("Tarama Kriterlerini Ayarla ve Taramayı Başlat"):
        
        col_tech, col_volume, col_sentiment, col_pattern = st.columns(4)
        
        with col_tech:
            st.markdown("**1. Dipten Dönüş & RSI**")
            rsi_min = st.slider("RSI (14) Alt Limit", min_value=20, max_value=50, value=30)
            rsi_max = st.slider("RSI (14) Üst Limit", min_value=50, max_value=80, value=70)
            price_ma = st.selectbox("Fiyat Durumu", ["SMA200 Üstü", "SMA200 Altı", "Fark Etmez"])

        with col_volume:
            st.markdown("**2. Hacim & Likidite**")
            rel_vol = st.slider("Relative Volume (RV) Min.", min_value=0.5, max_value=3.0, value=1.5, step=0.1)
            min_volume = st.number_input("Günlük Ortalama Hacim (USD)", value=1000000)
            
        with col_sentiment:
            st.markdown("**3. Duygu & Haber Akışı**")
            sentiment_change = st.selectbox("Sentiment Değişimi", ["Son 7 gün Artan", "Son 7 gün Azalan", "Nötr Yükselen"])
            news_level = st.selectbox("Haber Kaynak Seviyesi", ["Level 1 (Kritik)", "Level 2 (Analiz)", "Fark Etmez"])

        with col_pattern:
            st.markdown("**4. Konsolidasyon (Built-up)**")
            atr_days = st.slider("ATR Kaç Günün En Düşüğü Olsun?", min_value=10, max_value=90, value=30)
            consolidation_time = st.selectbox("Konsolidasyon Süresi", ["1 Ay (Kısa)", "3 Ay (Orta)", "6 Ay (Uzun)"])
        
        st.markdown("---")
        
        if st.button("🔴 Taramayı Başlat", use_container_width=True, type="primary"):
            st.session_state.run_scan = True
            st.info("Tarama başladı. Lütfen bu modülün V2.1'de aktif olacağını unutmayın. Şimdilik sonuçlar yer tutucudur.")
        
    if st.session_state.get('run_scan', False):
        st.subheader("🔍 Tarama Sonuçları")
        results_df = pd.DataFrame({
            'Hisse': ['AAPL', 'TSLA', 'MSFT'],
            'Kriter': ['RSI Dönüşü', 'Yüksek Hacim', 'Konsolidasyon'],
            'RSI (14)': [32.5, 45.1, 55.0],
            'Relative Volume': [1.8, 2.5, 0.9],
            'Sentiment': ['Artış', 'Nötr', 'Azalış']
        })
        st.dataframe(results_df, use_container_width=True)
        st.session_state.run_scan = False 
        
else:
    st.error("Veri bulunamadı. Lütfen hisse kodunu kontrol edin.")
