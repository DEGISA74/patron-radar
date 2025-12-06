import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import urllib.parse 
from textblob import TextBlob
from datetime import datetime
import streamlit.components.v1 as components
import time

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Patronun Terminali v2.3.0", layout="wide", page_icon="🦅")

# --- VARLIK LİSTELERİ (GENİŞ LİSTE GERİ GELDİ) ---
ASSET_GROUPS = {
    "TÜRK HİSSE (BIST 30)": [
        "THYAO.IS", "GARAN.IS", "ASELS.IS", "TUPRS.IS", "KCHOL.IS", "AKBNK.IS", "ISCTR.IS", "SISE.IS", 
        "BIMAS.IS", "EREGL.IS", "SAHOL.IS", "YKBNK.IS", "FROTO.IS", "KONTR.IS", "HEKTS.IS", "PETKM.IS", 
        "TOASO.IS", "PGSUS.IS", "ENKAI.IS", "ALARK.IS", "ODAS.IS", "EKGYO.IS", "KOZAL.IS", "SASA.IS"
    ],
    "S&P 500 (TOP 100)": [
        "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "BRK.B", "TSLA", "AVGO", 
        "JPM", "LLY", "UNH", "V", "XOM", "MA", "JNJ", "HD", "PG", "COST", 
        "ABBV", "MRK", "CRM", "CVX", "BAC", "AMD", "WMT", "NFLX", "ACN", "PEP", 
        "KO", "LIN", "TMO", "DIS", "ADBE", "WFC", "MCD", "CSCO", "QCOM", "CAT", 
        "VZ", "INTU", "IBM", "GE", "AMAT", "NOW", "PFE", "CMCSA", "SPGI", "UNP", 
        "TXN", "ISRG", "UBER", "PM", "LOW", "HON", "AMGN", "RTX", "SYK", "GS", 
        "BLK", "ELV", "PLD", "BKNG", "NEE", "T", "MS", "PGR", "ETN", "C", 
        "TJX", "UPS", "MDT", "BSX", "VRTX", "CHTR", "AXP", "CI", "DE", "CB", 
        "LRCX", "REGN", "SCHW", "ADP", "MMC", "KLAC", "MU", "PANW", "FI", "BX",
        "GILD", "ADI", "SNPS", "ZTS", "CRWD", "WM", "MO", "USB", "SO", "ICE"
    ],
    "NASDAQ 100 (TOP 100)": [
        "MSFT", "AAPL", "NVDA", "AMZN", "AVGO", "META", "TSLA", "GOOGL", "GOOG", "COST", 
        "AMD", "NFLX", "PEP", "LIN", "ADBE", "TMUS", "CSCO", "QCOM", "INTU", "AMAT", 
        "TXN", "ISRG", "CMCSA", "AMGN", "HON", "INTC", "BKNG", "VRTX", "LRCX", "MU", 
        "PANW", "ADP", "REGN", "ADI", "GILD", "KLAC", "MDLZ", "SNPS", "CRWD", "MELI", 
        "CSX", "CDNS", "PYPL", "MAR", "ORLY", "ASML", "NXPI", "CTAS", "MNST", "FTR",
        "ROP", "PCAR", "WDAY", "AEP", "LULU", "ADSK", "KDP", "DXCM", "PAYX", "ROST", 
        "IDXX", "MRVL", "MCHP", "ODFL", "BIIB", "EXC", "FAST", "CPRT", "SBUX", "CTSH", 
        "KHC", "BKR", "VRSK", "EA", "CSGP", "XEL", "CEG", "DDOG", "GEHC", "FANG", 
        "ON", "WBD", "TEAM", "ANSS", "TTD", "ALGN", "ILMN", "DLTR", "EBAY", "WBA", 
        "ZM", "SIRI", "ENPH", "LCID", "RIVN", "ZS", "GFS", "SPLK", "ABNB", "ARM"
    ],
    "KRİPTO (TOP 20)": [
        "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", "DOGE-USD", "AVAX-USD", 
        "TRX-USD", "LINK-USD", "DOT-USD", "MATIC-USD", "LTC-USD", "SHIB-USD", "BCH-USD", "UNI-USD", 
        "ATOM-USD", "XLM-USD", "ETC-USD", "FIL-USD"
    ],
    "EMTİA & DÖVİZ": ["EURUSD=X", "USDTRY=X", "EURTRY=X", "GBPTRY=X"]
}
ALL_ASSETS = [item for sublist in ASSET_GROUPS.values() for item in sublist]
INITIAL_CATEGORY = "TÜRK HİSSE (BIST 30)"

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

