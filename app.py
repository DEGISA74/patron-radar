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
st.set_page_config(page_title="Patronun Terminali v3.0.0", layout="wide", page_icon="🦅")

# --- VARLIK LİSTELERİ (150 HİSSE + TEMİZ EMTİA) ---
ASSET_GROUPS = {
    "S&P 500 (TOP 150)": [
        # Teknoloji & Devler
        "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "AMD", 
        "INTC", "QCOM", "TXN", "AMAT", "LRCX", "MU", "ADI", "CSCO", "ORCL", "CRM", 
        "ADBE", "IBM", "ACN", "NOW", "PANW", "SNPS", "CDNS", "KLAC", "NXPI", "APH",
        
        # Finans
        "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "AXP", "V", "MA", "PYPL", "SQ", 
        "SPGI", "MCO", "CB", "MMC", "PGR", "USB", "PNC", "TFC", "COF", "BK", "SCHW",
        
        # Sağlık
        "LLY", "UNH", "JNJ", "MRK", "ABBV", "PFE", "TMO", "DHR", "ABT", "BMY", "AMGN", 
        "ISRG", "SYK", "ELV", "CVS", "CI", "GILD", "REGN", "VRTX", "ZTS", "BSX", "BDX",
        
        # Tüketim & Perakende
        "AMZN", "WMT", "HD", "PG", "COST", "KO", "PEP", "MCD", "SBUX", "NKE", "DIS", 
        "CMCSA", "NFLX", "TGT", "LOW", "TJX", "PM", "MO", "EL", "CL", "K", "GIS", "MNST",
        
        # Sanayi & Enerji & Diğer
        "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HES", "KMI",
        "GE", "CAT", "DE", "HON", "MMM", "ETN", "ITW", "EMR", "PH", "CMI", "PCAR",
        "BA", "LMT", "RTX", "GD", "NOC", "LHX", "TDG", "TXT", "HII",
        "UPS", "FDX", "UNP", "CSX", "NSC", "DAL", "UAL", "AAL", "LUV",
        "AMT", "PLD", "CCI", "EQIX", "PSA", "O", "DLR", "SPG", "VICI",
        "NEE", "DUK", "SO", "AEP", "SRE", "D", "PEG", "ED", "XEL", "PCG"
    ],
    "KRİPTO (TOP 20)": [
        "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", "DOGE-USD", "AVAX-USD", 
        "TRX-USD", "LINK-USD", "DOT-USD", "MATIC-USD", "LTC-USD", "SHIB-USD", "BCH-USD", "UNI-USD", 
        "ATOM-USD", "XLM-USD", "ETC-USD", "FIL-USD"
    ],
    "EMTİA (ALTIN/GÜMÜŞ)": ["GC=F", "SI=F"]
}
ALL_ASSETS = [item for sublist in ASSET_GROUPS.values() for item in sublist]
INITIAL_CATEGORY = "S&P 500 (TOP 150)"

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
    
    .score-badge {
        font-weight: bold; padding: 2px 8px; border-radius: 4px; color: white; font-size: 0.8rem;
    }
    
    .stButton button { width: 100%; border-radius: 5px; }
