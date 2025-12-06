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
st.set_page_config(page_title="Patronun Terminali v3.1.0", layout="wide", page_icon="🦅")

# --- VARLIK LİSTELERİ ---
ASSET_GROUPS = {
    "S&P 500 (TOP 150)": [
        "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "AMD", 
        "INTC", "QCOM", "TXN", "AMAT", "LRCX", "MU", "ADI", "CSCO", "ORCL", "CRM", 
        "ADBE", "IBM", "ACN", "NOW", "PANW", "SNPS", "CDNS", "KLAC", "NXPI", "APH",
        "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "AXP", "V", "MA", "PYPL", "SQ", 
        "SPGI", "MCO", "CB", "MMC", "PGR", "USB", "PNC", "TFC", "COF", "BK", "SCHW",
        "LLY", "UNH", "JNJ", "MRK", "ABBV", "PFE", "TMO", "DHR", "ABT", "BMY", "AMGN", 
        "ISRG", "SYK", "ELV", "CVS", "CI", "GILD", "REGN", "VRTX", "ZTS", "BSX", "BDX",
        "AMZN", "WMT", "HD", "PG", "COST", "KO", "PEP", "MCD", "SBUX", "NKE", "DIS", 
        "CMCSA", "NFLX", "TGT", "LOW", "TJX", "PM", "MO", "EL", "CL", "K", "GIS", "MNST",
        "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HES", "KMI",
        "GE", "CAT", "DE", "HON", "MMM", "ETN", "ITW", "EMR", "PH", "CMI", "PCAR",
        "BA", "LMT", "RTX", "GD", "NOC", "LHX", "TDG", "TXT", "HII",
        "UPS", "FDX", "UNP", "CSX", "NSC", "DAL", "UAL", "AAL", "LUV",
        "AMT", "PLD", "CCI", "EQIX", "PSA", "O", "DLR", "SPG", "VICI",
        "NEE", "DUK", "SO", "AEP", "SRE", "D", "PEG", "ED", "XEL", "PCG"
    ],
    "NASDAQ (TOP 50)": [
        "AAPL", "MSFT", "NVDA", "AMZN", "AVGO", "META", "TSLA", "GOOGL", "GOOG", "COST",
        "NFLX", "AMD", "PEP", "LIN", "TMUS", "CSCO", "QCOM", "INTU", "AMAT", "TXN",
        "HON", "AMGN", "BKNG", "ISRG", "CMCSA", "SBUX", "MDLZ", "GILD", "ADP", "ADI",
        "REGN", "VRTX", "LRCX", "PANW", "MU", "KLAC", "SNPS", "CDNS", "MELI", "MAR",
        "ORLY", "CTAS", "NXPI", "CRWD", "CSX", "PCAR", "MNST", "WDAY", "ROP", "AEP"
    ],
    "EMTİA (ALTIN/GÜMÜŞ)": ["GC=F", "SI=F"]
}
INITIAL_CATEGORY = "S&P 500 (TOP 150)"

# --- GÜVENLİ BAŞLANGIÇ (SELF-HEALING) ---
if 'category' in st.session_state:
    if st.session_state.category not in ASSET_GROUPS:
        st.session_state.category = INITIAL_CATEGORY
        st.session_state.ticker = ASSET_GROUPS[INITIAL_CATEGORY][0]

if 'ticker' not in st.session_state: st.session_state.ticker = "AAPL"
if 'category' not in st.session_state: st.session_state.category = INITIAL_CATEGORY
if 'scan_data' not in st.session_state: st.session_state.scan_data = None