if 'scan_results' not in st.session_state:
    st.session_state.scan_results = None

# --- CALLBACK FONKSİYONLARI ---
def on_category_change():
    new_cat = st.session_state.selected_category_key
    st.session_state.category = new_cat
    st.session_state.ticker = ASSET_GROUPS[new_cat][0]

def on_asset_change():
    new_asset = st.session_state.selected_asset_key
    st.session_state.ticker = new_asset

def on_manual_button_click():
    input_val = st.session_state.manual_input_key
    if input_val:
        st.session_state.ticker = input_val.upper()

# --- TEKNİK ANALİZ MOTORU ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def run_scanner(asset_list, rsi_min, rsi_max, min_vol, rel_vol_thresh):
    """Gerçek zamanlı tarama motoru"""
    results = []
    progress_bar = st.progress(0)
    total = len(asset_list)
    
    for i, symbol in enumerate(asset_list):
        try:
            progress_bar.progress((i + 1) / total)
            
            # Veri çek
            stock = yf.Ticker(symbol)
            hist = stock.history(period="3mo")
            
            if len(hist) < 30: continue

            # Hesaplamalar
            hist['RSI'] = calculate_rsi(hist['Close'])
            current_rsi = hist['RSI'].iloc[-1]
            
            avg_vol = hist['Volume'].rolling(window=20).mean().iloc[-1]
            current_vol = hist['Volume'].iloc[-1]
            rv = current_vol / avg_vol if avg_vol > 0 else 0
            
            # Filtreleme
            if (rsi_min <= current_rsi <= rsi_max) and (current_vol >= min_vol) and (rv >= rel_vol_thresh):
                results.append({
                    "Hisse": symbol,
                    "Fiyat": round(hist['Close'].iloc[-1], 2),
                    "RSI (14)": round(current_rsi, 2),
                    "Rel. Vol": round(rv, 2),
                    "Hacim": f"{current_vol/1000000:.1f}M"
                })
                
        except Exception as e:
            continue
            
    progress_bar.empty()
    return pd.DataFrame(results)

# --- WIDGET VE VERİ FONKSİYONLARI ---

def render_tradingview_widget(ticker):
    # TRADINGVIEW SEMBOL DÜZELTMESİ (BIST FIX)
    tv_symbol = ticker
    
    if ".IS" in ticker:
        # ".IS" uzantısını kaldırıp BIST: ekliyoruz
        clean_ticker = ticker.split(".")[0] 
        tv_symbol = f"BIST:{clean_ticker}"
        
    elif "=X" in ticker: 
        tv_symbol = f"FX_IDC:{ticker.replace('=X', '')}"
    elif ticker in ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD"]:
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

        news_items.append({'title': title, 'link': link, 'date': date_str, 'source': source, 'sentiment': sent_text, 'color': sent_color, 'timestamp': dt_object})
    
    news_items.sort(key=lambda x: x['timestamp'], reverse=True)
    return news_items

