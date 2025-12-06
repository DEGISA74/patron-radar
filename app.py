import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import urllib.parse 
from textblob import TextBlob
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import numpy as np

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Patronun Terminali v2.6.0", layout="wide", page_icon="🦅")

# --- VARLIK LİSTELERİ (SIRALAMA GÜNCELLENDİ) ---
ASSET_GROUPS = {
    "S&P 500 (TOP 50)": [
        "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "BRK.B", "AVGO", "JPM", 
        "LLY", "UNH", "V", "XOM", "MA", "JNJ", "HD", "PG", "COST", "ABBV", 
        "MRK", "CRM", "CVX", "BAC", "AMD", "WMT", "NFLX", "ACN", "PEP", "KO",
        "LIN", "TMO", "DIS", "ADBE", "WFC", "MCD", "CSCO", "QCOM", "CAT", "VZ",
        "INTU", "IBM", "GE", "AMAT", "NOW", "PFE", "CMCSA", "SPGI", "UNP", "TXN"
    ],
    "KRİPTO (TOP 20)": [
        "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", "DOGE-USD", "AVAX-USD", 
        "TRX-USD", "LINK-USD", "DOT-USD", "MATIC-USD", "LTC-USD", "SHIB-USD", "BCH-USD", "UNI-USD", 
        "ATOM-USD", "XLM-USD", "ETC-USD", "FIL-USD"
    ],
    "EMTİA & DÖVİZ": ["EURUSD=X", "USDTRY=X", "EURTRY=X", "GBPTRY=X", "GC=F", "SI=F", "CL=F"],
    # TÜRK HİSSELERİ EN ALTA ALINDI (Stabilite İçin)
    "TÜRK HİSSE (BIST 30)": [
        "THYAO.IS", "GARAN.IS", "ASELS.IS", "TUPRS.IS", "KCHOL.IS", "AKBNK.IS", "ISCTR.IS", "SISE.IS", 
        "BIMAS.IS", "EREGL.IS", "SAHOL.IS", "YKBNK.IS", "FROTO.IS", "KONTR.IS", "HEKTS.IS", "PETKM.IS", 
        "TOASO.IS", "PGSUS.IS", "ENKAI.IS", "ALARK.IS", "ODAS.IS", "EKGYO.IS", "KOZAL.IS", "SASA.IS"
    ]
}
ALL_ASSETS = [item for sublist in ASSET_GROUPS.values() for item in sublist]
INITIAL_CATEGORY = "S&P 500 (TOP 50)" # Varsayılan kategori değiştirildi

