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
st.set_page_config(page_title="Patronun Terminali v3.5.0", layout="wide", page_icon="🦅")

# --- TEMA MOTORU ---
if 'theme' not in st.session_state: st.session_state.theme = "Buz Mavisi"

THEMES = {
    "Beyaz": {"bg": "#FFFFFF", "box_bg": "#F8F9FA", "text": "#000000", "border": "#DEE2E6", "news_bg": "#FFFFFF"},
    "Kirli Beyaz": {"bg": "#FAF9F6", "box_bg": "#FFFFFF", "text": "#2C3E50", "border": "#E5E7EB", "news_bg": "#FFFFFF"},
    "Buz Mavisi": {"bg": "#F0F8FF", "box_bg": "#FFFFFF", "text": "#0F172A", "border": "#BFDBFE", "news_bg": "#FFFFFF"}
}
current_theme = THEMES[st.session_state.theme]

# --- VARLIK LİSTELERİ (TOP 250) ---
ASSET_GROUPS = {
    "S&P 500 (TOP 250)": [
        "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "AMD", 
        "INTC", "QCOM", "TXN", "AMAT", "LRCX", "MU", "ADI", "CSCO", "ORCL", "CRM", 
        "ADBE", "IBM", "ACN", "NOW", "PANW", "SNPS", "CDNS", "KLAC", "NXPI", "APH",
        "MCHP", "ON", "ANET", "IT", "GLW", "HPE", "HPQ", "NTAP", "STX", "WDC", "TEL",
        "PLTR", "FTNT", "CRWD", "SMCI", "MSI", "TRMB", "TER", "PTC", "TYL", "FFIV",
        "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "AXP", "V", "MA", "PYPL", "SQ", 
        "SPGI", "MCO", "CB", "MMC", "PGR", "USB", "PNC", "TFC", "COF", "BK", "SCHW",
        "ICE", "CME", "AON", "AJG", "TRV", "ALL", "AIG", "MET", "PRU", "AFL", "HIG",
        "FITB", "MTB", "HBAN", "RF", "CFG", "KEY", "SYF", "DFS", "AMP", "PFG", "CINF",
        "LLY", "UNH", "JNJ", "MRK", "ABBV", "PFE", "TMO", "DHR", "ABT", "BMY", "AMGN", 
        "ISRG", "SYK", "ELV", "CVS", "CI", "GILD", "REGN", "VRTX", "ZTS", "BSX", "BDX",
        "HCA", "MCK", "COR", "CAH", "CNC", "HUM", "MOH", "DXCM", "EW", "RMD", "ALGN",
        "ZBH", "BAX", "STE", "COO", "WAT", "MTD", "IQV", "A", "HOLX", "IDXX", "BIO",
        "WMT", "HD", "PG", "COST", "KO", "PEP", "MCD", "SBUX", "NKE", "DIS", "TMUS",
        "CMCSA", "NFLX", "TGT", "LOW", "TJX", "PM", "MO", "EL", "CL", "K", "GIS", "MNST",
        "TSCO", "ROST", "FAST", "DLTR", "DG", "ORLY", "AZO", "ULTA", "BBY", "KHC", 
        "HSY", "MKC", "CLX", "KMB", "SYY", "KR", "ADM", "STZ", "TAP", "CAG", "SJM",
        "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HES", "KMI",
        "GE", "CAT", "DE", "HON", "MMM", "ETN", "ITW", "EMR", "PH", "CMI", "PCAR",
        "BA", "LMT", "RTX", "GD", "NOC", "LHX", "TDG", "TXT", "HII",
        "UPS", "FDX", "UNP", "CSX", "NSC", "DAL", "UAL", "AAL", "LUV",
        "FCX", "NEM", "NUE", "DOW", "CTVA", "LIN", "SHW", "PPG", "ECL", "APD", "VMC",
        "MLM", "ROP", "TT", "CARR", "OTIS", "ROK", "AME", "DOV", "XYL", "WAB",
        "NEE", "DUK", "SO", "AEP", "SRE", "D", "PEG", "ED", "XEL", "PCG", "WEC", "ES",
        "AMT", "PLD", "CCI", "EQIX", "PSA", "O", "DLR", "SPG", "VICI", "CBRE", "CSGP",
        "WELL", "AVB", "EQR", "EXR", "MAA", "HST", "KIM", "REG", "SBAC", "WY"
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
INITIAL_CATEGORY = "S&P 500 (TOP 250)"

# --- GÜVENLİ BAŞLANGIÇ ---
if 'category' in st.session_state:
    if st.session_state.category not in ASSET_GROUPS:
        st.session_state.category = INITIAL_CATEGORY
        st.session_state.ticker = ASSET_GROUPS[INITIAL_CATEGORY][0]

if 'ticker' not in st.session_state: st.session_state.ticker = "AAPL"
if 'category' not in st.session_state: st.session_state.category = INITIAL_CATEGORY
if 'scan_data' not in st.session_state: st.session_state.scan_data = None

# --- UI: TEMA SEÇİCİ ---
st.write("") 
c_theme, _, _ = st.columns([2, 4, 1])
with c_theme:
    selected_theme_name = st.radio(
        "Görünüm Modu", 
        ["Beyaz", "Kirli Beyaz", "Buz Mavisi"], 
        index=["Beyaz", "Kirli Beyaz", "Buz Mavisi"].index(st.session_state.theme),
        horizontal=True,
        label_visibility="collapsed"
    )
    st.session_state.theme = selected_theme_name

# --- DİNAMİK CSS (KOKPİT DÜZENİ) ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {current_theme['text']}; }}
    .stApp {{ background-color: {current_theme['bg']}; }}
    
    .stMetricValue, .money-text {{ font-family: 'JetBrains Mono', monospace !important; }}
    
    /* MİNİK STAT BOX (Compact) */
    .stat-box-small {{
        background: {current_theme['box_bg']}; border: 1px solid {current_theme['border']}; 
        border-radius: 6px; padding: 6px; text-align: center; margin-bottom: 5px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }}
    .stat-label-small {{ font-size: 0.65rem; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0px;}}
    .stat-value-small {{ font-size: 0.95rem; font-weight: 700; color: {current_theme['text']}; margin: 0px 0; }}
    .stat-delta-small {{ font-size: 0.75rem; margin-left: 4px; }}
    
    .delta-pos {{ color: #16A34A; }} .delta-neg {{ color: #DC2626; }} 
    
    .news-card {{
        background: {current_theme['news_bg']}; border-left: 3px solid {current_theme['border']}; 
        padding: 6px; margin-bottom: 6px; box-shadow: 0 1px 1px rgba(0,0,0,0.03); font-size: 0.8rem;
    }}
    .news-title {{ color: {current_theme['text']}; font-weight: 600; text-decoration: none; display: block; margin-bottom: 2px; line-height: 1.1; font-size: 0.85rem;}}
    .news-title:hover {{ text-decoration: underline; color: #2563EB; }}
    .news-meta {{ font-size: 0.65rem; color: #64748B; }}
    
    .stButton button {{ width: 100%; border-radius: 4px; font-size: 0.85rem; }}
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
    # 1. Benchmark
    try:
        spy_data = yf.download("^GSPC", period="1y", progress=False)
        if not spy_data.empty:
            spy_close = spy_data['Close']
            spy_5d_chg = (spy_close.iloc[-1] - spy_close.iloc[-6]) / spy_close.iloc[-6]
        else: spy_5d_chg = 0
    except: spy_5d_chg = 0

    # 2. Hisseler
    try:
        data = yf.download(asset_list, period="1y", group_by='ticker', threads=True, progress=False)
    except: return []

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
            if len(df) < 200: continue 

            close = df['Close']
            high = df['High']
            low = df['Low']
            volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))

            # Göstergeler
            sma200 = close.rolling(200).mean()
            ema5 = close.ewm(span=5, adjust=False).mean()
            ema20 = close.ewm(span=20, adjust=False).mean()
            
            sma20_bb = close.rolling(20).mean()
            std20_bb = close.rolling(20).std()
            bb_width = ((sma20_bb + 2*std20_bb) - (sma20_bb - 2*std20_bb)) / (sma20_bb + 0.0001)
            
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd_line = ema12 - ema26
            hist = macd_line - signal_line = macd_line.ewm(span=9, adjust=False).mean()
            
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs_val = gain / loss
            rsi = 100 - (100 / (1 + rs_val))
            
            highest_high = high.rolling(14).max()
            lowest_low = low.rolling(14).min()
            williams_r = (highest_high - close) / (highest_high - lowest_low) * -100
            
            daily_range = high - low
            
            # Puanlama
            score = 0; reasons = []
            curr_c = float(close.iloc[-1])
            curr_vol = float(volume.iloc[-1])
            avg_vol = float(volume.rolling(5).mean().iloc[-1]) if len(volume) > 5 else 1.0
            
            if curr_c > sma200.iloc[-1]: score += 1; reasons.append("🛡️ SMA200")
            stock_5d = (curr_c - float(close.iloc[-6])) / float(close.iloc[-6])
            if stock_5d > spy_5d_chg: score += 1; reasons.append("👑 RS")
            if bb_width.iloc[-1] <= bb_width.tail(60).min() * 1.15: score += 1; reasons.append("🚀 Squeeze")
            if daily_range.iloc[-1] <= daily_range.tail(4).min() * 1.05: score += 1; reasons.append("🔇 NR4")
            if ema5.iloc[-1] > ema20.iloc[-1]: score += 1; reasons.append("⚡ Trend")
            if williams_r.iloc[-1] > -50: score += 1; reasons.append("🔫 W%R")
            if hist.iloc[-1] > hist.iloc[-2]: score += 1; reasons.append("🟢 MACD")
            if rsi.iloc[-1] > 50 and rsi.iloc[-1] > rsi.iloc[-2]: score += 1; reasons.append("📈 RSI")
            if curr_vol > avg_vol * 1.2: score += 1; reasons.append(f"🔊 Vol")
            if curr_c >= high.tail(20).max() * 0.97: score += 1; reasons.append("🔨 Top")

            if score >= 3:
                signals.append({"Sembol": symbol, "Fiyat": f"{curr_c:.2f}", "Skor": score, "Nedenler": " | ".join(reasons)})

        except Exception: continue
    
    if not signals: return pd.DataFrame()
    return pd.DataFrame(signals).sort_values(by="Skor", ascending=False).head(20) # Sadece TOP 20

# --- WIDGET & DATA ---
def render_tradingview_widget(ticker, height=600):
    tv_symbol = ticker
    if ".IS" in ticker: tv_symbol = f"BIST:{ticker.replace('.IS', '')}"
    elif "=X" in ticker: tv_symbol = f"FX_IDC:{ticker.replace('=X', '')}"
    elif ticker in ["GC=F"]: tv_symbol = "COMEX:GC1!"
    elif ticker in ["SI=F"]: tv_symbol = "COMEX:SI1!"
    
    html_code = f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_chart"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
        "width": "100%", "height": {height}, "symbol": "{tv_symbol}", "interval": "D", "timezone": "Etc/UTC",
        "theme": "light", "style": "1", "locale": "tr", "toolbar_bg": "#f1f3f6", "enable_publishing": false,
        "allow_symbol_change": true, "container_id": "tradingview_chart"
      }});
      </script>
    </div>
    """
    components.html(html_code, height=height)

@st.cache_data(ttl=600)
def fetch_stock_info(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get('currentPrice') or info.get('regularMarketPrice')
        prev = info.get('previousClose')
        pct = ((price - prev) / prev) * 100 if price and prev else 0
        volume = info.get('volume', 0)
        return {'price': price, 'change_pct': pct, 'volume': volume, 'sector': info.get('sector', '-'), 'target': info.get('targetMeanPrice', '-')}
    except: return None

@st.cache_data(ttl=300)
def fetch_google_news(ticker):
    try:
        clean = ticker.replace(".IS", "").replace("=F", "")
        query = f"{clean} stock news site:investing.com OR site:seekingalpha.com"
        rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote_plus(query)}&hl=tr&gl=TR&ceid=TR:tr"
        feed = feedparser.parse(rss_url)
        news = []
        limit_date = datetime.now() - timedelta(days=10)
        for entry in feed.entries[:15]: # 15 Haber Limiti
            try: dt = datetime(*entry.published_parsed[:6])
            except: dt = datetime.now()
            if dt < limit_date: continue
            blob = TextBlob(entry.title); pol = blob.sentiment.polarity
            color = "#16A34A" if pol > 0.1 else "#DC2626" if pol < -0.1 else "#64748B"
            news.append({'title': entry.title, 'link': entry.link, 'date': dt.strftime('%d %b'), 'source': entry.source.title, 'color': color})
        return news
    except: return []

# --- ARAYÜZ (KOKPİT) ---
st.title(f"🦅 Patronun Terminali v3.5.0")
st.markdown("---")

current_ticker = st.session_state.ticker
current_category = st.session_state.category

# 1. ÜST MENÜ
col_cat, col_ass, col_search_in, col_search_btn = st.columns([1.5, 2, 2, 0.7])
with col_cat:
    cat_index = list(ASSET_GROUPS.keys()).index(current_category) if current_category in ASSET_GROUPS else 0
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

# 2. ANA KOKPİT (2 SÜTUNLU YAPI)
# Sol Sütun (Grafik + Info) vs Sağ Sütun (Akışlar)
col_main_left, col_main_right = st.columns([2.5, 1.2]) 

# --- SOL SÜTUN ---
with col_main_left:
    # MİNİK BİLGİ BARI (Yan Yana)
    info = fetch_stock_info(current_ticker)
    if info and info['price']:
        sc1, sc2, sc3, sc4 = st.columns(4)
        cls = "delta-pos" if info['change_pct'] >= 0 else "delta-neg"
        sgn = "+" if info['change_pct'] >= 0 else ""
        
        sc1.markdown(f'<div class="stat-box-small"><p class="stat-label-small">FİYAT</p><p class="stat-value-small money-text">{info["price"]:.2f}<span class="stat-delta-small {cls}">{sgn}{info["change_pct"]:.2f}%</span></p></div>', unsafe_allow_html=True)
        sc2.markdown(f'<div class="stat-box-small"><p class="stat-label-small">HACİM</p><p class="stat-value-small money-text">{info["volume"]/1e6:.1f}M</p></div>', unsafe_allow_html=True)
        sc3.markdown(f'<div class="stat-box-small"><p class="stat-label-small">HEDEF</p><p class="stat-value-small money-text">{info["target"]}</p></div>', unsafe_allow_html=True)
        sc4.markdown(f'<div class="stat-box-small"><p class="stat-label-small">SEKTÖR</p><p class="stat-value-small">{str(info["sector"])[:12]}</p></div>', unsafe_allow_html=True)
    
    # BÜYÜK GRAFİK
    st.write("")
    render_tradingview_widget(current_ticker, height=700) # Grafik Yüksekliği Arttırıldı

# --- SAĞ SÜTUN ---
with col_main_right:
    # 1. SENTIMENT 20
    st.subheader("🧠 Sentiment 20 Skoru")
    if st.button(f"⚡ {current_category} Tara", type="primary"):
        with st.spinner("Piyasa taranıyor..."):
            scan_df = analyze_market_intelligence(ASSET_GROUPS.get(current_category, []))
            st.session_state.scan_data = scan_df
    
    with st.container(height=350): # Scroll edilebilir alan
        if st.session_state.scan_data is not None:
            if not st.session_state.scan_data.empty:
                for index, row in st.session_state.scan_data.iterrows():
                    score = row['Skor']
                    icon = "🔥" if score >= 9 else "✅" if score >= 7 else "⚠️" 
                    label = f"{icon} {score}/10 | {row['Sembol']}"
                    
                    if st.button(label, key=f"btn_{row['Sembol']}_{index}", use_container_width=True):
                        on_scan_result_click(row['Sembol'])
                        st.rerun()
                    st.markdown(f"<div style='font-size:0.6rem; color:#64748B; margin-top:-8px; margin-bottom:4px; padding-left:5px;'>{row['Nedenler']}</div>", unsafe_allow_html=True)
            else: st.info("Güçlü sinyal yok.")
        else: st.info("Tara butonuna basın.")

    # 2. HABERLER (15 ADET)
    st.write("")
    st.subheader("📡 Haber Akışı")
    news_data = fetch_google_news(current_ticker)
    with st.container(height=400): # Scroll edilebilir alan
        if news_data:
            for n in news_data:
                st.markdown(f"""<div class="news-card" style="border-left-color: {n['color']};"><a href="{n['link']}" target="_blank" class="news-title">{n['title']}</a><div class="news-meta">{n['date']} • {n['source']}</div></div>""", unsafe_allow_html=True)
        else: st.info("Haber akışı yok.")