@st.cache_data(ttl=600)
def fetch_stock_info(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('ask')
        prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
        
        if current_price and prev_close: change_pct = ((current_price - prev_close) / prev_close) * 100
        else: change_pct = 0
        return {'price': current_price, 'change_pct': change_pct, 'volume': info.get('volume', 0), 'sector': info.get('sector', '-'), 'target_price': info.get('targetMeanPrice', '-'), 'pe_ratio': info.get('trailingPE', '-')}
    except: return None

# --- ARAYÜZ ---
st.title("🦅 Patronun Terminali v2.3.0")
st.markdown("---")

current_ticker = st.session_state.ticker
current_category = st.session_state.category

# 1. Filtreleme Alanı
col_cat, col_ass, col_search_in, col_search_btn = st.columns([1.5, 2, 2, 0.7])

with col_cat:
    st.selectbox("Kategori Seç", list(ASSET_GROUPS.keys()), index=list(ASSET_GROUPS.keys()).index(current_category) if current_category in ASSET_GROUPS else 0, key="selected_category_key", on_change=on_category_change)

with col_ass:
    asset_options = ASSET_GROUPS[current_category]
    try: default_index = asset_options.index(current_ticker)
    except ValueError: default_index = 0
    st.selectbox(f"{current_category} Listesi", asset_options, index=default_index, key="selected_asset_key", on_change=on_asset_change)

with col_search_in:
    st.text_input("Manuel Hisse Kodu (Örn: PFE, THYAO.IS)", value="", placeholder=f"Şu anki hisse: {current_ticker}", key="manual_input_key")

with col_search_btn:
    st.write(""); st.write("")
    st.button("🔎 Ara", on_click=on_manual_button_click)

st.markdown("---")

# Veri Akışı
info_data = fetch_stock_info(current_ticker)
news_data = fetch_google_news(current_ticker)

if info_data and info_data['price']:
    c1, c2, c3, c4 = st.columns(4)
    delta_class = "delta-pos" if info_data['change_pct'] >= 0 else "delta-neg"
    delta_sign = "+" if info_data['change_pct'] >= 0 else ""
    c1.markdown(f"""<div class="stat-box"><div class="stat-label">{current_ticker} FİYAT</div><div class="stat-value money-text">{info_data['price']:.2f}</div><div class="stat-delta {delta_class} money-text">{delta_sign}{info_data['change_pct']:.2f}%</div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="stat-box"><div class="stat-label">GÜNLÜK HACİM</div><div class="stat-value money-text">{(info_data['volume'] / 1_000_000):.1f}M</div><span style="color: #616161;">adet</span></div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class="stat-box"><div class="stat-label">ANALİST HEDEF</div><div class="stat-value money-text">{info_data['target_price']}</div><span style="color: #616161;">Ort. Fiyat</span></div>""", unsafe_allow_html=True)
    c4.markdown(f"""<div class="stat-box"><div class="stat-label">SEKTÖR / F/K</div><div class="stat-value">{info_data['sector']}</div><span style="color: #616161;">PE: {info_data['pe_ratio']}</span></div>""", unsafe_allow_html=True)

    st.write("")
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
                    st.markdown(f"""<div class="news-card" style="border-left-color: {color};"><a href="{item['link']}" target="_blank" class="news-title">{item['title']}</a><div style="display:flex; justify-content:space-between; align-items:center;"><span class="news-meta">{item['date']} | {item['source']} </span><span class="sentiment-badge" style="color:{color}; border:1px solid {color}">{item['sentiment']}</span></div></div>""", unsafe_allow_html=True)
            else: st.info("Haber akışı bulunamadı.")
    
    # --- GERÇEK TARAMA MOTORU ---
    st.markdown("---")
    if st.button("🔄 Tam Yenile"): st.cache_data.clear(); st.rerun()

    st.header("🔍 V2.0: Finansal İstihbarat & Tarama Motoru")
    st.info(f"Aktif Kategori: {current_category}. Bu kategorideki tüm hisseler taranacaktır. Liste uzun olduğu için işlem 30-60 sn sürebilir.")

    with st.expander("Tarama Kriterlerini Ayarla ve Taramayı Başlat"):
        col_tech, col_volume, col_dummy = st.columns([1, 1, 2])
        
        with col_tech:
            st.markdown("**1. RSI Filtresi**")
            # Varsayılan aralığı genişlettim (0-100) ki sonuç dönsün
            rsi_range = st.slider("RSI (14) Aralığı", 0, 100, (0, 100)) 
        
        with col_volume:
            st.markdown("**2. Hacim Filtresi**")
            rel_vol_thresh = st.number_input("Relative Volume (Ort. Hacmin Kaç Katı?)", value=0.5, step=0.1)
            min_volume = st.number_input("Min. Günlük Hacim (Adet)", value=0)
            
        st.markdown("---")
        
        if st.button("🔴 CANLI TARAMAYI BAŞLAT", use_container_width=True, type="primary"):
            st.session_state.run_scan = True
            with st.spinner('Piyasa taranıyor...'):
                target_list = ASSET_GROUPS[current_category]
                st.session_state.scan_results = run_scanner(target_list, rsi_range[0], rsi_range[1], min_volume, rel_vol_thresh)
            st.success("Tarama Tamamlandı!")
            st.session_state.run_scan = False 
        
    # --- SONUÇLARI GÖSTER ---
    if st.session_state.scan_results is not None:
        st.subheader("🔍 Tarama Sonuçları")
        if not st.session_state.scan_results.empty:
            st.dataframe(st.session_state.scan_results, use_container_width=True)
        else:
            st.warning("Kriterlere uygun hisse bulunamadı. Lütfen kriterleri gevşetin.")

else:
    st.error("Veri bulunamadı. Lütfen hisse kodunu kontrol edin.")