# --- CSS TASARIM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stMetricValue, .money-text { font-family: 'JetBrains Mono', monospace !important; }

    /* Stat Box */
    .stat-box {
        background: #FFFFFF; border: 1px solid #CFD8DC; border-radius: 8px; padding: 12px; text-align: center; margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stat-label { font-size: 0.75rem; color: #546E7A; text-transform: uppercase; letter-spacing: 0.5px; }
    .stat-value { font-size: 1.2rem; font-weight: 700; color: #263238; margin: 4px 0; }
    .delta-pos { color: #00C853; }
    .delta-neg { color: #D50000; }

    /* Haber Kartları */
    .news-card {
        background: #FFFFFF; border-left: 4px solid #ddd; padding: 8px; margin-bottom: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05); font-size: 0.85rem;
    }
    .news-title { 
        color: #263238; font-weight: 600; text-decoration: none; display: block; margin-bottom: 4px; line-height: 1.2;
    }
    .news-title:hover { text-decoration: underline; color: #0277BD; }
    .news-meta { font-size: 0.7rem; color: #90A4AE; }
    
    /* Butonlar */
    .stButton button { width: 100%; border-radius: 5px; }
    
    /* İstihbarat Açıklama */
    .intel-info { font-size: 0.75rem; color: #555; background: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True) 

# --- OTURUM YÖNETİMİ ---
if 'ticker' not in st.session_state: st.session_state.ticker = "AAPL" # Varsayılan AAPL
if 'category' not in st.session_state: st.session_state.category = INITIAL_CATEGORY
if 'scan_data' not in st.session_state: st.session_state.scan_data = None

# --- CALLBACKS ---
def on_category_change():
    new_cat = st.session_state.selected_category_key
    st.session_state.category = new_cat
    st.session_state.ticker = ASSET_GROUPS[new_cat][0]
    st.session_state.scan_data = None 

def on_asset_change():
    st.session_state.ticker = st.session_state.selected_asset_key

def on_manual_button_click():
    if st.session_state.manual_input_key:
        st.session_state.ticker = st.session_state.manual_input_key.upper()

def on_scan_result_click(symbol):
    """Tarama sonucuna tıklandığında çalışır"""
    st.session_state.ticker = symbol
    # Burada rerun'a gerek yok, butonun kendisi rerun tetikler

# --- GELİŞMİŞ FİNANSAL İSTİHBARAT MOTORU ---
def analyze_market_intelligence(asset_list):
    signals = []
    
    # 1. Toplu Veri Çekme (6 aylık)
    try:
        data = yf.download(asset_list, period="6mo", group_by='ticker', threads=True, progress=False)
    except:
        return []

    for symbol in asset_list:
        try:
            if len(asset_list) > 1: df = data[symbol].copy()
            else: df = data.copy()
            
            df = df.dropna(subset=['Close'])
            if len(df) < 50: continue 

            close = df['Close']
            
            # Göstergeler
            sma20 = close.rolling(window=20).mean()
            sma50 = close.rolling(window=50).mean()
            sma200 = close.rolling(window=200).mean()
            
            std = close.rolling(window=20).std()
            bb_upper = sma20 + (std * 2)
            bb_width = (bb_upper - (sma20 - (std * 2))) / sma20 

            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            curr_price = close.iloc[-1]
            curr_rsi = rsi.iloc[-1]
            curr_width = bb_width.iloc[-1]
            prev_close = close.iloc[-2]

            # --- STRATEJİLER ---
            found = False
            strategies = []

            # 1. Roket (Squeeze)
            min_width_3m = bb_width.tail(60).min()
            if curr_width <= min_width_3m * 1.1: 
                strategies.append("🚀 Squeeze")
                found = True

            # 2. Trend Lideri
            if (curr_price > sma50.iloc[-1]) and (sma50.iloc[-1] > sma200.iloc[-1]) and (50 < curr_rsi < 70):
                strategies.append("⭐ Trend")
                found = True

            # 3. Dip Avcısı
            if (curr_rsi < 35) and (curr_price > prev_close):
                strategies.append("⚓ Dip Dönüşü")
                found = True

            # 4. Direnç Kırma
            high_20 = close.tail(20).max()
            if (curr_price >= high_20 * 0.98) and (curr_price < high_20 * 1.02):
                strategies.append("🔨 Breakout")
                found = True

            if found:
                signals.append({
                    "Sembol": symbol,
                    "Fiyat": f"{curr_price:.2f}",
                    "Sinyal": " + ".join(strategies),
                    "RSI": round(curr_rsi, 1)
                })

        except: continue
            
    return pd.DataFrame(signals)


# --- WIDGET & DATA ---
def render_tradingview_widget(ticker):
    tv_symbol = ticker
    if ".IS" in ticker: tv_symbol = f"BIST:{ticker.replace('.IS', '')}"
    elif "=X" in ticker: tv_symbol = f"FX_IDC:{ticker.replace('=X', '')}"
    elif ticker in ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD"]: tv_symbol = f"BINANCE:{ticker.replace('-USD', 'USDT')}"
    elif "." not in ticker: tv_symbol = f"NASDAQ:{ticker}"

    html_code = f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_chart"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
        "width": "100%", "height": 550, "symbol": "{tv_symbol}", "interval": "D", "timezone": "Etc/UTC",
        "theme": "light", "style": "1", "locale": "tr", "toolbar_bg": "#f1f3f6", "enable_publishing": false,
        "allow_symbol_change": true, "container_id": "tradingview_chart"
      }});
      </script>
    </div>
    """
    components.html(html_code, height=550)

@st.cache_data(ttl=600)
def fetch_stock_info(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('ask')
        prev = info.get('previousClose') or info.get('regularMarketPreviousClose')
        pct = ((price - prev) / prev) * 100 if price and prev else 0
        return {'price': price, 'change_pct': pct, 'volume': info.get('volume', 0), 'sector': info.get('sector', '-'), 'target': info.get('targetMeanPrice', '-'), 'pe': info.get('trailingPE', '-')}
    except: return None

@st.cache_data(ttl=300)
def fetch_google_news(ticker):
    clean_ticker = ticker.replace(".IS", "")
    query = f"{clean_ticker} stock news" if ".IS" not in ticker else f"{clean_ticker} hisse haberleri"
    encoded_query = urllib.parse.quote_plus(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=tr&gl=TR&ceid=TR:tr"
    feed = feedparser.parse(rss_url)
    news = []
    for entry in feed.entries[:10]:
        try: dt = datetime(*entry.published_parsed[:6])
        except: dt = datetime.now()
        blob = TextBlob(entry.title); pol = blob.sentiment.polarity
        color = "#00C853" if pol > 0.1 else "#D50000" if pol < -0.1 else "#78909c"
        news.append({'title': entry.title, 'link': entry.link, 'date': dt.strftime('%d %b %H:%M'), 'source': entry.source.title, 'color': color, 'timestamp': dt})
    news.sort(key=lambda x: x['timestamp'], reverse=True)
    return news

# --- ARAYÜZ ---
st.title("🦅 Patronun Terminali v2.6.0")
st.markdown("---")

current_ticker = st.session_state.ticker
current_category = st.session_state.category

# 1. MENÜ
col_cat, col_ass, col_search_in, col_search_btn = st.columns([1.5, 2, 2, 0.7])
with col_cat:
    st.selectbox("Kategori", list(ASSET_GROUPS.keys()), index=list(ASSET_GROUPS.keys()).index(current_category) if current_category in ASSET_GROUPS else 0, key="selected_category_key", on_change=on_category_change)
with col_ass:
    opts = ASSET_GROUPS[current_category]
    idx = opts.index(current_ticker) if current_ticker in opts else 0
    st.selectbox("Varlık Listesi", opts, index=idx, key="selected_asset_key", on_change=on_asset_change)
with col_search_in:
    st.text_input("Manuel Kod", placeholder=f"Aktif: {current_ticker}", key="manual_input_key")
with col_search_btn:
    st.write(""); st.write("")
    st.button("🔎 Ara", on_click=on_manual_button_click)

st.markdown("---")

# 2. BİLGİ KARTLARI
info = fetch_stock_info(current_ticker)
if info and info['price']:
    c1, c2, c3, c4 = st.columns(4)
    cls = "delta-pos" if info['change_pct'] >= 0 else "delta-neg"
    sgn = "+" if info['change_pct'] >= 0 else ""
    c1.markdown(f'<div class="stat-box"><div class="stat-label">FİYAT</div><div class="stat-value money-text">{info["price"]:.2f}</div><div class="stat-delta {cls} money-text">{sgn}{info["change_pct"]:.2f}%</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-box"><div class="stat-label">HACİM</div><div class="stat-value money-text">{info["volume"]/1e6:.1f}M</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="stat-box"><div class="stat-label">HEDEF</div><div class="stat-value money-text">{info["target"]}</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="stat-box"><div class="stat-label">SEKTÖR</div><div class="stat-value">{info["sector"][:15]}</div></div>', unsafe_allow_html=True)

# 3. ANA EKRAN
st.write("")
col_main_chart, col_main_news, col_main_intel = st.columns([2.2, 0.9, 0.9])

# SÜTUN 1: GRAFİK
with col_main_chart:
    st.subheader(f"📈 {current_ticker}")
    render_tradingview_widget(current_ticker)

# SÜTUN 2: HABERLER
with col_main_news:
    st.subheader("📡 Haberler")
    news_data = fetch_google_news(current_ticker)
    with st.container(height=550):
        if news_data:
            for n in news_data:
                st.markdown(f"""
                <div class="news-card" style="border-left-color: {n['color']};">
                    <a href="{n['link']}" target="_blank" class="news-title">{n['title']}</a>
                    <div class="news-meta">{n['date']} • {n['source']}</div>
                </div>""", unsafe_allow_html=True)
        else: st.info("Haber yok.")

# SÜTUN 3: FİNANSAL İSTİHBARAT
with col_main_intel:
    st.subheader("🧠 İstihbarat")
    
    # Matematiksel Açıklama (Şeffaflık)
    with st.expander("ℹ️ Algoritma Nasıl Çalışır?"):
        st.markdown("""
        <div style="font-size:0.75rem;">
        <b>1. 🚀 Squeeze (Sıkışma):</b> Bollinger Bant genişliği son 3 ayın en düşüğünde. Patlama yakındır.<br>
        <b>2. ⭐ Trend:</b> Fiyat > SMA50 > SMA200. Trend güçlü ve yukarı.<br>
        <b>3. ⚓ Dip Dönüşü:</b> RSI < 35 (Aşırı Satım) ama fiyat tepki veriyor.<br>
        <b>4. 🔨 Breakout:</b> Fiyat son 20 günün zirvesini zorluyor.
        </div>
        """, unsafe_allow_html=True)

    if st.button(f"⚡ {current_category} Tara", type="primary"):
        with st.spinner("Analiz ediliyor..."):
            scan_df = analyze_market_intelligence(ASSET_GROUPS[current_category])
            st.session_state.scan_data = scan_df
    
    # SONUÇLAR (İNTERAKTİF BUTONLAR)
    with st.container(height=450):
        if st.session_state.scan_data is not None:
            if not st.session_state.scan_data.empty:
                for index, row in st.session_state.scan_data.iterrows():
                    # Buton Etiketi
                    label = f"{row['Sembol']} | {row['Sinyal']}"
                    # TIKLANABİLİR BUTON (Her biri bir hisseye link gibi çalışır)
                    if st.button(label, key=f"btn_{row['Sembol']}", use_container_width=True):
                        on_scan_result_click(row['Sembol'])
                        st.rerun() # Sayfayı yenile ve grafiği güncelle
            else:
                st.success("Tüm varlıklar yatay seyirde. Özel formasyon bulunamadı.")
        else:
            st.info("Listeyi taramak için butona basın.")

    if st.button("🗑️ Temizle"):
        st.session_state.scan_data = None
        st.rerun()
