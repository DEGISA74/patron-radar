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
st.set_page_config(
    page_title="Patronun Terminali v3.7.4 (V3.2.0 Sinyal + RADAR 2)",
    layout="wide",
    page_icon="🦅"
)

# --- TEMA MOTORU ---
if 'theme' not in st.session_state:
    st.session_state.theme = "Buz Mavisi"

THEMES = {
    "Beyaz": {
        "bg": "#FFFFFF",
        "box_bg": "#F8F9FA",
        "text": "#000000",
        "border": "#DEE2E6",
        "news_bg": "#FFFFFF"
    },
    "Kirli Beyaz": {
        "bg": "#FAF9F6",
        "box_bg": "#FFFFFF",
        "text": "#2C3E50",
        "border": "#E5E7EB",
        "news_bg": "#FFFFFF"
    },
    "Buz Mavisi": {
        "bg": "#F0F8FF",
        "box_bg": "#FFFFFF",
        "text": "#0F172A",
        "border": "#BFDBFE",
        "news_bg": "#FFFFFF"
    }
}

# --- VARLIK LİSTELERİ ---
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

# --- GÜVENLİ BAŞLANGIÇ & STATE ---
if 'category' in st.session_state:
    if st.session_state.category not in ASSET_GROUPS:
        st.session_state.category = INITIAL_CATEGORY
        st.session_state.ticker = ASSET_GROUPS[INITIAL_CATEGORY][0]

if 'ticker' not in st.session_state:
    st.session_state.ticker = "AAPL"
if 'category' not in st.session_state:
    st.session_state.category = INITIAL_CATEGORY
if 'scan_data' not in st.session_state:
    st.session_state.scan_data = None
if 'radar2_data' not in st.session_state:
    st.session_state.radar2_data = None
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = []
if 'radar1_log' not in st.session_state:
    st.session_state.radar1_log = []
if 'radar2_log' not in st.session_state:
    st.session_state.radar2_log = []
if 'radar2_profile' not in st.session_state:
    st.session_state.radar2_profile = "Swing"

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

current_theme = THEMES[st.session_state.theme]

