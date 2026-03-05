import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import urllib.parse
from ta.volume import VolumeWeightedAveragePrice
from textblob import TextBlob
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import numpy as np
import sqlite3
import os
import concurrent.futures
import re
import altair as alt
import random
import os

CACHE_DIR = "veriler"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# ==============================================================================
# 1. AYARLAR VE STİL
# ==============================================================================
st.set_page_config(
    page_title="SMART MONEY RADAR", 
    layout="wide",
    page_icon="💸"
)

# Tema seçeneği kaldırıldı, varsayılan "Buz Mavisi" olarak sabitlendi.
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
    section[data-testid="stSidebar"] {{ width: 350px !important; }}
    section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] * {{
        font-family: 'Inter', sans-serif !important;
    }}
    /* --- METRIC (SONUÇ KUTULARI) YAZI BOYUTU AYARI --- */
    div[data-testid="stMetricValue"] {{ font-size: 0.7rem !important; }}
    div[data-testid="stMetricLabel"] {{ font-size: 0.7rem !important; font-weight: 700; }}
    div[data-testid="stMetricDelta"] {{ font-size: 0.7rem !important; }}
    /* ------------------------------------------------ */

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght+400;700&display=swap');
    
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {current_theme['text']}; }}
    .stApp {{ background-color: {current_theme['bg']}; }}
    
    section.main > div.block-container {{ padding-top: 1rem; padding-bottom: 1rem; }}
    
    .stMetricValue, .money-text {{ font-family: 'JetBrains Mono', monospace !important; }}
    
    .stat-box-small {{
        background: {current_theme['box_bg']}; border: 1px solid {current_theme['border']};
        border-radius: 4px; padding: 8px; text-align: center; margin-bottom: 10px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }}
    .stat-label-small {{ font-size: 0.6rem; color: #64748B; text-transform: uppercase; margin: 0; font-weight: 700; letter-spacing: 0.5px; }}
    .stat-value-small {{ font-size: 1.1rem; font-weight: 700; color: {current_theme['text']}; margin: 2px 0 0 0; }}
    .stat-delta-small {{ font-size: 0.8rem; margin-left: 6px; font-weight: 600; }}
    
    hr {{ margin-top: 0.2rem; margin-bottom: 0.5rem; }}
    .stSelectbox, .stTextInput {{ margin-bottom: -10px; }}
    
    .delta-pos {{ color: #16A34A; }} .delta-neg {{ color: #DC2626; }}
    .news-card {{ background: {current_theme['news_bg']}; border-left: 3px solid {current_theme['border']}; padding: 6px; margin-bottom: 6px; font-size: 0.78rem; }}
    
    /* --- TARA VE ANA BUTONLAR (PRIMARY - DÜZELTİLMİŞ) --- */
    /* Hem kind="primary" özelliğine hem de testid'ye bakar, ıskalamaz */
    div.stButton > button[kind="primary"],
    div.stButton > button[data-testid="baseButton-primary"] {{
        background-color: #607D8B !important; /* İSTEDİĞİN MAVİ-GRİ RENK */
        border-color: #607D8B !important;
        color: white !important;
        opacity: 1 !important;
        border-radius: 6px;
        font-weight: 600;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}

    /* HOVER (ÜZERİNE GELİNCE) AYARLARI */
    div.stButton > button[kind="primary"]:hover,
    div.stButton > button[data-testid="baseButton-primary"]:hover {{
        background-color: #455A64 !important; /* ÜZERİNE GELİNCE KOYULAŞAN TON */
        border-color: #455A64 !important;
        color: white !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
    }}
    
    /* --- BİREYSEL TARAMA BUTONLARI (SECONDARY - SU YEŞİLİ) --- */
    div.stButton button[data-testid="baseButton-secondary"] {{
        background-color: #E0F7FA !important; /* SU YEŞİLİ ARKA PLAN */
        border: 1px solid #4DD0E1 !important; /* İnce Turkuaz Çerçeve */
        color: #1F2937 !important; /* KOYU GRİ YAZI */
        font-weight: 700 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        transition: all 0.2s ease-in-out;
    }}
    
    div.stButton button[data-testid="baseButton-secondary"]:hover {{
        background-color: #B2EBF2 !important; /* Üzerine gelince biraz koyulaşsın */
        border-color: #00BCD4 !important;
        color: #000000 !important;
        transform: translateY(-1px);
    }}
    
    /* --- GENEL BUTON BOYUT AYARI --- */
    .stButton button {{
        width: 100%;
        border-radius: 6px;
        font-size: 0.75rem;
        padding: 0.1rem 0.4rem;
    }}
    
    .info-card {{
        background: {current_theme['box_bg']}; border: 1px solid {current_theme['border']};
        border-radius: 6px; 
        padding: 6px;
        margin-top: 5px; 
        margin-bottom: 5px;
        font-size: 0.8rem;
        font-family: 'Inter', sans-serif;
    }}
    .info-header {{ font-weight: 700; color: #1e3a8a; border-bottom: 1px solid {current_theme['border']}; padding-bottom: 4px; margin-bottom: 4px; }}
    .info-row {{ display: flex; align-items: flex-start; margin-bottom: 2px; }}
    
    .label-short {{ font-weight: 600; color: #64748B; width: 80px; flex-shrink: 0; }}
    .label-long {{ font-weight: 600; color: #64748B; width: 100px; flex-shrink: 0; }} 
    
    .info-val {{ color: {current_theme['text']}; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; }}
    
    .edu-note {{
        font-size: 0.85rem;
        color: #040561;
        font-style: italic;
        margin-top: 2px;
        margin-bottom: 6px;
        line-height: 1.3;
        padding-left: 0px;
    }}

    .tech-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4px; }}
    .tech-item {{ display: flex; align-items: center; font-size: 0.8rem; }}

    /* --- KUTULARI (CONTAINER) OYNAK/BOYUTLANDIRILABİLİR YAPMA --- */
    /* st.container(height=...) ile oluşturulan kutuları hedefler */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        resize: vertical !important;    /* Dikey boyutlandırmayı açar */
        overflow: auto !important;      /* İçerik taşarsa kaydırma çubuğu çıkarır */
        min-height: 150px !important;   /* Kutunun çok küçülüp kaybolmasını engeller */
        margin-bottom: 10px !important; /* Altına biraz boşluk bırakır */
        border-bottom-right-radius: 8px !important; /* Tutamaç köşesini belirginleştirir */
    }}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. VERİTABANI VE LİSTELER
# ==============================================================================
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
    try:
        c.execute('INSERT INTO watchlist (symbol) VALUES (?)', (symbol,))
        conn.commit()
    except sqlite3.IntegrityError: 
        pass
    conn.close()

def remove_watchlist_db(symbol):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
    conn.commit()
    conn.close()

init_db()

# --- VARLIK LİSTELERİ ---
priority_sp = ["^GSPC", "^DJI", "^NDX", "^IXIC","QQQI", "SPYI", "TSPY", "ARCC", "JEPI"]

# S&P 500'ün Tamamı (503 Hisse - Güncel)
raw_sp500_rest = [
    "A", "AAL", "AAPL", "ABBV", "ABNB", "ABT", "ACGL", "ACN", "ADBE", "ADI", "ADM", "ADP", "ADSK", "AEE", "AEP", "AES", "AFL", "AGNC", "AIG", "AIZ", "AJG", 
    "AKAM", "ALB", "ALGN", "ALL", "ALLE", "AMAT", "AMCR", "AMD", "AME", "AMGN", "AMP", "AMT", "AMTM", "AMZN", "ANET", "ANSS", "AON", "AOS", "APA", 
    "APD", "APH", "APTV", "ARE", "ATO", "AVB", "AVGO", "AVY", "AWK", "AXON", "AXP", "AZO", "BA", "BAC", "BALL", "BAX", "BBWI", "BBY", "BDX", "BEN", 
    "BF-B", "BG", "BIIB", "BK", "BKNG", "BKR", "BLDR", "BLK", "BMY", "BR", "BRK-B", "BRO", "BSX", "BWA", "BX", "BXP", "C", "CAG", "CAH", "CARR", 
    "CAT", "CB", "CBOE", "CBRE", "CCI", "CCL", "CDNS", "CDW", "CE", "CEG", "CF", "CFG", "CHD", "CHRW", "CHTR", "CI", "CINF", "CL", "CLX", "CMCSA", 
    "CME", "CMG", "CMI", "CMS", "CNC", "CNP", "COF", "COO", "COP", "COR", "COST", "CPAY", "CPB", "CPRT", "CPT", "CRL", "CRM", "CRWD", "CSCO", 
    "CSGP", "CSX", "CTAS", "CTRA", "CTSH", "CTVA", "CVS", "CVX", "CZR", "D", "DAL", "DAY", "DD", "DE", "DECK", "DFS", "DG", "DGX", "DHI", "DHR", 
    "DIS", "DLR", "DLTR", "DOC", "DOV", "DOW", "DPZ", "DRI", "DTE", "DUK", "DVA", "DVN", "DXCM", "EA", "EBAY", "ECL", "ED", "EFX", "EG", "EIX", 
    "EL", "ELV", "EMN", "EMR", "ENPH", "EOG", "EQIX", "EQR", "EQT", "ERIE", "ES", "ESS", "ETN", "ETR", "EVRG", "EW", "EXC", "EXPD", "EXPE", "EXR", 
    "F", "FANG", "FAST", "FCX", "FDS", "FDX", "FE", "FFIV", "FI", "FICO", "FIS", "FITB", "FMC", "FOX", "FOXA", "FRT", "FSLR", "FTNT", "FTV", "GD", 
    "GE", "GEHC", "GEN", "GEV", "GILD", "GIS", "GL", "GLW", "GM", "GNRC", "GOOG", "GOOGL", "GPC", "GPN", "GRMN", "GS", "GWW", "HAL", "HAS", "HBAN", 
    "HCA", "HD", "HES", "HIG", "HII", "HLT", "HOLX", "HON", "HPE", "HPQ", "HRL", "HSY", "HUBB", "HUM", "HWM", "IBM", "ICE", "IDXX", "IEX", "IFF", 
    "ILMN", "INCY", "INTC", "INTU", "INVH", "IP", "IPG", "IQV", "IR", "IRM", "ISRG", "IT", "ITW", "IVZ", "J", "JBHT", "JBL", "JCI", "JEPQ", "JKHY", "JNJ", 
    "JNPR", "JPM", "K", "KDP", "KEY", "KEYS", "KHC", "KIM", "KKR", "KLAC", "KMB", "KMI", "KMX", "KO", "KR", "KVUE", "L", "LDOS", "LEN", "LH", 
    "LHX", "LIN", "LKQ", "LLY", "LMT", "LNT", "LOW", "LRCX", "LULU", "LUV", "LVS", "LW", "LYB", "LYV", "MA", "MAA", "MAR", "MAS", "MCD", "MCHP", 
    "MCK", "MCO", "MDLZ", "MDT", "MET", "META", "MGM", "MHK", "MKC", "MKTX", "MLM", "MMC", "MMM", "MNST", "MO", "MOH", "MOS", "MPC", "MPWR", "MRK", 
    "MRNA", "MS", "MSCI", "MSFT", "MSI", "MTB", "MTCH", "MTD", "MU", "NCLH", "NDSN", "NEE", "NEM", "NFLX", "NI", "NKE", "NOC", "NOW", "NRG", "NSC", 
    "NTAP", "NTRS", "NUE", "NVDA", "NVR", "NWS", "NWSA", "NXPI", "O", "ODFL", "OKE", "OMC", "ON", "ORCL", "ORLY", "OTIS", "OXY", "PANW", "PARA", 
    "PAYC", "PAYX", "PCAR", "PCG", "PEG", "PEP", "PFE", "PFG", "PG", "PGR", "PH", "PHM", "PKG", "PLD", "PLTR", "PM", "PNC", "PNR", "PNW", "POOL", 
    "PPG", "PPL", "PRU", "PSA", "PSX", "PTC", "PWR", "PYPL", "QCOM", "QRVO", "RCL", "REG", "REGN", "RF", "RJF", "RL", "RMD", "ROK", "ROL", "ROP", 
    "ROST", "RSG", "RTX", "RVTY", "SBAC", "SBUX", "SCHW", "SHW", "SJM", "SLB", "SMCI", "SNA", "SNPS", "SO", "SOLV", "SPG", "SPGI", "SRCL", "SRE", 
    "STE", "STLD", "STT", "STX", "STZ", "SW", "SWK", "SWKS", "SYF", "SYK", "SYY", "T", "TAP", "TDG", "TDY", "TECH", "TEL", "TER", "TFC", "TFX", 
    "TGT", "TJX", "TMO", "TMUS", "TPR", "TRGP", "TRMB", "TROW", "TRV", "TSCO", "TSLA", "TSN", "TT", "TTWO", "TXN", "TXT", "TYL", "UAL", "UBER", 
    "UDR", "UHS", "ULTA", "UNH", "UNP", "UPS", "URI", "USB", "V", "VICI", "VLO", "VLTO", "VMC", "VRSK", "VRSN", "VRTX", "VTR", "VTRS", "VZ", 
    "WAB", "WAT", "WBA", "WBD", "WDC", "WEC", "WELL", "WFC", "WM", "WMB", "WMT", "WRB", "WRK", "WST", "WTW", "WY", "WYNN", "XEL", "XOM", "XYL", 
    "YUM", "ZBH", "ZBRA", "ZTS"
]

# Kopyaları Temizle ve Birleştir
raw_sp500_rest = list(set(raw_sp500_rest) - set(priority_sp))
raw_sp500_rest.sort()
final_sp500_list = priority_sp + raw_sp500_rest

priority_crypto = ["BTC-USD", "ETH-USD"]
other_crypto = [
    # --- MAJOR ALTCOINS ---
    "BNB-USD", "SOL-USD", "XRP-USD", "ADA-USD", "DOGE-USD", "AVAX-USD", "TRX-USD",
    "DOT-USD", "MATIC-USD", "LINK-USD", "TON-USD", "SHIB-USD", "LTC-USD", "BCH-USD",
  
    # --- POPULER KATMAN 1 & 2 (L1/L2) ---
    "ICP-USD", "NEAR-USD", "APT-USD", "STX-USD", "FIL-USD", "ATOM-USD", "ARB-USD",
    "OP-USD", "INJ-USD", "KAS-USD", "TIA-USD", "SEI-USD", "SUI-USD", "ALGO-USD",
    "HBAR-USD", "EGLD-USD", "FTM-USD", "XLM-USD", "VET-USD", "ETC-USD", "EOS-USD",
    "XTZ-USD", "MINA-USD", "ASTR-USD", "FLOW-USD", "KLAY-USD", "IOTA-USD", "NEO-USD",
    
    # --- DEFI & WEB3 & AI ---
    "RNDR-USD", "GRT-USD", "FET-USD", "UNI-USD", "LDO-USD", "MKR-USD", "AAVE-USD",
    "SNX-USD", "RUNE-USD", "QNT-USD", "CRV-USD", "CFX-USD", "CHZ-USD", "AXS-USD",
    "SAND-USD", "MANA-USD", "THETA-USD", "GALA-USD", "ENJ-USD", "COMP-USD", "1INCH-USD",
    "ZIL-USD", "BAT-USD", "LRC-USD", "SUSHI-USD", "YFI-USD", "ZRX-USD", "ANKR-USD",
    
    # --- MEME & SPECULATIVE ---
    "PEPE-USD", "BONK-USD", "FLOKI-USD", "WIF-USD", "LUNC-USD",
    
    # --- ESKİ TOPRAKLAR (KLASİKLER) ---
    "XMR-USD", "DASH-USD", "ZEC-USD", "BTT-USD", "RVN-USD", "WAVES-USD", "OMG-USD",
    "ICX-USD", "IOST-USD", "ONT-USD", "QTUM-USD", "SC-USD", "DGB-USD", "XVG-USD"
]
other_crypto.sort()
final_crypto_list = priority_crypto + other_crypto

raw_nasdaq = [
    "AAPL", "MSFT", "NVDA", "AMZN", "AVGO", "META", "TSLA", "GOOGL", "GOOG", "COST", 
    "NFLX", "AMD", "PEP", "LIN", "TMUS", "CSCO", "QCOM", "INTU", "AMAT", "TXN", 
    "HON", "AMGN", "BKNG", "ISRG", "CMCSA", "SBUX", "MDLZ", "GILD", "ADP", "ADI", 
    "REGN", "VRTX", "LRCX", "PANW", "MU", "KLAC", "SNPS", "CDNS", "MELI", "MAR", 
    "ORLY", "CTAS", "NXPI", "CRWD", "CSX", "PCAR", "MNST", "WDAY", "ROP", "AEP", 
    "ROKU", "ZS", "OKTA", "TEAM", "DDOG", "MDB", "SHOP", "EA", "TTD", "DOCU", 
    "INTC", "SGEN", "ILMN", "IDXX", "ODFL", "EXC", "ADSK", "PAYX", "CHTR", "MRVL", 
    "KDP", "XEL", "LULU", "ALGN", "VRSK", "CDW", "DLTR", "SIRI", "JBHT", "WBA", 
    "PDD", "JD", "BIDU", "NTES", "NXST", "MTCH", "UAL", "SPLK", "ANSS", "SWKS", 
    "QRVO", "AVTR", "FTNT", "ENPH", "SEDG", "BIIB", "CSGP", "ASTS"
]
raw_nasdaq = sorted(list(set(raw_nasdaq)))

commodities_list = [
    "GC=F",   # Altın ONS (Vadeli - Gold Futures) - 7/24 Aktif
    "SI=F",   # Gümüş ONS (Vadeli - Silver Futures)
    "HG=F",   # Bakır (Copper Futures) - CPER yerine bu daha iyidir
    "CL=F",   # Ham Petrol (Crude Oil WTI Futures) - Piyasanın kalbi burasıdır
    "NG=F",   # Doğalgaz (Natural Gas Futures)
    "BZ=F"    # Brent Petrol (Brent Crude Futures)
]

# --- BIST LİSTESİ (GENİŞLETİLMİŞ - BIST 200+ Adayları) ---
priority_bist_indices = ["XU100.IS", "XU030.IS", "XBANK.IS", "XUSIN.IS", "EREGL.IS", "SISE.IS", "TUPRS.IS"]

# Buraya BIST TUM'deki hisseleri ekliyoruz
raw_bist_stocks = [
    "A1CAP.IS", "ACSEL.IS", "ADEL.IS", "ADESE.IS", "ADGYO.IS", "AEFES.IS", "AFYON.IS", "AGESA.IS", "AGHOL.IS", "AGROT.IS", "AGYO.IS", "AHGAZ.IS", "AKBNK.IS", "AKCNS.IS", "AKENR.IS", "AKFGY.IS", "AKGRT.IS", "AKMGY.IS", "AKSA.IS", "AKSEN.IS", "AKSGY.IS", "AKSUE.IS", "AKYHO.IS", "ALARK.IS", "ALBRK.IS", "ALCAR.IS", "ALCTL.IS", "ALFAS.IS", "ALGYO.IS", "ALKA.IS", "ALKIM.IS", "ALMAD.IS", "ALTNY.IS", "ALVES.IS", "ANELE.IS", "ANGEN.IS", "ANHYT.IS", "ANSGR.IS", "ARASE.IS", "ARCLK.IS", "ARDYZ.IS", "ARENA.IS", "ARSAN.IS", "ARTMS.IS", "ARZUM.IS", "ASELS.IS", "ASGYO.IS", "ASTOR.IS", "ASUZU.IS", "ATAGY.IS", "ATAKP.IS", "ATATP.IS", "ATEKS.IS", "ATLAS.IS", "ATSYH.IS", "AVGYO.IS", "AVHOL.IS", "AVOD.IS", "AVPGY.IS", "AVTUR.IS", "AYCES.IS", "AYDEM.IS", "AYEN.IS", "AYES.IS", "AYGAZ.IS", "AZTEK.IS",
    "BAGFS.IS", "BAKAB.IS", "BALAT.IS", "BANVT.IS", "BARMA.IS", "BASCM.IS", "BASGZ.IS", "BAYRK.IS", "BEGYO.IS", "BERA.IS", "BERK.IS", "BEYAZ.IS", "BFREN.IS", "BIENY.IS", "BIGCH.IS", "BIMAS.IS", "BINBN.IS", "BINHO.IS", "BIOEN.IS", "BIZIM.IS", "BJKAS.IS", "BLCYT.IS", "BMSCH.IS", "BMSTL.IS", "BNTAS.IS", "BOBET.IS", "BORLS.IS", "BOSSA.IS", "BRISA.IS", "BRKO.IS", "BRKSN.IS", "BRKVY.IS", "BRLSM.IS", "BRMEN.IS", "BRSAN.IS", "BRYAT.IS", "BSOKE.IS", "BTCIM.IS", "BUCIM.IS", "BURCE.IS", "BURVA.IS", "BVSAN.IS", "BYDNR.IS",
    "CANTE.IS", "CATES.IS", "CCOLA.IS", "CELHA.IS", "CEMAS.IS", "CEMTS.IS", "CEOEM.IS", "CIMSA.IS", "CLEBI.IS", "CMBTN.IS", "CMENT.IS", "CONSE.IS", "COSMO.IS", "CRDFA.IS", "CRFSA.IS", "CUSAN.IS", "CVKMD.IS", "CWENE.IS",
    "DAGH.IS", "DAGI.IS", "DAPGM.IS", "DARDL.IS", "DENGE.IS", "DERHL.IS", "DERIM.IS", "DESA.IS", "DESPC.IS", "DEVA.IS", "DGATE.IS", "DGGYO.IS", "DGNMO.IS", "DIRIT.IS", "DITAS.IS", "DMSAS.IS", "DNISI.IS", "DOAS.IS", "DOBUR.IS", "DOCO.IS", "DOFER.IS", "DOGUB.IS", "DOHOL.IS", "DOKTA.IS", "DURDO.IS", "DYOBY.IS", "DZGYO.IS",
    "EBEBK.IS", "ECILC.IS", "ECZYT.IS", "EDATA.IS", "EDIP.IS", "EGEEN.IS", "EGEPO.IS", "EGGUB.IS", "EGPRO.IS", "EGSER.IS", "EKGYO.IS", "EKIZ.IS", "EKSUN.IS", "ELITE.IS", "EMKEL.IS", "EMNIS.IS", "ENJSA.IS", "ENKAI.IS", "ENSRI.IS", "ENTRA.IS", "EPLAS.IS", "ERBOS.IS", "ERCB.IS", "EREGL.IS", "ERSU.IS", "ESCAR.IS", "ESCOM.IS", "ESEN.IS", "ETILR.IS", "ETYAT.IS", "EUHOL.IS", "EUKYO.IS", "EUPWR.IS", "EUREN.IS", "EUYO.IS", "EYGYO.IS",
    "FADE.IS", "FENER.IS", "FLAP.IS", "FMIZP.IS", "FONET.IS", "FORMT.IS", "FORTE.IS", "FRIGO.IS", "FROTO.IS", "FZLGY.IS",
    "GARAN.IS", "GARFA.IS", "GEDIK.IS", "GEDZA.IS", "GENIL.IS", "GENTS.IS", "GEREL.IS", "GESAN.IS", "GLBMD.IS", "GLCVY.IS", "GLRYH.IS", "GLYHO.IS", "GMTAS.IS", "GOKNR.IS", "GOLTS.IS", "GOODY.IS", "GOZDE.IS", "GRNYO.IS", "GRSEL.IS", "GSDDE.IS", "GSDHO.IS", "GSRAY.IS", "GUBRF.IS", "GWIND.IS", "GZNMI.IS",
    "HALKB.IS", "HATEK.IS", "HATSN.IS", "HDFGS.IS", "HEDEF.IS", "HEKTS.IS", "HKTM.IS", "HLGYO.IS", "HRKET.IS", "HTTBT.IS", "HUBVC.IS", "HUNER.IS", "HURGZ.IS",
    "ICBCT.IS", "ICUGS.IS", "IDGYO.IS", "IEYHO.IS", "IHAAS.IS", "IHEVA.IS", "IHGZT.IS", "ILVE.IS", "IMASM.IS", "INDES.IS", "INFO.IS", "INGRM.IS", "INTEM.IS", "INVEO.IS", "INVES.IS", "IPEKE.IS", "ISATR.IS", "ISBIR.IS", "ISBTR.IS", "ISCTR.IS", "ISDMR.IS", "ISFIN.IS", "ISGSY.IS", "ISGYO.IS", "ISKPL.IS", "ISKUR.IS", "ISMEN.IS", "ISSEN.IS", "ISYAT.IS", "ITTFH.IS", "IZENR.IS", "IZFAS.IS", "IZINV.IS", "IZMDC.IS",
    "JANTS.IS", "TRALT.IS",
    "KAPLM.IS", "KAREL.IS", "KARSN.IS", "KARYE.IS", "KATMR.IS", "KAYSE.IS", "KCAER.IS", "KCHOL.IS", "KENT.IS", "KERVN.IS", "KERVT.IS", "KFEIN.IS", "KGYO.IS", "KIMMR.IS", "KLGYO.IS", "KLKIM.IS", "KLMSN.IS", "KLNMA.IS", "KLSER.IS", "KLRHO.IS", "KMPUR.IS", "KNFRT.IS", "KOCMT.IS", "KONKA.IS", "KONTR.IS", "KONYA.IS", "KOPOL.IS", "KORDS.IS", "KOTON.IS", "KOZAA.IS", "KOZAL.IS", "KRDMA.IS", "KRDMB.IS", "KRDMD.IS", "KRGYO.IS", "KRONT.IS", "KRPLS.IS", "KRSTL.IS", "KRTEK.IS", "KRVGD.IS", "KSTUR.IS", "KTLEV.IS", "KTSKR.IS", "KUTPO.IS", "KUVVA.IS", "KUYAS.IS", "KZBGY.IS", "KZGYO.IS",
    "LIDER.IS", "LIDFA.IS", "LILAK.IS", "LINK.IS", "LKMNH.IS", "LMKDC.IS", "LOGO.IS", "LUKSK.IS",
    "MAALT.IS", "MACKO.IS", "MAGEN.IS", "MAKIM.IS", "MAKTK.IS", "MANAS.IS", "MARBL.IS", "MARKA.IS", "MARTI.IS", "MAVI.IS", "MEDTR.IS", "MEGAP.IS", "MEGMT.IS", "MEKAG.IS", "MEPET.IS", "MERCN.IS", "MERIT.IS", "MERKO.IS", "METEM.IS", "METRO.IS", "METUR.IS", "MGROS.IS", "MIATK.IS", "MIPAZ.IS", "MMCAS.IS", "MNDRS.IS", "MNDTR.IS", "MOBTL.IS", "MOGAN.IS", "MPARK.IS", "MRGYO.IS", "MRSHL.IS", "MSGYO.IS", "MTRKS.IS", "MTRYO.IS", "MZHLD.IS",
    "NATEN.IS", "NETAS.IS", "NIBAS.IS", "NTGAZ.IS", "NUGYO.IS", "NUHCM.IS",
    "OBASE.IS", "OBAMS.IS", "ODAS.IS", "ODINE.IS", "OFSYM.IS", "ONCSM.IS", "ORCA.IS", "ORGE.IS", "ORMA.IS", "OSMEN.IS", "OSTIM.IS", "OTKAR.IS", "OTTO.IS", "OYAKC.IS", "OYAYO.IS", "OYLUM.IS", "OYYAT.IS", "OZGYO.IS", "OZKGY.IS", "OZRDN.IS", "OZSUB.IS",
    "PAGYO.IS", "PAMEL.IS", "PAPIL.IS", "PARSN.IS", "PASEU.IS", "PCILT.IS", "PEGYO.IS", "PEKGY.IS", "PENGD.IS", "PENTA.IS", "PETKM.IS", "PETUN.IS", "PGSUS.IS", "PINSU.IS", "PKART.IS", "PKENT.IS", "PLAT.IS", "PNLSN.IS", "POLHO.IS", "POLTK.IS", "PRDGS.IS", "PRKAB.IS", "PRKME.IS", "PRZMA.IS", "PSDTC.IS", "PSGYO.IS", "PTEK.IS",
    "QNBFB.IS", "QNBFL.IS", "QUAGR.IS", "PLTUR.IS",
    "RALYH.IS", "RAYSG.IS", "REEDR.IS", "RGYAS.IS", "RNPOL.IS", "RODRG.IS", "ROYAL.IS", "RTALB.IS", "RUBNS.IS", "RYGYO.IS", "RYSAS.IS",
    "SAFKR.IS", "SAHOL.IS", "SAMAT.IS", "SANEL.IS", "SANFM.IS", "SANKO.IS", "SARKY.IS", "SASA.IS", "SAYAS.IS", "SDTTR.IS", "SEGYO.IS", "SEKFK.IS", "SEKUR.IS", "SELEC.IS", "SELGD.IS", "SELVA.IS", "SEYKM.IS", "SILVR.IS", "SISE.IS", "SKBNK.IS", "SKTAS.IS", "SKYMD.IS", "SMART.IS", "SMRTG.IS", "SNGYO.IS", "SNICA.IS", "SNKRN.IS", "SNPAM.IS", "SODSN.IS", "SOKE.IS", "SOKM.IS", "SONME.IS", "SRVGY.IS", "SUMAS.IS", "SUNTK.IS", "SURGY.IS", "SUWEN.IS", "SYS.IS",
    "TABGD.IS", "TARAF.IS", "TATGD.IS", "TAVHL.IS", "TBORG.IS", "TCELL.IS", "TDGYO.IS", "TEKTU.IS", "TERA.IS", "TETMT.IS", "TEZOL.IS", "TGSAS.IS", "THYAO.IS", "TKFEN.IS", "TKNSA.IS", "TLMAN.IS", "TMPOL.IS", "TMSN.IS", "TNZTP.IS", "TOASO.IS", "TRCAS.IS", "TRGYO.IS", "TRILC.IS", "TSGYO.IS", "TSKB.IS", "TSPOR.IS", "TTKOM.IS", "TTRAK.IS", "TUCLK.IS", "TUKAS.IS", "TUPRS.IS", "TUREX.IS", "TURGG.IS", "TURSG.IS",
    "UFUK.IS", "ULAS.IS", "ULKER.IS", "ULUFA.IS", "ULUSE.IS", "ULUUN.IS", "UMPAS.IS", "UNLU.IS", "USAK.IS", "UZERB.IS", "TATEN.IS",
    "VAKBN.IS", "VAKFN.IS", "VAKKO.IS", "VANGD.IS", "VBTYZ.IS", "VERUS.IS", "VESBE.IS", "VESTL.IS", "VKFYO.IS", "VKGYO.IS", "VKING.IS", "VRGYO.IS",
    "YAPRK.IS", "YATAS.IS", "YAYLA.IS", "YBTAS.IS", "YEOTK.IS", "YESIL.IS", "YGGYO.IS", "YGYO.IS", "YKBNK.IS", "YKSLN.IS", "YONGA.IS", "YUNSA.IS", "YYAPI.IS", "YYLGD.IS",
    "ZEDUR.IS", "ZOREN.IS", "ZRGYO.IS", "GIPTA.IS", "TEHOL.IS", "PAHOL.IS", "MARMR.IS", "BIGEN.IS", "GLRMK.IS", "TRHOL.IS"
]

# Kopyaları Temizle ve Birleştir
raw_bist_stocks = list(set(raw_bist_stocks) - set(priority_bist_indices))
raw_bist_stocks.sort()
final_bist100_list = priority_bist_indices + raw_bist_stocks

ASSET_GROUPS = {
    "BIST 500 ": final_bist100_list,
    "S&P 500": final_sp500_list,
    "NASDAQ-100": raw_nasdaq,
    "KRİPTO": final_crypto_list,
    "EMTİALAR": commodities_list
}
INITIAL_CATEGORY = "BIST 500 "

# --- STATE YÖNETİMİ ---
if 'category' not in st.session_state: st.session_state.category = INITIAL_CATEGORY
if 'ticker' not in st.session_state: st.session_state.ticker = "XU100.IS"
if 'scan_data' not in st.session_state: st.session_state.scan_data = None
if 'generate_prompt' not in st.session_state: st.session_state.generate_prompt = False
if 'radar2_data' not in st.session_state: st.session_state.radar2_data = None
if 'watchlist' not in st.session_state: st.session_state.watchlist = load_watchlist_db()
if 'stp_scanned' not in st.session_state: st.session_state.stp_scanned = False
if 'stp_crosses' not in st.session_state: st.session_state.stp_crosses = []
if 'stp_trends' not in st.session_state: st.session_state.stp_trends = []
if 'stp_filtered' not in st.session_state: st.session_state.stp_filtered = []
if 'accum_data' not in st.session_state: st.session_state.accum_data = None
if 'breakout_left' not in st.session_state: st.session_state.breakout_left = None
if 'breakout_right' not in st.session_state: st.session_state.breakout_right = None
if 'minervini_data' not in st.session_state: st.session_state.minervini_data = None
if 'pattern_data' not in st.session_state: st.session_state.pattern_data = None

# --- CALLBACKLER ---
def on_category_change():
    new_cat = st.session_state.get("selected_category_key")
    if new_cat and new_cat in ASSET_GROUPS:
        st.session_state.category = new_cat
        st.session_state.ticker = ASSET_GROUPS[new_cat][0]
        st.session_state.scan_data = None
        st.session_state.radar2_data = None
        st.session_state.stp_scanned = False
        st.session_state.accum_data = None 
        st.session_state.breakout_left = None
        st.session_state.breakout_right = None

def on_asset_change():
    new_asset = st.session_state.get("selected_asset_key")
    if new_asset: st.session_state.ticker = new_asset

def on_manual_button_click():
    if st.session_state.manual_input_key:
        st.session_state.ticker = st.session_state.manual_input_key.upper()

def on_scan_result_click(symbol): 
    st.session_state.ticker = symbol

def toggle_watchlist(symbol):
    wl = st.session_state.watchlist
    if symbol in wl:
        remove_watchlist_db(symbol)
        wl.remove(symbol)
    else:
        add_watchlist_db(symbol)
        wl.append(symbol)
    st.session_state.watchlist = wl

# ==============================================================================
# 3. OPTİMİZE EDİLMİŞ HESAPLAMA FONKSİYONLARI (CORE LOGIC)
# ==============================================================================

@st.cache_data(ttl=3600)
def get_benchmark_data(category):
    """
    Seçili kategoriye göre Endeks verisini (S&P 500 veya BIST 100) çeker.
    RS (Göreceli Güç) hesaplaması için referans noktasıdır.
    """
    try:
        # Kategoriye göre sembol seçimi
        ticker = "XU100.IS" if "BIST" in category else "^GSPC"
        
        # Hisse verileriyle uyumlu olması için 1 yıllık çekiyoruz
        df = yf.download(ticker, period="1y", progress=False)
        
        if df.empty: return None
        return df['Close']
    except:
        return None

@st.cache_data(ttl=3600)
def get_fundamental_score(ticker):
    """
    GLOBAL STANDART (IBD/Stockopedia Mantığı) - Kademeli Puanlama
    """
    # Endeks veya Kripto kontrolü
    if ticker.startswith("^") or "XU" in ticker or "-USD" in ticker:
        return {"score": 50, "details": [], "valid": False} # Nötr dön

    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if not info: return {"score": 50, "details": ["Veri Yok"], "valid": False}
        
        score = 0
        details = []
        
        # --- YARDIMCI FONKSİYON: Kademeli Puanlama ---
        def rate_metric(val, thresholds, max_pts):
            """Değeri eşiklere göre puanlar. Örn: val=15, thresh=[5, 10, 20], max=20"""
            if not val: return 0
            val = val * 100 if val < 10 else val # Yüzde dönüşümü
            step = max_pts / len(thresholds)
            earned = 0
            for t in thresholds:
                if val > t: earned += step
            return earned

        # 1. BÜYÜME (GROWTH) - Max 40 Puan
        # Ciro Büyümesi (Eşikler: %5, %15, %25) -> Max 20p
        rev_g = info.get('revenueGrowth', 0)
        s_rev = rate_metric(rev_g, [5, 15, 25], 20)
        score += s_rev
        if s_rev >= 10: details.append(f"Ciro Büyümesi: %{rev_g*100:.1f}")

        # Kâr Büyümesi (Eşikler: %5, %15, %25) -> Max 20p
        earn_g = info.get('earningsGrowth', 0)
        s_earn = rate_metric(earn_g, [5, 15, 25], 20)
        score += s_earn
        if s_earn >= 10: details.append(f"Kâr Büyümesi: %{earn_g*100:.1f}")

        # 2. KALİTE (QUALITY) - Max 40 Puan
        # ROE (Eşikler: %5, %10, %15, %20) -> Max 20p (Daha hassas)
        roe = info.get('returnOnEquity', 0)
        s_roe = rate_metric(roe, [5, 10, 15, 20], 20)
        score += s_roe
        if s_roe >= 15: details.append(f"Güçlü ROE: %{roe*100:.1f}")

        # Net Marj (Eşikler: %5, %10, %20) -> Max 20p
        margin = info.get('profitMargins', 0)
        s_marg = rate_metric(margin, [5, 10, 20], 20)
        score += s_marg
        if s_marg >= 10: details.append(f"Net Marj: %{margin*100:.1f}")

        # 3. SMART MONEY (SAHİPLİK) - Max 20 Puan
        inst = info.get('heldPercentInstitutions', 0)
        s_inst = rate_metric(inst, [10, 30, 50, 70], 20)
        score += s_inst
        if s_inst >= 10: details.append(f"Kurumsal: %{inst*100:.0f}")

        return {"score": min(score, 100), "details": details, "valid": True}
        
    except Exception:
        return {"score": 50, "details": [], "valid": False}

# --- GLOBAL DATA CACHE KATMANI ---
@st.cache_data(ttl=3600, show_spinner=False)
def get_batch_data_cached(asset_list, period="1y"):
    """
    TOPLU TARAMALAR İÇİN AKILLI ÖNBELLEK (SCANNER'LAR İÇİN)
    """
    if not asset_list:
        return pd.DataFrame()
        
    missing_assets = []
    
    # 1. Hangi hisselerin diskte verisi yok?
    for sym in asset_list:
        clean_sym = sym.replace(".IS", "")
        if "BIST" in sym or ".IS" in sym:
            clean_sym = sym if sym.endswith(".IS") else f"{sym}.IS"
        if not os.path.exists(os.path.join(CACHE_DIR, f"{clean_sym}_1d.parquet")):
            missing_assets.append(sym)
            
    # 2. HİÇ OLMAYANLARI ilk defaya mahsus 2 yıllık toplu çek ve diske yaz
    if missing_assets:
        df_missing = yf.download(" ".join(missing_assets), period="2y", group_by='ticker', threads=True, progress=False)
        if not df_missing.empty:
            for sym in missing_assets:
                clean_sym = sym.replace(".IS", "")
                if "BIST" in sym or ".IS" in sym:
                    clean_sym = sym if sym.endswith(".IS") else f"{sym}.IS"
                    
                try:
                    df_sym = df_missing[sym] if len(missing_assets) > 1 and isinstance(df_missing.columns, pd.MultiIndex) else df_missing
                    df_sym = df_sym.dropna(subset=['Close'])
                    if not df_sym.empty:
                        df_sym.columns = [c.capitalize() for c in df_sym.columns]
                        if 'Volume' not in df_sym.columns: df_sym['Volume'] = 1
                        df_sym.to_parquet(os.path.join(CACHE_DIR, f"{clean_sym}_1d.parquet"))
                except: continue

    # 3. TÜM LİSTE İÇİN (VAR OLANLAR DAHİL) SADECE SON 5 GÜNÜ TOPLU ÇEK (Güncel kalsın diye)
    df_recent = yf.download(" ".join(asset_list), period="5d", group_by='ticker', threads=True, progress=False)
    
    # 4. DİSKTEN OKU + 5 GÜNLÜKLE BİRLEŞTİR + SİSTEME VER
    combined_dict = {}
    period_map = {"10y": 2500, "5y": 1250, "2y": 500, "1y": 250, "6mo": 125, "3mo": 60, "1mo": 20}
    days_to_keep = period_map.get(period, 500) 
    
    for sym in asset_list:
        clean_sym = sym.replace(".IS", "")
        if "BIST" in sym or ".IS" in sym:
            clean_sym = sym if sym.endswith(".IS") else f"{sym}.IS"
        file_path = os.path.join(CACHE_DIR, f"{clean_sym}_1d.parquet")
        
        try:
            if os.path.exists(file_path):
                df_cached = pd.read_parquet(file_path)
                
                # Yeni 5 günlük veriyi ayıkla
                df_sym_recent = pd.DataFrame()
                if not df_recent.empty:
                    if len(asset_list) == 1:
                        df_sym_recent = df_recent
                    elif isinstance(df_recent.columns, pd.MultiIndex) and sym in df_recent.columns.levels[0]:
                        df_sym_recent = df_recent[sym]
                        
                if not df_sym_recent.empty:
                    df_sym_recent = df_sym_recent.dropna(subset=['Close'])
                    df_sym_recent.columns = [c.capitalize() for c in df_sym_recent.columns]
                    if 'Volume' not in df_sym_recent.columns: df_sym_recent['Volume'] = 1
                    
                    # ESKİ VE YENİ VERİYİ BİRLEŞTİR (Yeni veri ezerek günceller)
                    df_combined = pd.concat([df_cached, df_sym_recent])
                    df_combined = df_combined[~df_combined.index.duplicated(keep='last')]
                    df_combined.sort_index(inplace=True)
                    
                    df_combined.to_parquet(file_path) # Diski güncelle
                    final_df = df_combined
                else:
                    final_df = df_cached
                
                combined_dict[sym] = final_df.tail(days_to_keep)
        except Exception:
            continue
            
    # Taramaların (eski kodun) yapısını bozmamak için MultiIndex DataFrame olarak birleştir
    if combined_dict:
        return pd.concat(combined_dict.values(), axis=1, keys=combined_dict.keys())
    return pd.DataFrame()

# --- SINGLE STOCK CACHE (DETAY SAYFASI İÇİN) ---
@st.cache_data(ttl=300)
def get_safe_historical_data(ticker, period="1y", interval="1d"):
    try:
        clean_ticker = ticker.replace(".IS", "")
        if "BIST" in ticker or ".IS" in ticker:
            clean_ticker = ticker if ticker.endswith(".IS") else f"{ticker}.IS"
            
        file_path = os.path.join(CACHE_DIR, f"{clean_ticker}_{interval}.parquet")
        
        # 1. DİSK KONTROLÜ VE "SADECE EKSİĞİ (Son 5 Gün)" İNDİRME
        if os.path.exists(file_path):
            df_cached = pd.read_parquet(file_path)
            
            # SADECE son 5 günü çek (Ban riski yok, şimşek hızında ve hep canlı)
            df_new = yf.download(clean_ticker, period="5d", interval=interval, progress=False)
            
            if not df_new.empty:
                if isinstance(df_new.columns, pd.MultiIndex):
                    try: df_new = df_new.xs(clean_ticker, axis=1, level=1)
                    except: df_new.columns = df_new.columns.get_level_values(0)
                df_new.columns = [c.capitalize() for c in df_new.columns]
                if 'Volume' not in df_new.columns: df_new['Volume'] = 1
                
                # 2. ESKİ VE YENİ VERİYİ KAYNAŞTIR (Güncel olan eskisini ezer)
                df_combined = pd.concat([df_cached, df_new])
                df_combined = df_combined[~df_combined.index.duplicated(keep='last')]
                df_combined.sort_index(inplace=True)
                
                # 3. DİSKİ GÜNCELLE
                df_combined.to_parquet(file_path)
                final_df = df_combined
            else:
                final_df = df_cached
                
        else:
            # DİSKTE HİÇ YOKSA (İlk kez açılıyorsa): Tamamını indir
            # Gelecekte Lorentzian vb için lazım olacağından ana depoya hep 10y atalım
            fetch_period = "10y" if interval == "1d" else period
            df_new = yf.download(clean_ticker, period=fetch_period, interval=interval, progress=False)
            if df_new.empty: return None
            
            if isinstance(df_new.columns, pd.MultiIndex):
                try: df_new = df_new.xs(clean_ticker, axis=1, level=1)
                except: df_new.columns = df_new.columns.get_level_values(0)
            df_new.columns = [c.capitalize() for c in df_new.columns]
            if 'Volume' not in df_new.columns: df_new['Volume'] = 1
            
            df_new.to_parquet(file_path)
            final_df = df_new

        # 4. İSTENEN SÜREYİ VER (İçeride 10 yıl var ama "6mo" istendiyse sadece 6 ayı ver)
        period_map = {"10y": 2500, "5y": 1250, "2y": 500, "1y": 250, "6mo": 125, "3mo": 60, "1mo": 20}
        days_to_keep = period_map.get(period, len(final_df))
        
        return final_df.tail(days_to_keep)

    except Exception as e:
        return None

def calculate_harsi(df, period=14):
    """
    Heikin Ashi RSI (HARSI) Hesaplayıcı
    Dönüş: (HA_Open, HA_Close, Renk)
    """
    try:
        # 1. Standart RSI Hesapla
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # 2. Heikin Ashi Dönüşümü
        # Not: Vektörize hesaplama için başlangıç değerlerini ata
        ha_close = rsi.copy()
        ha_open = rsi.shift(1).fillna(rsi)
        
        # HA formülü gereği iteratif hesaplama (Hassas sonuç için)
        ha_open_vals = np.zeros(len(rsi))
        ha_close_vals = np.zeros(len(rsi))
        
        for i in range(len(rsi)):
            if i == 0:
                ha_open_vals[i] = rsi.iloc[i]
                ha_close_vals[i] = rsi.iloc[i]
            else:
                ha_open_vals[i] = (ha_open_vals[i-1] + ha_close_vals[i-1]) / 2
                ha_close_vals[i] = (rsi.iloc[i] + ha_open_vals[i] + 
                                    max(rsi.iloc[i], ha_open_vals[i]) + 
                                    min(rsi.iloc[i], ha_open_vals[i])) / 4
        
        last_ha_open = ha_open_vals[-1]
        last_ha_close = ha_close_vals[-1]
        prev_ha_close = ha_close_vals[-2]
        
        # Renk ve Durum Belirle
        is_green = last_ha_close > last_ha_open
        color = "#16a34a" if is_green else "#dc2626"
        trend_status = "BOĞA MOMENTUMU" if is_green else "AYI MOMENTUMU"
        
        return {
            "ha_open": last_ha_open,
            "ha_close": last_ha_close,
            "is_green": is_green,
            "color": color,
            "status": trend_status,
            "change": last_ha_close > prev_ha_close
        }
    except:
        return None
    
def check_lazybear_squeeze_breakout(df):
    """
    Hem BUGÜNÜ hem DÜNÜ kontrol eder.
    Dönüş: (is_squeeze_now, is_squeeze_yesterday)
    """
    try:
        if df.empty or len(df) < 22: return False, False

        close = df['Close']
        high = df['High']
        low = df['Low']

        # 1. Bollinger Bantları (20, 2.0)
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        bb_upper = sma20 + (2.0 * std20)
        bb_lower = sma20 - (2.0 * std20)

        # 2. Keltner Kanalları (20, 1.5 ATR)
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr20 = tr.rolling(20).mean()
        
        kc_upper = sma20 + (1.5 * atr20)
        kc_lower = sma20 - (1.5 * atr20)

        # 3. Kontrol (Son 2 gün)
        def is_sq(idx):
            return (bb_upper.iloc[idx] < kc_upper.iloc[idx]) and \
                   (bb_lower.iloc[idx] > kc_lower.iloc[idx])

        # -1: Bugün, -2: Dün
        sq_now = is_sq(-1)
        sq_prev = is_sq(-2)

        return sq_now, sq_prev

    except Exception:
        return False, False

@st.cache_data(ttl=900)
def get_ma_data_for_ui(ticker):
    """Arayüzdeki 4. sütun için hızlıca EMA ve SMA verilerini hesaplar."""
    try:
        # Son 1 yıllık veriyi hızlıca çek
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty: 
            return None
        
        # yfinance bazen MultiIndex döndürebilir, bunu güvenli hale getirelim
        if isinstance(df.columns, pd.MultiIndex):
            close_col = df['Close'][ticker] if ticker in df['Close'] else df['Close'].iloc[:, 0]
        else:
            close_col = df['Close']
            
        close = float(close_col.iloc[-1])
        
        # EMA Hesaplamaları
        ema5 = float(close_col.ewm(span=5, adjust=False).mean().iloc[-1])
        ema8 = float(close_col.ewm(span=8, adjust=False).mean().iloc[-1])
        ema13 = float(close_col.ewm(span=13, adjust=False).mean().iloc[-1])
        
        # SMA Hesaplamaları
        sma50 = float(close_col.rolling(window=50).mean().iloc[-1])
        sma100 = float(close_col.rolling(window=100).mean().iloc[-1])
        sma200 = float(close_col.rolling(window=200).mean().iloc[-1])
        
        return {
            "close": close,
            "ema5": ema5, "ema8": ema8, "ema13": ema13,
            "sma50": sma50, "sma100": sma100, "sma200": sma200
        }
    except Exception as e:
        return None
    
@st.cache_data(ttl=300)
def fetch_stock_info(ticker):
    try:
        t = yf.Ticker(ticker)
        price = prev_close = volume = None
        try:
            fi = getattr(t, "fast_info", None)
            if fi:
                price = fi.get("last_price")
                prev_close = fi.get("previous_close")
                volume = fi.get("last_volume")
        except: pass

        if price is None or prev_close is None:
            df = get_safe_historical_data(ticker, period="5d")
            if df is not None and not df.empty:
                 price = float(df["Close"].iloc[-1])
                 prev_close = float(df["Close"].iloc[-2]) if len(df) > 1 else price
                 volume = float(df["Volume"].iloc[-1])
            else: return None

        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
        return { "price": price, "change_pct": change_pct, "volume": volume or 0, "sector": "-", "target": "-" }
    except: return None

@st.cache_data(ttl=600)
def get_tech_card_data(ticker):
    try:
        df = get_safe_historical_data(ticker, period="2y")
        if df is None: return None
        close = df['Close']; high = df['High']; low = df['Low']
        
        sma50 = close.rolling(50).mean().iloc[-1] if len(close) > 50 else 0
        sma100 = close.rolling(100).mean().iloc[-1] if len(close) > 100 else 0
        sma200 = close.rolling(200).mean().iloc[-1] if len(close) > 200 else 0
        ema144 = close.ewm(span=144, adjust=False).mean().iloc[-1]
        atr = (high-low).rolling(14).mean().iloc[-1]
        
        return {
            "sma50": sma50, "sma100": sma100, "sma200": sma200, "ema144": ema144,
            "stop_level": close.iloc[-1] - (2 * atr), "risk_pct": (2 * atr) / close.iloc[-1] * 100,
            "atr": atr, "close_last": close.iloc[-1]
        }
    except: return None

@st.cache_data(ttl=1200)
def fetch_google_news(ticker):
    try:
        clean = ticker.replace(".IS", "").replace("=F", "")
        rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote_plus(f'{clean} stock news site:investing.com OR site:seekingalpha.com')}&hl=tr&gl=TR&ceid=TR:tr"
        feed = feedparser.parse(rss_url)
        news = []
        for entry in feed.entries[:6]:
            try: dt = datetime(*entry.published_parsed[:6])
            except: dt = datetime.now()
            if dt < datetime.now() - timedelta(days=10): continue
            pol = TextBlob(entry.title).sentiment.polarity
            color = "#16A34A" if pol > 0.1 else "#DC2626" if pol < -0.1 else "#64748B"
            news.append({'title': entry.title, 'link': entry.link, 'date': dt.strftime('%d %b'), 'source': entry.source.title, 'color': color})
        return news
    except: return []

def check_lazybear_squeeze(df):
    """
    LazyBear Squeeze Momentum Logic:
    Squeeze = Bollinger Bantları, Keltner Kanalının İÇİNDE mi?
    """
    try:
        if df.empty or len(df) < 20: return False, 0.0

        close = df['Close']
        high = df['High']
        low = df['Low']

        # 1. Bollinger Bantları (20, 2.0)
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        bb_upper = sma20 + (2.0 * std20)
        bb_lower = sma20 - (2.0 * std20)

        # 2. Keltner Kanalları (20, 1.5 ATR)
        # TR Hesaplama
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr20 = tr.rolling(20).mean()
        
        kc_upper = sma20 + (1.5 * atr20)
        kc_lower = sma20 - (1.5 * atr20)

        # 3. Squeeze Kontrolü (Son Gün İçin)
        # BB Üst, KC Üst'ten KÜÇÜK VE BB Alt, KC Alt'tan BÜYÜK olmalı (İçinde olmalı)
        last_bb_u = float(bb_upper.iloc[-1])
        last_bb_l = float(bb_lower.iloc[-1])
        last_kc_u = float(kc_upper.iloc[-1])
        last_kc_l = float(kc_lower.iloc[-1])

        is_squeeze_on = (last_bb_u < last_kc_u) and (last_bb_l > last_kc_l)

        return is_squeeze_on

    except Exception:
        return False

@st.cache_data(ttl=600)
def calculate_synthetic_sentiment(ticker):
    try:
        df = get_safe_historical_data(ticker, period="6mo")
        if df is None: return None
        
        close = df['Close']; high = df['High']; low = df['Low']; volume = df['Volume']
        
        # --- EVRENSEL FORMÜL V2.0 BAŞLANGIÇ ---
        # 1. Tipik Fiyat
        typical_price = (high + low + close) / 3

        # 2. DEMA 6 Hesaplama
        ema1 = typical_price.ewm(span=6, adjust=False).mean()
        ema2 = ema1.ewm(span=6, adjust=False).mean()
        dema6 = (2 * ema1) - ema2

        mf_smooth = (typical_price - dema6) / dema6 * 1000

        stp = ema1
        
        df = df.reset_index()
        if 'Date' not in df.columns: df['Date'] = df.index
        else: df['Date'] = pd.to_datetime(df['Date'])
        
        plot_df = pd.DataFrame({
            'Date': df['Date'], 
            'MF_Smooth': mf_smooth.values, 
            'STP': stp.values, 
            'Price': close.values
        }).tail(30).reset_index(drop=True)
        
        plot_df['Date_Str'] = plot_df['Date'].dt.strftime('%d %b')
        return plot_df
    except Exception: return None

@st.cache_data(ttl=600)
def get_obv_divergence_status(ticker):
    """
    OBV ile Fiyat arasındaki uyumsuzluğu (Profesyonel SMA Filtreli) hesaplar.
    Dönüş: (Başlık, Renk, Açıklama)
    """
    try:
        # Periyodu biraz geniş tutuyoruz ki SMA20 hesaplanabilsin
        df = get_safe_historical_data(ticker, period="3mo") 
        if df is None or len(df) < 30: return ("Veri Yok", "#64748B", "Yetersiz veri.")
        
        # 1. OBV ve SMA Hesapla
        change = df['Close'].diff()
        direction = np.sign(change).fillna(0)
        obv = (direction * df['Volume']).cumsum()
        obv_sma = obv.rolling(20).mean() # Profesyonel Filtre
        
        # 2. Son 10 Günlük Trend Kıyaslaması
        p_now = df['Close'].iloc[-1]; p_old = df['Close'].iloc[-11]
        obv_now = obv.iloc[-1]; obv_old = obv.iloc[-11]
        obv_sma_now = obv_sma.iloc[-1]
        
        price_trend = "YUKARI" if p_now > p_old else "AŞAĞI"
        # Klasik OBV trendi (Eski usul)
        obv_trend_raw = "YUKARI" if obv_now > obv_old else "AŞAĞI"
        
        # 3. GÜÇ FİLTRESİ: OBV şu an ortalamasının üzerinde mi?
        is_obv_strong = obv_now > obv_sma_now
        
        # 4. Karar Mekanizması
        if price_trend == "AŞAĞI" and obv_trend_raw == "YUKARI":
            if is_obv_strong:
                return ("🔥 GÜÇLÜ GİZLİ GİRİŞ", "#16a34a", "Fiyat düşerken OBV ortalamasını kırdı (Smart Money).")
            else:
                return ("👀 Olası Toplama (Zayıf)", "#d97706", "OBV artıyor ama henüz ortalamayı (SMA20) geçemedi.")
                
        elif price_trend == "YUKARI" and obv_trend_raw == "AŞAĞI":
            return ("⚠️ GİZLİ ÇIKIŞ (Dağıtım)", "#dc2626", "Fiyat yükselirken OBV düşüyor. (Negatif Uyumsuzluk)")
            
        elif is_obv_strong:
            # DÜZELTME: Trende değil, BUGÜNKÜ mumun rengine bakıyoruz.
            # 10 günlük trend yukarı olsa bile, bugün fiyat düşüyorsa "Yükseliş" deme.
            p_yesterday = df['Close'].iloc[-2]
            
            if p_now < p_yesterday: # Bugün Fiyat Düşüyorsa (Kırmızı Mum)
                return ("🛡️ Düşüşe Direnç (Hacimli)", "#d97706", "OBV trendi koruyor ama fiyat bugün baskı altında. (Tutunma Çabası)")
            else:
                return ("✅ Hacim Destekli Trend", "#15803d", "OBV ortalamanın üzerinde ve Fiyat Yükseliyor (Sağlıklı).")
            
        else:
            return ("Nötr / Zayıf", "#64748B", "Hacim akışı ortalamanın altında veya nötr.")
            
    except: return ("Hesaplanamadı", "#64748B", "-")

# --- OPTİMİZE EDİLMİŞ BATCH SCANNER'LAR ---

def process_single_stock_stp(symbol, df):
    """
    Tek bir hissenin STP hesaplamasını yapar.
    """
    try:
        if df.empty or 'Close' not in df.columns: return None
        df = df.dropna(subset=['Close'])
        if len(df) < 200: return None

        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = float(df['Volume'].iloc[-1]) if 'Volume' in df.columns else 0
        
        typical_price = (high + low + close) / 3
        stp = typical_price.ewm(span=6, adjust=False).mean()
        sma200 = close.rolling(200).mean()
        
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        c_last = float(close.iloc[-1]); c_prev = float(close.iloc[-2])
        s_last = float(stp.iloc[-1]); s_prev = float(stp.iloc[-2])
        
        result = None
        
        if c_prev <= s_prev and c_last > s_last:
            result = {
                "type": "cross_up",
                "data": {"Sembol": symbol, "Fiyat": c_last, "STP": s_last, "Fark": ((c_last/s_last)-1)*100, "Hacim": volume}
            }
            sma_val = float(sma200.iloc[-1])
            rsi_val = float(rsi.iloc[-1])
            if (c_last > sma_val) and (20 < rsi_val < 70):
                result["is_filtered"] = True
            else:
                result["is_filtered"] = False

        # --- YENİ: AŞAĞI KESİŞİM (SAT) ---
        elif c_prev >= s_prev and c_last < s_last:
            result = {
                "type": "cross_down",
                "data": {"Sembol": symbol, "Fiyat": c_last, "STP": s_last, "Fark": ((c_last/s_last)-1)*100, "Hacim": volume}
            }

        # YUKARI TREND
        elif c_prev > s_prev and c_last > s_last:
            above = close > stp
            streak = (above != above.shift()).cumsum()
            streak_count = above.groupby(streak).sum().iloc[-1]
            
            result = {
                "type": "trend_up",
                "data": {
                    "Sembol": symbol, 
                    "Fiyat": c_last, 
                    "STP": s_last, 
                    "Fark": ((c_last/s_last)-1)*100,
                    "Gun": int(streak_count),
                    "Hacim": volume
                }
            }

        # --- YENİ: AŞAĞI TREND ---
        elif c_prev < s_prev and c_last < s_last:
            below = close < stp
            streak = (below != below.shift()).cumsum()
            streak_count = below.groupby(streak).sum().iloc[-1]
            
            result = {
                "type": "trend_down",
                "data": {
                    "Sembol": symbol, 
                    "Fiyat": c_last, 
                    "STP": s_last, 
                    "Fark": ((c_last/s_last)-1)*100,
                    "Gun": int(streak_count),
                    "Hacim": volume
                }
            }
            
        return result
    except Exception: return None

def process_single_bear_trap_live(df):
    """
    Tekil hisse için Bear Trap kontrolü yapar.
    Canlı durum paneli için optimize edilmiştir.
    """
    try:
        if df.empty or len(df) < 60: return None
        
        close = df['Close']; low = df['Low']; volume = df['Volume']
        if 'Volume' not in df.columns: volume = pd.Series([1]*len(df))
        
        curr_price = float(close.iloc[-1])

        # RSI Hesabı
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain / loss)))

        # Son 4 mumu tara
        for i in range(4):
            idx = -(i + 1) # -1 (Şimdi), -2 (Önceki)...

            # 1. Referans Dip (50 mumluk)
            pivot_slice = low.iloc[idx-50 : idx]
            if len(pivot_slice) < 50: continue
            pivot_low = float(pivot_slice.min())

            # 2. Tuzak Mumu Verileri
            trap_low = float(low.iloc[idx])
            trap_close = float(close.iloc[idx])
            trap_vol = float(volume.iloc[idx])
            avg_vol = float(volume.iloc[idx-20:idx].mean())
            if avg_vol == 0: avg_vol = 1

            # 3. Kriterler
            is_sweep = trap_low < pivot_low
            is_rejection = trap_close > pivot_low
            is_vol_ok = trap_vol > (avg_vol * 1.5)
            is_safe = curr_price > pivot_low # Fiyat hala güvenli bölgede mi?

            if is_sweep and is_rejection and is_vol_ok and is_safe:
                time_ago = "Şimdi" if i == 0 else f"{i} bar önce"
                return {
                    "Zaman": time_ago,
                    "Hacim_Kat": f"{trap_vol/avg_vol:.1f}x",
                    "Pivot": pivot_low
                }
        return None
    except: return None

@st.cache_data(ttl=900)
def scan_bear_traps(asset_list):
    """
    BEAR TRAP TARAYICISI (Toplu)
    Mantık: 50 periyotluk dibi temizleyip (Sweep), hacimli dönenleri (Rejection) bulur.
    Pencere: Son 4 mum (0, 1, 2, 3).
    """
    # Mevcut önbellekten veriyi çek (İnterneti yormaz)
    data = get_batch_data_cached(asset_list, period="2y") 
    if data.empty: return pd.DataFrame()

    results = []
    stock_dfs = []

    # Veriyi hisselere ayır
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]:
                    stock_dfs.append((symbol, data[symbol]))
            else:
                if len(asset_list) == 1: stock_dfs.append((symbol, data))
        except: continue

    # -- İÇ FONKSİYON: TEKİL İŞLEM --
    def _worker_bear_trap(symbol, df):
        try:
            if df.empty or len(df) < 60: return None
            
            close = df['Close']; low = df['Low']; volume = df['Volume']
            # Hacim yoksa 1 kabul et (Hata önleyici)
            if 'Volume' not in df.columns: volume = pd.Series([1]*len(df))
            
            curr_price = float(close.iloc[-1])

            # RSI Hesabı
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + (gain / loss)))

            # DÖNGÜ: Son 4 muma bak
            for i in range(4):
                idx = -(i + 1) # -1, -2, -3, -4

                # 1. REFERANS DİP (Geriye dönük 50 mum)
                pivot_slice = low.iloc[idx-50 : idx]
                if len(pivot_slice) < 50: continue
                pivot_low = float(pivot_slice.min())

                # 2. TUZAK MUMU VERİLERİ
                trap_low = float(low.iloc[idx])
                trap_close = float(close.iloc[idx])
                trap_vol = float(volume.iloc[idx])
                
                # Ortalama Hacim (Önceki 20 mum)
                avg_vol = float(volume.iloc[idx-20:idx].mean())
                if avg_vol == 0: avg_vol = 1

                # 3. KRİTERLER (AND)
                is_sweep = trap_low < pivot_low           # Dibi deldi mi?
                is_rejection = trap_close > pivot_low     # Üstünde kapattı mı?
                is_vol_ok = trap_vol > (avg_vol * 1.5)    # Hacim var mı?
                is_rsi_ok = float(rsi.iloc[idx]) > 30     # RSI aşırı ölü değil mi?
                is_safe = curr_price > pivot_low          # ŞU AN fiyat güvenli mi?

                if is_sweep and is_rejection and is_vol_ok and is_rsi_ok and is_safe:
                    time_ago = "🔥 ŞİMDİ" if i == 0 else f"⏰ {i} Mum Önce"
                    
                    # Skorlama (Tazelik + Hacim Gücü)
                    score = 80 + (10 if i == 0 else 0) + (10 if trap_vol > avg_vol * 2.0 else 0)
                    
                    return {
                        "Sembol": symbol,
                        "Fiyat": curr_price,
                        "Pivot": pivot_low,
                        "Zaman": time_ago,
                        "Hacim_Kat": f"{trap_vol/avg_vol:.1f}x",
                        "Detay": f"Dip ({pivot_low:.2f}) temizlendi.",
                        "Skor": score
                    }
            return None
        except: return None

    # -- PARALEL İŞLEM (HIZ İÇİN) --
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_worker_bear_trap, sym, df) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: results.append(res)

    if results:
        return pd.DataFrame(results).sort_values(by="Skor", ascending=False)
    
    return pd.DataFrame()

@st.cache_data(ttl=900)
def scan_chart_patterns(asset_list):
    """
    V4 FİNAL: ERKEN SİNYALLERİ ELEYEN, SADECE 'OLMUŞ' FORMASYONLARI BULAN TARAMA
    """
    data = get_batch_data_cached(asset_list, period="1y") 
    if data.empty: return pd.DataFrame()

    results = []
    
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol not in data.columns.levels[0]: continue
                df = data[symbol].dropna()
            else:
                df = data.dropna()
            
            # Daha güvenilir analiz için en az 150 gün veri
            if len(df) < 150: continue 

            close = df['Close']; high = df['High']; low = df['Low']; open_ = df['Open']
            volume = df['Volume']
            curr_price = float(close.iloc[-1])
            
            # --- ACIMASIZ 2 BÜYÜK FİLTRE ---
            # 1. KURAL: Fiyat 200 günlük ortalamanın altındaysa HİÇ BAKMA.
            sma200 = close.rolling(200).mean().iloc[-1]
            if curr_price < sma200: continue 
            
            # 2. KURAL: Son gün mumu dünkü kapanışa göre %2.5 veya daha fazla düşmüşse (Ani Satış/Dump) HİÇ BAKMA.
            prev_close = float(close.iloc[-2])
            if (curr_price - prev_close) / prev_close <= -0.025: continue

            pattern_found = False; pattern_name = ""; desc = ""; base_score = 0
            
            # --- 1. BOĞA BAYRAĞI (BULL FLAG) ---
            # Direk en az %15, Bayrak en fazla %6 genişlikte
            p20 = float(close.iloc[-20]); p5 = float(close.iloc[-5])
            pole = (p5 - p20) / p20
            flag_h = high.iloc[-5:].max(); flag_l = low.iloc[-5:].min()
            tight = (flag_h - flag_l) / flag_l
            
            # Kırılım %1 aşağıdan başlar, direncin en fazla %4 üzerine kadar taze kabul edilir
            if pole > 0.15 and tight < 0.06 and (curr_price >= flag_h * 0.99) and (curr_price <= flag_h * 1.04):
                pattern_found = True; pattern_name = "🚩 BOĞA BAYRAĞI"; base_score = 85
                desc = f"Direk: %{pole*100:.1f} | Sıkışma: %{tight*100:.1f}"

            # --- 2. FİNCAN KULP DİNAMİK (10 Ay, 5 Ay) ---
            for scale in [2, 1]:
                if len(df) < 150 * scale: continue
                rim_l = high.iloc[-(150*scale):-(40*scale)].max() 
                cup_b = low.iloc[-(60*scale):-(20*scale)].min()
                rim_r = high.iloc[-(25*scale):-(5*scale)].max() 
                handle_low = low.iloc[-(10*scale):].min()
                
                aligned = abs(rim_l - rim_r) / rim_l < 0.05
                deep = cup_b < rim_l * 0.85
                handle_exists = (handle_low < rim_r * 0.97) and (handle_low > cup_b + (rim_r - cup_b)*0.5)
                
                # Kırılımın taze olması şartı: Maksimum %4 üstüne kadar kabul edilir.
                breaking = (curr_price >= rim_r * 0.99) and (curr_price <= rim_r * 1.04)
                approaching = (curr_price >= rim_r * 0.95) and not breaking

                if aligned and deep and handle_exists:
                    if breaking or approaching:
                        pattern_found = True
                        p_name = f"☕ FİNCAN KULP ({scale*5} Ay)" if breaking else f"⏳ OLUŞAN FİNCAN KULP ({scale*5} Ay)"
                        p_desc = f"{scale*150} mumluk kulp tamamlandı, kırılım var." if breaking else f"{scale*150} mumluk sağ tepeye/kulba yaklaşıyor, kırılım bekleniyor."
                        if pattern_name: pattern_name += " & " + p_name; desc += " | " + p_desc
                        else: pattern_name = p_name; desc = p_desc
                        base_score = max(base_score, 95 if breaking else 75)

            # --- 3. TOBO DİNAMİK (9 Ay, 6 Ay, 3 Ay) ---
            for scale in [3, 2, 1]:
                if len(df) < 60 * scale: continue
                ml_idx, mh_idx, mr_idx = 60*scale, 40*scale, 15*scale
                ml = low.iloc[-ml_idx:-mh_idx].min()
                mh = low.iloc[-mh_idx:-mr_idx].min()
                mr = low.iloc[-mr_idx:].min()
                neck = high.iloc[-ml_idx:-10].max()
                
                head_deep = mh < ml * 0.98 and mh < mr * 0.98
                sym = abs(ml - mr) / ml < 0.08
                
                is_breakout_fresh = (curr_price >= neck * 0.98) and (curr_price <= neck * 1.03)
                is_forming = (curr_price > mr * 1.02) and (curr_price < neck * 0.98) # Sağ omuzdan sekmiş, boyuna gidiyor

                if head_deep and sym:
                    if is_breakout_fresh or is_forming:
                        pattern_found = True
                        p_name = f"🧛 TOBO ({scale*3} Ay)" if is_breakout_fresh else f"⏳ OLUŞAN TOBO ({scale*3} Ay)"
                        p_desc = f"{scale*3} aylık ({ml_idx} mum) kırılım taze." if is_breakout_fresh else f"{scale*3} aylık yapıda Sağ Omuz oluştu, boyun çizgisine gidiyor."
                        if pattern_name: pattern_name += " & " + p_name; desc += " | " + p_desc
                        else: pattern_name = p_name; desc = p_desc
                        base_score = max(base_score, 90 if is_breakout_fresh else 70)

            # --- 4. YÜKSELEN ÜÇGEN DİNAMİK (135 Gün, 90 Gün, 45 Gün) ---
            for scale in [3, 2, 1]:
                if len(df) < 45 * scale: continue
                h_peaks = high.iloc[-(45*scale):].nlargest(3).values
                if len(h_peaks) > 0:
                    avg_res = h_peaks.mean()
                    flat = all(abs(p - avg_res)/avg_res < 0.02 for p in h_peaks)
                    
                    l3 = low.iloc[-(15*scale):].min()
                    l2 = low.iloc[-(30*scale):-(15*scale)].min()
                    l1 = low.iloc[-(45*scale):-(30*scale)].min()
                    rising = l3 > l2 and l2 > l1
                    
                    # Direnç kırılımı taze olmalı (maks %4 tolerans)
                    breaking = (curr_price >= avg_res * 0.99) and (curr_price <= avg_res * 1.04)
                    approaching = (curr_price >= avg_res * 0.95) and not breaking

                    if flat and rising:
                        if breaking or approaching:
                            pattern_found = True
                            p_name = f"📐 YÜKS. ÜÇGEN ({scale*45} Gün)" if breaking else f"⏳ OLUŞAN ÜÇGEN ({scale*45} Gün)"
                            p_desc = f"{scale*45} günlük direnç zorlanıyor/kırılıyor." if breaking else f"{scale*45} günlük daralma var, dirence yaklaşıyor."
                            if pattern_name: pattern_name += " & " + p_name; desc += " | " + p_desc
                            else: pattern_name = p_name; desc = p_desc
                            base_score = max(base_score, 88 if breaking else 68)

            # --- 4.5 EKSİK OLAN YENİ FORMASYON: RANGE (YATAY BANT) ---
            for window in [180, 120, 90, 60]:
                if len(df) < window: continue
                recent_highs = high.iloc[-window:]
                recent_lows = low.iloc[-window:]
                
                period_max = recent_highs.max()
                period_min = recent_lows.min()
                
                range_width = (period_max - period_min) / period_min
                
                if range_width < 0.15: # Fiyat %15'lik yatay bir kanalda hapsolmuş
                    # Yukarı kırılımın taze olması (maks %4 yukarıda)
                    breaking_up = (curr_price >= period_max * 0.98) and (curr_price <= period_max * 1.04)
                    # Destekten sekme (Desteğin hafif altına sarkabilir ama %4'ten fazla zıplamamış olmalı)
                    bouncing_up = (curr_price >= period_min * 0.98) and (curr_price <= period_min * 1.04)
                    
                    if breaking_up or bouncing_up:
                        pattern_found = True
                        p_name = f"🧱 RANGE DİRENCİ ({window} Gün)" if breaking_up else f"🧱 RANGE DESTEĞİ ({window} Gün)"
                        p_desc = f"{window} gündür süren yatay kanal direnci kırılıyor!" if breaking_up else f"{window} gündür süren bandın dibinden destek aldı."
                        if pattern_name: pattern_name += " & " + p_name; desc += " | " + p_desc
                        else: pattern_name = p_name; desc = p_desc
                        base_score = max(base_score, 88 if breaking_up else 85)
                        break # En geniş periyot bulununca Range için döngüyü kırar (karmaşayı önler)

            # --- 5. QML (QUASIMODO) DÖNÜŞ FORMASYONU ---
            if not pattern_found:
                # Bullish QML (Dip Dönüşü): L, H, LL, HH yapısı aranır
                l_left = low.iloc[-60:-30].min()   # Sol Omuz (L)
                h_mid = high.iloc[-50:-20].max()   # Orta Tepe (H)
                ll_head = low.iloc[-30:-10].min()  # Baş (LL - Likidite Avı)
                hh_right = high.iloc[-15:].max()   # Sağ Tepe (HH - Yapı Kırılımı)
                
                # Kurallar:
                # 1. Baş, sol omuzdan düşük olmalı (SSL Likiditesi alındı)
                cond_ll = ll_head < l_left * 0.98
                # 2. Sağ tepe, orta tepeden yüksek olmalı (CHOCH / MSS Onayı)
                cond_hh = hh_right > h_mid * 1.01
                # 3. Fiyat şu an Sol Omuz (QML Çizgisi) seviyesine geri çekilmiş (Pullback) olmalı
                cond_pullback = (curr_price >= l_left * 0.95) and (curr_price <= l_left * 1.05)
                
                if cond_ll and cond_hh and cond_pullback:
                    pattern_found = True; pattern_name = "🧲 QUASIMODO (QML)"; base_score = 92
                    desc = "🎢 Büyük Dönüş: Önce dipte likidite avı (LL) yapılmış, ardından sert bir kırılımla (HH) trend yön değiştirmiş görünüyor. Fiyat şu an potansiyel bir fırsat durağında (Sol Omuz) olabilir."

            # --- 6. 3D (THREE DRIVE) YORGUNLUK FORMASYONU ---
            if not pattern_found:
                # Bullish 3D (3 Düşen Dip - Trend Yorgunluğu)
                d1 = low.iloc[-60:-40].min()
                d2 = low.iloc[-40:-20].min()
                d3 = low.iloc[-20:].min()
                
                # 1. Şart: Dipler sırayla düşüyor olmalı
                if d1 > d2 > d3:
                    # 2. Şart: Simetri Kontrolü (Düşüş mesafeleri birbirine yakın mı?)
                    drop1 = d1 - d2
                    drop2 = d2 - d3
                    if drop1 > 0 and abs(drop1 - drop2) / drop1 < 0.4:
                        # 3. Şart: Fiyat son dipten sekmiş mi? (Onay)
                        if curr_price > d3 * 1.02 and curr_price < d2:
                            pattern_found = True; pattern_name = "🎢 3 DRIVE (DİP)"; base_score = 85
                            desc = "📉 Trend Yorgunluğu: Fiyat birbiriyle orantılı 3 ardışık dip yapmış durumda. Bu yapı, düşüş trendinin yorulduğuna ve olası bir tepki dönüşünün yaklaşmakta olabileceğine işaret eder."

            # --- KALİTE PUANLAMASI (GELİŞMİŞ DİNAMİK SKORLAMA) ---
            if pattern_found:
                q_score = base_score
                
                # 1. Hiyerarşi Düzenlemesi (Ağırlıklandırma)
                # Kurumsal dönüş ve maliyetlenme formasyonlarına "VIP" ayrıcalığı.
                if "FİNCAN" in pattern_name or "TOBO" in pattern_name or "QML" in pattern_name:
                    q_score += 15
                    
                # 2. Kademeli Hacim Puanlaması
                avg_vol = volume.iloc[-20:].mean()
                vol_ratio = volume.iloc[-1] / avg_vol if avg_vol > 0 else 1
                
                if vol_ratio > 2.5:
                    q_score += 25
                    desc += " (🚀 Ultra Hacim)"
                elif vol_ratio > 1.5:
                    q_score += 12
                    
                # 3. Trend Uyumu (SMA50 Filtresi)
                # Fiyat 50 günlük ortalamanın üzerindeyse trend arkasındadır, daha güvenlidir.
                sma50 = close.rolling(50).mean().iloc[-1]
                if curr_price > sma50:
                    q_score += 8
                    
                # 4. Kırmızı Mum / Düşüş Cezası
                # Arka arkaya 2 gün kırmızı kapatan hisseleri dibe gönderir.
                if close.iloc[-1] < open_.iloc[-1] and close.iloc[-2] < open_.iloc[-2]:
                    q_score -= 35
                    desc += " (⚠️ Düşüşte)"
                # 5. SIĞ TAHTA (LİKİDİTE) UYARISI
                # Son 20 günlük ortalama hacim 5 Milyon lotun altındaysa formasyon adına uyarı ekler.
                if avg_vol < 5000000:
                    pattern_name += " (⚠️ SIĞ TAHTA)"
                    desc += " | 🚨 Dikkat: Ortalama işlem hacmi 5 Milyon lotun altında, manipülasyona açık tahta!"
                # Sonuçları listeye ekliyoruz
                results.append({
                    "Sembol": symbol,
                    "Fiyat": curr_price,
                    "Formasyon": pattern_name,
                    "Detay": desc,
                    "Skor": int(q_score), # Puanı tam sayı (integer) yapıyoruz
                    "Hacim": float(volume.iloc[-1])
                })

        except Exception: continue

        except Exception: continue
            
    if results:
        # En yüksek puanlılar en üstte
        return pd.DataFrame(results).sort_values(by=["Skor", "Hacim"], ascending=[False, False])
    
    return pd.DataFrame()

@st.cache_data(ttl=900)
def scan_rsi_divergence_batch(asset_list):
    """
    RSI UYUMSUZLUK TARAMASI (TEYİTLİ)
    Sol: Negatif Uyumsuzluk (Ayı) - Teyit: Son Mum Kırmızı
    Sağ: Pozitif Uyumsuzluk (Boğa) - Teyit: Son Mum Yeşil
    """
    data = get_batch_data_cached(asset_list, period="6mo")
    if data.empty: return pd.DataFrame(), pd.DataFrame()

    bull_results = []
    bear_results = []
    stock_dfs = []

    # Veriyi hazırlama
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]:
                    stock_dfs.append((symbol, data[symbol]))
            elif len(asset_list) == 1:
                stock_dfs.append((symbol, data))
        except: continue

    # İşçi Fonksiyon (KESİN FİLTRELİ VERSİYON)
    def _worker_div(symbol, df):
        try:
            if df.empty or len(df) < 50: return None
            
            close = df['Close']; open_ = df['Open']; volume = df['Volume']
            if 'Volume' not in df.columns: volume = pd.Series([1]*len(df))
            
            # 1. Göstergeleri Hesapla (SMA50 ve RSI)
            sma50 = close.rolling(50).mean()
            
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi_series = 100 - (100 / (1 + gain/loss))
            
            # Pencereler (Son 5 gün vs Önceki 15 gün)
            curr_p = close.iloc[-5:]; prev_p = close.iloc[-20:-5]
            curr_r = rsi_series.iloc[-5:]; prev_r = rsi_series.iloc[-20:-5]
            
            curr_price = float(close.iloc[-1])
            curr_vol = float(volume.iloc[-1])
            rsi_val = float(rsi_series.iloc[-1])
            sma50_val = float(sma50.iloc[-1])
            
            # Mum Renkleri (Son gün)
            is_red_candle = close.iloc[-1] < open_.iloc[-1]
            is_green_candle = close.iloc[-1] > open_.iloc[-1]

            # --- 1. POZİTİF UYUMSUZLUK (BOĞA) ---
            # Kriterler: Fiyat yeni dip (veya eşit), RSI yükselen dip, RSI < 55 VE Son Mum Yeşil
            is_bull = (curr_p.min() <= prev_p.min()) and \
                      (curr_r.min() > prev_r.min()) and \
                      (rsi_val < 55) and \
                      is_green_candle 
            
            if is_bull:
                return {
                    "type": "bull",
                    "data": {"Sembol": symbol, "Fiyat": curr_price, "Hacim": curr_vol, "RSI": int(rsi_val)}
                }

            # --- 2. NEGATİF UYUMSUZLUK (AYI) ---
            
            # ÖNCE FİLTRELER (RSI 75 üstüyse hiç bakma bile!)
            is_rsi_saturated = rsi_val >= 75
            is_parabolic = curr_price > (sma50_val * 1.20)
            
            # Eğer RSI şişkinse veya Fiyat koptuysa -> DİREKT İPTAL ET (None dön)
            if is_rsi_saturated or is_parabolic:
                return None

            # Sadece normal şartlarda uyumsuzluk ara
            if (curr_p.max() >= prev_p.max()) and (curr_r.max() < prev_r.max()) and (curr_r.max() > 45):
                
                # Son Filtre: Mum Kırmızı mı?
                if is_red_candle:
                    return {
                        "type": "bear",
                        "data": {"Sembol": symbol, "Fiyat": curr_price, "Hacim": curr_vol, "RSI": int(rsi_val)}
                    }
                
            return None
        except: return None

    # Paralel Çalıştırma
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_worker_div, sym, df) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                if res['type'] == 'bull': bull_results.append(res['data'])
                elif res['type'] == 'bear': bear_results.append(res['data'])

    # DataFrame'e çevir ve Hacme göre sırala
    df_bull = pd.DataFrame(bull_results)
    if not df_bull.empty: df_bull = df_bull.sort_values(by="Hacim", ascending=False)
    
    df_bear = pd.DataFrame(bear_results)
    if not df_bear.empty: df_bear = df_bear.sort_values(by="Hacim", ascending=False)

    return df_bull, df_bear

@st.cache_data(ttl=900)
def scan_stp_signals(asset_list):
    """
    Optimize edilmiş STP tarayıcı.
    """
    data = get_batch_data_cached(asset_list, period="2y")
    if data.empty: return [], [], []

    cross_signals = []
    trend_signals = []
    filtered_signals = []

    stock_dfs = []
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]:
                    stock_dfs.append((symbol, data[symbol]))
            else:
                if len(asset_list) == 1:
                    stock_dfs.append((symbol, data))
        except: continue

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_single_stock_stp, sym, df) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                if res["type"] == "cross":
                    cross_signals.append(res["data"])
                    if res.get("is_filtered"):
                        filtered_signals.append(res["data"])
                elif res["type"] == "trend":
                    trend_signals.append(res["data"])

    cross_signals.sort(key=lambda x: x.get("Hacim", 0), reverse=True)
    filtered_signals.sort(key=lambda x: x.get("Hacim", 0), reverse=True) # İstersen filtrelenmişleri de sıralayabilirsin
    trend_signals.sort(key=lambda x: x["Gun"], reverse=False)
    return cross_signals, trend_signals, filtered_signals

def process_single_accumulation(symbol, df, benchmark_series):
    try:
        if df.empty or 'Close' not in df.columns: return None
        df = df.dropna(subset=['Close'])
        if len(df) < 60: return None

        close = df['Close']
        open_ = df['Open']
        high = df['High']
        low = df['Low']
        volume = df['Volume'] if 'Volume' in df.columns else pd.Series([1]*len(df), index=df.index)
        
        # --- 1. SAVAŞ'IN GÜVENLİK KALKANI (SON 2 GÜN KURALI) ---
        price_now = float(close.iloc[-1])
        if len(close) > 2:
            price_2_days_ago = float(close.iloc[-3]) 
            # Son 2 gün toplam %3'ten fazla düştüyse (0.97 altı) ELE.
            if price_now < (price_2_days_ago * 0.97): 
                return None 

        # --- 2. ZAMAN AYARLI HACİM HESABI (PRO-RATA) ---
        last_date = df.index[-1].date()
        today_date = datetime.now().date()
        is_live = (last_date == today_date)
        
        volume_for_check = float(volume.iloc[-1])
        
        if is_live:
            now = datetime.now() + timedelta(hours=3) # TR Saati
            current_hour = now.hour
            current_minute = now.minute
            
            if current_hour < 10: progress = 0.1
            elif current_hour >= 18: progress = 1.0
            else:
                progress = ((current_hour - 10) * 60 + current_minute) / 480.0
                progress = max(0.1, min(progress, 1.0))
            
            if progress > 0:
                volume_for_check = float(volume.iloc[-1]) / progress

        # --- 3. MEVCUT MANTIK (TOPLAMA & FORCE INDEX) ---
        delta = close.diff()
        force_index = delta * volume 
        mf_smooth = force_index.ewm(span=5, adjust=False).mean()

        last_10_mf = mf_smooth.tail(10)
        last_10_close = close.tail(10)
        
        if len(last_10_mf) < 10: return None
        
        pos_days_count = (last_10_mf > 0).sum()
        if pos_days_count < 7: return None 

        price_start = float(last_10_close.iloc[0]) 
        if price_start == 0: return None
        
        change_pct = (price_now - price_start) / price_start
        avg_mf = float(last_10_mf.mean())
        
        if avg_mf <= 0: return None
        if change_pct > 0.05: return None 
        # --- HALÜSİNASYON ÖNLEYİCİ (RSI FİLTRESİ) ---
        # Eğer RSI > 60 ise, fiyat tepededir. Bu 'Toplama' değil, 'Dağıtım'dır.
        # Bu yüzden RSI şişikse, bu hisseyi listeden atıyoruz.
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi_check = 100 - (100 / (1 + (gain / loss))).iloc[-1]
        
        if rsi_check > 60: return None # Şişkin hisseyi yok say.

        # --- 4. MANSFIELD RS (GÜÇ) ---
        rs_status = "Zayıf"
        rs_score = 0
        if benchmark_series is not None:
            try:
                common_idx = close.index.intersection(benchmark_series.index)
                if len(common_idx) > 50:
                    stock_aligned = close.loc[common_idx]
                    bench_aligned = benchmark_series.loc[common_idx]
                    rs_ratio = stock_aligned / bench_aligned
                    rs_ma = rs_ratio.rolling(50).mean()
                    mansfield = ((rs_ratio / rs_ma) - 1) * 10
                    curr_rs = float(mansfield.iloc[-1])
                    if curr_rs > 0: 
                        rs_status = "GÜÇLÜ (Endeks Üstü)"
                        rs_score = 1 
                        if curr_rs > float(mansfield.iloc[-5]): 
                            rs_status += " 🚀"
                            rs_score = 2
            except: pass

        # --- 5. POCKET PIVOT (ZAMAN AYARLI KONTROL) ---
        is_pocket_pivot = False
        pp_desc = "-"
        
        is_down_day = close < open_
        down_volumes = volume.where(is_down_day, 0)
        max_down_vol_10 = down_volumes.iloc[-11:-1].max()
        
        is_up_day = float(close.iloc[-1]) > float(open_.iloc[-1])
        
        if is_up_day and (volume_for_check > max_down_vol_10):
            is_pocket_pivot = True
            if float(volume.iloc[-1]) < max_down_vol_10:
                pp_desc = "⚡ PIVOT (Hacim Hızı Yüksek)"
            else:
                pp_desc = "⚡ POCKET PIVOT (Onaylı)"
            rs_score += 3 

        # --- YENİ EKLENEN: LAZYBEAR SQUEEZE KONTROLÜ ---
        is_sq = check_lazybear_squeeze(df)
        
        # Kalite Etiketi Belirleme
        if is_sq:
            quality_label = "A KALİTE (Sıkışmış)"
            # Squeeze varsa skoru ödüllendir (Listede üste çıksın)
            rs_score += 5 
        else:
            quality_label = "B KALİTE (Normal)"

        # --- SKORLAMA ---
        base_score = avg_mf * (10.0 if change_pct < 0 else 5.0)
        final_score = base_score * (1 + rs_score) 
        if avg_mf > 1_000_000: mf_str = f"{avg_mf/1_000_000:.1f}M"
        elif avg_mf > 1_000: mf_str = f"{avg_mf/1_000:.0f}K"
        else: mf_str = f"{int(avg_mf)}"
        squeeze_score = final_score / (abs(change_pct) + 0.02)

        return {
            "Sembol": symbol,
            "Fiyat": f"{price_now:.2f}",
            "Degisim_Raw": change_pct,
            "Degisim_Str": f"%{change_pct*100:.1f}",
            "MF_Gucu_Goster": mf_str, 
            "Gun_Sayisi": f"{pos_days_count}/10",
            "Skor": squeeze_score,
            "RS_Durumu": rs_status,       
            "Pivot_Sinyali": pp_desc,     
            "Pocket_Pivot": is_pocket_pivot,
            "Kalite": quality_label,
            "Hacim": float(volume.iloc[-1])
        }
    except Exception: return None

@st.cache_data(ttl=900)
def scan_hidden_accumulation(asset_list):
    # 1. Önce Hisse Verilerini Çek
    data = get_batch_data_cached(asset_list, period="1y") # RS için süreyi 1y yaptım (önce 1mo idi)
    if data.empty: return pd.DataFrame()

    # 2. Endeks Verisini Çek (Sadece tek sefer)
    current_cat = st.session_state.get('category', 'S&P 500')
    benchmark = get_benchmark_data(current_cat)

    results = []
    stock_dfs = []
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]:
                    stock_dfs.append((symbol, data[symbol]))
            else:
                if len(asset_list) == 1: stock_dfs.append((symbol, data))
        except: continue

    # 3. Paralel İşlem (Benchmark'ı da gönderiyoruz)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # benchmark serisini her fonksiyona argüman olarak geçiyoruz
        futures = [executor.submit(process_single_accumulation, sym, df, benchmark) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: results.append(res)

    if results: 
        df_res = pd.DataFrame(results)
        # Önce Pocket Pivot olanları, sonra Skoru yüksek olanları üste al
        return df_res.sort_values(by=["Pocket_Pivot", "Kalite", "Skor", "Hacim"], ascending=[False, True, False, False])
    
    return pd.DataFrame()

def process_single_radar1(symbol, df):
    try:
        if df.empty or 'Close' not in df.columns: return None
        df = df.dropna(subset=['Close'])
        if len(df) < 60: return None
        
        close = df['Close']; high = df['High']; low = df['Low']
        volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))
        
        # Göstergeler
        ema5 = close.ewm(span=5, adjust=False).mean()
        ema20 = close.ewm(span=20, adjust=False).mean()
        sma20 = close.rolling(20).mean(); std20 = close.rolling(20).std()
        
        # Bollinger Squeeze Hesabı
        bb_width = ((sma20 + 2*std20) - (sma20 - 2*std20)) / (sma20 - 0.0001)

        # MACD Hesabı
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        hist = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()
        
        # RSI Hesabı
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain / loss)))
        
        # ADX Hesabı (Trend Gücü)
        try:
            plus_dm = high.diff(); minus_dm = low.diff()
            plus_dm[plus_dm < 0] = 0; minus_dm[minus_dm > 0] = 0
            tr1 = pd.DataFrame(high - low); tr2 = pd.DataFrame(abs(high - close.shift(1))); tr3 = pd.DataFrame(abs(low - close.shift(1)))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr_adx = tr.rolling(14).mean()
            plus_di = 100 * (plus_dm.ewm(alpha=1/14).mean() / atr_adx)
            minus_di = 100 * (abs(minus_dm).ewm(alpha=1/14).mean() / atr_adx)
            dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
            curr_adx = float(dx.rolling(14).mean().iloc[-1])
        except: curr_adx = 20

        score = 0; reasons = []; details = {}
        curr_c = float(close.iloc[-1]); curr_vol = float(volume.iloc[-1])
        avg_vol = float(volume.rolling(5).mean().iloc[-1]) if len(volume) > 5 else 1.0
        
        # --- PUANLAMA (7 MADDE) ---
        
        # 1. Squeeze (Patlama Hazırlığı)
        if bb_width.iloc[-1] <= bb_width.tail(60).min() * 1.1: score += 1; reasons.append("🚀 Squeeze"); details['Squeeze'] = True
        else: details['Squeeze'] = False
        
        # 2. Trend (Kısa Vade Yükseliş)
        trend_condition = (ema5.iloc[-1] > ema20.iloc[-1] * 1.01) 
            
        if trend_condition: 
                score += 1
                reasons.append("⚡ Trend")
                details['Trend'] = True
        else: 
                details['Trend'] = False
        
        # 3. MACD (Momentum Artışı)
        if hist.iloc[-1] > hist.iloc[-2]: score += 1; reasons.append("🟢 MACD"); details['MACD'] = True
        else: details['MACD'] = False
        
        # 4. Hacim (İlgi Var mı?)
        if curr_vol > avg_vol * 1.2: score += 1; reasons.append("🔊 Hacim"); details['Hacim'] = True
        else: details['Hacim'] = False
        
        # 5. Breakout (Zirveye Yakınlık)
        if curr_c >= high.tail(20).max() * 0.98: score += 1; reasons.append("🔨 Breakout"); details['Breakout'] = True
        else: details['Breakout'] = False
        
        # 6. RSI Güçlü (İvme)
        rsi_c = float(rsi.iloc[-1])
        if 30 < rsi_c < 65 and rsi_c > float(rsi.iloc[-2]): score += 1; reasons.append("⚓ RSI Güçlü"); details['RSI Güçlü'] = (True, rsi_c)
        else: details['RSI Güçlü'] = (False, rsi_c)
        
        # 7. ADX (Trendin Gücü Yerinde mi?)
        if curr_adx > 25: 
            score += 1; reasons.append(f"💪 Güçlü Trend"); details['ADX Durumu'] = (True, curr_adx)
        else:
            details['ADX Durumu'] = (False, curr_adx)

        return { "Sembol": symbol, "Fiyat": f"{curr_c:.2f}", "Skor": score, "Nedenler": " | ".join(reasons), "Detaylar": details }
    except: return None

@st.cache_data(ttl=3600)
def analyze_market_intelligence(asset_list):
    data = get_batch_data_cached(asset_list, period="6mo")
    if data.empty: return pd.DataFrame()

    signals = []
    stock_dfs = []
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]: stock_dfs.append((symbol, data[symbol]))
            else:
                if len(asset_list) == 1: stock_dfs.append((symbol, data))
        except: continue

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_single_radar1, sym, df) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: signals.append(res)

    return pd.DataFrame(signals).sort_values(by="Skor", ascending=False) if signals else pd.DataFrame()

def process_single_radar2(symbol, df, idx, min_price, max_price, min_avg_vol_m):
    try:
        if df.empty or 'Close' not in df.columns: return None
        df = df.dropna(subset=['Close'])
        if len(df) < 120: return None
        
        close = df['Close']; high = df['High']; low = df['Low']
        volume = df['Volume'] if 'Volume' in df.columns else pd.Series([0]*len(df))
        curr_c = float(close.iloc[-1])
        
        # Filtreler
        if curr_c < min_price or curr_c > max_price: return None
        avg_vol_20 = float(volume.rolling(20).mean().iloc[-1])
        if avg_vol_20 < min_avg_vol_m * 1e6: return None
        
        # Trend Ortalamaları
        sma20 = close.rolling(20).mean(); sma50 = close.rolling(50).mean()
        sma100 = close.rolling(100).mean(); sma200 = close.rolling(200).mean()
        
        trend = "Yatay"
        if not np.isnan(sma200.iloc[-1]):
            if curr_c > sma50.iloc[-1] > sma100.iloc[-1] > sma200.iloc[-1] and sma200.iloc[-1] > sma200.iloc[-20]: trend = "Boğa"
            elif curr_c < sma200.iloc[-1] and sma200.iloc[-1] < sma200.iloc[-20]: trend = "Ayı"
        
        # RSI ve MACD (Sadece Setup için histogram hesabı kalıyor, puanlamadan çıkacak)
        delta = close.diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain / loss))); rsi_c = float(rsi.iloc[-1])
        ema12 = close.ewm(span=12, adjust=False).mean(); ema26 = close.ewm(span=26, adjust=False).mean()
        hist = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()
        
        # Breakout Oranı
        recent_high_60 = float(high.rolling(60).max().iloc[-1])
        breakout_ratio = curr_c / recent_high_60 if recent_high_60 > 0 else 0
        
        # RS Skoru (Endeks)
        rs_score = 0.0
        if idx is not None and len(close) > 60 and len(idx) > 60:
            common_index = close.index.intersection(idx.index)
            if len(common_index) > 60:
                cs = close.reindex(common_index); isx = idx.reindex(common_index)
                rs_score = float((cs.iloc[-1]/cs.iloc[-60]-1) - (isx.iloc[-1]/isx.iloc[-60]-1))
        
        # --- YENİ EKLENEN: ICHIMOKU BULUTU (Kumo) ---
        # Bulut şu anki fiyatın altında mı? (Trend Desteği)
        # Ichimoku değerleri 26 periyot ileri ötelenir. Yani bugünün bulutu, 26 gün önceki verilerle çizilir.
        tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
        kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
        
        # Span A (Bugün için değeri 26 gün önceki hesaptan gelir)
        span_a_calc = (tenkan + kijun) / 2
        # Span B (Bugün için değeri 26 gün önceki hesaptan gelir)
        span_b_calc = (high.rolling(52).max() + low.rolling(52).min()) / 2
        
        # Bugünün bulut sınırları (Veri setinin sonundan 26 önceki değerler)
        cloud_a = float(span_a_calc.iloc[-26])
        cloud_b = float(span_b_calc.iloc[-26])
        is_above_cloud = curr_c > max(cloud_a, cloud_b)
        # -----------------------------------------------

        setup = "-"; tags = []; score = 0; details = {}
        avg_vol_20 = max(avg_vol_20, 1); vol_spike = volume.iloc[-1] > avg_vol_20 * 1.3
        
        # Setup Tespiti
        if trend == "Boğa" and breakout_ratio >= 0.97: setup = "Breakout"; tags.append("Zirve")
        if trend == "Boğa" and setup == "-":
            if sma20.iloc[-1] <= curr_c <= sma50.iloc[-1] * 1.02 and 40 <= rsi_c <= 55: setup = "Pullback"; tags.append("Düzeltme")
            if volume.iloc[-1] < avg_vol_20 * 0.9: score += 0; tags.append("Sığ Satış")
        if setup == "-":
            if rsi.iloc[-2] < 30 <= rsi_c and hist.iloc[-1] > hist.iloc[-2]: setup = "Dip Dönüşü"; tags.append("Dip Dönüşü")
        
        # --- PUANLAMA (7 Madde) ---
        
        # 1. Hacim Patlaması
        if vol_spike: score += 1; tags.append("Hacim+"); details['Hacim Patlaması'] = True
        else: details['Hacim Patlaması'] = False

        # 2. RS (Endeks Gücü)
        if rs_score > 0: score += 1; tags.append("RS+"); details['RS (S&P500)'] = True
        else: details['RS (S&P500)'] = False
        
        # 3. Boğa Trendi (SMA Dizilimi)
        if trend == "Boğa": score += 1; details['Boğa Trendi'] = True
        else:
            if trend == "Ayı": score -= 1
            details['Boğa Trendi'] = False
            
        # 4. Ichimoku Bulutu (YENİ - MACD YERİNE GELDİ)
        if is_above_cloud: score += 1; details['Ichimoku'] = True
        else: details['Ichimoku'] = False

        # 5. 60 Günlük Zirveye Yakınlık
        details['60G Zirve'] = breakout_ratio >= 0.90
        if details['60G Zirve']: score += 1

        # 6. RSI Uygun Bölge (Aşırı şişmemiş)
        is_rsi_suitable = (40 <= rsi_c <= 65) # Biraz genişlettim
        details['RSI Bölgesi'] = (is_rsi_suitable, rsi_c)
        if is_rsi_suitable: score += 1
        
        # 7. Setup Puanı (Yukarıda hesaplandı, max 2 puan ama biz varlığını kontrol edelim)
        # Setup varsa ekstra güvenilirdir.
        if setup != "-": score += 1
        
        return { "Sembol": symbol, "Fiyat": round(curr_c, 2), "Trend": trend, "Setup": setup, "Skor": score, "RS": round(rs_score * 100, 1), "Etiketler": " | ".join(tags), "Detaylar": details }
    except: return None

# --- YENİ EKLENEN HACİM FONKSİYONLARI ---

def calculate_volume_delta(df):
    """Mumun kapanışına göre tahmini Hacim Deltası hesaplar."""
    df = df.copy()
    df['Range'] = df['High'] - df['Low']
    df['Range'] = df['Range'].replace(0, 0.0001) # Sıfıra bölünme hatasını önle
    
    df['Buying_Pressure'] = (df['Close'] - df['Low']) / df['Range']
    df['Selling_Pressure'] = (df['High'] - df['Close']) / df['Range']
    
    df['Buying_Volume'] = df['Volume'] * df['Buying_Pressure']
    df['Selling_Volume'] = df['Volume'] * df['Selling_Pressure']
    
    # Günlük net hacim farkı (Alıcılar - Satıcılar)
    df['Volume_Delta'] = df['Buying_Volume'] - df['Selling_Volume']
    return df

def calculate_volume_profile_poc(df, lookback=20, bins=20):
    """Belirtilen periyotta en çok hacmin yığıldığı fiyatı (POC) orantısal olarak bulur."""
    if len(df) < lookback:
        lookback = len(df)
        
    recent_df = df.tail(lookback).copy()
    min_price = float(recent_df['Low'].min())
    max_price = float(recent_df['High'].max())
    
    if min_price == max_price: # Fiyat hiç değişmemişse
        return min_price
        
    # Fiyat dilimlerini (bins) oluştur (Kenar noktaları için bins + 1 kullanıyoruz)
    price_bins = np.linspace(min_price, max_price, bins + 1)
    volume_profile = np.zeros(bins)
    
    # Her bir mumun hacmini, geçtiği dilimlere adil (orantısal) şekilde ekle
    for _, row in recent_df.iterrows():
        high = float(row['High'])
        low = float(row['Low'])
        vol = float(row['Volume'])
        candle_range = high - low
        
        if candle_range <= 0:
            # Doji mumu ise hacmi tek bir dilime at
            idx = np.digitize((high + low) / 2, price_bins) - 1
            idx = min(max(idx, 0), bins - 1)
            volume_profile[idx] += vol
            continue
            
        for i in range(bins):
            bin_bottom = price_bins[i]
            bin_top = price_bins[i+1]
            
            # Mum bu fiyat diliminden geçmiş mi?
            if high >= bin_bottom and low <= bin_top:
                overlap_top = min(high, bin_top)
                overlap_bottom = max(low, bin_bottom)
                overlap_range = overlap_top - overlap_bottom
                
                if overlap_range > 0:
                    # Kesiştiği alanın yüksekliğine göre hacmi bölüştür
                    volume_profile[i] += vol * (overlap_range / candle_range)
                    
    # En yüksek hacme sahip dilimi bul
    poc_index = np.argmax(volume_profile)
    
    # POC fiyatını dilimin TAM ORTASI olarak belirle (eski koddaki gibi alt sınır değil)
    poc_price = (price_bins[poc_index] + price_bins[poc_index + 1]) / 2.0
    
    return poc_price

def calculate_volume_profile(df, lookback=50, bins=20):
    """
    Son 'lookback' kadar mumu alır, fiyatı 'bins' kadar parçaya böler 
    ve en çok hacmin döndüğü fiyatı (Point of Control) orantısal dağılımla bulur.
    """
    if len(df) < lookback:
        lookback = len(df)
        
    recent_df = df.tail(lookback).copy()
    
    # Fiyatı min ve max arasında belirle
    min_price = float(recent_df['Low'].min())
    max_price = float(recent_df['High'].max())
    
    if min_price == max_price: 
        return min_price
        
    # Fiyat dilimlerini oluştur
    price_bins = np.linspace(min_price, max_price, bins + 1)
    volume_profile = np.zeros(bins)
    
    # Typical_Price yerine Orantısal Dağılım Döngüsü
    for _, row in recent_df.iterrows():
        high = float(row['High'])
        low = float(row['Low'])
        vol = float(row['Volume'])
        candle_range = high - low
        
        if candle_range <= 0:
            idx = np.digitize((high + low) / 2, price_bins) - 1
            idx = min(max(idx, 0), bins - 1)
            volume_profile[idx] += vol
            continue
            
        for i in range(bins):
            bin_bottom = price_bins[i]
            bin_top = price_bins[i+1]
            
            if high >= bin_bottom and low <= bin_top:
                overlap_top = min(high, bin_top)
                overlap_bottom = max(low, bin_bottom)
                overlap_range = overlap_top - overlap_bottom
                
                if overlap_range > 0:
                    volume_profile[i] += vol * (overlap_range / candle_range)
                    
    # En yüksek hacme sahip dilimi (POC) bul
    poc_index = np.argmax(volume_profile)
    
    # POC Fiyatını belirle
    poc_price = (price_bins[poc_index] + price_bins[poc_index + 1]) / 2.0
        
    return poc_price
    
# ==============================================================================
# 🧠 MERKEZİ VERİ ÖNBELLEĞİ (BAN KORUMASI VE SÜPER HIZ)
# ==============================================================================
@st.cache_data(ttl=900, show_spinner=False)
def fetch_market_data_cached(tickers_tuple):
    import yfinance as yf
    tickers_str = " ".join(tickers_tuple)
    return yf.download(tickers_str, period="1y", group_by='ticker', auto_adjust=True, progress=False, threads=True)

@st.cache_data(ttl=900, show_spinner=False)
def fetch_index_data_cached():
    import yfinance as yf
    import pandas as pd
    try:
        index_df = yf.download("XU100.IS", period="1y", progress=False)
        if not index_df.empty:
            if isinstance(index_df.columns, pd.MultiIndex):
                return index_df['Close'].iloc[:, 0] if not index_df['Close'].empty else None
            else:
                return index_df['Close']
    except:
        pass
    return None

@st.cache_data(ttl=3600)
def radar2_scan(asset_list, min_price=5, max_price=5000, min_avg_vol_m=0.5):
    # ORTAK HAFIZADAN ÇEKER (Altın Fırsatlar ile Aynı Havuz)
    try:
        data = fetch_market_data_cached(tuple(asset_list))
    except Exception as e:
        st.error(f"Radar 2 veri hatası: {e}")
        return pd.DataFrame()
        
    if data.empty: return pd.DataFrame()
    
    try: idx = yf.download("^GSPC", period="1y", progress=False)["Close"]
    except: idx = None

    results = []
    stock_dfs = []
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]: stock_dfs.append((symbol, data[symbol]))
            else:
                if len(asset_list) == 1: stock_dfs.append((symbol, data))
        except: continue

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_single_radar2, sym, df, idx, min_price, max_price, min_avg_vol_m) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: results.append(res)

    return pd.DataFrame(results).sort_values(by=["Skor", "RS"], ascending=False).head(50) if results else pd.DataFrame()

def process_single_breakout(symbol, df):
    try:
        if df.empty or 'Close' not in df.columns: return None
        df = df.dropna(subset=['Close'])
        # Minimum veri şartı (EMA/SMA hesapları için)
        if len(df) < 50: return None 

        close = df['Close']; high = df['High']; low = df['Low']; open_ = df['Open']
        volume = df['Volume'] if 'Volume' in df.columns else pd.Series([1]*len(df))
        
        # --- 1. ZAMAN AYARLI HACİM (SABAH KORUMASI) ---
        last_date = df.index[-1].date()
        today_date = datetime.now().date()
        is_live = (last_date == today_date)
        
        progress = 1.0 
        if is_live:
            now = datetime.now() + timedelta(hours=3) # TR Saati
            current_hour = now.hour
            current_minute = now.minute
            
            if current_hour < 10: progress = 0.1
            elif current_hour >= 18: progress = 1.0
            else:
                progress = ((current_hour - 10) * 60 + current_minute) / 480.0
                progress = max(0.1, min(progress, 1.0))

        curr_vol_raw = float(volume.iloc[-1])
        curr_vol_projected = curr_vol_raw / progress
        
        vol_20 = volume.iloc[:-1].tail(20).mean()
        if pd.isna(vol_20) or vol_20 == 0: vol_20 = 1

        rvol = curr_vol_projected / vol_20
        
        # --- TEKNİK HESAPLAMALAR ---
        ema5 = close.ewm(span=5, adjust=False).mean()
        ema20 = close.ewm(span=20, adjust=False).mean()
        sma20 = close.rolling(20).mean(); sma50 = close.rolling(50).mean()
        
        # 👑 DÜZELTME BURADA: Artık iğnelere (high) değil, gövdelere (close) bakıyoruz!
        high_val = close.iloc[:-1].tail(45).max()
        curr_price = close.iloc[-1]
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]
        
        # --- ŞARTLAR ---
        cond_ema = ema5.iloc[-1] > ema20.iloc[-1]
        cond_vol = rvol > 1.2 
        cond_prox = (curr_price > high_val * 0.90) and (curr_price <= high_val * 1.1)
        cond_rsi = rsi < 70
        sma_ok = sma20.iloc[-1] > sma50.iloc[-1]
        
        if cond_ema and cond_vol and cond_prox and cond_rsi:
            
            sq_now, sq_prev = check_lazybear_squeeze_breakout(df)
            is_firing = sq_prev and not sq_now
            
            sort_score = rvol + (1000 if is_firing else 0)

            # Görsel Metin
            prox_pct = (curr_price / high_val) * 100
            
            if is_firing:
                prox_str = f"🚀 TETİKLENDİ"
            elif sq_now:
                prox_str = f"💣 Sıkışma Var"
            else:
                # DÜZELTME: Eğer fiyat zaten direnci (%100'ü) geçmişse ekranda KIRIYOR yazsın
                if prox_pct >= 100:
                    prox_str = f"%{prox_pct:.1f} (Direnç Üstü)"
                else:
                    prox_str = f"%{prox_pct:.1f}" + (" (Sınırda)" if prox_pct >= 98 else " (Hazırlık)")
            
            # Fitil Uyarısı
            body_size = abs(close.iloc[-1] - open_.iloc[-1])
            upper_wick = high.iloc[-1] - max(open_.iloc[-1], close.iloc[-1])
            is_wick_rejected = (upper_wick > body_size * 1.5) and (upper_wick > 0)
            wick_warning = " ⚠️ Satış Baskısı" if is_wick_rejected else ""
            
            if (curr_vol_raw < vol_20) and (rvol > 1.2):
                rvol_text = "Hız Yüksek (Proj.) 📈"
            else:
                rvol_text = "Olağanüstü 🐳" if rvol > 2.0 else "İlgi Artıyor 📈"

            return { 
                "Sembol_Raw": symbol, 
                "Sembol_Display": symbol, 
                "Fiyat": f"{curr_price:.2f}", 
                "Zirveye Yakınlık": prox_str + wick_warning, 
                "Hacim Durumu": rvol_text, 
                "Trend Durumu": f"✅EMA | {'✅SMA' if sma_ok else '❌SMA'}", 
                "RSI": f"{rsi:.0f}", 
                "SortKey": sort_score,
                "Hacim": curr_vol_raw
            }
        return None
    except: return None

@st.cache_data(ttl=3600)
def agent3_breakout_scan(asset_list):
    data = get_batch_data_cached(asset_list, period="6mo")
    if data.empty: return pd.DataFrame()

    results = []
    stock_dfs = []
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]: stock_dfs.append((symbol, data[symbol]))
            else:
                if len(asset_list) == 1: stock_dfs.append((symbol, data))
        except: continue

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_single_breakout, sym, df) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: results.append(res)
    
    return pd.DataFrame(results).sort_values(by="Hacim", ascending=False) if results else pd.DataFrame()

def process_single_confirmed(symbol, df):
    try:
        if df.empty or 'Close' not in df.columns: return None
        df = df.dropna(subset=['Close'])
        if len(df) < 100: return None 

        # DÜZELTME 1: open_ eklendi (Aşağıda Gap hesabı hata vermesin diye)
        close = df['Close']; high = df['High']; open_ = df['Open']; volume = df['Volume'] if 'Volume' in df.columns else pd.Series([1]*len(df))
        
        # --- 1. ADIM: ZİRVE KONTROLÜ (Son 20 İş Günü) ---
        # 👑 DÜZELTME 2: Artık iğnelere (high) değil, mum kapanışlarına (close) bakıyoruz!
        high_val = close.iloc[:-1].tail(20).max()
        curr_close = float(close.iloc[-1])
        
        # Eğer bugünkü fiyat, geçmiş 20 günün zirvesini geçmediyse ELE.
        if curr_close <= high_val: return None 

        # --- 2. ADIM: GÜVENLİ HACİM HESABI (TIME-BASED) ---
        
        # Önce Tarih Kontrolü: Elimizdeki son veri (df.index[-1]) BUGÜNE mi ait?
        last_data_date = df.index[-1].date()
        today_date = datetime.now().date()
        
        # Eğer son veri bugüne aitse "Canlı Seans" mantığı çalışsın.
        # Eğer veri eskiyse (akşam olduysa veya hafta sonuysa), gün bitmiş sayılır (Progress = 1.0)
        is_live_today = (last_data_date == today_date)
        
        day_progress = 1.0 # Varsayılan: Gün bitti (%100)

        if is_live_today:
            # Sadece veri "Bugün" ise saat hesabına gir.
            now = datetime.now()
            current_hour = now.hour
            current_minute = now.minute
            
            # BIST Seans: 10:00 - 18:00 (480 dk)
            if current_hour < 10:
                day_progress = 0.1 # Seans öncesi veri gelirse sapıtmasın
            elif current_hour >= 18:
                day_progress = 1.0 # Seans bitti
            else:
                minutes_passed = (current_hour - 10) * 60 + current_minute
                day_progress = minutes_passed / 480.0
                day_progress = max(0.1, min(day_progress, 1.0)) # 0.1 ile 1.0 arasına sıkıştır

        # Geçmiş 20 günün ortalama hacmi (Bugün hariç)
        avg_vol_20 = volume.rolling(20).mean().shift(1).iloc[-1]
        
        # BEKLENEN HACİM
        expected_vol_now = avg_vol_20 * day_progress
        curr_vol = float(volume.iloc[-1])
        
        # PERFORMANS ORANI
        # Eğer günün yarısı bittiyse ve hacim de ortalamanın yarısıysa oran 1.0 olur.
        # Biz biraz 'hareket' istiyoruz, o yüzden 0.6 (Normalin %60'ı) alt sınır olsun.
        if avg_vol_20 > 0:
            performance_ratio = curr_vol / expected_vol_now
        else:
            performance_ratio = 0
            
        # Filtre: Eğer o saate kadar yapması gereken hacmi yapmadıysa ELE.
        if performance_ratio < 0.6: return None 
        
        # --- GÜVENLİK 3: GAP (BOŞLUK) TUZAĞI ---
        prev_close = float(close.iloc[-2])
        curr_open = float(open_.iloc[-1])
        gap_pct = (curr_open - prev_close) / prev_close
        if gap_pct > 0.03: return None # %3'ten fazla GAP'li açıldıysa tren kaçmıştır.
       
        # --- GÖRSEL ETİKETLEME ---
        # Kullanıcıya "Günlük ortalamanın kaç katına gidiyor" bilgisini verelim
        # Bu 'Projected Volume' (Tahmini Gün Sonu Hacmi) mantığıdır.
        vol_display = f"{performance_ratio:.1f}x (Hız)"
        
        if performance_ratio > 1.5: vol_display = f"{performance_ratio:.1f}x (Patlama🔥)"
        elif performance_ratio >= 1.0: vol_display = f"{performance_ratio:.1f}x (Güçlü✅)"
        else: vol_display = f"{performance_ratio:.1f}x (Yeterli🆗)"

        # --- 3. DİĞER TEKNİK FİLTRELER ---
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        bb_upper = sma20 + (2 * std20); bb_lower = sma20 - (2 * std20)
        bb_width = (bb_upper - bb_lower) / sma20
        avg_width = bb_width.rolling(20).mean().iloc[-1]
        
        is_range_breakout = bb_width.iloc[-2] < avg_width * 0.9 
        breakout_type = "📦 RANGE" if is_range_breakout else "🏔️ ZİRVE"
        
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]
        
        if rsi > 85: return None

        return {
            "Sembol": symbol,
            "Fiyat": f"{curr_close:.2f}",
            "Kirim_Turu": breakout_type,
            "Hacim_Kati": vol_display,
            "RSI": int(rsi),
            "SortKey": performance_ratio,
            "Hacim": curr_vol
        }
    except: return None

@st.cache_data(ttl=3600)
def scan_confirmed_breakouts(asset_list):
    data = get_batch_data_cached(asset_list, period="1y")
    if data.empty: return pd.DataFrame()

    results = []
    stock_dfs = []
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]: stock_dfs.append((symbol, data[symbol]))
            else:
                if len(asset_list) == 1: stock_dfs.append((symbol, data))
        except: continue

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_single_confirmed, sym, df) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: results.append(res)
    
    return pd.DataFrame(results).sort_values(by="Hacim", ascending=False).head(20) if results else pd.DataFrame()

# --- TEMEL VE MASTER SKOR FONKSİYONLARI (YENİ) ---
@st.cache_data(ttl=3600)
def get_fundamental_score(ticker):
    """
    GLOBAL STANDART V2: Kademeli Puanlama (Grading System)
    AGNC gibi sektörleri veya Apple gibi devleri '0' ile cezalandırmaz.
    """
    # Endeks veya Kripto kontrolü
    if ticker.startswith("^") or "XU" in ticker or "-USD" in ticker:
        return {"score": 50, "details": [], "valid": False} 

    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if not info: return {"score": 50, "details": ["Veri Yok"], "valid": False}
        
        score = 0
        details = []
        
        # --- KADEMELİ PUANLAMA MOTORU ---
        def rate(val, thresholds, max_p):
            if not val: return 0
            val = val * 100 if val < 10 else val # Yüzdeye çevir
            # Eşikler: [Düşük, Orta, Yüksek] -> Puanlar kademeli artar
            step = max_p / len(thresholds)
            earned = 0
            for t in thresholds:
                if val > t: earned += step
            return earned

        # 1. BÜYÜME (GROWTH) - Max 40 Puan
        # Ciro Büyümesi: %0 üstü puan almaya başlar. %25 üstü tavan yapar.
        rev_g = info.get('revenueGrowth', 0)
        s_rev = rate(rev_g, [0, 10, 20, 25], 20) 
        score += s_rev
        if s_rev >= 10: details.append(f"Ciro Büyümesi: %{rev_g*100:.1f}")

        # Kâr Büyümesi
        earn_g = info.get('earningsGrowth', 0)
        s_earn = rate(earn_g, [0, 10, 20, 25], 20)
        score += s_earn
        if s_earn >= 10: details.append(f"Kâr Büyümesi: %{earn_g*100:.1f}")

        # 2. KALİTE (QUALITY) - Max 40 Puan
        # ROE: %5 üstü puan başlar. %20 üstü tavan.
        roe = info.get('returnOnEquity', 0)
        s_roe = rate(roe, [5, 10, 15, 20], 20)
        score += s_roe
        if s_roe >= 10: details.append(f"ROE: %{roe*100:.1f}")

        # Marjlar
        margin = info.get('profitMargins', 0)
        s_marg = rate(margin, [5, 10, 15, 20], 20)
        score += s_marg
        if s_marg >= 10: details.append(f"Net Marj: %{margin*100:.1f}")

        # 3. KURUMSAL SAHİPLİK - Max 20 Puan
        inst = info.get('heldPercentInstitutions', 0)
        s_inst = rate(inst, [10, 30, 50, 70], 20)
        score += s_inst
        if s_inst >= 10: details.append(f"Kurumsal: %{inst*100:.0f}")

        return {"score": min(score, 100), "details": details, "valid": True}
        
    except Exception:
        return {"score": 50, "details": [], "valid": False}


# ==============================================================================
# YENİ: TEMEL ANALİZ VE MASTER SKOR MOTORU (GLOBAL STANDART)
# ==============================================================================

@st.cache_data(ttl=3600)
def get_fundamental_score(ticker):
    """
    GLOBAL STANDART: IBD, Stockopedia ve Buffett Kriterlerine Göre Puanlama.
    Veri Kaynağı: yfinance
    """
    # Endeks veya Kripto ise Temel Analiz Yoktur
    if ticker.startswith("^") or "XU" in ticker or "-USD" in ticker:
        return {"score": 0, "details": [], "valid": False}

    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if not info: return {"score": 50, "details": ["Veri Yok"], "valid": False}
        
        score = 0
        details = []
        
        # 1. KALİTE (QUALITY) - %40 Etki (Warren Buffett Kriterleri)
        # ROE (Özkaynak Kârlılığı) - Şirketin verimliliği
        roe = info.get('returnOnEquity', 0)
        if roe and roe > 0.20: score += 20; details.append(f"Müthiş ROE: %{roe*100:.1f}")
        elif roe and roe > 0.12: score += 10
            
        # Net Kâr Marjı (Profit Margins) - Rekabet gücü
        margin = info.get('profitMargins', 0)
        if margin and margin > 0.20: score += 20; details.append(f"Yüksek Marj: %{margin*100:.1f}")
        elif margin and margin > 0.10: score += 10

        # 2. BÜYÜME (GROWTH) - %40 Etki (IBD / CANSLIM Kriterleri)
        # Çeyreklik Ciro Büyümesi
        rev_growth = info.get('revenueGrowth', 0)
        if rev_growth and rev_growth > 0.25: score += 20; details.append(f"Ciro Patlaması: %{rev_growth*100:.1f}")
        elif rev_growth and rev_growth > 0.15: score += 10
            
        # Çeyreklik Kâr Büyümesi
        earn_growth = info.get('earningsGrowth', 0)
        if earn_growth and earn_growth > 0.20: score += 20; details.append(f"Kâr Büyümesi: %{earn_growth*100:.1f}")
        elif earn_growth and earn_growth > 0.10: score += 10

        # 3. SAHİPLİK (SMART MONEY) - %20 Etki
        inst_own = info.get('heldPercentInstitutions', 0)
        if inst_own and inst_own > 0.40: score += 20; details.append("Fonlar Topluyor")
        elif inst_own and inst_own > 0.20: score += 10
            
        return {"score": min(score, 100), "details": details, "valid": True}
        
    except Exception:
        return {"score": 50, "details": ["Veri Hatası"], "valid": False}

@st.cache_data(ttl=900)
def calculate_master_score(ticker):
    """
    PSİKOLOJİK OLARAK DOĞRU & GERÇEKÇİ MASTER SKOR:
    Puan kazandıran (1 bile olsa) her şey "Artılar" (Pros) listesine gider (Uyarı emojisiyle).
    Sadece 0 puan alıp sınıfta kalanlar "Eksiler" (Cons) listesine gider.
    """
    # 1. VERİLERİ TOPLA
    mini_data = calculate_minervini_sepa(ticker)
    fund_data = get_fundamental_score(ticker)
    sent_data = calculate_sentiment_score(ticker)
    ict_data = calculate_ict_deep_analysis(ticker)
    tech = get_tech_card_data(ticker)
    
    # Radar Puanlarını Al
    r1_score = 0.0; r2_score = 0.0
    scan_df = st.session_state.get('scan_data')
    if scan_df is not None and not scan_df.empty and 'Sembol' in scan_df.columns:
        row = scan_df[scan_df['Sembol'] == ticker]
        if not row.empty: r1_score = float(row.iloc[0]['Skor'])
    
    radar2_df = st.session_state.get('radar2_data')
    if radar2_df is not None and not radar2_df.empty and 'Sembol' in radar2_df.columns:
        row = radar2_df[radar2_df['Sembol'] == ticker]
        if not row.empty: r2_score = float(row.iloc[0]['Skor'])

    is_index = ticker.startswith("^") or "XU" in ticker or "-USD" in ticker

    # AĞIRLIKLAR
    w_trend = 0.40 if is_index else 0.30
    w_fund = 0.0 if is_index else 0.30
    w_mom = 0.30 if is_index else 0.20
    w_ict = 0.15 if is_index else 0.10
    w_r2 = 0.15 if is_index else 0.10

    pros = []; cons = []

    def format_pt(val):
        return f"+{int(val)}" if val > 0 and val.is_integer() else (f"+{val:.1f}" if val > 0 else f"{val:.1f}")

    # ---------------------------------------------------
    # A. TREND - KADEMELİ CEZA SİSTEMİ
    # ---------------------------------------------------
    s_trend = 0
    if tech:
        close = tech.get('close_last', 0)
        sma200 = tech.get('sma200', 0)
        sma50 = tech.get('sma50', 0)
        
        # 1. Ana Trend
        if sma200 > 0:
            if close > sma200:
                uzaklik = ((close - sma200) / sma200) * 100
                
                if uzaklik <= 15:
                    s_trend += 40
                    pros.append(f"✅ Ana Trend İdeal: SMA200'e güvenli mesafede ({format_pt(40 * w_trend)} Puan)")
                elif uzaklik <= 30:
                    s_trend += 30
                    # Puan veriyor ama uyarıyor (Kırmızıya atmıyoruz)
                    pros.append(f"⚠️ Trend Yukarıda: SMA200'den %{int(uzaklik)} uzaklaştı ({format_pt(30 * w_trend)} Puan)")
                elif uzaklik <= 50:
                    s_trend += 20
                    pros.append(f"⚠️ Trend Çok Primli: Ortalamadan %{int(uzaklik)} koptu ({format_pt(20 * w_trend)} Puan)")
                else:
                    s_trend += 10
                    pros.append(f"🚨 Köpük Riski: Fiyat SMA200'e göre %{int(uzaklik)} şişkin ({format_pt(10 * w_trend)} Puan)")
            else:
                # 0 Puan aldığı için kesinlikle kırmızı kutuya (cons) gider
                cons.append(f"Ana Trend Negatif: Fiyat SMA200 altında (0 Puan)")

        # 2. Orta/Kısa Vade 
        if sma50 > 0:
            if close > sma50: 
                s_trend += 40
                pros.append(f"✅ Kısa Vadeli İvme: Fiyat SMA50 üzerinde ({format_pt(40 * w_trend)} Puan)")
            else:
                cons.append(f"Kısa Vade Zayıf: SMA50 altında baskı var (0 Puan)")
        
        # 3. Minervini Onayı
        if mini_data and mini_data.get('score', 0) > 50: 
            s_trend += 20
            pros.append(f"✅ Trend Şablonu: Minervini Kriterleri Sağlanıyor ({format_pt(20 * w_trend)} Puan)")
    else:
        cons.append(f"Teknik Veri Hatası (0 Puan)")
        
    s_trend = min(s_trend, 100)

    # ---------------------------------------------------
    # B. MOMENTUM 
    # ---------------------------------------------------
    sent_raw = sent_data.get('total', 50) if sent_data else 50
    rsi_val = sent_data.get('raw_rsi', 50) if sent_data else 50
    
    s_mom = 0
    if sent_raw >= 60: 
        s_mom += 60
        pros.append(f"✅ Net Para Girişi: Kurumsal duyarlılık yüksek ({format_pt(60 * w_mom)} Puan)")
    elif sent_raw <= 40: 
        cons.append(f"Para Çıkışı: Kurumsal duyarlılık zayıf (0 Puan)")
    else:
        s_mom += 20 
        pros.append(f"⚖️ Momentum Nötr: Net bir yön yok ({format_pt(20 * w_mom)} Puan)")
        
    if rsi_val > 60: 
        s_mom += 40
        pros.append(f"✅ RSI Güçlü: Alım iştahı yüksek ({format_pt(40 * w_mom)} Puan)")
    elif rsi_val > 45:
        s_mom += 15
        pros.append(f"⚖️ RSI Toparlanıyor: Aşırı satımdan çıkış ({format_pt(15 * w_mom)} Puan)")
    else: 
        cons.append(f"RSI Zayıf: Satış baskısı devam ediyor (0 Puan)")

    # ---------------------------------------------------
    # C. TEMEL ANALİZ
    # ---------------------------------------------------
    s_fund = fund_data.get('score', 50) if fund_data else 50
    fund_pt = s_fund * w_fund
    
    if not is_index:
        if s_fund >= 65: 
            pros.append(f"✅ Temel: Büyüme ve kârlılık olumlu ({format_pt(fund_pt)} Puan)")
        elif s_fund <= 40: 
            # Puan katkısı var ama zayıf, bu yüzden pros listesinde uyarı ile gösteriyoruz
            pros.append(f"⚠️ Temel: Temel veriler zayıf ({format_pt(fund_pt)} Puan)")
        else:
            pros.append(f"⚖️ Temel: Sektörel olarak nötr ({format_pt(fund_pt)} Puan)")

    # ---------------------------------------------------
    # D. SMART MONEY / ICT
    # ---------------------------------------------------
    s_ict = 0
    if ict_data:
        if "bullish" in ict_data.get('bias', ''): 
            s_ict += 40
            pros.append(f"✅ Smart Money: Yön Yukarı (Bullish) ({format_pt(40 * w_ict)} Puan)")
        elif "bearish" in ict_data.get('bias', ''):
            cons.append(f"Smart Money: Yön Aşağı (Bearish) (0 Puan)")
            
        if "Güçlü" in ict_data.get('displacement', ''): 
            s_ict += 40
            pros.append(f"✅ ICT Hacim: Güçlü Kurumsal Mum ({format_pt(40 * w_ict)} Puan)")
            
        if "Ucuz" in ict_data.get('zone', ''): 
            s_ict += 20
            pros.append(f"✅ ICT Konum: Fiyat Ucuzluk Bölgesinde ({format_pt(20 * w_ict)} Puan)")
            
        if s_ict == 0:
            cons.append(f"ICT Setup Yok: Kurumsal iz bulunamadı (0 Puan)")
    else:
        cons.append(f"ICT Verisi Yok (0 Puan)")
        
    s_ict = min(s_ict, 100)

    # ---------------------------------------------------
    # E. RADAR 2
    # ---------------------------------------------------
    s_r2_norm = (r2_score / 7) * 100
    r2_pt = s_r2_norm * w_r2
    
    if r2_score >= 4: 
        pros.append(f"✅ Formasyon: Radar-2 Setup Onaylandı ({format_pt(r2_pt)} Puan)")
    elif r2_score > 0:
        pros.append(f"⚠️ Zayıf Formasyon: Radar-2 Sinyali Eksik ({format_pt(r2_pt)} Puan)")
    else: 
        cons.append(f"Formasyon Yok: Radar-2 temiz (0 Puan)")

    # ---------------------------------------------------
    # FİNAL HESAPLAMA VE KORUMA SİSTEMİ
    # ---------------------------------------------------
    final = (s_trend * w_trend) + (s_fund * w_fund) + (s_mom * w_mom) + (s_ict * w_ict) + (s_r2_norm * w_r2)

    # Mavi Çip Koruması
    if not is_index and s_fund >= 80 and final < 30:
        fark = 30 - final
        final = 30
        pros.append(f"🛡️ Şirket Değeri Koruması: Aşırı satım (Alt Limit 30) ({format_pt(fark)} Puan)")

    return int(final), pros, cons

# ==============================================================================
# 🧱 YENİ: ARZ-TALEP (SUPPLY & DEMAND) VE ERC MOTORU
# ==============================================================================
def detect_supply_demand_zones(df):
    """
    RBR, DBD, RBD ve DBR formasyonlarını ERC (Momentum Mumu) onayıyla tarar.
    En taze (test edilmemiş veya yeni) bölgeyi döndürür.
    """
    try:
        if df is None or df.empty or len(df) < 50: return None
        
        close = df['Close']
        open_ = df['Open']
        high = df['High']
        low = df['Low']
        
        # 1. Mum Geometrisi ve ERC (Extended Range Candle) Tespiti
        body = abs(close - open_)
        rng = high - low
        
        # Son 20 mumun ortalama gövde boyutu (Kıyaslama için)
        avg_body = body.rolling(20).mean()
        
        zones = []
        
        # Son 100 muma bakıyoruz (Taze bölgeler için yeterli bir derinlik)
        start_idx = max(2, len(df) - 100)
        
        for i in range(start_idx, len(df)):
            leg_in_idx = i - 2
            base_idx = i - 1
            leg_out_idx = i
            
            # --- ERC (Geniş Gövdeli Momentum Mumu) Şartları ---
            # Giriş ve Çıkış mumlarının gövdesi hem ortalamadan büyük olmalı hem de kendi fitillerinden (mumun %50'sinden) büyük olmalı.
            leg_in_erc = body.iloc[leg_in_idx] > avg_body.iloc[leg_in_idx] and body.iloc[leg_in_idx] > (rng.iloc[leg_in_idx] * 0.5)
            leg_out_erc = body.iloc[leg_out_idx] > avg_body.iloc[leg_out_idx] and body.iloc[leg_out_idx] > (rng.iloc[leg_out_idx] * 0.5)
            
            # --- Base (Denge) Mumu Şartları ---
            # Gövdesi küçük olmalı (kendi toplam boyunun %50'sinden küçük)
            is_base = body.iloc[base_idx] < (rng.iloc[base_idx] * 0.5)
            
            if leg_in_erc and leg_out_erc and is_base:
                # Yönleri Belirle
                in_green = close.iloc[leg_in_idx] > open_.iloc[leg_in_idx]
                in_red = close.iloc[leg_in_idx] < open_.iloc[leg_in_idx]
                out_green = close.iloc[leg_out_idx] > open_.iloc[leg_out_idx]
                out_red = close.iloc[leg_out_idx] < open_.iloc[leg_out_idx]
                
                z_type = ""
                z_top = 0.0
                z_bot = 0.0
                
                # Formasyon Eşleştirmeleri
                if in_green and out_green:
                    z_type = "RBR (Rally-Base-Rally) / Talep"
                    z_top = max(open_.iloc[base_idx], close.iloc[base_idx]) # Base gövde üstü
                    z_bot = low.iloc[base_idx] # Base fitil altı
                elif in_red and out_red:
                    z_type = "DBD (Drop-Base-Drop) / Arz"
                    z_bot = min(open_.iloc[base_idx], close.iloc[base_idx]) # Base gövde altı
                    z_top = high.iloc[base_idx] # Base fitil üstü
                elif in_green and out_red:
                    z_type = "RBD (Rally-Base-Drop) / Arz"
                    z_bot = min(open_.iloc[base_idx], close.iloc[base_idx])
                    z_top = high.iloc[base_idx]
                elif in_red and out_green:
                    z_type = "DBR (Drop-Base-Rally) / Talep"
                    z_top = max(open_.iloc[base_idx], close.iloc[base_idx])
                    z_bot = low.iloc[base_idx]
                    
                if z_type != "":
                    # Fiyat aralığı çok darsa (Hatalı veri engellemesi) alma
                    if z_top > z_bot:
                        zones.append({
                            'Type': z_type,
                            'Top': float(z_top),
                            'Bottom': float(z_bot),
                            'Age': len(df) - i # Kaç mum önce oluştu?
                        })
        
        if not zones: return None
        
        # En taze (en son oluşan) bölgeyi al
        latest_zone = zones[-1]
        curr_price = float(close.iloc[-1])
        
        # Bölge şu an ihlal edildi mi? (Test Durumu)
        status = "Taze / Beklemede"
        if "Talep" in latest_zone['Type'] and curr_price < latest_zone['Bottom']:
            status = "İhlal Edildi (Kırıldı)"
        elif "Arz" in latest_zone['Type'] and curr_price > latest_zone['Top']:
            status = "İhlal Edildi (Kırıldı)"
        elif latest_zone['Bottom'] <= curr_price <= latest_zone['Top']:
            status = "Bölge İçinde (Test Ediliyor)"
            
        latest_zone['Status'] = status
        return latest_zone
        
    except Exception:
        return None
    
# ==============================================================================
# 🦅 YENİ: ICT SNIPER TARAMA MOTORU (4 ŞARTLI DEDEKTÖR)
# ==============================================================================
def process_single_ict_setup(symbol, df):
    """
    ICT 2022 Mentorship Model - MAXIMUM WIN RATE (KESKİN NİŞANCI AJANI)
    Özellikler:
    1. FVG %50 (Consequent Encroachment) Girişi (Dar Stop, Yüksek Win Rate)
    2. 7-Mumluk Güçlendirilmiş Fraktal Likidite (Daha Zor Kırılan Tepeler)
    3. Hacim Onaylı Displacement (> %130)
    4. RRR >= 2.5 Asimetrik Giyotini
    """
    try:
        if df.empty or len(df) < 50: return None
        
        close = df['Close']; high = df['High']; low = df['Low']; open_ = df['Open']
        current_price = float(close.iloc[-1])
        
        # --- 1. HACİM VE GÖVDE (Displacement Teyidi) ---
        has_vol = 'Volume' in df.columns and not df['Volume'].isnull().all()
        volume = df['Volume'] if has_vol else pd.Series([1]*len(df), index=df.index)
        avg_vol = volume.rolling(20).mean()
        
        body_sizes = abs(close - open_)
        avg_body = body_sizes.rolling(20).mean()
        
        # --- 2. GÜÇLENDİRİLMİŞ FRAKTAL LİKİDİTE (Win Rate Hack 1) ---
        # 5 mumluk değil, sağında ve solunda 3'er mum olan 7-mumluk "Majör" swingleri arıyoruz.
        sw_highs = []; sw_lows = []
        for i in range(len(df)-40, len(df)-3): 
            if i < 3: continue
            if high.iloc[i] == max(high.iloc[i-3:i+4]):
                sw_highs.append((df.index[i], high.iloc[i], i))
            if low.iloc[i] == min(low.iloc[i-3:i+4]):
                sw_lows.append((df.index[i], low.iloc[i], i))
        
        if not sw_highs or not sw_lows: return None
        
        last_sh_val = sw_highs[-1][1]
        last_sl_val = sw_lows[-1][1]
        
        # --- 3. HTF TREND FİLTRESİ ---
        sma_50 = close.rolling(50).mean().iloc[-1]
        htf_bullish = current_price > sma_50
        htf_bearish = current_price < sma_50

        # =========================================================
        # SENARYO A: LONG (BOĞA) SETUP ARANIYOR
        # =========================================================
        if htf_bullish:
            # Likidite Avı
            recent_low = low.iloc[-10:].min()
            sweep_lows = [sl for sl in sw_lows[:-1] if recent_low < sl[1]] 
            
            if sweep_lows:
                # MSS (Market Structure Shift)
                if close.iloc[-1] > last_sh_val or close.iloc[-2] > last_sh_val:
                    
                    # Hacimli Yeşil Mum (Displacement)
                    green_bodies = body_sizes.where(close > open_, 0)
                    max_green_recent = green_bodies.iloc[-5:].max()
                    idx_max_green = green_bodies.iloc[-5:].idxmax()
                    
                    vol_check = volume[idx_max_green] > (avg_vol[idx_max_green] * 1.3) if has_vol else True
                    
                    if max_green_recent > (avg_body.iloc[-1] * 1.5) and vol_check:
                        
                        # FVG Tespiti
                        for i in range(len(df)-1, len(df)-5, -1):
                            if low.iloc[i] > high.iloc[i-2]: # Bullish FVG
                                fvg_top = low.iloc[i]
                                fvg_bot = high.iloc[i-2]
                                
                                # --- 4. WIN RATE HACK 2: Consequent Encroachment (CE) ---
                                # FVG'nin tam %50 orta noktasını hesapla
                                fvg_ce = fvg_bot + ((fvg_top - fvg_bot) * 0.5)
                                
                                # Fiyat FVG'nin tepesinden değil, %50 indirimli ortasından (CE) tepki almalı
                                if current_price <= (fvg_ce * 1.01) and current_price >= (fvg_bot * 0.99):
                                    
                                    stop_loss = recent_low * 0.99 # Sweep ucunun %1 altı
                                    entry_price = current_price
                                    risk = entry_price - stop_loss
                                    if risk <= 0: continue
                                    
                                    # Hedef
                                    targets = [sh[1] for sh in sw_highs if sh[1] > entry_price * 1.02]
                                    if not targets: continue
                                    target_price = min(targets) 
                                    
                                    reward = target_price - entry_price
                                    rrr = reward / risk
                                    
                                    # VETO Giyotini (Giriş CE'de olduğu için RRR rahatça 2.5'i geçer)
                                    if rrr >= 2.5:
                                        return {
                                            "Sembol": symbol, "Fiyat": current_price,
                                            "Yön": "LONG", "İkon": "🎯", "Renk": "#16a34a",
                                            "Durum": f"Giriş: CE | RRR: {rrr:.1f} | Hedef: ${target_price:.2f}",
                                            "Stop_Loss": f"{stop_loss:.2f}",
                                            "Skor": 99
                                        }

        # =========================================================
        # SENARYO B: SHORT (AYI) SETUP ARANIYOR
        # =========================================================
        elif htf_bearish:
            # Likidite Avı
            recent_high = high.iloc[-10:].max()
            sweep_highs = [sh for sh in sw_highs[:-1] if recent_high > sh[1]]
            
            if sweep_highs:
                # MSS (Market Structure Shift)
                if close.iloc[-1] < last_sl_val or close.iloc[-2] < last_sl_val:
                    
                    # Hacimli Kırmızı Mum (Displacement)
                    red_bodies = body_sizes.where(close < open_, 0)
                    max_red_recent = red_bodies.iloc[-5:].max()
                    idx_max_red = red_bodies.iloc[-5:].idxmax()
                    
                    vol_check = volume[idx_max_red] > (avg_vol[idx_max_red] * 1.3) if has_vol else True
                    
                    if max_red_recent > (avg_body.iloc[-1] * 1.5) and vol_check:
                        
                        # FVG Tespiti
                        for i in range(len(df)-1, len(df)-5, -1):
                            if high.iloc[i] < low.iloc[i-2]: # Bearish FVG
                                fvg_top = low.iloc[i-2]
                                fvg_bot = high.iloc[i]
                                
                                # --- 4. WIN RATE HACK 2: Consequent Encroachment (CE) ---
                                fvg_ce = fvg_bot + ((fvg_top - fvg_bot) * 0.5)
                                
                                # Fiyat CE bölgesinden tepki almalı
                                if current_price >= (fvg_ce * 0.99) and current_price <= (fvg_top * 1.01):
                                    
                                    stop_loss = recent_high * 1.01 # Sweep ucunun %1 üstü
                                    entry_price = current_price
                                    risk = stop_loss - entry_price
                                    if risk <= 0: continue
                                    
                                    # Hedef
                                    targets = [sl[1] for sl in sw_lows if sl[1] < entry_price * 0.98]
                                    if not targets: continue
                                    target_price = max(targets)
                                    
                                    reward = entry_price - target_price
                                    rrr = reward / risk
                                    
                                    # VETO Giyotini
                                    if rrr >= 2.5:
                                        return {
                                            "Sembol": symbol, "Fiyat": current_price,
                                            "Yön": "SHORT", "İkon": "🎯", "Renk": "#dc2626",
                                            "Durum": f"Giriş: CE | RRR: {rrr:.1f} | Hedef: ${target_price:.2f}",
                                            "Stop_Loss": f"{stop_loss:.2f}",
                                            "Skor": 99
                                        }

        return None

    except Exception:
        return None


@st.cache_data(ttl=900)
def scan_ict_batch(asset_list):
    """
    ICT Toplu Tarama Ajanı (Paralel Çalışır)
    """
    # 1. Veri Çek (Cache'den)
    data = get_batch_data_cached(asset_list, period="1y")
    if data.empty: return pd.DataFrame()
    
    results = []
    stock_dfs = []
    
    # Veriyi hisselere ayır
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]:
                    stock_dfs.append((symbol, data[symbol]))
            else:
                if len(asset_list) == 1: stock_dfs.append((symbol, data))
        except: continue

    # 2. Paralel İşleme (Dedektörü Çalıştır)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_single_ict_setup, sym, df) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: results.append(res)
            
    # 3. Sonuç Döndür
    if results:
        return pd.DataFrame(results)
    
    return pd.DataFrame()    
# ==============================================================================
# MINERVINI SEPA MODÜLÜ (HEM TEKLİ ANALİZ HEM TARAMA) - GÜNCELLENMİŞ VERSİYON
# ==============================================================================

@st.cache_data(ttl=600)
def calculate_minervini_sepa(ticker, benchmark_ticker="^GSPC", provided_df=None):
    """
    GÖRSEL: Eski (Sade)
    MANTIK: Sniper (Çok Sert)
    """
    try:
        # 1. VERİ YÖNETİMİ (Batch taramadan geliyorsa provided_df kullan, yoksa indir)
        if provided_df is not None:
            df = provided_df
        else:
            df = get_safe_historical_data(ticker, period="2y")
            
        if df is None or len(df) < 260: return None
        
        # MultiIndex Temizliği
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Endeks verisi (RS için) - Eğer cache'de yoksa indir
        bench_df = get_safe_historical_data(benchmark_ticker, period="2y")
        
        close = df['Close']; volume = df['Volume']
        curr_price = float(close.iloc[-1])
        
        # ---------------------------------------------------------
        # KRİTER 1: TREND ŞABLONU (ACIMASIZ FİLTRE)
        # ---------------------------------------------------------
        sma50 = float(close.rolling(50).mean().iloc[-1])
        sma150 = float(close.rolling(150).mean().iloc[-1])
        sma200 = float(close.rolling(200).mean().iloc[-1])
        
        # Eğim Kontrolü: SMA200, 1 ay önceki değerinden yüksek olmalı
        sma200_prev = float(close.rolling(200).mean().iloc[-22])
        sma200_up = sma200 >= (sma200_prev * 0.99)
        
        year_high = float(close.rolling(250).max().iloc[-1])
        year_low = float(close.rolling(250).min().iloc[-1])
        
        # Zirveye Yakınlık: Minervini %25 der ama biz sertleşip %15 (0.85) yapıyoruz
        near_high = curr_price >= (year_high * 0.9)
        above_low = curr_price >= (year_low * 1.30)
        
        # HEPSİ DOĞRU OLMALI
        trend_ok = (curr_price > sma150 > sma200) and \
                   (sma50 > sma150) and \
                   (curr_price > sma50) and \
                   sma200_up and \
                   near_high and \
                   above_low
                   
        if not trend_ok: return None # Trend yoksa elendi.

        # ---------------------------------------------------------
        # KRİTER 2: RS KONTROLÜ (ACIMASIZ)
        # ---------------------------------------------------------
        rs_val = 0; rs_rating = "ZAYIF"
        if bench_df is not None:
            common = close.index.intersection(bench_df.index)
            if len(common) > 50:
                s_p = close.loc[common]; b_p = bench_df['Close'].loc[common]
                ratio = s_p / b_p
                rs_val = float(((ratio / ratio.rolling(50).mean()) - 1).iloc[-1] * 10)
        
        # Endeksten Zayıfsa ELE (0 altı kabul edilmez)
        if rs_val <= 1: return None
        
        rs_rating = f"GÜÇLÜ (RS: {rs_val:.1f})"

        # ---------------------------------------------------------
        # KRİTER 3: PUANLAMA (VCP + ARZ + PIVOT)
        # ---------------------------------------------------------
        raw_score = 60 # Başlangıç puanı (Trend ve RS geçtiği için)
        
        # VCP (Sertleşmiş Formül: %65 daralma)
        std_10 = close.pct_change().rolling(10).std().iloc[-1]
        std_50 = close.pct_change().rolling(50).std().iloc[-1]
        is_vcp = std_10 < (std_50 * 0.65)
        if is_vcp: raw_score += 20
        
        # Arz Kuruması (Sertleşmiş: %75 altı)
        avg_vol = volume.rolling(20).mean().iloc[-1]
        last_5 = df.tail(5)
        down_days = last_5[last_5['Close'] < last_5['Open']]
        is_dry = True if down_days.empty else (down_days['Volume'].mean() < avg_vol * 0.75)
        if is_dry: raw_score += 10
        
        # Pivot Bölgesi (Zirveye %5 kala)
        dist_high = curr_price / year_high
        in_pivot = 0.95 <= dist_high <= 1.02
        if in_pivot: raw_score += 10

        # ---------------------------------------------------------
        # ÇIKTI (ESKİ TASARIMIN ANLAYACAĞI FORMAT)
        # ---------------------------------------------------------
        # Buradaki key isimleri (Durum, Detay vs.) senin eski kodunla aynı.
        # Böylece UI bozulmayacak.
        
        status = "🔥 GÜÇLÜ TREND"
        if is_vcp and in_pivot: status = "💎💎 SÜPER BOĞA (VCP)"
        elif in_pivot: status = "🔥 KIRILIM EŞİĞİNDE"
        
        # Renk (Skor bazlı)
        color = "#16a34a" if raw_score >= 80 else "#ea580c"

        return {
            "Sembol": ticker,
            "Fiyat": f"{curr_price:.2f}",
            "Durum": status,
            "Detay": f"{rs_rating} | VCP: {'Sıkışmada düşük oynaklık' if is_vcp else '-'} | Arz: {'Kurudu(satıcılar yoruldu)' if is_dry else '-'}",
            "Raw_Score": raw_score,
            "score": raw_score, # UI bazen bunu arıyor
            "trend_ok": True,
            "is_vcp": is_vcp,
            "is_dry": is_dry,
            "rs_val": rs_val,
            "rs_rating": rs_rating,
            "reasons": ["Trend: Mükemmel", f"VCP: {is_vcp}", f"RS: {rs_val:.1f}"],
            "color": color,
            "sma200": sma200,
            "year_high": year_high
        }
    except Exception: return None

# ==============================================================================
# LORENTZIAN CLASSIFICATION (10 YILLIK GÜNLÜK VERİ - TRADINGVIEW FORMÜLLERİ)
# ==============================================================================
@st.cache_data(ttl=3600)
def calculate_lorentzian_classification(ticker, k_neighbors=8):
    try:
        # 1. VERİ ÇEKME (10 YILLIK GÜNLÜK - Derin Öğrenme İçin Şart)
        clean_ticker = ticker.replace(".IS", "")
        if ".IS" in ticker: clean_ticker = ticker 
        
        try:
            # Artık doğrudan yeni akıllı yerel önbellek fonksiyonumuzu kullanıyoruz
            # Diskten şimşek hızında çekecek ve sadece son günleri yfinance'e soracak.
            df = get_safe_historical_data(clean_ticker, period="10y", interval="1d")
        except: return None
        if df is None or len(df) < 200: return None 

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Hesaplama Serileri
        src = df['Close']
        high = df['High']
        low = df['Low']
        hlc3 = (high + low + src) / 3

        # ---------------------------------------------------------
        # 3. FEATURE ENGINEERING (TRADINGVIEW SCRIPT BİREBİR)
        # ---------------------------------------------------------
        
        # --- Feature 1: RSI (14) ---
        delta = src.diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        avg_up = up.ewm(alpha=1/14, adjust=False).mean()
        avg_down = down.ewm(alpha=1/14, adjust=False).mean()
        rs = avg_up / avg_down
        f1_rsi14 = 100 - (100 / (1 + rs))

        # --- Feature 2: WaveTrend (10, 11) ---
        esa = hlc3.ewm(span=10, adjust=False).mean()
        d = abs(hlc3 - esa).ewm(span=10, adjust=False).mean()
        ci = (hlc3 - esa) / (0.015 * d)
        f2_wt = ci.ewm(span=11, adjust=False).mean()

        # --- Feature 3: CCI (20) ---
        tp = hlc3
        sma20 = tp.rolling(20).mean()
        mad = (tp - sma20).abs().rolling(20).mean()
        f3_cci = (tp - sma20) / (0.015 * mad)

        # --- Feature 4: ADX (20) ---
        # Script ADX periyodunu 20 kullanıyor.
        tr1 = high - low
        tr2 = abs(high - src.shift(1))
        tr3 = abs(low - src.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr20 = tr.ewm(alpha=1/20, adjust=False).mean()

        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        plus_di = 100 * (pd.Series(plus_dm, index=df.index).ewm(alpha=1/20, adjust=False).mean() / atr20)
        minus_di = 100 * (pd.Series(minus_dm, index=df.index).ewm(alpha=1/20, adjust=False).mean() / atr20)
        dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
        f4_adx = dx.ewm(alpha=1/20, adjust=False).mean()

        # --- Feature 5: RSI (9) ---
        avg_up9 = up.ewm(alpha=1/9, adjust=False).mean()
        avg_down9 = down.ewm(alpha=1/9, adjust=False).mean()
        rs9 = avg_up9 / avg_down9
        f5_rsi9 = 100 - (100 / (1 + rs9))

        # 4. NORMALİZASYON (Min-Max Scaling 0-1)
        features_df = pd.DataFrame({
            'f1': f1_rsi14, 'f2': f2_wt, 'f3': f3_cci, 'f4': f4_adx, 'f5': f5_rsi9
        }).dropna()

        features_norm = (features_df - features_df.min()) / (features_df.max() - features_df.min())
        features_norm = features_norm.fillna(0.5)

        # ---------------------------------------------------------
        # 5. HEDEF (TARGET) - OPTİMİZASYON
        # ---------------------------------------------------------
        # TradingView 4 bar sonrasına bakar. Günlük grafikte bu 4 gün eder.
        # Biz burada "Yarın Yükselecek mi?" sorusuna (1 Bar) odaklanıyoruz.
        # Bu, günlük trade için daha değerlidir.
        future_close = src.shift(-1) 
        target = (future_close > src).astype(int) 

        common_idx = features_norm.index.intersection(target.index)
        features_final = features_norm.loc[common_idx]
        target_final = target.loc[common_idx]

        if len(features_final) < 50: return None

        # Eğitim: Son mum HARİÇ tüm geçmiş
        current_features = features_final.iloc[-1].values
        history_features = features_final.iloc[:-1].values
        history_targets = target_final.iloc[:-1].values

        # ---------------------------------------------------------
        # 6. LORENTZIAN MESAFE (Script ile Birebir)
        # ---------------------------------------------------------
        abs_diff = np.abs(history_features - current_features)
        distances = np.sum(np.log(1 + abs_diff), axis=1)

        nearest_indices = np.argsort(distances)[:k_neighbors]

        bullish_votes = 0
        bearish_votes = 0

        for idx in nearest_indices:
            if history_targets[idx] == 1: bullish_votes += 1
            else: bearish_votes += 1

        if bullish_votes >= bearish_votes:
            signal = "YÜKSELİŞ"
            prob = (bullish_votes / k_neighbors) * 100
            color = "#16a34a"
        else:
            signal = "DÜŞÜŞ"
            prob = (bearish_votes / k_neighbors) * 100
            color = "#dc2626"

        return {
            "signal": signal,
            "prob": prob,
            "votes": max(bullish_votes, bearish_votes),
            "total": k_neighbors,
            "color": color,
            "bars": len(df) # Veri derinliğini görmek için
        }

    except Exception: return None

def render_lorentzian_panel(ticker, just_text=False):
    data = calculate_lorentzian_classification(ticker)
    
    # 1. KİLİT: Veri hiç yoksa çık (Bunu koymazsan kod çöker)
    if not data: return ""
    # 2. KİLİT: Veri var ama güven 7/8'den düşükse çık (Senin istediğin filtre)
    if data['votes'] < 7: return ""

    display_prob = int(data['prob'])
    # İkon seçimi
    ml_icon = "🚀" if data['signal'] == "YÜKSELİŞ" and display_prob >= 75 else "🐻" if data['signal'] == "DÜŞÜŞ" and display_prob >= 75 else "🧠"
    
    bar_width = display_prob
    signal_text = f"{data['signal']} BEKLENTİSİ"

    # Başlık: GÜNLÜK
    # Alt Bilgi: Vade: 1 Gün
    # Not: ticker temizliğini burada da yapıyoruz
    clean_name = ticker.replace('.IS', '').replace('-USD', '').replace('=F', '')
    
    # --- HTML TASARIMI (GÜNCELLENDİ) ---
    html_content = f"""
    <div class="info-card" style="border-top: 3px solid {data['color']}; margin-bottom: 15px;">
        <div class="info-header" style="color:{data['color']}; display:flex; justify-content:space-between; align-items:center;">
            <span>{ml_icon} Lorentzian (GÜNLÜK): {clean_name}</span>
        </div>
        
        <div style="text-align:center; padding:8px 0;">
            <div style="display:flex; justify-content:center; align-items:center; gap:10px; margin-bottom:4px;">
                <span style="font-size:0.9rem; font-weight:800; color:{data['color']}; letter-spacing:0.5px;">
                    {signal_text}
                </span>
                <span style="font-size:0.7rem; background:{data['color']}15; padding:2px 8px; border-radius:10px; font-weight:700; color:{data['color']};">
                    %{display_prob} Güven
                </span>
            </div>

            <div style="font-size:0.65rem; color:#64748B;">
                Son 10 Yılın verisini inceledi.<br>
                Benzer <b>8</b> senaryonun <b>{data['votes']}</b> tanesinde yön aynıydı.
            </div>
        </div>

        <div style="margin-top:5px; margin-bottom:8px; padding:0 4px;">
            <div style="display:flex; justify-content:space-between; font-size:0.65rem; color:#64748B; margin-bottom:2px;">
                <span>Oylama: <b>{data['votes']}/{data['total']}</b></span>
                <span>Vade: <b>1 Gün (Yarın)</b></span>
            </div>
            <div style="width:100%; height:6px; background:#e2e8f0; border-radius:3px; overflow:hidden;">
                <div style="width:{bar_width}%; height:100%; background:{data['color']};"></div>
            </div>
        </div>
    </div>
    """
    if not just_text:  # <-- EĞER SADECE METİN İSTENMİYORSA ÇİZ
        st.markdown(html_content.replace("\n", " "), unsafe_allow_html=True)

# 3. VE EN ÖNEMLİ DEĞİŞİKLİK: AI İÇİN METİN OLUŞTUR VE DÖNDÜR
    ai_data_text = f"""
LORENTZIAN MODELİ'NİN GEÇMİŞ 2000 GÜNE BAKARAK YAPTIĞI YARIN (1 GÜNLÜK) TAHMİNİ: 
- Beklenti: {data['signal']}
- Güven Oranı: %{display_prob}
- Oylama (Benzer Senaryo): {data['votes']}/{data['total']}
"""
    return ai_data_text

@st.cache_data(ttl=900)
def scan_minervini_batch(asset_list):
    # 1. Veri İndirme (Hızlı Batch)
    data = get_batch_data_cached(asset_list, period="2y")
    if data.empty: return pd.DataFrame()
    
    # 2. Endeks Belirleme
    cat = st.session_state.get('category', 'S&P 500')
    bench = "XU100.IS" if "BIST" in cat else "^GSPC"

    results = []
    stock_dfs = []
    
    # Veriyi hazırlama (Hisselere bölme)
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]:
                    stock_dfs.append((symbol, data[symbol]))
            elif len(asset_list) == 1:
                stock_dfs.append((symbol, data))
        except: continue

    # 3. Paralel Tarama (Yukarıdaki sertleştirilmiş fonksiyonu çağırır)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # provided_df argümanını kullanarak internetten tekrar indirmeyi engelliyoruz
        futures = [executor.submit(calculate_minervini_sepa, sym, bench, df) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: results.append(res)
            
    # 4. Sıralama ve Kesme
    if results:
        df = pd.DataFrame(results)
        # En yüksek Puanlı ve en yüksek RS'li olanları üste al
        # Sadece ilk 30'u göster ki kullanıcı boğulmasın.
        return df.sort_values(by=["Raw_Score", "rs_val"], ascending=[False, False]).head(30)
    
    return pd.DataFrame()

@st.cache_data(ttl=900)
def scan_rs_momentum_leaders(asset_list):
    """
    GÜNCELLENMİŞ: RS MOMENTUM + BETA AYARLI ALPHA
    Hız Tuzağına Düşmeden, İşlemci Gücüyle Beta ve Sigma Hesabı Yapar.
    Profesyonel Fon Yöneticisi Mantığı: Beta Adjusted Alpha + Dynamic Sigma Safety Lock.
    """
    # 1. Verileri Çek (3 ay yeterli, Beta için ideal)
    data = get_batch_data_cached(asset_list, period="3mo")
    if data.empty: return pd.DataFrame()

    # 2. Endeks Verisi
    cat = st.session_state.get('category', 'S&P 500')
    bench_ticker = "XU100.IS" if "BIST" in cat else "^GSPC"
    df_bench = get_safe_historical_data(bench_ticker, period="3mo")
    
    if df_bench is None or df_bench.empty: return pd.DataFrame()
    
    # Endeks Performansları ve Getirileri (Beta hesabı için kritik)
    b_close = df_bench['Close']
    bench_returns = b_close.pct_change().dropna() 
    
    # Basit Kıyaslama (Eski yöntem - Referans ve ham hesap için)
    bench_5d = ((b_close.iloc[-1] - b_close.iloc[-6]) / b_close.iloc[-6]) * 100
    bench_1d = ((b_close.iloc[-1] - b_close.iloc[-2]) / b_close.iloc[-2]) * 100

    results = []

    # 3. Hisseleri Tara
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol not in data.columns.levels[0]: continue
                df = data[symbol].dropna()
            else:
                df = data.dropna()

            # Beta ve Sigma hesabı için en az 60 bar veri lazım
            if len(df) < 60: continue 

            close = df['Close']; volume = df['Volume']
            stock_returns = close.pct_change().dropna()

            # --- A. YENİ NESİL BETA HESAPLAMASI (CPU Hızıyla) ---
            # Hissenin ve Endeksin zaman serilerini eşle (Alignment)
            aligned_stock = stock_returns.reindex(bench_returns.index).dropna()
            aligned_bench = bench_returns.reindex(aligned_stock.index).dropna()
            
            # Kovaryans / Varyans = Beta
            if len(aligned_bench) > 20: # Yeterli ortak gün varsa hesapla
                covariance = np.cov(aligned_stock, aligned_bench)[0][1]
                variance = np.var(aligned_bench)
                beta = covariance / variance if variance != 0 else 1.0
            else:
                beta = 1.0 # Veri yetmezse varsayılan
            
            # --- B. PERFORMANS HESAPLARI ---
            stock_now = float(close.iloc[-1])
            stock_old_5 = float(close.iloc[-6])
            
            # 5 Günlük Performans
            stock_perf_5d = ((stock_now - stock_old_5) / stock_old_5) * 100
            
            # Beta Ayarlı Alpha (Jensen's Alpha Mantığı)
            # Beklenen Getiri = Beta * Endeks Getirisi
            expected_return_5d = bench_5d * beta
            adjusted_alpha_5d = stock_perf_5d - expected_return_5d

            # --- C. DİNAMİK EMNİYET KİLİDİ (SIGMA) ---
            # Hissenin endekse göre "normal" sapmasını bul
            alpha_series = (stock_returns - bench_returns).dropna().tail(20)
            alpha_std = alpha_series.std() * 100 # Yüzde cinsinden standart sapma
            
            # Kilit Eşiği: Kendi oynaklığının 1.5 katı kadar negatif ayrışma
            safety_threshold = -(alpha_std * 1.5)
            
            # Bugünün durumu
            stock_perf_1d = ((stock_now - float(close.iloc[-2])) / float(close.iloc[-2])) * 100
            today_raw_alpha = stock_perf_1d - bench_1d

            # Hacim Kontrolü
            curr_vol = float(volume.iloc[-1])
            avg_vol = float(volume.iloc[-21:-1].mean())
            vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 0

            # --- FİLTRELEME (PROFESYONEL KRİTERLER) ---
            # 1. Beta Ayarlı Alpha > 1.25 (Gerçek Güç)
            # 2. Hacim > 0.9 (İlgi var)
            # 3. Bugün "Güvenli Eşik"ten daha fazla düşmemiş (Momentum Kırılmamış)
            if adjusted_alpha_5d >= 1.25 and vol_ratio > 0.9 and today_raw_alpha > safety_threshold:
                
                results.append({
                    "Sembol": symbol,
                    "Fiyat": stock_now,
                    "Beta": round(beta, 2), # Bilgi için ekranda görünebilir
                    "Alpha_5D": adjusted_alpha_5d,     # İsmi Alpha_5D olarak düzelttik
                    "Adj_Alpha_5D": adjusted_alpha_5d, # Sıralama kriteri
                    "Ham_Alpha_5D": stock_perf_5d - bench_5d, # Eski usül (referans)
                    "Eşik": round(safety_threshold, 2),
                    "Hacim_Kat": vol_ratio,
                    "Skor": adjusted_alpha_5d # Skor artık "Gerçek Alpha"
                })

        except Exception as e: continue

    # 4. Sıralama
    if results:
        # Skora göre azalan sırala
        return pd.DataFrame(results).sort_values(by="Skor", ascending=False)
    
    return pd.DataFrame()

@st.cache_data(ttl=600)
def calculate_sentiment_score(ticker):
    try:
        # Veri Çekme (2y: SMA200 garantisi için)
        df = get_safe_historical_data(ticker, period="2y")
        if df is None or len(df) < 200: return None
        
        close = df['Close']; high = df['High']; low = df['Low']; volume = df['Volume']
        
        # --- TANIMLAMALAR (Endeks/Hisse Ayrımı) ---
        bist_indices_roots = [
            "XU100", "XU030", "XU050", "XBANK", "XUSIN", "XTEKN", 
            "XBLSM", "XGMYO", "XTRZM", "XILET", "XKMYA", "XMANA", 
            "XSPOR", "XILTM", "XINSA", "XHOLD", "XTUMY"
        ]
        is_global_index = ticker.startswith("^")
        is_bist_index = any(root in ticker for root in bist_indices_roots)
        is_crypto = "-USD" in ticker
        is_index = is_global_index or is_bist_index or is_crypto
        
        # --- PUAN AĞIRLIKLARI ---
        if is_index:
            W_STR, W_TR, W_VOL = 25, 25, 25
            W_MOM, W_VOLA = 15, 10
            W_RS = 0
        else:
            W_STR, W_TR, W_VOL = 20, 20, 20
            W_MOM, W_VOLA = 15, 10
            W_RS = 15

        # =========================================================
        # 1. YAPI (MARKET STRUCTURE)
        # =========================================================
        score_str = 0; reasons_str = []
        recent_high = high.rolling(20).max().shift(1).iloc[-1]
        recent_low = low.rolling(20).min().shift(1).iloc[-1]
        curr_close = close.iloc[-1]
        
        if curr_close > recent_high:
            score_str += (W_STR * 0.6); reasons_str.append("BOS: Zirve Kırılımı")
        elif curr_close >= (recent_high * 0.97):
            score_str += (W_STR * 0.6); reasons_str.append("Zirveye Yakın (Güçlü)")
            
        if low.iloc[-1] > recent_low:
            score_str += (W_STR * 0.4); reasons_str.append("HL: Yükselen Dip")

        # =========================================================
        # 2. TREND
        # =========================================================
        score_tr = 0; reasons_tr = []
        sma50 = close.rolling(50).mean(); sma200 = close.rolling(200).mean()
        ema20 = close.ewm(span=20, adjust=False).mean()
        
        if close.iloc[-1] > sma200.iloc[-1]: score_tr += (W_TR * 0.4); reasons_tr.append("Ana Trend+")
        if close.iloc[-1] > ema20.iloc[-1]: score_tr += (W_TR * 0.4); reasons_tr.append("Kısa Vade+")
        if ema20.iloc[-1] > sma50.iloc[-1]: score_tr += (W_TR * 0.2); reasons_tr.append("Hizalı")

        # =========================================================
        # [GÜNCELLENMİŞ] 3. HACİM (ZAMAN AYARLI / PROJESİYONLU)
        # =========================================================
        score_vol = 0; reasons_vol = []
        
        # A. Ortalamayı hesapla (Bugünü hariç tutarak son 20 günün ortalaması)
        # Çünkü bugünün yarım yamalak hacmi ortalamayı bozmasın.
        avg_vol_20 = volume.iloc[:-1].tail(20).mean()
        if pd.isna(avg_vol_20) or avg_vol_20 == 0: avg_vol_20 = 1
        
        # B. Zaman İlerlemesini Hesapla (Progress 0.0 - 1.0)
        last_date = df.index[-1].date()
        today_date = datetime.now().date()
        is_live_today = (last_date == today_date)
        
        progress = 1.0 # Varsayılan: Gün bitti
        
        if is_live_today:
            now = datetime.now()
            # BIST Saati Kontrolü (Global sunucuda TR saati ayarı gerekebilir, 
            # burası sunucu saatine göre çalışır. Basitlik için 10:00-18:00 varsayıyoruz)
            # Eğer sunucun UTC ise +3 eklemek gerekebilir: datetime.now() + timedelta(hours=3)
            # Burayı standart yerel saat varsayıyoruz:
            current_hour = now.hour
            current_minute = now.minute
            
            # Kripto 7/24'tür ama hisse 10-18 arasıdır. Ayrım yapalım:
            if is_crypto:
                progress = (current_hour * 60 + current_minute) / 1440.0
            else:
                # Borsa İstanbul (10:00 - 18:00 = 480 dakika)
                if current_hour < 10: progress = 0.1
                elif current_hour >= 18: progress = 1.0
                else:
                    passed_mins = (current_hour - 10) * 60 + current_minute
                    progress = passed_mins / 480.0
            
            progress = max(0.1, min(progress, 1.0)) # 0'a bölme hatası olmasın
            
        # C. Projeksiyonlu Hacim (Bu hızla giderse gün sonu ne olur?)
        curr_vol_raw = float(volume.iloc[-1])
        projected_vol = curr_vol_raw / progress
        
        # KURAL 1: Hacim Artışı (Ortalamadan Büyük mü?)
        if projected_vol > avg_vol_20:
            score_vol += (W_VOL * 0.6)
            # Eğer saat erkense "Proj." ibaresi ekle ki kullanıcı anlasın
            suffix = " (Proj.)" if (is_live_today and progress < 0.9) else ""
            reasons_vol.append(f"Hacim Artışı{suffix}")
            
        # KURAL 2: OBV (On Balance Volume)
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        obv_ma = obv.rolling(10).mean()
        if obv.iloc[-1] > obv_ma.iloc[-1]: 
            score_vol += (W_VOL * 0.4)
            reasons_vol.append("OBV+")

        # =========================================================
        # 4. MOMENTUM
        # =========================================================
        score_mom = 0; reasons_mom = []
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs)).fillna(50)
        
        if rsi.iloc[-1] > 50: score_mom += 5; reasons_mom.append("RSI>50")
        if rsi.iloc[-1] > rsi.iloc[-5]: score_mom += 5; reasons_mom.append("RSI İvme")
        
        ema12 = close.ewm(span=12, adjust=False).mean(); ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26; signal = macd.ewm(span=9, adjust=False).mean()
        if macd.iloc[-1] > signal.iloc[-1]: score_mom += 5; reasons_mom.append("MACD Al")

        # =========================================================
        # 5. VOLATİLİTE
        # =========================================================
        score_vola = 0; reasons_vola = []
        std = close.rolling(20).std()
        upper = close.rolling(20).mean() + (2 * std)
        lower = close.rolling(20).mean() - (2 * std)
        bb_width = (upper - lower) / close.rolling(20).mean()
        
        if bb_width.iloc[-1] < bb_width.rolling(20).mean().iloc[-1]:
            score_vola += 10; reasons_vola.append("Sıkışma")
            
        # =========================================================
        # 6. GÜÇ (RS)
        # =========================================================
        score_rs = 0; reasons_rs = []
        if not is_index:
            bench_ticker = "XU100.IS" if ".IS" in ticker else "^GSPC"
            try:
                bench_df = get_safe_historical_data(bench_ticker, period="2y")
                if bench_df is not None:
                    common_idx = close.index.intersection(bench_df.index)
                    stock_p = close.loc[common_idx]
                    bench_p = bench_df['Close'].loc[common_idx]
                    
                    rs_ratio = stock_p / bench_p
                    rs_ma = rs_ratio.rolling(50).mean()
                    mansfield = ((rs_ratio / rs_ma) - 1) * 10
                    
                    if mansfield.iloc[-1] > 0: score_rs += 5; reasons_rs.append("Mansfield+")
                    if mansfield.iloc[-1] > mansfield.iloc[-5]: score_rs += 5; reasons_rs.append("RS İvme")
                    
                    stock_chg = (stock_p.iloc[-1] - stock_p.iloc[-2]) / stock_p.iloc[-2]
                    bench_chg = (bench_p.iloc[-1] - bench_p.iloc[-2]) / bench_p.iloc[-2]
                    if bench_chg < 0 and stock_chg > 0: score_rs += 5; reasons_rs.append("Alpha (Lider)")
                    elif stock_chg > bench_chg: score_rs += 3; reasons_rs.append("Endeks Üstü")
            except: reasons_rs.append("Veri Yok")

        total = int(score_str + score_tr + score_vol + score_mom + score_vola + score_rs)
        bars = int(total / 5)
        bar_str = "【" + "█" * bars + "░" * (20 - bars) + "】"
        def fmt(lst): 
            if not lst: return ""
            return f"<span style='font-size:0.7rem; color:#334155; font-style:italic; font-weight:300;'>({' + '.join(lst)})</span>"
        
        if is_index:
            rs_text = f"<span style='color:#94a3b8; font-style:italic; font-weight:600;'>Devre Dışı</span>"
        else:
            rs_text = f"{int(score_rs)}/{W_RS} {fmt(reasons_rs)}"

        return {
            "total": total, "bar": bar_str, 
            "mom": f"{int(score_mom)}/{W_MOM} {fmt(reasons_mom)}",
            "vol": f"{int(score_vol)}/{W_VOL} {fmt(reasons_vol)}", 
            "tr": f"{int(score_tr)}/{W_TR} {fmt(reasons_tr)}",
            "vola": f"{int(score_vola)}/{W_VOLA} {fmt(reasons_vola)}", 
            "str": f"{int(score_str)}/{W_STR} {fmt(reasons_str)}",
            "rs": rs_text, 
            "raw_rsi": rsi.iloc[-1], "raw_macd": (macd-signal).iloc[-1], "raw_obv": obv.iloc[-1], "raw_atr": 0,
            "is_index": is_index
        }
    except: return None
        
def get_deep_xray_data(ticker):
    sent = calculate_sentiment_score(ticker)
    if not sent: return None
    def icon(cond): return "✅" if cond else "❌"
    return {
        "mom_rsi": f"{icon(sent['raw_rsi']>50)} RSI Trendi",
        "mom_macd": f"{icon(sent['raw_macd']>0)} MACD Hist",
        "vol_obv": f"{icon('OBV ↑' in sent['vol'])} OBV Akışı",
        "tr_ema": f"{icon('GoldCross' in sent['tr'])} EMA Dizilimi",
        "tr_adx": f"{icon('P > SMA50' in sent['tr'])} Trend Gücü",
        "vola_bb": f"{icon('BB Break' in sent['vola'])} BB Sıkışması",
        "str_bos": f"{icon('BOS ↑' in sent['str'])} Yapı Kırılımı"
    }

@st.cache_data(ttl=600)
def calculate_ict_deep_analysis(ticker):
    error_ret = {"status": "Error", "msg": "Veri Yok", "structure": "-", "bias": "-", "entry": 0, "target": 0, "stop": 0, "rr": 0, "desc": "Veri bekleniyor", "displacement": "-", "fvg_txt": "-", "ob_txt": "-", "zone": "-", "mean_threshold": 0, "curr_price": 0, "setup_type": "BEKLE", "bottom_line": "-", "eqh_eql_txt": "-", "sweep_txt": "-"}
    
    try:
        df = get_safe_historical_data(ticker, period="1y")
        if df is None or len(df) < 60: return error_ret
        
        high = df['High']; low = df['Low']; close = df['Close']; open_ = df['Open']
        
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        avg_body_size = abs(open_ - close).rolling(20).mean()

        sw_highs = []; sw_lows = []
        for i in range(2, len(df)-2):
            try:
                if high.iloc[i] >= max(high.iloc[i-2:i]) and high.iloc[i] >= max(high.iloc[i+1:i+3]):
                    sw_highs.append((df.index[i], high.iloc[i])) 
                if low.iloc[i] <= min(low.iloc[i-2:i]) and low.iloc[i] <= min(low.iloc[i+1:i+3]):
                    sw_lows.append((df.index[i], low.iloc[i]))
            except: continue

        if not sw_highs or not sw_lows: return error_ret

        curr_price = close.iloc[-1]
        last_sh = sw_highs[-1][1] 
        last_sl = sw_lows[-1][1]  
        
        # --- BİAS VE YAPI TESPİTİ ---
        structure = "YATAY / KONSOLİDE"
        bias = "neutral"
        displacement_txt = "Zayıf (Hacimsiz Hareket)"
        
        # MSS (Market Structure Shift) Tespiti için bir önceki bias kontrolü
        prev_close = close.iloc[-2]
        is_prev_bearish = prev_close < last_sl
        is_prev_bullish = prev_close > last_sh

        last_candle_body = abs(open_.iloc[-1] - close.iloc[-1])
        if last_candle_body > avg_body_size.iloc[-1] * 1.2:
             displacement_txt = "🔥 Güçlü Displacement (Hacimli Kırılım)"
        
        if curr_price > last_sh:
            # Eğer önceden ayı yapısındaysak ve son tepeden yukarı çıktıysak bu MSS'tir
            if is_prev_bearish:
                structure = "MSS (Market Structure Shift) 🐂"
            else:
                structure = "BOS (Yükseliş Kırılımı) Order Flow Pozitif 🐂"
            bias = "bullish"
        elif curr_price < last_sl:
            # Eğer önceden boğa yapısındaysak ve son dpten aşağı indiysek bu MSS'tir
            if is_prev_bullish:
                structure = "MSS (Market Structure Shift) 🐻"
            else:
                structure = "BOS (Düşüş Kırılımı) Order Flow Negatif 🐻"
            bias = "bearish"
        else:
            structure = "Internal Range (Düşüş/Düzeltme)"
            if close.iloc[-1] > open_.iloc[-1]: bias = "bullish_retrace" 
            else: bias = "bearish_retrace"

        # --- 👇 YENİ: MIKNATIS (DOL) HESAPLAMA MANTIĞI 👇 ---
        # Fiyatın gitmek isteyeceği en yakın Likidite havuzlarını buluyoruz
        next_bsl = min([h[1] for h in sw_highs if h[1] > curr_price], default=high.max())
        next_ssl = max([l[1] for l in sw_lows if l[1] < curr_price], default=low.min())
        # Eğer bir setup yoksa, sistemin "Nereye bakacağını" belirleyen DOL (Draw on Liquidity)
        # Ayı piyasasında mıknatıs aşağıdaki DİP, Boğa piyasasında yukarıdaki TEPE'dir.
        magnet_target = next_bsl if "bullish" in bias else next_ssl
        # --- 👆 ---------------------------------------- 👆 ---
        # --- 👇 YENİ: LİKİDİTE HAVUZLARI (EQH / EQL) VE LİKİDİTE AVI (SWEEP) 👇 ---
        eqh_eql_txt = "Yok"
        sweep_txt = "Yok"
        
        tol = curr_price * 0.003 # Eşitlik için %0.3 tolerans payı
        
        # EQL / EQH (Eşit Tepe ve Dipler) Tespiti
        if len(sw_lows) >= 2:
            l1 = sw_lows[-1][1]; l2 = sw_lows[-2][1]
            if abs(l1 - l2) < tol: eqh_eql_txt = f"EQL (Eşit Dipler): {l1:.2f}"
                
        if len(sw_highs) >= 2:
            h1 = sw_highs[-1][1]; h2 = sw_highs[-2][1]
            if abs(h1 - h2) < tol:
                if eqh_eql_txt == "Yok": eqh_eql_txt = f"EQH (Eşit Tepeler): {h1:.2f}"
                else: eqh_eql_txt += f" | EQH: {h1:.2f}"

        # LİKİDİTE AVI (SWEEP / TURTLE SOUP) Tespiti
        # Fiyat son 3 mumda son tepenin/dibin dışına çıkıp (iğne atıp), ters yönde kapattıysa
        recent_lows = low.iloc[-3:]
        recent_highs = high.iloc[-3:]
        
        # BSL Sweep (Tepe Likidite Avı - Ayı Sinyali)
        if (recent_highs.max() > last_sh) and (close.iloc[-1] < last_sh):
            sweep_txt = f"🧹 BSL Sweep (Tepe Avı): {last_sh:.2f}"
            
        # SSL Sweep (Dip Likidite Avı - Boğa Sinyali)
        elif (recent_lows.min() < last_sl) and (close.iloc[-1] > last_sl):
            sweep_txt = f"🧹 SSL Sweep (Dip Avı): {last_sl:.2f}"
        # --- 👆 ------------------------------------------------------------- 👆 ---
        # FVG ve OB Taraması
        bullish_fvgs = []; bearish_fvgs = []
        active_fvg_txt = "Yok"
        for i in range(len(df)-30, len(df)-1):
            if i < 2: continue
            if low.iloc[i] > high.iloc[i-2]:
                gap_size = low.iloc[i] - high.iloc[i-2]
                if gap_size > atr * 0.05:
                    bullish_fvgs.append({'top': low.iloc[i], 'bot': high.iloc[i-2], 'idx': i})
            elif high.iloc[i] < low.iloc[i-2]:
                gap_size = low.iloc[i-2] - high.iloc[i]
                if gap_size > atr * 0.05:
                    bearish_fvgs.append({'top': low.iloc[i-2], 'bot': high.iloc[i], 'idx': i})

        active_ob_txt = "Yok"
        mean_threshold = 0.0
        lookback = 20
        start_idx = max(0, len(df) - lookback)
        
        if bias == "bullish" or bias == "bullish_retrace":
            if bullish_fvgs:
                f = bullish_fvgs[-1]
                active_fvg_txt = f"Açık FVG var (Destek): {f['bot']:.2f} - {f['top']:.2f}"
            lowest_idx = df['Low'].iloc[start_idx:].idxmin()
            if isinstance(lowest_idx, pd.Timestamp): lowest_idx = df.index.get_loc(lowest_idx)
            for i in range(lowest_idx, max(0, lowest_idx-5), -1):
                if df['Close'].iloc[i] < df['Open'].iloc[i]:
                    ob_low = df['Low'].iloc[i]; ob_high = df['High'].iloc[i]
                    active_ob_txt = f"{ob_low:.2f} - {ob_high:.2f} (Talep Bölgesi)"
                    mean_threshold = (ob_low + ob_high) / 2
                    break
        elif bias == "bearish" or bias == "bearish_retrace":
            if bearish_fvgs:
                f = bearish_fvgs[-1]
                active_fvg_txt = f"Açık FVG var (Direnç): {f['bot']:.2f} - {f['top']:.2f}"
            highest_idx = df['High'].iloc[start_idx:].idxmax()
            if isinstance(highest_idx, pd.Timestamp): highest_idx = df.index.get_loc(highest_idx)
            for i in range(highest_idx, max(0, highest_idx-5), -1):
                if df['Close'].iloc[i] > df['Open'].iloc[i]:
                    ob_low = df['Low'].iloc[i]; ob_high = df['High'].iloc[i]
                    active_ob_txt = f"{ob_low:.2f} - {ob_high:.2f} (Arz Bölgesi)"
                    mean_threshold = (ob_low + ob_high) / 2
                    break

        range_high = max(high.tail(60)); range_low = min(low.tail(60))
        range_loc = (curr_price - range_low) / (range_high - range_low)
        zone = "PREMIUM (Pahalı)" if range_loc > 0.5 else "DISCOUNT (Ucuz)"

        # --- SETUP VE HEDEF KARARI ---
        setup_type = "BEKLE"
        entry_price = 0.0; stop_loss = 0.0; take_profit = 0.0; rr_ratio = 0.0
        # Varsayılan hedefi mıknatıs (DOL) olarak belirliyoruz
        final_target = magnet_target 
        setup_desc = "İdeal bir setup (Entry) bekleniyor. Mevcut yön mıknatısı takip ediliyor."

        if bias in ["bullish", "bullish_retrace"] and zone == "DISCOUNT (Ucuz)":
            valid_fvgs = [f for f in bullish_fvgs if f['top'] < curr_price]
            if valid_fvgs and next_bsl > curr_price:
                best_fvg = valid_fvgs[-1]; temp_entry = best_fvg['top']
                if next_bsl > temp_entry:
                    entry_price = temp_entry; take_profit = next_bsl
                    stop_loss = last_sl if last_sl < entry_price else best_fvg['bot'] - atr * 0.5
                    final_target = take_profit # Setup varsa hedef kâr al seviyesidir
                    setup_type = "LONG"; setup_desc = "Fiyat ucuzluk bölgesinde. FVG desteğinden likidite (BSL) hedefleniyor."

        elif bias in ["bearish", "bearish_retrace"] and zone == "PREMIUM (Pahalı)":
            valid_fvgs = [f for f in bearish_fvgs if f['bot'] > curr_price]
            if valid_fvgs and next_ssl < curr_price:
                best_fvg = valid_fvgs[-1]; temp_entry = best_fvg['bot']
                if next_ssl < temp_entry:
                    entry_price = temp_entry; take_profit = next_ssl
                    stop_loss = last_sh if last_sh > entry_price else best_fvg['top'] + atr * 0.5
                    final_target = take_profit # Setup varsa hedef kâr al seviyesidir
                    setup_type = "SHORT"; setup_desc = "Fiyat pahalılık bölgesinde. Direnç bloğundan likidite (SSL) hedefleniyor."

        # --- 👇 YENİ: AKSİYON ÖZETİ (THE BOTTOM LINE) ANALİZÖRÜ 👇 ---
        struct_summary = "Yapı zayıf (Order Flow Negatif)" if "bearish" in bias else "Yapı güçlü (Order Flow Pozitif)"
        zone_summary = "fiyat pahalı bölgesinden" if zone == "PREMIUM (Pahalı)" else "fiyat ucuzluk bölgesinden"
        
        # --- GÜVENLİ SEVİYE MANTIĞI (DÜZELTİLDİ: Trader Mantığı) ---
        safety_lvl = 0.0
        
        if "bearish" in bias:
            # Ayı piyasasında "Güvenli Alım" için Önümüzdeki İLK CİDDİ ENGELE (FVG veya Swing High) bakarız.
            candidates = []
            
            # 1. Aday: En yakın üst direnç FVG'sinin TEPESİ
            valid_fvgs = [f for f in bearish_fvgs if f['bot'] > curr_price]
            if valid_fvgs:
                # En yakındaki FVG'yi bul
                closest_fvg = min(valid_fvgs, key=lambda x: x['bot'] - curr_price)
                candidates.append(closest_fvg['top'])
            
            # 2. Aday: Son Swing High (MSS Seviyesi)
            if last_sh > curr_price:
                candidates.append(last_sh)
            
            # Hiçbiri yoksa mecburen Mean Threshold veya %5 yukarı
            if not candidates:
                 safety_lvl = mean_threshold if mean_threshold > curr_price else curr_price * 1.05
            else:
                 # En yakın (en düşük) direnci seçiyoruz.
                 safety_lvl = min(candidates)

        else:
            # Boğa piyasasında destek kırılımı (Stop) seviyesi
            safety_lvl = last_sl
        
        
        import random

        # --- İleri ve Derin Hedeflerin Hesaplanması (Sıralı Likidite Havuzları) ---
        # Fiyatın üstündeki tepeleri (küçükten büyüğe) ve altındaki dipleri (büyükten küçüğe) sırala
        all_highs = sorted([h[1] for h in sw_highs if h[1] > curr_price])
        all_lows = sorted([l[1] for l in sw_lows if l[1] < curr_price], reverse=True)
        
        # Boğa (Yükseliş) için 2. Likidite Havuzunu (İleri Hedef) belirle
        if len(all_highs) > 1:
            ileri_hedef = all_highs[1]
        elif len(all_highs) == 1:
            ileri_hedef = all_highs[0] * 1.02
        else:
            ileri_hedef = curr_price * 1.04
            
        # Ayı (Düşüş) için 2. Likidite Havuzunu (Derin Hedef) belirle
        if len(all_lows) > 1:
            derin_hedef = all_lows[1]
        elif len(all_lows) == 1:
            derin_hedef = all_lows[0] * 0.98
        else:
            derin_hedef = curr_price * 0.96
            
        # Matematiksel Emniyet Kilidi (İkinci hedef, ilk hedeften daha geride olamaz)
        if derin_hedef >= final_target: 
            derin_hedef = final_target * 0.98
        if ileri_hedef <= final_target: 
            ileri_hedef = final_target * 1.02

        # KARAR MATRİSİ: Yön (Bias) x Konum (Zone) Çaprazlaması (HİBRİT SENARYOLAR)
        is_bullish = "bullish" in bias
        is_premium = "PREMIUM" in zone

        if is_bullish and not is_premium:
            # 1. ÇEYREK: Boğa + Ucuzluk (İdeal Long Bölgesi)
            lines = [
                f"Trend yukarı (Bullish) ve fiyat cazip (Discount) bölgesinde. Kurumsal alım iştahı (Order Flow) ivmeleniyor. {final_target:.2f} direncindeki ilk stop havuzu alındıktan sonra gözler {ileri_hedef:.2f} ana hedefine çevrilecek. Sermaye koruması için {safety_lvl:.2f} majör destek olarak sıkı korunmalı.",
                f"İdeal 'Smart Money' koşulları devrede: Yön yukarı, fiyat iskontolu. Toplanan emirlerle {final_target:.2f} seviyesindeki likidite hedefleniyor, ardından {ileri_hedef:.2f} bandına yürüyüş başlayabilir. Olası tuzaklara karşı {safety_lvl:.2f} seviyesinin altı yapısal iptal (invalidation) alanıdır.",
                f"Piyasa yapısı güçlü ve fiyat ucuzluk (Discount) seviyelerinde. Kurumsal destekle önce {final_target:.2f}, ardından {ileri_hedef:.2f} dirençleri kademeli hedef konumunda. Trendin sigortası olan {safety_lvl:.2f} desteği kırılmadıkça yön yukarıdır."
            ]
        elif is_bullish and is_premium:
            # 2. ÇEYREK: Boğa + Pahalılık (FOMO / Kâr Realizasyonu Riski - Senin Formatın)
            lines = [
                f"Trend yukarı (Bullish) ancak fiyat pahalılık (Premium) bölgesinde. Kurumsal alım iştahı (Order Flow) devam ediyor. {final_target:.2f} seviyesindeki ilk stop havuzu alındıktan sonra gözler {ileri_hedef:.2f} likiditesine çevrilecek. Ancak {final_target:.2f} hedefine ulaşılamadan kurumsal kâr satışları (Realizasyon) gelebilir. {safety_lvl:.2f} kırılırsa trend bozulur.",
                f"Yapı pozitif olsa da fiyat 'Premium' seviyelerde yorulma emareleri gösteriyor. Hedefte ilk olarak {final_target:.2f}, ardından {ileri_hedef:.2f} dirençleri var. Buralardan (FOMO ile) yeni maliyetlenmek risklidir; {safety_lvl:.2f} altı kapanışlarda anında savunmaya geçilmeli.",
                f"Boğalar kontrolü elinde tutuyor fakat fiyat şişmiş (Premium) durumda. Kademeli hedeflerimiz sırasıyla {final_target:.2f} ve {ileri_hedef:.2f} olsa da, bu bölgelerde son bir likidite avı izlenip sert satış gelebilir. İptal seviyesi {safety_lvl:.2f} kesinlikle tavizsiz uygulanmalı."
            ]
        elif not is_bullish and is_premium:
            # 3. ÇEYREK: Ayı + Pahalılık (İdeal Short / Dağıtım Bölgesi)
            lines = [
                f"Trend aşağı (Bearish) ve fiyat tam dağıtım (Premium) bölgesinde. Satıcılı baskı sürüyor; {final_target:.2f} seviyesindeki ilk durak kırıldıktan sonra gözler ana uçurum olan {derin_hedef:.2f} likiditesine çevrilecek. Bu ivmenin bozulması ve trend dönüşü için {safety_lvl:.2f} üzerinde kalıcılık şart.",
                f"Piyasa yapısı zayıf ve kurumsal oyuncular mal çıkıyor (Distribution). Pahalılık bölgesinden başlayan düşüş trendinde {final_target:.2f} hedefine çekilme var, satışlar derinleşirse {derin_hedef:.2f} bandı test edilebilir. İptal seviyesi: {safety_lvl:.2f}.",
                f"Aşağı yönlü momentum devrede, satıcılar avantajlı (Premium) konumda. Hedefte sırasıyla {final_target:.2f} ve {derin_hedef:.2f} desteklerindeki stop havuzları var. Fiyata karşı inatlaşmamak ve 'Long' denemek için {safety_lvl:.2f} aşılmasını beklemek kritik."
            ]
        else:
            # 4. ÇEYREK: Ayı + Ucuzluk (Aşırı Satım / Sweep Beklentisi)
            lines = [
                f"Trend aşağı (Bearish) ancak fiyat iskontolu (Discount) bölgeye inmiş durumda. Satış baskısı devam ediyor; ilk durak {final_target:.2f} ve ardından {derin_hedef:.2f} hedefleri masada. Ancak buralardan 'Short' açmak risklidir, kurumsallar stop patlatıp (Sweep) dönebilir. Dönüş onayı {safety_lvl:.2f}.",
                f"Aşırı satım (Oversold) bölgesi! Yapı negatif görünse de fiyat çok ucuzlamış. {final_target:.2f} altındaki likiditeye doğru son bir silkeleme (Liquidity Hunt) yaşandıktan sonra {derin_hedef:.2f} görülmeden sert tepki gelebilir. Trend dönüşü için {safety_lvl:.2f} aşılmalı.",
                f"Ayı piyasası sürüyor fakat fiyatın ucuzluk (Discount) bölgesinde olması düşüş momentumunu yavaşlatabilir. Kademeli hedefler {final_target:.2f} ve {derin_hedef:.2f} olsa da, olası sert tepki alımlarına karşı savunmada kalınmalı ve {safety_lvl:.2f} direnci yakından izlenmeli."
            ]

        bottom_line = random.choice(lines)
        

        return {
            "status": "OK", "structure": structure, "bias": bias, "zone": zone,
            "setup_type": setup_type, "entry": entry_price, "stop": stop_loss, 
            "target": final_target, 
            "rr": rr_ratio, "desc": setup_desc, "last_sl": last_sl, "last_sh": last_sh,
            "displacement": displacement_txt, "fvg_txt": active_fvg_txt, "ob_txt": active_ob_txt,
            "mean_threshold": mean_threshold, "curr_price": curr_price,
            "bottom_line": bottom_line,
            "eqh_eql_txt": eqh_eql_txt,
            "sweep_txt": sweep_txt
        }

    except Exception: return error_ret
        
@st.cache_data(ttl=600)
def calculate_price_action_dna(ticker):
    try:
        df = get_safe_historical_data(ticker, period="6mo") 
        if df is None or len(df) < 50: return None
        # --- YENİ HACİM HESAPLAMALARI (ADIM 2) BURAYA EKLENDİ ---
        df = df[df['Volume'] > 0].copy() 
        if len(df) < 20: return None
        df = calculate_volume_delta(df)
        poc_price = calculate_volume_profile_poc(df, lookback=20, bins=20)
        # --------------------------------------------------------
        o = df['Open']; h = df['High']; l = df['Low']; c = df['Close']; v = df['Volume']
        
        # --- VERİ HAZIRLIĞI (SON 3 GÜN) ---
        # Şimdi iloc[-1] dediğinde her zaman hacmi olan EN SON GERÇEK günü alacak
        c1_o, c1_h, c1_l, c1_c = float(o.iloc[-1]), float(h.iloc[-1]), float(l.iloc[-1]), float(c.iloc[-1]) 
        c1_v = float(v.iloc[-1])
        c2_o, c2_h, c2_l, c2_c = float(o.iloc[-2]), float(h.iloc[-2]), float(l.iloc[-2]), float(c.iloc[-2]) # Dün
        c3_o, c3_h, c3_l, c3_c = float(o.iloc[-3]), float(h.iloc[-3]), float(l.iloc[-3]), float(c.iloc[-3]) # Önceki Gün
        
        c1_v = float(v.iloc[-1])
        avg_v = float(v.rolling(20).mean().iloc[-1]) 
        sma50 = c.rolling(50).mean().iloc[-1]
        # --- [YENİ] GELİŞMİŞ HACİM ANALİZİ DEĞİŞKENLERİ ---
        rvol = c1_v / avg_v if avg_v > 0 else 1.0
        
        # RSI Serisi
        delta = c.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs_calc = gain / loss
        rsi_series = 100 - (100 / (1 + rs_calc))
        rsi_val = rsi_series.iloc[-1]

        # Mum Geometrisi
        body = abs(c1_c - c1_o)
        total_len = c1_h - c1_l if (c1_h - c1_l) > 0 else 0.01
        u_wick = c1_h - max(c1_o, c1_c)
        l_wick = min(c1_o, c1_c) - c1_l
        is_green = c1_c > c1_o
        is_red = c1_c < c1_o
        
        # --- [YENİ] STOPPING & CLIMAX KONTROLLERİ ---
        stop_vol_msg = "Yok"
        if c1_v > (avg_v * 1.5) and body < (total_len * 0.3) and l_wick > (total_len * 0.5):
            stop_vol_msg = "VAR 🔥 (Dipten kurumsal toplama emaresi!)"

        climax_msg = "Yok"
        ema20_tmp = c.ewm(span=20).mean().iloc[-1]
        price_dist_tmp = (c1_c / ema20_tmp) - 1
        if c1_v == v.tail(50).max() and price_dist_tmp > 0.10:
            climax_msg = "VAR ⚠️ (Trend sonu tahliye/FOMO riski!)"

        # RSI Serisi (Uyumsuzluk için)
        delta = c.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs_calc = gain / loss
        rsi_series = 100 - (100 / (1 + rs_calc))
        rsi_val = rsi_series.iloc[-1]

        # Mum Geometrisi (Son gün)
        body = abs(c1_c - c1_o)
        total_len = c1_h - c1_l
        u_wick = c1_h - max(c1_o, c1_c)
        l_wick = min(c1_o, c1_c) - c1_l
        is_green = c1_c > c1_o
        is_red = c1_c < c1_o
        
        # Toleranslar
        wick_ratio = 2.0 
        doji_threshold = 0.15 
        tweezer_tol = c1_c * 0.001 

        bulls, bears, neutrals = [], [], []
        
        # --- BAĞLAM (CONTEXT) ANALİZİ ---
        trend_dir = "YÜKSELİŞ" if c1_c > sma50 else "DÜŞÜŞ"
        is_overbought = rsi_val > 70
        is_oversold = rsi_val < 30
        vol_confirmed = c1_v > avg_v * 1.2 

        # Sinyal Ekleme Fonksiyonu
        def add_signal(sig_list, name, is_bullish):
            prefix = ""
            if is_bullish:
                if trend_dir == "YÜKSELİŞ": prefix = "🔥 Trend Yönünde "
                elif trend_dir == "DÜŞÜŞ": prefix = "⚠️ Tepki/Dönüş "
                if is_overbought: prefix += "(Riskli Tepe) "
            else: 
                if trend_dir == "DÜŞÜŞ": prefix = "📉 Trend Yönünde "
                elif trend_dir == "YÜKSELİŞ": prefix = "⚠️ Düzeltme/Dönüş "
                if is_oversold: prefix += "(Riskli Dip) "
            suffix = " (Hacimli!)" if vol_confirmed else ""
            sig_list.append(f"{prefix}{name}{suffix}")

        # ======================================================
        # 1. TEKLİ MUM FORMASYONLARI (KESİN ÇÖZÜM - FULL BLOK)
        # ======================================================
        if total_len > 0:
            # Doji çakışmasını ve hatalı "bağlam" atlamalarını önlemek için kilit değişken
            is_identified = False 

            # A) SHOOTING STAR / TERS PİNBAR (Üst Fitil Baskın)
            # Kural: Üst fitil mumun en az %60'ı kadar olmalı ve alt fitil küçük kalmalı.
            if u_wick > total_len * 0.60 and l_wick < total_len * 0.25:
                is_identified = True
                # Şekli tanıdık, şimdi bağlama göre isimlendirelim
                if trend_dir == "YÜKSELİŞ" or is_overbought:
                    add_signal(bears, "Shooting Star (Kayan Yıldız) 🌠", False)
                elif trend_dir == "DÜŞÜŞ":
                    add_signal(bulls, "Inverted Hammer (Ters Çekiç) 🏗️", True)
                else:
                    neutrals.append("Ters Pinbar (Üstten Ret) 📌")

            # B) HAMMER / ÇEKİÇ (Alt Fitil Baskın)
            # Kural: Alt fitil mumun en az %60'ı kadar olmalı ve üst fitil küçük kalmalı.
            elif l_wick > total_len * 0.60 and u_wick < total_len * 0.25:
                is_identified = True
                if trend_dir == "DÜŞÜŞ" or is_oversold:
                    add_signal(bulls, "Hammer (Çekiç) 🔨", True)
                elif trend_dir == "YÜKSELİŞ":
                    add_signal(bears, "Hanging Man (Asılı Adam) 💀", False)
                else:
                    neutrals.append("Pinbar (Alttan Destek) 📌")

            # C) MARUBOZU (Gövde Baskın - Güçlü Mum)
            elif body > total_len * 0.85:
                is_identified = True
                if is_green: 
                    add_signal(bulls, "Marubozu (Güçlü Boğa) 🚀", True)
                else: 
                    add_signal(bears, "Marubozu (Güçlü Ayı) 🔻", False)

            # D) STOPPING VOLUME (Fiyat Hareketi + Hacim Onayı)
            if not is_identified and (l_wick > body * 2.0) and (c1_v > avg_v * 1.5) and (c1_l < c2_l):
                bulls.append("🛑 STOPPING VOLUME (Kurumsal Alım)")
                is_identified = True

            # E) DOJİ (Son Çare / Çöp Kutusu)
            # Sadece yukarıdaki belirgin şekillerden biri DEĞİLSE ve gövde çok küçükse çalışır.
            if not is_identified and body < total_len * doji_threshold:
                neutrals.append("Doji (Kararsızlık) ⚖️")

        # ======================================================
        # 2. İKİLİ MUM FORMASYONLARI
        # ======================================================
        
        # Bullish Kicker (Sert Gap Up)
        if (c2_c < c2_o) and is_green and (c1_o > c2_o): 
            add_signal(bulls, "Bullish Kicker (Sert GAP) 🦵", True)

        # Engulfing (Yutan)
        if (c2_c < c2_o) and is_green and (c1_c > c2_o) and (c1_o < c2_c): add_signal(bulls, "Bullish Engulfing 🐂", True)
        if (c2_c > c2_o) and is_red and (c1_c < c2_o) and (c1_o > c2_c): add_signal(bears, "Bearish Engulfing 🐻", False)
        
        # Piercing / Dark Cloud
        c2_mid = (c2_o + c2_c) / 2
        if (c2_c < c2_o) and is_green and (c1_o < c2_c) and (c1_c > c2_mid) and (c1_c < c2_o): add_signal(bulls, "Piercing Line 🌤️", True)
        if (c2_c > c2_o) and is_red and (c1_o > c2_c) and (c1_c < c2_mid) and (c1_c > c2_o): add_signal(bears, "Dark Cloud Cover ☁️", False)
        
        # Tweezer (Cımbız)
        if abs(c1_l - c2_l) < tweezer_tol and (c1_l < c3_l): add_signal(bulls, "Tweezer Bottom 🥢", True)
        if abs(c1_h - c2_h) < tweezer_tol and (c1_h > c3_h): add_signal(bears, "Tweezer Top 🥢", False)
        
        # Harami
        if (c1_h < c2_h) and (c1_l > c2_l):
            # Eğer hacim de son 10 günün en düşüğüyse veya ortalamanın en az %35 altındaysa
            if c1_v < avg_v * 0.7:
                neutrals.append("NR4: 4 Gündür Dar Bantta (Patlama gelebilir)") # Çok daha değerli bir sinyal!
            else:
                neutrals.append("Inside Bar (Bekle) ⏸️")

        # ======================================================
        # 3. ÜÇLÜ MUM FORMASYONLARI
        # ======================================================
        
        # Morning Star (Sabah Yıldızı - Dipten Dönüş)
        # 1. Kırmızı, 2. Küçük Gövde, 3. Yeşil (ilk mumun yarısını geçen)
        if (c3_c < c3_o) and (abs(c2_c - c2_o) < total_len * 0.3) and is_green and (c1_c > (c3_o + c3_c)/2):
             if is_oversold or trend_dir == "DÜŞÜŞ": add_signal(bulls, "Morning Star ⭐", True)

        # [EKLENEN EKSİK PARÇA] Evening Star (Akşam Yıldızı - Tepeden Dönüş)
        # 1. Yeşil, 2. Küçük Gövde, 3. Kırmızı (ilk mumun yarısını aşağı geçen)
        if (c3_c > c3_o) and (abs(c2_c - c2_o) < total_len * 0.3) and is_red and (c1_c < (c3_o + c3_c)/2):
             if is_overbought or trend_dir == "YÜKSELİŞ": add_signal(bears, "Evening Star 🌆", False)

        # 3 White Soldiers
        if (c1_c > c1_o) and (c2_c > c2_o) and (c3_c > c3_o) and (c1_c > c2_c > c3_c):
             if c1_c > c1_h * 0.95: add_signal(bulls, "3 White Soldiers ⚔️", True)

        # 3 Black Crows
        if (c1_c < c1_o) and (c2_c < c2_o) and (c3_c < c3_o) and (c1_c < c2_c < c3_c):
             if c1_c < c1_l * 1.05: add_signal(bears, "3 Black Crows 🦅", False)

        # --- ÇIKTI FORMATLAMA ---
        signal_summary = ""
        priorities = ["Bullish Kicker", "Stopping Volume", "3 White Soldiers"]
        for p in priorities:
            for b in bulls:
                if p in b: bulls.remove(b); bulls.insert(0, b); break

        if bulls: signal_summary += f"ALICI: {', '.join(bulls)} "
        if bears: signal_summary += f"SATICI: {', '.join(bears)} "
        if neutrals: signal_summary += f"NÖTR: {', '.join(neutrals)}"
        
        candle_desc = signal_summary if signal_summary else "Belirgin, güçlü bir formasyon yok."
        candle_title = "Formasyon Tespiti"

        # ======================================================
        # 4. DİĞER GÖSTERGELER (SFP, VSA, KONUM, SIKIŞMA)
        # ======================================================
        
        # SFP
        sfp_txt, sfp_desc = "Yok", "Önemli bir tuzak tespiti yok."
        recent_highs = h.iloc[-20:-1].max(); recent_lows = l.iloc[-20:-1].min()
        if c1_h > recent_highs and c1_c < recent_highs: sfp_txt, sfp_desc = "⚠️ Bearish SFP (Boğa Tuzağı)", "Tepe temizlendi ama tutunamadı."
        elif c1_l < recent_lows and c1_c > recent_lows: sfp_txt, sfp_desc = "💎 Bullish SFP (Ayı Tuzağı)", "Dip temizlendi ve geri döndü."

        # VSA
        vol_txt, vol_desc = "Normal", "Hacim ortalama seyrediyor."
        if c1_v > avg_v * 1.5:
            if "🛑 STOPPING VOLUME" in signal_summary: vol_txt, vol_desc = "🛑 STOPPING VOLUME", "Düşüşte devasa hacimle frenleme."
            elif body < total_len * 0.3: vol_txt, vol_desc = "⚠️ Churning (Boşa Çaba)", "Yüksek hacme rağmen fiyat gidemiyor."
            else: vol_txt, vol_desc = "🔋 Trend Destekli", "Fiyat hareketi hacimle destekleniyor."

        # Konum (BOS)
        loc_txt, loc_desc = "Denge Bölgesi", "Fiyat konsolidasyon içinde."
        if c1_c > h.iloc[-20:-1].max(): loc_txt, loc_desc = "📈 Zirve Kırılımı (BOS)", "Son 20 günün zirvesi aşıldı."
        elif c1_c < l.iloc[-20:-1].min(): loc_txt, loc_desc = "📉 Dip Kırılımı (BOS)", "Son 20 günün dibi kırıldı."

        # Volatilite (Coil)
        atr = (h-l).rolling(14).mean().iloc[-1]
        range_5 = h.tail(5).max() - l.tail(5).min()
        sq_txt, sq_desc = "Normal", "Oynaklık normal seviyede."
        if range_5 < (1.5 * atr): sq_txt, sq_desc = "⏳ SÜPER SIKIŞMA (Coil)", "Fiyat yay gibi gerildi. Patlama yakın."

        # ======================================================
        # 5.5. OBV UYUMSUZLUĞU (SMART MONEY FİLTRELİ - YENİ)
        # ======================================================
        # A. OBV ve SMA Hesapla
        change_obv = c.diff()
        dir_obv = np.sign(change_obv).fillna(0)
        obv = (dir_obv * v).cumsum()
        
        # Profesyonel Filtre: OBV'nin 20 günlük ortalaması
        obv_sma = obv.rolling(20).mean()
        
        # B. Kıyaslamalar
        p_now = c.iloc[-1]; p_old = c.iloc[-11]
        obv_now = obv.iloc[-1]; obv_old = obv.iloc[-11]
        obv_sma_now = obv_sma.iloc[-1]
        
        p_tr = "YUKARI" if p_now > p_old else "AŞAĞI"
        o_tr_raw = "YUKARI" if obv_now > obv_old else "AŞAĞI"
        
        # Güç Filtresi: OBV şu an ortalamasının üzerinde mi?
        is_obv_strong = obv_now > obv_sma_now

        obv_data = {"title": "Nötr / Zayıf", "desc": "Hacim akışı ortalamanın altında.", "color": "#64748B"}
        
        # Senaryo 1: GİZLİ GİRİŞ (Fiyat Düşerken Mal Toplama)
        if p_tr == "AŞAĞI" and o_tr_raw == "YUKARI":
            if is_obv_strong:
                obv_data = {"title": "🔥 GÜÇLÜ GİZLİ GİRİŞ", "desc": "Fiyat düşerken OBV ortalamasını kırdı (Smart Money).", "color": "#16a34a"}
            else:
                obv_data = {"title": "👀 Olası Toplama (Zayıf)", "desc": "OBV artıyor ama henüz ortalamayı geçemedi.", "color": "#d97706"}
                
        # Senaryo 2: GİZLİ ÇIKIŞ (Fiyat Çıkarken Mal Çakma)
        elif p_tr == "YUKARI" and o_tr_raw == "AŞAĞI":
            obv_data = {"title": "⚠️ GİZLİ ÇIKIŞ", "desc": "Fiyat çıkarken OBV düşüyor.", "color": "#dc2626"}
            
        # Senaryo 3: TREND DESTEĞİ
        elif is_obv_strong:
            obv_data = {"title": "✅ Hacim Destekli Trend", "desc": "OBV ortalamasının üzerinde.", "color": "#15803d"}

        # ======================================================
        # 6. RSI UYUMSUZLUK (DIVERGENCE) - GÜNCELLENMİŞ HASSASİYET
        # ==========================================================
        div_txt, div_desc, div_type = "Uyumlu", "RSI ve Fiyat paralel.", "neutral"
        try:
            # Son 5 gün vs Önceki 15 gün
            current_window = c.iloc[-5:]
            prev_window = c.iloc[-20:-5]

            # Negatif Uyumsuzluk (Ayı)
            p_curr_max = current_window.max(); p_prev_max = prev_window.max()
            r_curr_max = rsi_series.iloc[-5:].max(); r_prev_max = rsi_series.iloc[-20:-5].max()

            # --- FİLTRELER ---
            # 1. RSI Tavanı: 75 üstüyse "Sat" deme.
            is_rsi_saturated = rsi_val >= 75
            # 2. SMA50 Kuralı: Fiyat SMA50'nin %20'sinden fazla yukarıdaysa "Ralli Modu"dur.
            is_parabolic = c1_c > (sma50 * 1.20)
            # 3. Mum Rengi: Son mum (is_red) kırmızı değilse sat deme. (is_red yukarıda tanımlıydı)

            # Matematiksel Uyumsuzluk Kontrolü
            # DÜZELTME: ">" yerine ">=" kullanarak İkili Tepeleri de dahil ettik.
            if (p_curr_max >= p_prev_max) and (r_curr_max < r_prev_max) and (r_prev_max > 60):
                
                # KARAR MEKANİZMASI: Filtrelerin HEPSİNDEN geçerse uyarı ver
                if not is_rsi_saturated and is_red and not is_parabolic:
                    div_txt = "🐻 NEGATİF UYUMSUZLUK (Tepe Zayıflığı)"
                    div_desc = "Fiyat zirveyi zorluyor, RSI yoruluyor ve satış geldi."
                    div_type = "bearish"
                else:
                    # Uyumsuzluk var ama trend çok güçlü (Ralli Modu)
                    div_txt = "🚀 GÜÇLÜ MOMENTUM (Aşırı Alım)"
                    reason = "Fiyat koptu (%20+)" if is_parabolic else "RSI doygunlukta"
                    div_desc = f"Negatif uyumsuzluk var ANCAK trend çok güçlü ({reason}). Henüz dönüş onayı yok."
                    div_type = "neutral"

            # Pozitif Uyumsuzluk (Boğa)
            p_curr_min = current_window.min(); p_prev_min = prev_window.min()
            r_curr_min = rsi_series.iloc[-5:].min(); r_prev_min = rsi_series.iloc[-20:-5].min()

            # DÜZELTME: "<" yerine "<=" kullanarak İkili Dipleri de dahil ettik.
            if (p_curr_min <= p_prev_min) and (r_curr_min > r_prev_min) and (r_prev_min < 45):
                div_txt = "💎 POZİTİF UYUMSUZLUK (Gizli Güç)"
                div_desc = "Fiyat dipte tutunuyor ve RSI yükseliyor. Toplama sinyali!"
                div_type = "bullish"

        except: pass

        # ======================================================
        # 7. & 8. SMART MONEY VERİLERİ (VWAP & RS)
        # ======================================================
        
        # --- 7. VWAP (KURUMSAL MALİYET) ---
        vwap_now = c1_c; vwap_diff = 0
        try:
            # 'ta' kütüphanesi ile 20 günlük (Aylık) VWAP hesabı
            vwap_indicator = VolumeWeightedAveragePrice(high=h, low=l, close=c, volume=v, window=20)
            vwap_series = vwap_indicator.volume_weighted_average_price()
            vwap_now = float(vwap_series.iloc[-1])
            
            # Sapma Yüzdesi
            vwap_diff = ((c1_c - vwap_now) / vwap_now) * 100
        except:
            pass

        # --- 8. RS (PİYASA GÜCÜ / ALPHA) ---
        alpha_val = 0.0
        try:
            # Hissenin ait olduğu endeksi bul
            bench_ticker = "XU100.IS" if ".IS" in ticker else "^GSPC"
            # Endeks verisini çek (Cache'den gelir, hızlıdır)
            df_bench = get_safe_historical_data(bench_ticker, period="1mo")
            
            if df_bench is not None and not df_bench.empty:
                # Günlük Değişimleri Hesapla (Son gün)
                stock_chg = ((c1_c - c2_c) / c2_c) * 100
                
                b_close = df_bench['Close']
                bench_chg = ((b_close.iloc[-1] - b_close.iloc[-2]) / b_close.iloc[-2]) * 100
                
                # Alpha (Fark): Hisse %3 arttı, Endeks %1 arttıysa -> Alpha +2 (Güçlü)
                alpha_val = stock_chg - bench_chg
        except:
            pass
        # ======================================================
        # 9. GELİŞMİŞ HACİM ANALİZİ (SMART VOLUME)
        # ======================================================
        std_v_20 = float(v.rolling(20).std().iloc[-1])
        c_std = std_v_20 if std_v_20 > 0 else 1.0
        rvol = c1_v / avg_v if avg_v > 0 else 1.0
        
        # Stopping Volume: Fiyat dipteyken gelen devasa karşılayıcı hacim
        stop_vol_msg = "Yok"
        if c1_v > (avg_v * 1.5) and body < (total_len * 0.3) and l_wick > (total_len * 0.5):
            stop_vol_msg = "VAR 🔥 (Dipten kurumsal toplama emaresi!)"

        # Climax Volume: Trend sonunda gelen aşırı şişkin hacim
        climax_msg = "Yok"
        ema20_val = c.ewm(span=20).mean().iloc[-1]
        price_dist_ema20 = (c1_c / ema20_val) - 1
        if c1_v == v.tail(50).max() and price_dist_ema20 > 0.10:
            climax_msg = "VAR ⚠️ (Trend sonu tahliye/FOMO riski!)"

        # ======================================================
        # 10. HACİM DELTASI VE POC İLİŞKİSİ (YENİ FORMAT + YÜZDE)
        # ======================================================
        son_mum = df.iloc[-1]
        onceki_mum = df.iloc[-2]
        delta_val = son_mum['Volume_Delta']
        fiyat = son_mum['Close']
        toplam_hacim = son_mum['Volume']
        
        # Fiyat ile POC Yüzde farkı hesaplama
        fark_yuzde = abs((fiyat - poc_price) / poc_price) * 100
        
        # DELTA GÜCÜ (Baskınlık Yüzdesi) Hesaplama
        if toplam_hacim > 0:
            delta_gucu_yuzde = abs((delta_val / toplam_hacim) * 100)
        else:
            delta_gucu_yuzde = 0
        
        # Başlığı hazırlama
        if fiyat > poc_price:
            delta_title = "✅ Point of Control ÜZERİNDE"
            yon_metni = "üzerinde"
        else:
            delta_title = "⚠️ Point of Control ALTINDA"
            yon_metni = "altında"
            
        # Uyumsuzluk (Divergence) Kontrolü - Hacim Şiddeti Filtreli
        if fiyat > onceki_mum['Close'] and delta_val < 0:
            if delta_gucu_yuzde >= 60.0:
                delta_title += " (🚨 Gizli Satış)"
            elif delta_gucu_yuzde >= 55.0:
                delta_title += " (🟠 Zayıf Gizli Satış - Teyit Bekliyor)"
            else:
                delta_title += " (⚪ Fiyat/Hacim Gürültüsü - Dikkate Alma)"
                
        elif fiyat < onceki_mum['Close'] and delta_val > 0:
            if delta_gucu_yuzde >= 60.0:
                delta_title += " (🟢 Gizli Alım)"
            elif delta_gucu_yuzde >= 55.0:
                delta_title += " (🟠 Zayıf Gizli Alım - Teyit Bekliyor)"
            else:
                delta_title += " (⚪ Fiyat/Hacim Gürültüsü - Dikkate Alma)"
            
        # İstediğin formatta Edu-Note Açıklaması
        delta_desc = f"Fiyat son 20 mumun hacim merkezi (yani alıcı ve satıcıların en çok işlem yaptığı yer) olan <b>{poc_price:.2f}</b>, %{fark_yuzde:.2f} {yon_metni}."

        return {
            "candle": {"title": candle_title, "desc": candle_desc},
            "sfp": {"title": sfp_txt, "desc": sfp_desc},
            "vol": {"title": vol_txt, "desc": vol_desc},
            "loc": {"title": loc_txt, "desc": loc_desc},
            "sq": {"title": sq_txt, "desc": sq_desc},
            "obv": obv_data,
            "div": {"title": div_txt, "desc": div_desc, "type": div_type},
            "vwap": {"val": vwap_now, "diff": vwap_diff},
            "rs": {"alpha": alpha_val},
            "smart_volume": {
                "title": delta_title, 
                "desc": delta_desc, 
                "poc": poc_price, 
                "delta": delta_val, 
                "delta_yuzde": delta_gucu_yuzde,
                "rvol": round(rvol, 2),      
                "stopping": stop_vol_msg,    
                "climax": climax_msg         
            }
        }
    except Exception: return None

def render_golden_trio_banner(ict_data, sent_data):
    if not ict_data or not sent_data: return

    # --- 1. MANTIK KONTROLÜ ---
    # GÜÇ: Sentiment puanı 55 üstü veya 'Lider/Artıda' ibaresi var mı?
    rs_text = sent_data.get('rs', '').lower()
    cond_power = ("artıda" in rs_text or "lider" in rs_text or "pozitif" in rs_text or 
              sent_data.get('total', 0) >= 50 or sent_data.get('raw_rsi', 0) > 50)
    
    # KONUM: ICT analizinde 'Discount' bölgesinde mi?
    # Discount bölgesinde değilse bile, eğer dönüş sinyali (BOS/MSS) varsa konumu onayla
    cond_loc = "DISCOUNT" in ict_data.get('zone', '') or "MSS" in ict_data.get('structure', '') or "BOS" in ict_data.get('structure', '')
    
    # ENERJİ: ICT analizinde 'Güçlü' enerji var mı?
    # Displacement yoksa bile Hacim puanı iyiyse veya RSI ivmeliyse (55+) enerjiyi onayla
    cond_energy = ("Güçlü" in ict_data.get('displacement', '') or 
                "Hacim" in sent_data.get('vol', '') or 
                sent_data.get('raw_rsi', 0) > 55)

    # --- 2. FİLTRE (YA HEP YA HİÇ) ---
    # Eğer 3 şartın hepsi sağlanmıyorsa, fonksiyonu burada bitir (Ekrana hiçbir şey basma).
    if not (cond_power and cond_loc and cond_energy):
        return

    # --- 3. HTML ÇIKTISI (SADECE 3/3 İSE BURASI ÇALIŞIR) ---
    bg = "linear-gradient(90deg, #ca8a04 0%, #eab308 100%)" # Altın Sarısı
    border = "#a16207"
    txt = "#ffffff"
    
    st.markdown(f"""<div style="background:{bg}; border:1px solid {border}; border-radius:8px; padding:12px; margin-bottom:15px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
<div style="display:flex; justify-content:space-between; align-items:center;">
<div style="display:flex; align-items:center; gap:10px;">
<span style="font-size:1.6rem;">🏆</span>
<div style="line-height:1.2;">
<div style="font-weight:800; color:{txt}; font-size:1rem; letter-spacing:0.5px;">ALTIN FIRSAT (GOLDEN TRIO)</div>
<div style="font-size:0.75rem; color:{txt}; opacity:0.95;">RS Gücü + Ucuz Konum + Güçlü Enerji (ICT): Mükemmel Uyum.</div>
</div>
</div>
<div style="font-family:'JetBrains Mono'; font-weight:800; font-size:1.2rem; color:{txt}; background:rgba(255,255,255,0.25); padding:4px 10px; border-radius:6px;">3/3</div>
</div>
</div>""", unsafe_allow_html=True)

# --- ROYAL FLUSH HESAPLAYICI ---
def render_royal_flush_banner(ict_data, sent_data, ticker):
    if not ict_data or not sent_data: return

    # --- KRİTER 1: YAPI (ICT) ---
    # BOS veya MSS (Bullish) olmalı
    cond_struct = "BOS (Yükseliş" in ict_data.get('structure', '') or "MSS (Market Structure Shift) 🐂" in ict_data.get('structure', '')
    
    # --- KRİTER 2: ZEKA (LORENTZIAN AI) ---
    # 7/8 veya 8/8 Yükseliş olmalı
    lor_data = calculate_lorentzian_classification(ticker)
    cond_ai = False
    votes_txt = "0/8"
    if lor_data and lor_data['signal'] == "YÜKSELİŞ" and lor_data['votes'] >= 7:
        cond_ai = True
        votes_txt = f"{lor_data['votes']}/8"

    # --- KRİTER 3: GÜÇ (RS MOMENTUM) ---
    # Alpha pozitif olmalı
    alpha_val = 0
    pa_data = calculate_price_action_dna(ticker)
    if pa_data:
        alpha_val = pa_data.get('rs', {}).get('alpha', 0)
    cond_rs = alpha_val > 0

    # --- KRİTER 4: MALİYET (VWAP) ---
    # Ralli modu veya Ucuz olmalı (Parabolik olmamalı)
    v_diff = pa_data.get('vwap', {}).get('diff', 0) if pa_data else 0
    cond_vwap = v_diff < 12 # %12'den fazla sapmamış (Aşırı şişmemiş) olmalı

    # --- FİLTRE (YA HEP YA HİÇ - 4/4) ---
    if not (cond_struct and cond_ai and cond_rs and cond_vwap):
        return

    # --- HTML ÇIKTISI ---
    bg = "linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%)" # Kraliyet Mavisi
    border = "#1e40af"
    txt = "#ffffff"
    
    st.markdown(f"""<div style="background:{bg}; border:1px solid {border}; border-radius:8px; padding:12px; margin-top:5px; margin-bottom:15px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);">
<div style="display:flex; justify-content:space-between; align-items:center;">
<div style="display:flex; align-items:center; gap:10px;">
<span style="font-size:1.6rem;">♠️</span>
<div style="line-height:1.2;">
<div style="font-weight:800; color:{txt}; font-size:1rem; letter-spacing:0.5px;">ROYAL FLUSH (KRALİYET SET-UP)</div>
<div style="font-size:0.75rem; color:{txt}; opacity:0.95;">AI ({votes_txt}) + ICT Yapı + RS Liderliği + VWAP Uyumu: En Yüksek Olasılık.</div>
</div>
</div>
<div style="font-family:'JetBrains Mono'; font-weight:800; font-size:1.2rem; color:{txt}; background:rgba(255,255,255,0.25); padding:4px 10px; border-radius:6px;">4/4</div>
</div>
</div>""", unsafe_allow_html=True)

# --- SUPERTREND VE FIBONACCI HESAPLAYICI ---
def calculate_supertrend(df, period=10, multiplier=3.0):
    """
    SuperTrend indikatörünü hesaplar.
    Dönüş: (SuperTrend Değeri, Trend Yönü [1: Boğa, -1: Ayı])
    """
    try:
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        # ATR Hesaplama
        tr1 = pd.DataFrame(high - low)
        tr2 = pd.DataFrame(abs(high - close.shift(1)))
        tr3 = pd.DataFrame(abs(low - close.shift(1)))
        frames = [tr1, tr2, tr3]
        tr = pd.concat(frames, axis=1, join='inner').max(axis=1)
        atr = tr.ewm(alpha=1/period, adjust=False).mean()

        # Temel Bantlar
        hl2 = (high + low) / 2
        final_upperband = hl2 + (multiplier * atr)
        final_lowerband = hl2 - (multiplier * atr)
        
        supertrend = [True] * len(df) # Başlangıç (True = Boğa varsayımı)
        st_value = [0.0] * len(df)
        
        # Döngüsel Hesaplama (SuperTrend doğası gereği önceki değere bakar)
        for i in range(1, len(df.index)):
            curr, prev = i, i-1
            
            # Üst Bant Mantığı
            if close.iloc[curr] > final_upperband.iloc[prev]:
                supertrend[curr] = True
            elif close.iloc[curr] < final_lowerband.iloc[prev]:
                supertrend[curr] = False
            else:
                supertrend[curr] = supertrend[prev]
                
                # Bantları Daraltma (Trailing Stop Mantığı)
                if supertrend[curr] == True and final_lowerband.iloc[curr] < final_lowerband.iloc[prev]:
                    final_lowerband.iloc[curr] = final_lowerband.iloc[prev]
                
                if supertrend[curr] == False and final_upperband.iloc[curr] > final_upperband.iloc[prev]:
                    final_upperband.iloc[curr] = final_upperband.iloc[prev]

            if supertrend[curr] == True:
                st_value[curr] = final_lowerband.iloc[curr]
            else:
                st_value[curr] = final_upperband.iloc[curr]
                
        return st_value[-1], (1 if supertrend[-1] else -1)
        
    except Exception:
        return 0, 0

# --- YENİ KOD: Dinamik Makro Döngü Fibonacci Motoru ---
def calculate_fib_levels(df, st_dir=1, period=144):
    """
    Dinamik Makro Döngü (Macro Cycle) Fibonacci Hesaplama
    Trend yönüne göre anlık sekmeleri değil, GEÇMİŞ MAKRO DALGAYI referans alır.
    """
    try:
        if len(df) < period: period = len(df)
        recent_data = df.tail(period)
        
        max_h = recent_data['High'].max()
        min_l = recent_data['Low'].min()
        diff = max_h - min_l
        
        # Trend yönü doğrudan SuperTrend'den alınır.
        is_uptrend = (st_dir == 1)
        
        levels = {}
        
        if is_uptrend:
            # YÜKSELİŞ SENARYOSU: Geçmiş makro düşüşü ölçüyoruz.
            # (Tepeden Dibe Çekilen Fibonacci) 
            # 0 noktası Dipte. Fiyat dipten yukarı çıkarken Premium dirençleri test eder.
            levels = {
                "-0.618 (Hedef)": max_h + (diff * 0.618),
                "-0.236 (Kırılım Hedefi)": max_h + (diff * 0.236),
                "1 (Tepe)": max_h,
                "0.618 (Golden - Satış)": min_l + (diff * 0.618), # OTE Direnci (Akıllı Para Short)
                "0.5 (Orta)": min_l + (diff * 0.5),
                "0.382": min_l + (diff * 0.382),
                "0.236": min_l + (diff * 0.236),
                "0 (Dip)": min_l
            }
        else:
            # DÜŞÜŞ SENARYOSU: Geçmiş makro yükselişi ölçüyoruz.
            # (Dipten Tepeye Çekilen Fibonacci)
            # 0 noktası Tepede. Fiyat zirveden aşağı düşerken Discount destekleri test eder.
            levels = {
                "0 (Tepe)": max_h,
                "0.236": max_h - (diff * 0.236),
                "0.382": max_h - (diff * 0.382),
                "0.5 (Orta)": max_h - (diff * 0.5),
                "0.618 (Golden - Alım)": max_h - (diff * 0.618), # Makro Destek (11764 - Akıllı Para Long)
                "1 (Dip)": min_l,
                "1.236 (Kırılım Hedefi)": min_l - (diff * 0.236),
                "1.618 (Hedef)": min_l - (diff * 0.618)
            }
            
        return levels
    except:
        return {}
    
def calculate_z_score_live(df, period=20):
    try:
        if len(df) < period: return 0
        
        # Son 20 barı al
        recent = df.tail(period)
        
        # Ortalama ve Standart Sapma
        mean = recent['Close'].mean()
        std = recent['Close'].std()
        
        if std == 0: return 0
        
        # Son fiyat
        last_close = df['Close'].iloc[-1]
        
        # Z-Score Formülü
        z_score = (last_close - mean) / std
        
        return z_score
    except:
        return 0

@st.cache_data(ttl=600)
def get_advanced_levels_data(ticker):
    """
    Arayüz için verileri paketler. (GÜNCELLENMİŞ: Buffer ve 1.236 Mantığı)
    """
    df = get_safe_historical_data(ticker, period="1y")
    if df is None: return None
    
    # 1. SuperTrend
    st_val, st_dir = calculate_supertrend(df)
    
    # 2. Fibonacci (DÜZELTME: st_dir pusulası motora gönderildi)
    fibs = calculate_fib_levels(df, st_dir=st_dir, period=120)
    
    curr_price = float(df['Close'].iloc[-1])
    
    # En yakın destek ve direnci bulma
    sorted_fibs = sorted(fibs.items(), key=lambda x: float(x[1]))
    support = (None, -999999)
    resistance = (None, 999999)
    
    # TAMPON BÖLGE (BUFFER) - Binde 2
    # Fiyat dirence %0.2 kadar yaklaştıysa veya geçtiyse, o direnci "GEÇİLDİ" say.
    buffer = 0.002 
    
    for label, val in sorted_fibs:
        # Destek: Fiyatın altında kalan en büyük değer
        if val < curr_price and val > support[1]:
            support = (label, val)
            
        # Direnç: Fiyatın (ve tamponun) üzerinde kalan en küçük değer
        # MANTIK: Eğer Fiyat > Zirve ise, Zirve elenir, sıradaki "1.236 (Kırılım Hedefi)" seçilir.
        if val > (curr_price * (1 + buffer)) and val < resistance[1]:
            resistance = (label, val)
            
    if resistance[1] == 999999:
        resistance = ("UZAY BOŞLUĞU 🚀", curr_price * 1.15) 

    return {
        "st_val": st_val,
        "st_dir": st_dir,
        "fibs": fibs,
        "nearest_sup": support,
        "nearest_res": resistance,
        "curr_price": curr_price
    }
# ==============================================================================
# 🧠 GRANDMASTER MATRİSİ V8.0 (MERCAN KORUMALI & 60 GÜN HAFIZALI)
# ==============================================================================
def calculate_grandmaster_score_single(symbol, df, bench_series, fast_mode=False):
    """
    V8.0: Patron'un 'Mercan' tespiti üzerine revize edildi.
    1. ICT Referansı: Son 252 Gün (Yıllık) zirve/dip baz alınır.
    2. Tazelik Testi: Son 60 Gün (3 Ay) içinde Discount gören hisseye ceza kesilmez.
    """
    try:
        if df is None or len(df) < 100: return None
        
        # Son veriler
        close = df['Close']
        curr_price = float(close.iloc[-1])
        curr_vol = float(df['Volume'].iloc[-1])
        avg_vol = float(df['Volume'].rolling(20).mean().iloc[-1])
        vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 0
        
        z_score = calculate_z_score_live(df)
        is_squeezed = check_lazybear_squeeze(df)
        
        # --- PUANLAMA MOTORU ---
        raw_score = 0
        story_tags = [] 
        penalty_log = []
        ai_power = 0 

        # 1. LORENTZIAN (AI)
        if not fast_mode:
            try:
                lor_data = calculate_lorentzian_classification(symbol) 
                if lor_data:
                    votes = lor_data['votes']
                    signal = lor_data['signal']
                    if signal == "YÜKSELİŞ":
                        if votes == 8: 
                            raw_score += 40
                            ai_power = 2
                            story_tags.append("🧠 Lorentzian: 8/8")
                        elif votes >= 7: 
                            raw_score += 30
                            ai_power = 1
                            story_tags.append("🧠 Lorentzian: 7/8")
                    elif signal == "DÜŞÜŞ":
                        raw_score = -999 
            except: pass

        # 2. HACİM
        if vol_ratio >= 2.5: 
            raw_score += 20
            story_tags.append("⛽ Hacim Artışı 2.5x")
        elif vol_ratio >= 1.5: 
            raw_score += 10
            story_tags.append("⛽ Hacim Artışı 1.5x")
        
        # 3. SIKIŞMA
        if is_squeezed:
            raw_score += 15
            story_tags.append("📐 Sıkışma Halinde")

        # 4. ICT KONUMU (MACRO ANALİZ & 60 GÜN HAFIZA)
        # ---------------------------------------------------------
        # A. Yıllık Range Hesabı (Macro Bakış)
        lookback_period = min(252, len(df))
        macro_high = df['High'].tail(lookback_period).max()
        macro_low = df['Low'].tail(lookback_period).min()
        
        if macro_high > macro_low:
            range_diff = macro_high - macro_low
            fib_50 = macro_low + (range_diff * 0.5)
            fib_premium_start = macro_low + (range_diff * 0.75) # Çok pahalı bölge
            
            # B. Mevcut Konum
            is_currently_premium = curr_price > fib_50
            
            # C. 60 Günlük Hafıza Testi (Patron Kuralı)
            # Son 60 gün içinde fiyatın %50 seviyesinin altına inip inmediğine bakıyoruz.
            recent_lookback = min(60, len(df))
            recent_lows = df['Low'].tail(recent_lookback)
            was_recently_discount = (recent_lows < fib_50).any()
            
            # --- KARAR MEKANİZMASI ---
            if not is_currently_premium:
                # Şu an zaten ucuzsa (Discount) ödül ver
                raw_score += 15
                story_tags.append("🦅 ICT: Ucuzluk Bölgesinde")
            
            else:
                # Şu an PAHALI (Premium) görünüyor.
                # Ama geçmiş 60 günde ucuzladıysa veya AI çok güçlüyse CEZA KESME.
                if was_recently_discount or ai_power > 0:
                    # Ceza yok. Bu hareket 'Mal Toplama' sonrası kırılımdır.
                    pass
                else:
                    # Hem pahalı, hem son 3 aydır hiç ucuzlamamış, hem AI zayıf.
                    # İşte bu gerçek pahalıdır. Vur kırbacı.
                    raw_score -= 25
                    penalty_log.append("ICT:Premium(Şişkin)")
        # ---------------------------------------------------------

        # 5. TEKNİK & LİDERLİK
        if -2.5 <= z_score <= -1.5:
            raw_score += 10
            story_tags.append(f"💎 Dip (Z:{z_score:.2f})")
        
        # Alpha Hesabı
        if bench_series is not None:
             try:
                stock_5d = (close.iloc[-1] / close.iloc[-6]) - 1
                common_idx = close.index.intersection(bench_series.index)
                if len(common_idx) > 5:
                    b_aligned = bench_series.loc[common_idx]
                    bench_5d = (b_aligned.iloc[-1] / b_aligned.iloc[-6]) - 1
                    alpha_val = (stock_5d - bench_5d) * 100
                    if alpha_val > 3.0:
                        raw_score += 5
                        story_tags.append(f"🚀 Alpha Lideri")
             except: pass

        # --- EMNİYET SİBOBU ---
        if z_score > 3.0: 
            raw_score = -100 
            penalty_log.append("Aşırı Şişkin")

        # RSI Kontrolü
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain/loss))).iloc[-1]
        
        if rsi > 85: # Toleransı biraz artırdım (80->85) çünkü boğa piyasası
            raw_score -= 10
            penalty_log.append("RSI>85")
            
        story_text = " | ".join(story_tags[:3]) if story_tags else "İzleme Listesi"

        return {
            "Sembol": symbol,
            "Skor": int(raw_score),
            "Fiyat": curr_price,
            "Hacim_Kat": round(vol_ratio, 1),
            "Z_Score": round(z_score, 2),
            "Hikaye": story_text,
            "RS Gücü": round(alpha_val, 1),
            "Uyarılar": ", ".join(penalty_log) if penalty_log else "Temiz"
        }

    except Exception: return None

@st.cache_data(ttl=900)
def scan_grandmaster_batch(asset_list):
    """
    GRANDMASTER TARAMA MOTORU (V6):
    - 40 Puan altı hisseler kesinlikle listeye giremez.
    """
    # 1. TOPLU VERİ ÇEK (Hızlı)
    data = get_batch_data_cached(asset_list, period="1y") 
    if data.empty: return pd.DataFrame()
    
    cat = st.session_state.get('category', 'S&P 500')
    bench_ticker = "XU100.IS" if "BIST" in cat else "^GSPC"
    bench_df = get_safe_historical_data(bench_ticker, period="1y")
    bench_series = bench_df['Close'] if bench_df is not None else None

    candidates = []
    stock_dfs = []
    
    for symbol in asset_list:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if symbol in data.columns.levels[0]: stock_dfs.append((symbol, data[symbol]))
            else:
                if len(asset_list) == 1: stock_dfs.append((symbol, data))
        except: continue

    # --- AŞAMA 1: HIZLI ÖN ELEME ---
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(calculate_grandmaster_score_single, sym, df, bench_series, True) for sym, df in stock_dfs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            # Baraj: Ön elemede 25 puanı geçmeli
            if res and res['Skor'] >= 25: 
                candidates.append(res['Sembol'])

    # --- AŞAMA 2: DERİN ANALİZ (Lorentzian Devrede) ---
    final_results = []
    df_dict = {sym: df for sym, df in stock_dfs}

    for sym in candidates:
        if sym in df_dict:
            final_res = calculate_grandmaster_score_single(sym, df_dict[sym], bench_series, False)
            # FİNAL BARAJI: Patron Emri -> 40 Puanın altı listeye giremez.
            if final_res and final_res['Skor'] >= 40:
                final_results.append(final_res)
    
    if final_results:
        df_final = pd.DataFrame(final_results)
        return df_final.sort_values(by="Skor", ascending=False).head(10)
        
    return pd.DataFrame()

# ==============================================================================
# 4. GÖRSELLEŞTİRME FONKSİYONLARI (EKSİK OLAN KISIM)
# ==============================================================================
def render_gauge_chart(score):
    """Ana Skor için Hız Göstergesi (Kompakt & Renkli & Lacivert Yazılı)"""
    score = int(score)
    
    # Renk Belirleme
    color = "#b91c1c" 
    if score >= 50: color = "#d97706" 
    if score >= 70: color = "#16a34a" 
    if score >= 85: color = "#15803d" 
    
    source = pd.DataFrame({"category": ["Skor", "Kalan"], "value": [score, 100-score]})
    
    base = alt.Chart(source).encode(
        theta=alt.Theta("value", stack=True)
    )
    
    # Yarıçapları biraz kıstım (Sığdırmak için)
    pie = base.mark_arc(outerRadius=55, innerRadius=40).encode(
        color=alt.Color("category", scale=alt.Scale(domain=["Skor", "Kalan"], range=[color, "#e2e8f0"]), legend=None),
        order=alt.Order("category", sort="descending"),
        tooltip=["value"]
    )
    
    # Ortadaki Sayı
    text = base.mark_text(radius=0, size=28, color=color, fontWeight="bold", dy=-5).encode(
        text=alt.value(f"{score}")
    )
    
    # Altındaki Etiket (KOYU LACİVERT ve BÜYÜK)
    label = base.mark_text(radius=0, size=12, color="#1e3a8a", fontWeight="bold", dy=20).encode(
        text=alt.value("ANA SKOR")
    )
    
    # Yüksekliği 130px'e çektim (Daha kompakt)
    chart = (pie + text + label).properties(height=130) 
    
    st.altair_chart(chart, use_container_width=True)

def render_sentiment_card(sent):
    if not sent: return
    display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")
    
    score = sent['total']
    # Renk ve İkon Belirleme
    if score >= 70: 
        color = "#16a34a"; icon = "🔥"; status = "GÜÇLÜ BOĞA"; bg_tone = "#f0fdf4"; border_tone = "#bbf7d0"
    elif score >= 50: 
        color = "#d97706"; icon = "↔️"; status = "NÖTR / POZİTİF"; bg_tone = "#fffbeb"; border_tone = "#fde68a"
    elif score >= 30: 
        color = "#b91c1c"; icon = "🐻"; status = "ZAYIF / AYI"; bg_tone = "#fef2f2"; border_tone = "#fecaca"
    else: 
        color = "#7f1d1d"; icon = "❄️"; status = "ÇÖKÜŞ"; bg_tone = "#fef2f2"; border_tone = "#fecaca"
    
    # Etiketler
    p_label = '25p' if sent.get('is_index', False) else '20p'
    rs_label = 'Devre Dışı' if sent.get('is_index', False) else '15p'

    # --- KART OLUŞTURUCU (SOLA YASLI - HATA VERMEZ) ---
    def make_card(num, title, score_lbl, val, desc, emo):
        # DİKKAT: Aşağıdaki HTML kodları bilerek en sola yaslanmıştır.
        return f"""<div style="border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 8px; background: white; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
<div style="background: #f8fafc; padding: 8px 12px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
<div style="display:flex; align-items:center; gap:6px;">
<span style="background:{color}; color:white; width:20px; height:20px; border-radius:50%; display:flex; justify-content:center; align-items:center; font-size:0.7rem; font-weight:bold;">{num}</span>
<span style="font-weight: 700; color: #334155; font-size: 0.8rem;">{title} <span style="color:#94a3b8; font-weight:400; font-size:0.7rem;">({score_lbl})</span></span>
</div>
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; font-weight: 700; color: #0f172a;">{val}</div>
</div>
<div style="padding: 10px; font-size: 0.85rem; color: #1e3a8a; line-height: 1.4; background: #ffffff;">
<span style="color:{color}; font-size:1rem; float:left; margin-right:6px; line-height:1;">{emo}</span>
{desc}
</div>
</div>"""

    # --- KARTLARI OLUŞTUR ---
    cards_html = ""
    cards_html += make_card("1", "YAPI", p_label, sent['str'], "Market Yapısı- Son 20 günün %97-100 zirvesinde (12). Son 5 günün en düşük seviyesi, önceki 20 günün en düşük seviyesinden yukarıdaysa: HL (8)", "🏗️")
    cards_html += make_card("2", "TREND", p_label, sent['tr'], "Ortalamalara bakar. Hisse fiyatı SMA200 üstünde (8). EMA20 üstünde (8). Kısa vadeli ortalama, orta vadeli ortalamanın üzerinde, yani EMA20 > SMA50 (4)", "📈")
    cards_html += make_card("3", "HACİM", p_label, sent['vol'], "Hacmin 20G ortalamaya oranını ve On-Balance Volume (OBV) denetler. Bugünün hacmi son 20G ort.üstünde (12) Para girişi var: 10G ortalamanın üstünde (8)", "🌊")
    cards_html += make_card("4", "MOMENTUM", "15p", sent['mom'], "RSI ve MACD ile itki gücünü ölçer. 50 üstü RSI (5) RSI ivmesi artıyor (5). MACD sinyal çizgisi üstünde (5)", "🚀")
    cards_html += make_card("5", "SIKIŞMA", "10p", sent['vola'], "Bollinger Bant genişliğini inceler. Bant genişliği son 20G ortalamasından dar (10)", "📐")
    cards_html += make_card("6", "GÜÇ", rs_label, sent['rs'], "Hissenin Endekse göre relatif gücünü (RS) ölçer. Mansfield RS göstergesi 0'ın üzerinde (5). RS trendi son 5 güne göre yükselişte (5). Endeks düşerken hisse artıda (Alpha) (5)", "💪")

    # --- ANA HTML (SOLA YASLI) ---
    final_html = f"""<div class="info-card" style="border-top: 3px solid {color}; background-color: #f8fafc; padding-bottom: 2px;">
<div class="info-header" style="color:#1e3a8a; display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
<span>🐦 Smart Money Sentiment: {display_ticker}</span>
<span style="font-family:'JetBrains Mono'; font-weight:800; font-size:1.1rem; color:{color}; background:{color}15; padding:2px 8px; border-radius:6px;">{score}/100</span>
</div>
<div style="background:{bg_tone}; border:1px solid {border_tone}; border-radius:6px; padding:8px; text-align:center; margin-bottom:12px;">
<div style="font-weight:800; color:{color}; font-size:0.9rem; letter-spacing:0.5px;">{icon} {status}</div>
<div style="font-size:0.65rem; color:#64748b; margin-top:2px; font-family: monospace;">{sent['bar']}</div>
</div>
<div style="display:flex; flex-direction:column; gap:2px;">
{cards_html}
</div>
</div>"""
    
    st.markdown(final_html, unsafe_allow_html=True)

def render_deep_xray_card(xray):
    if not xray: return
    
    display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")
    
    html_icerik = f"""
    <div class="info-card">
        <div class="info-header">🔍 Derin Teknik Röntgen: {display_ticker}</div>
        
        <div class="info-row">
            <div class="label-long">1. Momentum:</div>
            <div class="info-val">{xray['mom_rsi']} | {xray['mom_macd']}</div>
        </div>
        <div class="edu-note">RSI 50 üstü ve MACD pozitif bölgedeyse ivme alıcıların kontrolündedir. RSI 50 üstünde? MACD 0'dan büyük?</div>

        <div class="info-row">
            <div class="label-long">2. Hacim Akışı:</div>
            <div class="info-val">{xray['vol_obv']}</div>
        </div>
        <div class="edu-note">Para girişinin (OBV) fiyat hareketini destekleyip desteklemediğini ölçer. OBV, 5 günlük ortalamasının üzerinde?</div>

        <div class="info-row">
            <div class="label-long">3. Trend Sağlığı:</div>
            <div class="info-val">{xray['tr_ema']} | {xray['tr_adx']}</div>
        </div>
        <div class="edu-note">Fiyatın EMA50 ve EMA200 üzerindeki kalıcılığını ve trendin gücünü denetler. 1. EMA50 EMA200'ü yukarı kesmiş? 2. Zaten üstünde?</div>

        <div class="info-row">
            <div class="label-long">4. Volatilite:</div>
            <div class="info-val">{xray['vola_bb']}</div>
        </div>
        <div class="edu-note">Bollinger Bantlarındaki daralma, yakında bir patlama olabileceğini gösterir. Fiyat üst bandı yukarı kırdı?</div>

        <div class="info-row">
            <div class="label-long">5. Piyasa Yapısı:</div>
            <div class="info-val">{xray['str_bos']}</div>
        </div>
        <div class="edu-note">Kritik direnç seviyelerinin kalıcı olarak aşılması (BOS) yükselişin devamı için şarttır. Fiyat son 20 günün en yüksek seviyesini aştı?</div>
    </div>
    """.replace("\n", "")
    
    st.markdown(html_icerik, unsafe_allow_html=True)
    
def render_detail_card_advanced(ticker):
    ACIKLAMALAR = {
        "Squeeze": "🚀 Squeeze: Bollinger Bant genişliği son 60 günün en dar aralığında (Patlama Hazır)",
        "Trend": "⚡ Trend: EMA5 > EMA20 üzerinde (Yükseliyor)",
        "MACD": "🟢 MACD: Histogram bir önceki günden yüksek (Momentum Artışı Var)",
        "Hacim": "🔊 Hacim: Son 5 günlük hacim ortalama hacmin %20 üzerinde",
        "Breakout": "🔨 Breakout: Fiyat son 20 gün zirvesinin %98 veya üzerinde",
        "RSI Güçlü": "⚓ RSI Güçlü: 30-65 arasında ve artışta",
        "Hacim Patlaması": "💥 Hacim son 20 gün ortalamanın %30 üzerinde seyrediyor",
        "RS (S&P500)": "💪 Hisse, Endeksten daha güçlü",
        "Boğa Trendi": "🐂 Boğa Trendi: Fiyat Üç Ortalamanın da (SMA50 > SMA100 > SMA200) üzerinde",
        "60G Zirve": "⛰️ Zirve: Fiyat son 60 günün tepesine %97 yakınlıkta",
        "RSI Bölgesi": "🎯 RSI Uygun: Pullback için uygun (40-55 arası)",
        "Ichimoku": "☁️ Ichimoku: Fiyat Bulutun Üzerinde (Trend Pozitif)",
        "RS": "💪 Relatif Güç (RS)",
        "Setup": "🛠️ Setup Durumu",
        "ADX Durumu": "💪 ADX Trend Gücü"
    }

    display_ticker = ticker.replace(".IS", "").replace("=F", "")
    dt = get_tech_card_data(ticker)
    info = fetch_stock_info(ticker)
    
    price_val = f"{info['price']:.2f}" if info else "Veri Yok"
    ma_vals = f"SMA50: {dt['sma50']:.0f} | SMA200: {dt['sma200']:.0f}" if dt else ""
    stop_vals = f"{dt['stop_level']:.2f} (Risk: %{dt['risk_pct']:.1f})" if dt else ""

    # RADAR 1 VERİSİ
    r1_res = {}; r1_score = 0
    if st.session_state.scan_data is not None:
        row = st.session_state.scan_data[st.session_state.scan_data["Sembol"] == ticker]
        if not row.empty and "Detaylar" in row.columns: r1_res = row.iloc[0]["Detaylar"]; r1_score = row.iloc[0]["Skor"]
    if not r1_res:
        temp_df = analyze_market_intelligence([ticker])
        if not temp_df.empty and "Detaylar" in temp_df.columns: r1_res = temp_df.iloc[0]["Detaylar"]; r1_score = temp_df.iloc[0]["Skor"]

    # RADAR 2 VERİSİ
    r2_res = {}; r2_score = 0
    if st.session_state.radar2_data is not None:
        if "Sembol" not in st.session_state.radar2_data.columns:
            st.session_state.radar2_data = st.session_state.radar2_data.reset_index()
            st.session_state.radar2_data.rename(columns={'index': 'Sembol', 'Symbol': 'Sembol', 'Ticker': 'Sembol'}, inplace=True)
        row = st.session_state.radar2_data[st.session_state.radar2_data["Sembol"] == ticker]
        if not row.empty and "Detaylar" in row.columns: r2_res = row.iloc[0]["Detaylar"]; r2_score = row.iloc[0]["Skor"]
    if not r2_res:
        temp_df2 = radar2_scan([ticker])
        if not temp_df2.empty and "Detaylar" in temp_df2.columns: r2_res = temp_df2.iloc[0]["Detaylar"]; r2_score = temp_df2.iloc[0]["Skor"]

    r1_suffix = ""
    if r1_score < 2: r1_suffix = " <span style='color:#dc2626; font-weight:500; background:#fef2f2; padding:1px 4px; border-radius:3px; margin-left:5px; font-size:0.7rem;'>(⛔ RİSKLİ)</span>"
    elif r1_score > 5: r1_suffix = " <span style='color:#16a34a; font-weight:500; background:#f0fdf4; padding:1px 4px; border-radius:3px; margin-left:5px; font-size:0.7rem;'>(🚀 GÜÇLÜ)</span>"

    def get_icon(val): return "✅" if val else "❌"

    # RADAR 1 HTML (FİLTRELİ)
    r1_html = ""
    for k, v in r1_res.items():
        if k in ACIKLAMALAR: 
            text = ACIKLAMALAR.get(k, k); is_valid = v
            if isinstance(v, (tuple, list)): 
                is_valid = v[0]; val_num = v[1]
                if k == "RSI Güçlü":
                    if is_valid:
                        # 30-65 arası ve yükseliyorsa
                        text = f"⚓ RSI Güçlü/İvmeli: ({int(val_num)})"
                    else:
                        # Eğer çarpı yemişse sebebini yazalım
                        if val_num >= 65:
                            text = f"🔥 RSI Şişkin (Riskli Olabilir): ({int(val_num)})"
                        elif val_num <= 30:
                            text = f"❄️ RSI Zayıf (Dipte): ({int(val_num)})"
                        else:
                            text = f"📉 RSI İvme Kaybı: ({int(val_num)})"
                elif k == "ADX Durumu": text = f"💪 ADX Güçlü: {int(val_num)}" if is_valid else f"⚠️ ADX Zayıf: {int(val_num)}"
            r1_html += f"<div class='tech-item' style='margin-bottom:2px;'>{get_icon(is_valid)} <span style='margin-left:4px;'>{text}</span></div>"

    # RADAR 2 HTML (FİLTRELİ ve DÜZELTİLMİŞ)
    r2_html = ""
    for k, v in r2_res.items():
        if k in ACIKLAMALAR:
            text = ACIKLAMALAR.get(k, k); is_valid = v
            
            if isinstance(v, (tuple, list)): 
                is_valid = v[0]; val_num = v[1]
                if k == "RSI Bölgesi": 
                    if is_valid:
                        text = f"🎯 RSI Uygun: ({int(val_num)})"
                    else:
                        # Eğer geçerli değilse nedenini yazalım
                        if val_num > 65:
                            text = f"🔥 RSI Şişkin (Riskli Olabilir): ({int(val_num)})"
                        else:
                            text = f"❄️ RSI Zayıf: ({int(val_num)})"

            # Ichimoku Özel Kontrolü (Gerekirse)
            if k == "Ichimoku":
                # Eğer özel bir şey yapmak istersen buraya, yoksa standart metin gelir
                pass 

            r2_html += f"<div class='tech-item' style='margin-bottom:2px;'>{get_icon(is_valid)} <span style='margin-left:4px;'>{text}</span></div>"

    full_html = f"""
    <div class="info-card">
        <div class="info-header">📋 Gelişmiş Teknik Kart: {display_ticker}</div>
        <div style="display:flex; justify-content:space-between; margin-bottom:8px; border-bottom:1px solid #e5e7eb; padding-bottom:4px;">
            <div style="font-size:0.8rem; font-weight:700; color:#1e40af;">Fiyat: {price_val}</div>
            <div style="font-size:0.75rem; color:#64748B;">{ma_vals}</div>
        </div>
        <div style="font-size:0.8rem; color:#991b1b; margin-bottom:8px;">🛑 Stop: {stop_vals}</div>
        <div style="background:#f0f9ff; padding:4px; border-radius:4px; margin-bottom:4px;">
            <div style="font-weight:700; color:#0369a1; font-size:0.75rem; margin-bottom:4px;">🧠 RADAR 1 (3-12 gün): Momentum ve Hacim - SKOR: {r1_score}/7{r1_suffix}</div>
            <div class="tech-grid" style="font-size:0.75rem;">{r1_html}</div>
        </div>
        <div style="background:#f0fdf4; padding:4px; border-radius:4px;">
            <div style="font-weight:700; color:#15803d; font-size:0.75rem; margin-bottom:4px;">🚀 RADAR 2 (10-50 gün): Trend Takibi - SKOR: {r2_score}/7</div>
            <div class="tech-grid" style="font-size:0.75rem;">{r2_html}</div>
        </div>
    </div>
    """
    st.markdown(full_html.replace("\n", " "), unsafe_allow_html=True)

def render_synthetic_sentiment_panel(data):
    if data is None or data.empty: return
    # --- YENİ EKLENECEK KISIM (BAŞLIYOR) ---
    display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")
    
    # Fiyatı çekiyoruz (Başlığın sağına koymak için)
    info = fetch_stock_info(st.session_state.ticker)
    current_price = info.get('price', 0) if info else 0
    
    header_color = "#3b82f6" # Mavi Başlık Rengi

    # Yeni Profesyonel Başlık
    st.markdown(f"""
    <div class="info-card" style="border-top: 3px solid {header_color}; margin-bottom:15px;">
        <div class="info-header" style="color:#1e3a8a; display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:1.1rem;">🌊 Para Akış İvmesi & Fiyat Dengesi: {display_ticker}</span>
            <span style="font-family:'JetBrains Mono'; font-weight:700; color:#0f172a; background:#eff6ff; padding:2px 8px; border-radius:4px; font-size:1.25rem;">
                {current_price:.2f}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    # --- YENİ EKLENECEK KISIM (BİTTİ) ---
    c1, c2 = st.columns([1, 1]); x_axis = alt.X('Date_Str', axis=alt.Axis(title=None, labelAngle=-45), sort=None)
    with c1:
        base = alt.Chart(data).encode(x=x_axis)
        color_condition = alt.condition(
            alt.datum.MF_Smooth > 0,
            alt.value("#5B84C4"), 
            alt.value("#ef4444")
        )
        bars = base.mark_bar(size=12, opacity=0.9).encode(
            y=alt.Y('MF_Smooth:Q', axis=alt.Axis(title='Para Akışı (Güç)', labels=False, titleColor='#4338ca')), 
            color=color_condition, 
            tooltip=['Date_Str', 'Price', 'MF_Smooth']
        )
        price_line = base.mark_line(color='#1e40af', strokeWidth=2).encode(y=alt.Y('Price:Q', scale=alt.Scale(zero=False), axis=alt.Axis(title='Fiyat', titleColor='#0f172a')))
        st.altair_chart(alt.layer(bars, price_line).resolve_scale(y='independent').properties(height=280, title=alt.TitleParams("Momentum", fontSize=14, color="#1e40af")), use_container_width=True)
    with c2:
        base2 = alt.Chart(data).encode(x=x_axis)
        line_stp = base2.mark_line(color='#fbbf24', strokeWidth=3).encode(y=alt.Y('STP:Q', scale=alt.Scale(zero=False), axis=alt.Axis(title='Fiyat', titleColor='#64748B')), tooltip=['Date_Str', 'STP', 'Price'])
        line_price = base2.mark_line(color='#2563EB', strokeWidth=2).encode(y='Price:Q')
        area = base2.mark_area(opacity=0.15, color='gray').encode(y='STP:Q', y2='Price:Q')
        st.altair_chart(alt.layer(area, line_stp, line_price).properties(height=280, title=alt.TitleParams("Sentiment Analizi: Mavi (Fiyat) Sarıyı (STP-DEMA6) Yukarı Keserse AL, aşağıya keserse SAT", fontSize=14, color="#1e40af")), use_container_width=True)

def render_price_action_panel(ticker):
    obv_title, obv_color, obv_desc = get_obv_divergence_status(ticker)
    pa = calculate_price_action_dna(ticker)
    if not pa:
        st.info("PA verisi bekleniyor...")
        return
    # --- 👇 YENİ: S&D BÖLGESİ VERİSİ ÇEKİLİYOR 👇 ---
    df_sd = get_safe_historical_data(ticker, period="1y")
    try: sd_data = detect_supply_demand_zones(df_sd)
    except: sd_data = None
    
    sd_txt = "Taze bölge (RBR/DBD vb.) görünmüyor."
    sd_col = "#64748B"
    if sd_data:
        sd_txt = f"{sd_data['Type']} | {sd_data['Bottom']:.2f} - {sd_data['Top']:.2f} ({sd_data['Status']} olabilir)"
        sd_col = "#16a34a" if "Talep" in sd_data['Type'] else "#dc2626"
    # --- 👆 -------------------------------------- 👆 ---
    display_ticker = ticker.replace(".IS", "").replace("=F", "")

    sfp_color = "#16a34a" if "Bullish" in pa['sfp']['title'] else "#dc2626" if "Bearish" in pa['sfp']['title'] else "#475569"
    sq_color = "#d97706" if "BOBİN" in pa['sq']['title'] else "#475569"
    
    # RSI DIV RENKLENDİRME
    div_data = pa.get('div', {'type': 'neutral', 'title': '-', 'desc': '-'})
    if div_data['type'] == 'bearish':
        div_style = "background:#fef2f2; border-left:3px solid #dc2626; color:#991b1b;"
    elif div_data['type'] == 'bullish':
        div_style = "background:#f0fdf4; border-left:3px solid #16a34a; color:#166534;"
    else:
        div_style = "color:#475569;"

    # --- YENİ VERİLERİN HAZIRLIĞI ---
    vwap_data = pa.get('vwap', {'val': 0, 'diff': 0})
    rs_data = pa.get('rs', {'alpha': 0})
    
    # 7. VWAP MANTIĞI (TREND DOSTU GÜNCELLEME)
    v_diff = vwap_data['diff']
    
    if v_diff < -2.0:
        vwap_txt = "🟢 DİP FIRSATI (Aşırı İskonto)"
        vwap_desc = f"Fiyat maliyetin %{abs(v_diff):.1f} altında. Tepki ihtimali yüksek."
        vwap_col = "#035f25" # Koyu Yeşil
    elif v_diff < 0.0:
        vwap_txt = "🟢 UCUZ (Toplama)"
        vwap_desc = "Fiyat kurumsal maliyetin hemen altında."
        vwap_col = "#056d2b" # Açık Yeşil
    elif v_diff < 8.0:
        # %0 ile %8 arası: SAĞLIKLI TREND BÖLGESİ (Trenden İnme!)
        vwap_txt = "🚀 RALLİ MODU (Güçlü Trend)"
        vwap_desc = f"Fiyat maliyetin %{v_diff:.1f} üzerinde. Momentum arkanda."
        vwap_col = "#034969" # Sky Blue (Güven Veren Mavi)
    elif v_diff < 15.0:
        # %8 ile %15 arası: ISINMA BÖLGESİ
        vwap_txt = "🟠 DİKKAT (Piyasa Isınıyor)"
        vwap_desc = f"Fiyat ortalamadan %{v_diff:.1f} uzaklaştı. Stop seviyesi yükseltilse iyi olur."
        vwap_col = "#a36903" # Amber (Turuncu Uyarı)
    else:
        # %15 üzeri: ARTIK GERÇEKTEN RİSKLİ
        vwap_txt = "🔴 PARABOLİK (Aşırı Kopuş)"
        vwap_desc = f"Fiyat %{v_diff:.1f} saptı. Bu sürdürülemez, kâr almak düşünülebilir."
        vwap_col = "#570214" # Rose Kırmızı

    # 8. RS MANTIĞI
    alpha = rs_data['alpha']
    if alpha > 1.0:
        rs_txt = "🦁 LİDER (Endeksi Yeniyor)"
        rs_desc = f"Endekse göre %{alpha:.1f} daha güçlü (Alpha Pozitif)."
        rs_col = "#059669"
    elif alpha < -1.0:
        rs_txt = "🐢 ZAYIF (Endeksin Gerisinde)"
        rs_desc = f"Piyasa giderken gitmiyor (Fark %{alpha:.1f})."
        rs_col = "#470312"
    else:
        rs_txt = "🔗 NÖTR (Endeks ile Aynı)"
        rs_desc = "Piyasa rüzgarıyla paralel hareket ediyor."
        rs_col = "#475569"

    html_content = f"""
    <div class="info-card" style="border-top: 3px solid #6366f1;">
        <div class="info-header" style="color:#1e3a8a;">🕯️ Price Action Analizi: {display_ticker}</div>

        <div style="margin-bottom:8px;">
            <div style="font-weight:700; font-size:0.8rem; color:#1e3a8a;">1. MUM & FORMASYONLAR: {pa['candle']['title']}</div>
            <div class="edu-note">{pa['candle']['desc']}</div>
        </div>

        <div style="margin-bottom:8px; border-left: 2px solid {sfp_color}; padding-left:6px;">
            <div style="font-weight:700; font-size:0.8rem; color:{sfp_color};">2. TUZAK DURUMU: {pa['sfp']['title']}</div>
            <div class="edu-note">{pa['sfp']['desc']}</div>
        </div>

        <div style="margin-bottom:8px;">
            <div style="font-weight:700; font-size:0.8rem; color:#0f172a;">3. HACİM & VSA ANALİZİ: {pa['vol']['title']}</div>
            <div class="edu-note">{pa['vol']['desc']}</div>
        </div>

        <div style="margin-top:4px; padding:4px; background:{obv_color}15; border-radius:4px; border-left:2px solid {obv_color};">
            <div style="font-size:0.75rem; font-weight:700; color:{obv_color};">💰 {obv_title}</div>
            <div style="font-size:0.7rem; color:#475569; font-style:italic;">{obv_desc}</div>
        </div>

        <div style="margin-bottom:8px;">
            <div style="font-weight:700; font-size:0.8rem; color:#0f172a;">4. BAĞLAM & KONUM: {pa['loc']['title']}</div>
            <div class="edu-note">{pa['loc']['desc']}</div>
        </div>

        <div style="margin-bottom:8px;">
            <div style="font-weight:700; font-size:0.8rem; color:{sq_color};">5. VOLATİLİTE: {pa['sq']['title']}</div>
            <div class="edu-note">{pa['sq']['desc']}</div>
        </div>

        <div style="margin-bottom:6px; padding:4px; border-radius:4px; {div_style}">
            <div style="font-weight:700; font-size:0.8rem;">6. RSI UYUMSUZLUK: {div_data['title']}</div>
            <div class="edu-note" style="margin-bottom:0; color:inherit; opacity:0.9;">{div_data['desc']}</div>
        </div>

        <div style="margin-bottom:6px; padding:6px; border-left:3px solid {sd_col}; background:#f8fafc; border-radius:4px;">
            <div style="font-weight:700; font-size:0.8rem; color:{sd_col};">🧱 ARZ-TALEP (S&D) BÖLGELERİ:</div>
            <div style="font-size:0.85rem; font-weight:600; color:#0f172a; margin-top:2px;">{sd_txt}</div>
            <div class="edu-note" style="margin-top:4px; margin-bottom:0; color:inherit; opacity:0.9;">🐳 <b>Balina Ayak İzi:</b> Kurumsal fonların geçmişte yüklü emir bırakmış olabileceği gizli maliyet bölgesi. Fiyat bu alana girdiğinde potansiyel bir sıçrama (tepki) ihtimali doğabilir.</div>
        </div>

        <div style="border-top: 1px dashed #cbd5e1; margin-top:8px; padding-top:6px;"></div> 

        <div style="margin-bottom:8px;">
            <div style="font-weight:700; font-size:0.8rem; color:{vwap_col};">7. KURUMSAL REFERANS MALİYET (VWAP): {vwap_txt}</div>
            <div class="edu-note">{vwap_desc} (Son 20 gün Hacim Ağırlıklı Ortalama Fiyat-VWAP: {vwap_data['val']:.2f})</div>
        </div>

        <div style="margin-bottom:2px;">
            <div style="font-weight:700; font-size:0.8rem; color:{rs_col};">8. RS: PİYASA GÜCÜ (Bugün): {rs_txt}</div>
            <div class="edu-note" style="margin-bottom:0;">{rs_desc}</div>
        </div>        
    </div>
    """
    st.markdown(html_content.replace("\n", " "), unsafe_allow_html=True)

    # --- EKRANDA SMART MONEY HACİM ROZETİ GÖSTERİMİ ---
    if pa and "smart_volume" in pa:
        sv_data = pa["smart_volume"]
        delta_val = sv_data.get("delta", 0)
        delta_yuzde = sv_data.get("delta_yuzde", 0) # Yeni eklediğimiz yüzdeyi çekiyoruz
        
        # Seçili sembolün ENDEKS olup olmadığını kontrol etme
        # (BIST endeksleri genellikle XU, XB, XT ile başlar. Global endeksler ^ ile başlar)
        is_index = ticker.startswith(("XU", "XB", "XT", "XY", "^"))
        
        # Yüzde durumuna ve yönüne göre RENKLENDİRİLMİŞ baskınlık metni
        if is_index:
            # Sembol bir ENDEKS ise YÜZDE GÖSTERME
            if delta_val < 0:
                if delta_yuzde >= 60.0:
                    baskinlik = f"<span style='color: #dc2626; font-weight: 900;'>Agresif Satıcı Baskısı</span>"
                else:
                    baskinlik = f"<span style='color: #64748b; font-weight: 900;'>Sığ Satış (Gürültü)</span>"
            elif delta_val > 0:
                if delta_yuzde >= 60.0:
                    baskinlik = f"<span style='color: #16a34a; font-weight: 900;'>Agresif Alıcı Baskısı</span>"
                else:
                    baskinlik = f"<span style='color: #64748b; font-weight: 900;'>Pasif Alım (Gürültü)</span>"
            else:
                baskinlik = f"<span style='color: #64748b; font-weight: 900;'>Kusursuz Denge</span>"
        else:
            # Sembol bir HİSSE ise YÜZDEYİ GÖSTER
            if delta_val < 0:
                if delta_yuzde >= 60.0:
                    baskinlik = f"<span style='color: #dc2626; font-weight: 900;'>-%{delta_yuzde:.1f} Agresif Satıcı Baskısı</span>"
                else:
                    baskinlik = f"<span style='color: #64748b; font-weight: 900;'>-%{delta_yuzde:.1f} Sığ Satış (Gürültü)</span>"
            elif delta_val > 0:
                if delta_yuzde >= 60.0:
                    baskinlik = f"<span style='color: #16a34a; font-weight: 900;'>+%{delta_yuzde:.1f} Agresif Alıcı Baskısı</span>"
                else:
                    baskinlik = f"<span style='color: #64748b; font-weight: 900;'>+%{delta_yuzde:.1f} Pasif Alım (Gürültü)</span>"
            else:
                baskinlik = f"<span style='color: #64748b; font-weight: 900;'>Kusursuz Denge (%0)</span>"
            
        # İstediğin formattaki alt metin (Lot kelimesi kalktı, yüzde geldi)
        delta_text = f"Tahmini Delta (BUGÜN): {baskinlik}"
        
        # Renk temaları
        if "SATICI" in sv_data["title"] or "ALTINDA" in sv_data["title"]:
            border_color = "#dc2626"; bg_color = "#fef2f2"
        elif "ALIM" in sv_data["title"] or "ÜZERİNDE" in sv_data["title"]:
            border_color = "#16a34a"; bg_color = "#f0fdf4"
        else:
            border_color = "#d97706"; bg_color = "#fffbeb"

        st.markdown(f"""
        <div style="
            border: 2px solid {border_color}; 
            background-color: {bg_color}; 
            padding: 12px; 
            border-radius: 8px; 
            margin-top: 10px; 
            margin-bottom: 10px;">
            <div style="font-weight: 800; font-size: 0.9rem; color: {border_color}; margin-bottom: 4px;">
                📊 SMART MONEY HACİM ANALİZİ
            </div>
            <div style="font-weight: 700; font-size: 0.85rem; color: #0f172a;">{sv_data['title']}</div>
            <div style="font-style: italic; font-size: 0.95rem; color: #1e3a8a; margin-top: 4px; line-height: 1.4;">{sv_data['desc']}</div>
            <div style="border-top: 1px dashed {border_color}; margin-top: 10px; padding-top: 8px; font-size: 0.8rem; color: #1e3a8a;">
                {delta_text}
            </div>
        </div>
        """, unsafe_allow_html=True)
    # --------------------------------------------------

def render_ict_certification_card(ticker):
    """
    Sadece 5 şartı geçen hisselerde 'Onay Sertifikası' gösterir.
    Görsel: Başlık solda, Sonuç sağda (Yeşil Tikli), Açıklama altta (Edu Note).
    """
    # 1. Teyit Et (Logic Çalıştır)
    df = get_safe_historical_data(ticker, period="1y")
    # Daha önce yazdığımız dedektör fonksiyonunu kullanıyoruz
    res = process_single_ict_setup(ticker, df)
    
    # EĞER HİSSE SETUP'A UYMUYORSA HİÇ GÖSTERME (Sessizce çık)
    if res is None: return 

    # 2. HTML Tasarımı (MARTI Paneli Formatında)
    html_content = f"""
    <div class="info-card" style="border-top: 3px solid #7c3aed; background: #faf5ff; margin-bottom: 10px;">
        <div class="info-header" style="color:#5b21b6; display:flex; justify-content:space-between; align-items:center;">
            <span>🦅 ICT Sniper Onay Raporu</span>
            <span style="font-size:0.8rem; background:#7c3aed15; padding:2px 8px; border-radius:10px; font-weight:700;">5/5</span>
        </div>
        
        <div class="info-row" style="margin-top:5px;">
            <div class="label-long" style="width:160px; color:#4c1d95;">1. Likidite Temizliği (SSL):</div>
            <div class="info-val" style="color:#16a34a; font-weight:800;">GEÇTİ ✅</div>
        </div>
        <div class="edu-note" style="margin-bottom:8px;">
            Son 20-40 günün dibi aşağı kırıldı. Stoplar patlatıldı.
        </div>

        <div class="info-row">
            <div class="label-long" style="width:160px; color:#4c1d95;">2. Market Yapı Kırılımı:</div>
            <div class="info-val" style="color:#16a34a; font-weight:800;">GEÇTİ ✅</div>
        </div>
        <div class="edu-note" style="margin-bottom:8px;">
            Fiyat ani bir "U" dönüşüyle son tepeyi yukarı kırdı.
        </div>

        <div class="info-row">
            <div class="label-long" style="width:160px; color:#4c1d95;">3. Enerji / Hacim:</div>
            <div class="info-val" style="color:#16a34a; font-weight:800;">GEÇTİ ✅</div>
        </div>
        <div class="edu-note" style="margin-bottom:8px;">
            Yükseliş cılız mumlarla değil, gövdeli ve iştahlı mumlarla oldu.
        </div>

        <div class="info-row">
            <div class="label-long" style="width:160px; color:#4c1d95;">4. FVG Bıraktılar (İmza):</div>
            <div class="info-val" style="color:#16a34a; font-weight:800;">VAR (Destek) ✅</div>
        </div>
        <div class="edu-note" style="margin-bottom:8px;">
            Yükselirken arkasında doldurulmamış boşluk bıraktı.
        </div>

        <div class="info-row" style="border-top:1px dashed #d8b4fe; padding-top:6px; margin-top:4px;">
            <div class="label-long" style="width:160px; color:#4c1d95; font-weight:800;">5. İndirimli Bölge:</div>
            <div class="info-val" style="color:#16a34a; font-weight:800;">OTE (Mükemmel) ✅</div>
        </div>
        <div class="edu-note">
            Fiyat, hareketin %50'sinden fazlasını geri alarak "Toptan Fiyat" bölgesine indi.
        </div>
    </div>
    """
    st.markdown(html_content.replace("\n", " "), unsafe_allow_html=True)

def render_ict_deep_panel(ticker):
    data = calculate_ict_deep_analysis(ticker)
    
    if not data or data.get("status") == "Error":
        st.warning(f"ICT Analiz Bekleniyor... ({data.get('msg', 'Veri Yok')})")
        return
    
    # ==============================================================================
    # 1. ORİJİNAL İÇERİK MANTIĞI (ORİJİNAL METİNLER KORUNDU)
    # ==============================================================================
    
    # Yapı Başlığı ve Açıklaması
    struct_title = "MARKET YAPISI"
    struct_desc = "Piyasa kararsız."
    
    if "MSS" in data['structure']:
        if "🐂" in data['structure']: 
            struct_title = "TREND DÖNÜŞÜ (BULLISH MSS)"
            struct_desc = "Fiyat, düşüş yapısını bozan son önemli tepeyi aştı. Ayı piyasası bitmiş, Boğa dönemi başlıyor olabilir!"
        else: 
            struct_title = "TREND DÖNÜŞÜ (BEARISH MSS)"
            struct_desc = "Fiyat, yükseliş yapısını tutan son önemli dibi kırdı. Boğa piyasası bitmiş, Ayı dönemi başlıyor olabilir!"
    elif "BOS (Yükseliş" in data['structure']: 
        struct_title = "YÜKSELİŞ TRENDİ (BULLISH BOS)"
        struct_desc = "Boğalar kontrolü elinde tutuyor. Eski tepeler aşıldı, bu da yükseliş iştahının devam ettiğini gösterir. Geri çekilmeler alım fırsatı olabilir."
    elif "BOS (Düşüş" in data['structure']: 
        struct_title = "DÜŞÜŞ TRENDİ (BEARISH BOS)"
        struct_desc = "Ayılar piyasaya hakim. Eski dipler kırıldı, düşüş trendi devam ediyor. Yükselişler satış fırsatı olarak görülebilir."
    elif "Internal" in data['structure']: 
        struct_title = "INTERNAL RANGE (Düşüş/Düzeltme)" if "bearish" in data['bias'] else "INTERNAL RANGE (Yükseliş/Tepki)"
        struct_desc = "Ana trendin tersine bir düzeltme hareketi (Internal Range) yaşanıyor olabilir. Piyasada kararsızlık hakim."

    # Enerji Açıklaması
    energy_title = "ENERJİ DURUMU"
    energy_desc = "Zayıf (Hacimsiz Hareket)\nMum gövdeleri küçük, hacimsiz bir hareket. Kurumsal oyuncular henüz oyuna tam girmemiş olabilir. Kırılımlar tuzak olabilir."
    if "Güçlü" in data['displacement']: 
        energy_desc = "Güçlü (Displacement Var)\nFiyat güçlü ve hacimli mumlarla hareket ediyor. Bu 'Akıllı Para'nın (Smart Money) ayak sesidir."

    # MT (Denge) Başlığı
    mt_title = "Kritik Denge Seviyesi"
    if "bearish" in data['bias']: mt_title = "Satıcılar Baskın"
    elif "bullish" in data['bias']: mt_title = "Alıcılar Baskın"

    # Konum Açıklaması
    zone_desc = "Fiyat 'Ucuzluk' (Discount) bölgesinde. Kurumsal yatırımcılar bu seviyelerden alım yapmayı tercih eder."
    if "PREMIUM" in data['zone']: 
        zone_desc = "Fiyat 'Pahalılık' (Premium) bölgesinde. Kurumsal yatırımcılar bu bölgede satış yapmayı veya kar almayı sever."

    # FVG Açıklaması
    fvg_desc = "Yakınlarda önemli bir dengesizlik boşluğu tespit edilemedi."
    if "Destek" in data['fvg_txt']: fvg_desc = "Fiyatın bu boşluğu doldurup destek alması beklenebilir."
    elif "Direnç" in data['fvg_txt']: fvg_desc = "Fiyatın bu boşluğu doldurup direnç görmesi beklenebilir."

    # OB Açıklaması
    ob_desc = "Order Block: Yani Kurumsal oyuncuların son yüklü işlem yaptığı seviye. Fiyat buraya dönerse güçlü tepki alabilir. Eğer bu bölge fiyatı yeni bir tepeye (BOS) götürdüyse 'Kaliteli'dir. Götürmediyse zayıftır."
    
    # Likidite Açıklaması
    liq_desc = "Yani Fiyatın bir sonraki durağı. Stop emirlerinin (Likiditenin) biriktiği, fiyatın çekildiği hedef seviye."

    # --- RENK PALETİ ---
    main_color = "#16a34a" if "bullish" in data['bias'] else "#dc2626" if "bearish" in data['bias'] else "#7c3aed"
    bg_light = "#f0fdf4" if "bullish" in data['bias'] else "#fef2f2" if "bearish" in data['bias'] else "#f5f3ff"
    
    display_ticker = ticker.replace(".IS", "").replace("=F", "")
    info = fetch_stock_info(ticker)
    current_price_str = f"{info.get('price', 0):.2f}" if info else "0.00"

# --- ICT SMART MONEY ANALİZİ BÖLÜMÜ (GÜNCELLENMİŞ MODERN ARAYÜZ) ---

# BAŞLIK (Hiyerarşik Bloklar - Revize Edilmiş Son Hali)
    st.markdown(f"""
<div class="info-card" style="border-top: 4px solid {main_color}; margin-bottom:10px; border-radius: 8px;">
<div class="info-header" style="color:#1e3a8a; display:flex; justify-content:space-between; align-items:center; padding: 3px 12px;">
<span style="font-size:1.15rem; font-weight: 800;">🧠 ICT Smart Money Analizi: {display_ticker}</span>
<span style="font-family:'JetBrains Mono'; font-weight:800; color:#0f172a; font-size:1.1rem; background: #f1f5f9; padding: 2px 8px; border-radius: 6px;">{current_price_str}</span>
</div>
</div>
""", unsafe_allow_html=True)

    c1, c2 = st.columns([1.4, 1])

    with c1:
        # Alt sütunlar: Market Yapısı ve Enerji
        sc1, sc2 = st.columns(2)
        
        with sc1:
            st.markdown(f"""
<div style="border:2px solid {main_color}; background:{bg_light}; border-radius:8px; padding:12px; height: 100%;">
<div style="font-weight:800; color:{main_color}; font-size:0.85rem; text-transform: uppercase; margin-bottom:6px;">{struct_title}</div>
<div style="font-size:0.8rem; color:#1e3a8a; line-height:1.4;">{struct_desc}</div>
</div>
""", unsafe_allow_html=True)

        with sc2:
            st.markdown(f"""
<div style="border:2px solid #94a3b8; background:#f8fafc; border-radius:8px; padding:12px; height: 100%;">
<div style="font-weight:800; color:#7c3aed; font-size:0.85rem; text-transform: uppercase; margin-bottom:6px;">{energy_title}</div>
<div style="font-size:0.8rem; color:#1e3a8a; line-height:1.4;">{energy_desc}</div>
</div>
""", unsafe_allow_html=True)

        # MT (Denge/Alıcılar Baskın) ve Hedef Likidite Yanyana (Yeni 2 Sütun)
        hc1, hc2 = st.columns(2)
        
        with hc1:
            st.markdown(f"""
<div style="background:#fff7ed; border:2px solid #ea580c; border-left:6px solid #ea580c; padding:12px; margin-top:12px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; border-radius:8px; height: 100%;">
<div>
<div style="font-weight:800; color:#c2410c; font-size:0.9rem;">🛡️ {mt_title}</div>
<div style="font-size:0.75rem; color:#9a3412; margin-top: 2px;">Fiyat kritik orta noktanın altına sarktı/üstüne çıktı. Yapı bozulmuş olabilir.</div>
</div>
<div style="font-family:'JetBrains Mono'; font-weight:800; font-size:1.1rem; color:#c2410c; background: white; padding: 4px 8px; border-radius: 4px; margin-left: 8px;">{data['mean_threshold']:.2f}</div>
</div>
""", unsafe_allow_html=True)

        with hc2:
            st.markdown(f"""
<div style="border:2px solid #e11d48; background:#fff1f2; padding:12px; border-radius:8px; margin-top:12px; margin-bottom:12px; height: 100%;">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
<div style="font-weight:800; color:#be185d; font-size:0.9rem; text-transform: uppercase;">🎯 HEDEF LİKİDİTE</div>
<div style="font-weight:800; font-family:'JetBrains Mono'; font-size:1.2rem; color:#be185d; background: white; padding: 2px 8px; border-radius: 6px;">{data['target']:.2f}</div>
</div>
<div style="font-size:0.8rem; color:#9f1239; line-height:1.3;">{liq_desc}</div>
</div>
""", unsafe_allow_html=True)

        # The Bottom Line (Sonuç) Tam Genişlik - Koyu Arka Plan, 2px Kalın Çerçeve
        st.markdown(f"""
<div style="background:#dbeafe; border:2px solid #3b82f6; border-radius:8px; padding:16px; text-align: center;">
<div style="font-weight:800; color:#1e40af; font-size:0.9rem; margin-bottom:8px; text-transform: uppercase;">🖥️ BOTTOM LINE (SONUÇ)</div>
<div style="font-size:1.05rem; color:#1e3a8a; font-style:italic; line-height:1.4; font-weight: 500;">"{data.get('bottom_line', '-')}"</div>
</div>
""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
<div style="border:2px solid #cbd5e1; background:white; border-radius:8px; padding:16px; height:100%;">
<div style="font-weight:800; color:#be185d; font-size:0.9rem; text-transform: uppercase; border-bottom:2px solid #e2e8f0; padding-bottom:8px; margin-bottom:12px;">📍 GİRİŞ/ÇIKIŞ REFERANSLARI</div>
<div style="margin-bottom:14px;">
<div style="font-weight:800; color:#9f1239; font-size:0.85rem; margin-bottom: 2px;">KONUM: <span style="color:#0f172a; font-weight: 600; background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">{data['zone']}</span></div>
<div style="font-size:0.8rem; color:#475569; line-height:1.3;">{zone_desc}</div>
</div>
<div style="margin-bottom:14px;">
<div style="font-weight:800; color:#7e22ce; font-size:0.85rem; margin-bottom: 2px;">GAP (FVG): <span style="color:#0f172a; font-family: 'JetBrains Mono'; font-weight: 700; background: #f3e8ff; padding: 2px 6px; border-radius: 4px;">{data['fvg_txt']}</span></div>
<div style="font-size:0.8rem; color:#475569; line-height:1.3;">{fvg_desc}</div>
</div>
<div style="margin-bottom:14px;">
<div style="font-weight:800; color:#0369a1; font-size:0.85rem; margin-bottom: 2px;">AKTİF OB: <span style="color:#0f172a; font-family: 'JetBrains Mono'; font-weight: 700; background: #e0f2fe; padding: 2px 6px; border-radius: 4px;">{data['ob_txt']}</span></div>
<div style="font-size:0.8rem; color:#475569; line-height:1.3;">{ob_desc}</div>
</div>
<div style="margin-bottom:14px; background: #f8fafc; padding: 8px; border-radius: 6px; border-left: 4px solid #ea580c; border: 2px solid #cbd5e1;">
<div style="font-weight:800; color:#ea580c; font-size:0.85rem; margin-bottom: 4px;">HAVUZ / SWEEP: <span style="color:#0f172a; font-weight: 600;">{data.get('eqh_eql_txt', '-')} | {data.get('sweep_txt', '-')}</span></div>
<div style="font-size:0.75rem; color:#475569; line-height:1.3;">🧲 <b>Mıknatıs & Av:</b> EQH/EQL, potansiyel tuzak alanlarıdır. Fiyat buraları kırıp hızla geri dönüyorsa (Sweep), büyük fonlar stopları patlatıp yönü değiştiriyor olabilir.</div>
</div>
</div>
""", unsafe_allow_html=True)

def render_levels_card(ticker):
    data = get_advanced_levels_data(ticker)
    if not data: return

    # Renk ve İkon Ayarları
    is_bullish = data['st_dir'] == 1
    
    st_color = "#16a34a" if is_bullish else "#dc2626"
    st_text = "YÜKSELİŞ (AL)" if is_bullish else "DÜŞÜŞ (SAT)"
    st_icon = "🐂" if is_bullish else "🐻"
    
    # --- DİNAMİK METİN AYARLARI ---
    if is_bullish:
        # Yükseliş Senaryosu
        st_label = "Takip Eden Stop (Stop-Loss)"
        st_desc = "⚠️ Fiyat bu seviyenin <b>altına inerse</b> trend bozulur, stop olunmalıdır."
        
        # Golden Pocket Metni (Yükseliş)
        gp_desc_text = "Kurumsal alım bölgesi (İdeal Giriş/Destek)."
        gp_desc_color = "#92400e" # Amber/Kahve
        
        # Dinamik Kutu Metinleri (Yükseliş)
        res_ui_label = "EN YAKIN DİRENÇ 🚧"
        res_ui_desc = "Zorlu tavan. Geçilirse yükseliş hızlanır."
        sup_ui_label = "EN YAKIN DESTEK 🛡️"
        sup_ui_desc = "İlk savunma hattı. Düşüşü tutmalı."
    else:
        # Düşüş Senaryosu
        st_label = "Trend Dönüşü (Direnç)"
        st_desc = "🚀 Fiyat bu seviyenin <b>üstüne çıkarsa</b> düşüş biter, yükseliş başlar."
        
        # Golden Pocket Metni (Düşüş)
        gp_desc_text = "⚠️ Güçlü Direnç / Tepki Satış Bölgesi (Short)."
        gp_desc_color = "#b91c1c" # Kırmızı
        
        # Dinamik Kutu Metinleri (Düşüş - ICT Uyumlu)
        res_ui_label = "O.T.E. DİRENCİ"
        res_ui_desc = "Akıllı Para short arar. Trend yönünde satış bölgesidir."
        sup_ui_label = "AŞAĞIDAKİ LİKİDİTE HEDEFİ"
        sup_ui_desc = "Düşüş trendinde destek aranmaz, kırılması beklenir."
    
    # Fibonacci Formatlama
    sup_lbl, sup_val = data['nearest_sup']
    res_lbl, res_val = data['nearest_res']
    
    # --- GÖRSEL DÜZELTME ---
    if res_lbl == "ZİRVE AŞIMI":
        res_display = "---"
        res_desc_final = "🚀 Fiyat tüm dirençleri kırdı (Price Discovery)."
    else:
        res_display = f"{res_val:.2f}"
        res_desc_final = res_ui_desc

    # --- GOLDEN POCKET DEĞERİ ---
    gp_key = next((k for k in data['fibs'].keys() if "Golden" in k), "0.618 (Golden)")
    gp_val = data['fibs'].get(gp_key, 0)
    
    html_content = f"""
    <div class="info-card" style="border-top: 3px solid #8b5cf6;">
        <div class="info-header" style="color:#4c1d95;">📐 Orta Vadeli Trend (1-6 ay): {display_ticker}</div>
        
        <div style="background:{st_color}15; padding:8px; border-radius:5px; border:1px solid {st_color}; margin-bottom:8px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:700; color:{st_color}; font-size:0.8rem;">{st_icon} SuperTrend (10,3)</span>
                <span style="font-weight:500; color:{st_color}; font-size:0.9rem;">{st_text}</span>
            </div>
            <div style="font-size:0.75rem; color:#64748B; margin-top:2px;">
                {st_label}: <strong style="color:#0f172a;">{data['st_val']:.2f}</strong>
            </div>
            <div style="font-size:0.65rem; color:#6b7280; font-style:italic; margin-top:4px; border-top:1px dashed {st_color}40; padding-top:2px;">
                {st_desc}
            </div>
        </div>

        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:6px;">
            <div style="background:#f0fdf4; padding:6px; border-radius:4px; border:1px solid #bbf7d0;">
                <div style="font-size:0.65rem; color:#166534; font-weight:700;">{res_ui_label}</div>
                <div style="font-family:'JetBrains Mono'; font-weight:700; color:#15803d; font-size:0.85rem;">{res_display}</div>
                <div style="font-size:0.6rem; color:#166534; margin-bottom:2px;">Fib {res_lbl}</div>
                <div style="font-size:0.6rem; color:#64748B; font-style:italic; line-height:1.1;">{res_desc_final}</div>
            </div>
            
            <div style="background:#fef2f2; padding:6px; border-radius:4px; border:1px solid #fecaca;">
                <div style="font-size:0.65rem; color:#991b1b; font-weight:700;">{sup_ui_label}</div>
                <div style="font-family:'JetBrains Mono'; font-weight:700; color:#b91c1c; font-size:0.85rem;">{sup_val:.2f}</div>
                <div style="font-size:0.6rem; color:#991b1b; margin-bottom:2px;">Fib {sup_lbl}</div>
                <div style="font-size:0.6rem; color:#64748B; font-style:italic; line-height:1.1;">{sup_ui_desc}</div>
            </div>
        </div>
        
        <div style="margin-top:6px;">
            <div style="font-size:0.7rem; font-weight:700; color:#6b7280; margin-bottom:2px;">⚜️ Golden Pocket (0.618 - 0.65):</div>
            <div style="display:flex; align-items:center; gap:6px;">
                <div style="font-family:'JetBrains Mono'; font-size:0.8rem; background:#fffbeb; padding:2px 6px; border-radius:4px; border:1px dashed #f59e0b;">
                    {gp_val:.2f}
                </div>
                <div style="font-size:0.65rem; color:{gp_desc_color}; font-style:italic;">
                    {gp_desc_text}
                </div>
            </div>
        </div>
    </div>
    """
    st.markdown(html_content.replace("\n", " "), unsafe_allow_html=True)

def render_minervini_panel_v2(ticker):
    # 1. Verileri al
    cat = st.session_state.get('category', 'S&P 500')
    bench = "XU100.IS" if "BIST" in cat else "^GSPC"
    
    data = calculate_minervini_sepa(ticker, benchmark_ticker=bench)
    
    if not data: return 

    # --- HİSSE ADINI HAZIRLA ---
    display_ticker = ticker.replace(".IS", "").replace("=F", "")

    # 2. Görsel öğeleri hazırla
    trend_icon = "✅" if data['trend_ok'] else "❌"
    vcp_icon = "✅" if data['is_vcp'] else "❌"
    vol_icon = "✅" if data['is_dry'] else "❌"
    rs_icon = "✅" if data['rs_val'] > 0 else "❌"
    
    rs_width = min(max(int(data['rs_val'] * 5 + 50), 0), 100)
    rs_color = "#16a34a" if data['rs_val'] > 0 else "#dc2626"
    
    # 3. HTML KODU (HİSSE ADI EKLENDİ)
    html_content = f"""
<div class="info-card" style="border-top: 3px solid {data['color']};">
<div class="info-header" style="display:flex; justify-content:space-between; align-items:center; color:{data['color']};">
<span>🦁 Minervini SEPA Analizi</span>
<span style="font-size:0.8rem; font-weight:800; background:{data['color']}15; padding:2px 8px; border-radius:10px;">{data['score']}/100</span>
</div>
<div style="text-align:center; margin-bottom:5px;">
<div style="font-size:0.9rem; font-weight:800; color:{data['color']}; letter-spacing:0.5px;">{display_ticker} | {data['Durum']}</div>
</div>
<div class="edu-note" style="text-align:center; margin-bottom:10px;">
"Aşama 2" yükseliş trendi ve düşük oynaklık (VCP) aranıyor.
</div>
<div style="display:grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap:4px; margin-bottom:5px; text-align:center;">
<div style="background:#f8fafc; padding:4px; border-radius:4px; border:1px solid #e2e8f0;">
<div style="font-size:0.6rem; color:#64748B; font-weight:700;">TREND</div>
<div style="font-size:1rem;">{trend_icon}</div>
</div>
<div style="background:#f8fafc; padding:4px; border-radius:4px; border:1px solid #e2e8f0;">
<div style="font-size:0.6rem; color:#64748B; font-weight:700;">VCP</div>
<div style="font-size:1rem;">{vcp_icon}</div>
</div>
<div style="background:#f8fafc; padding:4px; border-radius:4px; border:1px solid #e2e8f0;">
<div style="font-size:0.6rem; color:#64748B; font-weight:700;">ARZ</div>
<div style="font-size:1rem;">{vol_icon}</div>
</div>
<div style="background:#f8fafc; padding:4px; border-radius:4px; border:1px solid #e2e8f0;">
<div style="font-size:0.6rem; color:#64748B; font-weight:700;">RS</div>
<div style="font-size:1rem;">{rs_icon}</div>
</div>
</div>
<div class="edu-note">
1. <b>Trend:</b> Fiyat > SMA200 (Yükseliş Trendinde vs Yatayda-Düşüşte)<br>
2. <b>VCP:</b> Fiyat sıkışıyor mu? (Düşük Oynaklık vs Dalgalı-Dengesiz Yapı)<br>
3. <b>Arz:</b> Düşüş günlerinde hacim daralıyor mu? (Satıcılar yoruldu vs Düşüşlerde hacim yüksek)<br>
4. <b>RS:</b> Endeksten daha mı güçlü? (Endeks düşerken bu hisse duruyor veya yükseliyor vs Endeksle veya daha çok düşüyor)
</div>
<div style="margin-bottom:2px; margin-top:8px;">
<div style="display:flex; justify-content:space-between; font-size:0.7rem; margin-bottom:2px;">
<span style="color:#64748B; font-weight:600;">Endeks Gücü (Mansfield RS)</span>
<span style="font-weight:700; color:{rs_color};">{data['rs_rating']}</span>
</div>
<div style="width:100%; height:6px; background:#e2e8f0; border-radius:3px; overflow:hidden;">
<div style="width:{rs_width}%; height:100%; background:{rs_color};"></div>
</div>
</div>
<div class="edu-note">Bar yeşil ve doluysa hisse endeksi yeniyor (Lider).</div>
<div style="margin-top:6px; padding-top:4px; border-top:1px dashed #cbd5e1; font-size:0.7rem; color:#475569; display:flex; justify-content:space-between;">
<span>SMA200: {data['sma200']:.2f}</span>
<span>52H Zirve: {data['year_high']:.2f}</span>
</div>
<div class="edu-note">Minervini Kuralı: Fiyat 52 haftalık zirveye %25'ten fazla uzak olmamalı.</div>
</div>
"""
    
    st.markdown(html_content, unsafe_allow_html=True)
    
# ==============================================================================
# 5. SIDEBAR UI
# ==============================================================================
with st.sidebar:
    st.markdown(f"""<div style="font-size:1.5rem; font-weight:700; color:#1e3a8a; text-align:center; padding-top: 10px; padding-bottom: 10px;">SMART MONEY RADAR</div><hr style="border:0; border-top: 1px solid #e5e7eb; margin-top:5px; margin-bottom:10px;">""", unsafe_allow_html=True)

    # --- YENİ EKLENEN: TEKNİK SEVİYELER (MA) PANELİ ---
    try:
        if "ticker" in st.session_state and st.session_state.ticker:
            
            df_ma = get_safe_historical_data(st.session_state.ticker, period="1y") 
            
            if df_ma is not None and not df_ma.empty:
                if 'Close' in df_ma.columns: c_col = 'Close'
                elif 'close' in df_ma.columns: c_col = 'close'
                elif 'Fiyat' in df_ma.columns: c_col = 'Fiyat'
                else: c_col = df_ma.columns[0]

                current_price = df_ma[c_col].iloc[-1]

                ema5 = df_ma[c_col].ewm(span=5, adjust=False).mean().iloc[-1]
                ema8 = df_ma[c_col].ewm(span=8, adjust=False).mean().iloc[-1]
                ema13 = df_ma[c_col].ewm(span=13, adjust=False).mean().iloc[-1]
                ema144 = df_ma[c_col].ewm(span=144, adjust=False).mean().iloc[-1]

                sma50 = df_ma[c_col].rolling(window=50).mean().iloc[-1]
                sma100 = df_ma[c_col].rolling(window=100).mean().iloc[-1]
                sma200 = df_ma[c_col].rolling(window=200).mean().iloc[-1]

                # AKILLI FORMAT: Endeksleri (XU) veya 1000'den büyük rakamları yakala
                is_index = "XU" in st.session_state.ticker.upper() or "^" in st.session_state.ticker or current_price > 1000

                def ma_status(ma_value, price):
                    if pd.isna(ma_value): return "⏳ -"
                    
                    # Küsurat ayarı
                    if is_index:
                        val_str = f"{int(ma_value)}" # Endeks ise tam sayı yap (Örn: 14016)
                    else:
                        val_str = f"{ma_value:.2f}"  # Hisse ise küsuratlı kalsın (Örn: 15.42)
                        
                    if price > ma_value:
                        return f"🟢 <b>{val_str}</b>"
                    else:
                        return f"🔴 <b>{val_str}</b>"

                # YENİ EKLENEN: Sembolü temizleme (Örn: XU100.IS -> XU100)
                # Noktadan (.) bölüp ilk kısmı alıyoruz ve her ihtimale karşı büyük harfe çeviriyoruz.
                clean_ticker = st.session_state.ticker.split('.')[0].upper()

                # DİKKAT: Üç tırnaktan sonraki HTML etiketleri tamamen en sola dayalı olmalıdır!
                st.markdown(f"""
<div style="border: 1px solid #3b82f6; border-radius: 6px; overflow: hidden; margin-bottom: 15px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
<div style="background: linear-gradient(45deg, #1e3a8a, #3b82f6); color: white; padding: 6px; text-align: center; font-weight: 700; font-size: 0.9rem;">
📊 TEKNİK SEVİYELER
</div>
<div style="background-color: #f8fafc; border-bottom: 1px solid #e2e8f0; padding: 6px; text-align: center; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);">
<span style="font-weight: 800; font-size: 0.95rem; color: #0f172a; letter-spacing: 0.5px;">{clean_ticker}</span>
<span style="color: #64748b; margin: 0 8px; font-weight: 400;">—</span>
<span style="font-weight: 700; font-size: 0.95rem; color: #0284c7;">{current_price:,.2f}</span>
</div>
<div style="display: flex; padding: 10px 5px; background-color: transparent;">
<div style="flex: 1; padding-right: 10px; border-right: 1px solid #4b5563;">
<div style="font-size: 0.75rem; color: #6b7280; font-weight: bold; margin-bottom: 5px;">📉 KISA VADE</div>
<div style="font-size: 0.85rem; line-height: 1.6;">
EMA 5: {ma_status(ema5, current_price)}<br>
EMA 8: {ma_status(ema8, current_price)}<br>
EMA 13: {ma_status(ema13, current_price)}
</div>
</div>
<div style="flex: 1; padding-left: 10px;">
<div style="font-size: 0.75rem; color: #6b7280; font-weight: bold; margin-bottom: 5px;">🔭 ORTA/UZUN VADE</div>
<div style="font-size: 0.85rem; line-height: 1.6;">
SMA 50: {ma_status(sma50, current_price)}<br>
SMA 100: {ma_status(sma100, current_price)}<br>
SMA 200: {ma_status(sma200, current_price)}<br>
EMA 144: {ma_status(ema144, current_price)}
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)
                
    except Exception as e:
        st.warning(f"Teknik tablo oluşturulamadı. Hata: {e}")
    # --------------------------------------------------
    # --------------------------------------------------
    # --- TEMEL ANALİZ DETAYLARI (DÜZELTİLMİŞ & TEK PARÇA) ---
    sentiment_verisi = calculate_sentiment_score(st.session_state.ticker)
    
    # 1. PİYASA DUYGUSU (En Üstte)
    sentiment_verisi = calculate_sentiment_score(st.session_state.ticker)
    if sentiment_verisi:
        render_sentiment_card(sentiment_verisi)

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    # LORENTZİAN PANELİ 
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    render_lorentzian_panel(st.session_state.ticker)
    st.divider()
    # MINERVINI PANELİ (Hatasız Versiyon)
    render_minervini_panel_v2(st.session_state.ticker)
    # --- YILDIZ ADAYLARI (KESİŞİM PANELİ) ---
    st.markdown(f"""
    <div style="background: linear-gradient(45deg, #06b6d4, #3b82f6); color: white; padding: 12px 8px; border-radius: 6px; text-align: center; margin-bottom: 10px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
        <div style="font-weight: 800; font-size: 1.05rem; letter-spacing: 0.5px; margin-bottom: 5px;">🌟 YILDIZ ADAYLARI</div>
        <div style="font-size: 0.75rem; font-weight: 400; opacity: 0.9; line-height: 1.3;">
            Son 5 gündür Endeksten güçlü, 45 günlük yatay direnci hacimle kırdı ya da kırmak üzere, RSI<70
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Kesişim Mantığı
    stars_found = False
    
    # Scroll Alanı Başlatıyoruz
    with st.container(height=350):
        
        # Verilerin varlığını kontrol et
        has_accum = st.session_state.accum_data is not None and not st.session_state.accum_data.empty
        has_warm = st.session_state.breakout_left is not None and not st.session_state.breakout_left.empty
        has_break = st.session_state.breakout_right is not None and not st.session_state.breakout_right.empty
        
        if has_accum:
            # Akıllı Para listesindeki sembolleri ve verileri al
            acc_df = st.session_state.accum_data
            acc_symbols = set(acc_df['Sembol'].values)
            
            # ------------------------------------------------------------------
            # SENARYO 1: 🚀 ROKET MODU (RS Lideri + [Kıran VEYA Isınan])
            # ------------------------------------------------------------------
            
            has_rs = st.session_state.rs_leaders_data is not None and not st.session_state.rs_leaders_data.empty
            
            # Hem Kıranlara (Right) hem Isınanlara (Left) bakıyoruz
            has_break_right = st.session_state.breakout_right is not None and not st.session_state.breakout_right.empty
            has_break_left = st.session_state.breakout_left is not None and not st.session_state.breakout_left.empty

            if has_rs and (has_break_right or has_break_left):
                rs_df = st.session_state.rs_leaders_data
                rs_symbols = set(rs_df['Sembol'].values)
                
                # İki listeyi (Kıranlar + Isınanlar) birleştiriyoruz
                bo_symbols = set()
                bo_data_map = {} # Detayları saklamak için

                # 1. Kıranları Ekle (Öncelikli)
                if has_break_right:
                    df_r = st.session_state.breakout_right
                    for _, row in df_r.iterrows():
                        sym = row['Sembol']
                        bo_symbols.add(sym)
                        bo_data_map[sym] = {'status': 'KIRDI 🔨', 'info': row['Hacim_Kati']}

                # 2. Isınanları Ekle
                if has_break_left:
                    df_l = st.session_state.breakout_left
                    for _, row in df_l.iterrows():
                        # Sütun adı bazen Sembol_Raw bazen Sembol olabiliyor, kontrol et
                        sym = row.get('Sembol_Raw', row.get('Sembol'))
                        if sym:
                            bo_symbols.add(sym)
                            # Eğer zaten Kıranlarda yoksa, Isınan olarak ekle
                            if sym not in bo_data_map:
                                # Zirveye yakınlık bilgisini temizle
                                prox = str(row.get('Zirveye Yakınlık', '')).split('<')[0].strip()
                                bo_data_map[sym] = {'status': 'ISINIYOR', 'info': prox}

                # KESİŞİM BUL (RS Lideri + [Kıran veya Isınan])
                rocket_stars = rs_symbols.intersection(bo_symbols)

                if rocket_stars:
                    rocket_list = []
                    for sym in rocket_stars:
                        row_rs = rs_df[rs_df['Sembol'] == sym].iloc[0]
                        bo_info = bo_data_map.get(sym, {'status': '?', 'info': ''})
                        
                        rocket_list.append({
                            'sym': sym, 
                            'price': row_rs['Fiyat'], 
                            'alpha': row_rs.get('Alpha_5D', row_rs.get('Adj_Alpha_5D', 0)),
                            'status': bo_info['status'],
                            'info': bo_info['info'],
                            'score': row_rs['Skor']
                        })
                    
                    # Puana göre sırala
                    rocket_list.sort(key=lambda x: x['score'], reverse=True)

                    for item in rocket_list:
                        stars_found = True
                        sym = item['sym']
                        # Etiket: 💎 THYAO | Alpha:+%5.2 | KIRDI 🔨 (3.5x)
                        # Etiket: 💎 ASELS | Alpha:+%3.1 | ISINIYOR 🔥 (%98)
                        label = f"💎 {sym.replace('.IS', '')} | Alpha:+%{item['alpha']:.1f} | {item['status']}"
                        
                        if st.button(label, key=f"star_rocket_hybrid_{sym}", use_container_width=True):
                            on_scan_result_click(sym)
                            st.rerun()
                            
            # --- 2. SENARYO: HAREKET (Kıranlar + Akıllı Para) ---
            if has_break:
                bo_df = st.session_state.breakout_right
                bo_symbols = set(bo_df['Sembol'].values)
                
                # Kesişim Bul
                move_stars_symbols = acc_symbols.intersection(bo_symbols)
                
                if move_stars_symbols:
                    # Kesişenleri Hacime Göre Sıralamak İçin Liste Oluştur
                    move_star_list = []
                    for sym in move_stars_symbols:
                        # Veriyi accum_data'dan çek (Hacim orada var)
                        row = acc_df[acc_df['Sembol'] == sym].iloc[0]
                        vol = row.get('Hacim', 0)
                        price = row['Fiyat']
                        move_star_list.append({'sym': sym, 'price': price, 'vol': vol})
                    
                    # SIRALAMA: Hacme Göre Büyükten Küçüğe
                    move_star_list.sort(key=lambda x: x['vol'], reverse=True)
                    
                    for item in move_star_list:
                        stars_found = True
                        sym = item['sym']
                        label = f"🚀 {sym.replace('.IS', '')} ({item['price']}) | HAREKET"
                        if st.button(label, key=f"star_mov_{sym}", use_container_width=True):
                            on_scan_result_click(sym)
                            st.rerun()

            # --- 3. SENARYO: HAZIRLIK (Isınanlar + Akıllı Para) ---
            if has_warm:
                warm_df = st.session_state.breakout_left
                col_name = 'Sembol_Raw' if 'Sembol_Raw' in warm_df.columns else 'Sembol'
                warm_symbols = set(warm_df[col_name].values)
                
                # Kesişim Bul
                prep_stars_symbols = acc_symbols.intersection(warm_symbols)
                
                if prep_stars_symbols:
                    # Kesişenleri Hacime Göre Sıralamak İçin Liste Oluştur
                    prep_star_list = []
                    for sym in prep_stars_symbols:
                        # Veriyi accum_data'dan çek
                        row = acc_df[acc_df['Sembol'] == sym].iloc[0]
                        vol = row.get('Hacim', 0)
                        price = row['Fiyat']
                        prep_star_list.append({'sym': sym, 'price': price, 'vol': vol})
                    
                    # SIRALAMA: Hacme Göre Büyükten Küçüğe
                    prep_star_list.sort(key=lambda x: x['vol'], reverse=True)

                    for item in prep_star_list:
                        stars_found = True
                        sym = item['sym']
                        label = f"⏳ {sym.replace('.IS', '')} ({item['price']}) | HAZIRLIK"
                        if st.button(label, key=f"star_prep_{sym}", use_container_width=True):
                            on_scan_result_click(sym)
                            st.rerun()
        if not stars_found:
            if not has_accum:
                st.caption("💎'Endeksi Yenen Güçlü Hisseler / Breakout Ajanı' ve ⏳'Akıllı Para Topluyor / Breakout Ajanı' taramalarının ortak sonuçları gösterilir.")
            elif not (has_warm or has_break):
                st.caption("💎'Endeksi Yenen Güçlü Hisseler / Breakout Ajanı' ve ⏳'Akıllı Para Topluyor / Breakout Ajanı' taramalarının ortak sonuçları gösterilir.")
            else:
                st.warning("Şu an toplanan ORTAK bir hisse yok.")
    # ==============================================================================
    # ⚓ DİPTEN DÖNÜŞ PANELİ (Sidebar'a Taşındı)
    # ==============================================================================
    
    # --- HATAYI ÖNLEYEN BAŞLATMA KODLARI (EKLEME) ---
    if 'bear_trap_data' not in st.session_state: st.session_state.bear_trap_data = None
    if 'rsi_div_bull' not in st.session_state: st.session_state.rsi_div_bull = None
    # -----------------------------------------------

    # 1. Veri Kontrolü
    has_bt = st.session_state.bear_trap_data is not None and not st.session_state.bear_trap_data.empty
    has_div = st.session_state.rsi_div_bull is not None and not st.session_state.rsi_div_bull.empty
    
    reversal_list = []
    
    # 2. Kesişim Mantığı
    if has_bt and has_div:
        bt_df = st.session_state.bear_trap_data
        div_df = st.session_state.rsi_div_bull
        
        # Sembol Kümeleri
        bt_syms = set(bt_df['Sembol'].values)
        div_syms = set(div_df['Sembol'].values)
        
        # Ortak Olanlar (Kesişim)
        common_syms = bt_syms.intersection(div_syms)
        
        for sym in common_syms:
            # Verileri al
            row_bt = bt_df[bt_df['Sembol'] == sym].iloc[0]
            row_div = div_df[div_df['Sembol'] == sym].iloc[0]
            
            reversal_list.append({
                'Sembol': sym,
                'Fiyat': row_bt['Fiyat'],
                'Zaman': row_bt['Zaman'],       # Örn: 2 Mum Önce
                'RSI': int(row_div['RSI']) # Örn: 28
            })
            
    # 3. DİPTEN DÖNÜŞ PANELİ)
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background: linear-gradient(45deg, #06b6d4, #3b82f6); color: white; padding: 8px; border-radius: 6px; text-align: center; font-weight: 700; font-size: 0.9rem; margin-bottom: 10px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
        ⚓ DİPTEN DÖNÜŞ?
    </div>
    """, unsafe_allow_html=True)
    
    with st.container(height=150):
        if reversal_list:
            # RSI değerine göre (Düşük RSI en üstte) sıralayalım
            reversal_list.sort(key=lambda x: x['RSI']) 
            
            for item in reversal_list:
                # Buton Etiketi: 💎 GARAN (150.20) | RSI:28 | 2 Mum Önce
                label = f"💎 {item['Sembol'].replace('.IS', '')} ({item['Fiyat']:.2f}) | RSI:{item['RSI']} | {item['Zaman']}"
                
                if st.button(label, key=f"rev_btn_sidebar_{item['Sembol']}", use_container_width=True):
                    on_scan_result_click(item['Sembol'])
                    st.rerun()
        else:
            if not (has_bt and has_div):
                st.caption("'Ayı Tuzağı' ve 'RSI Uyumsuzluk' taramalarının ortak sonuçları burada gösterilir.")
            else:
                st.info("Şu an hem tuzağa düşürüp hem uyumsuzluk veren (Kesişim) hisse yok.")

    # 4. AI ANALIST PANELİ
    with st.expander("🤖 AI Analist (Prompt)", expanded=True):
        st.caption("Verileri toplayıp Yapay Zeka için hazır metin oluşturur.")
        if st.button("📋 Analiz Metnini Hazırla", type="primary"): 
            st.session_state.generate_prompt = True

# ==============================================================================
# 6. ANA SAYFA (MAIN UI) - GÜNCELLENMİŞ MASTER SCAN VERSİYONU
# ==============================================================================

# Üst Menü Düzeni: Kategori | Varlık Listesi | DEV TARAMA BUTONU
col_cat, col_ass, col_btn = st.columns([1.5, 2, 1.5])

# 1. Kategori Seçimi
try: cat_index = list(ASSET_GROUPS.keys()).index(st.session_state.category)
except ValueError: cat_index = 0
with col_cat:
    st.selectbox("Kategori", list(ASSET_GROUPS.keys()), index=cat_index, key="selected_category_key", on_change=on_category_change, label_visibility="collapsed")

# 2. Varlık Listesi (Dropdown)
with col_ass:
    current_opts = ASSET_GROUPS.get(st.session_state.category, ASSET_GROUPS[INITIAL_CATEGORY]).copy()
    active_ticker = st.session_state.ticker
    if active_ticker not in current_opts:
        current_opts.insert(0, active_ticker)
        asset_idx = 0
    else:
        try: asset_idx = current_opts.index(active_ticker)
        except ValueError: asset_idx = 0
    st.selectbox("Varlık Listesi", current_opts, index=asset_idx, key="selected_asset_key", on_change=on_asset_change, label_visibility="collapsed", format_func=lambda x: x.replace(".IS", ""))

# 3. MASTER SCAN BUTONU (Eski arama kutusu yerine geldi)
with col_btn:
    # Butona basıldığında çalışacak sihirli kod
    if st.button("🕵️ TÜM PİYASAYI TARA (MASTER SCAN)", type="primary", use_container_width=True):
        
        # --- A. HAZIRLIK ---
        st.toast("Ajanlar göreve çağrılıyor...", icon="🕵️")
        scan_list = ASSET_GROUPS.get(st.session_state.category, [])
        
        # İlerleme Çubuğu ve Bilgi Mesajı
        progress_text = "Operasyon Başlıyor..."
        my_bar = st.progress(0, text=progress_text)
        
        try:
            # 1. ÖNCE VERİYİ ÇEK (Yahoo Koruması) - %10
            # En geniş veriyi (2y) bir kez çağırıyoruz ki önbelleğe (cache) girsin.
            # Diğer ajanlar cache'den okuyacağı için Yahoo'ya tekrar gitmeyecekler.
            my_bar.progress(10, text="📡 Veriler İndiriliyor (Batch Download)...%10")
            get_batch_data_cached(scan_list, period="2y")
            
            # 2. STP & MOMENTUM AJANI - %15
            my_bar.progress(15, text="⚡ STP ve Momentum Taranıyor...%15")
            crosses, trends, filtered = scan_stp_signals(scan_list)
            st.session_state.stp_crosses = crosses
            st.session_state.stp_trends = trends
            st.session_state.stp_filtered = filtered
            st.session_state.stp_scanned = True

            # 3. ICT SNIPER AJANI --- %20
            my_bar.progress(20, text="🦅 ICT Sniper Kurulumları (Liquidity+MSS+FVG) Taranıyor...%20")
            st.session_state.ict_scan_data = scan_ict_batch(scan_list)

            # 5. PATLAMA ADAYLARI / GRANDMASTER - %35
            my_bar.progress(35, text="🚀 Grandmaster Patlama Adayları Taranıyor...%35")
            st.session_state.gm_results = scan_grandmaster_batch(scan_list)

            # 6. SENTIMENT (AKILLI PARA) AJANI - %40
            my_bar.progress(40, text="🤫 Gizli Toplama (Smart Money) Aranıyor...%40")
            st.session_state.accum_data = scan_hidden_accumulation(scan_list)
            
            # 7. RS LİDERLERİ TARAMASI - %45
            my_bar.progress(45, text="🏆 Son 5 günün Piyasa Liderleri (RS Momentum) Hesaplanıyor...%45")
            st.session_state.rs_leaders_data = scan_rs_momentum_leaders(scan_list)
            
            # 8. BREAKOUT AJANI (ISINANLAR/KIRANLAR) - %55
            my_bar.progress(55, text="🔨 Kırılımlar ve Hazırlıklar Kontrol Ediliyor...%55")
            st.session_state.breakout_left = agent3_breakout_scan(scan_list)      # Isınanlar
            st.session_state.breakout_right = scan_confirmed_breakouts(scan_list) # Kıranlar
            
            # 9. RADAR 1 & RADAR 2 (GENEL TEKNİK) - %65
            my_bar.progress(65, text="🧠 Radar Sinyalleri İşleniyor...%65")
            st.session_state.scan_data = analyze_market_intelligence(scan_list)
            st.session_state.radar2_data = radar2_scan(scan_list)
            
            # 10. FORMASYON & TUZAKLAR - %75
            my_bar.progress(75, text="🦁Formasyon ve Tuzaklar Taranıyor...%75")
            st.session_state.pattern_data = scan_chart_patterns(scan_list)
            st.session_state.bear_trap_data = scan_bear_traps(scan_list)
            
            # 11. RSI UYUMSUZLUKLARI - %85
            my_bar.progress(85, text="⚖️ RSI Uyumsuzlukları Hesaplanıyor...%85")
            bull_df, bear_df = scan_rsi_divergence_batch(scan_list)
            st.session_state.rsi_div_bull = bull_df
            st.session_state.rsi_div_bear = bear_df

            # 12. MİNERVİNİ SEPA AJANI - %95
            my_bar.progress(95, text="🦁 Minervini Sepa Taranıyor...%95")
            st.session_state.minervini_data = scan_minervini_batch(scan_list)

            # --- BİTİŞ ---
            my_bar.progress(100, text="✅ TARAMA TAMAMLANDI! Sonuçlar Yükleniyor...%100")
            st.session_state.generate_prompt = False # Eski prompt varsa temizle
            st.rerun() # Sayfayı yenile ki tablolar dolsun
            
        except Exception as e:
            st.error(f"Tarama sırasında bir hata oluştu: {str(e)}")
            st.stop()

st.markdown("<hr style='margin-top:0.5rem; margin-bottom:0.5rem;'>", unsafe_allow_html=True)

if st.session_state.generate_prompt:
    t = st.session_state.ticker
    clean_ticker = t.replace(".IS", "").replace("-USD", "").replace("=F", "")
    # --- 1. GEREKLİ VERİLERİ TOPLA ---
    info = fetch_stock_info(t)
    df_hist = get_safe_historical_data(t) # Ana veri
    
    # EKSİK OLAN TANIMLAMALAR EKLENDİ (bench_series ve idx_data)
    cat_for_bench = st.session_state.category
    bench_ticker = "XU100.IS" if "BIST" in cat_for_bench else "^GSPC"
    bench_series = get_benchmark_data(cat_for_bench)
    idx_data = get_safe_historical_data(bench_ticker)['Close'] if bench_ticker else None
    # Teknik verileri çeken fonksiyonunuzu çağırıyoruz
    tech_vals = get_tech_card_data(t) 
    # Eğer veri geldiyse değişkenlere atıyoruz, gelmediyse 0 diyoruz
    if tech_vals:
        sma50_val  = tech_vals.get('sma50', 0)
        sma100_val = tech_vals.get('sma100', 0)
        sma200_val = tech_vals.get('sma200', 0)
        ema144_val = tech_vals.get('ema144', 0)
    else:
        sma50_val = 0
        sma100_val = 0
        sma200_val = 0
        ema144_val = 0    
    # Diğer Hesaplamalar
    ict_data = calculate_ict_deep_analysis(t) or {}
    sent_data = calculate_sentiment_score(t) or {}
    tech_data = get_tech_card_data(t) or {}
    pa_data = calculate_price_action_dna(t) or {}
    levels_data = get_advanced_levels_data(t) or {}
    synth_data = calculate_synthetic_sentiment(t)

    # --- Arada verileri çekebiliriz Para Akışı İvmesi ---
    if synth_data is not None and not synth_data.empty:
        son_satir = synth_data.iloc[-1]
        guncel_ivme = float(son_satir['MF_Smooth'])
        guncel_stp = float(son_satir['STP'])
        guncel_fiyat = float(son_satir['Price'])
        denge_sapmasi = ((guncel_fiyat / guncel_stp) - 1) * 100
        ivme_yonu = "YÜKSELİŞ (Pozitif)" if guncel_ivme > 0 else "DÜŞÜŞ (Negatif)"
    else:
        # Veri gelmezse AI hata almasın diye varsayılan değerler
        guncel_ivme = 0; guncel_stp = 0; guncel_fiyat = 0; denge_sapmasi = 0; ivme_yonu = "Bilinmiyor"
    mini_data = calculate_minervini_sepa(t) or {} 
    master_score, pros, cons = calculate_master_score(t)
    lorentzian_bilgisi = render_lorentzian_panel(t, just_text=True)
    # --- YENİ: AI İÇİN S&D VE LİKİDİTE VERİLERİ ---
    try: 
        sd_data = detect_supply_demand_zones(df_hist)
        sd_txt_ai = f"{sd_data['Type']} ({sd_data['Bottom']:.2f} - {sd_data['Top']:.2f}) Durum: {sd_data['Status']} olabilir." if sd_data else "Taze bölge görünmüyor."
    except: 
        sd_txt_ai = "Veri Yok"
        
    havuz_ai = ict_data.get('eqh_eql_txt', 'Yok')
    sweep_ai = ict_data.get('sweep_txt', 'Yok')
    # --- ALTIN FIRSAT DURUMU HESAPLAMA (Garantili Versiyon) ---
    rs_text_prompt = sent_data.get('rs', '').lower()
    # 1. Güç Kontrolü
    c_pwr = ("artıda" in rs_text_prompt or "lider" in rs_text_prompt or "pozitif" in rs_text_prompt or 
             sent_data.get('total', 0) >= 50 or sent_data.get('raw_rsi', 0) > 50)
    # 2. Konum Kontrolü
    c_loc = ("DISCOUNT" in ict_data.get('zone', '') or "MSS" in ict_data.get('structure', '') or 
             "BOS" in ict_data.get('structure', ''))
    # 3. Enerji Kontrolü
    c_nrg = ("Güçlü" in ict_data.get('displacement', '') or "Hacim" in sent_data.get('vol', '') or 
             sent_data.get('raw_rsi', 0) > 55)
    # Final Onay Durumu
    is_golden = "🚀 EVET (3/3 Onaylı - KRİTİK FIRSAT)" if (c_pwr and c_loc and c_nrg) else "HAYIR"

    # --- ROYAL FLUSH DURUMU HESAPLAMA (4/4 Kesişim) ---
    # 1. Yapı: BOS veya MSS Bullish olmalı
    c_struct = "BOS (Yükseliş" in ict_data.get('structure', '') or "MSS" in ict_data.get('structure', '')
    # 2. Zeka: Lorentzian 7/8 veya 8/8 olmalı
    lor_data_prompt = calculate_lorentzian_classification(t)
    c_ai = False
    if lor_data_prompt and lor_data_prompt['signal'] == "YÜKSELİŞ" and lor_data_prompt['votes'] >= 7:
        c_ai = True
    # 3. Güç: Alpha Pozitif olmalı (RS Liderliği)
    c_rs = pa_data.get('rs', {}).get('alpha', 0) > 0
    # 4. Maliyet: VWAP sapması %12'den az olmalı (Güvenli Zemin)
    c_vwap = pa_data.get('vwap', {}).get('diff', 0) < 12
    # Final Royal Flush Onayı
    is_royal = "♠️ EVET (4/4 KRALİYET SET-UP - EN YÜKSEK OLASILIK)" if (c_struct and c_ai and c_rs and c_vwap) else "HAYIR"

    # [YENİ EKLENTİ] MOMENTUM DEDEKTİFİ (Yorgun Boğa Analizi)
    momentum_analiz_txt = "Veri Yok"
    if synth_data is not None and not synth_data.empty:
        # Son satırdaki MF_Smooth (Bar Rengi) verisini al
        last_mf = float(synth_data.iloc[-1]['MF_Smooth'])
        # Günlük fiyat değişimini al
        p_change = info.get('change_pct', 0)

        if last_mf > 0:
            momentum_analiz_txt = "✅ GÜÇLÜ (Uyumlu): Momentum barı MAVİ. Para akışı fiyatı destekliyor."
        else:
            # Bar Kırmızı (Negatif) ise şimdi Fiyata bakıyoruz
            if p_change >= 0:
                # SENARYO: Fiyat Yükseliyor AMA Bar Kırmızı -> SENİN CÜMLEN BURADA
                momentum_analiz_txt = "⚠️ UYARI (YORGUN BOĞA mı yoksa DEVAM mı): Fiyat hala tepede görünüyor olabilir ama aldanma. Son 6 günün ortalama hızının altına düştük: Bu yükselişin yakıtını sorgulamak gerekebilir, yakıt bitmiş olabilir, sadece rüzgarla gidiyor olabiliriz. 1) Eğer hacim düşükse bu bir 'Bayrak/Flama' (Güç Toplama) olabilir. 2) Eğer hacim yüksekse bu bir 'Mal Çıkışı' (Yorgun Boğa) olabilir. Stopları yaklaştır ve kırılımı bekle."
            else:
                # SENARYO: Fiyat Düşüyor VE Bar Kırmızı -> NORMAL
                momentum_analiz_txt = "🔻 ZAYIF (Uyumlu): Düşüş trendi momentumla teyit ediliyor."
    # -----------------------------------------------------------    
    # --- 2. AJAN HESAPLAMALARI ---
    stp_res = process_single_stock_stp(t, df_hist)                   
    acc_res = process_single_accumulation(t, df_hist, bench_series) 
    bo_res = process_single_breakout(t, df_hist)                     
    pat_df = scan_chart_patterns([t])                                
    bt_res = process_single_bear_trap_live(df_hist)                  
    r2_res = process_single_radar2(t, df_hist, idx_data, 0, 999999, 0)

    # --- 3. SICAK İSTİHBARAT ÖZETİ (AI SİNYAL KUTUSU - DERİNLEŞTİRİLMİŞ) ---
    scan_box_txt = []
    
    # A. ELİT KURULUMLAR (Sistemin En Tepesi)
    if is_royal != "HAYIR": 
        scan_box_txt.append("👑 ELİT KURULUM: ROYAL FLUSH (4/4 Onay. Algoritmik kusursuzluk! Kurumsal fonların en sevdiği, başarı ihtimali en yüksek asimetrik risk/ödül noktası olabilir.)")
    elif is_golden != "HAYIR": 
        scan_box_txt.append("🏆 ALTIN FIRSAT: Golden Trio Onaylandı (Fiyat ucuz, trend güçlü, hacim destekliyor. Büyük bir hareketin arifesinde olabilir.)")

    # B. ICT & MARKET YAPISI (Kurumsal Ayak İzleri)
    if ict_data and ict_data.get('status') != 'Error':
        struct_txt = ict_data.get('structure', '')
        if "MSS" in struct_txt or "BOS" in struct_txt:
            scan_box_txt.append(f"🦅 YAPI KIRILIMI (ICT): {struct_txt} (KRİTİK: Akıllı para piyasa yapısını kırmış görünüyor. Önceki trend bozuldu, yeni bir likidite arayışı başlıyor.)")

    # C. SMART MONEY (Sessiz Toplama / Hacim Patlaması)
    if acc_res:
        if acc_res.get('Pocket_Pivot', False):
            scan_box_txt.append("⚡ AKILLI PARA: Pocket Pivot (Hacimli Kurumsal Alım. Küçük yatırımcı uyurken tahtaya para girişi yapılmış gibi görünüyor.)")
        else:
            scan_box_txt.append("🤫 AKILLI PARA: Sessiz Toplama (Fiyat yatay veya baskılı görünse de arka planda sinsi bir fon alımı var. Kırılım hazırlığı..)")

    # D. STP MOMENTUM (Kısa Vadeli İvme ve Duygu Durumu)
    if stp_res:
        if stp_res['type'] == 'cross_up': 
            scan_box_txt.append("🟢 STP MOMENTUM: Denge Yukarı Kırıldı (Kısa vadeli alıcılar iştahlandı, taze bir yükseliş ivmesi tetiklendi.)")
        elif stp_res['type'] == 'cross_down': 
            scan_box_txt.append("🔴 STP MOMENTUM: Denge Aşağı Kırıldı (Kısa vadeli likidite çıkışı var, satıcı baskısı an itibariyle taze ve tehlikeli.)")
        elif stp_res['type'] == 'trend_up': 
            scan_box_txt.append(f"📈 STP MOMENTUM: Pozitif Trend ({stp_res['data'].get('Gun','?')} Gündür trend alıcıların kontrolünde görünüyor.)")
        elif stp_res['type'] == 'trend_down': 
            scan_box_txt.append(f"📉 STP MOMENTUM: Negatif Trend ({stp_res['data'].get('Gun','?')} Gündür ayılar tahtayı baskılıyor)")

    # E. FORMASYON (Geometrik Yapılar)
    if not pat_df.empty:
        scan_box_txt.append(f"📐 GEOMETRİK YAPI: {pat_df.iloc[0]['Formasyon']} (Teknik analistlerin ve algoritmaların ekranına düşecek bir formasyon.)")

    # F. TUZAKLAR VE LİKİDİTE AVI (Veto Sebepleri)
    if bt_res:
        scan_box_txt.append(f"🪤 LİKİDİTE AVI (Bear Trap): {bt_res['Zaman']} oluştu. (Panikleyen retail yatırımcının stopları patlatılmış ve ucuz mal kurumsallar tarafından süpürülmüş olabilir. Vol: {bt_res['Hacim_Kat']})")

    # G. BREAKOUT (Kırılım Ajanı)
    if bo_res:
        if "TETİKLENDİ" in bo_res['Zirveye Yakınlık']:
            scan_box_txt.append("🔨 DİRENÇ KIRILIMI: Breakout Tetiklendi! (Önemli bir direnç hacimle aşıldı, 'Fiyat Keşfi' moduna geçiliyor olabilir.)")
        elif "Sıkışma" in bo_res['Zirveye Yakınlık']:
            scan_box_txt.append("💣 VOLATİLİTE DARALMASI: Bir Sıkışma (Squeeze) var. (Enerji birikti, yay gerildi. Her an sert bir yön patlaması gelebilir.)")

    # H. İSTATİSTİKSEL ANOMALİLER (Z-Score Aşırılıkları)
    try:
        z_val = calculate_z_score_live(df_hist)
        if z_val >= 2.0: 
            scan_box_txt.append(f"🚨 İSTATİSTİKSEL ANOMALİ: Z-Score +{z_val:.1f} (DİKKAT: Fiyat ortalamalardan matematiksel olarak saptı. 'Mean Reversion' yani aşağı yönlü düzeltme riski masada!)")
        elif z_val <= -2.0: 
            scan_box_txt.append(f"🚨 İSTATİSTİKSEL ANOMALİ: Z-Score {z_val:.1f} (DİKKAT: Aşırı satım bölgesi. Fiyat o kadar ucuzladı ki, istatistiksel bir yukarı tepki sıçraması ihtimali artıyor.)")
    except: pass

    # I. GİZLİ YALANLAR: RSI Uyumsuzluk ve Smart Volume Anomalileri
    if pa_data:
        # Uyumsuzluk
        div_type = pa_data.get('div', {}).get('type', 'neutral')
        if div_type == 'bearish': 
            scan_box_txt.append("⚠️ GİZLİ YALAN (Negatif Uyumsuzluk): Fiyat yeni zirve yapıyor ama RSI (Momentum) düşüyor. (Yorgun boğa! Fiyat çıkarken mal dağıtılıyor olabilir.)")
        elif div_type == 'bullish': 
            scan_box_txt.append("💎 GİZLİ GÜÇ (Pozitif Uyumsuzluk): Fiyat yeni dip yapıyor ama RSI yükseliyor. (Satıcılar yorulmuş görünüyor, büyükler dipten topluyor olabilir.)")
        
        # Hacim Anomalisi (Stopping / Climax)
        sv_data = pa_data.get('smart_volume', {})
        if sv_data.get('stopping') != 'Yok': 
            scan_box_txt.append("🐋 BALİNA İZİ (Stopping Volume): Düşüş nihayet yüksek bir hacimle karşılanmış görünüyor. (Kurumsal fren mekanizması devrede, düşüş durduruluyor olabilir.)")
        if sv_data.get('climax') != 'Yok': 
            scan_box_txt.append("🌋 BALİNA İZİ (Climax Volume): Rallinin zirvesinde anormal bir hacim var. (Müzik durmak üzere ve akıllı para malı küçük yatırımcıya boşaltıyor olabilir!)")

    # Eğer hiçbir sıcak sinyal yoksa:
    if not scan_box_txt:
        scan_box_txt.append("⚖️ PİYASA DURUMU NÖTR: An itibariyle sıcak bir kırılım, anomali veya tuzak tespit edilmedi. Standart fiyat hareketi (Konsolidasyon) devam ediyor.")

    scan_summary_str = "\n".join([f"- {s}" for s in scan_box_txt])

    # --- 4. DEĞİŞKEN TANIMLAMA (HATAYI ÇÖZEN KISIM) ---
    # Kodun eski halinde bu değişkenler tanımlanmadığı için NameError veriyordu.
    
    # SMA50 Durumu
    curr_price = info.get('price', 0) if info else 0
    sma50_val = tech_data.get('sma50', 0)
    sma50_str = "ÜZERİNDE (Pozitif)" if curr_price > sma50_val else "ALTINDA (Negatif)"

    # --- EMA HESAPLAMALARI (YENİ EKLENEN KISIM) ---
    # df_hist verisinden EMA'ları hesaplayalım
    df_hist['EMA8'] = df_hist['Close'].ewm(span=8, adjust=False).mean()
    df_hist['EMA13'] = df_hist['Close'].ewm(span=13, adjust=False).mean()

    ema8_val = df_hist['EMA8'].iloc[-1]
    ema13_val = df_hist['EMA13'].iloc[-1]
    
    # Fiyatın bu ortalamalara göre durumu
    ema8_status = "Üstünde (Kısa Vadede Güçlü)" if curr_price > ema8_val else "Altında (Kısa Vadede Zayıflama var)"
    ema13_status = "Üstünde (Destek)" if curr_price > ema13_val else "Altında (Direnç)"

    # Fark yüzdeleri
    diff_ema8 = ((curr_price / ema8_val) - 1) * 100
    diff_ema13 = ((curr_price / ema13_val) - 1) * 100

    ema_txt = f"EMA8: {ema8_val:.2f} ({ema8_status} %{diff_ema8:.1f}) | EMA13: {ema13_val:.2f} ({ema13_status} %{diff_ema13:.1f})"

    # Destek/Direnç (Levels Data'dan çekme)
    fib_res = "-"
    fib_sup = "-"
    if levels_data:
        # nearest_res bir tuple döner: (Etiket, Fiyat)
        res_tuple = levels_data.get('nearest_res')
        sup_tuple = levels_data.get('nearest_sup')
        if res_tuple: fib_res = f"{res_tuple[1]:.2f} ({res_tuple[0]})"
        if sup_tuple: fib_sup = f"{sup_tuple[1]:.2f} ({sup_tuple[0]})"

    # Likidite Hedefi
    liq_str = f"{ict_data.get('target', 0):.2f}" if ict_data else "-"

    # Price Action Tanımları
    mum_desc = "-"
    pa_div = "-"
    sfp_desc = "-"
    loc_desc = "-"
    if pa_data:
        mum_desc = pa_data.get('candle', {}).get('desc', '-')
        
        sfp_info = pa_data.get('sfp', {})
        sfp_desc = f"{sfp_info.get('title', '-')} ({sfp_info.get('desc', '-')})"
        
        # Ekstra: Konum (Structure) bilgisini de ekleyelim, AI sevinir.
        loc_info = pa_data.get('loc', {})
        loc_desc = f"{loc_info.get('title', '-')} - {loc_info.get('desc', '-')}"

        # --- GÜNCELLENEN RSI KISMI ---
        div_data = pa_data.get('div', {})
        div_title = div_data.get('title', '-')
        div_reason = div_data.get('desc', '-')
        pa_div = f"{div_title} -> DETAY: {div_reason}"
    
    # --- SMART MONEY VERİLERİ (AI İÇİN HAZIRLIK) ---
    # Önce varsayılan değerleri atayalım (Veri yoksa hata vermesin)
    v_val = 0; v_diff = 0; vwap_ai_txt = "Veri Yok"; rs_ai_txt = "Veri Yok"; alpha_val = 0

    if pa_data: # Eğer Price Action verisi varsa hesapla
        # VWAP Verisi
        vwap_info = pa_data.get('vwap', {'val': 0, 'diff': 0})
        v_val = vwap_info['val']
        v_diff = vwap_info['diff']
        
        # VWAP Yorumu (Trend Dostu Mantık)
        if v_diff < -2.0: vwap_ai_txt = "DİP FIRSATI (Aşırı İskonto)"
        elif v_diff < 0.0: vwap_ai_txt = "UCUZ (Toplama Bölgesi)"
        elif v_diff < 8.0: vwap_ai_txt = "RALLİ MODU (Güçlü Trend - Güvenli)"
        elif v_diff < 15.0: vwap_ai_txt = "ISINIYOR (Dikkatli Takip Gerekir)"
        else: vwap_ai_txt = "PARABOLİK (Aşırı Kopuş - Riskli)"

        # RS Verisi
        rs_info = pa_data.get('rs', {'alpha': 0})
        alpha_val = rs_info['alpha']
        
        # RS Yorumu
        if alpha_val > 1.0: rs_ai_txt = "LİDER (Endeksi Yeniyor - Güçlü)"
        elif alpha_val < -1.0: rs_ai_txt = "ZAYIF (Endeksin Gerisinde - İlgi Yok)"
        else: rs_ai_txt = "NÖTR (Endeksle Paralel)"
    # --- HARSI ANALİZİ (AI PROMPT İÇİN) ---
    harsi_prompt_data = calculate_harsi(df_hist)
    harsi_txt = "Veri Yok"
    if harsi_prompt_data:
        harsi_txt = f"{harsi_prompt_data['status']} (HA-RSI Değeri: {harsi_prompt_data['ha_close']:.2f})"
        if harsi_prompt_data['is_green']:
            harsi_txt += " | Görünüm: POZİTİF (Yeşil Bar - Momentum Artıyor)"
        else:
            harsi_txt += " | Görünüm: NEGATİF (Kırmızı Bar - Momentum Kayboluyor)"
    # Diğer Metin Hazırlıkları
    radar_val = "Veri Yok"; radar_setup = "Belirsiz"
    r1_txt = "Veri Yok"
    if st.session_state.radar2_data is not None and not st.session_state.radar2_data.empty:
        if 'Sembol' in st.session_state.radar2_data.columns:
            r_row = st.session_state.radar2_data[st.session_state.radar2_data['Sembol'] == t]
            if not r_row.empty:
                radar_val = f"{r_row.iloc[0]['Skor']}/7"
                radar_setup = r_row.iloc[0]['Setup']
    
    if st.session_state.scan_data is not None and not st.session_state.scan_data.empty:
        col_name = 'Sembol' if 'Sembol' in st.session_state.scan_data.columns else 'Ticker'
        if col_name in st.session_state.scan_data.columns:
            r_row = st.session_state.scan_data[st.session_state.scan_data[col_name] == t]
            if not r_row.empty: r1_txt = f"Skor: {r_row.iloc[0]['Skor']}/7"
            
    r2_txt = f"Skor: {radar_val} | Setup: {radar_setup}"

    # --- GERÇEK PARA AKIŞI (OBV & DIVERGENCE) ---
    para_akisi_txt = "Nötr"

    # df_hist değişkeninin yukarıda tanımlı olduğundan emin ol (genelde prompt başında tanımlıdır)
    if 'df_hist' in locals() and df_hist is not None and len(df_hist) > 20:
        # 1. OBV Hesapla
        change = df_hist['Close'].diff()
        direction = np.sign(change).fillna(0)
        obv = (direction * df_hist['Volume']).cumsum()

        # 2. Trendleri Kıyasla (Son 10 Gün)
        p_now = df_hist['Close'].iloc[-1]; p_old = df_hist['Close'].iloc[-11]
        obv_now = obv.iloc[-1]; obv_old = obv.iloc[-11]

        price_trend = "YUKARI" if p_now > p_old else "AŞAĞI"
        obv_trend = "YUKARI" if obv_now > obv_old else "AŞAĞI"
        
        # --- [YENİ] Prompt İçin RSI Emniyet Kilidi ---
        # AI'ın tepede "Gizli Giriş" diye saçmalamasını engeller.
        delta_p = df_hist['Close'].diff()
        gain_p = (delta_p.where(delta_p > 0, 0)).rolling(14).mean()
        loss_p = (-delta_p.where(delta_p < 0, 0)).rolling(14).mean()
        rsi_val_prompt = 100 - (100 / (1 + gain_p/loss_p)).iloc[-1]

        # 3. Yorumla (Güncellenmiş Mantık)
        if rsi_val_prompt > 60 and price_trend == "AŞAĞI":
             # Fiyat düşüyor ama RSI hala tepedeyse bu giriş değil, "Mal Yedirme" olabilir.
             para_akisi_txt = "⚠️ ZİRVE BASKISI (Dağıtım Riski - RSI Şişkin)"
        elif price_trend == "AŞAĞI" and obv_trend == "YUKARI":
            para_akisi_txt = "🔥 GİZLİ GİRİŞ (Pozitif Uyumsuzluk - Fiyat Düşerken Mal Toplanıyor olabilir)"
        elif price_trend == "YUKARI" and obv_trend == "AŞAĞI":
            para_akisi_txt = "⚠️ GİZLİ ÇIKIŞ (Negatif Uyumsuzluk - Fiyat Çıkarken Mal Çakılıyor olabilir)"
        elif obv_trend == "YUKARI":
            para_akisi_txt = "Pozitif (Para Girişi Fiyatı Destekliyor)"
        else:
            para_akisi_txt = "Negatif (Para Çıkışı Var)"
            
    elif synth_data is not None and len(synth_data) > 15:
        # Yedek Plan: df_hist yoksa eski yöntemi kullan
        wma_now = synth_data['MF_Smooth'].tail(10).mean()
        para_akisi_txt = "Pozitif (Giriş Var)" if wma_now > 0 else "Negatif (Çıkış Var)"
        
    mini_txt = "Veri Yok"
    if mini_data:
        mini_txt = f"{mini_data.get('Durum', '-')} | RS Rating: {mini_data.get('rs_rating', '-')}"
        if mini_data.get('is_vcp'): mini_txt += " | VCP Var"
            
    def clean_html_val(key):
            val = sent_data.get(key, '0/0')
            return re.sub(r'<[^>]+>', '', str(val))
    
    sent_yapi = clean_html_val('str')
    sent_trend = clean_html_val('tr')
    sent_hacim = clean_html_val('vol')
    sent_mom = clean_html_val('mom')
    sent_vola = clean_html_val('vola')
    
    fiyat_str = f"{info.get('price', 0):.2f}" if info else "0.00"
    master_txt = f"{master_score}/100"
    pros_txt = ", ".join(pros[:5])
    
    st_txt = f"{'YÜKSELİŞ' if levels_data.get('st_dir')==1 else 'DÜŞÜŞ'} | {levels_data.get('st_val',0):.2f}" if levels_data else "-"
    # ==============================================================================
    # 🧠 ALGORİTMİK KARAR MATRİSİ V3.0 (FULL-CYCLE SCENARIO DETECTOR)
    # ==============================================================================
    # 1. TEMEL METRİKLERİN HESAPLANMASI
    # ---------------------------------------------------------
    try:
        # Fiyat & Değişim
        p_now = info.get('price', 0)
        p_change_pct = info.get('change_pct', 0) # Günlük Yüzde Değişim
        
        # Trend Gücü (SMA50 Referansı) ve Yönü
        sma50_val = tech_data.get('sma50', 0)
        trend_ratio = (p_now / sma50_val) if sma50_val > 0 else 1.0
        # Trendin Eğimi (Pozitif: Yukarı yönlü, Negatif: Aşağı yönlü)
        sma50_slope = tech_data.get('sma50_slope', 1) 
        
        # Hacim Oranı (20 Günlük Ortalamaya Göre)
        vol_ratio = 1.0
        if df_hist is not None and len(df_hist) > 20:
            v_curr = float(df_hist['Volume'].iloc[-1])
            v_avg = float(df_hist['Volume'].rolling(20).mean().iloc[-1])
            if v_avg > 0: vol_ratio = v_curr / v_avg

        # STP Durumu (Momentum)
        is_stp_broken = False
        if synth_data is not None and not synth_data.empty:
            l_p = float(synth_data.iloc[-1]['Price'])
            l_s = float(synth_data.iloc[-1]['STP'])
            if l_p < l_s: is_stp_broken = True
            
        # RSI Durumu (Negatif ve Pozitif Uyumsuzluklar)
        rsi_val_now = sent_data.get('raw_rsi', 50)
        is_rsi_div_neg = "NEGATİF" in str(pa_data.get('div', {}).get('title', '')).upper()
        is_rsi_div_pos = "POZİTİF" in str(pa_data.get('div', {}).get('title', '')).upper()
        
        # Mum Durumu (İyi ve Kötü Formasyonlar)
        mum_str = str(mum_desc)
        bad_candles = ["Black Crows", "Bearish Engulfing", "Shooting Star", "Marubozu 🔻"]
        has_bad_candle = any(x in mum_str for x in bad_candles)
        good_candles = ["Hammer", "Bullish Engulfing", "Morning Star", "Marubozu 🔺", "Doji 🟢"]
        has_good_candle = any(x in mum_str for x in good_candles)

    except:
        # Veri hatası olursa çökmemesi için tüm varsayılan değerler
        p_change_pct = 0; trend_ratio = 1.0; vol_ratio = 1.0; is_stp_broken = False; rsi_val_now = 50
        is_rsi_div_neg = False; is_rsi_div_pos = False; has_bad_candle = False; has_good_candle = False; sma50_slope = 1

    # 2. SENARYO TESPİT MOTORU (12 SENARYO - TAM DÖNGÜ)
    # ---------------------------------------------------------
    ai_scenario_title = "NORMAL PİYASA AKIŞI"
    ai_mood_instruction = "Veriler nötr/karışık. Yön tayini zor. Her iki yönü de (Destek/Direnç) dengeli anlat."
    
    # --- 1. EN UÇ SENARYOLAR (AŞIRILIKLAR) ---
    
    # SENARYO 1: 🚀 AŞIRI ALIM ÇILGINLIĞI (FOMO)
    if (p_change_pct > 4.0) and (vol_ratio > 1.5) and (trend_ratio > 1.10) and (rsi_val_now > 75):
        ai_scenario_title = "🚀 SENARYO: AŞIRI ALIM ÇILGINLIĞI (FOMO)"
        ai_mood_instruction = """
        DURUM: Fiyat parabolik uçuyor. Hacim coşmuş, RSI aşırı alımda ve fiyat SMA50'den çok uzak (Köpük).
        TALİMAT: Yeni alım yapmanın (FOMO) çok riskli olduğunu belirt. Kâr al seviyelerini yukarı taşıma (Trailing Stop) mantığını anlat.
        """

    # SENARYO 2: 🩸 KAPİTÜLASYON (PANİK SATIŞI)
    elif (p_change_pct < -5.0) and (vol_ratio > 1.8) and (rsi_val_now < 30):
        ai_scenario_title = "🩸 SENARYO: KAPİTÜLASYON (PANIC SELLING)"
        ai_mood_instruction = """
        DURUM: Tam bir kan banyosu. İnanılmaz yüksek hacimle fiyat çöküyor. Ancak RSI aşırı satımda diplerde.
        TALİMAT: "Akıllı Para"nın dipten toplama fırsatı olabileceğini hissettir. "Düşen bıçak tutulmaz" de ama fırsat penceresini de arala.
        """

    # --- 2. DÖNÜŞ VE ANOMALİ SENARYOLARI ---

    # SENARYO 3: 🟢 DİPTEN DÖNÜŞ TEYİDİ (YENİ)
    # Şart: Fiyat dipte (trend_ratio < 0.98), %1.5'ten fazla yükselmiş, hacim iyi ve pozitif bir emare var.
    elif (p_change_pct >= 1.5) and (vol_ratio >= 1.2) and (trend_ratio < 0.98) and (has_good_candle or is_rsi_div_pos):
        ai_scenario_title = "🟢 SENARYO: DİPTEN DÖNÜŞ (RECOVERY)"
        ai_mood_instruction = """
        DURUM: Fiyat ana trendin çok altındaydı ama bugün güçlü bir hacim ve iyi bir mumla yukarı tepki verdi.
        TALİMAT: Bu hareketin bir "Dipten Dönüş" sinyali olabileceğini, akıllı paranın alıma geçtmiş olabileceğini, umut verici ama temkinli bir dille anlat.
        """

    # SENARYO 4: ⚫ TREND ÇÖKÜŞÜ (STOP-OUT)
    elif (p_change_pct < -2.5) and (vol_ratio > 1.1) and (trend_ratio < 0.99) and is_stp_broken and (sma50_slope <= 0 or has_bad_candle):
        ai_scenario_title = "⚫ SENARYO: TREND ÇÖKÜŞÜ (REVERSAL)"
        ai_mood_instruction = """
        DURUM: Sert ve hacimli bir düşüşle ana trend (SMA50) kırıldı. Ayılar kontrolü aldı.
        TALİMAT: Umut verme. "STOP-OUT" seviyesinin delindiğini belirt. En korumacı senaryoyu yaz.
        """ 

    # SENARYO 5: 🔴 DAĞITIM / CHURNING (GİZLİ SATIŞ)
    elif (abs(p_change_pct) < 1.5) and (vol_ratio > 1.3) and (trend_ratio > 1.05) and has_bad_candle:
        ai_scenario_title = "🔴 SENARYO: DAĞITIM / CHURNING (GİZLİ SATIŞ)"
        ai_mood_instruction = """
        DURUM: Hacim patlamış ama fiyat gitmiyor, üstelik satıcılı (kötü) bir mum var. (Patinaj)
        TALİMAT: "Hacim yüksek ama fiyat yerinde sayıyor, bu hayra alamet değil" de. Büyüklerin mal devrediyor olabileceğini uyar.
        """

    # SENARYO 6: ⚪ SIKIŞMA (CONSOLIDATION)
    elif (abs(p_change_pct) < 0.5) and (vol_ratio < 0.6) and (0.98 < trend_ratio < 1.02):
        ai_scenario_title = "⚪ SENARYO: SIKIŞMA (CONSOLIDATION / SQUEEZE)"
        ai_mood_instruction = """
        DURUM: Piyasada yaprak kımıldamıyor. Fiyat SMA50 civarında yataya bağlamış, hacim kurumuş.
        TALİMAT: "Fırtına öncesi sessizlik" temasını kullan. Yön tahmini yapma, büyük bir kırılımın yaklaştığını belirt.
        """

    # --- 3. TREND VE DÜZELTME SENARYOLARI ---

    # SENARYO 7: 📈 İSTİKRARLI YÜKSELİŞ (YENİ)
    # Şart: Sağlıklı yükseliş (%1 - %4 arası), hacim fena değil, trend yukarı bakıyor, kötü mum yok.
    elif (1.0 <= p_change_pct <= 4.0) and (vol_ratio >= 0.9) and (trend_ratio > 1.02) and (sma50_slope > 0) and not has_bad_candle:
        ai_scenario_title = "📈 SENARYO: İSTİKRARLI YÜKSELİŞ (MARKUP)"
        ai_mood_instruction = """
        DURUM: Trend yönü yukarı, hacim destekliyor ve fiyat istikrarlı şekilde yükseliyor. Kötü bir emare şimdilik yok.
        TALİMAT: Boğaların kontrolü elinde tuttuğunu, her şeyin yolunda olduğunu, desteklerin yukarı çekilerek (iz sürerek) trendin takip edilmesi gerektiğini söyle.
        """

    # SENARYO 8: 🐻 ÖLÜ KEDİ SIÇRAMASI (YENİ)
    # Şart: Trend aşağı bakıyor, fiyat SMA50 altında, fiyat yükselmiş AMA hacim çok düşük!
    elif (p_change_pct >= 1.0) and (trend_ratio < 0.98) and (sma50_slope <= 0) and (vol_ratio < 0.85):
        ai_scenario_title = "🐻 SENARYO: ÖLÜ KEDİ SIÇRAMASI (DEAD CAT BOUNCE)"
        ai_mood_instruction = """
        DURUM: Ana trend aşağı yönlü. Bugün fiyat yükseliyor gibi görünse de hacim çok zayıf.
        TALİMAT: Acemi yatırımcıyı uyar. Bunun kalıcı bir yükseliş değil, "Ölü Kedi Sıçraması" (Sahte yükseliş) olma ihtimalinin yüksek olduğunu vurgula.
        """

    # SENARYO 9: 🟡 KÂR REALİZASYONU (PROFIT TAKING)
    elif (-5.0 <= p_change_pct <= -1.5) and (0.85 <= vol_ratio <= 1.25) and (trend_ratio > 1.03) and is_stp_broken:
        ai_scenario_title = "🟡 SENARYO: KÂR REALİZASYONU (PROFIT TAKING)"
        ai_mood_instruction = """
        DURUM: Kısa vadeli momentum kırıldı. Ancak Ana Trend (SMA50) hala güvende.
        TALİMAT: Kısa vadeli düzeltmenin derinleşebileceğini, acele etmemek gerektiğini ve dönüş sinyali beklenmesini tavsiye et.
        """

    # SENARYO 10: 🟢 DİNLENEN BOĞA (HEALTHY PULLBACK)
    elif (-3.5 <= p_change_pct <= -0.5) and (vol_ratio < 0.85) and (trend_ratio > 1.03) and (sma50_slope > 0) and not has_bad_candle:
        ai_scenario_title = "🟢 SENARYO: DİNLENEN BOĞA (HEALTHY PULLBACK)"
        ai_mood_instruction = """
        DURUM: Fiyat düşüyor FAKAT Hacim çok düşük ve trend yönü hala yukarı. Kötü bir mum yok.
        TALİMAT: Asla "Çöküş" deme. Bunun "Düzeltme" olabileceğini yorumlar, sağlıklı düzeltme için gerekli şartların neler olduğunu sırala. Sabırlı olunması gerektiğini vurgula.
        """

    # SENARYO 11: 🟠 TREND SAVAŞI (MAJOR TEST)
    elif (0.985 <= trend_ratio <= 1.015) and is_stp_broken:
        ai_scenario_title = "🟠 SENARYO: TREND SAVAŞI (MAJOR TEST)"
        ai_mood_instruction = """
        DURUM: Fiyat "Son Kale" olan SMA50 ortalamasına dayandı. Tam bıçak sırtı durum.
        TALİMAT: Çok ciddi ve profesyonel konuş. Tahmin yapma. "SMA50 altı kapanış stop, üstü devam" de.
        """

    # SENARYO 12: 🟠 YORGUN BOĞA (TUZAK RİSKİ)
    elif (p_change_pct > -1.0) and (trend_ratio > 1.05) and (is_rsi_div_neg or has_bad_candle or (rsi_val_now > 70 and vol_ratio < 0.7)):
        ai_scenario_title = "🟠 SENARYO: YORGUN BOĞA (EXHAUSTION)"
        ai_mood_instruction = """
        DURUM: Fiyat yükseliyor GİBİ görünüyor AMA yakıt bitmiş. Negatif uyumsuzluk veya kötü mum var.
        TALİMAT: Kullanıcıyı "Gel-Gel Tuzağı" (Bull Trap) konusunda uyar. Yükselişlerin satış fırsatı olabileceğini söyle.
        """
    # --- YENİ: AI İÇİN S&D VE LİKİDİTE VERİLERİ ÇEKİMİ ---
    try: 
        sd_data = detect_supply_demand_zones(df_hist)
        sd_txt_ai = f"{sd_data['Type']} ({sd_data['Bottom']:.2f} - {sd_data['Top']:.2f}) Durum: {sd_data['Status']} olabilir." if sd_data else "Taze bölge görünmüyor."
    except: 
        sd_txt_ai = "Veri Yok"
        
    havuz_ai = ict_data.get('eqh_eql_txt', 'Yok') if isinstance(ict_data, dict) else 'Yok'
    sweep_ai = ict_data.get('sweep_txt', 'Yok') if isinstance(ict_data, dict) else 'Yok'
    # --- 🚨 PROMPT'TAN HEMEN ÖNCE PAKETİ AÇIYORUZ ---
    # calculate_price_action_dna'dan dönen veriyi (örneğin dna değişkeni) kontrol ediyoruz:
    df = get_safe_historical_data(t, period="6mo") 
    dna = calculate_price_action_dna(t)
    # Prompt oluşturulmadan hemen önce bu verileri çekiyoruz
    sv_extra = pa_data.get('smart_volume', {})
    rvol_val = sv_extra.get('rvol', 1.0)
    stop_vol_val = sv_extra.get('stopping', 'Yok')
    climax_vol_val = sv_extra.get('climax', 'Yok')
    # --- PROMPT İÇİN POC VERİLERİNİ HAZIRLAMA ---
    if dna and "smart_volume" in dna:
        sv = dna["smart_volume"]
        poc_price = f"{sv['poc']:.2f}"
        delta_val = sv.get("delta", 0)
        delta_yuzde = sv.get("delta_yuzde", 0)
        
        if delta_val < 0:
            if delta_yuzde >= 60.0:
                baskinlik = f"-%{delta_yuzde:.1f} (Agresif Satıcılar Baskın)"
            else:
                baskinlik = f"-%{delta_yuzde:.1f} (Nötr/Gürültü - Sığ Satış)"
        elif delta_val > 0:
            if delta_yuzde >= 60.0:
                baskinlik = f"+%{delta_yuzde:.1f} (Agresif Alıcılar Baskın)"
            else:
                baskinlik = f"+%{delta_yuzde:.1f} (Nötr/Gürültü - Pasif Limit Emirler)"
        else:
            baskinlik = "Kusursuz Denge (%0)"
            
        delta_durumu = f"{sv['title']} | Net Baskınlık: {baskinlik}"
    else:
        delta_durumu = "Veri Yok"
        poc_price = "Veri Yok"
        # -----------------------------------------------------

    # Güncel fiyatı DataFrame'den veya mevcut bir fiyattan çekiyoruz
    try:
        guncel_fiyat = f"{df['Close'].iloc[-1]:.2f}"
    except:
        guncel_fiyat = "Bilinmiyor"
    # ------------------------------------------------

    # --- 5. FİNAL PROMPT ---
    prompt = f"""*** SİSTEM ROLLERİ ***
Sen Al Brooks gibi Price Action konusunda uzman, Michael J. Huddleston gibi ICT (Smart Money) konusunda uzman, Paul Tudor Jones gibi VWAP konusunda uzman, Mark Minervini gibi SEPA ve Momentum stratejilerinde uzmanlaşmış dünyaca tanınan ve saygı duyulan bir yatırım bankasının kıdemli bir Fon Yöneticisisin.
Aşağıdaki TEKNİK verilere dayanarak Linda Raschke gibi profesyonel bir analiz/işlem planı oluştur. Lance Beggs gibi konusunda uzman biri gibi "Stratejik Price Action ve Yatırımcı Psikolojisi" analizlerini ve yorumlarını, Twitter için SEO'luk ve etkileşimlik açısından çekici, vurucu ve net bir şekilde ama aynı zamanda sade bir dille yaz.
Analizini hazırlarken iki aşamalı bir süreç izle: Önce arka planda tüm teknik verileri bir kurumsal risk masası ciddiyetiyle en derin ayrıntısına kadar analiz et. Ardından, bu derin analizden süzülen en vurucu ve net sonuçları aşağıda belirtilen formatta (yalın ve sade) kullanıcıya sun
Teknik terimleri parantez içinde global kısaltmalarıyla (örneğin: Fiyat Boşluğu deyip ama yanına (FVG) yaz) kullan ama anlatımı tamamen Türkçe ve yalın yap.
Aşağıdaki her hangi bir veri noktası 'Bilinmiyor' veya 'Yok' olarak gelmişse, o alanı yorumlamaya zorlama, mevcut diğer verilerle sentezini yap.
*** 🚨 DURUM RAPORU: {ai_scenario_title} ***
(Analizini bu senaryo ve talimat üzerine kur!)
Sistem Talimatı: {ai_mood_instruction}
Kurumsal Özet (Bottom Line): {ict_data.get('bottom_line', 'Özel bir durum belirtilmedi.')}
*** CANLI TARAMA SONUÇLARI (SİNYAL KUTUSU) ***
(Burası sistemin tespit ettiği en sıcak sinyallerdir, )
{scan_summary_str}

*** VARLIK KİMLİĞİ ***
- Sembol: {t}
- GÜNCEL FİYAT: {fiyat_str}
- ANA SKOR: {master_txt} (Algoritmik Puan)
- Temel Artılar: {pros_txt}
- ALTIN FIRSAT (GOLDEN TRIO) DURUMU: {is_golden}
- ROYAL FLUSH (KRALİYET SET-UP): {is_royal}
*** SMART MONEY SENTIMENT KARNESİ (Detaylı Puanlar) Ama bunların GECİKMELİ VERİLER olduğunu unutma. Analize ekleyeceksen 'son kaç günün verileri' olduğunu belirt***
- YAPI (Structure): {sent_yapi} (Market yapısı puanları şöyle: Son 20 günün %97-100 zirvesinde (12). Son 5 günün en düşük seviyesi, önceki 20 günün en düşük seviyesinden yukarıdaysa: HL (8))
- HACİM (Volume): {sent_hacim} (Hacmin 20G ortalamaya oranını ve On-Balance Volume (OBV) denetler. Bugünün hacmi son 20G ort.üstünde (12) Para girişi var: 10G ortalamanın üstünde (8))
- TREND: {sent_trend} (Ortalamalara bakar. Hisse fiyatı SMA200 üstünde (8). EMA20 üstünde (8). Kısa vadeli ortalama, orta vadeli ortalamanın üzerinde, yani EMA20 > SMA50 (4))
- MOMENTUM: {sent_mom} (RSI ve MACD ile itki gücünü ölçer. 50 üstü RSI (5) RSI ivmesi artıyor (5). MACD sinyal çizgisi üstünde (5))
- VOLATİLİTE: {sent_vola} (Bollinger Bant genişliğini inceler. Bant genişliği son 20G ortalamasından dar (10))
- MOMENTUM DURUMU (Özel Sinyal): {momentum_analiz_txt} (Hissenin Endekse göre relatif gücünü (RS) ölçer. Mansfield RS göstergesi 0'ın üzerinde (5). RS trendi son 5 güne göre yükselişte (5). Endeks düşerken hisse artıda (Alpha) (5))
*** GELİŞMİŞ MOMENTUM VE FİYAT DENGESİ (GRAFİK VERİLERİ) ***
- Para Akış İvmesi Değeri: {guncel_ivme:.4f} ({ivme_yonu}) -> (Not: Bu değer 0'ın ne kadar üzerindeyse kurumsal momentum o kadar tazedir.. Tam tersi durum için ise durum kötüdür)
- Fiyat Dengesi (Denge Seviyesi): {guncel_stp:.2f}
- Fiyat/Denge Sapması: %{denge_sapmasi:.2f} -> (Not: Eğer fiyat sarı denge çizgisinden (STP) %5'ten fazla uzaklaşmışsa 'Isınma' uyarısı yap.)
*** 1. TREND VE GÜÇ ***
KISA VADELİ TREND GÖSTERGELERİ:
- HARSI Durumu (Heikin Ashi RSI): {harsi_txt} (son 14 günlük hafızayı kullanır, RSI üzerindeki gürültüyü temizleyerek, momentumun mevcut trend yönünü ve kalıcılığını ölçer.)
- EMA Durumu (8/13): {ema_txt} (eğer hisse EMA8/13 altına düştüyse ve HARSI de negatifse kısa vadeli trend kırılmış olabilir)
ORTA VADELİ TEKNİK GÖSTERGELER ve KURUMSAL SEVİYELER:
- SuperTrend (son 60 günlük Yön): {st_txt}
- Minervini Durumu: {mini_txt}
HAREKETLİ ORTALAMALAR VE KURUMSAL SEVİYELER:
- SMA50 Durumu: {sma50_str}
- SMA 50 (Orta Vade): {sma50_val:.2f}
- SMA 100 (Ana Destek): {sma100_val:.2f}
- SMA 200 (Global Trend Sınırı): {sma200_val:.2f}
- EMA 144 (Fibonacci/Robotik Seviye): {ema144_val:.2f}
Son birkaç gündür bu hareketli ortalamalardan en az birinden tepki alıp almadığını incele. bu desteklerin tamamı Kurumsal yatırımcıların yakından takip ettiği kritik seviyelerdir. Eğer fiyat bu seviyelerden tepki alıyorsa, ya da bu hareketli ortalamaların civarında bir süredir takılıyorsa, bu seviyelerin geçerliliği ve gücü hakkında yorum yap.
- RADAR 1 (Momentum/Hacim): {r1_txt}
- RADAR 2 (Trend/Setup): {r2_txt}
Kısa vadeli momentumun (HARSI/EMA8), ana trend (SMA200/SuperTrend) ile uyumunu kontrol et. Eğer kısa vadeli sinyal ana trendin tersineyse, bunu bir 'Trend Dönüş Başlangıcı' mı yoksa 'Yüksek Riskli Bir Tepki Yükselişi' mi olduğunu netleştir.
*** 2. PRICE ACTION / ARZ-TALEP BÖLGELERİ / SMART MONEY LİKİDİTE & ICT YAPISI ***
- Market Yapısı: {ict_data.get('structure', 'Bilinmiyor')} ({ict_data.get('bias', 'Nötr')})
- Konum (Zone): {ict_data.get('zone', 'Bilinmiyor')}
- LİKİDİTE HAVUZLARI (Mıknatıs): {havuz_ai}
- LİKİDİTE AVI (Sweep/Silkeleme): {sweep_ai}
Likidite havuzlarına bakarak, perakende yatırımcıların nerede 'terste kalmış' olabileceğini ve Akıllı Para'nın bu likiditeyi nasıl kullanmak isteyeceğini yorumla
- Balina Ayak İzi (Taze Arz-Talep Bölgesi): {sd_txt_ai}
- Kısa Vadeli Trend Hassasiyeti (10G WMA): {para_akisi_txt} (Son günlerin fiyat hareketine daha fazla ağırlık vererek, trenddeki taze değişimleri ölçer.)
- Aktif FVG: {ict_data.get('fvg_txt', 'Yok')}
- Aktif Order Block: {ict_data.get('ob_txt', 'Yok')}
- HEDEF LİKİDİTE (Mıknatıs): {ict_data.get('target', 0)}
- Mum Formasyonu: {mum_desc}
- RSI Uyumsuzluğu: {pa_div} (Varsa çok dikkat et!)
- TUZAK DURUMU (SFP): {sfp_desc}
- NİHAİ KARAR VE AKSİYON PLANI (THE BOTTOM LINE): {ict_data.get('bottom_line', 'Veri Yok')}
*** 3. HEDEFLER VE RİSK ***
- Direnç (Hedef): {fib_res}
- Destek (Stop): {fib_sup}
- Hedef Likidite: {liq_str}
- İptal Seviyesi (Invalidation Point): Bu teknik tezin (Boğa/Ayı) tamamen çökeceği, piyasanın 'yanıldık' diyeceği o kritik likidite seviyesi veya yapı kırılımı (BOS) noktası neresidir? Tüm verilere bakarak net bir fiyat seviyesi olarak belirle.
*** 4. EK TEKNİK VERİLER (SMART MONEY METRİKLERİ) ***
- Bugüne ait Smart Money Hacim Durumu: {delta_durumu}
- Hacim Profili son 20 günlük hacim ortalaması "POC (Kontrol Noktası)": {poc_price}
- Güncel Fiyat: {guncel_fiyat}
- Fiyat son 20 günlük mumum hacim ortalaması olan "POC (Kontrol Noktası)" seviyesinin altındaysa bunun bir "Ucuzluk" (Discount) bölgesi mi yoksa "Düşüş Trendi" onayı mı olduğunu yorumla. Fiyat POC üzerindeyse bir "Pahalı" (Premium) bölge riski var mı, değerlendir.
- Bugüne ait Smart Money Hacim Durumundaki "Bugüne ait Net Baskınlık" yüzdesine dikkat et! Eğer bu oran %40'ın üzerindeyse, tahtada bugün için ciddi bir "Smart Money (Balina/Kurumsal)" müdahalesi olabileceğini belirt.
-"Net Baskınlık" sadece bugüne ait veridir, bunu unutma. Fiyat hareketi arasında bir uyumsuzluk var mı kontrol et. Fiyat artarken bugüne ait Net Baskınlık EKSİ (-) yönde yüksekse, "Tepeden mal dağıtımı (Distribution) yapılıyor olabilir, Boğa Tuzağı riski yüksek!" şeklinde kullanıcıyı uyar. Ama bu durumum bugün için geçerli olabileceğini, yarın her şeyin değişebileceğini unutmadan yorumla.
Veriler arasındaki uyumu (Confluence) ve çelişkiyi (Divergence) sorgula. Eğer Momentum (RSI/MACD) yükselirken Akıllı Para Hacmi (Delta) düşüyorsa, bunu 'Zayıf El Alımı' olarak işaretleyebilirsin. Fiyat VWAP'tan çok uzaksa (Parabolik), Golden Trio olsa bile kurumsalın perakende yatırımcıyı 'Çıkış Likiditesi' (Exit Liquidity) olarak kullanıp kullanmadığını dürüstçe değerlendir.
*** AKILLI PARA HACİM ANOMALİLERİ ***
- Göreceli Hacim (RVOL): {rvol_val}
- Stopping Volume (Frenleme): {stop_vol_val}
- Climax Volume (Tahliye): {climax_vol_val}
RVOL yüksekken fiyatın hareket etmemesi (Churning) bir dağıtım (Distribution) sinyali olması ihtimalini gösterir; RVOL yüksekken bir kırılım gelmesi ise gerçek bir kurumsal katılımdır. Bu ikisi arasındaki farkı mutlaka analiz et.
Hacim artarken (RVOL > 1.2) fiyatın dar bir bantta kalması 'Sessiz Birikim' veya 'Dağıtım' olabilir. Hacim düşerken fiyatın yükselmesi 'Zayıf El Yükselişi'dir. Bu uyumsuzlukları mutlaka vurgula.
*** 5. KURUMSAL REFERANS MALİYETİ VE ALPHA GÜCÜ ***
- VWAP (Adil Değer): {v_val:.2f} (Günün hacim ağırlıklı ortalama fiyatıdır; piyasa yapıcıların ve akıllı paranın 'denge' kabul ettiği ana maliyet merkezini ölçer.)
- Fiyat Konumu: Kurumsal Referans Maliyetin (VWAP) %{v_diff:.1f} üzerinde/altında. (Fiyatın kurumsal maliyetten ne kadar uzaklaştığını ölçer)
- VWAP DURUMU: {vwap_ai_txt} (Momentumun kalitesini ölçer; ralli modu sağlıklı kurumsal alımı, parabolik ise perakende yatırımcının yarattığı tehlikeli aşırı ısınmayı simgeler.)
- RS (Piyasa Gücü): {rs_ai_txt} (Alpha: {alpha_val:.1f}) (Hissenin endeksten bağımsız 'ayrışma' gücünü ölçer; pozitif Alpha, piyasa düşerken bile ayakta kalan lider 'at' olduğunu kanıtlar.)
(NOT: Eğer VWAP durumu 'PARABOLİK' veya 'ISINIYOR' ise bu durumu teşhis et ve hatırlat. 'RALLİ MODU' ise trendi sürmeyi önerebilirsin.)
*** 6. YARIN NE OLABİLİR ***
{lorentzian_bilgisi} 

*** KESİN DİL VE HUKUKİ GÜVENLİK PROTOKOLÜ ***
Bu bir finansal analizdir ve HUKUKİ RİSKLER barındırır. Bu yüzden aşağıdaki kurallara HARFİYEN uyacaksın:
1. YASAKLI KELİMELER LİSTESİ: "Kesin, kesinlikle, %100, uçacak, kaçacak, çökecek, çok sert, devasa, garanti, mükemmel, felaket" gibi abartılı, duygusal ve kesinlik bildiren sıfatları ASLA KULLANMAYACAKSIN.
2. TAVSİYE VERMEK YASAKTIR: "Alın, satın, tutun, kaçın, ekleyin" gibi yatırımcıyı doğrudan yönlendiren fiiller KULLANILAMAZ. 
3. ALGORİTMA DİLİ KULLAN: Analizleri kendi kişisel fikrin gibi değil, "Sistemin ürettiği veriler", "İstatistiksel durum", "Matematiksel sapma" gibi nesnel bir dille aktar.
4. GELECEĞİ TAHMİN ETME: Gelecekte ne olacağını söyleme. Sadece "Mevcut verinin tarihsel olarak ne anlama geldiğini" ve "Risk/Ödül dengesinin nerede olduğunu" belirt.
Örnek Doğru Cümle: "Z-Score +2 seviyesinin aşıldığını gösteriyor. Algoritmik olarak bu bölgeler aşırı fiyatlanma alanlarıdır ve düzeltme riski taşıyabilir."

*** İKİ GÖREVİN VAR *** 

Birinci Görevin; 
Tüm bu teknik verileri Linda Raschke'nin profesyonel soğukkanlılığıyla sentezleyip, Lance Beggs'in 'Stratejik Price Action' ve 'Yatırımcı Psikolojisi' odaklı bakış açısıyla yorumlamaktır. Asla tavsiye verme (bekle, al, sat, tut vs deme), sadece olasılıkları belirt. "etmeli" "yapmalı" gibi emir kipleri ile konuşma. "edilebilir" "yapılabilir" gibi konuş. Asla keskin konuşma. "en yüksek", "en kötü", "en sert", "çok", "büyük", "küçük", "dev", "keskin", "sert" gibi aşırılık ifade eden kelimelerden uzak dur. Bizim işimiz basitçe olasılıkları sıralamak.
Analizini yaparken karmaşık finans jargonundan kaçın; mümkün olduğunca Türkçe terimler kullanarak sade ve anlaşılır bir dille konuş. Verilerin neden önemli olduğunu, birbirleriyle nasıl etkileşime girebileceğini ve bu durumun yatırımcı psikolojisi üzerinde nasıl bir etkisi olabileceğini açıklamaya çalış. Unutma, geleceği kimse bilemez, bu sadece olasılıkların bir değerlendirmesidir.
Teknik terimleri sadece ilk geçtiği yerde kısaltmasıyla ver, sonraki anlatımlarda akıcılığı bozmamak için sadeleştir.
Analizinde 'Retail Sentiment' (Küçük Yatırımcı Psikolojisi) ile 'Institutional Intent' (Kurumsal Niyet) arasındaki farka odaklan. Verilerdeki anormallikleri (örneğin: RSI düşerken fiyatın yatay kalması veya düşük hacimli kırılımlar) birer 'ipucu' olarak kabul et ve bu ipuçlarını birleştirerek piyasa yapıcının bir sonraki hamlesini tahmin etmeye çalış.
Bir veri noktası 'Bilinmiyor' gelirse onu yok say, ancak eldeki verilerle bir 'Olasılık Matrisi' kur. Asla tek yönlü (sadece olumlu) bir tablo çizme; 'Madalyonun Öteki Yüzü'nü her zaman göster. Savunma mekanizman 'analizi haklı çıkarmak' değil, 'riski bulmak' olsun.
Herhangi bir veri alanı boş veya süslü parantez içinde {...} şeklinde ham halde gelmişse, o verinin teknik bir arıza nedeniyle okunamadığını varsay ve mevcut diğer verilerle analizi tamamla. Asla "Veri Yok" veya "Bilinmiyor" yazan bir alanı yorumlamaya zorlama, sadece mevcut verilerle en iyi sentezi yapmaya çalış.
En başa "SMART MONEY RADAR   #{clean_ticker}  ANALİZİ -  {fiyat_str} 👇📷" başlığı at ve şunları analiz et. (Twitter için atılacak bi twit tarzında, aşırıya kaçmadan ve basit bir dilde yaz)
YÖNETİCİ ÖZETİ: Önce aşağıdaki tüm değerlendirmelerini bu başlık altında 5 cümle ile özetle.. 
1. GENEL ANALİZ: Yanına "(Önem derecesine göre)" diye de yaz 
   - Yukarıdaki verilerden SADECE EN KRİTİK OLANLARI seçerek maksimum 6 maddelik bir liste oluştur. Zorlama madde ekleme! 2 kritik sinyal varsa 2 madde yaz. 
   - SIRALAMA KURALI (BU KURAL ÖNEMLİ): Maddeleri "Önem Derecesine" göre azalan şekilde sırala. Düzyazı halinde yapma; Her madde için paragraf aç. Önce olumlu olanları sırala; en çok olumlu’dan en az olumlu’ya doğru sırala. Sonra da olumsuz olanları sırala; en çok olumsuz’dan en az olumsuz’a doğru sırala. Olumsuz olanları sıralamadan evvel "Öte Yandan; " diye bir başlık at ve altına olumsuzları sırala. Otoriter yazma. Geleceği kimse bilemez.
   - SIRALAMA KURALI DEVAMI: Her maddeyi 3 cümle ile yorumla ve yorumlarken; o verinin neden önemli olduğunu (8/10) gibi puanla ve finansal bir dille açıkla. Olumlu maddelerin başına "✅" ve verdiğin puanı, olumsuz/nötr maddelerin başına " 📍 " ve verdiğin puanı koy. Olumlu maddeleri alt alta, Olumsuz maddeleri de alt alta yaz. Sırayı asla karıştırma. (Yani bir olumlu bir olumsuz madde yazma)
     a) Listenin en başına; "Kırılım (Breakout)", "Akıllı Para (Smart Money)", "Trend Dönüşü" veya "BOS" içeren EN GÜÇLÜ sinyalleri koy ve bunlara (8/10) ile (10/10) arasında puan ver.
        - Eğer ALTIN FIRSAT durumu 'EVET' ise, bu hissenin piyasadan pozitif ayrıştığını (RS Gücü), kurumsal toplama bölgesinde olduğunu (ICT) ve ivme kazandığını vurgula. Analizinde bu 3/3 onayın neden kritik bir 'alım penceresi' sunduğunu belirt.
        - Eğer ROYAL FLUSH durumu 'EVET' ise, bu nadir görülen 4/4'lük onayı analizin en başında vurgula ve bu kurulumun neden en yüksek kazanma oranına sahip olduğunu finansal gerekçeleriyle açıkla.
     b) Listenin devamına; trendi destekleyen ama daha zayıf olan yan sinyalleri (örneğin: "Hareketli ortalama üzerinde", "RSI 50 üstü" vb.) ekle. Ancak bunlara DÜRÜSTÇE (1/10) ile (7/10) arasında puan ver.
   - UYARI: Listeyi 6 maddeye tamamlamak için zayıf sinyallere asla yapay olarak yüksek puan (8+) verme! Sinyal gücü neyse onu yaz.
2. SENARYO A: ELİNDE OLANLAR İÇİN 
   - Yöntem: [TUTULABİLİR / EKLENEBİLİR / SATILABİLİR / KAR ALINABİLİR]
   - Strateji: Trend bozulmadığı sürece taşınabilir mi? Kar realizasyonu için hangi (BOS/Fibonacci/EMA8/EMA13) seviyesi beklenebilir? Emir kipi kullanmadan ("edilebilir", "beklenebilir") Trend/Destek kırılımına göre risk yönetimi çiz. İzsüren stop seviyesi öner.
   - İzsüren Stop: Stop seviyesi nereye yükseltilebilir?
3. SENARYO B: ELİNDE OLMAYANLAR İÇİN 
   - Yöntem: [ALINABİLİR / GERİ ÇEKİLME BEKLENEBİLİR / UZAK DURULMASI İYİ OLUR]
   - Risk/Ödül Analizi: Şu an girmek finansal açıdan olumlu mu? yoksa "FOMO" (Tepeden alma) riski taşıyabilir mi? Fiyat çok mu şişkin yoksa çok mu ucuz?
   - İdeal Giriş: Güvenli alım için fiyatın hangi seviyeye (FVG/Destek/EMA8/EMA13/SMA20) gelmesi beklenebilir? "etmeli" "yapmalı" gibi emir kipleri ile konuşma. "edilebilir" "yapılabilir" gibi konuş. Sadece olasılıkları belirt.
   - Tezin İptal Noktası (sadece Senaryo B için geçerli): Analizdeki yükseliş/düşüş beklentisinin hangi seviyede tamamen geçersiz kalacağını (Invalidation) net fiyatla belirt. Bu seviyeye gelinirse, mevcut teknik yapının çökmüş olabileceği ve yeni bir analiz yapılması gerektiği yorumunu yap.
4. SONUÇ VE UYARI: Önce "SONUÇ" başlığı aç Kurumsal Özet kısmını da aynen buraya da ekle. 
Ardından, bir alt satıra "UYARI" başlığı aç ve eğer RSI pozitif-negatif uyumsuzluğu, Hacim düşüklüğü, stopping volume, Trend tersliği, Ayı-Boğa Tuzağı, gizli satışlar (satış işareti olan tekli-ikili-üçlü mumlar) vb varsa büyük harflerle uyar. 
Analizinde HARSI (Heikin Ashi RSI) verilerini kullanacaksan bunun son 14 günlük olduğunu unutma ve son gün mumu için şu şartlar sağlanıyorsa dikkati çek: 1) Eğer 'Yeşil Bar' ise bunu "gürültüden arınmış gerçek bir yükseliş ivmesi" olarak yorumla. 2) Eğer 'Kırmızı Bar' ise fiyat yükselse bile momentumun (RSI bazında) düştüğünü ve bunun bir yorgunluk sinyali olabileceğini belirt. 
Analizin sonuna daima büyük ve kalın harflerle "YATIRIM TAVSİYESİ DEĞİLDİR  " ve onun da altındaki satıra " #SmartMoneyRadar #{clean_ticker} #BIST100 #XU100" yaz.

İkinci Görevin;
Birinci görevinde yapmış olduğun o analizin en vurucu yerlerinin Twitter için SEO'luk ve etkileşimlik açısından çekici, vurucu ve net bir şekilde özetini çıkarmak. Bu özet şu formatta alacak:
1. Görsel ve Biçimsel Standartlar
    - Toplam 3 Madde Kuralı: Paylaşımların Twitter arayüzünde tam görünmesi ve vurucu olması için içerik her zaman toplam 3 maddeden oluşmalıdır. Satırlar arasında boşluk bırakmadan yaz.
    - Emoji Standartı: Her maddenin başında mutlaka "🔹" emojisi kullanılmalıdır.
    - İçerik Tonu ve Uzunluk: Maddeler çok kısa (mümkünse bir cümle), öz ve "Societe Generale risk toplantısı" ciddiyetinde, laf kalabalığından arındırılmış olmalıdır.
    - Hashtag Protokolü: Tweet sonuna mutlaka ilgili hisse kodu ile birlikte #BIST100 #SmartMoneyRadar #[HisseKodu] etiketleri eklenmelidir.
2. Dinamik Başlık ve "Kanca" (Hook) Kuralları
    - İlk Başlık daima #{clean_ticker}  {fiyat_str} ve bir önceki güne kıyasla değişim yüzdesi belirtilmelidir Örneğin: "#HISSE 123.45 (+2.34%) 👇📷".
    - En Çarpıcı Veri Odaklılık: Başlıkta sadece jenerik etiketler değil, paneldeki en çarpıcı teknik anomali (örneğin: "11266 Ana Uçurumu", "339.25 FOMO Tuzağı", "GAP Temizliği") ve kritik durumlar kullanılmalıdır.
    - Kanca (Hook) Kullanımı: Başlıkta, okuyucunun dikkatini çekecek ve onları okumaya devam etmeye teşvik edecek bir "kanca" (hook) bulunmalıdır. Bu, genellikle analizdeki en kritik veya şaşırtıcı bulguya atıfta bulunan kısa bir ifade olabilir.
    - En alta "Detaylı analiz ve çok detaylı görsel bir sonraki Twit’te 👇" cümlesi yazılmalıdır
"""
    with st.sidebar:
        st.code(prompt, language="text")
        st.success("Prompt Güncellendi")
        # ==============================================================================
        # 𝕏 TWITTER VİRAL AJANI (V18.0 - MAJOR OYUNCU MODU)
        # ==============================================================================
        st.markdown("---")
        st.markdown("### 𝕏 Twitter Vitrini")

        # 1. ADIM: INIT
        clean_ticker = "HISSE"
        c_rsi = 50.0
        c_rs = 0.0
        c_score = 50.0
        c_ict = 0.0
        c_vol = 0.0
        check_royal = False
        check_golden = False
        c_destek = "Grafikte"
        c_direnc = "Grafikte"

        # 2. ADIM: VERİ ÇEKME
        if 't' in locals() and t: 
            clean_ticker = str(t).replace(".IS", "").replace(".is", "").replace("-USD", "").replace("=F", "")
        elif 'sembol' in locals() and sembol: 
            clean_ticker = str(sembol).replace(".IS", "").replace(".is", "").replace("-USD", "").replace("=F", "")

        try:
            if 'sent_data' in locals() and sent_data: 
                c_rsi = float(sent_data.get('raw_rsi', 50.0))
                if 'vol' in sent_data and 'Hacim' in str(sent_data['vol']): c_vol = 20.0 
            
            if 'mini_data' in locals() and mini_data: 
                c_rs = float(mini_data.get('rs_val', 0.0))
            
            if 'master_score' in locals(): 
                c_score = float(master_score)
                
            if 'ict_score' in locals(): 
                c_ict = float(ict_score)
            elif 'ict_data' in locals() and ict_data:
                 if "MSS" in str(ict_data) or "BOS" in str(ict_data): c_ict = 20.0
        except Exception as e:
            st.error(f"Veri çekme hatası: {e}")
            pass 

        try:
            if 'is_royal' in locals() and "EVET" in str(is_royal): check_royal = True
            if 'is_golden' in locals() and "EVET" in str(is_golden): check_golden = True
        except:
            pass

        try:
            if 'fib_sup' in locals(): c_destek = str(fib_sup).split(' ')[0]
            if 'fib_res' in locals(): c_direnc = str(fib_res).split(' ')[0]
        except:
            pass
        # --- YENİ: AJANA GETİRİ HAFIZASI EKLENİYOR ---
        aylik_getiri = 0.0
        try:
            if 'df' in locals() and len(df) >= 20:
                ilk_fiyat = float(df['Close'].iloc[-20])
                son_fiyat = float(df['Close'].iloc[-1])
                aylik_getiri = ((son_fiyat - ilk_fiyat) / ilk_fiyat) * 100
        except:
            pass
        # ------------------------------------------------------------------
        # 2.5. ADIM: TURNİKE SİSTEMİ (VARLIK KİMLİĞİ VE JARGON SÖZLÜĞÜ)
        # ------------------------------------------------------------------
        # Varsayılan (Borsa İstanbul Ağzı)
        context_piyasa = "Borsa"
        context_varlik = "Hisse"
        context_rakip  = "Endeks" 
        context_tag    = "#Bist100"
        is_major = False # Ana oyuncu mu?
        
        # Jargon Değişkenleri (Varsayılan)
        j_aktor  = "Fon Yöneticileri"   # Kim alıyor?
        j_analiz = "Takas"              # Neye bakıyoruz?
        j_dusus  = "Taban Serisi"       # Kötü durum ne?
        j_yuksel = "Tavan Serisi"       # İyi durum ne?
        j_sebep  = "Bilanço/Haber"      # Neden düştü?

        # 1. TURNİKE: KRİPTO (Bitcoin ve Altcoinler)
        if "-USD" in str(t):
            context_piyasa = "Kripto"
            context_varlik = "Coin"
            context_tag    = "#Bitcoin #Kripto"
            
            # Altcoin mi Bitcoin mi?
            if "BTC-" in str(t):
                context_rakip = "Nasdaq" 
                context_tag   = "#Bitcoin #BTC"
                is_major = True # BTC bir Ana Oyuncudur
            else:
                context_rakip = "BTC"    
            
            # Kripto Jargonu
            j_aktor  = "Balinalar (Whales)"
            j_analiz = "On-Chain Verileri"
            j_dusus  = "Sert Dump"
            j_yuksel = "Parabolik Pump"
            j_sebep  = "FUD/Haber"

        # 2. TURNİKE: SEKTÖR ENDEKSLERİ
        elif str(t).startswith("X") and ".IS" in str(t):
            context_piyasa = "BIST"
            context_varlik = "Sektör"
            context_rakip  = "XU100"
            context_tag    = "#Bist100 #Sektör"
            j_aktor        = "Büyük Fonlar"
            is_major = True # Sektör endeksleri majördür

        # 3. TURNİKE: GLOBAL/EMTIA/ENDEKS
        elif ".IS" not in str(t) and "=F" not in str(t) and "-USD" not in str(t):
            context_piyasa = "ABD"
            context_varlik = "Hisse"
            context_rakip  = "SP500"
            context_tag    = "#WallStreet"
            # Eğer SPX, NDX, GOLD gibi bir şeyse is_major=True yapabiliriz ama
        # 3. ADIM: SENARYO MOTORU (DİNAMİK VARYASYONLAR - TAMAMEN VERİYE DAYALI)
        txt_baslik = ""
        txt_kanca = "" 
        
        # --- 0. GRUP: FORMASYON TARAMA AJANI (MUTLAK ÖNCELİK) ---
        # Ajanın ürettiği formasyon metnini güvenli bir şekilde alıyoruz
        aktif_formasyon = ""
        if 'formasyon_sonucu' in locals():
            aktif_formasyon = str(formasyon_sonucu).upper()
        elif 'formasyon_metni' in locals():
            aktif_formasyon = str(formasyon_metni).upper()
        elif 'aktif_formasyonlar' in locals():
            aktif_formasyon = str(aktif_formasyonlar).upper()

        if aktif_formasyon:
            # 1. GEOMETRİK DÖNÜŞ FORMASYONLARI
            if "TOBO" in aktif_formasyon:
                txt_baslik = f"🏗️ {clean_ticker}: TOBO Formasyonu Onaylandı mı?"
                txt_kanca = "Düşüş trendinin tabanında devasa bir (TOBO) tespit edildi! Boyun çizgisi kırılıyor, ayılar masadan kalktı mı? Sonuç ve UYARI kısmına dikkat👇"
            elif "OBO" in aktif_formasyon and "TOBO" not in aktif_formasyon:
                txt_baslik = f"☠️ {clean_ticker}: OBO Tehlikesi?"
                txt_kanca = "Zirvede tehlikeli bir (OBO) yapısı belirdi. Akıllı para malı dağıtıyor ve boyun çizgisi tehdit altında! Sonuç ve UYARI kısmına dikkat👇"
            elif "FİNCAN" in aktif_formasyon or "CUP" in aktif_formasyon:
                txt_baslik = f"☕ {clean_ticker}: Fincan-Kulp Hazırlığı mı?"
                txt_kanca = "Uzun süren sabır testi bitiyor! Fincan-Kulp formasyonu tamamlanmak üzere. Devasa bir ralli kapıda mı? Sonuç ve UYARI kısmına dikkat👇"
            elif "BAYRAK" in aktif_formasyon or "FLAG" in aktif_formasyon:
                txt_baslik = f"🏴 {clean_ticker}: Boğa Bayrağı Dalgalanıyor mu?"
                txt_kanca = "Sert bir direğin ardından kusursuz bir bayrak flama dinlenmesi! Rallinin ikinci ve daha sert ayağı başlıyor mu? Sonuç ve UYARI kısmına dikkat👇"

            # 2. KURUMSAL ARZ-TALEP (SUPPLY/DEMAND) BÖLGELERİ
            elif "RBR" in aktif_formasyon or "RALLY BASE RALLY" in aktif_formasyon:
                txt_baslik = f"🚀 {clean_ticker}: Rally-Base-Rally? Yeni Dalga!"
                txt_kanca = "Kurumsal Arz-Talep formasyonu devrede. Ralli, dinlenme ve yeni bir ralli! Hedef neresi? Sonuç ve UYARI kısmına dikkat👇"
            elif "DBR" in aktif_formasyon or "DROP BASE RALLY" in aktif_formasyon:
                txt_baslik = f"🧲 {clean_ticker}: Drop-Base-Rally? Dip Dönüşü!"
                txt_kanca = "Sert düşüş sonrası yatay toplama evresi bitti. Akıllı para dipten dönüşü (DBR) ateşledi mi? Sonuç ve UYARI kısmına dikkat👇"
            elif "DBD" in aktif_formasyon or "DROP BASE DROP" in aktif_formasyon:
                txt_baslik = f"📉 {clean_ticker}: Drop-Base-Drop? Ayıların İnsafı Yok!"
                txt_kanca = "Düşüş sonrası soluklanma (Base) başarısız oldu. Destekler kırılıyor, yeni bir satış dalgası mı tetikleniyor? Sonuç ve UYARI kısmına dikkat👇"
            elif "RBD" in aktif_formasyon or "RALLY BASE DROP" in aktif_formasyon:
                txt_baslik = f"🧱 {clean_ticker}: Rally-Base-Drop? Zirvede Dağıtım?"
                txt_kanca = "Ralli sonrası tepede oyalama (Base) ve ardından sert çöküş (Drop). Büyük oyuncular malı devredip çıkıyor mu? Sonuç ve UYARI kısmına dikkat👇"

        # --- GRUP A: EFSANE SİNYALLER ---
        if check_royal:
            if c_rsi >= 70:
                if c_rs > 80:
                    txt_baslik = f"💎 {clean_ticker}: Kusursuz Fırtına Liderliği? (Flash Royal)"
                    txt_kanca = "RSI şişmiş olsa da RS (Alpha) gücü endeksi eziyor mu? Trendin zirvesinde kurumsal inat devam ediyor. Sonuç ve UYARI kısmına dikkat👇"
                else:
                    txt_baslik = f"🔥 {clean_ticker}: Rallide Kâr Katlanıyor ama Yorulma Belirtileri mi Var?"
                    txt_kanca = "Kusursuz yükseliş sürüyor fakat RS ivmesi yavaşlıyor. Erken girenler kârını maksimize ederken, düzeltme ufukta olabilir mi? Sonuç ve UYARI kısmına dikkat👇"
            else:
                if c_vol > 20:
                    txt_baslik = f"🚀 {clean_ticker}: Tarihi Fırsat ve Hacim Patlaması?"
                    txt_kanca = "Tüm göstergeler aynı anda yeşil yaktı ve devasa bir hacimle onaylandı! Büyük kalkış için kurumsal vagonlar doldu mu? Sonuç ve UYARI kısmına dikkat👇"
                else:
                    txt_baslik = f"💎 {clean_ticker}: Kusursuz Hizalanma Tamamlandı mı? (Flash Royal)"
                    txt_kanca = "Sistem 4/4 onay verdi ancak hacim hala sakin. Sessizce pozisyon alanlar büyük hareketi mi bekliyor? Sonuç ve UYARI kısmına dikkat👇"
        
        elif check_golden:
            if c_rsi >= 70:
                if aylik_getiri > 15.0:
                    txt_baslik = f"🏆 {clean_ticker}: Altın Ralli Zirveyi Zorluyor?"
                    txt_kanca = f"Son 1 ayda %{aylik_getiri:.1f} getiri ile ralli olgunluk evresinde. Tutanlar rahat, peki yeni girenler için risk/ödül ne durumda? Sonuç ve UYARI kısmına dikkat👇"
                else:
                    txt_baslik = f"🔥 {clean_ticker}: Golden Trio Onayıyla İstikrarlı Yükseliş?"
                    txt_kanca = "Trend, ivme ve hacim sapasağlam! Göstergeler sıcak ama fiyat aşırı fiyatlanmamış. Ralli devam edecek mi? Sonuç ve UYARI kısmına dikkat👇"
            else:
                if c_score > 80:
                    txt_baslik = f"⚡ {clean_ticker}: Güçlü Sinyal, Yüksek Skor? (Golden Trio)"
                    txt_kanca = "Algoritmik skor zirvede, üçlü onay devrede! Tahtada akıllı para toplanıyor, kalkış izni çıktı. Sonuç ve UYARI kısmına dikkat👇"
                else:
                    txt_baslik = f"🏆 {clean_ticker}: Ralli Hazırlığı mı? (Golden Trio!)"
                    txt_kanca = "Trend ve momentum onay verdi. Radar yeşile döndü ancak ana skor hala temkinli. Kırılım an meselesi mi? Sonuç ve UYARI kısmına dikkat👇"

        # --- GRUP B: KURUMSAL İZLER ---
        elif c_ict >= 15:
            if c_rsi > 60:
                txt_baslik = f"🦁 {clean_ticker}: Ayılar Tamamen Pes Etti mi? (Kurumsal Hakimiyet)"
                txt_kanca = "Fiyat momentum kazanıyor ve kurumsal fonlar tahtayı domine ediyor. Dirençler tek tek kırılacak mı? Sonuç ve UYARI kısmına dikkat👇"
            else:
                txt_baslik = f"🦁 {clean_ticker}: Düşüş Trendi Kırıldı mı? (MSS/BOS)"
                txt_kanca = "Ayıların son kalesi yıkıldı! Diplerden gelen kurumsal alımlarla direksiyon artık Boğaların elinde. Sonuç ve UYARI kısmına dikkat👇"

        # --- ÖZEL FIRSATLAR ---
        elif c_vol < 5 and 45 < c_rsi < 55 and c_score > 50:
            if c_rs > 50:
                txt_baslik = f"💣 {clean_ticker}: Yukarı Yönlü Fırtına Öncesi Sessizlik? (Squeeze)"
                txt_kanca = f"Hacim kurudu, bantlar daraldı. Ancak hisse {context_rakip} karşısında güçlü (RS>50). Yukarı yönlü %20'lik bir patlama kapıda mı? Sonuç ve UYARI kısmına dikkat👇"
            else:
                txt_baslik = f"🗜️ {clean_ticker}: Yön Kararı An Meselesi olabilir mi? (Volatilite Daralması)"
                txt_kanca = "Fiyat dar bir alana hapsoldu, alıcı ve satıcı dengede. Akıllı para tetiği hangi yöne çekecek? Sonuç ve UYARI kısmına dikkat👇"

        elif c_score > 70 and c_vol > 25 and c_rs > 80:
            txt_baslik = f"🚀 {clean_ticker}: Köprüleri Yaktı mı? (Breakaway/Kaçış)"
            txt_kanca = "Güçlü hacim, yüksek RS ve devasa skor! Bu sıradan bir hareket değil, kurumsal bir 'Kaçış' dalgası olabilir. Sonuç ve UYARI kısmına dikkat👇"

        # --- UÇ DURUMLAR ---
        elif c_rsi < 22 and c_score < 30:
            if c_vol > 15:
                txt_baslik = f"💀 {clean_ticker}: Kan Banyosunda Panik Satışı mı? (Kapitülasyon)"
                txt_kanca = f"RSI tarihi dipte ve hacim çok yüksek! Küçük yatırımcı 'Battık' diyip kaçarken {j_aktor} dipten mi topluyor? Sonuç ve UYARI kısmına dikkat👇"
            else:
                txt_baslik = f"🕳️ {clean_ticker}: Sessiz Çöküş Devam Ediyor mu? (Aşırı Satım)"
                txt_kanca = "RSI dipte ama hacim yok. Kimse almaya cesaret edemiyor. Bıçağı tutmak için erken mi? Sonuç ve UYARI kısmına dikkat👇"

        elif c_rsi > 88:
            if c_vol > 20:
                txt_baslik = f"🎈 {clean_ticker}: Kusursuz Balon Şişti mi? (Dağıtım Tehlikesi)"
                txt_kanca = "RSI 88 üstünde ve hacim patlıyor! Akıllı para malı ky'ye mi devrediyor? 'Hüzün' gelmeden kârı koruma vakti mi? Sonuç ve UYARI kısmına dikkat👇"
            else:
                txt_baslik = f"🔥 {clean_ticker}: Yerçekimine Meydan mı Okuyor? (Parabolik)"
                txt_kanca = "Aşırı alım bölgesinde limitsiz gidiş. Motor hararet yaptı, kâr realizasyonu her an sert gelebilir. Sonuç ve UYARI kısmına dikkat👇"

        # --- 1. GRUP: RS GÜCÜ ---
        elif c_rs > 90 and c_score > 65:
            txt_baslik = f"🦖 {clean_ticker}: {context_piyasa}'nın Mutlak Lideri mi?"
            txt_kanca = f"{context_rakip} kan ağlarken o zirve yeniliyor. {j_aktor} buraya sığınıyor, Alfa gücü devrede! Sonuç ve UYARI kısmına dikkat👇"

        elif c_score < 45:
            if aylik_getiri > 12.0:
                txt_baslik = f"🚧 {clean_ticker}: Zirve Yorgunluğu mu? (Ralli Molası)"
                txt_kanca = f"Son 1 ayda %{aylik_getiri:.1f} ralli yaptı ama şimdi skor düşüyor. Kâr satışları başladı, yeni bir sıçrama için güç mü topluyor? Sonuç ve UYARI kısmına dikkat👇"
            else:
                if "BTC-" in str(t):
                    txt_baslik = f"🥀 {clean_ticker}: Dijital Altın Pas mı Tuttu?"
                    txt_kanca = "Risk iştahı kesildi, skor yerlerde. Piyasa beklerken o neden kan kaybediyor? Sonuç ve UYARI kısmına dikkat👇"
                elif is_major:
                    txt_baslik = f"🏛️ {clean_ticker}: Piyasanın Kolonları Titriyor mu?"
                    txt_kanca = "Ana oyuncu zayıfladı, güven erozyonu sürüyor. Bu çöküş tüm piyasayı aşağı çeker mi? Sonuç ve UYARI kısmına dikkat👇"
                else:
                    txt_baslik = f"🚜 {clean_ticker}: Piyasa Giderken O Neden Duruyor?"
                    txt_kanca = f"Denge skoru düşük, hareket yok. {j_aktor} bu tahtayı tamamen unuttu mu, yoksa bezdirme mi var? Sonuç ve UYARI kısmına dikkat👇"

        elif c_rs < 35 and c_score > 60:
            txt_baslik = f"🧟 {clean_ticker}: Bu Yükseliş Gerçek mi? (Yalancı Bahar)"
            txt_kanca = "Skor yüksek ama RS (Endeks Gücü) yerlerde. Fiyat artıyor ama altı boş. Bu bir 'Boğa Tuzağı' olabilir mi? Sonuç ve UYARI kısmına dikkat👇"

        elif c_score < 30 and 40 < c_rs < 50:
            txt_baslik = f"🕳️ {clean_ticker}: Ucuz Sandıkça Daha da Ucuzluyor mu?"
            txt_kanca = "RS nötr ama ana skor iflas bayrağı çekiyor. Dibi bulmaya çalışmak portföy intiharı mı? Sonuç ve UYARI kısmına dikkat👇"

        elif c_rs < 45 and c_score > 40 and c_vol > 12:
            txt_baslik = f"🎭 {clean_ticker}: Direnç Kırıldı mı, Kandırdı mı? (Boğa Tuzağı)"
            txt_kanca = "Hacim geldi ama RS hala zayıf. Dün 'Tamam' dedik, bugün vazgeçtiler. Sahte kırılımla mal mı kilitlediler? Sonuç ve UYARI kısmına dikkat👇"

        # --- 2. GRUP: ANOMALİLER ---
        elif c_score < 45 and 40 < c_rsi < 50:
            txt_baslik = f"🧹 {clean_ticker}: Gizli Toplama (Akümülasyon) İzi mi?"
            txt_kanca = f"Fiyat dipte yataya bağladı ama Z-Score iyileşiyor. {j_aktor} panik yaptırıp sessizce mal mı topluyor? Sonuç ve UYARI kısmına dikkat👇"

        elif c_rsi > 75 and c_rs < 60:
            txt_baslik = f"🥵 {clean_ticker}: Rallinin Nefesi Kesildi mi?"
            txt_kanca = "Fiyat zirveyi gördü ama RS (Alfa) desteklemiyor. Rüzgar tersine dönmek üzere, kârı cebine koyma vakti mi? Sonuç ve UYARI kısmına dikkat👇"

        elif c_rsi > 40 and c_score < 40 and c_vol > 8:
            txt_baslik = f"👻 {clean_ticker}: Fiyat Yalan Söylüyor mu? (RSI Uyumsuzluğu)"
            txt_kanca = "Fiyat 'Öldüm' diyor, İndikatörler 'Hayır' diyor. Trend dönüşü mü yoksa son bir silkeleme mi? Sonuç ve UYARI kısmına dikkat👇"

        elif c_score > 60 and c_rsi < 60 and c_vol < 8:
            txt_baslik = f"🪤 {clean_ticker}: Ekranda Yeşil Mumlar, Peki Altı Boş mu? (Fake Out)"
            txt_kanca = "Skor şişmiş ama hacim yok, RSI yatay. Malı yavaşça yukarıdan mı devrediyorlar? Sonuç ve UYARI kısmına dikkat👇"

        elif c_rs > 75 and c_score > 75 and c_rsi > 50:
            txt_baslik = f"🌟 {clean_ticker}: Kutsal Kase Formasyonu Onaylandı mı?"
            txt_kanca = "Trend, Momentum ve Alfa gücü (RS) aynı yönü gösteriyor. Büyük oyun başladı, hedefler neresi? Sonuç ve UYARI kısmına dikkat👇"

        # --- 3. GRUP: ZİRVE/YATAY ---
        elif c_vol > 20 and 60 < c_rsi < 80:
            txt_baslik = f"🌪️ {clean_ticker}: Sessiz Dağıtım Devrede mi?"
            txt_kanca = "Fiyat gitmiyor ama hacim patlıyor. Yukarı kırmıyor, satışı karşılıyorlar. Bu bir 'Gel Gel' operasyonu mu? Sonuç ve UYARI kısmına dikkat👇"

        elif c_score > 65 and c_vol < 8 and 50 < c_rsi < 65:
            txt_baslik = f"🏳️ {clean_ticker}: Boğa Bayrağı Dalgalanıyor mu? (Mola)"
            txt_kanca = "Hacim kurudu, satıcılar isteksiz, skor güçlü. Rallinin ikinci ayağı için enerji mi toplanıyor? Sonuç ve UYARI kısmına dikkat👇"

        elif c_rsi > 70 and c_score < 60:
            txt_baslik = f"🎣 {clean_ticker}: Wyckoff Tuzağı! İçeri mi Çektiler?"
            txt_kanca = "Tavanı deliyor gibi yapıp geri bastılar. Skor zayıf, RSI şişik. Bu tam bir 'Fake Breakout'. Sonuç ve UYARI kısmına dikkat👇"
        
        elif 50 < c_rsi < 60 and c_score > 75:
            txt_baslik = f"🧊 {clean_ticker}: Sağlıklı Yükseliş mi? (RSI Reset)"
            txt_kanca = "Fiyat düşmeden indikatörler soğudu. Trendin gücünü koruduğu en sağlıklı ralli işareti! Sonuç ve UYARI kısmına dikkat👇"

        # --- 4. GRUP: DÜŞÜŞ ---
        elif c_score < 30 and c_vol > 20:
            txt_baslik = f"🛗 {clean_ticker}: Halat Koptu, Serbest Düşüş mü?"
            txt_kanca = "Bu sıradan bir düzeltme değil! Devasa hacimle skor dibe vurdu. Kurumsallar 'Ne olursa olsun sat' diyor! Sonuç ve UYARI kısmına dikkat👇"

        elif c_rs > 70 and c_rsi < 55 and c_score > 55:
            txt_baslik = f"🩺 {clean_ticker}: Sağlıklı Pullback! (Alım Fırsatı mı?)"
            txt_kanca = "Köpük alındı, fiyat trend desteğine indi. Endeksten güçlü hissede trene binmek için ikinci şans mı? Sonuç ve UYARI kısmına dikkat👇"

        elif 50 < c_score < 65 and c_rsi < 50:
            txt_baslik = f"🎒 {clean_ticker}: Trend Yoruldu, Kanama Başlayabilir mi?"
            txt_kanca = "Tırmanış açısı eğildi, ivme kayboldu. Denge bozuluyor, yavaş yavaş destekler test edilecek. Sonuç ve UYARI kısmına dikkat👇"
        
        elif c_score < 40 and c_rsi < 30 and c_vol > 15:
            txt_baslik = f"🦈 {clean_ticker}: Likidite Avı! Stopları Patlattılar mı?"
            txt_kanca = f"Desteğin altına atılan o hacimli iğne tesadüf değil. {j_aktor} panikleyenlerin ucuz malını mı topluyor? Sonuç ve UYARI kısmına dikkat👇"

        elif c_score > 40 and c_vol > 25 and c_rsi < 60:
            txt_baslik = f"🦅 {clean_ticker}: Anka Kuşu! Küllerinden Doğuyor mu?"
            txt_kanca = "Dünün kaybını devasa hacimle tek lokmada yuttu! Ayılar gafil avlandı, rüzgar aniden döndü. Sonuç ve UYARI kısmına dikkat👇"
        
        elif c_score > 75 and 48 < c_rsi < 55:
            txt_baslik = f"⚓ {clean_ticker}: Trend Onayı! Güvenli Giriş Limanı mı?"
            txt_kanca = "Fırtına dindi, RSI tam 50 desteğinden güç aldı. Skor zirvedeyken en güvenli alım penceresi mi? Sonuç ve UYARI kısmına dikkat👇"

        # --- 5. GRUP: ARZ-TALEP (SUPPLY/DEMAND) FORMASYONLARI ---
        
        # 1. RALLY - BASE - RALLY (RBR)
        elif aylik_getiri > 10.0 and 50 < c_rsi < 65 and c_vol < 10 and c_score > 65:
            txt_baslik = f"🚀 {clean_ticker}: Rally-Base-Rally! Yeni Zirve Hazırlığı mı?"
            txt_kanca = "Güçlü bir yükseliş (Rally), ardından hacimsiz bir dinlenme (Base) ve şimdi yeniden yukarı sinyali! İkinci dalga başlıyor mu? Sonuç ve UYARI kısmına dikkat👇"
            
        # 2. DROP - BASE - RALLY (DBR)
        elif aylik_getiri < -10.0 and 40 < c_rsi < 55 and c_ict >= 15:
            txt_baslik = f"🧲 {clean_ticker}: Drop-Base-Rally! Dip Dönüşü Onaylandı mı?"
            txt_kanca = "Sert düşüş (Drop) sonrası yatay bantta (Base) mal toplandı ve şimdi Market Yapısı Kırılımı (MSS/Rally) geldi! Akıllı para trene bindi mi? Sonuç ve UYARI kısmına dikkat👇"

        # 3. DROP - BASE - DROP (DBD)
        elif aylik_getiri < -5.0 and 40 < c_rsi < 50 and c_score < 35:
            txt_baslik = f"📉 {clean_ticker}: Drop-Base-Drop! Ayıların İnsafı Yok mu?"
            txt_kanca = "Düşüş (Drop) sonrası soluklanma (Base) başarısız oldu. Destekler kırılıyor, yeni bir satış dalgası mı tetikleniyor? Sonuç ve UYARI kısmına dikkat👇"
            
        # 4. RALLY - BASE - DROP (RBD)
        elif aylik_getiri > 15.0 and 55 < c_rsi < 70 and c_score < 45:
            txt_baslik = f"🧱 {clean_ticker}: Rally-Base-Drop! Zirvede Dağıtım Formasyonu mu?"
            txt_kanca = "Güçlü ralli (Rally) sonrası tepede oyalama (Base) ve şimdi skor hızla düşüyor (Drop). Büyük oyuncular malı devredip çıkıyor mu? Sonuç ve UYARI kısmına dikkat👇"

        # 5. ÖLÜMCÜL YATAY BANT (Uzun Süreli Konsolidasyon)
        elif -3.0 < aylik_getiri < 3.0 and 45 < c_rsi < 55 and c_vol < 8:
            txt_baslik = f"⏳ {clean_ticker}: Ölümcül Yatay Bant! Akümülasyon mu, Dağıtım mı?"
            txt_kanca = "Uzun süredir yön bulamıyor. Hacim ölü, getiri sıfır. Bu devasa sıkışmanın sonu efsanevi bir patlama mı olacak? Sonuç ve UYARI kısmına dikkat👇"

        # --- ESKİLER ---
        elif c_vol > 18 and c_score > 60:
            txt_baslik = f"🐋 {clean_ticker}: Balina Hazırlığı! Gizli Toplama mı?"
            txt_kanca = f"Fiyat henüz patlamadı ama Hacim çıldırıyor. {j_aktor} büyük bir ralli için vagonları mı dolduruyor? Sonuç ve UYARI kısmına dikkat👇"

        elif c_rs > 88:
            txt_baslik = f"👑 {clean_ticker}: Piyasaya Meydan Okuyan Lider!"
            txt_kanca = f"{context_rakip} düşerken o neden dimdik ayakta? Kurumsal koruma kalkanı devrede! Sonuç ve UYARI kısmına dikkat👇"

        elif c_score >= 85:
            txt_baslik = f"🚀 {clean_ticker}: Roket Modu Açıldı, Hedef Neresi?"
            txt_kanca = "Trend o kadar güçlü ki önüne geleni eziyor! Kusursuz skor, amansız yükseliş! Sonuç ve UYARI kısmına dikkat👇"

        elif c_score >= 60 and c_rsi < 50:
            txt_baslik = f"🧘 {clean_ticker}: Boğaların Dinlenme Tesisleri! (Pit Stop)"
            txt_kanca = "Skor hala güçlü ama RSI dinleniyor. Bu bir çöküş değil, yeni bir sıçrama öncesi enerji toplama molası. Sonuç ve UYARI kısmına dikkat👇"

        elif c_score >= 40 and c_rsi < 30:
            txt_baslik = f"🎯 {clean_ticker}: Korkunun Zirvesinde Sniper Atışı!"
            txt_kanca = "Korku tavan yaptı, fiyat 'Bedava' bölgesine düştü. RSI diplerdeyken cesaret eden kazanacak mı? Sonuç ve UYARI kısmına dikkat👇"

        elif c_score < 35 and c_rsi < 40:
            txt_baslik = f"🔪 {clean_ticker}: Düşen Bıçağı Tutmak? (Yüksek Risk)"
            txt_kanca = "Ucuz görünüyor ama teknik yapı iflas çekiyor. Dip sandığın yer aslında yeni bir uçurumun kenarı olabilir. Sonuç ve UYARI kısmına dikkat👇"

        elif 35 < c_score < 55 and 40 < c_rsi < 60:
            txt_baslik = f"🐢 {clean_ticker}: Bezdirme Politikası mı Devrede?"
            txt_kanca = "Ne düşüyor ne çıkıyor. Gitmiyor diye sattığınız an uçuracaklar mı? Büyük bir sabır testi! Sonuç ve UYARI kısmına dikkat👇"

        elif c_vol < 5 and c_score < 50:
            txt_baslik = f"🚜 {clean_ticker}: Zaman Kaybı mı, Güvenli Liman mı?"
            txt_kanca = "Herkes kazanırken o yerinde sayıyor. Hacim yok, skor düşük. Tahta yapıcısı tatile mi çıktı? Sonuç ve UYARI kısmına dikkat👇"

        elif c_score < 50 and c_rsi > 70:
            txt_baslik = f"🪤 {clean_ticker}: Kusursuz Boğa Tuzağı mı? (Gel-Gel)"
            txt_kanca = "Fiyat çıkıyor, RSI şişiyor ama ana skor desteklemiyor. Malı kitleyip kaçma ihtimalleri masada! Sonuç ve UYARI kısmına dikkat👇"

        elif c_rsi > 85:
            txt_baslik = f"🔥 {clean_ticker}: Motor Hararet Yaptı mı? (Aşırı Isınma)"
            txt_kanca = "RSI tarihi zirvede! Rasyonellik bitti, FOMO başladı. Kârı alıp kenara çekilme vakti mi? Sonuç ve UYARI kısmına dikkat👇"

        else:
            txt_baslik = f"👀 {clean_ticker}: Radara Girdi! Hazırlık Başladı mı?"
            txt_kanca = "Henüz net bir 'AL' veya 'SAT' kırılımı yok ama göstergeler hareketleniyor. Kritik eşik neresi? Sonuç ve UYARI kısmına dikkat👇"

        # ---------------------------------------------------------
        # 4. ADIM: NİHAİ TWEET (ICT MOTORUNA TAM ENTEGRE)
        # ---------------------------------------------------------

        # 1. AKILLI HATA ÇÖZÜMÜ: Eğer hiçbir senaryoya girmediyse, ICT MOTORUNDAN VERİ ÇEK!
        if 'txt_kanit' not in locals():
            
            # A) Skor Güvenlik Kontrolü
            safe_score = c_score if 'c_score' in locals() else 0
            
            # ==============================================================================
            # AKILLI VİTRİN MANTIĞI (Dinamik Başlıklar v2.0)
            # ==============================================================================
            
            # 1. DİNAMİK MADDELEME (Rüya Takımı Modu - Önem Sırasına Göre)
            dinamik_maddeler = []

            # A) NADİR KURULUMLAR VE ICT (AKILLI PARA) SİNYALLERİ (EN YÜKSEK ÖNCELİK)
            if check_royal:
                dinamik_maddeler.append("👑 Kusursuz Kurulum: Flash Royal (4/4 Onay)")
            elif check_golden:
                dinamik_maddeler.append("🏆 Altın Fırsat: Golden Trio (3/3 Onay)")
                
            if 'ict_data' in locals() and ict_data:
                if "MSS" in str(ict_data) or "BOS" in str(ict_data) or c_ict >= 15:
                    dinamik_maddeler.append("🐳 Smart Money: Market Yapısı Kırılımı (BOS/MSS)")

            # B) DİNAMİK DESTEK / DİRENÇ KONTROLÜ
            if 'ict_data' in locals() and ict_data:
                import re
                try:
                    bl_text = ict_data.get('bottom_line', '').split('için')[-1]
                    match = re.search(r"(\d+\.?\d*)", bl_text)
                    if match:
                        val_float = float(match.group(1))
                        curr_p = info.get('price', 0) if 'info' in locals() and info else 0
                        if curr_p > 0 and val_float < curr_p:
                            dinamik_maddeler.append(f"🛡️ Kale (Destek): {val_float:,.2f}")
                        elif curr_p > 0:
                            dinamik_maddeler.append(f"🧱 Duvar (Direnç): {val_float:,.2f}")
                except:
                    pass

            # C) RSI VE HACİM ANOMALİLERİ (PRICE ACTION)
            if 'rsi_val' in locals():
                if rsi_val < 30:
                    dinamik_maddeler.append(f"💎 Aşırı Satım: RSI {int(rsi_val)} (Dip Fırsatı)")
                elif rsi_val > 70:
                    dinamik_maddeler.append(f"⚠️ Aşırı Alım: RSI {int(rsi_val)} (Şişkinlik Uyarısı)")
            
            if c_vol < 5 and 45 < c_rsi < 55:
                dinamik_maddeler.append("💣 Hacim Kuruması: Fırtına Öncesi Sessizlik (Squeeze)")
            elif c_vol > 20:
                dinamik_maddeler.append("🌊 Anormal Hacim: Kurumsal Giriş İhtimali")

            # D) ALGORİTMİK SKOR (ZORUNLU DEĞİL, DURUMA GÖRE EKLENİR)
            if safe_score >= 80:
                dinamik_maddeler.append(f"🚀 Algoritmik Skor: {safe_score}/100 (Ralli Gücü)")
            elif safe_score <= 30:
                dinamik_maddeler.append(f"🩸 Algoritmik Skor: {safe_score}/100 (Yüksek Risk)")
            elif len(dinamik_maddeler) < 3: # Sadece liste boşsa ortalama skoru göster
                dinamik_maddeler.append(f"⚖️ Denge Skoru: {safe_score}/100")

            # E) LİSTEYİ FİLTRELE (SADECE EN KRİTİK İLK 3 MADDEYİ AL)
            # Kod akışı zaten en önemliden en aza doğru eklendiği için direkt ilk 3'ü alıyoruz.
            secilen_maddeler = dinamik_maddeler[:3]
            
            # Eğer her şeye rağmen boş kalırsa
            if not secilen_maddeler:
                secilen_maddeler.append("👀 Görünüm: Yön Arayışında (Nötr)")

            # D) Metni Birleştir (Dinamik Etiketler)
            txt_kanit = "\n".join(secilen_maddeler)
            
            # E) Başlık ve Kanca Kontrolü
            if 'txt_baslik' not in locals():
                txt_baslik = "Yön Arayışında (Karar Anı)"
                
            if 'txt_kanca' not in locals():
                txt_kanca = "Net bir sinyal yok ama teknik seviyeler konuşuyor. İşte son durum... 👇"

        # 2. SATIRLARI OLUŞTURMA
        satirlar = []

        # A) BAŞLIK AYARI (Sadece Metin)
        if clean_ticker in txt_baslik:
            final_baslik = txt_baslik.replace(clean_ticker, f"#{clean_ticker}", 1)
        else:
            final_baslik = f"#{clean_ticker}: {txt_baslik}"
            
        satirlar.append(final_baslik)

        # Kanca Metni
        if 'txt_kanca' in locals():
            satirlar.append(txt_kanca)

        # Teknik Kanıtlar Başlığı
        satirlar.append("📊 TEKNİK KANITLAR:")

        # B) MADDE İŞARETİ AYARI (Çift Yıldız Sorunu Çözüldü)
        # Kanıt satırlarını kontrol et, zaten şekilli geliyorsa dokunma.
        if 'txt_kanit' in locals():
            for s in txt_kanit.split('\n'):
                line = s.strip()
                if line:
                    # Eğer satır zaten bir simgeyle başlıyorsa (🔹, 🚀, 🩸 vb.) OLDUĞU GİBİ ekle
                    if any(line.startswith(char) for char in ["🔹", "🔸", "▪️", "🚀", "🩸", "🛡️", "⚖️", "🧱", "🚧", "💎", "⚠️", "🌊", "🌧️"]):
                        satirlar.append(line)
                    else:
                        # Başlamıyorsa mavi elması biz ekleyelim
                        satirlar.append(f"🔹 {line}")

        # Alt Bilgi
        satirlar.append("Detaylı analiz ve resimli risk haritası için buyrun: 👇")

        # 3. LİSTEYİ BİRLEŞTİR VE SONUCU ÜRET
        final_tweet_safe = "\n".join(satirlar)

        # 4. ADIM: EKRANA BASMA (Sınırlı yükseklik ve kopyalama butonlu)
        st.markdown("𝕏 Başlık:")
        with st.container(height=200): 
            st.code(final_tweet_safe, language="text")
        st.caption("📸 Analizin veya Grafiğin ekran görüntüsünü eklemeyi unutma!")
    st.session_state.generate_prompt = False

info = fetch_stock_info(st.session_state.ticker)

col_left, col_right = st.columns([4, 1])

# --- SOL SÜTUN ---
with col_left:
    # 1. PARA AKIŞ İVMESİ & FİYAT DENGESİ (EN TEPE)
    synth_data = calculate_synthetic_sentiment(st.session_state.ticker)
    if synth_data is not None and not synth_data.empty: render_synthetic_sentiment_panel(synth_data)
    
    # 2. ANA SKOR PANELİ (İKİNCİ SIRA)
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    
    master_score, score_pros, score_cons = calculate_master_score(st.session_state.ticker)

    # --- YENİ 4 SÜTUNLU ANA SKOR DÜZENİ ---
    # Oranları 4 sütuna göre dengeledik: Hız göstergesi(1.2), Artılar(1.9, Eksiler(1.9), Ortalamalar(1.4)
    c_gauge, c_pos, c_neg, c_ma = st.columns([1.2, 1.9, 1.9, 1.4], vertical_alignment="center")
    
    # CSS: Özel ve İnce Kaydırma Çubuğu (Custom Scrollbar)
    custom_scrollbar_css = """
    <style>
    .custom-scroll::-webkit-scrollbar { width: 6px; }
    .custom-scroll::-webkit-scrollbar-track { background: transparent; }
    .custom-scroll::-webkit-scrollbar-thumb { background-color: rgba(0,0,0,0.15); border-radius: 10px; }
    .custom-scroll:hover::-webkit-scrollbar-thumb { background-color: rgba(0,0,0,0.3); }
    </style>
    """
    st.markdown(custom_scrollbar_css, unsafe_allow_html=True)

    # 1. SÜTUN: HIZ GÖSTERGESİ
    with c_gauge:
        bosluk_sol, grafik_alani, bosluk_sag = st.columns([0.2, 1, 0.2]) 
        with grafik_alani:
            render_gauge_chart(master_score)

    # 2. SÜTUN: POZİTİF ETKENLER (YEŞİL KUTU)
    with c_pos:
        pos_items_html = ""
        if score_pros:
            for p in score_pros:
                # DİKKAT: Baştaki hardcoded ✅ işaretini kaldırdık, çünkü fonksiyondan geliyor!
                pos_items_html += f"<div style='font-size:0.8rem; color:#14532d; margin-bottom:1px; padding:3px 2px; border-bottom:1px solid rgba(22, 163, 74, 0.2);'>{p}</div>"
        else:
            pos_items_html = "<div style='font-size:0.8rem; color:#14532d; padding:6px 2px;'>Belirgin pozitif etken yok.</div>"

        st.markdown(f"""
        <div class="custom-scroll" style="background-color:#f0fdf4; border:1px solid #16a34a; border-radius:8px; padding:0; height:200px; overflow-y:auto; position:relative; box-shadow: 0 4px 6px -1px rgba(22, 163, 74, 0.1);">
            <div style="font-weight:800; font-size:0.85rem; color:#15803d; background-color:#dcfce7; padding:10px 12px; border-bottom:2px solid #16a34a; position:sticky; top:0; z-index:10; display:flex; justify-content:space-between;">
                <span>POZİTİF ETKENLER</span>
                <span style="background-color:#16a34a; color:white; padding:2px 8px; border-radius:12px; font-size:0.75rem;">{len(score_pros)}</span>
            </div>
            <div style="padding:8px 12px;">
                {pos_items_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 3. SÜTUN: NEGATİF ETKENLER (KIRMIZI KUTU)
    with c_neg:
        neg_items_html = ""
        if score_cons:
            for c in score_cons:
                # DİKKAT: Baştaki hardcoded ❌ işaretini kaldırdık, çünkü cons listesine sadece 0 alanları attık.
                # Arayüzde net bir kırmızı çarpı görünmesi için buraya sadece ❌ ekliyoruz.
                neg_items_html += f"<div style='font-size:0.8rem; color:#7f1d1d; margin-bottom:1px; padding:3px 2px; border-bottom:1px solid rgba(220, 38, 38, 0.2);'>❌ {c}</div>"
        else:
            neg_items_html = "<div style='font-size:0.8rem; color:#7f1d1d; padding:6px 2px;'>Belirgin negatif etken yok.</div>"

        st.markdown(f"""
        <div class="custom-scroll" style="background-color:#fef2f2; border:1px solid #dc2626; border-radius:8px; padding:0; height:200px; overflow-y:auto; position:relative; box-shadow: 0 4px 6px -1px rgba(220, 38, 38, 0.1);">
            <div style="font-weight:800; font-size:0.85rem; color:#b91c1c; background-color:#fee2e2; padding:10px 12px; border-bottom:2px solid #dc2626; position:sticky; top:0; z-index:10; display:flex; justify-content:space-between;">
                <span>NEGATİF ETKENLER</span>
                <span style="background-color:#dc2626; color:white; padding:2px 8px; border-radius:12px; font-size:0.75rem;">{len(score_cons)}</span>
            </div>
            <div style="padding:8px 12px;">
                {neg_items_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 4. SÜTUN: HAREKETLİ ORTALAMALAR (YENİ - MAVİ KUTU / 2 SÜTUNLU)
    with c_ma:
        ma_data = get_ma_data_for_ui(st.session_state.ticker)
        
        if ma_data:
            c = ma_data["close"]
            
            def render_ma_row(name, val, current_price):
                if pd.isna(val) or val == 0: return ""
                
                # Fiyat üstündeyse yeşil, altındaysa kırmızı daire
                color_icon = "🟢" if current_price > val else "🔴"
                
                # 1000 ve üzeri değerlerde ondalık kısmı at, virgülle ayır (Örn: 13,915)
                # 1000 altı değerlerde ise 2 küsurat bırak (Örn: 15.42)
                if val >= 1000:
                    val_str = f"{int(val):,}"
                else:
                    val_str = f"{val:,.2f}"
                
                # İki sütuna sığması için font-size'ı 0.8rem'den 0.75rem'e düşürdük
                return f"<div style='font-size:0.75rem; color:#334155; margin-bottom:4px; padding:4px 2px; border-bottom:1px solid rgba(0,0,0,0.05); display:flex; justify-content:space-between; align-items:center;'><span>{name}</span> <span><b>{val_str}</b> {color_icon}</span></div>"
            
            # EMA'ları ve SMA'ları ayrı ayrı HTML değişkenlerine alıyoruz
            ema_html = ""
            ema_html += render_ma_row("EMA 5", ma_data["ema5"], c)
            ema_html += render_ma_row("EMA 8", ma_data["ema8"], c)
            ema_html += render_ma_row("EMA 13", ma_data["ema13"], c)
            
            sma_html = ""
            sma_html += render_ma_row("SMA 50", ma_data["sma50"], c)
            sma_html += render_ma_row("SMA 100", ma_data["sma100"], c)
            sma_html += render_ma_row("SMA 200", ma_data["sma200"], c)
            
            # CSS Grid (display: grid; grid-template-columns: 1fr 1fr;) ile ikiye bölüyoruz
            # Streamlit hatası almamak için HTML bloğunu TAMAMEN sola yaslıyoruz
            final_html = f"""
<div class="custom-scroll" style="background-color:#f8fafc; border:1px solid #94a3b8; border-radius:8px; padding:0; height:200px; overflow-y:auto; position:relative; box-shadow: 0 4px 6px -1px rgba(148, 163, 184, 0.1);">
<div style="font-weight:800; font-size:0.85rem; color:#334155; background-color:#e2e8f0; padding:10px 12px; border-bottom:2px solid #94a3b8; position:sticky; top:0; z-index:10; text-align:center;">
HAREKETLİ ORTALAMALAR 
</div>
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 10px 12px;">
<div>
{ema_html}
</div>
<div>
{sma_html}
</div>
</div>
</div>
"""
            st.markdown(final_html, unsafe_allow_html=True)
            
        else:
            st.markdown("<div style='font-size:0.8rem; color:#64748b; padding:6px 2px;'>Veri hesaplanamadı.</div>", unsafe_allow_html=True)



    # 3. ICT SMART MONEY ANALİZİ (YENİ YERİ: ANA SKOR ALTINDA)
    # (Not: Fonksiyon içinde zaten 2 sütuna bölme işlemi yapıldı, burada sadece çağırıyoruz)
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    render_ict_deep_panel(st.session_state.ticker)

    # 4. GELİŞMİŞ TEKNİK KART (ICT ALTINDA)
    render_detail_card_advanced(st.session_state.ticker)

    # ---------------------------------------------------------
    # 🦅 YENİ: ICT SNIPER AJANI (TARAMA PANELİ)
    # Konum: Bear Trap Altı, Minervini Üstü
    # ---------------------------------------------------------
    if 'ict_scan_data' not in st.session_state: st.session_state.ict_scan_data = None

    st.markdown('<div class="info-header" style="margin-top: 20px; margin-bottom: 5px;">🦅 ICT Sniper Ajanı (Kurumsal Kurulum: 90/100)</div>', unsafe_allow_html=True)
    
    # 1. TARAMA BUTONU
    if st.button(f"🦅 KURUMSAL SETUP TARA ({st.session_state.category})", type="secondary", use_container_width=True, key="btn_scan_ict"):
        with st.spinner("Kurumsal ayak izleri (MSS + Displacement + FVG) taranıyor..."):
            current_assets = ASSET_GROUPS.get(st.session_state.category, [])
            # Daha önce yazdığımız (veya yazacağımız) batch fonksiyonu buraya gelecek
            # Şimdilik placeholder (yer tutucu) fonksiyonu çağırıyoruz, aşağıda tanımlayacağız
            st.session_state.ict_scan_data = scan_ict_batch(current_assets) 
            
    # 2. SONUÇ EKRANI (ÇİFT SÜTUNLU)
    if st.session_state.ict_scan_data is not None:
        df_res = st.session_state.ict_scan_data
        
        if not df_res.empty:
            # Long ve Shortları ayır
            longs = df_res[df_res['Yön'] == 'LONG']
            shorts = df_res[df_res['Yön'] == 'SHORT']
            
            # İki Sütun Oluştur
            c_long, c_short = st.columns(2)
            
            # --- SOL SÜTUN: LONG FIRSATLARI ---
            with c_long:
                st.markdown(f"<div style='text-align:center; color:#16a34a; font-weight:800; background:#f0fdf4; padding:5px; border-radius:5px; border:1px solid #86efac; margin-bottom:10px;'>🐂 LONG (Yükseliş) SETUPLARI ({len(longs)})</div>", unsafe_allow_html=True)
                if not longs.empty:
                    with st.container(height=100):
                        for i, row in longs.iterrows():
                            sym = row['Sembol']
                            # Etiket: 🐂 THYAO (300.0) | Hedef: Yukarı
                            label = f"🐂 {sym.replace('.IS', '')} ({row['Fiyat']:.2f}) | {row['Durum']}"
                            if st.button(label, key=f"ict_long_{sym}_{i}", use_container_width=True, help=f"Stop Loss: {row['Stop_Loss']}"):
                                on_scan_result_click(sym)
                                st.rerun()
                else:
                    st.info("Long yönlü kurumsal Setup yok.")

            # --- SAĞ SÜTUN: SHORT FIRSATLARI ---
            with c_short:
                st.markdown(f"<div style='text-align:center; color:#dc2626; font-weight:800; background:#fef2f2; padding:5px; border-radius:5px; border:1px solid #fca5a5; margin-bottom:10px;'>🐻 SHORT (Düşüş) SETUPLARI ({len(shorts)})</div>", unsafe_allow_html=True)
                if not shorts.empty:
                    with st.container(height=100):
                        for i, row in shorts.iterrows():
                            sym = row['Sembol']
                            # Etiket: 🐻 GARAN (100.0) | Hedef: Aşağı
                            label = f"🐻 {sym.replace('.IS', '')} ({row['Fiyat']:.2f}) | {row['Durum']}"
                            if st.button(label, key=f"ict_short_{sym}_{i}", use_container_width=True, help=f"Stop Loss: {row['Stop_Loss']}"):
                                on_scan_result_click(sym)
                                st.rerun()
                else:
                    st.info("Short yönlü kurumsal Setup yok.")
                    
        else:
            st.info("Şu an 'High Probability' (Yüksek Olasılıklı) ICT kurulumu (ne Long ne Short) tespit edilemedi.") 
    # ---------------------------------------------------------
    # 🚀 YENİ: RS MOMENTUM LİDERLERİ (ALPHA TARAMASI) - EN TEPEYE
    # ---------------------------------------------------------
    if 'rs_leaders_data' not in st.session_state: st.session_state.rs_leaders_data = None

    st.markdown('<div class="info-header" style="margin-top: 5px; margin-bottom: 5px;">🕵️ RS Momentum Liderleri (Piyasa Şampiyonları: 80/100)</div>', unsafe_allow_html=True)
    
    # 1. TARAMA BUTONU
    if st.button(f"🕵️ SON 5 GÜNDE ENDEKSTEN HIZLI YÜKSELENLERİ GETİR ({st.session_state.category})", type="secondary", use_container_width=True, key="btn_scan_rs_leaders"):
        with st.spinner("Piyasayı ezip geçen hisseler (Alpha > %2) sıralanıyor..."):
            current_assets = ASSET_GROUPS.get(st.session_state.category, [])
            # Daha önce tanımladığımız fonksiyonu çağırıyoruz
            st.session_state.rs_leaders_data = scan_rs_momentum_leaders(current_assets)
            
    # 2. SONUÇ EKRANI
    if st.session_state.rs_leaders_data is not None:
        count = len(st.session_state.rs_leaders_data)
        if count > 0:
            # st.success(f"🏆 Endeksi yenen {count} adet şampiyon bulundu!")
            with st.container(height=250, border=True):
                for i, row in st.session_state.rs_leaders_data.iterrows():
                    # Verileri Satırdan Çekiyoruz (Fonksiyondan gelen yeni sütunlar)
                    sym = row['Sembol']
                    alpha_5 = row['Alpha_5D']
                    alpha_1 = row.get('Alpha_1D', 0) # Hata olmasın diye .get kullanıyoruz
                    degisim_1 = row.get('Degisim_1D', 0)
                    vol = row['Hacim_Kat']
                    
                    # Renkler ve İkon (5 Günlük performansa göre ana rengi belirle)
                    icon = "🔥" if alpha_5 > 5.0 else "💪"
                    
                    # Bugünün Durumu (Metin)
                    today_status = "LİDER" if alpha_1 > 0.5 else "ZAYIF" if alpha_1 < -0.5 else "NÖTR"
                    
                    # YENİ BUTON METNİ: ||| Çizgili Format
                    # Örn: 🔥 BURVA.IS (684.00) | Alpha(5G): +%42.7 | Vol: 0.9x ||| Bugün: +%5.2 (LİDER)
                    label = f"{icon} {sym.replace('.IS', '')} ({row['Fiyat']:.2f}) | Alpha(5G): +%{alpha_5:.1f} | Vol: {vol:.1f}x ||| Bugün: %{degisim_1:.1f} ({today_status})"
                    
                    if st.button(label, key=f"rs_lead_{sym}_{i}", use_container_width=True):
                        on_scan_result_click(sym)
                        st.rerun()
        else:
            st.info("Şu an endekse belirgin fark atan (%2+) hisse bulunamadı.")

    # Araya bir çizgi çekelim ki Sentiment Ajanı ile karışmasın
    st.markdown("<hr style='margin-top:15px; margin-bottom:15px;'>", unsafe_allow_html=True)
    # ---------------------------------------------------------------    
    st.markdown('<div class="info-header" style="margin-top: 15px; margin-bottom: 10px;">🕵️ Sentiment Ajanı (Akıllı Para Topluyor: 60/100)</div>', unsafe_allow_html=True)
    
    if 'accum_data' not in st.session_state: st.session_state.accum_data = None
    if 'stp_scanned' not in st.session_state: st.session_state.stp_scanned = False
    if 'stp_crosses' not in st.session_state: st.session_state.stp_crosses = []
    if 'stp_trends' not in st.session_state: st.session_state.stp_trends = []
    if 'stp_filtered' not in st.session_state: st.session_state.stp_filtered = []

    if st.button(f"🕵️ SENTIMENT & MOMENTUM TARAMASI BAŞLAT ({st.session_state.category})", type="secondary", use_container_width=True):
        with st.spinner("Ajan piyasayı didik didik ediyor (STP + Akıllı Para Topluyor?)..."):
            current_assets = ASSET_GROUPS.get(st.session_state.category, [])
            crosses, trends, filtered = scan_stp_signals(current_assets)
            st.session_state.stp_crosses = crosses
            st.session_state.stp_trends = trends
            st.session_state.stp_filtered = filtered
            st.session_state.stp_scanned = True
            st.session_state.accum_data = scan_hidden_accumulation(current_assets)

    if st.session_state.stp_scanned or (st.session_state.accum_data is not None):

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.markdown("<div style='text-align:center; color:#1e40af; font-weight:700; font-size:0.9rem; margin-bottom:5px;'>⚡ STP'Yİ YUKARI KESTİ</div>", unsafe_allow_html=True)
            with st.container(height=200, border=True):
                if st.session_state.stp_crosses:
                    for item in st.session_state.stp_crosses:
                        if st.button(f"🚀 {item['Sembol']} ({item['Fiyat']:.2f})", key=f"stp_c_{item['Sembol']}", use_container_width=True): 
                            st.session_state.ticker = item['Sembol']
                            st.rerun()
                else:
                    st.caption("Kesişim yok.")
        
        with c2:
            st.markdown("<div style='text-align:center; color:#b91c1c; font-weight:700; font-size:0.8rem; margin-bottom:5px;'>🎯 MOMENTUM BAŞLANGICI?</div>", unsafe_allow_html=True)
            with st.container(height=200, border=True):
                if st.session_state.stp_filtered:
                    for item in st.session_state.stp_filtered:
                        if st.button(f"🔥 {item['Sembol']} ({item['Fiyat']:.2f})", key=f"stp_f_{item['Sembol']}", use_container_width=True): 
                            st.session_state.ticker = item['Sembol']
                            st.rerun()
                else:
                    st.caption("Tam eşleşme yok.")

        with c3:
            st.markdown("<div style='text-align:center; color:#15803d; font-weight:700; font-size:0.8rem; margin-bottom:5px;'>✅ STP ÜSTÜNDEKİ TREND</div>", unsafe_allow_html=True)
            with st.container(height=200, border=True):
                if st.session_state.stp_trends:
                    for item in st.session_state.stp_trends:
                        # HATA DÜZELTME: .get() kullanarak eğer 'Gun' verisi yoksa '?' koy, çökmesin.
                        gun_sayisi = item.get('Gun', '?')
                        
                        if st.button(f"📈 {item['Sembol']} ({gun_sayisi} Gün)", key=f"stp_t_{item['Sembol']}", use_container_width=True): 
                            st.session_state.ticker = item['Sembol']
                            st.rerun()
                else:
                    st.caption("Trend yok.")

        with c4:
            st.markdown("<div style='text-align:center; color:#7c3aed; font-weight:700; font-size:0.8rem; margin-bottom:5px;'>🤫 AKILLI PARA TOPLUYOR?</div>", unsafe_allow_html=True)
            
            with st.container(height=200, border=True):
                if st.session_state.accum_data is not None and not st.session_state.accum_data.empty:
                    for index, row in st.session_state.accum_data.iterrows():
                        
                        # İkon Belirleme (Pocket Pivot varsa Yıldırım, yoksa Şapka)
                        icon = "⚡" if row.get('Pocket_Pivot', False) else "🎩"
                        
                        # Buton Metni: "⚡ AAPL (150.20) | RS: Güçlü"
                        # RS bilgisini kısa tutuyoruz
                        rs_raw = str(row.get('RS_Durumu', 'Not Yet'))
                        rs_short = "RS+" if "GÜÇLÜ" in rs_raw else "Not Yet"
                        
                        # Buton Etiketi
                        # Kaliteye göre kısa etiket
                        q_tag = "💎 A" if "A KALİTE" in row.get('Kalite', '') else "B"

                        # Buton Etiketi (A ise Elmas koyar, B ise sadece harf)
                        btn_label = f"{icon} {row['Sembol'].replace('.IS', '')} ({row['Fiyat']}) | {q_tag} | {rs_short}"
                        
                        # Basit ve Çalışan Buton Yapısı
                        if st.button(btn_label, key=f"btn_acc_{row['Sembol']}_{index}", use_container_width=True):
                            on_scan_result_click(row['Sembol'])
                            st.rerun()
                else:
                    st.caption("Tespit edilemedi.")

    # --- DÜZELTİLMİŞ BREAKOUT & KIRILIM İSTİHBARATI BÖLÜMÜ ---
    st.markdown('<div class="info-header" style="margin-top: 15px; margin-bottom: 10px;">🕵️ Breakout Ajanı (Isınanlar: 75/100)</div>', unsafe_allow_html=True)
    
    # Session State Tanımları (Eğer yoksa)
    if 'breakout_left' not in st.session_state: st.session_state.breakout_left = None
    if 'breakout_right' not in st.session_state: st.session_state.breakout_right = None

    
    if st.button(f"⚡ {st.session_state.category} İÇİN BREAK-OUT TARAMASI BAŞLAT", type="secondary", key="dual_breakout_btn", use_container_width=True):
        with st.spinner("Ajanlar sahaya indi: Hem ısınanlar hem kıranlar taranıyor..."):
            curr_list = ASSET_GROUPS.get(st.session_state.category, [])
            # Paralel tarama simülasyonu (Sırayla çalışır ama hızlıdır)
            st.session_state.breakout_left = agent3_breakout_scan(curr_list) # Mevcut Isınanlar
            st.session_state.breakout_right = scan_confirmed_breakouts(curr_list) # Yeni Kıranlar
            st.rerun()
    if st.session_state.breakout_left is not None or st.session_state.breakout_right is not None:
       # 2 Sütunlu Sade Yapı (YENİ TASARIM)
        c_left, c_right = st.columns(2)
        
        # --- SOL SÜTUN: ISINANLAR (Hazırlık) ---
        with c_left:
            st.markdown("<div style='text-align:center; color:#d97706; font-weight:700; font-size:0.9rem; margin-bottom:5px; background:#fffbeb; padding:5px; border-radius:4px; border:1px solid #fcd34d;'>🔥 ISINANLAR (Hazırlık)</div>", unsafe_allow_html=True)
            
            with st.container(height=150): # Scroll Alanı
                if st.session_state.breakout_left is not None and not st.session_state.breakout_left.empty:
                    df_left = st.session_state.breakout_left.head(20)
                    for i, (index, row) in enumerate(df_left.iterrows()):
                        sym_raw = row.get("Sembol_Raw", row.get("Sembol", "UNK"))
                        
                        # HTML etiketlerini temizle (Sadece oranı al: %98 gibi)
                        prox_clean = str(row['Zirveye Yakınlık']).split('<')[0].strip()
                        
                        # Buton Metni: 🔥 AAPL (150.20) | %98
                        btn_label = f"🔥 {sym_raw} ({row['Fiyat']}) | {prox_clean}"
                        
                        if st.button(btn_label, key=f"L_btn_new_{sym_raw}_{i}", use_container_width=True):
                            on_scan_result_click(sym_raw)
                            st.rerun()
                else:
                    st.info("Isınan hisse bulunamadı.")
    
        # --- SAĞ SÜTUN: KIRANLAR (Onaylı) ---
        with c_right:
            st.markdown("<div style='text-align:center; color:#16a34a; font-weight:700; font-size:0.9rem; margin-bottom:5px; background:#f0fdf4; padding:5px; border-radius:4px; border:1px solid #86efac;'>🔨 KIRANLAR (Onaylı)</div>", unsafe_allow_html=True)
            
            with st.container(height=150): # Scroll Alanı
                if st.session_state.breakout_right is not None and not st.session_state.breakout_right.empty:
                    df_right = st.session_state.breakout_right.head(20)
                    for i, (index, row) in enumerate(df_right.iterrows()):
                        sym = row['Sembol']
                        
                        # Buton Metni: 🚀 TSLA (200.50) | Hacim: 2.5x
                        btn_label = f"🚀 {sym} ({row['Fiyat']}) | Hacim: {row['Hacim_Kati']}"
                        
                        if st.button(btn_label, key=f"R_btn_new_{sym}_{i}", use_container_width=True):
                            on_scan_result_click(sym)
                            st.rerun()
                else:
                    st.info("Kırılım yapan hisse bulunamadı.")

    # ---------------------------------------------------------
    # ⚖️ YENİ: RSI UYUMSUZLUK TARAMASI (SOL: AYI | SAĞ: BOĞA)
    # ---------------------------------------------------------
    if 'rsi_div_bull' not in st.session_state: st.session_state.rsi_div_bull = None
    if 'rsi_div_bear' not in st.session_state: st.session_state.rsi_div_bear = None

    st.markdown('<div class="info-header" style="margin-top: 15px; margin-bottom: 10px;">⚖️ RSI Uyumsuzluk Ajanı (70/100)</div>', unsafe_allow_html=True)

    if st.button(f"⚖️ UYUMSUZLUKLARI TARA ({st.session_state.category})", type="secondary", use_container_width=True, key="btn_scan_div"):
        with st.spinner("RSI ile Fiyat arasındaki yalanlar tespit ediliyor..."):
            current_assets = ASSET_GROUPS.get(st.session_state.category, [])
            # Tarama Fonksiyonunu Çağır
            bull_df, bear_df = scan_rsi_divergence_batch(current_assets)
            st.session_state.rsi_div_bull = bull_df
            st.session_state.rsi_div_bear = bear_df
            st.rerun()

    if st.session_state.rsi_div_bull is not None or st.session_state.rsi_div_bear is not None:
        c_div_left, c_div_right = st.columns(2)

        # --- SOL SÜTUN: NEGATİF (AYI) ---
        with c_div_left:
            st.markdown("<div style='text-align:center; color:#b91c1c; font-weight:700; font-size:0.8rem; margin-bottom:5px; background:#fef2f2; padding:5px; border-radius:4px; border:1px solid #fecaca;'>🐻 NEGATİF (Satış?)</div>", unsafe_allow_html=True)
            with st.container(height=150):
                if st.session_state.rsi_div_bear is not None and not st.session_state.rsi_div_bear.empty:
                    # Hacme göre sıralı geliyor zaten, ilk 20'yi al
                    for i, row in st.session_state.rsi_div_bear.head(20).iterrows():
                        sym = row['Sembol']
                        # Buton Metni: 🔻 THYAO (250.0) | RSI: 68
                        btn_label = f"🔻 {sym.replace('.IS', '')} ({row['Fiyat']:.2f}) | RSI: {row['RSI']}"
                        if st.button(btn_label, key=f"div_bear_{sym}_{i}", use_container_width=True):
                            on_scan_result_click(sym)
                            st.rerun()
                else:
                    st.caption("Negatif uyumsuzluk yok.")

        # --- SAĞ SÜTUN: POZİTİF (BOĞA) ---
        with c_div_right:
            st.markdown("<div style='text-align:center; color:#15803d; font-weight:700; font-size:0.8rem; margin-bottom:5px; background:#f0fdf4; padding:5px; border-radius:4px; border:1px solid #bbf7d0;'>💎 POZİTİF (Alış?)</div>", unsafe_allow_html=True)
            with st.container(height=150):
                if st.session_state.rsi_div_bull is not None and not st.session_state.rsi_div_bull.empty:
                    # Hacme göre sıralı
                    for i, row in st.session_state.rsi_div_bull.head(20).iterrows():
                        sym = row['Sembol']
                        # Buton Metni: ✅ ASELS (45.0) | RSI: 32
                        btn_label = f"✅ {sym.replace('.IS', '')} ({row['Fiyat']:.2f}) | RSI: {row['RSI']}"
                        if st.button(btn_label, key=f"div_bull_{sym}_{i}", use_container_width=True):
                            on_scan_result_click(sym)
                            st.rerun()
                else:
                    st.caption("Pozitif uyumsuzluk yok.")
    # ---------------------------------------------------------
    # 📐 YENİ: FORMASYON AJANI (TOBO, BAYRAK, RANGE)
    # ---------------------------------------------------------
    if 'pattern_data' not in st.session_state: st.session_state.pattern_data = None

    st.markdown('<div class="info-header" style="margin-top: 20px; margin-bottom: 5px;">📐 Formasyon Ajanı (TOBO, Bayrak, Range, Fincan-Kulp, Yükselen Üçgen)(65/100)</div>', unsafe_allow_html=True)
    
    # TARAMA BUTONU
    if st.button(f"📐 FORMASYONLARI TARA ({st.session_state.category})", type="secondary", use_container_width=True, key="btn_scan_pattern"):
        with st.spinner("Cetveller çekiliyor... Bayraklar ve TOBO'lar aranıyor..."):
            current_assets = ASSET_GROUPS.get(st.session_state.category, [])
            st.session_state.pattern_data = scan_chart_patterns(current_assets)
            
    # SONUÇ EKRANI
    if st.session_state.pattern_data is not None:
        count = len(st.session_state.pattern_data)
        if count > 0:
            # st.success(f"🧩 {count} adet formasyon yapısı tespit edildi!")
            with st.container(height=300, border=True):
                for i, row in st.session_state.pattern_data.iterrows():
                    sym = row['Sembol']
                    pat = row['Formasyon']
                    
                    # Renkler
                    icon = "🚩" if "BAYRAK" in pat else "📦" if "RANGE" in pat else "🧛"
                    
                    label = f"{icon} {sym.replace('.IS', '')} ({row['Fiyat']:.2f}) | {pat} (Puan: {int(row['Skor'])})"
                    
                    if st.button(label, key=f"pat_{sym}_{i}", use_container_width=True, help=row['Detay']):
                        on_scan_result_click(sym)
                        st.rerun()
        else:
            st.info("Şu an belirgin bir 'Kitabi Formasyon' (TOBO, Bayrak vb.) oluşumu bulunamadı.")
    # ---------------------------------------------------------
    # 🐻 BEAR TRAP (AYI TUZAĞI) AJANI - TARAMA PANELİ
    # ---------------------------------------------------------
    if 'bear_trap_data' not in st.session_state: st.session_state.bear_trap_data = None

    st.markdown('<div class="info-header" style="margin-top: 20px; margin-bottom: 5px;">🐻 Bear Trap Ajanı (Dip Avcısı)(80/100)</div>', unsafe_allow_html=True)
    
    # 1. TARAMA BUTONU
    if st.button(f"🐻 TUZAKLARI TARA ({st.session_state.category})", type="secondary", use_container_width=True, key="btn_scan_bear_trap"):
        with st.spinner("Ayı tuzakları ve likidite temizlikleri taranıyor (50 Mum Pivot)..."):
            current_assets = ASSET_GROUPS.get(st.session_state.category, [])
            st.session_state.bear_trap_data = scan_bear_traps(current_assets)
            
    # 2. SONUÇ EKRANI
    if st.session_state.bear_trap_data is not None:
        count = len(st.session_state.bear_trap_data)
        if count > 0:
            # st.success(f"🎯 {count} adet Bear Trap tespit edildi!")
            with st.container(height=250, border=True):
                for i, row in st.session_state.bear_trap_data.iterrows():
                    sym = row['Sembol']
                    
                    # Buton Metni: 🪤 GARAN (112.5) | ⏰ 2 Mum Önce | 2.5x Vol
                    label = f"🪤 {sym.replace('.IS', '')} ({row['Fiyat']:.2f}) | {row['Zaman']} | Vol: {row['Hacim_Kat']}"
                    
                    if st.button(label, key=f"bt_scan_{sym}_{i}", use_container_width=True, help=row['Detay']):
                        on_scan_result_click(sym)
                        st.rerun()
        else:
            st.info("Kriterlere uyan (50 mumluk dibi süpürüp dönen) hisse bulunamadı.")    

    # ---------------------------------------------------------
    # 🦁 YENİ: MINERVINI SEPA AJANI (SOL TARAF - TARAYICI)
    # ---------------------------------------------------------
    if 'minervini_data' not in st.session_state: st.session_state.minervini_data = None

    st.markdown('<div class="info-header" style="margin-top: 20px; margin-bottom: 5px;">🦁 Minervini SEPA Ajanı (85/100)</div>', unsafe_allow_html=True)
    
    # 1. TARAMA BUTONU
    if st.button(f"🦁 SEPA TARAMASI BAŞLAT ({st.session_state.category})", type="secondary", use_container_width=True, key="btn_scan_sepa"):
        with st.spinner("Aslan avda... Trend şablonu, VCP ve RS taranıyor..."):
            current_assets = ASSET_GROUPS.get(st.session_state.category, [])
            st.session_state.minervini_data = scan_minervini_batch(current_assets)
            
    # 2. SONUÇ EKRANI (Scroll Bar - 300px)
    if st.session_state.minervini_data is not None:
        count = len(st.session_state.minervini_data)
        if count > 0:
            # st.success(f"🎯 Kriterlere uyan {count} hisse bulundu!")
            with st.container(height=300, border=True):
                for i, row in st.session_state.minervini_data.iterrows():
                    sym = row['Sembol']
                    icon = "💎💎" if "SÜPER" in row['Durum'] else "🔥(İkinci)"
                    label = f"{icon} {sym} ({row['Fiyat']}) | {row['Durum']} | {row['Detay']}"
                    
                    if st.button(label, key=f"sepa_{sym}_{i}", use_container_width=True):
                        on_scan_result_click(sym)
                        st.rerun()
        else:
            st.warning("Bu zorlu kriterlere uyan hisse bulunamadı.")


    st.markdown(f"<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:20px;'>📡 {st.session_state.ticker} hakkında haberler ve analizler</div>", unsafe_allow_html=True)
    symbol_raw = st.session_state.ticker; base_symbol = (symbol_raw.replace(".IS", "").replace("=F", "").replace("-USD", "")); lower_symbol = base_symbol.lower()
    st.markdown(f"""<div class="news-card" style="display:flex; flex-wrap:wrap; align-items:center; gap:8px; border-left:none;"><a href="https://seekingalpha.com/symbol/{base_symbol}/news" target="_blank" style="text-decoration:none;"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.8rem; font-weight:600;">SeekingAlpha</div></a><a href="https://finance.yahoo.com/quote/{base_symbol}/news" target="_blank" style="text-decoration:none;"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.8rem; font-weight:600;">Yahoo Finance</div></a><a href="https://www.nasdaq.com/market-activity/stocks/{lower_symbol}/news-headlines" target="_blank" style="text-decoration:none;"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.8rem; font-weight:600;">Nasdaq</div></a><a href="https://stockanalysis.com/stocks/{lower_symbol}/" target="_blank" style="text-decoration:none;"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.8rem; font-weight:600;">StockAnalysis</div></a><a href="https://finviz.com/quote.ashx?t={base_symbol}&p=d" target="_blank" style="text-decoration:none;"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.8rem; font-weight:600;">Finviz</div></a><a href="https://unusualwhales.com/stock/{base_symbol}/overview" target="_blank" style="text-decoration:none;"><div style="padding:4px 8px; border-radius:4px; border:1px solid #e5e7eb; font-size:0.7rem; font-weight:600;">UnusualWhales</div></a></div>""", unsafe_allow_html=True)

# --- SAĞ SÜTUN ---
with col_right:
    if not info: info = fetch_stock_info(st.session_state.ticker)
    
    # 1. Fiyat (YENİ TERMİNAL GÖRÜNÜMÜ)
    if info and info.get('price'):
        display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")
        price_val = info.get('price', 0)
        change_val = info.get('change_pct', 0)

        # Rengi Belirle
        if change_val >= 0:
            bg_color = "#81bb96"  # Yeşil
            arrow = "▲"
            shadow_color = "rgba(22, 163, 74, 0.4)"
        else:
            bg_color = "#9B7C99"  # Kırmızı
            arrow = "▼"
            shadow_color = "rgba(220, 38, 38, 0.4)"

        # HTML Kodları (Sola Yaslı - Hata Vermez)
        st.markdown(f"""<div style="background-color:{bg_color}; border-radius:12px; padding:15px; color:white; text-align:center; box-shadow: 0 10px 15px -3px {shadow_color}, 0 4px 6px -2px rgba(0,0,0,0.05); margin-bottom:15px; border: 1px solid rgba(255,255,255,0.2);">
<div style="font-size:1.1rem; font-weight:600; opacity:0.9; letter-spacing:1px; margin-bottom:5px; text-transform:uppercase;">FİYAT: {display_ticker}</div>
<div style="font-family:'JetBrains Mono', monospace; font-size:2.4rem; font-weight:800; line-height:1; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">{price_val:.2f}</div>
<div style="margin-top:10px;">
<span style="background:rgba(255,255,255,0.25); color:white; font-weight:700; font-size:1.1rem; padding:4px 12px; border-radius:20px; backdrop-filter: blur(4px);">
{arrow} %{change_val:.2f}
</span>
</div>
</div>""", unsafe_allow_html=True)
    
    else:
        st.warning("Fiyat verisi alınamadı.")

    # --- YENİ EKLENEN: HIZLI TARAMA DURUM PANELİ (FULL KAPSAM) ---
    active_t = st.session_state.ticker
    scan_results_html = ""
    found_any = False
    is_star_candidate = False
    
    # 1. VERİYİ ÇEK (Tek Sefer)
    df_live = get_safe_historical_data(active_t)
    pa_data = None
    bt_live = None
    mini_live = None
    acc_live = None
    bo_live = None
    r1_live = None
    r2_live = None
    stp_live = None
    if df_live is not None and not df_live.empty:
        
        # A. ENDEKS VERİLERİ (Gerekli hesaplamalar için)
        cat_for_bench = st.session_state.category
        bench_ticker = "XU100.IS" if "BIST" in cat_for_bench else "^GSPC"
        bench_series = get_benchmark_data(cat_for_bench)
        idx_data = get_safe_historical_data(bench_ticker)['Close'] if bench_ticker else None

        # --- B. TÜM HESAPLAMALAR (Sırayla) ---
        
        # 1. STP (Smart Trend Pilot) - Kesişim, Momentum, Trend
        stp_live = process_single_stock_stp(active_t, df_live)
        
        # 2. Sentiment Ajanı (Akıllı Para)
        acc_live = process_single_accumulation(active_t, df_live, bench_series)
        
        # 3. Breakout Ajanı (Isınanlar / Kıranlar)
        bo_live = process_single_breakout(active_t, df_live)
        
        # 4. Minervini SEPA
        mini_live = calculate_minervini_sepa(active_t, benchmark_ticker=bench_ticker)
        
        # 5. Formasyonlar
        pat_df = pd.DataFrame()
        try: pat_df = scan_chart_patterns([active_t])
        except: pass
        
        # 6. Radar 1 & 2
        r1_live = process_single_radar1(active_t, df_live)
        r2_live = process_single_radar2(active_t, df_live, idx_data, 0, 100000, 0)
        
        # 7. Bear Trap Kontrolü
        bt_live = process_single_bear_trap_live(df_live)
        pa_data = calculate_price_action_dna(active_t)

        # --- C. YILDIZ ADAYI KONTROLÜ ---
        # Kural: Akıllı Para VARSA ve Breakout (Isınan veya Kıran) VARSA -> Yıldız
        if acc_live and bo_live:
            is_star_candidate = True

        # ============================================================
        # SIDEBAR İÇİN: 20 GÜNLÜK ALPHA (SWING MOMENTUM) - GARANTİLİ VERSİYON
        # ============================================================
        rs_html = ""
        try:
            # --- YENİ EKLENEN KISIM: ENDEKS KONTROLÜ ---
            # Eğer seçili varlık bir endeks ise RS hesaplama, direkt çık.
            is_index_asset = active_t.startswith("^") or "XU" in active_t or "XBANK" in active_t
            if is_index_asset:
                raise ValueError("Endeks için RS hesaplanmaz")
            # -----------------------------------------------
            # 1. HİSSE VERİSİ KONTROLÜ
            if df_live is None or len(df_live) < 5:
                raise ValueError("Hisse verisi yetersiz")

            # 2. ENDEKS VERİSİ (GARANTİLEME)
            # Öncelik 1: bench_series, Öncelik 2: idx_data, Öncelik 3: İndir
            final_bench = None
            
            if 'bench_series' in locals() and bench_series is not None and len(bench_series) > 5:
                final_bench = bench_series
            elif 'idx_data' in locals() and idx_data is not None and len(idx_data) > 5:
                final_bench = idx_data
            else:
                # Hiçbiri yoksa şimdi indir (XU100 veya S&P500)
                b_ticker = "XU100.IS" if "BIST" in st.session_state.category else "^GSPC"
                final_bench = yf.download(b_ticker, period="1mo", progress=False)['Close']

            if final_bench is None or len(final_bench) < 5:
                raise ValueError("Endeks verisi yok")

            # 3. VERİ TİPİ DÜZELTME (Series formatına zorla)
            if isinstance(final_bench, pd.DataFrame):
                # Eğer DataFrame ise ve 'Close' sütunu varsa onu al, yoksa ilk sütunu al
                if 'Close' in final_bench.columns:
                    final_bench = final_bench['Close']
                else:
                    final_bench = final_bench.iloc[:, 0]

            # 4. HESAPLAMA (Son 5 İş Günü)
            # Hissenin performansı
            stock_now = float(df_live['Close'].iloc[-1])
            stock_old = float(df_live['Close'].iloc[-6])
            stock_perf = ((stock_now - stock_old) / stock_old) * 100
            
            # Endeksin performansı
            bench_now = float(final_bench.iloc[-1])
            bench_old = float(final_bench.iloc[-6])
            bench_perf = ((bench_now - bench_old) / bench_old) * 100
            
            # 5. ALPHA (FARK)
            alpha = stock_perf - bench_perf
            
            # 6. GÖRSEL DURUM
            if alpha > 2.0: 
                rs_icon = "🔥"; rs_color = "#056829"; rs_text = f"Endeksi Eziyor (+%{alpha:.1f})"
            elif alpha > 0.0: 
                rs_icon = "💪"; rs_color = "#05772f"; rs_text = f"Endeksi Yeniyor (+%{alpha:.1f})"
            elif alpha > -2.0: 
                rs_icon = "⚠️"; rs_color = "#9e9284"; rs_text = f"Endeksle Paralel (%{alpha:.1f})"
            else: 
                rs_icon = "🐢"; rs_color = "#770505"; rs_text = f"Endeksin Gerisinde (%{alpha:.1f})" 

            rs_html = f"<div style='font-size:0.75rem; margin-bottom:2px; color:{rs_color};'>{rs_icon} <b>RS Momentum (5 GÜN):</b> {rs_text}</div>"
                
        except Exception as e:
            # Hata varsa ekrana basalım ki görelim (Canlı hata ayıklama)
            # Normalde boş bırakırdık ama sorunu çözmek için hata mesajını yazdırıyoruz
            rs_html = f"<div style='font-size:0.6rem; color:gray;'>RS Verisi Yok: {str(e)}</div>"

        # --- D. HTML OLUŞTURMA ---
        # 0. RS Gücünü En Üste Ekle (YENİ)
        if rs_html:
            scan_results_html += rs_html
            found_any = True
        # 1. STP Sonuçları
        if stp_live:
            found_any = True
            if stp_live['type'] == 'cross':
                scan_results_html += f"<div style='font-size:0.75rem; margin-bottom:2px; color:#056829;'>⚡ <b>STP:</b> Kesişim (AL Sinyali)</div>"
                # Momentum Başlangıcı Kontrolü (Filtreli mi?)
                if stp_live.get('is_filtered', False):
                    scan_results_html += f"<div style='font-size:0.75rem; margin-bottom:2px; color:#db2777;'>🎯 <b>Momentum:</b> Başlangıç Sinyali (Filtreli)</div>"
            elif stp_live['type'] == 'trend':
                gun = stp_live['data'].get('Gun', '?')
                scan_results_html += f"<div style='font-size:0.75rem; margin-bottom:2px; color:#15803d;'>✅ <b>STP:</b> Trend ({gun} Gündür)</div>"

        # 2. Akıllı Para (Sentiment)
        if acc_live:
            found_any = True
            is_pp = acc_live.get('Pocket_Pivot', False)
            icon = "⚡" if is_pp else "🤫"
            text = "Pocket Pivot (Patlama)" if is_pp else "Sessiz Toplama"
            scan_results_html += f"<div style='font-size:0.75rem; margin-bottom:2px; color:#7c3aed;'>{icon} <b>Akıllı Para:</b> {text}</div>"

        # 3. Breakout (Isınan / Kıran)
        if bo_live:
            found_any = True
            is_firing = "TETİKLENDİ" in bo_live['Zirveye Yakınlık'] or "Sıkışma Var" in bo_live['Zirveye Yakınlık']
            prox_clean = str(bo_live['Zirveye Yakınlık']).split('<')[0].strip()
            if is_firing:
                scan_results_html += f"<div style='font-size:0.75rem; margin-bottom:2px; color:#16a34a;'>🔨 <b>Breakout:</b> KIRILIM (Onaylı)</div>"
            else:
                scan_results_html += f"<div style='font-size:0.75rem; margin-bottom:2px; color:#d97706;'>🔥 <b>Breakout:</b> Isınanlar ({prox_clean})</div>"

        # 4. Minervini SEPA
        if mini_live:
            found_any = True
            # Verinin içinden Durum ve Puanı çekiyoruz
            durum = mini_live.get('Durum', 'Trend?')
            puan = mini_live.get('Raw_Score', 0)
            
            # Ekrana dinamik olarak yazdırıyoruz: "🦁 Minervini: KIRILIM EŞİĞİNDE (70)"
            scan_results_html += f"<div style='font-size:0.75rem; margin-bottom:2px; color:#ea580c;'>🦁 <b>Minervini:</b> {durum} ({puan})</div>"

        # 5. Formasyonlar
        if not pat_df.empty:
            found_any = True
            pat_name = pat_df.iloc[0]['Formasyon']
            scan_results_html += f"<div style='font-size:0.75rem; margin-bottom:2px; color:#0f172a;'>📐 <b>Formasyon:</b> {pat_name}</div>"

        # 6. Radarlar
        if r1_live and r1_live['Skor'] >= 4:
            found_any = True
            scan_results_html += f"<div style='font-size:0.75rem; margin-bottom:2px; color:#0369a1;'>🧠 <b>Radar 1:</b> Momentum ({r1_live['Skor']}/7)</div>"
        
        if r2_live and r2_live['Skor'] >= 4:
            found_any = True
            setup_name = r2_live['Setup'] if r2_live['Setup'] != "-" else "Trend Takibi"
            scan_results_html += f"<div style='font-size:0.75rem; margin-bottom:2px; color:#15803d;'>🚀 <b>Radar 2:</b> {setup_name} ({r2_live['Skor']}/7)</div>"
        
        # 7. Bear Trap (Görseli)
        if bt_live:
            found_any = True
            scan_results_html += f"<div style='font-size:0.75rem; margin-bottom:2px; color:#b45309;'>🪤 <b>Bear Trap:</b> {bt_live['Zaman']} (Vol: {bt_live['Hacim_Kat']})</div>"
            
    # --- HTML ÇIKTISI ---
    star_title = " ⭐" if is_star_candidate else ""
    display_ticker_safe = active_t.replace(".IS", "").replace("=F", "")

    # 8. RSI UYUMSUZLUKLARI (YENİ EKLENEN KISIM)
    # Detay panelindeki veriyi (pa_data) kullanalım
    if pa_data:
        div_info = pa_data.get('div', {})
        div_type = div_info.get('type', 'neutral')
        
        if div_type == 'bullish':
            found_any = True
            scan_results_html += f"<div style='font-size:0.75rem; margin-bottom:2px; color:#15803d;'>💎 <b>RSI Uyumsuzluk:</b> POZİTİF (Alış?)</div>"
        elif div_type == 'bearish':
            found_any = True
            scan_results_html += f"<div style='font-size:0.75rem; margin-bottom:2px; color:#b91c1c;'>🐻 <b>RSI Uyumsuzluk:</b> NEGATİF (Satış?)</div>"

    # 9. DİPTEN DÖNÜŞ (KUTSAL KASE) KONTROLÜ (YENİ EKLENEN KISIM)
    # Eğer hem Bear Trap hem de Pozitif Uyumsuzluk varsa
    if bt_live and pa_data and pa_data.get('div', {}).get('type') == 'bullish':
        found_any = True
        is_star_candidate = True # Yıldız da ekleyelim
        scan_results_html += f"<div style='font-size:0.75rem; margin-bottom:2px; color:#059669; font-weight:bold;'>⚓ DİPTEN DÖNÜŞ?</div>"

    # ----------------------------------------------------------------------
    # 10. İSTATİSTİKSEL Z-SCORE TARAMASI (4 AŞAMALI KADEMELİ SİSTEM)
    # ----------------------------------------------------------------------
    z_score_val = round(calculate_z_score_live(df_live), 2)
    
    # --- A. DÜŞÜŞ SENARYOLARI (UCUZLAMA) ---
    if z_score_val <= -2.0: 
        # SEVİYE 3: KRİTİK DİP (FIRSAT)
        found_any = True
        scan_results_html += f"<div style='margin-top:4px; font-size:0.8rem; color:#059669; font-weight:bold;'>🔥 İstatistiksel DİP (Z-Score: {z_score_val:.2f})</div>"
        scan_results_html += f"""
        <div style='background:#ecfdf5; border-left:3px solid #059669; padding:4px; margin-top:2px; border-radius:0 4px 4px 0;'>
            <div style='font-size:0.65rem; color:#047857; font-weight:bold;'>🎓 GÜÇLÜ ANOMALİ</div>
            <div style='font-size:0.65rem; color:#065f46; line-height:1.2;'>Fiyat -2 sapmayı kırdı. İstatistiksel olarak dönüş (tepki) ihtimali çok yüksektir.</div>
        </div>
        """
    elif z_score_val <= -1.5: 
        # SEVİYE 2: DİBE YAKLAŞIYOR (UYARI)
        found_any = True
        scan_results_html += f"<div style='margin-top:4px; font-size:0.8rem; color:#d97706;'>⚠️ Dibe Yaklaşıyor (Z-Score: {z_score_val:.2f})</div>"
        
    elif z_score_val <= -1.0: 
        # SEVİYE 1: UCUZLUYOR (BİLGİ) - [YENİ]
        found_any = True
        scan_results_html += f"<div style='margin-top:4px; font-size:0.8rem; color:#0284c7;'>📉 Ucuzluyor (Z-Score: {z_score_val:.2f})</div>"

    # --- B. YÜKSELİŞ SENARYOLARI (PAHALILANMA) ---
    elif z_score_val >= 2.0: 
        # SEVİYE 3: KRİTİK TEPE (SATIŞ RİSKİ)
        found_any = True
        scan_results_html += f"<div style='margin-top:4px; font-size:0.8rem; color:#dc2626; font-weight:bold;'>🔥 İstatistiksel TEPE (Z-Score: {z_score_val:.2f})</div>"
        scan_results_html += f"""
        <div style='background:#fef2f2; border-left:3px solid #dc2626; padding:4px; margin-top:2px; border-radius:0 4px 4px 0;'>
            <div style='font-size:0.65rem; color:#b91c1c; font-weight:bold;'>🎓 GÜÇLÜ ANOMALİ</div>
            <div style='font-size:0.65rem; color:#7f1d1d; line-height:1.2;'>Fiyat +2 sapmayı aştı. Aşırı alım bölgesinde, düzeltme riski çok yüksek.</div>
        </div>
        """
    elif z_score_val >= 1.5: 
        # SEVİYE 2: TEPEYE YAKLAŞIYOR (UYARI)
        found_any = True
        scan_results_html += f"<div style='margin-top:4px; font-size:0.8rem; color:#ea580c;'>⚠️ Tepeye Yaklaşıyor (Z-Score: {z_score_val:.2f})</div>"
        
    elif z_score_val >= 1.0: 
        # SEVİYE 1: PAHALILANIYOR (BİLGİ) - [YENİ]
        found_any = True
        scan_results_html += f"<div style='margin-top:4px; font-size:0.8rem; color:#854d0e;'>📈 Pahalılanıyor (Z-Score: {z_score_val:.2f})</div>"
    if found_any:
        st.markdown(f"""
        <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; padding:8px; margin-bottom:15px;">
            <div style="font-size:1.0rem; font-weight:700; color:#1e3a8a; border-bottom:1px solid #e2e8f0; padding-bottom:4px; margin-bottom:4px;">📋 TARAMA SONUÇLARI - {display_ticker_safe}{star_title}</div>
            {scan_results_html}
        </div>
        """, unsafe_allow_html=True)
    else:
        # Hiçbir şey yoksa boş bırak
        pass
    # 2. Price Action Paneli
    render_price_action_panel(st.session_state.ticker)

    # 🦅 YENİ: ICT SNIPER ONAY RAPORU (Sadece Setup Varsa Çıkar)
    render_ict_certification_card(st.session_state.ticker)

    # --- YENİ EKLEME: ALTIN ÜÇLÜ KONTROL PANELİ ---
    # Verileri taze çekelim ki hata olmasın
    try:
        ict_data_check = calculate_ict_deep_analysis(st.session_state.ticker)
        # DÜZELTME: Resimdeki doğru fonksiyon ismini kullandık:
        sent_data_check = calculate_sentiment_score(st.session_state.ticker) 
        # 2. Fonksiyonu çağır (Sadece 3/3 ise ekrana basacak, yoksa boş geçecek)
        render_golden_trio_banner(ict_data_check, sent_data_check)
    except Exception as e:
        pass # Bir hata olursa sessizce geç, ekranı bozma.

    # Royal Flush Paneli
    render_royal_flush_banner(ict_data_check, sent_data_check, st.session_state.ticker)
  
    # 3. Kritik Seviyeler
    render_levels_card(st.session_state.ticker)

    st.markdown("<hr style='margin-top:15px; margin-bottom:10px;'>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------------
    # 🏆 ALTIN FIRSAT & ♠️ ROYAL FLUSH (SÜPER TARAMA MOTORU)
    # -----------------------------------------------------------------------------
    def get_golden_trio_batch_scan(ticker_list):
        # Gerekli tüm kütüphaneleri burada çağırıyoruz
        import yfinance as yf
        import pandas as pd
        import time

        # --- YARDIMCI RSI HESAPLAMA FONKSİYONU ---
        def calc_rsi_manual(series, period=14):
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))

        golden_candidates = []
        royal_candidates = [] # YENİ: Royal Flush adayları

        # 1. BİLGİLENDİRME & HAZIRLIK
        st.toast("Veri Ambari İndiriliyor (1 Yıllık Derinlik)...", icon="⏳")
        progress_text = "📡 Tüm Piyasa Verisi Tek Pakette İndiriliyor (Ban Korumalı Mod)..."
        my_bar = st.progress(10, text=progress_text)

        # 2. ENDEKS VERİSİNİ AL (Hafızadan Çeker)
        index_close = fetch_index_data_cached()

        # 3. TOPLU İNDİRME (Hafızadan Çeker - BAN Korumalı)
        try:
            data = fetch_market_data_cached(tuple(ticker_list))
        except Exception as e:
            st.error(f"Veri çekme hatası: {e}")
            return pd.DataFrame(), pd.DataFrame()

        my_bar.progress(40, text="⚡ Hafızadaki Veriler İşleniyor (Çift Katmanlı Analiz)...")

        # 4. HIZLI ANALİZ DÖNGÜSÜ
        if isinstance(data.columns, pd.MultiIndex):
            valid_tickers = [t for t in ticker_list if t in data.columns.levels[0]]
        else:
            valid_tickers = ticker_list if not data.empty else []

        total_tickers = len(valid_tickers)

        for i, ticker in enumerate(valid_tickers):
            try:
                # Veriyi al
                if isinstance(data.columns, pd.MultiIndex):
                    df = data[ticker].copy()
                else:
                    df = data.copy()

                # Veri yetersizse atla (SMA200 için en az 200 bar lazım)
                if df.empty or len(df) < 200: continue

                # --- YENİ: DÜŞEN BIÇAK VE TUZAK KALKANI (5 KURAL) ---
                today_c = df['Close'].iloc[-1]
                today_o = df['Open'].iloc[-1]
                today_h = df['High'].iloc[-1]
                today_l = df['Low'].iloc[-1]
                yest_c = df['Close'].iloc[-2]
                yest_o = df['Open'].iloc[-2]
                day2_c = df['Close'].iloc[-3]

                # 1. Kırmızı Mum İptali (Bugün Kapanış < Açılış ise direkt ele)
                if today_c < today_o:
                    continue

                # 2. Son 2 Günlük Mikro RS Kalkanı (Dün kırmızı, bugün yeşilse)
                if yest_c < yest_o and today_c >= today_o:
                    if index_close is not None and len(index_close) > 3:
                        stock_2d_ret = (today_c / day2_c) - 1
                        index_2d_ret = (index_close.iloc[-1] / index_close.iloc[-3]) - 1
                        if stock_2d_ret < index_2d_ret:
                            continue # Ölü kedi sıçraması, endeksi yenemedi, ele.

                # 3. %4 Çöküş Koruması
                crash_2d = (today_c - day2_c) / day2_c
                if crash_2d < -0.04:
                    continue # 2 günde %4'ten fazla düştüyse şelaledir, ele.

                # UYARI BAYRAKLARI (Shooting Star & Doji)
                has_warning = False
                body = abs(today_c - today_o)
                rng = today_h - today_l
                upper_shadow = today_h - max(today_c, today_o)
                lower_shadow = min(today_c, today_o) - today_l

                # 4. Shooting Star (Kayan Yıldız) Uyarısı
                if upper_shadow >= 2 * body and lower_shadow <= body and body > 0:
                    has_warning = True

                # 5. Doji Uyarısı
                if rng > 0 and body <= rng * 0.1:
                    has_warning = True

                current_price = today_c
                
                # --- KRİTER 1: GÜÇ (RS) - GÜNCELLENDİ (10 GÜN) ---
                is_powerful = False
                # DİKKAT: 20 yerine 10 yaptık. TRHOL gibi yeni uyananları yakalar.
                prev_price_rs = df['Close'].iloc[-10] 

                if index_close is not None and len(index_close) > 10:
                    stock_ret = (current_price / prev_price_rs) - 1
                    index_ret = (index_close.iloc[-1] / index_close.iloc[-10]) - 1
                    if stock_ret > index_ret: is_powerful = True
                else:
                    # Endeks yoksa RSI > 55 (Biraz gevşettik)
                    rsi_val = calc_rsi_manual(df['Close']).iloc[-1]
                    if rsi_val > 55: is_powerful = True

                # --- KRİTER 2: KONUM (3 AYLIK DÜZELTME) ---
                high_60 = df['High'].rolling(60).max().iloc[-1]
                low_60 = df['Low'].rolling(60).min().iloc[-1]
                range_diff = high_60 - low_60
                
                is_discount = False
                if range_diff > 0:
                    # Fiyat 3 aylık bandın neresinde?
                    loc_ratio = (current_price - low_60) / range_diff
                    
                    # 3 aylık bandın alt %50'sindeyse kabul et
                    if loc_ratio < 0.5: 
                        is_discount = True

                # --- KRİTER 3: ENERJİ (HACİM / MOMENTUM) - GÜNCELLENDİ ---
                vol_sma20 = df['Volume'].rolling(20).mean().iloc[-1]
                current_vol = df['Volume'].iloc[-1]
                rsi_now = calc_rsi_manual(df['Close']).iloc[-1]
                
                # Hacim barajını %10'dan %5'e çektik (1.1 -> 1.05)
                is_energy = (current_vol > vol_sma20 * 1.05) or (rsi_now > 55)

                # === ANA FİLTRE: ALTIN FIRSAT ===
                if is_powerful and is_discount and is_energy:
                    
                    # Piyasa Değeri
                    try:
                        info = yf.Ticker(ticker).info
                        mcap = info.get('marketCap', 0)
                    except:
                        mcap = 0

                    # 1. ALTIN LİSTEYE EKLE
                    golden_candidates.append({
                        "Hisse": ticker,
                        "Fiyat": current_price,
                        "M.Cap": mcap,
                        "Onay": "🏆 RS Gücü + Ucuz Konum + Güçlü Enerji",
                        "Warning": has_warning
                    })

                    # === İKİNCİ FİLTRE: ROYAL FLUSH (ELİT) KONTROLÜ ===
                    # Sadece Altın olanlara bakıyoruz

                    # Royal Şart 1: Uzun Vade Trend (SMA200 Üzerinde mi?)
                    sma200 = df['Close'].rolling(200).mean().iloc[-1]
                    is_bull_trend = current_price > sma200

                    # Royal Şart 2: Maliyet/Trend (SMA50 Üzerinde mi?)
                    sma50 = df['Close'].rolling(50).mean().iloc[-1]
                    is_structure_solid = current_price > sma50

                    # Royal Şart 3: RSI Güvenli Bölge (Aşırı şişmemiş)
                    is_safe_entry = rsi_now < 70

                    if is_bull_trend and is_structure_solid and is_safe_entry:
                        # 2. ROYAL LİSTEYE DE EKLE
                        royal_candidates.append({
                            "Hisse": ticker,
                            "Fiyat": current_price,
                            "M.Cap": mcap,
                            "Onay": "♠️ 4/4 KRALİYET: Trend(200) + Yapı(50) + RS + Enerji",
                            "Warning": has_warning
                        })

            except:
                continue

            if i % 10 == 0 and total_tickers > 0:
                prog = int((i / total_tickers) * 100)
                my_bar.progress(40 + int(prog/2), text=f"⚡ Analiz: {ticker}...")

        my_bar.progress(100, text="✅ Tarama Tamamlandı! Listeleniyor...")
        time.sleep(0.3)
        my_bar.empty()

        return pd.DataFrame(golden_candidates), pd.DataFrame(royal_candidates)

    # --- ARAYÜZ KODU (State Mantığı ile Düzeltilmiş) ---

    # 1. State Tanımlaması
    if 'golden_results' not in st.session_state: 
        st.session_state.golden_results = None
    if 'royal_results' not in st.session_state: # YENİ
        st.session_state.royal_results = None

    st.markdown("---")

    # 2. MERKEZİ TARAMA TETİKLEYİCİSİ (TEK TUŞ - TÜM RADARLAR)
    if st.button("🏆 TARA (LORENTZIAN + ALTIN FIRSATLAR)", type="primary", use_container_width=True):

        scan_list = ASSET_GROUPS.get(st.session_state.category, [])

        if not scan_list:
            st.error("⚠️ Lütfen önce sol menüden bir hisse grubu seçin.")
        else:
            with st.spinner("Tüm Piyasa Verisi Çekiliyor ve Algoritmalar Çalışıyor (Lütfen Bekleyin)..."):

                # 1. Radar 2 (Lorentzian) Taraması
                df_radar2 = radar2_scan(scan_list)
                st.session_state.radar2_data = df_radar2

                # 2. Altın Fırsat & Royal Flush Taraması
                df_golden, df_royal = get_golden_trio_batch_scan(scan_list)

                # State'lere kaydet
                if not df_golden.empty:
                    st.session_state.golden_results = df_golden.sort_values(by="M.Cap", ascending=False).reset_index(drop=True)
                else:
                    st.session_state.golden_results = pd.DataFrame()

                if not df_royal.empty:
                    st.session_state.royal_results = df_royal.sort_values(by="M.Cap", ascending=False).reset_index(drop=True)
                else:
                    st.session_state.royal_results = pd.DataFrame()

            if st.session_state.golden_results.empty and st.session_state.royal_results.empty and (df_radar2 is None or df_radar2.empty):
                st.warning("⚠️ Kriterlere uyan hisse bulunamadı.")
            else:
                st.rerun() # Sayfayı yenile ki tüm paneller aynı anda dolsun

    # 3. SONUÇ GÖSTERİCİ EKRAN (TÜM RADARLAR ALT ALTA)
    
    # --- BÖLÜM A: ♠️ ROYAL FLUSH (EN ÜSTTE ÇÜNKÜ EN ELİT) ---
    if st.session_state.royal_results is not None and not st.session_state.royal_results.empty:
        st.markdown("---")
        st.markdown(f"<div style='background:linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); border:1px solid #1e40af; border-radius:6px; padding:8px; margin-bottom:10px; font-size:1rem; font-weight:bold; color:white; text-align:center;'>♠️ ROYAL FLUSH (ELİTLER) ({len(st.session_state.royal_results)})</div>", unsafe_allow_html=True)
        st.caption("Kriterler: SMA200 üzerinde + SMA50 üzerinde + Şişmemiş RSI<70")

        cols_royal = st.columns(3)
        for index, row in st.session_state.royal_results.head(6).iterrows():
            raw_symbol = row['Hisse']
            display_symbol = raw_symbol.replace(".IS", "")
            fiyat_val = row['Fiyat']
            has_warn = row.get('Warning', False)
            fiyat_str = f"🟠 {fiyat_val:.2f}" if has_warn else f"{fiyat_val:.2f}"

            if cols_royal[index % 3].button(f"♠️ {display_symbol}\n{fiyat_str}", type="primary", key=f"btn_royal_{index}", use_container_width=True):
                st.session_state.ticker = raw_symbol
                st.session_state.run_analysis = True
                st.session_state.scan_data = None
                st.rerun()

    # --- BÖLÜM B: 🦁 ALTIN FIRSATLAR LİSTESİ ---
    if st.session_state.golden_results is not None and not st.session_state.golden_results.empty:
        st.markdown("---")
        st.markdown(f"<div style='background:#fffbeb; border:1px solid #fcd34d; border-radius:6px; padding:5px; margin-bottom:10px; font-size:0.9rem; color:#92400e; text-align:center;'>🦁 ALTIN FIRSATLAR ({len(st.session_state.golden_results)})</div>", unsafe_allow_html=True)
        st.caption("Kriterler: Son 10 gün Endeksten Güçlü + Son 60 güne göre Ucuz + Hacim/Enerji artıyor")

        cols_gold = st.columns(3)
        for index, row in st.session_state.golden_results.head(12).iterrows():
            raw_symbol = row['Hisse']
            display_symbol = raw_symbol.replace(".IS", "")
            fiyat_val = row['Fiyat']
            has_warn = row.get('Warning', False)
            fiyat_str = f"🟠 {fiyat_val:.2f}" if has_warn else f"{fiyat_val:.2f}"

            if cols_gold[index % 3].button(f"🦁 {display_symbol}\n{fiyat_str}", key=f"btn_gold_{index}", use_container_width=True):
                st.session_state.ticker = raw_symbol
                st.session_state.run_analysis = True
                st.session_state.scan_data = None
                st.rerun()

    # --- BÖLÜM C: 🚀 RADAR 2 (LORENTZIAN / YÜKSELİŞ ADAYLARI) ---
    if st.session_state.radar2_data is not None and not st.session_state.radar2_data.empty:
        st.markdown("---")
        st.markdown(f"<div style='background:#f0fdf4; border:1px solid #86efac; border-radius:6px; padding:5px; margin-bottom:10px; font-size:0.9rem; color:#166534; text-align:center;'>🚀 YÜKSELİŞ ADAYLARI (LORENTZIAN) ({len(st.session_state.radar2_data)})</div>", unsafe_allow_html=True)
        st.caption("Kriterler: Makine Öğrenimi KNN Algoritması ile Alım Sinyalleri")

        # 👇 İŞTE BURASI KAYAR KUTUYU (SCROLL) OLUŞTURAN YER
        with st.container(height=180, border=True):
            cols_radar2 = st.columns(3)
            for index, row in st.session_state.radar2_data.iterrows():
                sym = row["Sembol"]
                display_sym = sym.replace(".IS", "")
                setup = row['Setup'] if row['Setup'] != "-" else "Trend"
                
                if cols_radar2[index % 3].button(f"🚀 {int(row['Skor'])}/7 | {display_sym}", key=f"r2_res_new_{index}", use_container_width=True, help=f"Setup: {setup}"):
                    st.session_state.ticker = sym
                    st.session_state.run_analysis = True
                    st.session_state.scan_data = None
                    st.rerun()
    
    elif st.session_state.golden_results is not None and st.session_state.golden_results.empty:
        # Eğer tarama yapılmış ama sonuç yoksa (Daha önce uyarı vermiştik ama burada da temiz dursun)
        pass

    # ---------------------------------------------------------
    # 🏆 GRANDMASTER TOP 10 (TEKNİK & NET)
    # ---------------------------------------------------------
    st.markdown('<div class="info-header" style="margin-top: 20px; margin-bottom: 5px;">🏆 1-5 GÜNLÜK YÜKSELİŞ ADAYLARI</div>', unsafe_allow_html=True)
    
    if 'gm_results' not in st.session_state: st.session_state.gm_results = None

    if st.button("🏆 PATLAMA ADAYLARINI LİSTELE", type="primary", use_container_width=True, key="btn_gm_scan"):
        with st.spinner("Grandmaster Algoritması çalışıyor... (Lorentzian + ICT + Momentum)"):
            current_assets = ASSET_GROUPS.get(st.session_state.category, [])
            st.session_state.gm_results = scan_grandmaster_batch(current_assets)
            
    if st.session_state.gm_results is not None and not st.session_state.gm_results.empty:
        
        with st.container(height=450, border=True):
            for i, row in st.session_state.gm_results.iterrows():
                # Renk Skalası
                sc = row['Skor']
                if sc >= 80: s_col = "#15803d" 
                elif sc >= 60: s_col = "#055d8a" 
                else: s_col = "#d97706" 
                
                # Etiket Hazırlığı 
                story = row.get('Hikaye', '-')
                label = f"{i+1}. {row['Sembol']} | SKOR: {sc}"
                
                # Teknik Detay (Alt Gri Yazı)
                # Alpha -7.9 gibi ise de burada görünür, karar senindir.
                alpha_val = row.get('Alpha', 0) 
                detail_txt = f"Vol: {row['Hacim_Kat']}x | Z-Score: {row['Z_Score']} | Alpha: %{alpha_val}"

                # Buton
                if st.button(label, key=f"gm_res_{i}", use_container_width=True, help=f"Uyarılar: {row['Uyarılar']}"):
                    on_scan_result_click(row['Sembol'])
                    st.rerun()
                
                # Hikaye (Teknik Terimler - Mavi)
                st.markdown(f"<div style='font-size:0.75rem; color:#1e40af; margin-top:-10px; margin-bottom:2px; padding-left:10px; font-weight:700;'>{story}</div>", unsafe_allow_html=True)
                # Gri Detay
                st.markdown(f"<div style='font-size:0.75rem; color:#045c8b; margin-bottom:10px; padding-left:10px;'>{detail_txt}</div>", unsafe_allow_html=True)

    elif st.session_state.gm_results is not None:
        st.warning("Kriterlere uyan (Skor > 40) hisse bulunamadı.")

    # --- TEK TUŞLA DEV TARAMA BUTONU ---
    if st.button(f"🚀 {st.session_state.category} KAPSAMLI TARA (R1 + R2)", type="primary", use_container_width=True, key="master_scan_btn"):
        with st.spinner("Piyasa Röntgeni Çekiliyor... Hem Momentum (R1) Hem Trend (R2) taranıyor..."):
            current_assets = ASSET_GROUPS.get(st.session_state.category, [])
            
            # Paralel olarak iki taramayı da yapıp hafızaya atıyoruz
            st.session_state.scan_data = analyze_market_intelligence(current_assets)
            st.session_state.radar2_data = radar2_scan(current_assets)
            
            st.rerun() # Sayfayı yenile ki aşağıdaki listeler dolsun    
    # 5. Ortak Fırsatlar Başlığı
    st.markdown(f"<div style='font-size:0.9rem;font-weight:600;margin-bottom:4px; margin-top:10px; color:#1e40af; background-color:{current_theme['box_bg']}; padding:5px; border-radius:5px; border:1px solid #1e40af;'>🎯 Ortak Fırsatlar (Kesişim)</div>", unsafe_allow_html=True)
    
    # 6. Ortak Fırsatlar Listesi (Otomatik Dolacak)
    with st.container(height=200):
        df1 = st.session_state.scan_data; df2 = st.session_state.radar2_data
        
        # Eğer iki veri de varsa hesapla
        if df1 is not None and df2 is not None and not df1.empty and not df2.empty:
            commons = []; symbols = set(df1["Sembol"]).intersection(set(df2["Sembol"]))
            if symbols:
                for sym in symbols:
                    row1 = df1[df1["Sembol"] == sym].iloc[0]; row2 = df2[df2["Sembol"] == sym].iloc[0]
                    r1_score = float(row1["Skor"]); r2_score = float(row2["Skor"]); combined_score = r1_score + r2_score
                    if combined_score >= 11: commons.append({"symbol": sym, "r1_score": r1_score, "r2_score": r2_score, "combined": combined_score})
                
                # Puanı yüksek olan en üste
                sorted_commons = sorted(commons, key=lambda x: x["combined"], reverse=True)
                
                cols = st.columns(2) 
                for i, item in enumerate(sorted_commons):
                    sym = item["symbol"]
                    # Buton Metni: 1. THYAO (13)
                    score_text = f"{i+1}. {sym} ({int(item['combined'])})"
                    with cols[i % 2]:
                        if st.button(f"{score_text}", key=f"common_{sym}", help=f"R1: {int(item['r1_score'])} | R2: {int(item['r2_score'])}", use_container_width=True): 
                            on_scan_result_click(sym); st.rerun()
            else: 
                st.info("Kesişim yok (İki listede de olan hisse yok).")
        else: 
            st.caption("Yukarıdaki butona basarak taramayı başlatın.")
    
    # 7. TABLAR (Artık içlerinde buton yok, sadece sonuç var)
    tab1, tab2 = st.tabs(["🧠 RADAR 1", "🚀 RADAR 2"])
    
    with tab1:
        if st.session_state.scan_data is not None and not st.session_state.scan_data.empty:
            with st.container(height=300):
                cols = st.columns(2)
                for i, (index, row) in enumerate(st.session_state.scan_data.iterrows()):
                    sym = row["Sembol"]
                    with cols[i % 2]:
                        if st.button(f"🔥 {int(row['Skor'])}/7 | {sym}", key=f"r1_res_{i}", use_container_width=True): 
                            on_scan_result_click(sym); st.rerun()
        else:
            st.info("Sonuçlar bekleniyor...")

    with tab2:
        if st.session_state.radar2_data is not None and not st.session_state.radar2_data.empty:
            with st.container(height=300):
                cols = st.columns(2)
                for i, (index, row) in enumerate(st.session_state.radar2_data.iterrows()):
                    sym = row["Sembol"]
                    with cols[i % 2]:
                        setup = row['Setup'] if row['Setup'] != "-" else "Trend"
                        if st.button(f"🚀 {int(row['Skor'])}/7 | {sym}", key=f"r2_res_{i}", use_container_width=True, help=f"Setup: {setup}"): 
                            on_scan_result_click(sym); st.rerun()
        else:
            st.info("Sonuçlar bekleniyor...")