# --- CSS TASARIM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stMetricValue, .money-text { font-family: 'JetBrains Mono', monospace !important; }
    .stat-box {
        background: #FFFFFF; border: 1px solid #CFD8DC; border-radius: 8px; padding: 12px; text-align: center; margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stat-label { font-size: 0.75rem; color: #546E7A; text-transform: uppercase; letter-spacing: 0.5px; }
    .stat-value { font-size: 1.2rem; font-weight: 700; color: #263238; margin: 4px 0; }
    .delta-pos { color: #00C853; }
    .delta-neg { color: #D50000; }
    .news-card {
        background: #FFFFFF; border-left: 4px solid #ddd; padding: 8px; margin-bottom: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05); font-size: 0.85rem;
    }
    .news-title { 
        color: #263238; font-weight: 600; text-decoration: none; display: block; margin-bottom: 4px; line-height: 1.2;
    }
    .news-title:hover { text-decoration: underline; color: #0277BD; }
    .news-meta { font-size: 0.7rem; color: #90A4AE; }
    .stButton button { width: 100%; border-radius: 5px; }
</style>
""", unsafe_allow_html=True) 

# --- CALLBACKLER ---
def on_category_change():
    new_cat = st.session_state.get("selected_category_key")
    if new_cat and new_cat in ASSET_GROUPS:
        st.session_state.category = new_cat
        st.session_state.ticker = ASSET_GROUPS[new_cat][0]
        st.session_state.scan_data = None 

def on_asset_change():
    new_asset = st.session_state.get("selected_asset_key")
    if new_asset:
        st.session_state.ticker = new_asset

def on_manual_button_click():
    if st.session_state.manual_input_key:
        st.session_state.ticker = st.session_state.manual_input_key.upper()

def on_scan_result_click(symbol):
    st.session_state.ticker = symbol

# --- ANALİZ MOTORU ---
def analyze_market_intelligence(asset_list):
    signals = []
    
    try:
        data = yf.download(asset_list, period="6mo", group_by='ticker', threads=True, progress=False)
    except Exception: return []

    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]: df = data[symbol].copy()
                else: continue
            else:
                if len(asset_list) == 1: df = data.copy()
                else: continue

            if df.empty or 'Close' not in df.columns: continue
            df = df.dropna(subset=['Close'])
            if len(df) < 60: continue 

            close = df['Close']
            high = df['High']
            low = df['Low']
            volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))

            # GÖSTERGELER
            ema5 = close.ewm(span=5, adjust=False).mean()
            ema20 = close.ewm(span=20, adjust=False).mean()
            
            sma20 = close.rolling(20).mean()
            std20 = close.rolling(20).std()
            bb_width = ((sma20 + 2*std20) - (sma20 - 2*std20)) / (sma20 + 0.0001)
            
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            hist = macd_line - signal_line
            
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs_val = gain / loss
            rsi = 100 - (100 / (1 + rs_val))
            
            highest_high = high.rolling(14).max()
            lowest_low = low.rolling(14).min()
            williams_r = (highest_high - close) / (highest_high - lowest_low) * -100
            
            daily_range = high - low

            # PUANLAMA
            score = 0; reasons = []
            curr_c = float(close.iloc[-1])
            curr_vol = float(volume.iloc[-1])
            avg_vol = float(volume.rolling(5).mean().iloc[-1]) if len(volume) > 5 else 1.0
            
            # KRİTERLER
            if bb_width.iloc[-1] <= bb_width.tail(60).min() * 1.1: score += 1; reasons.append("🚀 Squeeze")
            if daily_range.iloc[-1] == daily_range.tail(4).min() and daily_range.iloc[-1] > 0: score += 1; reasons.append("🔇 NR4")
            if ((ema5.iloc[-1] > ema20.iloc[-1]) and (ema5.iloc[-2] <= ema20.iloc[-2])) or ((ema5.iloc[-2] > ema20.iloc[-2]) and (ema5.iloc[-3] <= ema20.iloc[-3])): score += 1; reasons.append("⚡ Trend")
            if hist.iloc[-1] > hist.iloc[-2]: score += 1; reasons.append("🟢 MACD")
            if williams_r.iloc[-1] > -50: score += 1; reasons.append("🔫 Will%R")
            if curr_vol > avg_vol * 1.2: score += 1; reasons.append(f"🔊 Hacim")
            if curr_c >= high.tail(20).max() * 0.98: score += 1; reasons.append("🔨 Breakout")
            rsi_c = rsi.iloc[-1]
            if 30 < rsi_c < 65 and rsi_c > rsi.iloc[-2]: score += 1; reasons.append("⚓ RSI Güçlü")

            if score > 0:
                signals.append({"Sembol": symbol, "Fiyat": f"{curr_c:.2f}", "Skor": score, "Nedenler": " | ".join(reasons), "RSI": round(rsi_c, 1)})

        except Exception: continue
    
    if not signals: return pd.DataFrame()
    return pd.DataFrame(signals).sort_values(by="Skor", ascending=False)

# --- WIDGET & DATA ---
def render_tradingview_widget(ticker):
    tv_symbol = ticker
    if ".IS" in ticker: tv_symbol = f"BIST:{ticker.replace('.IS', '')}"
    elif "=X" in ticker: tv_symbol = f"FX_IDC:{ticker.replace('=X', '')}"
    elif ticker in ["GC=F"]: tv_symbol = "COMEX:GC1!"
    elif ticker in ["SI=F"]: tv_symbol = "COMEX:SI1!"
    elif ticker in ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD"]: tv_symbol = f"BINANCE:{ticker.replace('-USD', 'USDT')}"
    
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
        volume = info.get('volume', 0)
        return {'price': price, 'change_pct': pct, 'volume': volume, 'sector': info.get('sector', '-'), 'target': info.get('targetMeanPrice', '-')}
    except: return None

@st.cache_data(ttl=300)
def fetch_google_news(ticker):
    try:
        clean = ticker.replace(".IS", "").replace("=F", "")
        query = f"{clean} stock news" if ".IS" not in ticker else f"{clean} hisse haberleri"
        rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote_plus(query)}&hl=tr&gl=TR&ceid=TR:tr"
        feed = feedparser.parse(rss_url)
        news = []
        limit_date = datetime.now() - timedelta(days=10)
        for entry in feed.entries[:8]:
            try: dt = datetime(*entry.published_parsed[:6])
            except: dt = datetime.now()
            if dt < limit_date: continue
            blob = TextBlob(entry.title); pol = blob.sentiment.polarity
            color = "#00C853" if pol > 0.1 else "#D50000" if pol < -0.1 else "#78909c"
            news.append({'title': entry.title, 'link': entry.link, 'date': dt.strftime('%d %b'), 'source': entry.source.title, 'color': color})
        return news
    except: return []

# --- ARAYÜZ ---
st.title("🦅 Patronun Terminali v3.1.0 (Master Trader)")
st.markdown("---")

current_ticker = st.session_state.ticker
current_category = st.session_state.category

# 1. MENÜ
col_cat, col_ass, col_search_in, col_search_btn = st.columns([1.5, 2, 2, 0.7])
with col_cat:
    cat_index = 0
    if current_category in ASSET_GROUPS:
        cat_index = list(ASSET_GROUPS.keys()).index(current_category)
    else:
        st.session_state.category = INITIAL_CATEGORY
        cat_index = 0
    st.selectbox("Kategori", list(ASSET_GROUPS.keys()), index=cat_index, key="selected_category_key", on_change=on_category_change)

with col_ass:
    opts = ASSET_GROUPS.get(current_category, ASSET_GROUPS[INITIAL_CATEGORY])
    try: idx = opts.index(current_ticker)
    except: idx = 0
    st.selectbox("Varlık Listesi", opts, index=idx, key="selected_asset_key", on_change=on_asset_change)

with col_search_in:
    st.text_input("Manuel Kod", placeholder=f"Aktif: {current_ticker}", key="manual_input_key")
with col_search_btn:
    st.write(""); st.write("")
    st.button("🔎 Ara", on_click=on_manual_button_click)

st.markdown("---")

# 2. İÇERİK
info = fetch_stock_info(current_ticker)
if info and info['price']:
    c1, c2, c3, c4 = st.columns(4)
    cls = "delta-pos" if info['change_pct'] >= 0 else "delta-neg"
    sgn = "+" if info['change_pct'] >= 0 else ""
    c1.markdown(f'<div class="stat-box"><div class="stat-label">FİYAT</div><div class="stat-value money-text">{info["price"]:.2f}</div><div class="stat-delta {cls} money-text">{sgn}{info["change_pct"]:.2f}%</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-box"><div class="stat-label">HACİM</div><div class="stat-value money-text">{info["volume"]/1e6:.1f}M</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="stat-box"><div class="stat-label">HEDEF</div><div class="stat-value money-text">{info["target"]}</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="stat-box"><div class="stat-label">SEKTÖR</div><div class="stat-value">{str(info["sector"])[:15]}</div></div>', unsafe_allow_html=True)
else:
    st.warning(f"{current_ticker} fiyat verisi anlık çekilemedi. Grafik aşağıdadır.")

st.write("")
col_main_chart, col_main_news, col_main_intel = st.columns([2.2, 0.9, 0.9])

with col_main_chart:
    st.subheader(f"📈 {current_ticker}")
    render_tradingview_widget(current_ticker)

with col_main_news:
    st.subheader("📡 Haberler")
    news_data = fetch_google_news(current_ticker)
    with st.container(height=550):
        if news_data:
            for n in news_data:
                st.markdown(f"""<div class="news-card" style="border-left-color: {n['color']};"><a href="{n['link']}" target="_blank" class="news-title">{n['title']}</a><div class="news-meta">{n['date']} • {n['source']}</div></div>""", unsafe_allow_html=True)
        else: st.info("Haber yok.")

with col_main_intel:
    st.subheader("🧠 Sentiment")
    with st.expander("ℹ️ 8'li Puan Sistemi"):
        st.markdown("""
        <div style="font-size:0.7rem;">
        <b>1. 🚀 Squeeze:</b> Daralma (Patlama Hazırlığı)<br>
        <b>2. 🔇 NR4:</b> Sessiz Gün<br>
        <b>3. ⚡ Trend:</b> EMA5 > EMA20<br>
        <b>4. 🟢 MACD:</b> Momentum Yeşil<br>
        <b>5. 🔫 Will%R:</b> -50 Kırılımı<br>
        <b>6. 🔊 Hacim:</b> %20+ Artış<br>
        <b>7. 🔨 Breakout:</b> Zirve Zorluyor<br>
        <b>8. ⚓ RSI:</b> 30-65 Yükselen
        </div>""", unsafe_allow_html=True)

    if st.button(f"⚡ {current_category} Analiz", type="primary"):
        with st.spinner("Taranıyor..."):
            scan_df = analyze_market_intelligence(ASSET_GROUPS.get(current_category, []))
            st.session_state.scan_data = scan_df
    
    with st.container(height=450):
        if st.session_state.scan_data is not None:
            if not st.session_state.scan_data.empty:
                for index, row in st.session_state.scan_data.iterrows():
                    score = row['Skor']
                    label = f"★ {score}/8 | {row['Sembol']}"
                    if st.button(label, key=f"btn_{row['Sembol']}_{index}", use_container_width=True):
                        on_scan_result_click(row['Sembol'])
                        st.rerun()
                    st.markdown(f"<div style='font-size:0.65rem; color:#666; margin-top:-10px; margin-bottom:5px; padding-left:5px;'>{row['Nedenler']}</div>", unsafe_allow_html=True)
            else: st.info("Sinyal yok.")
        else: st.info("Analiz için butona basın.")