# --- DİNAMİK CSS ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&display=swap');

    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {current_theme['text']}; }}

    .stApp {{
        background-color: {current_theme['bg']};
    }}

    .stMetricValue, .money-text {{ font-family: 'JetBrains Mono', monospace !important; }}

    .stat-box-small {{
        background: {current_theme['box_bg']}; border: 1px solid {current_theme['border']};
        border-radius: 6px; padding: 6px; text-align: center; margin-bottom: 5px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }}
    .stat-label-small {{ font-size: 0.65rem; color: #64748B; text-transform: uppercase;
        letter-spacing: 0.5px; margin-bottom: 0px;}}
    .stat-value-small {{ font-size: 0.95rem; font-weight: 700; color: {current_theme['text']};
        margin: 0px 0; }}
    .stat-delta-small {{ font-size: 0.75rem; margin-left: 4px; }}

    .delta-pos {{ color: #16A34A; }}
    .delta-neg {{ color: #DC2626; }}

    .news-card {{
        background: {current_theme['news_bg']};
        border-left: 3px solid {current_theme['border']};
        padding: 6px; margin-bottom: 6px; box-shadow: 0 1px 1px rgba(0,0,0,0.03);
        font-size: 0.8rem;
    }}
    .news-title {{
        color: {current_theme['text']}; font-weight: 600; text-decoration: none;
        display: block; margin-bottom: 2px; line-height: 1.1; font-size: 0.85rem;
    }}
    .news-title:hover {{ text-decoration: underline; color: #2563EB; }}
    .news-meta {{ font-size: 0.65rem; color: #64748B; }}

    .signal-card {{
        background: {current_theme['box_bg']};
        border: 1px solid {current_theme['border']};
        border-radius: 6px;
        padding: 8px;
        font-size: 0.75rem;
        margin-top: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }}

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
        st.session_state.radar2_data = None

def on_asset_change():
    new_asset = st.session_state.get("selected_asset_key")
    if new_asset:
        st.session_state.ticker = new_asset

def on_manual_button_click():
    if st.session_state.manual_input_key:
        st.session_state.ticker = st.session_state.manual_input_key.upper()

def on_scan_result_click(symbol):
    st.session_state.ticker = symbol

def toggle_watchlist(symbol):
    wl = st.session_state.watchlist
    if symbol in wl:
        wl.remove(symbol)
    else:
        wl.append(symbol)

def add_to_log(log_name, category, df):
    if df is None or df.empty:
        return
    entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "category": category,
        "count": len(df)
    }
    st.session_state[log_name].insert(0, entry)

# --- ANALİZ MOTORU (RADAR 1 - V3.2.0) ---
def analyze_market_intelligence(asset_list):
    signals = []
    try:
        data = yf.download(asset_list, period="6mo", group_by='ticker', threads=True, progress=False)
    except Exception:
        return pd.DataFrame()

    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]:
                    df = data[symbol].copy()
                else:
                    continue
            else:
                if len(asset_list) == 1:
                    df = data.copy()
                else:
                    continue

            if df.empty or 'Close' not in df.columns:
                continue
            df = df.dropna(subset=['Close'])
            if len(df) < 60:
                continue

            close = df['Close']
            high = df['High']
            low = df['Low']
            volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))

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

            score = 0
            reasons = []
            curr_c = float(close.iloc[-1])
            curr_vol = float(volume.iloc[-1])
            avg_vol = float(volume.rolling(5).mean().iloc[-1]) if len(volume) > 5 else 1.0

            if bb_width.iloc[-1] <= bb_width.tail(60).min() * 1.1:
                score += 1; reasons.append("🚀 Squeeze")
            if daily_range.iloc[-1] == daily_range.tail(4).min() and daily_range.iloc[-1] > 0:
                score += 1; reasons.append("🔇 NR4")
            if ((ema5.iloc[-1] > ema20.iloc[-1]) and (ema5.iloc[-2] <= ema20.iloc[-2])) or \
               ((ema5.iloc[-2] > ema20.iloc[-2]) and (ema5.iloc[-3] <= ema20.iloc[-3])):
                score += 1; reasons.append("⚡ Trend")
            if hist.iloc[-1] > hist.iloc[-2]:
                score += 1; reasons.append("🟢 MACD")
            if williams_r.iloc[-1] > -50:
                score += 1; reasons.append("🔫 Will%R")
            if curr_vol > avg_vol * 1.2:
                score += 1; reasons.append("🔊 Hacim")
            if curr_c >= high.tail(20).max() * 0.98:
                score += 1; reasons.append("🔨 Breakout")
            rsi_c = rsi.iloc[-1]
            if 30 < rsi_c < 65 and rsi_c > rsi.iloc[-2]:
                score += 1; reasons.append("⚓ RSI Güçlü")

            if score > 0:
                signals.append({
                    "Sembol": symbol,
                    "Fiyat": f"{curr_c:.2f}",
                    "Skor": score,
                    "Nedenler": " | ".join(reasons),
                    "RSI": round(rsi_c, 1)
                })

        except Exception:
            continue

    if not signals:
        return pd.DataFrame()
    return pd.DataFrame(signals).sort_values(by="Skor", ascending=False)

# --- ANALİZ MOTORU (RADAR 2) ---
def radar2_scan(asset_list, min_price=5, max_price=500, min_avg_vol_m=1.0):
    if not asset_list:
        return pd.DataFrame()

    try:
        data = yf.download(asset_list, period="1y", group_by="ticker", threads=True, progress=False)
    except Exception:
        return pd.DataFrame()

    try:
        idx = yf.download("^GSPC", period="1y", progress=False)["Close"]
    except Exception:
        idx = None

    results = []
    progress_bar = st.progress(0, text=f"RADAR 2: 0/{len(asset_list)} sembol taranıyor...")

    for i, symbol in enumerate(asset_list):
        progress_val = (i + 1) / len(asset_list)
        progress_bar.progress(progress_val, text=f"RADAR 2: {i + 1}/{len(asset_list)} sembol taranıyor: {symbol}")

        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol not in data.columns.levels[0]:
                    continue
                df = data[symbol].copy()
            else:
                if len(asset_list) == 1:
                    df = data.copy()
                else:
                    continue

            if df.empty or 'Close' not in df.columns:
                continue

            df = df.dropna(subset=['Close'])
            if len(df) < 120:
                continue

            close = df['Close']
            high = df['High']
            volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))

            curr_c = float(close.iloc[-1])
            if curr_c < min_price or curr_c > max_price:
                continue

            avg_vol_20 = float(volume.rolling(20).mean().iloc[-1])
            if avg_vol_20 < min_avg_vol_m * 1e6:
                continue

            sma20 = close.rolling(20).mean()
            sma50 = close.rolling(50).mean()
            sma100 = close.rolling(100).mean()
            sma200 = close.rolling(200).mean()

            trend = "Yatay"
            if not np.isnan(sma200.iloc[-1]):
                if curr_c > sma50.iloc[-1] > sma100.iloc[-1] > sma200.iloc[-1] and sma200.iloc[-1] > sma200.iloc[-20]:
                    trend = "Boğa"
                elif curr_c < sma200.iloc[-1] and sma200.iloc[-1] < sma200.iloc[-20]:
                    trend = "Ayı"

            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs_val = gain / loss.replace(0, np.nan).fillna(1e-10)
            rsi = 100 - (100 / (1 + rs_val))
            rsi_c = float(rsi.iloc[-1])

            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            hist = macd_line - signal_line

            recent_high_60 = float(high.rolling(60).max().iloc[-1])
            breakout_ratio = curr_c / recent_high_60 if recent_high_60 > 0 else 0

            rs_score = 0.0
            if idx is not None and len(close) > 60 and len(idx) > 60:
                common_index = close.index.intersection(idx.index)
                if len(common_index) > 60:
                    cs = close.reindex(common_index)
                    isx = idx.reindex(common_index)
                    stock_ret = cs.iloc[-1] / cs.iloc[-60] - 1
                    idx_ret = isx.iloc[-1] / isx.iloc[-60] - 1
                    rs_score = float(stock_ret - idx_ret)

            setup = "-"
            tags = []
            score = 0

            avg_vol_20 = max(avg_vol_20, 1)

            vol_spike = volume.iloc[-1] > avg_vol_20 * 1.3
            if trend == "Boğa" and breakout_ratio >= 0.97:
                setup = "Breakout"
                score += 2
                tags.append("Zirveye yakın")
                if vol_spike:
                    score += 1
                    tags.append("Hacim spike")

            if trend == "Boğa" and setup == "-":
                if sma20.iloc[-1] <= curr_c <= sma50.iloc[-1] * 1.02 and 40 <= rsi_c <= 55:
                    setup = "Pullback"
                    score += 2
                    tags.append("Trend içinde düzeltme")
                    if volume.iloc[-1] < avg_vol_20 * 0.9:
                        score += 1
                        tags.append("Satış hacmi düşük")

            if setup == "-":
                if rsi.iloc[-2] < 30 <= rsi_c and hist.iloc[-1] > hist.iloc[-2]:
                    setup = "Dip Dönüşü"
                    score += 2
                    tags.append("Aşırı satımdan dönüş")

            if rs_score > 0:
                score += 1
                tags.append("Endeksi yeniyor")

            if trend == "Boğa":
                score += 1
            elif trend == "Ayı":
                score -= 1

            if score <= 0:
                continue

            results.append({
                "Sembol": symbol,
                "Fiyat": round(curr_c, 2),
                "Trend": trend,
                "Setup": setup,
                "Skor": score,
                "RS": round(rs_score * 100, 1),
                "Etiketler": " | ".join(tags)
            })

        except Exception:
            continue

    progress_bar.empty()

    if not results:
        return pd.DataFrame()
    df_res = pd.DataFrame(results)
    return df_res.sort_values(by=["Skor", "RS"], ascending=False).head(50)

# --- TRADINGVIEW WIDGET ---
def render_tradingview_widget(ticker, height=550):
    tv_symbol = ticker
    if ".IS" in ticker:
        tv_symbol = f"BIST:{ticker.replace('.IS', '')}"
    elif "=X" in ticker:
        tv_symbol = f"FX_IDC:{ticker.replace('=X', '')}"
    elif ticker in ["GC=F"]:
        tv_symbol = "COMEX:GC1!"
    elif ticker in ["SI=F"]:
        tv_symbol = "COMEX:SI1!"

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

# --- YARDIMCI FONKSİYONLAR ---
def fetch_stock_info(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get('currentPrice') or info.get('regularMarketPrice')
        prev = info.get('previousClose')
        pct = ((price - prev) / prev) * 100 if price and prev else 0
        volume = info.get('volume', 0)
        return {
            'price': price,
            'change_pct': pct,
            'volume': volume,
            'sector': info.get('sector', '-'),
            'target': info.get('targetMeanPrice', '-')
        }
    except Exception:
        return None

@st.cache_data(ttl=300)
def fetch_google_news(ticker):
    try:
        clean = ticker.replace(".IS", "").replace("=F", "")
        query = f"{clean} stock news site:investing.com OR site:seekingalpha.com"
        rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote_plus(query)}&hl=tr&gl=TR&ceid=TR:tr"
        feed = feedparser.parse(rss_url)
        news = []
        limit_date = datetime.now() - timedelta(days=10)
        for entry in feed.entries[:15]:
            try:
                dt = datetime(*entry.published_parsed[:6])
            except Exception:
                dt = datetime.now()
            if dt < limit_date:
                continue
            blob = TextBlob(entry.title)
            pol = blob.sentiment.polarity
            color = "#16A34A" if pol > 0.1 else "#DC2626" if pol < -0.1 else "#64748B"
            news.append({
                'title': entry.title,
                'link': entry.link,
                'date': dt.strftime('%d %b'),
                'source': entry.source.title,
                'color': color
            })
        return news
    except Exception:
        return []

def get_signal_summary_html(ticker):
    radar1_row = None
    radar2_row = None

    if st.session_state.scan_data is not None and not st.session_state.scan_data.empty:
        df1 = st.session_state.scan_data
        r1 = df1[df1["Sembol"] == ticker]
        if not r1.empty:
            radar1_row = r1.iloc[0]

    if st.session_state.radar2_data is not None and not st.session_state.radar2_data.empty:
        df2 = st.session_state.radar2_data
        r2 = df2[df2["Sembol"] == ticker]
        if not r2.empty:
            radar2_row = r2.iloc[0]

    parts = []
    if radar1_row is not None:
        parts.append(
            f"<b>RADAR 1:</b> Skor {radar1_row['Skor']}/8 • "
            f"Nedenler: {radar1_row['Nedenler']}"
        )
    else:
        parts.append("<b>RADAR 1:</b> Aktif sinyal yok.")

    if radar2_row is not None:
        parts.append(
            f"<b>RADAR 2:</b> {radar2_row['Trend']} • {radar2_row['Setup']} • "
            f"Skor {radar2_row['Skor']} • RS: {radar2_row['RS']}%"
        )
    else:
        parts.append("<b>RADAR 2:</b> Aktif setup yok.")

    html = "<div class='signal-card'>" + "<br>".join(parts) + "</div>"
    return html

# --- ARAYÜZ ---
st.title("🦅 Patronun Terminali v3.7.4")

current_ticker = st.session_state.ticker
current_category = st.session_state.category

# ÜST MENÜ
col_cat, col_ass, col_search_in, col_search_btn = st.columns([1.5, 2, 2, 0.7])
with col_cat:
    cat_index = list(ASSET_GROUPS.keys()).index(current_category) if current_category in ASSET_GROUPS else 0
    st.selectbox(
        "Kategori",
        list(ASSET_GROUPS.keys()),
        index=cat_index,
        key="selected_category_key",
        on_change=on_category_change
    )

with col_ass:
    opts = ASSET_GROUPS.get(current_category, ASSET_GROUPS[INITIAL_CATEGORY])
    try:
        idx = opts.index(current_ticker)
    except Exception:
        idx = 0
    st.selectbox(
        "Varlık Listesi",
        opts,
        index=idx,
        key="selected_asset_key",
        on_change=on_asset_change
    )

with col_search_in:
    st.text_input("Manuel Kod", placeholder=f"Aktif: {current_ticker}", key="manual_input_key")
with col_search_btn:
    st.write(""); st.write("")
    st.button("🔎 Ara", on_click=on_manual_button_click)

st.markdown("---")

# Ortak bilgi: fiyat verisi
info = fetch_stock_info(current_ticker)

col_main_left, col_main_right = st.columns([2.5, 1.2])

# --- SOL SÜTUN ---
with col_main_left:
    # Mini bilgi barı
    if info and info['price']:
        sc1, sc2, sc3, sc4 = st.columns(4)
        cls = "delta-pos" if info['change_pct'] >= 0 else "delta-neg"
        sgn = "+" if info['change_pct'] >= 0 else ""
        sc1.markdown(
            f'<div class="stat-box-small"><p class="stat-label-small">FİYAT</p>'
            f'<p class="stat-value-small money-text">{info["price"]:.2f}'
            f'<span class="stat-delta-small {cls}">{sgn}{info["change_pct"]:.2f}%</span>'
            f'</p></div>',
            unsafe_allow_html=True
        )
        sc2.markdown(
            f'<div class="stat-box-small"><p class="stat-label-small">HACİM</p>'
            f'<p class="stat-value-small money-text">{info["volume"]/1e6:.1f}M</p></div>',
            unsafe_allow_html=True
        )
        sc3.markdown(
            f'<div class="stat-box-small"><p class="stat-label-small">HEDEF</p>'
            f'<p class="stat-value-small money-text">{info["target"]}</p></div>',
            unsafe_allow_html=True
        )
        sc4.markdown(
            f'<div class="stat-box-small"><p class="stat-label-small">SEKTÖR</p>'
            f'<p class="stat-value-small">{str(info["sector"])[:12]}</p></div>',
            unsafe_allow_html=True
        )

    # TradingView grafiği
    st.write("")
    st.subheader(f"📈 {current_ticker} Grafiği (TradingView)")
    render_tradingview_widget(current_ticker, height=550)

    # Sinyal özeti
    st.markdown(get_signal_summary_html(current_ticker), unsafe_allow_html=True)

    # Haber akışı
    st.write("")
    st.subheader("📡 Haber Akışı")
    news_data = fetch_google_news(current_ticker)
    with st.container(height=350):
        if news_data:
            for n in news_data:
                st.markdown(
                    f"""<div class="news-card" style="border-left-color: {n['color']};">
                    <a href="{n['link']}" target="_blank" class="news-title">{n['title']}</a>
                    <div class="news-meta">{n['date']} • {n['source']}</div>
                    </div>""",
                    unsafe_allow_html=True
                )
        else:
            st.info("Haber akışı yok.")

# --- SAĞ SÜTUN ---
with col_main_right:
    st.subheader("📡 Tarama Paneli")

    tab1, tab2, tab3 = st.tabs(["🧠 RADAR 1", "🚀 RADAR 2", "📜 Watchlist"])

    # --- RADAR 1 TAB ---
    with tab1:
        with st.expander("ℹ️ 8'li Puan Sistemi (V3.2.0)", expanded=True):
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
            </div>
            """, unsafe_allow_html=True)

        if st.button(f"⚡ {current_category} Tara (RADAR 1)", type="primary"):
            with st.spinner("Piyasa taranıyor (RADAR 1)..."):
                scan_df = analyze_market_intelligence(ASSET_GROUPS.get(current_category, []))
                st.session_state.scan_data = scan_df
                add_to_log("radar1_log", current_category, scan_df)

        with st.container(height=230):
            df = st.session_state.scan_data
            if df is not None:
                if not df.empty:
                    for index, row in df.iterrows():
                        cols = st.columns([0.18, 0.82])
                        symbol = row["Sembol"]
                        star_label = "★" if symbol in st.session_state.watchlist else "☆"
                        if cols[0].button(star_label, key=f"radar1_star_{symbol}_{index}"):
                            toggle_watchlist(symbol)
                            st.rerun()

                        score = row['Skor']
                        icon = "🔥" if score >= 7 else "✅" if score >= 4 else "⚠️"
                        label = f"{icon} {score}/8 | {symbol}"
                        if cols[1].button(label, key=f"radar1_btn_{symbol}_{index}"):
                            on_scan_result_click(symbol)
                            st.rerun()
                        st.markdown(
                            f"<div style='font-size:0.6rem; color:#64748B; "
                            f"margin-top:-8px; margin-bottom:4px; padding-left:5px;'>{row['Nedenler']}</div>",
                            unsafe_allow_html=True
                        )
                else:
                    st.info("Güçlü sinyal yok.")
            else:
                st.info("Tara butonuna basın.")

        with st.expander("🕒 Geçmiş Taramalar (oturum içi)"):
            logs = st.session_state.radar1_log
            if logs:
                for e in logs:
                    st.write(f"- {e['time']} • {e['category']} • {e['count']} sinyal")
            else:
                st.caption("Henüz kayıt yok.")

    # --- RADAR 2 TAB ---
    with tab2:
        with st.expander("ℹ️ RADAR 2 Mantığı", expanded=True):
            st.markdown("""
            <div style="font-size:0.7rem;">
            <b>Filtreler:</b><br>
            • Fiyat aralığı (varsayılan: 5–500 USD)<br>
            • 20 günlük ortalama hacim (varsayılan: ≥ 1M)<br><br>
            <b>Trend Rejimi:</b><br>
            • <b>Boğa:</b> Fiyat &gt; 50 &gt; 100 &gt; 200 MA ve 200 MA yukarı eğimli<br>
            • <b>Ayı:</b> Fiyat 200 MA altında ve 200 MA aşağı eğimli<br>
            • <b>Yatay:</b> Diğer durumlar<br><br>
            <b>Setup Tipleri:</b><br>
            • <b>Breakout:</b> Boğa trendi + son 60 gün zirvesine çok yakın + hacim artışı<br>
            • <b>Pullback:</b> Boğa trendi içinde 20–50 MA bölgesine geri çekilme + RSI 40–55<br>
            • <b>Dip Dönüşü:</b> RSI &lt;30'dan yukarı kesmiş + MACD histogram artıyor<br><br>
            <b>RS (Relative Strength):</b><br>
            • Son 60 günde S&P 500'den göreli fark (%). Pozitif ise endeksi yeniyor.<br>
            </div>
            """, unsafe_allow_html=True)

        profile = st.selectbox(
            "Profil",
            ["Swing", "Position", "Emerging Breakout", "Custom"],
            key="radar2_profile"
        )

        if profile == "Swing":
            suggested = (5.0, 300.0, 1.0)
        elif profile == "Position":
            suggested = (20.0, 500.0, 2.0)
        elif profile == "Emerging Breakout":
            suggested = (5.0, 100.0, 0.5)
        else:
            suggested = None

        col_r2_l, col_r2_r = st.columns(2)
        with col_r2_l:
            if suggested:
                st.caption(f"Öneri • Min: {suggested[0]}, Max: {suggested[1]}, Hacim≥ {suggested[2]}M")
            min_price = st.number_input(
                "Min Fiyat",
                value=suggested[0] if suggested else 5.0,
                step=1.0
            )
            max_price = st.number_input(
                "Max Fiyat",
                value=suggested[1] if suggested else 500.0,
                step=5.0
            )
        with col_r2_r:
            min_vol = st.number_input(
                "Min 20G Ortalama Hacim (M)",
                value=suggested[2] if suggested else 1.0,
                step=0.5
            )

        if st.button(f"🚀 {current_category} RADAR 2 Tara", type="primary"):
            with st.spinner("Piyasa taranıyor (RADAR 2)..."):
                radar_df = radar2_scan(
                    ASSET_GROUPS.get(current_category, []),
                    min_price=min_price,
                    max_price=max_price,
                    min_avg_vol_m=min_vol
                )
                st.session_state.radar2_data = radar_df
                add_to_log("radar2_log", current_category, radar_df)

        with st.container(height=230):
            df2 = st.session_state.radar2_data
            if df2 is not None:
                if not df2.empty:
                    for index, row in df2.iterrows():
                        cols = st.columns([0.18, 0.82])
                        symbol = row["Sembol"]
                        star_label = "★" if symbol in st.session_state.watchlist else "☆"
                        if cols[0].button(star_label, key=f"radar2_star_{symbol}_{index}"):
                            toggle_watchlist(symbol)
                            st.rerun()

                        icon = "🚀" if row["Setup"] == "Breakout" else "🔁" if row["Setup"] == "Pullback" else "🩹"
                        label = f"{icon} {symbol} | {row['Trend']} | {row['Setup']} | Skor: {row['Skor']}"
                        if cols[1].button(label, key=f"radar2_btn_{symbol}_{index}"):
                            on_scan_result_click(symbol)
                            st.rerun()
                        sub = f"Fiyat: {row['Fiyat']} • RS: {row['RS']}% • {row['Etiketler']}"
                        st.markdown(
                            f"<div style='font-size:0.6rem; color:#64748B; "
                            f"margin-top:-6px; margin-bottom:4px; padding-left:5px;'>{sub}</div>",
                            unsafe_allow_html=True
                        )
                else:
                    st.info("Filtrelere uyan hisse bulunamadı.")
            else:
                st.info("RADAR 2 için tara butonuna basın.")

        with st.expander("🕒 Geçmiş Taramalar (oturum içi)"):
            logs2 = st.session_state.radar2_log
            if logs2:
                for e in logs2:
                    st.write(f"- {e['time']} • {e['category']} • {e['count']} sinyal")
            else:
                st.caption("Henüz kayıt yok.")

    # --- WATCHLIST TAB ---
    with tab3:
        wl = st.session_state.watchlist
        if not wl:
            st.info("Watchlist boş. RADAR sonuçlarından ⭐ ile hisse ekleyebilirsin.")
        else:
            st.write("Takip listendeki hisseler:")
            for symbol in wl:
                cols = st.columns([0.2, 0.5, 0.3])
                if cols[0].button("❌", key=f"wl_del_{symbol}"):
                    toggle_watchlist(symbol)
                    st.rerun()
                if cols[1].button(symbol, key=f"wl_go_{symbol}"):
                    on_scan_result_click(symbol)
                    st.rerun()
                cols[2].write("")

            st.markdown("---")
            st.caption("Watchlist üzerinde hızlı tarama:")

            col_wl1, col_wl2 = st.columns(2)
            with col_wl1:
                if st.button("⚡ RADAR 1 ile Tara (WL)"):
                    with st.spinner("Watchlist RADAR 1 taranıyor..."):
                        df_wl1 = analyze_market_intelligence(wl)
                        st.session_state.scan_data = df_wl1
                        add_to_log("radar1_log", "WATCHLIST", df_wl1)
            with col_wl2:
                if st.button("🚀 RADAR 2 ile Tara (WL)"):
                    with st.spinner("Watchlist RADAR 2 taranıyor..."):
                        df_wl2 = radar2_scan(wl)
                        st.session_state.radar2_data = df_wl2
                        add_to_log("radar2_log", "WATCHLIST", df_wl2)

    # --- POZİSYON HESAPLAMA ---
    st.markdown("---")
    with st.expander("🧮 Pozisyon Hesaplama", expanded=False):
        if not info or not info.get("price"):
            st.info("Aktif hissenin fiyatını çekemedim.")
        else:
            acc = st.number_input("Hesap Büyüklüğü (USD)", value=10000.0, step=500.0)
            risk_pct = st.number_input("Trade başına risk (%)", value=1.0, step=0.25)
            stop_pct = st.number_input("Stop mesafesi (%)", value=5.0, step=0.5)

            if stop_pct <= 0 or risk_pct <= 0:
                st.warning("Risk ve stop pozitif olmalı.")
            else:
                risk_amount = acc * risk_pct / 100
                per_share_risk = info["price"] * stop_pct / 100
                size = int(risk_amount / per_share_risk) if per_share_risk > 0 else 0

                st.write(f"• Fiyat: **{info['price']:.2f} USD**")
                st.write(f"• Riske edilen tutar: **{risk_amount:.2f} USD**")
                st.write(f"• Maks. pozisyon boyutu: **{size} adet** (yuvarlanmış)")
