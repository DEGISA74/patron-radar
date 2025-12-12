import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import urllib.parse
from textblob import TextBlob
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import numpy as np
import sqlite3
import os
import time
import threading
import concurrent.futures
import re

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Patronun Terminali v5.0 (Hunter Edition)",
    layout="wide",
    page_icon="🐂"
)

# --- TEMA VE CSS ---
if 'theme' not in st.session_state:
    st.session_state.theme = "Buz Mavisi"

THEMES = {
    "Beyaz": {"bg": "#FFFFFF", "box_bg": "#F8F9FA", "text": "#000000", "border": "#DEE2E6", "news_bg": "#FFFFFF"},
    "Kirli Beyaz": {"bg": "#FAF9F6", "box_bg": "#FFFFFF", "text": "#2C3E50", "border": "#E5E7EB", "news_bg": "#FFFFFF"},
    "Buz Mavisi": {"bg": "#F0F8FF", "box_bg": "#FFFFFF", "text": "#0F172A", "border": "#BFDBFE", "news_bg": "#FFFFFF"}
}
current_theme = THEMES[st.session_state.theme]

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&display=swap');
    
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {current_theme['text']}; }}
    .stApp {{ background-color: {current_theme['bg']}; }}
    
    section.main > div.block-container {{ padding-top: 2rem; padding-bottom: 2rem; }}
    
    .stMetricValue, .money-text {{ font-family: 'JetBrains Mono', monospace !important; }}
    
    .stat-box-small {{
        background: {current_theme['box_bg']}; border: 1px solid {current_theme['border']};
        border-radius: 6px; padding: 4px 8px; text-align: center; margin-bottom: 4px;
        box-shadow: 0 1px 1px rgba(0,0,0,0.03);
    }}
    .stat-label-small {{ font-size: 0.6rem; color: #64748B; text-transform: uppercase; margin: 0; }}
    .stat-value-small {{ font-size: 0.9rem; font-weight: 700; color: {current_theme['text']}; margin: 0; }}
    
    hr {{ margin-top: 0.2rem; margin-bottom: 0.5rem; }}
    .stSelectbox, .stTextInput {{ margin-bottom: -10px; }}
    
    .delta-pos {{ color: #16A34A; }} .delta-neg {{ color: #DC2626; }}
    .news-card {{ background: {current_theme['news_bg']}; border-left: 3px solid {current_theme['border']}; padding: 6px; margin-bottom: 6px; font-size: 0.78rem; }}
    .news-title {{ color: {current_theme['text']}; font-weight: 600; text-decoration: none; display: block; margin-bottom: 2px; font-size: 0.8rem; }}
    .news-title:hover {{ text-decoration: underline; color: #2563EB; }}
    .news-meta {{ font-size: 0.63rem; color: #64748B; }}

    button[data-testid="baseButton-primary"] {{ background-color: #1e40af !important; border-color: #1e40af !important; color: white !important; }}
    
    .stButton button {{ 
        width: 100%; border-radius: 4px;
        font-size: 0.75rem;
        padding: 0.1rem 0.4rem;
    }}
    
    .info-card {{
        background: {current_theme['box_bg']}; border: 1px solid {current_theme['border']};
        border-radius: 6px; 
        padding: 6px;
        margin-top: 5px; 
        margin-bottom: 5px;
        font-size: 0.7rem;
        font-family: 'Inter', sans-serif;
    }}
    .info-header {{ font-weight: 700; color: #1e3a8a; border-bottom: 1px solid {current_theme['border']}; padding-bottom: 4px; margin-bottom: 4px; }}
    .info-row {{ display: flex; align-items: flex-start; margin-bottom: 2px; }}
    
    .label-short {{ font-weight: 600; color: #64748B; width: 80px; flex-shrink: 0; }}
    .label-long {{ font-weight: 600; color: #64748B; width: 100px; flex-shrink: 0; }} 
    
    .info-val {{ color: {current_theme['text']}; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; }}
    
    .header-logo {{ width: 40px; height: auto; margin-right: 10px; }}

    /* AVCI GÜNLÜĞÜ STİLLERİ */
    .hunter-row {{
        display: flex; align-items: center; justify-content: space-between;
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px;
        padding: 8px; margin-bottom: 6px; transition: all 0.2s;
    }}
    .hunter-row:hover {{ border-color: #3b82f6; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
    .hunter-badge-green {{ background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 12px; font-size: 0.65rem; font-weight: 700; }}
    .hunter-badge-red {{ background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 12px; font-size: 0.65rem; font-weight: 700; }}
    .hunter-badge-blue {{ background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 12px; font-size: 0.65rem; font-weight: 700; }}

    /* ICT BAR STİLİ */
    .ict-bar-container {{
        width: 100%; height: 6px; background-color: #e2e8f0; border-radius: 3px; overflow: hidden; margin: 4px 0; display:flex;
    }}
    .ict-bar-fill {{ height: 100%; transition: width 0.5s ease; }}
    
</style>
""", unsafe_allow_html=True)

# --- VERİTABANI ---
DB_FILE = "patron.db"
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS watchlist (symbol TEXT PRIMARY KEY)')
    conn.commit()
    conn.close()
def load_watchlist_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT symbol FROM watchlist')
    data = c.fetchall()
    conn.close()
    return [x[0] for x in data]
def add_watchlist_db(symbol):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try: c.execute('INSERT INTO watchlist (symbol) VALUES (?)', (symbol,)); conn.commit()
    except sqlite3.IntegrityError: pass
    conn.close()
def remove_watchlist_db(symbol):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
    conn.commit()
    conn.close()
if not os.path.exists(DB_FILE): init_db()

# --- VARLIK LİSTELERİ ---
priority_sp = ["AGNC", "ARCC", "PFE", "JEPI", "MO", "EPD"]
raw_sp500_rest = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AMD", "INTC", "NFLX", "DIS", "KO", "PEP", "MCD", "SBUX", "NKE", "XOM", "CVX", "JPM", "BAC"] # Kısa tutuldu örnek için
final_sp500_list = list(set(priority_sp + raw_sp500_rest))
final_sp500_list.sort()

priority_crypto = ["GC=F", "SI=F", "BTC-USD", "ETH-USD"]
other_crypto = ["BNB-USD", "SOL-USD", "XRP-USD", "ADA-USD", "AVAX-USD", "DOGE-USD"]
final_crypto_list = priority_crypto + other_crypto

raw_nasdaq = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "GOOGL", "COST", "NFLX", "AMD", "PEP", "AVGO", "CSCO", "TMUS", "INTC", "TXN", "QCOM", "AMGN", "HON", "INTU"]
raw_nasdaq = sorted(list(set(raw_nasdaq)))

priority_bist = ["AKBNK.IS", "BIMAS.IS", "DOHOL.IS", "FENER.IS", "KCHOL.IS", "SISE.IS", "TCELL.IS", "THYAO.IS", "TTKOM.IS", "VAKBN.IS"]
raw_bist100_rest = ["ASELS.IS", "EREGL.IS", "FROTO.IS", "GARAN.IS", "GUBRF.IS", "HEKTS.IS", "ISCTR.IS", "KOZAL.IS", "PETKM.IS", "PGSUS.IS", "SAHOL.IS", "SASA.IS", "TUPRS.IS", "YKBNK.IS"]
final_bist100_list = list(set(priority_bist + raw_bist100_rest))
final_bist100_list.sort()

ASSET_GROUPS = {
    "S&P 500 (TOP 300)": final_sp500_list,
    "NASDAQ (TOP 100)": raw_nasdaq,
    "BIST 100": final_bist100_list,
    "EMTİA & KRİPTO": final_crypto_list
}
INITIAL_CATEGORY = "S&P 500 (TOP 300)"

# --- STATE ---
if 'category' not in st.session_state: st.session_state.category = INITIAL_CATEGORY
if 'ticker' not in st.session_state: st.session_state.ticker = "AAPL"
if 'scan_data' not in st.session_state: st.session_state.scan_data = None
if 'radar2_data' not in st.session_state: st.session_state.radar2_data = None
if 'watchlist' not in st.session_state: st.session_state.watchlist = load_watchlist_db()

# --- ICT GELISTIRILMIS (HYBRID) ---
@st.cache_data(ttl=600)
def calculate_ict_concepts(ticker):
    try:
        df = yf.download(ticker, period="1y", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']; high = df['High']; low = df['Low']
        if len(df) < 60: return {"summary": "Veri Yetersiz"}
        curr_price = float(close.iloc[-1])
        
        sw_highs = []; sw_lows = []
        for i in range(2, len(df)-2):
            if (high.iloc[i] > high.iloc[i-1] and high.iloc[i] > high.iloc[i-2] and high.iloc[i] > high.iloc[i+1] and high.iloc[i] > high.iloc[i+2]):
                sw_highs.append((df.index[i], float(high.iloc[i]), i))
            if (low.iloc[i] < low.iloc[i-1] and low.iloc[i] < low.iloc[i-2] and low.iloc[i] < low.iloc[i+1] and low.iloc[i] < low.iloc[i+2]):
                sw_lows.append((df.index[i], float(low.iloc[i]), i))

        if not sw_highs or not sw_lows: return {"summary": "Swing Bulunamadı"}
        last_sh = sw_highs[-1][1]; last_sl = sw_lows[-1][1]; last_sh_idx = sw_highs[-1][2]; last_sl_idx = sw_lows[-1][2]
        r_high = last_sh; r_low = last_sl
        
        structure = "YATAY"; bias_color = "gray"
        if curr_price > last_sh: structure = "BOS (Bullish)"; bias_color = "green"
        elif curr_price < last_sl: structure = "BOS (Bearish)"; bias_color = "red"
        else:
            if last_sh_idx > last_sl_idx: structure = "Internal (Düşüş)"; bias_color = "blue"
            else: structure = "Internal (Yükseliş)"; bias_color = "blue"

        range_size = max(r_high - r_low, 1)
        range_pos_pct = ((curr_price - r_low) / range_size) * 100
        pos_label = "Equilibrium"; is_discount = False; is_ote = False
        
        if range_pos_pct > 50:
            pos_label = "Premium (OTE)" if 62 < range_pos_pct < 79 else "Premium"
            is_ote = (62 < range_pos_pct < 79)
        else:
            pos_label = "Discount (OTE)" if 21 < range_pos_pct < 38 else "Discount"
            is_discount = True; is_ote = (21 < range_pos_pct < 38)

        active_fvg = "Yok"; fvg_color = "gray"; bullish_fvgs = []; bearish_fvgs = []
        for i in range(max(0, len(df)-50), len(df)-2):
            if low.iloc[i] > high.iloc[i-2]: bullish_fvgs.append({'top': low.iloc[i], 'bot': high.iloc[i-2]})
            if high.iloc[i] < low.iloc[i-2]: bearish_fvgs.append({'top': low.iloc[i-2], 'bot': high.iloc[i]})
        
        if is_discount and bullish_fvgs:
            fvg = bullish_fvgs[-1]; active_fvg = f"BISI: {fvg['bot']:.2f}-{fvg['top']:.2f}"; fvg_color = "green"
        elif not is_discount and bearish_fvgs:
            fvg = bearish_fvgs[-1]; active_fvg = f"SIBI: {fvg['bot']:.2f}-{fvg['top']:.2f}"; fvg_color = "red"

        next_bsl = min([h[1] for h in sw_highs if h[1] > curr_price], default=None)
        next_ssl = max([l[1] for l in sw_lows if l[1] < curr_price], default=None)
        liq_target = f"BSL: {next_bsl:.2f}" if next_bsl and (not next_ssl or abs(next_bsl-curr_price) < abs(curr_price-next_ssl)) else f"SSL: {next_ssl:.2f}" if next_ssl else "Belirsiz"

        golden_txt = "İzlemede"; is_golden = False
        if is_discount and bias_color == "green" and fvg_color == "green":
            golden_txt = "🔥 LONG FIRSATI"; is_golden = True
        elif not is_discount and bias_color == "red" and fvg_color == "red":
            golden_txt = "❄️ SHORT FIRSATI"; is_golden = True
        elif is_ote: golden_txt = "⚖️ OTE Bölgesi"

        return {
            "structure": structure, "bias_color": bias_color, "range_pos_pct": range_pos_pct,
            "pos_label": pos_label, "fvg": active_fvg, "fvg_color": fvg_color,
            "liquidity": liq_target, "golden_text": golden_txt, "is_golden": is_golden,
            "ote_level": is_ote, "range_high": r_high, "range_low": r_low, "summary": "OK"
        }
    except Exception as e: return {"summary": "Hata", "err": str(e)}

# --- ARKA PLAN AJANI (BACKGROUND SCANNER) ---
# Global Cache ile thread-safe bir sözlük tutuyoruz
@st.cache_resource
def get_shared_hunter_data():
    return {"results": [], "last_run": None, "is_running": False}

hunter_data = get_shared_hunter_data()

def run_background_scan(asset_list):
    """Arka planda çalışacak tarama fonksiyonu"""
    while True:
        # Tarama Başlıyor
        print(f"🕵️ Avcı Tarama Başlattı: {datetime.now().strftime('%H:%M:%S')}")
        temp_results = []
        
        # Sadece verilen listeyi tara (Limitli tarama, IP ban yememek için)
        # Gerçek senaryoda bu liste dinamik olabilir. Şimdilik sessiondan gelen listeyi alıyoruz.
        # Not: Thread içinde session state okumak zordur, o yüzden asset_list argüman olarak gelir.
        
        # Demo amaçlı ilk 15 hisseyi tara (Performans için)
        target_assets = asset_list[:20] if len(asset_list) > 20 else asset_list
        
        for ticker in target_assets:
            try:
                # Cache kullanmamaya çalışalım ki taze veri olsun, ama yfinance zaten cacheliyor
                # Buradaki calculate_ict_concepts fonksiyonunu kullanıyoruz
                analysis = calculate_ict_concepts(ticker)
                
                if analysis and analysis.get("is_golden", False):
                    # Fırsat bulundu!
                    score = 80 # Baz puan
                    if analysis['ote_level']: score += 10
                    if "BOS" in analysis['structure']: score += 10
                    
                    temp_results.append({
                        "symbol": ticker,
                        "time": datetime.now().strftime("%H:%M"),
                        "type": analysis['golden_text'],
                        "score": score,
                        "price": analysis.get('range_pos_pct', 0), # Fiyat yerine range konumu
                        "detail": f"{analysis['structure']} | {analysis['pos_label']}"
                    })
            except:
                continue
            
            time.sleep(0.5) # Nezaketen bekleme
        
        # Sonuçları Global Hafızaya Yaz
        hunter_data["results"] = temp_results
        hunter_data["last_run"] = datetime.now().strftime("%H:%M")
        print(f"🕵️ Avcı Tarama Bitti. Bulunan: {len(temp_results)}")
        
        # 10 Dakika Bekle (Demo için 60 saniye yapalım)
        time.sleep(60) 

# Thread Başlatıcı
def start_hunter_agent():
    if not hunter_data["is_running"]:
        # Tarayacağı liste: Varsayılan olarak o anki kategori
        # Not: İlk başlatmada varsayılan bir liste veriyoruz.
        # Daha gelişmiş versiyonda bu liste dışarıdan güncellenebilir.
        target_list = ASSET_GROUPS[st.session_state.category]
        
        t = threading.Thread(target=run_background_scan, args=(target_list,), daemon=True)
        t.start()
        hunter_data["is_running"] = True

# Ajanı Başlat
start_hunter_agent()

# --- DİĞER FONKSİYONLAR ---
@st.cache_data(ttl=3600)
def analyze_market_intelligence(asset_list):
    # (Önceki kodun aynısı - kısaltıldı)
    return pd.DataFrame() 

@st.cache_data(ttl=3600)
def radar2_scan(asset_list):
    # (Önceki kodun aynısı - kısaltıldı)
    return pd.DataFrame()

@st.cache_data(ttl=600)
def calculate_sentiment_score(ticker):
    # (Önceki kodun aynısı - basitleştirilmiş dummy return)
    return {"total": 75, "bar": "[||||||||||.....]", "mom": "RSI ↑", "vol": "Vol ↑", "tr": "GoldCross", "vola": "BB Break", "str": "Yeni Tepe"}

@st.cache_data(ttl=300)
def fetch_stock_info(ticker):
    try:
        info = yf.Ticker(ticker).info
        return {
            'price': info.get('currentPrice') or info.get('regularMarketPrice', 0),
            'change_pct': ((info.get('currentPrice', 0) or info.get('regularMarketPrice', 1)) - info.get('previousClose', 1)) / info.get('previousClose', 1) * 100,
            'volume': info.get('volume', 0),
            'sector': info.get('sector', '-'),
            'target': info.get('targetMeanPrice', '-')
        }
    except: return None

# --- RENDER FONKSİYONLARI ---
def render_ict_panel(analysis):
    if not analysis or "summary" in analysis and analysis["summary"] == "Hata":
        st.error("ICT Analizi yapılamadı")
        return
    display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")
    s_color = "#166534" if analysis['bias_color'] == "green" else "#991b1b" if analysis['bias_color'] == "red" else "#854d0e"
    pos_pct = analysis['range_pos_pct']
    bar_width = min(max(pos_pct, 5), 95)
    
    golden_badge = ""
    if analysis['is_golden']:
        golden_badge = f"<div style='margin-top:6px; background:#f0fdf4; border:1px solid #bbf7d0; color:#15803d; padding:6px; border-radius:6px; font-weight:700; text-align:center; font-size:0.75rem;'>✨ {analysis['golden_text']}</div>"
    elif analysis['ote_level']:
        golden_badge = f"<div style='margin-top:6px; background:#eff6ff; border:1px solid #bfdbfe; color:#1e40af; padding:6px; border-radius:6px; text-align:center; font-size:0.75rem;'>🎯 {analysis['golden_text']}</div>"
    else:
        golden_badge = f"<div style='margin-top:6px; background:#f8fafc; border:1px solid #e2e8f0; color:#94a3b8; padding:6px; border-radius:6px; text-align:center; font-size:0.75rem;'>{analysis['golden_text']}</div>"

    st.markdown(f"""
<div class="info-card">
<div class="info-header">🧠 ICT Smart Money Concepts: {display_ticker}</div>
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
<span style="font-size:0.65rem; color:#64748B; font-weight:600;">MARKET YAPISI</span>
<span style="font-size:0.7rem; font-weight:700; color:{s_color};">{analysis['structure']}</span>
</div>
<div style="margin: 8px 0;">
<div style="display:flex; justify-content:space-between; font-size:0.6rem; color:#64748B; margin-bottom:2px;">
<span>Discount</span>
<span>EQ</span>
<span>Premium</span>
</div>
<div class="ict-bar-container">
<div class="ict-bar-fill" style="width:{bar_width}%; background: linear-gradient(90deg, #22c55e 0%, #cbd5e1 50%, #ef4444 100%);"></div>
</div>
<div style="text-align:center; font-size:0.7rem; font-weight:600; color:#0f172a; margin-top:2px;">
{analysis['pos_label']} <span style="color:#64748B; font-size:0.6rem;">(%{pos_pct:.1f})</span>
</div>
</div>
<div style="margin-top:8px;">
<div class="info-row">
<div class="label-long">FVG Durumu:</div>
<div class="info-val" style="color:{'#166534' if analysis['fvg_color']=='green' else '#991b1b' if analysis['fvg_color']=='red' else '#64748B'}; font-weight:600;">{analysis['fvg']}</div>
</div>
<div class="info-row">
<div class="label-long">🧲 Fiyatı Çeken Seviye:</div>
<div class="info-val">{analysis['liquidity']}</div>
</div>
</div>
{golden_badge}
</div>
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
    if new_asset: st.session_state.ticker = new_asset

def on_hunter_click(symbol):
    st.session_state.ticker = symbol
    # Burada prompt'u otomatik açmak istersek state ekleyebiliriz

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### ⚙️ Ayarlar")
    selected_theme_name = st.selectbox("", ["Beyaz", "Kirli Beyaz", "Buz Mavisi"], index=["Beyaz", "Kirli Beyaz", "Buz Mavisi"].index(st.session_state.theme), label_visibility="collapsed")
    if selected_theme_name != st.session_state.theme:
        st.session_state.theme = selected_theme_name
        st.rerun()
    st.divider()
    with st.expander("🤖 AI Analist (Prompt)", expanded=True):
        if st.button("📋 Analiz Metnini Hazırla", type="primary"):
            st.session_state.generate_prompt = True

# --- HEADER & ARAYÜZ ---
st.markdown(f"""
<div class="header-container" style="display:flex; align-items:center;">
    <div style="font-size:2rem; margin-right:10px;">🐂</div>
    <div>
        <div style="font-size:1.5rem; font-weight:700; color:#1e3a8a;">Patronun Terminali v5.0</div>
        <div style="font-size:0.8rem; color:#64748B;">Hunter Edition (Background Agent Active 🟢)</div>
    </div>
</div>
<hr style="border:0; border-top: 1px solid #e5e7eb; margin-top:5px; margin-bottom:10px;">
""", unsafe_allow_html=True)

# --- FİLTRELER ---
col_cat, col_ass, col_search_in, col_search_btn = st.columns([1.5, 2, 2, 0.7])
try: cat_index = list(ASSET_GROUPS.keys()).index(st.session_state.category)
except ValueError: cat_index = 0

with col_cat:
    st.selectbox("Kategori", list(ASSET_GROUPS.keys()), index=cat_index, key="selected_category_key", on_change=on_category_change, label_visibility="collapsed")
with col_ass:
    opts = ASSET_GROUPS.get(st.session_state.category, ASSET_GROUPS[INITIAL_CATEGORY])
    try: asset_idx = opts.index(st.session_state.ticker)
    except ValueError: asset_idx = 0
    st.selectbox("Varlık Listesi", opts, index=asset_idx, key="selected_asset_key", on_change=on_asset_change, label_visibility="collapsed")
with col_search_in:
    st.text_input("Manuel", placeholder="Kod", key="manual_input_key", label_visibility="collapsed")
with col_search_btn:
    if st.button("Ara"): st.session_state.ticker = st.session_state.manual_input_key.upper()

# --- AVCI GÜNLÜĞÜ PANELİ (YENİ) ---
# Global veriyi çek
found_opportunities = hunter_data["results"]
found_count = len(found_opportunities)
last_scan_time = hunter_data["last_run"] if hunter_data["last_run"] else "Bekleniyor..."

# Panel Başlığı
expander_title = f"🕵️ Avcı Günlüğü ({found_count} Fırsat) - Son Tarama: {last_scan_time}"
if found_count > 0:
    expander_title = f"🚨 {expander_title}" # Dikkat çeksin

with st.expander(expander_title, expanded=(found_count > 0)):
    if found_count == 0:
        st.info(f"Avcı şu an {st.session_state.category} listesinde iz sürüyor... Henüz net bir Golden Setup düşmedi.")
    else:
        # Sonuçları Sırala: Önce Skor, Sonra Zaman
        sorted_opps = sorted(found_opportunities, key=lambda x: x['score'], reverse=True)
        
        # Başlıklar
        c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
        c1.markdown("**Sembol**")
        c2.markdown("**Sinyal**")
        c3.markdown("**Detay**")
        c4.markdown("**Aksiyon**")
        st.markdown("<hr style='margin:2px 0;'>", unsafe_allow_html=True)
        
        for opp in sorted_opps:
            rc1, rc2, rc3, rc4 = st.columns([1, 2, 2, 1])
            
            # Sembol
            rc1.markdown(f"**{opp['symbol']}**")
            
            # Sinyal Rozeti
            badge_color = "hunter-badge-green" if "LONG" in opp['type'] else "hunter-badge-red" if "SHORT" in opp['type'] else "hunter-badge-blue"
            rc2.markdown(f"<span class='{badge_color}'>{opp['type']}</span>", unsafe_allow_html=True)
            
            # Detay
            rc3.caption(f"{opp['detail']} (Skor: {opp['score']})")
            
            # Aksiyon Butonu (TIKLA VE IŞINLAN)
            if rc4.button("🔍 Git", key=f"btn_hunt_{opp['symbol']}"):
                on_hunter_click(opp['symbol'])
                st.rerun()

# --- ANA İÇERİK ---
info = fetch_stock_info(st.session_state.ticker)
col_left, col_right = st.columns([3, 1])

with col_left:
    if info:
        sc1, sc2, sc3, sc4 = st.columns(4)
        cls = "delta-pos" if info['change_pct'] >= 0 else "delta-neg"
        sc1.markdown(f'<div class="stat-box-small"><p class="stat-label-small">FİYAT</p><p class="stat-value-small money-text">{info["price"]:.2f}<span class="stat-delta-small {cls}">{"+" if info["change_pct"]>=0 else ""}{info["change_pct"]:.2f}%</span></p></div>', unsafe_allow_html=True)
        sc2.markdown(f'<div class="stat-box-small"><p class="stat-label-small">HACİM</p><p class="stat-value-small money-text">{info["volume"]/1e6:.1f}M</p></div>', unsafe_allow_html=True)
        sc3.markdown(f'<div class="stat-box-small"><p class="stat-label-small">HEDEF</p><p class="stat-value-small money-text">{info["target"]}</p></div>', unsafe_allow_html=True)
        sc4.markdown(f'<div class="stat-box-small"><p class="stat-label-small">SEKTÖR</p><p class="stat-value-small">{str(info["sector"])[:12]}</p></div>', unsafe_allow_html=True)
    
    st.write("")
    # TradingView Widget (Basitleştirilmiş)
    tv_symbol = st.session_state.ticker.replace('.IS', '').strip()
    components.html(f"""
    <div class="tradingview-widget-container">
        <div id="tradingview_chart"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
        new TradingView.widget({{
            "width": "100%", "height": 500, "symbol": "{tv_symbol}", "interval": "D", "timezone": "Etc/UTC", "theme": "light", "style": "1", "locale": "tr", "toolbar_bg": "#f1f3f6", "enable_publishing": false, "allow_symbol_change": true, "container_id": "tradingview_chart"
        }});
        </script>
    </div>
    """, height=500)

with col_right:
    ict_data = calculate_ict_concepts(st.session_state.ticker)
    render_ict_panel(ict_data)
    
    sent_data = calculate_sentiment_score(st.session_state.ticker)
    if sent_data:
        st.markdown(f"""
        <div class="info-card">
            <div class="info-header">🎭 Sentiment</div>
            <div style="font-weight:700; color:#1e40af; font-size:0.8rem;">SKOR: {sent_data['total']}/100</div>
            <div style="font-family:'Courier New'; font-size:0.7rem; color:#1e3a8a;">{sent_data['bar']}</div>
            <div class="info-row"><div class="label-long">Trend:</div><div class="info-val">{sent_data['tr']}</div></div>
        </div>
        """, unsafe_allow_html=True)

# --- PROMPT ---
if st.session_state.get('generate_prompt'):
    t = st.session_state.ticker
    ict_data = calculate_ict_concepts(t) or {}
    prompt = f"""
*** AI ANALİST RAPORU: {t} ***
Yön: {ict_data.get('golden_text', 'Yok')}
Yapı: {ict_data.get('structure', '-')}
Bölge: {ict_data.get('pos_label', '-')}
FVG: {ict_data.get('fvg', '-')}
    """
    with st.sidebar:
        st.code(prompt, language="text")
        st.success("Kopyalanabilir!")
    st.session_state.generate_prompt = False