</style>
""", unsafe_allow_html=True) 

# --- OTURUM YÖNETİMİ ---
if 'ticker' not in st.session_state: st.session_state.ticker = "AAPL"
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
    st.session_state.ticker = symbol

# --- İSTİHBARAT & PUANLAMA MOTORU (MASTER TRADER) ---
def analyze_market_intelligence(asset_list):
    signals = []
    
    # 6 Aylık Veri (Tüm göstergeler için yeterli)
    try:
        data = yf.download(asset_list, period="6mo", group_by='ticker', threads=True, progress=False)
    except Exception:
        return []

    for symbol in asset_list:
        try:
            # VERİ HAZIRLIĞI
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]:
                    df = data[symbol].copy()
                else: continue
            else:
                if len(asset_list) == 1: df = data.copy()
                else: continue

            if df.empty or 'Close' not in df.columns: continue
            df = df.dropna(subset=['Close'])
            if len(df) < 60: continue # Williams%R ve MACD için veri lazım

            # TEMEL SERİLER
            close = df['Close']
            high = df['High']
            low = df['Low']
            volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))

            # --- GÖSTERGE HESAPLAMALARI ---
            
            # 1. EMA (Trend)
            ema5 = close.ewm(span=5, adjust=False).mean()
            ema20 = close.ewm(span=20, adjust=False).mean()
            
            # 2. Bollinger (Squeeze)
            sma20 = close.rolling(20).mean()
            std20 = close.rolling(20).std()
            bb_width = ((sma20 + 2*std20) - (sma20 - 2*std20)) / sma20
            
            # 3. MACD
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            hist = macd_line - signal_line
            
            # 4. RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs_val = gain / loss
            rsi = 100 - (100 / (1 + rs_val))
            
            # 5. Williams %R
            # Formül: (Highest High - Close) / (Highest High - Lowest Low) * -100
            highest_high = high.rolling(14).max()
            lowest_low = low.rolling(14).min()
            williams_r = (highest_high - close) / (highest_high - lowest_low) * -100
            
            # 6. NR4 (Daralma)
            # Range = High - Low
            daily_range = high - low
            # Son 4 günün range'lerini al
            
            # --- PUANLAMA (MUHTEŞEM SEKİZLİ) ---
            score = 0
            reasons = []
            
            # SON DEĞERLER (float)
            curr_c = float(close.iloc[-1])
            prev_c = float(close.iloc[-2])
            curr_vol = float(volume.iloc[-1])
            avg_vol = float(volume.rolling(5).mean().iloc[-1]) if len(volume) > 5 else 1.0
            
            # 1. 🚀 SQUEEZE
            # Bant genişliği son 60 günün en düşüğüne %10 yakınsa
            min_width = bb_width.tail(60).min()
            if bb_width.iloc[-1] <= min_width * 1.1:
                score += 1
                reasons.append("🚀 Squeeze")

            # 2. 🔇 NR4 (Sessizlik)
            # Bugünkü range, son 4 günün en küçüğü mü?
            r_today = daily_range.iloc[-1]
            r_last4 = daily_range.tail(4)
            if r_today == r_last4.min() and r_today > 0:
                score += 1
                reasons.append("🔇 NR4")

            # 3. ⚡ TREND (EMA Cross)
            # EMA5 > EMA20 (Bugün veya Dün Kesişim)
            cross_today = (ema5.iloc[-1] > ema20.iloc[-1]) and (ema5.iloc[-2] <= ema20.iloc[-2])
            cross_yest = (ema5.iloc[-2] > ema20.iloc[-2]) and (ema5.iloc[-3] <= ema20.iloc[-3])
            if cross_today or cross_yest:
                score += 1
                reasons.append("⚡ Trend")

            # 4. 🟢 MACD DÖNÜŞÜ
            # Histogram Yeşile Döndü (Artıyor) VE (Pozitif veya Sığ Negatif)
            h_curr = hist.iloc[-1]
            h_prev = hist.iloc[-2]
            if h_curr > h_prev: # Momentum Artıyor (Yeşil Bar)
                score += 1
                reasons.append("🟢 MACD")

            # 5. 🔫 WILLIAMS %R
            # -50'nin üzerine attı (Momentum)
            wr_curr = williams_r.iloc[-1]
            if wr_curr > -50:
                score += 1
                reasons.append("🔫 Will%R")

            # 6. 🔊 HACİM
            # Hacim ortalamadan %20 fazla
            if curr_vol > avg_vol * 1.2:
                pct = int(((curr_vol - avg_vol)/avg_vol)*100)
                score += 1
                reasons.append(f"🔊 Hacim(+%{pct})")

            # 7. 🔨 BREAKOUT
            # Son 20 günün zirvesine %2 yakınlıkta
            h20 = high.tail(20).max()
            if curr_c >= h20 * 0.98:
                score += 1
                reasons.append("🔨 Breakout")

            # 8. ⚓ GÜVENLİ DİP/GİRİŞ
            # RSI 30-60 arasında ve Yükseliyor (Aşırı şişkin değil, düşmüyor)
            rsi_curr = rsi.iloc[-1]
            rsi_prev = rsi.iloc[-2]
            if 30 < rsi_curr < 65 and rsi_curr > rsi_prev:
                score += 1
                reasons.append("⚓ RSI Güçlü")

            # LİSTEYE EKLE (Sadece Skoru 1 ve üzeri olanlar)
            if score >= 4: # Gürültüyü azaltmak için en az 4 puan şartı koyabiliriz veya hepsini gösteririz.
                # Patron "Sıralama" istedi, hepsini alıp sıralayalım.
                # Ama liste çok şişmesin, en az 3 diyelim.
                pass
            
            if score > 0:
                signals.append({
                    "Sembol": symbol,
                    "Fiyat": f"{curr_c:.2f}",
                    "Skor": score,
                    "Nedenler": " | ".join(reasons),
                    "RSI": round(rsi_curr, 1)
                })

        except Exception: continue
    
    # SONUÇLARI PUANA GÖRE SIRALA (BÜYÜKTEN KÜÇÜĞE)
    if not signals: return pd.DataFrame()
    
    df_res = pd.DataFrame(signals)
    df_res = df_res.sort_values(by="Skor", ascending=False)
    return df_res


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
        return {'price': price, 'change_pct': pct, 'volume': volume, 'sector': info.get('sector', '-'), 'target': info.get('targetMeanPrice', '-'), 'pe': info.get('trailingPE', '-')}
    except: return None

@st.cache_data(ttl=300)
def fetch_google_news(ticker):
    try:
        clean_ticker = ticker.replace(".IS", "").replace("=F", "")
        query = f"{clean_ticker} stock news" if ".IS" not in ticker else f"{clean_ticker} hisse haberleri"
        encoded_query = urllib.parse.quote_plus(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=tr&gl=TR&ceid=TR:tr"
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
st.title("🦅 Patronun Terminali v3.0.0 (Master Trader)")
st.markdown("---")

current_ticker = st.session_state.ticker
current_category = st.session_state.category

# 1. MENÜ
col_cat, col_ass, col_search_in, col_search_btn = st.columns([1.5, 2, 2, 0.7])
with col_cat:
    st.selectbox("Kategori", list(ASSET_GROUPS.keys()), index=list(ASSET_GROUPS.keys()).index(current_category) if current_category in ASSET_GROUPS else 0, key="selected_category_key", on_change=on_category_change)
with col_ass:
    opts = ASSET_GROUPS[current_category]
    try: idx = opts.index(current_ticker)
    except: idx = 0
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
    c4.markdown(f'<div class="stat-box"><div class="stat-label">SEKTÖR</div><div class="stat-value">{str(info["sector"])[:15]}</div></div>', unsafe_allow_html=True)

# 3. ANA EKRAN
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
        else: st.info("Son 10 günde önemli haber yok.")

with col_main_intel:
    st.subheader("🧠 Sentiment Skor Kartı")
    
    with st.expander("ℹ️ 8'li Puan Sistemi"):
        st.markdown("""
        <div style="font-size:0.7rem;">
        <b>1. 🚀 Squeeze:</b> Bollinger Daralması (Patlama Hazırlığı)<br>
        <b>2. 🔇 NR4:</b> En dar gün (Fırtına öncesi sessizlik)<br>
        <b>3. ⚡ Trend:</b> EMA5 > EMA20 Kesişimi<br>
        <b>4. 🟢 MACD:</b> Momentum artışı (Yeşil Bar)<br>
        <b>5. 🔫 Will%R:</b> -50 Kırılımı (Hızlı Kalkış)<br>
        <b>6. 🔊 Hacim:</b> Ortalamanın %20 üzerinde<br>
        <b>7. 🔨 Breakout:</b> Zirve zorluyor<br>
        <b>8. ⚓ RSI Güçlü:</b> 30-65 arası ve yükseliyor
        </div>
        """, unsafe_allow_html=True)

    if st.button(f"⚡ {current_category} Analiz Et", type="primary"):
        with st.spinner(f"{len(ASSET_GROUPS[current_category])} varlık taranıyor..."):
            scan_df = analyze_market_intelligence(ASSET_GROUPS[current_category])
            st.session_state.scan_data = scan_df
    
    with st.container(height=450):
        if st.session_state.scan_data is not None:
            if not st.session_state.scan_data.empty:
                for index, row in st.session_state.scan_data.iterrows():
                    score = row['Skor']
                    # Renk Kodlaması
                    s_color = "#4CAF50" if score >= 6 else "#FF9800" if score >= 4 else "#9E9E9E"
                    label = f"★ {score}/8 | {row['Sembol']}"
                    
                    if st.button(label, key=f"btn_{row['Sembol']}_{index}", use_container_width=True):
                        on_scan_result_click(row['Sembol'])
                        st.rerun()
                    
                    # Detayları butonun altında ufak göster
                    st.markdown(f"<div style='font-size:0.7rem; color:#555; margin-top:-10px; margin-bottom:10px; padding-left:5px;'>{row['Nedenler']}</div>", unsafe_allow_html=True)
            else:
                st.info("Piyasada şu an güçlü bir kurulum (Setup) yok.")
        else:
            st.info("Analiz için butona basın.")

    if st.button("🗑️ Temizle"):
        st.session_state.scan_data = None
        st.rerun()
