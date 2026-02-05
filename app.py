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
        font-size: 0.75rem;
        color: #64748B;
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
priority_sp = ["^GSPC", "^DJI", "^NDX", "^IXIC","QQQI", "AGNC", "ARCC", "TSPY", "JEPI", "MO", "JEPQ"]

# S&P 500'ün Tamamı (503 Hisse - Güncel)
raw_sp500_rest = [
    "A", "AAL", "AAPL", "ABBV", "ABNB", "ABT", "ACGL", "ACN", "ADBE", "ADI", "ADM", "ADP", "ADSK", "AEE", "AEP", "AES", "AFL", "AIG", "AIZ", "AJG", 
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
    "ILMN", "INCY", "INTC", "INTU", "INVH", "IP", "IPG", "IQV", "IR", "IRM", "ISRG", "IT", "ITW", "IVZ", "J", "JBHT", "JBL", "JCI", "JKHY", "JNJ", 
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
    "QRVO", "AVTR", "FTNT", "ENPH", "SEDG", "BIIB", "CSGP"
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
    "JANTS.IS",
    "KAPLM.IS", "KAREL.IS", "KARSN.IS", "KARYE.IS", "KATMR.IS", "KAYSE.IS", "KCAER.IS", "KCHOL.IS", "KENT.IS", "KERVN.IS", "KERVT.IS", "KFEIN.IS", "KGYO.IS", "KIMMR.IS", "KLGYO.IS", "KLKIM.IS", "KLMSN.IS", "KLNMA.IS", "KLSER.IS", "KLRHO.IS", "KMPUR.IS", "KNFRT.IS", "KOCMT.IS", "KONKA.IS", "KONTR.IS", "KONYA.IS", "KOPOL.IS", "KORDS.IS", "KOTON.IS", "KOZAA.IS", "KOZAL.IS", "KRDMA.IS", "KRDMB.IS", "KRDMD.IS", "KRGYO.IS", "KRONT.IS", "KRPLS.IS", "KRSTL.IS", "KRTEK.IS", "KRVGD.IS", "KSTUR.IS", "KTLEV.IS", "KTSKR.IS", "KUTPO.IS", "KUVVA.IS", "KUYAS.IS", "KZBGY.IS", "KZGYO.IS",
    "LIDER.IS", "LIDFA.IS", "LILAK.IS", "LINK.IS", "LKMNH.IS", "LMKDC.IS", "LOGO.IS", "LUKSK.IS",
    "MAALT.IS", "MACKO.IS", "MAGEN.IS", "MAKIM.IS", "MAKTK.IS", "MANAS.IS", "MARBL.IS", "MARKA.IS", "MARTI.IS", "MAVI.IS", "MEDTR.IS", "MEGAP.IS", "MEGMT.IS", "MEKAG.IS", "MEPET.IS", "MERCN.IS", "MERIT.IS", "MERKO.IS", "METEM.IS", "METRO.IS", "METUR.IS", "MGROS.IS", "MIATK.IS", "MIPAZ.IS", "MMCAS.IS", "MNDRS.IS", "MNDTR.IS", "MOBTL.IS", "MOGAN.IS", "MPARK.IS", "MRGYO.IS", "MRSHL.IS", "MSGYO.IS", "MTRKS.IS", "MTRYO.IS", "MZHLD.IS",
    "NATEN.IS", "NETAS.IS", "NIBAS.IS", "NTGAZ.IS", "NUGYO.IS", "NUHCM.IS",
    "OBASE.IS", "OBAMS.IS", "ODAS.IS", "ODINE.IS", "OFSYM.IS", "ONCSM.IS", "ORCA.IS", "ORGE.IS", "ORMA.IS", "OSMEN.IS", "OSTIM.IS", "OTKAR.IS", "OTTO.IS", "OYAKC.IS", "OYAYO.IS", "OYLUM.IS", "OYYAT.IS", "OZGYO.IS", "OZKGY.IS", "OZRDN.IS", "OZSUB.IS",
    "PAGYO.IS", "PAMEL.IS", "PAPIL.IS", "PARSN.IS", "PASEU.IS", "PCILT.IS", "PEGYO.IS", "PEKGY.IS", "PENGD.IS", "PENTA.IS", "PETKM.IS", "PETUN.IS", "PGSUS.IS", "PINSU.IS", "PKART.IS", "PKENT.IS", "PLAT.IS", "PNLSN.IS", "POLHO.IS", "POLTK.IS", "PRDGS.IS", "PRKAB.IS", "PRKME.IS", "PRZMA.IS", "PSDTC.IS", "PSGYO.IS", "PTEK.IS",
    "QNBFB.IS", "QNBFL.IS", "QUAGR.IS",
    "RALYH.IS", "RAYSG.IS", "REEDR.IS", "RGYAS.IS", "RNPOL.IS", "RODRG.IS", "ROYAL.IS", "RTALB.IS", "RUBNS.IS", "RYGYO.IS", "RYSAS.IS",
    "SAFKR.IS", "SAHOL.IS", "SAMAT.IS", "SANEL.IS", "SANFM.IS", "SANKO.IS", "SARKY.IS", "SASA.IS", "SAYAS.IS", "SDTTR.IS", "SEGYO.IS", "SEKFK.IS", "SEKUR.IS", "SELEC.IS", "SELGD.IS", "SELVA.IS", "SEYKM.IS", "SILVR.IS", "SISE.IS", "SKBNK.IS", "SKTAS.IS", "SKYMD.IS", "SMART.IS", "SMRTG.IS", "SNGYO.IS", "SNICA.IS", "SNKRN.IS", "SNPAM.IS", "SODSN.IS", "SOKE.IS", "SOKM.IS", "SONME.IS", "SRVGY.IS", "SUMAS.IS", "SUNTK.IS", "SURGY.IS", "SUWEN.IS", "SYS.IS",
    "TABGD.IS", "TARAF.IS", "TATGD.IS", "TAVHL.IS", "TBORG.IS", "TCELL.IS", "TDGYO.IS", "TEKTU.IS", "TERA.IS", "TETMT.IS", "TEZOL.IS", "TGSAS.IS", "THYAO.IS", "TKFEN.IS", "TKNSA.IS", "TLMAN.IS", "TMPOL.IS", "TMSN.IS", "TNZTP.IS", "TOASO.IS", "TRCAS.IS", "TRGYO.IS", "TRILC.IS", "TSGYO.IS", "TSKB.IS", "TSPOR.IS", "TTKOM.IS", "TTRAK.IS", "TUCLK.IS", "TUKAS.IS", "TUPRS.IS", "TUREX.IS", "TURGG.IS", "TURSG.IS",
    "UFUK.IS", "ULAS.IS", "ULKER.IS", "ULUFA.IS", "ULUSE.IS", "ULUUN.IS", "UMPAS.IS", "UNLU.IS", "USAK.IS", "UZERB.IS",
    "VAKBN.IS", "VAKFN.IS", "VAKKO.IS", "VANGD.IS", "VBTYZ.IS", "VERUS.IS", "VESBE.IS", "VESTL.IS", "VKFYO.IS", "VKGYO.IS", "VKING.IS", "VRGYO.IS",
    "YAPRK.IS", "YATAS.IS", "YAYLA.IS", "YBTAS.IS", "YEOTK.IS", "YESIL.IS", "YGGYO.IS", "YGYO.IS", "YKBNK.IS", "YKSLN.IS", "YONGA.IS", "YUNSA.IS", "YYAPI.IS", "YYLGD.IS",
    "ZEDUR.IS", "ZOREN.IS", "ZRGYO.IS", "GIPTA.IS", "TEHOL.IS", "PAHOL.IS", "MARMR.IS", "BIGEN.IS", "GLRMK.IS"
]

# Kopyaları Temizle ve Birleştir
raw_bist_stocks = list(set(raw_bist_stocks) - set(priority_bist_indices))
raw_bist_stocks.sort()
final_bist100_list = priority_bist_indices + raw_bist_stocks

ASSET_GROUPS = {
    "BIST 500 ": final_bist100_list,
    "S&P 500": final_sp500_list,
    "NASDAQ-100": raw_nasdaq,
    "KRİPTO-TOP 100": final_crypto_list,
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
    Tüm listenin verisini tek seferde çeker ve önbellekte tutar.
    Tarama fonksiyonları internete değil, buraya başvurur.
    """
    if not asset_list:
        return pd.DataFrame()
    
    try:
        # Tickers listesini string'e çevir
        tickers_str = " ".join(asset_list)
        
        # Tek seferde devasa indirme (Batch Download)
        data = yf.download(
            tickers_str, 
            period=period, 
            group_by='ticker', 
            threads=True, 
            progress=False,
            auto_adjust=False 
        )
        return data
    except Exception:
        return pd.DataFrame()

# --- SINGLE STOCK CACHE (DETAY SAYFASI İÇİN) ---
@st.cache_data(ttl=300)
def get_safe_historical_data(ticker, period="1y", interval="1d"):
    try:
        clean_ticker = ticker.replace(".IS", "")
        if "BIST" in ticker or ".IS" in ticker:
            clean_ticker = ticker if ticker.endswith(".IS") else f"{ticker}.IS"
        
        df = yf.download(clean_ticker, period=period, interval=interval, progress=False)
        
        if df.empty: return None
            
        if isinstance(df.columns, pd.MultiIndex):
            try:
                if clean_ticker in df.columns.levels[1]: df = df.xs(clean_ticker, axis=1, level=1)
                else: df.columns = df.columns.get_level_values(0)
            except: df.columns = df.columns.get_level_values(0)
                
        df.columns = [c.capitalize() for c in df.columns]
        required = ['Close', 'High', 'Low', 'Open']
        if not all(col in df.columns for col in required): return None

        if 'Volume' not in df.columns: df['Volume'] = 1
        df['Volume'] = df['Volume'].replace(0, 1)
        return df

    except Exception: return None

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
            return ("✅ Hacim Destekli Trend", "#15803d", "OBV, 20 günlük ortalamasının üzerinde (Sağlıklı).")
            
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
                "type": "cross",
                "data": {"Sembol": symbol, "Fiyat": c_last, "STP": s_last, "Fark": ((c_last/s_last)-1)*100, "Hacim": volume}
            }
            sma_val = float(sma200.iloc[-1])
            rsi_val = float(rsi.iloc[-1])
            if (c_last > sma_val) and (20 < rsi_val < 70):
                result["is_filtered"] = True
            else:
                result["is_filtered"] = False

        elif c_prev > s_prev and c_last > s_last:
            above = close > stp
            streak = (above != above.shift()).cumsum()
            streak_count = above.groupby(streak).sum().iloc[-1]
            
            result = {
                "type": "trend",
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
            
            # --- ACIMASIZ ANA TREND FİLTRESİ ---
            # Fiyat 200 günlük ortalamanın altındaysa HİÇ BAKMA.
            sma200 = close.rolling(200).mean().iloc[-1]
            if curr_price < sma200: continue 

            pattern_found = False; pattern_name = ""; desc = ""; base_score = 0
            
            # --- 1. BOĞA BAYRAĞI (BULL FLAG) ---
            # Direk en az %15, Bayrak en fazla %6 genişlikte
            p20 = float(close.iloc[-20]); p5 = float(close.iloc[-5])
            pole = (p5 - p20) / p20
            flag_h = high.iloc[-5:].max(); flag_l = low.iloc[-5:].min()
            tight = (flag_h - flag_l) / flag_l
            
            if pole > 0.15 and tight < 0.06 and curr_price > flag_h * 0.99:
                pattern_found = True; pattern_name = "🚩 BOĞA BAYRAĞI"; base_score = 85
                desc = f"Direk: %{pole*100:.1f} | Sıkışma: %{tight*100:.1f}"

            # --- 2. FİNCAN KULP (CUP & HANDLE) - APTV DÜZELTMESİ ---
            if not pattern_found:
                # Daha geniş bak: Sol Tepe (4-6 ay önce), Sağ Tepe (Son 1 ay)
                rim_l = high.iloc[-150:-40].max() 
                cup_b = low.iloc[-60:-20].min()
                rim_r = high.iloc[-25:-5].max() 
                
                # Kulp Dibi
                handle_low = low.iloc[-10:].min()
                
                # 1. Simetri: Sol ve Sağ tepe birbirine çok yakın olmalı (%5)
                # APTV burada %10 farkla elenecek veya "Henüz kulp yapmadı" diyecek.
                aligned = abs(rim_l - rim_r) / rim_l < 0.05
                
                # 2. Derinlik: Çanak belirgin olmalı
                deep = cup_b < rim_l * 0.85
                
                # 3. KULP ŞARTI: Fiyat, Sağ Tepeden sonra biraz düşmüş (Kulp yapmış) ama çok da çökmemiş olmalı.
                # APTV şu an sağ tepede olduğu için "pullback" yapmadı, elenecek.
                handle_exists = (handle_low < rim_r * 0.97) and (handle_low > cup_b + (rim_r - cup_b)*0.5)
                
                # 4. KIRILIM ŞARTI: Fiyat şu an TAM DİRENÇTE veya GEÇMİŞ olmalı.
                # 0.96 yerine 0.99 yaptık. Yani tam sınıra dayanmalı.
                breaking = curr_price >= rim_r * 0.99
                
                if aligned and deep and handle_exists and breaking:
                    pattern_found = True; pattern_name = "☕ FİNCAN KULP"; base_score = 95
                    desc = "Kulp tamamlandı, boyun çizgisi kırılıyor."

            # --- 3. TOBO (Inverse Head & Shoulders) - GÜNCELLENDİ ---
            if not pattern_found:
                # Periyotlar
                ml = low.iloc[-60:-40].min()
                mh = low.iloc[-40:-15].min()
                mr = low.iloc[-15:].min()
                
                # Boyun Çizgisi (Direnç)
                neck = high.iloc[-60:-10].max()
                
                # KURALLAR:
                # 1. Baş en altta mı?
                head_deep = mh < ml * 0.98 and mh < mr * 0.98
                
                # 2. Simetri: Omuzlar arası fark %8'i geçmesin
                sym = abs(ml - mr) / ml < 0.08
                
                # 3. YENİ FİLTRE: "CHASE FILTER" (Peşinden Koşma)
                # Fiyat boyun çizgisini kırmış olmalı AMA %3'ten fazla uzaklaşmamış olmalı.
                # SCHW $97 boynunu kırmış ama $101 olmuş (%4+). Bu filtre onu eler.
                is_breakout_fresh = (curr_price >= neck * 0.98) and (curr_price <= neck * 1.03)
                
                if head_deep and sym and is_breakout_fresh:
                    pattern_found = True; pattern_name = "🧛 TOBO"; base_score = 90
                    desc = "Dönüş Formasyonu. Kırılım taze."

            # --- 4. YÜKSELEN ÜÇGEN ---
            if not pattern_found:
                h_peaks = high.iloc[-45:].nlargest(3).values
                if len(h_peaks) > 0:
                    avg_res = h_peaks.mean()
                    flat = all(abs(p - avg_res)/avg_res < 0.02 for p in h_peaks)
                    
                    l3=low.iloc[-15:].min(); l2=low.iloc[-30:-15].min(); l1=low.iloc[-45:-30].min()
                    rising = l3 > l2 and l2 > l1
                    
                    if flat and rising and curr_price >= avg_res * 0.99:
                        pattern_found = True; pattern_name = "📐 YÜKSELEN ÜÇGEN"; base_score = 88
                        desc = "Direnç zorlanıyor"

            # --- KALİTE PUANLAMASI ---
            if pattern_found:
                q_score = base_score
                
                # Hacim Desteği (+15 Puan)
                avg_vol = volume.iloc[-20:].mean()
                if volume.iloc[-1] > avg_vol * 1.5: q_score += 15
                
                # Son 2 Gün Kırmızıysa AĞIR CEZA (-30 Puan)
                # Senin istediğin özellik: Düşen formasyonları en alta atar.
                if close.iloc[-1] < open_.iloc[-1] and close.iloc[-2] < open_.iloc[-2]:
                    q_score -= 30
                    desc += " (⚠️ Düşüşte)"
                
                results.append({
                    "Sembol": symbol,
                    "Fiyat": curr_price,
                    "Formasyon": pattern_name,
                    "Detay": desc,
                    "Skor": q_score,
                    "Hacim": float(volume.iloc[-1])
                })

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

@st.cache_data(ttl=3600)
def radar2_scan(asset_list, min_price=5, max_price=5000, min_avg_vol_m=0.5):
    data = get_batch_data_cached(asset_list, period="1y")
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
        
        # Varsayılan: Gün bitti (%100)
        progress = 1.0 

        if is_live:
            now = datetime.now() + timedelta(hours=3) # TR Saati
            current_hour = now.hour
            current_minute = now.minute
            
            # BIST Seans Mantığı (10:00 - 18:00)
            if current_hour < 10: progress = 0.1
            elif current_hour >= 18: progress = 1.0
            else:
                progress = ((current_hour - 10) * 60 + current_minute) / 480.0
                progress = max(0.1, min(progress, 1.0))

        # Mevcut Hacim
        curr_vol_raw = float(volume.iloc[-1])
        # Yansıtılmış (Projected) Hacim: "Bu hızla giderse gün sonu ne olur?"
        curr_vol_projected = curr_vol_raw / progress
        
        # Hacim Ortalaması (Bugün hariç son 20 gün)
        vol_20 = volume.iloc[:-1].tail(20).mean()
        if pd.isna(vol_20) or vol_20 == 0: vol_20 = 1

        # Relative Volume (RVOL) - Projeksiyon kullanılarak hesaplanır
        rvol = curr_vol_projected / vol_20
        
        # --- TEKNİK HESAPLAMALAR ---
        # Ortalamalar
        ema5 = close.ewm(span=5, adjust=False).mean()
        ema20 = close.ewm(span=20, adjust=False).mean()
        sma20 = close.rolling(20).mean(); sma50 = close.rolling(50).mean()
        
        # Zirve Hesabı (Bugün hariç son 45 gün - Taze Zirve)
        high_val = high.iloc[:-1].tail(45).max()
        curr_price = close.iloc[-1]
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]
        
        # --- ŞARTLAR (HAVUZ DARALTMAMAK İÇİN MEVCUT KRİTERLER KORUNDU) ---
        cond_ema = ema5.iloc[-1] > ema20.iloc[-1]
        
        # DÜZELTME: Artık "Projected" hacme bakıyoruz, sabah da çalışır.
        cond_vol = rvol > 1.2 
        
        cond_prox = curr_price > (high_val * 0.90) # %10 Yakınlık
        cond_rsi = rsi < 70
        sma_ok = sma20.iloc[-1] > sma50.iloc[-1]
        
        if cond_ema and cond_vol and cond_prox and cond_rsi:
            
            # --- 2. LAZYBEAR PATLAMA KONTROLÜ (YENİ) ---
            sq_now, sq_prev = check_lazybear_squeeze_breakout(df)
            
            # Patlama Tanımı: Dün Sıkışık (True) VE Bugün Değil (False)
            is_firing = sq_prev and not sq_now
            
            # --- 3. SIRALAMA VE ÇIKTI ---
            
            # Sıralama: Tetiklenenler en üste, diğerleri hacim hızına göre
            # +1000 puan vererek listenin en tepesine çiviliyoruz.
            sort_score = rvol + (1000 if is_firing else 0)

            # Görsel Metin
            prox_pct = (curr_price / high_val) * 100
            
            if is_firing:
                prox_str = f"🚀 TETİKLENDİ (Triggered)"
            elif sq_now:
                prox_str = f"💣 Sıkışma Var (Squeeze)"
            else:
                prox_str = f"%{prox_pct:.1f}" + (" (Sınırda)" if prox_pct >= 98 else " (Hazırlık)")
            
            # Fitil Uyarısı (Satış baskısı var mı?)
            body_size = abs(close.iloc[-1] - open_.iloc[-1])
            upper_wick = high.iloc[-1] - max(open_.iloc[-1], close.iloc[-1])
            is_wick_rejected = (upper_wick > body_size * 1.5) and (upper_wick > 0)
            wick_warning = " ⚠️ Satış Baskısı" if is_wick_rejected else ""
            
            # Hacim Metni (Eğer gerçek hacim düşükse ama hız yüksekse belirtelim)
            if (curr_vol_raw < vol_20) and (rvol > 1.2):
                rvol_text = "Hız Yüksek (Proj.) 📈"
            else:
                rvol_text = "Olağanüstü 🐳" if rvol > 2.0 else "İlgi Artıyor 📈"

            display_symbol = symbol
            trend_display = f"✅EMA | {'✅SMA' if sma_ok else '❌SMA'}"
            
            return { 
                "Sembol_Raw": symbol, 
                "Sembol_Display": display_symbol, 
                "Fiyat": f"{curr_price:.2f}", 
                "Zirveye Yakınlık": prox_str + wick_warning, 
                "Hacim Durumu": rvol_text, 
                "Trend Durumu": trend_display, 
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

        close = df['Close']; high = df['High']; volume = df['Volume'] if 'Volume' in df.columns else pd.Series([1]*len(df))
        
        # --- 1. ADIM: ZİRVE KONTROLÜ (Son 20 İş Günü) ---
        # Bugünü (son satırı) hesaba katmadan, düne kadarki 20 günün zirvesi
        high_val = high.iloc[:-1].tail(20).max()
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

@st.cache_data(ttl=3600)
def calculate_master_score(ticker):
    """
    FİNAL MASTER SKOR (Gelişmiş Raporlu):
    Puanı hesaplarken nedenlerini (Artı/Eksi) kaydeder.
    """
    # 1. VERİLERİ TOPLA
    mini_data = calculate_minervini_sepa(ticker)
    fund_data = get_fundamental_score(ticker)
    sent_data = calculate_sentiment_score(ticker)
    ict_data = calculate_ict_deep_analysis(ticker)
    tech = get_tech_card_data(ticker)
    
    # Radar Puanlarını Al
    r1_score = 0; r2_score = 0
    scan_df = st.session_state.get('scan_data')
    if scan_df is not None and not scan_df.empty and 'Sembol' in scan_df.columns:
        row = scan_df[scan_df['Sembol'] == ticker]
        if not row.empty: r1_score = float(row.iloc[0]['Skor'])
    
    radar2_df = st.session_state.get('radar2_data')
    if radar2_df is not None and not radar2_df.empty and 'Sembol' in radar2_df.columns:
        row = radar2_df[radar2_df['Sembol'] == ticker]
        if not row.empty: r2_score = float(row.iloc[0]['Skor'])

    # RAPOR LİSTELERİ
    pros = [] # Artılar
    cons = [] # Eksiler (Puan kırılan yerler)

    # ---------------------------------------------------
    # A. TREND (%30)
    # ---------------------------------------------------
    s_trend = 0
    if tech:
        close = tech['close_last']
        sma200 = tech['sma200']; sma50 = tech['sma50']
        
        # Ana Trend (SMA200)
        if close > sma200: 
            s_trend += 50
            pros.append("Fiyat SMA200 üzerinde (Ana Trend Boğa)")
        elif close > sma200 * 0.95: 
            s_trend += 30
            cons.append("Fiyat SMA200 altında ama yakın (Tolerans)")
        else:
            cons.append("Ana Trend Zayıf (Fiyat < SMA200)")
        
        # Orta Vade (SMA50)
        if close > sma50: 
            s_trend += 30
            pros.append("Fiyat SMA50 üzerinde (Orta Vade Güçlü)")
        else:
            cons.append("Orta Vade Zayıf (Fiyat < SMA50)")
        
        # Minervini Onayı
        if mini_data and mini_data.get('score', 0) > 50: 
            s_trend += 20
            pros.append("Minervini Trend Şablonuna Uygun")
    
    s_trend = min(s_trend, 100)

    # ---------------------------------------------------
    # B. MOMENTUM (%20)
    # ---------------------------------------------------
    sent_raw = sent_data.get('total', 50) if sent_data else 50
    rsi_val = sent_data.get('raw_rsi', 50) if sent_data else 50
    
    s_mom = (sent_raw * 0.6) + (rsi_val * 0.4)
    
    if sent_raw >= 60: pros.append(f"Genel Duygu Güçlü ({sent_raw}/100)")
    elif sent_raw <= 40: cons.append(f"Genel Duygu Zayıf ({sent_raw}/100)")
    
    if rsi_val > 50: pros.append(f"RSI Pozitif Bölgede ({int(rsi_val)})")
    else: cons.append(f"RSI Negatif Bölgede ({int(rsi_val)})")

    # ---------------------------------------------------
    # C. TEMEL (%30) - Endeks değilse
    # ---------------------------------------------------
    s_fund = fund_data.get('score', 50)
    is_index = ticker.startswith("^") or "XU" in ticker or "-USD" in ticker
    
    if not is_index:
        if s_fund >= 60: pros.append("Temel Veriler Güçlü (Büyüme/Kalite)")
        elif s_fund <= 40: cons.append("Temel Veriler Zayıf/Yetersiz")
        
        # Detaylardan gelenleri ekle
        for d in fund_data.get('details', []):
            pros.append(f"Temel: {d}")

    # ---------------------------------------------------
    # D. SMART / TEKNİK (%20)
    # ---------------------------------------------------
    # ICT (%10)
    s_ict = 50
    if ict_data:
        if "bullish" in ict_data.get('bias', ''): 
            s_ict += 20; pros.append("ICT Yapısı: Bullish (Boğa)")
        elif "bearish" in ict_data.get('bias', ''):
            cons.append("ICT Yapısı: Bearish (Ayı)")
            
        if "Güçlü" in ict_data.get('displacement', ''): 
            s_ict += 20; pros.append("Güçlü Hacim/Enerji (Displacement)")
        else:
            cons.append("Hacim/Enerji Zayıf")
            
        if "Ucuz" in ict_data.get('zone', ''): 
            s_ict += 10; pros.append("Fiyat Ucuzluk (Discount) Bölgesinde")
    s_ict = min(s_ict, 100)

    # Radar 2 (%10)
    s_r2_norm = (r2_score / 7) * 100
    if r2_score >= 4: pros.append("Radar-2 Setup Onayı Mevcut")
    else: cons.append("Net bir Radar-2 Setup Formasyonu Yok")

    # ---------------------------------------------------
    # FİNAL HESAPLAMA
    # ---------------------------------------------------
    if is_index:
        final = (s_trend * 0.40) + (s_mom * 0.30) + (s_ict * 0.15) + (s_r2_norm * 0.15)
    else:
        final = (s_trend * 0.30) + (s_fund * 0.30) + (s_mom * 0.20) + (s_ict * 0.10) + (s_r2_norm * 0.10)

    # Mavi Çip Koruması
    if not is_index and s_fund >= 80 and final < 50:
        final = 50
        pros.append("🛡️ Mavi Çip Koruması (Temel çok güçlü olduğu için puan yükseltildi)")

    return int(final), pros, cons
# ==============================================================================
# 🦅 YENİ: ICT SNIPER TARAMA MOTORU (5 ŞARTLI DEDEKTÖR)
# ==============================================================================
def process_single_ict_setup(symbol, df):
    """
    ICT 2022 Mentorship Model (LONG ve SHORT) Tarayıcısı.
    Hem Alış (Discount) hem Satış (Premium) fırsatlarını aynı anda arar.
    """
    try:
        if df.empty or len(df) < 50: return None
        
        # Son veriler
        close = df['Close']; high = df['High']; low = df['Low']; open_ = df['Open']
        current_price = float(close.iloc[-1])
        
        # --- 1. ADIM: DEALING RANGE (OYUN SAHASI) ---
        lookback = 40
        recent_high = high.tail(lookback).max()
        recent_low = low.tail(lookback).min()
        
        range_size = recent_high - recent_low
        equilibrium = recent_low + (range_size * 0.5) # %50 Seviyesi
        
        # Karar: Fiyat Nerede?
        is_discount = current_price < equilibrium # Ucuz (Long Aranır)
        is_premium = current_price > equilibrium  # Pahalı (Short Aranır)

        # --- ORTAK HESAPLAMALAR ---
        # Displacement (Gövde Gücü) Kontrolü
        body_sizes = abs(close - open_)
        avg_body = body_sizes.rolling(20).mean().iloc[-1]
        recent_max_body = body_sizes.tail(5).max()
        is_displacement = recent_max_body > (avg_body * 1.5)
        
        if not is_displacement: return None # Enerji yoksa iki yöne de bakma

        # =========================================================
        # SENARYO A: LONG (BOĞA) ARANIYOR (Discount Bölgesi)
        # =========================================================
        if is_discount:
            # 1. Likidite Alımı (SSL Taken): Son 20 günde, önceki dipler ihlal edildi mi?
            prev_low_20 = low.iloc[-40:-20].min()
            curr_low_20 = low.iloc[-20:].min()
            
            if curr_low_20 < prev_low_20: # Dip temizliği var
                # 2. MSS (Market Yapı Kırılımı): Yukarı dönüş var mı?
                short_term_high = high.iloc[-20:-5].max()
                if close.iloc[-1] > short_term_high: # Kırılım gerçekleşti
                    
                    # 3. FVG Kontrolü (Bullish)
                    for i in range(len(df)-1, len(df)-10, -1):
                        if low.iloc[i] > high.iloc[i-2]: # Gap Var
                            fvg_top = low.iloc[i]; fvg_bot = high.iloc[i-2]
                            # Fiyata yakın mı?
                            if current_price <= (fvg_top * 1.02) and current_price >= (fvg_bot * 0.98):
                                return {
                                    "Sembol": symbol, "Fiyat": current_price,
                                    "Yön": "LONG", "İkon": "🐂", "Renk": "#16a34a",
                                    "Durum": "OTE (Ucuzluk Bölgesi)",
                                    "Stop_Loss": f"{curr_low_20:.2f}",
                                    "Skor": 95
                                }

        # =========================================================
        # SENARYO B: SHORT (AYI) ARANIYOR (Premium Bölgesi)
        # =========================================================
        elif is_premium:
            # 1. Likidite Alımı (BSL Taken): Son 20 günde, önceki tepeler ihlal edildi mi?
            prev_high_20 = high.iloc[-40:-20].max()
            curr_high_20 = high.iloc[-20:].max()
            
            if curr_high_20 > prev_high_20: # Tepe temizliği var
                # 2. MSS (Market Yapı Kırılımı): Aşağı dönüş var mı?
                short_term_low = low.iloc[-20:-5].min()
                if close.iloc[-1] < short_term_low: # Aşağı kırılım gerçekleşti
                    
                    # 3. FVG Kontrolü (Bearish)
                    # Bearish FVG: Mum(i) High < Mum(i-2) Low
                    for i in range(len(df)-1, len(df)-10, -1):
                        if high.iloc[i] < low.iloc[i-2]: # Gap Var
                            fvg_top = low.iloc[i-2]; fvg_bot = high.iloc[i]
                            # Fiyata yakın mı?
                            if current_price >= (fvg_bot * 0.98) and current_price <= (fvg_top * 1.02):
                                return {
                                    "Sembol": symbol, "Fiyat": current_price,
                                    "Yön": "SHORT", "İkon": "🐻", "Renk": "#dc2626",
                                    "Durum": "OTE (Pahalılık Bölgesi)",
                                    "Stop_Loss": f"{curr_high_20:.2f}",
                                    "Skor": 95
                                }

        return None # Hiçbir şarta uymadı

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
        sma200_up = sma200 > sma200_prev
        
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
            # TradingView'in "Max Bars Back" (2000 bar) limitini karşılamak için
            # Günlük veri çekiyoruz. 10 Yıl = ~2500 bar.
            df = yf.download(clean_ticker, period="10y", interval="1d", progress=False)
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

def render_lorentzian_panel(ticker):
    data = calculate_lorentzian_classification(ticker)
    
    # 1. KİLİT: Veri hiç yoksa çık (Bunu koymazsan kod çöker)
    if not data: return
    # 2. KİLİT: Veri var ama güven 7/8'den düşükse çık (Senin istediğin filtre)
    if data['votes'] < 7: return 

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
    st.markdown(html_content.replace("\n", " "), unsafe_allow_html=True)

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
    GÜNCELLENMİŞ: RS MOMENTUM LİDERLERİ TARAMASI (SWING + GÜNLÜK)
    Hem 5 günlük Alpha'yı hem de BUGÜNKÜ anlık Alpha'yı hesaplar.
    """
    # 1. Verileri Çek (Biraz daha geniş alalım, 3 ay yeterli)
    data = get_batch_data_cached(asset_list, period="3mo")
    if data.empty: return pd.DataFrame()

    # 2. Endeks Verisi
    cat = st.session_state.get('category', 'S&P 500')
    bench_ticker = "XU100.IS" if "BIST" in cat else "^GSPC"
    df_bench = get_safe_historical_data(bench_ticker, period="3mo")
    
    if df_bench is None or df_bench.empty: return pd.DataFrame()
    
    # Endeks Performansları
    b_close = df_bench['Close']
    # 5 Günlük Endeks Değişimi
    bench_5d = ((b_close.iloc[-1] - b_close.iloc[-6]) / b_close.iloc[-6]) * 100
    # 1 Günlük Endeks Değişimi (Bugün)
    bench_1d = ((b_close.iloc[-1] - b_close.iloc[-2]) / b_close.iloc[-2]) * 100

    results = []

    # 3. Hisseleri Tara
    for symbol in asset_list:
        try:
            # Veri Ayrıştırma
            if isinstance(data.columns, pd.MultiIndex):
                if symbol not in data.columns.levels[0]: continue
                df = data[symbol].dropna()
            else:
                df = data.dropna()

            if len(df) < 20: continue

            # --- HESAPLAMALAR ---
            close = df['Close']; volume = df['Volume']
            
            # A. 5 GÜNLÜK PERFORMANS
            stock_now = float(close.iloc[-1])
            stock_old_5 = float(close.iloc[-6])
            stock_perf_5d = ((stock_now - stock_old_5) / stock_old_5) * 100
            alpha_5d = stock_perf_5d - bench_5d
            
            # B. 1 GÜNLÜK PERFORMANS (BUGÜN)
            stock_old_1 = float(close.iloc[-2])
            stock_perf_1d = ((stock_now - stock_old_1) / stock_old_1) * 100
            alpha_1d = stock_perf_1d - bench_1d # Bugün endekse ne kadar fark attı?

            # C. Hacim
            curr_vol = float(volume.iloc[-1])
            avg_vol = float(volume.iloc[-21:-1].mean())
            vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 0

            # --- FİLTRELEME (SWING KRİTERİ: 5 Günlük Güç) ---
            # Alpha > 2.0 ve Hacim ölmemiş
            if alpha_5d >= 2.0 and vol_ratio > 0.8:
                
                results.append({
                    "Sembol": symbol,
                    "Fiyat": stock_now,
                    "Alpha_5D": alpha_5d,
                    "Alpha_1D": alpha_1d, # Bugünün Gücü
                    "Degisim_1D": stock_perf_1d, # Bugünün Yüzdesi
                    "Hacim_Kat": vol_ratio,
                    "Skor": alpha_5d + alpha_1d # Sıralama puanı
                })

        except: continue

    # 4. Sıralama
    if results:
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

# --- ICT MODÜLÜ (GÜNCELLENMİŞ: Hata Korumalı) ---
@st.cache_data(ttl=600)
def calculate_ict_deep_analysis(ticker):
    error_ret = {"status": "Error", "msg": "Veri Yok", "structure": "-", "bias": "-", "entry": 0, "target": 0, "stop": 0, "rr": 0, "desc": "Veri bekleniyor", "displacement": "-", "fvg_txt": "-", "ob_txt": "-", "zone": "-", "mean_threshold": 0, "curr_price": 0, "setup_type": "BEKLE"}
    
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
        
        structure = "YATAY / KONSOLİDE"
        bias = "neutral"
        displacement_txt = "Zayıf (Hacimsiz Hareket)"
        
        last_candle_body = abs(open_.iloc[-1] - close.iloc[-1])
        if last_candle_body > avg_body_size.iloc[-1] * 1.2:
             displacement_txt = "🔥 Güçlü Displacement (Hacimli Kırılım)"
        
        if curr_price > last_sh:
            structure = "BOS (Yükseliş Kırılımı) 🐂"
            bias = "bullish"
        elif curr_price < last_sl:
            structure = "BOS (Düşüş Kırılımı) 🐻"
            bias = "bearish"
        else:
            structure = "Internal Range (Düşüş/Düzeltme)"
            if close.iloc[-1] > open_.iloc[-1]: bias = "bullish_retrace" 
            else: bias = "bearish_retrace"

        next_bsl = min([h[1] for h in sw_highs if h[1] > curr_price], default=high.max())
        next_ssl = max([l[1] for l in sw_lows if l[1] < curr_price], default=low.min())

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
                    ob_low = df['Low'].iloc[i]
                    ob_high = df['High'].iloc[i]
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
                    ob_low = df['Low'].iloc[i]
                    ob_high = df['High'].iloc[i]
                    active_ob_txt = f"{ob_low:.2f} - {ob_high:.2f} (Arz Bölgesi)"
                    mean_threshold = (ob_low + ob_high) / 2
                    break

        range_high = max(high.tail(60)); range_low = min(low.tail(60))
        range_loc = (curr_price - range_low) / (range_high - range_low)
        zone = "PREMIUM (Pahalı)" if range_loc > 0.5 else "DISCOUNT (Ucuz)"

        setup_type = "BEKLE"
        entry_price = 0.0; stop_loss = 0.0; take_profit = 0.0; rr_ratio = 0.0
        setup_desc = "Mantıklı bir R/R kurulumu veya Bölge uyumu bekleniyor."
        
        if bias in ["bullish", "bullish_retrace"] and zone == "DISCOUNT (Ucuz)":
            valid_fvgs = [f for f in bullish_fvgs if f['top'] < curr_price]
            if valid_fvgs and next_bsl > curr_price:
                best_fvg = valid_fvgs[-1]
                temp_entry = best_fvg['top']
                if next_bsl > temp_entry:
                    entry_price = temp_entry
                    take_profit = next_bsl
                    stop_loss = last_sl if last_sl < entry_price else best_fvg['bot'] - atr * 0.5
                    risk = entry_price - stop_loss
                    reward = take_profit - entry_price
                    if risk > 0:
                        rr_ratio = reward / risk
                        setup_type = "LONG"
                        setup_desc = "Fiyat ucuzluk bölgesinde. FVG desteğinden yukarıdaki likidite (BSL) hedefleniyor."

        elif bias in ["bearish", "bearish_retrace"] and zone == "PREMIUM (Pahalı)":
            valid_fvgs = [f for f in bearish_fvgs if f['bot'] > curr_price]
            if valid_fvgs and next_ssl < curr_price:
                best_fvg = valid_fvgs[-1]
                temp_entry = best_fvg['bot']
                if next_ssl < temp_entry:
                    entry_price = temp_entry
                    take_profit = next_ssl
                    stop_loss = last_sh if last_sh > entry_price else best_fvg['top'] + atr * 0.5
                    risk = stop_loss - entry_price
                    reward = entry_price - take_profit
                    if risk > 0:
                        rr_ratio = reward / risk
                        setup_type = "SHORT"
                        setup_desc = "Fiyat pahalılık bölgesinde. Direnç bloğundan aşağıdaki likidite (SSL) hedefleniyor."

        return {
            "status": "OK", "structure": structure, "bias": bias, "zone": zone,
            "setup_type": setup_type, "entry": entry_price, "stop": stop_loss, "target": take_profit,
            "rr": rr_ratio, "desc": setup_desc, "last_sl": last_sl, "last_sh": last_sh,
            "displacement": displacement_txt, "fvg_txt": active_fvg_txt, "ob_txt": active_ob_txt,
            "mean_threshold": mean_threshold, "curr_price": curr_price
        }

    except Exception: return error_ret
        
@st.cache_data(ttl=600)
def calculate_price_action_dna(ticker):
    try:
        df = get_safe_historical_data(ticker, period="6mo") 
        if df is None or len(df) < 50: return None
        
        o = df['Open']; h = df['High']; l = df['Low']; c = df['Close']; v = df['Volume']
        
        # --- VERİ HAZIRLIĞI (SON 3 GÜN) ---
        c1_o, c1_h, c1_l, c1_c = float(o.iloc[-1]), float(h.iloc[-1]), float(l.iloc[-1]), float(c.iloc[-1]) # Bugün
        c2_o, c2_h, c2_l, c2_c = float(o.iloc[-2]), float(h.iloc[-2]), float(l.iloc[-2]), float(c.iloc[-2]) # Dün
        c3_o, c3_h, c3_l, c3_c = float(o.iloc[-3]), float(h.iloc[-3]), float(l.iloc[-3]), float(c.iloc[-3]) # Önceki Gün
        
        c1_v = float(v.iloc[-1])
        avg_v = float(v.rolling(20).mean().iloc[-1]) 
        sma50 = c.rolling(50).mean().iloc[-1]
        
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
        # 1. TEKLİ MUM FORMASYONLARI
        # ======================================================
        if total_len > 0:
            # Hammer
            if l_wick > body * wick_ratio and u_wick < body * 0.5: 
                if trend_dir == "DÜŞÜŞ" or is_oversold: add_signal(bulls, "Hammer 🔨", True)
                else: neutrals.append("Hanging Man Potansiyeli")
            
            # Shooting Star
            if u_wick > body * wick_ratio and l_wick < body * 0.5: 
                if trend_dir == "YÜKSELİŞ" or is_overbought: add_signal(bears, "Shooting Star 🔫", False)
            
            # Stopping Volume (Smart Money İmzası)
            if (l_wick > body * 2.0) and (c1_v > avg_v * 1.5) and (c1_l < c2_l):
                bulls.append("🛑 STOPPING VOLUME (Kurumsal Alım)")
            
            # Marubozu
            if body > total_len * 0.85: 
                if is_green: add_signal(bulls, "Marubozu 🚀", True)
                else: add_signal(bears, "Marubozu 🔻", False)
            
            # Doji
            if body < total_len * doji_threshold: neutrals.append("Doji (Kararsızlık) ⚖️")

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

        # GÜNCELLENMİŞ RETURN BLOĞU
        return {
            "candle": {"title": candle_title, "desc": candle_desc},
            "sfp": {"title": sfp_txt, "desc": sfp_desc},
            "vol": {"title": vol_txt, "desc": vol_desc},
            "loc": {"title": loc_txt, "desc": loc_desc},
            "sq": {"title": sq_txt, "desc": sq_desc},
            "obv": obv_data,
            "div": {"title": div_txt, "desc": div_desc, "type": div_type},
            # --- YENİ EKLENENLER ---
            "vwap": {"val": vwap_now, "diff": vwap_diff},
            "rs": {"alpha": alpha_val}
        }
    except Exception: return None

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

def calculate_fib_levels(df, period=144):
    """
    Trend yönüne göre Dinamik Fibonacci Hesaplama
    """
    try:
        if len(df) < period: period = len(df)
        recent_data = df.tail(period)
        
        max_h = recent_data['High'].max()
        min_l = recent_data['Low'].min()
        diff = max_h - min_l
        
        # Trend Yönünü Basitçe Bulalım (Son fiyat ortalamanın üstünde mi?)
        close = df['Close'].iloc[-1]
        sma50 = df['Close'].rolling(50).mean().iloc[-1]
        is_uptrend = close > sma50 
        
        levels = {}
        
        if is_uptrend:
            # YÜKSELİŞ TRENDİ (Dipten Tepeye Referans)
            # Golden Pocket AŞAĞIDA (Destek) olmalı
            levels = {
                "1.618 (Hedef)": max_h + (diff * 0.618),
                "1.236 (Kırılım Hedefi)": max_h + (diff * 0.236), # YENİ EKLENEN SEVİYE
                "0 (Tepe)": max_h,
                "0.236": max_h - (diff * 0.236),
                "0.382": max_h - (diff * 0.382),
                "0.5 (Orta)": max_h - (diff * 0.5),
                "0.618 (Golden - Alım)": max_h - (diff * 0.618), # Fiyatın altında kalır
                "1 (Dip)": min_l
            }
        else:
            # DÜŞÜŞ TRENDİ (Tepeden Dibe Referans)
            # Golden Pocket YUKARIDA (Direnç/Short) olmalı
            levels = {
                "1 (Tepe)": max_h,
                "0.618 (Golden - Satış)": min_l + (diff * 0.618), # Fiyatın üstünde kalır
                "0.5 (Orta)": min_l + (diff * 0.5),
                "0.382": min_l + (diff * 0.382),
                "0.236": min_l + (diff * 0.236),
                "0 (Dip)": min_l,
                "-0.236 (Kırılım Hedefi)": min_l - (diff * 0.236), # YENİ EKLENEN SEVİYE
                "-0.618 (Hedef)": min_l - (diff * 0.618)
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
    
    # 2. Fibonacci
    fibs = calculate_fib_levels(df, period=120)
    
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
# 4. GÖRSELLEŞTİRME FONKSİYONLARI (EKSİK OLAN KISIM)
# ==============================================================================

def render_sentiment_card(sent):
    if not sent: return
    display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")
    
    score = sent['total']
    if score >= 70: color = "#16a34a"; icon = "🔥"; status = "GÜÇLÜ BOĞA"
    elif score >= 50: color = "#d97706"; icon = "↔️"; status = "NÖTR / POZİTİF"
    elif score >= 30: color = "#b91c1c"; icon = "🐻"; status = "ZAYIF / AYI"
    else: color = "#7f1d1d"; icon = "❄️"; status = "ÇÖKÜŞ"
    
    # 1. Başlık Puan Etiketi (25p mi 20p mi?)
    p_label = '25p' if sent.get('is_index', False) else '20p'
    
    # 2. RS Kutusu Başlığı (Devre Dışı mı 15p mi?)
    rs_label = 'Devre Dışı' if sent.get('is_index', False) else '15p'

    html_content = f"""
    <div class="info-card">
        <div class="info-header">🎭 Smart Money Sentiment: {display_ticker}</div>
        
        <div class="info-row" style="border-bottom: 2px solid {color}; padding-bottom:6px; margin-bottom:8px; background-color:{color}10; border-radius:4px; padding:6px;">
            <div style="font-weight:500; color:{color}; font-size:1rem;">{score}/100 {icon} {status}</div>
        </div>
        
        <div style="font-family:'Arial', sans-serif; font-size:0.8rem; color:#1e3a8a; margin-bottom:8px; text-align:center; letter-spacing:1px;">{sent['bar']}</div>
        
        <div class="info-row" style="background:#f0f9ff; padding:2px; border-radius:4px;">
            <div class="label-long" style="width:120px; color:#0369a1;">1. YAPI ({p_label}):</div>
            <div class="info-val" style="font-weight:700;">{sent['str']}</div>
        </div>
        <div class="edu-note">Market Yapısı- Son 20 günün %97-100 zirvesinde (12). Son 5 günün en düşük seviyesi, önceki 20 günün en düşük seviyesinden yukarıdaysa: HL (8)</div>

        <div class="info-row">
            <div class="label-long" style="width:120px;">2. TREND ({p_label}):</div>
            <div class="info-val">{sent['tr']}</div>
        </div>
        <div class="edu-note">Ortalamalara bakar. Hisse fiyatı SMA200 üstünde (8). EMA20 üstünde (8). Kısa vadeli ortalama, orta vadeli ortalamanın üzerinde, yani EMA20 > SMA50 (4)</div>
        
        <div class="info-row">
            <div class="label-long" style="width:120px;">3. HACİM ({p_label}):</div>
            <div class="info-val">{sent['vol']}</div>
        </div>
        <div class="edu-note">Hacmin 20G ortalamaya oranını ve On-Balance Volume (OBV) denetler. Bugünün hacmi son 20G ort.üstünde (12) Para girişi var: 10G ortalamanın üstünde (8)</div>

        <div class="info-row">
            <div class="label-long" style="width:120px;">4. MOMENTUM (15p):</div>
            <div class="info-val">{sent['mom']}</div>
        </div>
        <div class="edu-note">RSI ve MACD ile itki gücünü ölçer. 50 üstü RSI (5) RSI ivmesi artıyor (5). MACD sinyal çizgisi üstünde (5)</div>
        
        <div class="info-row">
            <div class="label-long" style="width:120px;">5. SIKIŞMA (10p):</div>
            <div class="info-val">{sent['vola']}</div>
        </div>
        <div class="edu-note">Bollinger Bant genişliğini inceler. Bant genişliği son 20G ortalamasından dar (10)</div>

        <div class="info-row">
            <div class="label-long" style="width:120px;">6. GÜÇ ({rs_label}):</div>
            <div class="info-val">{sent['rs']}</div>
        </div>
        <div class="edu-note">Hissenin Endekse göre relatif gücünü (RS) ölçer. Mansfield RS göstergesi 0'ın üzerinde (5). RS trendi son 5 güne göre yükselişte (5). Endeks düşerken hisse artıda (Alpha) (5)</div>
    </div>
    """.replace("\n", "")
    
    st.markdown(html_content, unsafe_allow_html=True)

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
    display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")
    st.markdown(f"""<div class="info-card" style="margin-bottom:10px;"><div class="info-header">🌊 Para Akış İvmesi & Fiyat Dengesi: {display_ticker}</div></div>""", unsafe_allow_html=True)
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
        st.altair_chart(alt.layer(area, line_stp, line_price).properties(height=280, title=alt.TitleParams("Sentiment Analizi: Mavi (Fiyat) Sarıyı (STP-EMA6) Yukarı Keserse AL, aşağıya keserse SAT", fontSize=14, color="#1e40af")), use_container_width=True)

def render_price_action_panel(ticker):
    obv_title, obv_color, obv_desc = get_obv_divergence_status(ticker)
    pa = calculate_price_action_dna(ticker)
    if not pa:
        st.info("PA verisi bekleniyor...")
        return

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
        <div style="border-top: 1px dashed #cbd5e1; margin-top:8px; padding-top:6px;"></div>

        <div style="margin-bottom:8px;">
            <div style="font-weight:700; font-size:0.8rem; color:{vwap_col};">7. KURUMSAL MALİYET (VWAP): {vwap_txt}</div>
            <div class="edu-note">{vwap_desc} (Son 20 gün Hacim Ağırlıklı Ortalama Fiyat-VWAP: {vwap_data['val']:.2f})</div>
        </div>

        <div style="margin-bottom:2px;">
            <div style="font-weight:700; font-size:0.8rem; color:{rs_col};">8. RS: PİYASA GÜCÜ (Bugün): {rs_txt}</div>
            <div class="edu-note" style="margin-bottom:0;">{rs_desc}</div>
        </div>        
    </div>
    """
    st.markdown(html_content.replace("\n", " "), unsafe_allow_html=True)
    
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
    
    struct_desc = "Piyasa kararsız."
    if "BOS (Yükseliş" in data['structure']: struct_desc = "Boğalar kontrolü elinde tutuyor. Eski tepeler aşıldı, bu da yükseliş iştahının devam ettiğini gösterir. Geri çekilmeler alım fırsatı olabilir."
    elif "BOS (Düşüş" in data['structure']: struct_desc = "Ayılar piyasaya hakim. Eski dipler kırıldı, düşüş trendi devam ediyor. Yükselişler satış fırsatı olarak görülebilir."
    elif "Internal" in data['structure']: struct_desc = "Ana trendin tersine bir düzeltme hareketi (Internal Range) yaşanıyor olabilir. Piyasada kararsızlık hakim."

    energy_desc = "Mum gövdeleri küçük, hacimsiz bir hareket. Kurumsal oyuncular henüz oyuna tam girmemiş olabilir. Kırılımlar tuzak olabilir."
    if "Güçlü" in data['displacement']: energy_desc = "Fiyat güçlü ve hacimli mumlarla hareket ediyor. Bu 'Akıllı Para'nın (Smart Money) ayak sesidir."

    zone_desc = "Fiyat 'Ucuzluk' (Discount) bölgesinde. Kurumsal yatırımcılar bu seviyelerden alım yapmayı tercih eder."
    if "PREMIUM" in data['zone']: zone_desc = "Fiyat 'Pahalılık' (Premium) bölgesinde. Kurumsal yatırımcılar bu bölgede satış yapmayı veya kar almayı sever."

    fvg_desc = "Dengesizlik Boşluğu: Yani, Fiyatın denge bulmak için bu aralığı doldurması (rebalance) beklenir. Mıknatıs etkisi yapar."
    if "Yok" in data['fvg_txt']: fvg_desc = "Yakınlarda önemli bir dengesizlik boşluğu tespit edilemedi."

    ob_desc = "Order Block: Yani Kurumsal oyuncuların son yüklü işlem yaptığı seviye. Fiyat buraya dönerse güçlü tepki alabilir: Eğer bu bölge fiyatı yeni bir tepeye (BOS) götürdüyse 'Kaliteli'dir. Götürmediyse zayıftır."
    
    liq_desc = "Yani Fiyatın bir sonraki durağı. Stop emirlerinin (Likiditenin) biriktiği, fiyatın çekildiği hedef seviye."

    bias_color = "#16a34a" if "bullish" in data['bias'] else "#dc2626" if "bearish" in data['bias'] else "#475569"
    bg_color_old = "#f0fdf4" if "bullish" in data['bias'] else "#fef2f2" if "bearish" in data['bias'] else "#f8fafc"

    mt_html = "" 
    mt_val = data.get('mean_threshold', 0)
    curr = data.get('curr_price', 0)
    
    if mt_val > 0 and curr > 0:
        diff_pct = (curr - mt_val) / mt_val
        if abs(diff_pct) < 0.003: 
            mt_status = "⚠️ KARAR ANI (BIÇAK SIRTI)"
            mt_desc = "Fiyat, yapının tam %50 denge noktasını test ediyor. Kırılım yönü beklenmeli."
            mt_color = "#d97706"; mt_bg = "#fffbeb" 
        elif diff_pct > 0:
            mt_status = "🛡️ Alıcılar Korumada" if "bullish" in data['bias'] else "Fiyat Dengenin Üzerinde"
            mt_desc = "Fiyat kritik orta noktanın üzerinde tutunuyor. Yapı korunuyor."
            mt_color = "#15803d"; mt_bg = "#f0fdf4" 
        else:
            mt_status = "🛡️ Satıcılar Baskın" if "bearish" in data['bias'] else "💀 Savunma Çöktü"
            mt_desc = "Fiyat kritik orta noktanın altına sarktı. Yapı bozulmuş olabilir."
            mt_color = "#b91c1c"; mt_bg = "#fef2f2" 
            
        mt_html = f"""
        <div style="background:{mt_bg}; padding:6px; border-radius:5px; border-left:3px solid {mt_color}; margin-bottom:8px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:700; color:{mt_color}; font-size:0.8rem;">⚖️ {mt_status}</span>
                <span style="font-family:'JetBrains Mono'; font-size:0.8rem; font-weight:700;">{mt_val:.2f}</span>
            </div>
            <div class="edu-note" style="margin-bottom:0;">{mt_desc}</div>
        </div>
        """
   
    html_content = f"""
    <div class="info-card" style="margin-bottom:8px;">
        <div class="info-header">🧠 ICT Smart Money Analizi: {display_ticker}</div>
        
        <div style="background:{bg_color_old}; padding:6px; border-radius:5px; border-left:3px solid {bias_color}; margin-bottom:8px;">
            <div style="font-weight:700; color:{bias_color}; font-size:0.8rem; margin-bottom:2px;">{data['structure']}</div>
            <div class="edu-note">{struct_desc}</div>
            
            <div class="info-row"><div class="label-long">Enerji:</div><div class="info-val">{data['displacement']}</div></div>
            <div class="edu-note">{energy_desc}</div>
        </div>

        {mt_html}

        <div style="margin-bottom:8px;">
            <div style="font-size:0.8rem; font-weight:700; color:#1e3a8a; border-bottom:1px dashed #cbd5e1; margin-bottom:4px;">📍 Ucuz Pahalı Okları (Giriş/Çıkış Referansları)</div>
            
            <div class="info-row"><div class="label-long">Konum:</div><div class="info-val" style="font-weight:700;">{data['zone']}</div></div>
            <div class="edu-note">{zone_desc}</div>
            
            <div class="info-row"><div class="label-long">GAP (FVG):</div><div class="info-val">{data['fvg_txt']}</div></div>
            <div class="edu-note">{fvg_desc}</div>
            
            <div class="info-row"><div class="label-long">Aktif OB:</div><div class="info-val">{data['ob_txt']}</div></div>
            <div class="edu-note">{ob_desc}</div>
        </div>

        <div style="background:#f1f5f9; padding:5px; border-radius:4px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:0.8rem; font-weight:600; color:#475569;">🧲 Hedef Likidite</span>
                <span style="font-family:'JetBrains Mono'; font-weight:700; font-size:0.8rem; color:#0f172a;">{data['target']:.2f}</span>
            </div>
            <div class="edu-note" style="margin-bottom:0;">{liq_desc}</div>
        </div>
    </div>
    """
    
    st.markdown(html_content.replace("\n", " "), unsafe_allow_html=True)

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
    else:
        # Düşüş Senaryosu
        st_label = "Trend Dönüşü (Direnç)"
        st_desc = "🚀 Fiyat bu seviyenin <b>üstüne çıkarsa</b> düşüş biter, yükseliş başlar."
        
        # Golden Pocket Metni (Düşüş)
        gp_desc_text = "⚠️ Güçlü Direnç / Tepki Satış Bölgesi (Short)."
        gp_desc_color = "#b91c1c" # Kırmızı
    
    # Fibonacci Formatlama
    sup_lbl, sup_val = data['nearest_sup']
    res_lbl, res_val = data['nearest_res']
    
    # --- GÖRSEL DÜZELTME ---
    if res_lbl == "ZİRVE AŞIMI":
        res_display = "---"
        res_desc = "🚀 Fiyat tüm dirençleri kırdı (Price Discovery)."
    else:
        res_display = f"{res_val:.2f}"
        res_desc = "Zorlu tavan. Geçilirse yükseliş hızlanır."

    # --- GOLDEN POCKET DEĞERİ ---
    gp_key = next((k for k in data['fibs'].keys() if "Golden" in k), "0.618 (Golden)")
    gp_val = data['fibs'].get(gp_key, 0)
    
    html_content = f"""
    <div class="info-card" style="border-top: 3px solid #8b5cf6;">
        <div class="info-header" style="color:#4c1d95;">📐 Kritik Seviyeler & Trend: {display_ticker}</div>
        
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
                <div style="font-size:0.65rem; color:#166534; font-weight:700;">EN YAKIN DİRENÇ 🚧</div>
                <div style="font-family:'JetBrains Mono'; font-weight:700; color:#15803d; font-size:0.85rem;">{res_display}</div>
                <div style="font-size:0.6rem; color:#166534; margin-bottom:2px;">Fib {res_lbl}</div>
                <div style="font-size:0.6rem; color:#64748B; font-style:italic; line-height:1.1;">{res_desc}</div>
            </div>
            
            <div style="background:#fef2f2; padding:6px; border-radius:4px; border:1px solid #fecaca;">
                <div style="font-size:0.65rem; color:#991b1b; font-weight:700;">EN YAKIN DESTEK 🛡️</div>
                <div style="font-family:'JetBrains Mono'; font-weight:700; color:#b91c1c; font-size:0.85rem;">{sup_val:.2f}</div>
                <div style="font-size:0.6rem; color:#991b1b; margin-bottom:2px;">Fib {sup_lbl}</div>
                <div style="font-size:0.6rem; color:#64748B; font-style:italic; line-height:1.1;">İlk savunma hattı. Düşüşü tutmalı.</div>
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

def render_lorentzian_panel(ticker):
    data = calculate_lorentzian_classification(ticker)
    
    # Veri yoksa gösterme (Eski satır)
    if not data: return
    # Skor 7 altında kalsa da gösterme 
    if data['votes'] < 7: return

    display_prob = int(data['prob'])
    # İkon seçimi
    ml_icon = "🚀" if data['signal'] == "YÜKSELİŞ" and display_prob >= 75 else "🐻" if data['signal'] == "DÜŞÜŞ" and display_prob >= 75 else "🧠"
    
    bar_width = display_prob
    signal_text = f"{data['signal']} BEKLENTİSİ"

    # Başlık: GÜNLÜK
    # Alt Bilgi: Vade: 1 Gün
    html_content = f"""
    <div class="info-card" style="border-top: 3px solid {data['color']}; margin-bottom: 15px;">
        <div class="info-header" style="color:{data['color']}; display:flex; justify-content:space-between; align-items:center;">
            <span>{ml_icon} Lorentzian (Yarın Beklentisi): {ticker.replace('.IS', '')}</span>
            <span style="font-size:0.75rem; background:{data['color']}15; padding:2px 8px; border-radius:10px; font-weight:400; color:{data['color']};">%{display_prob} Güven</span>
        </div>
        
        <div style="text-align:center; padding:8px 0;">
            <div style="font-size:0.9rem; font-weight:800; color:{data['color']}; letter-spacing:0.5px;">
                {signal_text}
            </div>
            <div style="font-size:0.65rem; color:#64748B; margin-top:4px;">
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
            <div style="font-size:0.8rem; font-weight:700; color:#1e3a8a; border-bottom:1px solid #e2e8f0; padding-bottom:4px; margin-bottom:4px;">📋 TARAMA SONUÇLARI - {display_ticker_safe}{star_title}</div>
            {scan_results_html}
        </div>
        """, unsafe_allow_html=True)
    else:
        # Hiçbir şey yoksa boş bırak
        pass
        
    # -----------------------------------------------------------
    # --- TEMEL ANALİZ DETAYLARI (DÜZELTİLMİŞ & TEK PARÇA) ---
        sentiment_verisi = calculate_sentiment_score(st.session_state.ticker)
    
    # 1. PİYASA DUYGUSU (En Üstte)
    sentiment_verisi = calculate_sentiment_score(st.session_state.ticker)
    if sentiment_verisi:
        render_sentiment_card(sentiment_verisi)

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # MINERVINI PANELİ (Hatasız Versiyon)
    render_minervini_panel_v2(st.session_state.ticker)
    # --- YILDIZ ADAYLARI (KESİŞİM PANELİ) ---
    st.markdown(f"""
    <div style="background: linear-gradient(45deg, #06b6d4, #3b82f6); color: white; padding: 8px; border-radius: 6px; text-align: center; font-weight: 700; font-size: 0.9rem; margin-bottom: 10px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
        🌟 YILDIZ ADAYLARI
    </div>
    """, unsafe_allow_html=True)
    
    # Kesişim Mantığı
    stars_found = False
    
    # Scroll Alanı Başlatıyoruz
    with st.container(height=150):
        
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
                            'alpha': row_rs['Alpha_5D'],
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
                        label = f"💎 {sym} | Alpha:+%{item['alpha']:.1f} | {item['status']}"
                        
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
                        label = f"🚀 {sym} ({item['price']}) | HAREKET"
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
                        label = f"⏳ {sym} ({item['price']}) | HAZIRLIK"
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

    # LORENTZİAN PANELİ 
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    render_lorentzian_panel(st.session_state.ticker)
    st.divider()
    # 3. AI ANALIST (En Altta)
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
            
            # 2. STP & MOMENTUM AJANI - %25
            my_bar.progress(25, text="⚡ STP ve Momentum Taranıyor...%25")
            crosses, trends, filtered = scan_stp_signals(scan_list)
            st.session_state.stp_crosses = crosses
            st.session_state.stp_trends = trends
            st.session_state.stp_filtered = filtered
            st.session_state.stp_scanned = True

            # 3. ICT SNIPER AJANI --- %35
            my_bar.progress(50, text="🦅 ICT Sniper Kurulumları (Liquidity+MSS+FVG) Taranıyor...%35")
            st.session_state.ict_scan_data = scan_ict_batch(scan_list)

            # 4. SENTIMENT (AKILLI PARA) AJANI - %40
            my_bar.progress(40, text="🤫 Gizli Toplama (Smart Money) Aranıyor...%40")
            st.session_state.accum_data = scan_hidden_accumulation(scan_list)
            
            # 5. RS LİDERLERİ TARAMASI - %45
            my_bar.progress(45, text="🏆 Son 5 günün Piyasa Liderleri (RS Momentum) Hesaplanıyor...%45")
            st.session_state.rs_leaders_data = scan_rs_momentum_leaders(scan_list)
            
            # 6. BREAKOUT AJANI (ISINANLAR/KIRANLAR) - %55
            my_bar.progress(55, text="🔨 Kırılımlar ve Hazırlıklar Kontrol Ediliyor...%55")
            st.session_state.breakout_left = agent3_breakout_scan(scan_list)      # Isınanlar
            st.session_state.breakout_right = scan_confirmed_breakouts(scan_list) # Kıranlar
            
            # 7. RADAR 1 & RADAR 2 (GENEL TEKNİK) - %70
            my_bar.progress(70, text="🧠 Radar Sinyalleri İşleniyor...%70")
            st.session_state.scan_data = analyze_market_intelligence(scan_list)
            st.session_state.radar2_data = radar2_scan(scan_list)
            
            # 8. FORMASYON & TUZAKLAR - %85
            my_bar.progress(85, text="🦁Formasyon ve Tuzaklar Taranıyor...%85")
            st.session_state.pattern_data = scan_chart_patterns(scan_list)
            st.session_state.bear_trap_data = scan_bear_traps(scan_list)
            
            # 9. RSI UYUMSUZLUKLARI - %95
            my_bar.progress(95, text="⚖️ RSI Uyumsuzlukları Hesaplanıyor...%95")
            bull_df, bear_df = scan_rsi_divergence_batch(scan_list)
            st.session_state.rsi_div_bull = bull_df
            st.session_state.rsi_div_bear = bear_df
            
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
    
    # --- 1. GEREKLİ VERİLERİ TOPLA ---
    info = fetch_stock_info(t)
    df_hist = get_safe_historical_data(t) # Ana veri
    
    # EKSİK OLAN TANIMLAMALAR EKLENDİ (bench_series ve idx_data)
    cat_for_bench = st.session_state.category
    bench_ticker = "XU100.IS" if "BIST" in cat_for_bench else "^GSPC"
    bench_series = get_benchmark_data(cat_for_bench)
    idx_data = get_safe_historical_data(bench_ticker)['Close'] if bench_ticker else None
    
    # Diğer Hesaplamalar
    ict_data = calculate_ict_deep_analysis(t) or {}
    sent_data = calculate_sentiment_score(t) or {}
    tech_data = get_tech_card_data(t) or {}
    pa_data = calculate_price_action_dna(t) or {}
    levels_data = get_advanced_levels_data(t) or {}
    synth_data = calculate_synthetic_sentiment(t) 
    mini_data = calculate_minervini_sepa(t) or {} 
    fund_data = get_fundamental_score(t) or {}
    master_score, pros, cons = calculate_master_score(t)
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

    # --- 3. METİN ÖZETLEME (SCAN SUMMARY) ---
    scan_box_txt = []
    
    # A. STP
    if stp_res:
        if stp_res['type'] == 'cross': scan_box_txt.append("STP: Kesişim (AL Sinyali)")
        elif stp_res['type'] == 'trend': scan_box_txt.append(f"STP: Trend ({stp_res['data'].get('Gun','?')} Gündür)")
    else: scan_box_txt.append("STP: Nötr")
    
    # B. Akıllı Para
    if acc_res:
        acc_txt = "Pocket Pivot" if acc_res.get('Pocket_Pivot') else "Sessiz Toplama"
        scan_box_txt.append(f"Akıllı Para: {acc_txt}")
    
    # C. Formasyon
    if not pat_df.empty:
        scan_box_txt.append(f"Formasyon: {pat_df.iloc[0]['Formasyon']}")
    
    # D. Radar 2
    if r2_res and r2_res['Skor'] >= 4:
        scan_box_txt.append(f"Radar 2: {r2_res['Setup']} ({r2_res['Skor']}/7)")

    # E. Bear Trap
    bt_txt = "Yok / Temiz"
    if bt_res:
        bt_txt = f"VAR ({bt_res['Zaman']} oluştu, Hacim: {bt_res['Hacim_Kat']})"
        scan_box_txt.append(f"BEAR TRAP: {bt_txt}")

    # F. Breakout
    if bo_res:
        bo_status = "KIRILIM" if ("TETİKLENDİ" in bo_res['Zirveye Yakınlık']) else "Hazırlık"
        scan_box_txt.append(f"Breakout: {bo_status}")

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

        # 3. Yorumla
        if price_trend == "AŞAĞI" and obv_trend == "YUKARI":
            para_akisi_txt = "🔥 GİZLİ GİRİŞ (Pozitif Uyumsuzluk - Fiyat Düşerken Mal Toplanıyor)"
        elif price_trend == "YUKARI" and obv_trend == "AŞAĞI":
            para_akisi_txt = "⚠️ GİZLİ ÇIKIŞ (Negatif Uyumsuzluk - Fiyat Çıkarken Mal Çakılıyor)"
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
    
    fund_txt = " | ".join(fund_data.get('details', [])) if fund_data else "-"
    fiyat_str = f"{info.get('price', 0):.2f}" if info else "0.00"
    master_txt = f"{master_score}/100"
    pros_txt = ", ".join(pros[:5])
    
    st_txt = f"{'YÜKSELİŞ' if levels_data.get('st_dir')==1 else 'DÜŞÜŞ'} | {levels_data.get('st_val',0):.2f}" if levels_data else "-"
    
    # --- 5. FİNAL PROMPT ---
    prompt = f"""*** SİSTEM ROLLERİ ***
Sen Price Action, ICT (Smart Money) ve Mark Minervini (SEPA) stratejilerinde uzmanlaşmış kıdemli bir Fon Yöneticisisin.
Aşağıdaki TEKNİK ve TEMEL verilere dayanarak profesyonel bir analiz/işlem planı oluştur. Basit bir dille anlat.

*** CANLI TARAMA SONUÇLARI (SİNYAL KUTUSU) ***
(Burası sistemin tespit ettiği en sıcak sinyallerdir, analizin merkezine koy!)
{scan_summary_str}

*** VARLIK KİMLİĞİ ***
- Sembol: {t}
- GÜNCEL FİYAT: {fiyat_str}
- ANA SKOR: {master_txt} (Algoritmik Puan)
- Temel Artılar: {pros_txt}

*** SMART MONEY SENTIMENT KARNESİ (Detaylı Puanlar) ***
(Bu bölüm hissenin içsel gücünü gösterir, analizinde mutlaka kullan!)
- YAPI (Structure): {sent_yapi} (Market yapısı Bullish mi?)
- HACİM (Volume): {sent_hacim} (Yükselişi destekliyor mu?)
- TREND: {sent_trend} (Ortalamaların durumu ve kısa vadeli trend için EMA 8/13 üstünde olup olmadığı)
- MOMENTUM: {sent_mom} (RSI ve MACD gücü)
- VOLATİLİTE: {sent_vola} (Sıkışma var mı?)
- MOMENTUM DURUMU (Özel Sinyal): {momentum_analiz_txt}

*** 1. TREND VE GÜÇ (Minervini & SuperTrend) ***
- SuperTrend (Yön): {st_txt}
- Minervini Durumu: {mini_txt}
- SMA50 Durumu: {sma50_str}
- EMA Durumu (8/13): {ema_txt}
- RADAR 1 (Momentum/Hacim): {r1_txt}
- RADAR 2 (Trend/Setup): {r2_txt}
(NOT: Radar 2'deki "Setup" tipi [Trend/Setup] strateji için çok önemlidir.)

*** 2. SMART MONEY & ICT YAPISI ***
- Market Yapısı: {ict_data.get('structure', 'Bilinmiyor')} ({ict_data.get('bias', 'Nötr')})
- Konum (Zone): {ict_data.get('zone', 'Bilinmiyor')}
- Gizli Para Akışı (10G WMA): {para_akisi_txt}
- Aktif FVG: {ict_data.get('fvg_txt', 'Yok')}

*** 3. ŞİRKET TEMEL KALİTESİ ***
- Öne Çıkanlar: {fund_txt}

*** 4. HEDEFLER VE RİSK ***
- Direnç (Hedef): {fib_res}
- Destek (Stop): {fib_sup}
- Hedef Likidite: {liq_str}

*** 5. PRICE ACTION  ***
- Mum Formasyonu: {mum_desc}
- RSI Uyumsuzluğu: {pa_div} (Varsa çok dikkat et!)
- TUZAK DURUMU (SFP): {sfp_desc}
- En Yakın Direnç: {fib_res}
- En Yakın Destek: {fib_sup}
- Hedef Likidite (Mıknatıs): {liq_str}
*** 6. KURUMSAL MALİYET VE GÜÇ ***
- VWAP (Adil Değer): {v_val:.2f}
- Fiyat Konumu: Maliyetin %{v_diff:.1f} üzerinde/altında.
- VWAP DURUMU: {vwap_ai_txt}
- RS (Piyasa Gücü): {rs_ai_txt} (Alpha: {alpha_val:.1f})
(NOT: Eğer VWAP durumu 'PARABOLİK' veya 'ISINIYOR' ise kar realizasyonu uyarısı yap. 'RALLİ MODU' ise trendi sürmeyi öner.)

*** GÖREVİN *** Verileri sentezle ve kaliteli bir analiz kurgula, tavsiye verme (bekle, al, sat, tut vs deme), sadece olasılıkları belirt. 
En başa "SMART MONEY RADAR   #{t}  ANALİZİ -  {fiyat_str} 👇📷" başlığı at ve şunları analiz et. (Twitter için atılacak bi twit tarzında, aşırıya kaçmadan ve basit bir dilde yaz)
1. GENEL ANALİZ: Yanına "(Önem derecesine göre)" diye de yaz 
   - Verilen tüm verileri tara ve toplamda 8 maddelik bir analiz listesi oluştur.
   - SIRALAMA KURALI: Maddeleri "Önem Derecesine" göre azalan şekilde sırala. Düzyazı halinde yapma; Her madde için paragraf aç. Önce olumlu olanları sırala; en çok olumlu’dan en az olumlu’ya doğru sırala. Sonra da olumsuz olanları sırala; en çok olumsuz’dan en az olumsuz’a doğru sırala. Olumsuz olanları sıralamadan evvel "Öte Yandan; " diye bir başlık at ve altına olumsuzları sırala. Otoriter yazma. Geleceği kimse bilemez.
     a) Listenin en başına; "Kırılım (Breakout)", "Akıllı Para (Smart Money)", "Trend Dönüşü" veya "BOS" içeren EN GÜÇLÜ sinyalleri koy ve bunlara (8/10) ile (10/10) arasında puan ver.
     b) Listenin devamına; trendi destekleyen ama daha zayıf olan yan sinyalleri (örneğin: "Hareketli ortalama üzerinde", "RSI 50 üstü" vb.) ekle. Ancak bunlara DÜRÜSTÇE (1/10) ile (7/10) arasında puan ver.
   - UYARI: Listeyi 12 maddeye tamamlamak için zayıf sinyallere asla yapay olarak yüksek puan (8+) verme! Sinyal gücü neyse onu yaz.
   - Her maddeyi yorumlarken; o verinin neden önemli olduğunu (8/10) gibi puanla ve finansal bir dille açıkla. Olumlu maddelerin başına "✅", olumsuz/nötr maddelerin başına " 📍 " koy. 
   Şu terimlerin, (eğer açtığın maddelerin başlık kısmında yer almıyorsa ama açtığın maddelerin açıklama kısmında yer alıyorsa) , başına "#" koyarak yaz: FOMO, BIST100, RSI, ICT, SmartMoney, EMA5, EMA8, EMA13, Sentiment, Supertrend, BOS, Breakout, Minervini, FVG. (yani mesela şöyle: (9/10) MINERVINI HİZALANMASI: #Minervini şablonuna göre....)
2. SENARYO A: ELİNDE OLANLAR İÇİN 
   - Yöntem: [TUTULABİLİR / EKLENEBİLİR / SATILABİLİR / KAR ALINABİLİR]
   - Strateji: Trend bozulmadığı sürece taşınabilir mi? Kar realizasyonu için hangi (BOS/Fibonacci/EMA8/EMA13) seviyesi beklenebilir? "etmeli" "yapmalı" gibi emir kipleri ile konuşma. "edilebilir" "yapılabilir" gibi konuş.
   - İzsüren Stop (Trailing Stop): Stop seviyesi nereye yükseltilebilir?
3. SENARYO B: ELİNDE OLMAYANLAR İÇİN 
   - Yöntem: [ALINABİLİR / GERİ ÇEKİLME BEKLENEBİLİR / UZAK DURULMASI İYİ OLUR]
   - Risk/Ödül Analizi: Şu an girmek finansal açıdan olumlu mu? yoksa "FOMO" (Tepeden alma) riski taşıyabilir mi? Fiyat çok mu şişkin yoksa çok mu ucuz??
   - İdeal Giriş: Güvenli alım için fiyatın hangi seviyeye (FVG/Destek/EMA8/EMA13/SMA20) gelmesi beklenebilir? "etmeli" "yapmalı" gibi emir kipleri ile konuşma. "edilebilir" "yapılabilir" gibi konuş.
4. UYARI: Eğer RSI pozitif-negatif uyumsuzluğu, Hacim düşüklüğü, stopping volume, Trend tersliği, Ayı-Boğa Tuzağı, gizlisatışlar (satış işareti olan tekli-ikili-üçlü mumlar) vb varsa büyük harflerle uyar. Analizin sonuna daima büyük ve kalın harflerle "YATIRIM TAVSİYESİ DEĞİLDİR  " ve onun da altına " #SmartMoneyRadar #{t}" yaz.
"""
    with st.sidebar:
        st.code(prompt, language="text")
        st.success("Prompt Güncellendi")
    
    st.session_state.generate_prompt = False

info = fetch_stock_info(st.session_state.ticker)

col_left, col_right = st.columns([4, 1])

# --- SOL SÜTUN ---
with col_left:
    synth_data = calculate_synthetic_sentiment(st.session_state.ticker)
    if synth_data is not None and not synth_data.empty: render_synthetic_sentiment_panel(synth_data)
    render_detail_card_advanced(st.session_state.ticker)

    # --- YENİ SADE ANA SKOR KARTI (ESTETİK & KOMPAKT) ---
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    
    # 1. SKOR HESAPLA
    master_score, score_pros, score_cons = calculate_master_score(st.session_state.ticker)

    # 2. DERECELENDİRME
    if master_score >= 85: grade="A+ (MÜKEMMEL)"; score_color="#15803d"; icon="🏆"
    elif master_score >= 70: grade="B (GÜÇLÜ)"; score_color="#0369a1"; icon="💎"
    elif master_score >= 50: grade="C (NÖTR)"; score_color="#b45309"; icon="⚖️"
    else: grade="D (ZAYIF)"; score_color="#b91c1c"; icon="⚠️"

    # 3. BAŞLIK KARTI (Gelişmiş Teknik Kart ile Aynı Stil)
    display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")
    
    st.markdown(f"""
    <div class="info-card" style="border-top: 3px solid {score_color}; margin-bottom: 5px;">
        <div class="info-header" style="display:flex; justify-content:space-between; align-items:center; border-bottom:none; margin-bottom:0; padding-bottom:0;">
            <span style="color:{score_color}; font-size: 0.9rem;">⚖️ ANA SKOR: {display_ticker}</span>
            <span style="font-weight:700; font-size:0.85rem; background:{score_color}15; color:{score_color}; padding:2px 8px; border-radius:4px;">
            {master_score} - {grade.split(' ')[0]}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 4. NEDENLER (İKİ SÜTUN: SOL POZİTİF / SAĞ NEGATİF)
    c_pros, c_cons = st.columns(2)

    # --- Sol Sütun: Pozitifler (Yeşil Kutu) ---
    with c_pros:
        if score_pros:
            # 1. LİMİTLEME: En fazla 10 madde göster
            limited_pros = score_pros[:12]
            
            html_pros = ""
            for p in limited_pros:
                # 'break-inside: avoid-column' maddelerin sütun arasında bölünmesini engeller
                html_pros += f"<div style='font-size:0.75rem; color:#14532d; margin-bottom:3px; break-inside: avoid-column;'>✅ {p}</div>"
            
            st.markdown(f"""
            <div style="background:#f0fdf4; padding:8px; border-radius:6px; border:1px solid #bbf7d0; height:100%;">
                <div style="font-size:0.75rem; font-weight:700; color:#166534; margin-bottom:5px; border-bottom:1px solid #bbf7d0; padding-bottom:2px;">POZİTİF ETKENLER ({len(limited_pros)})</div>
                <div style="column-count: 2; column-gap: 15px;">
                    {html_pros}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Belirgin pozitif etken yok.")

    # --- Sağ Sütun: Negatifler (Kırmızı Kutu) ---
    with c_cons:
        if score_cons:
            # 1. LİMİTLEME: En fazla 10 madde göster
            limited_cons = score_cons[:12]
            
            html_cons = ""
            for c in limited_cons:
                html_cons += f"<div style='font-size:0.75rem; color:#7f1d1d; margin-bottom:3px; break-inside: avoid-column;'>❌ {c}</div>"
            
            st.markdown(f"""
            <div style="background:#fef2f2; padding:8px; border-radius:6px; border:1px solid #fecaca; height:100%;">
                <div style="font-size:0.75rem; font-weight:700; color:#991b1b; margin-bottom:5px; border-bottom:1px solid #fecaca; padding-bottom:2px;">NEGATİF ETKENLER ({len(limited_cons)})</div>
                <div style="column-count: 2; column-gap: 15px;">
                    {html_cons}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.success("Belirgin negatif etken yok.")

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
                    with st.container(height=300):
                        for i, row in longs.iterrows():
                            sym = row['Sembol']
                            # Etiket: 🐂 THYAO (300.0) | Hedef: Yukarı
                            label = f"🐂 {sym} ({row['Fiyat']:.2f}) | {row['Durum']}"
                            if st.button(label, key=f"ict_long_{sym}_{i}", use_container_width=True, help=f"Stop Loss: {row['Stop_Loss']}"):
                                on_scan_result_click(sym)
                                st.rerun()
                else:
                    st.info("Long yönlü kurumsal kurulum yok.")

            # --- SAĞ SÜTUN: SHORT FIRSATLARI ---
            with c_short:
                st.markdown(f"<div style='text-align:center; color:#dc2626; font-weight:800; background:#fef2f2; padding:5px; border-radius:5px; border:1px solid #fca5a5; margin-bottom:10px;'>🐻 SHORT (Düşüş) SETUPLARI ({len(shorts)})</div>", unsafe_allow_html=True)
                if not shorts.empty:
                    with st.container(height=300):
                        for i, row in shorts.iterrows():
                            sym = row['Sembol']
                            # Etiket: 🐻 GARAN (100.0) | Hedef: Aşağı
                            label = f"🐻 {sym} ({row['Fiyat']:.2f}) | {row['Durum']}"
                            if st.button(label, key=f"ict_short_{sym}_{i}", use_container_width=True, help=f"Stop Loss: {row['Stop_Loss']}"):
                                on_scan_result_click(sym)
                                st.rerun()
                else:
                    st.info("Short yönlü kurumsal kurulum yok.")
                    
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
                    label = f"{icon} {sym} ({row['Fiyat']:.2f}) | Alpha(5G): +%{alpha_5:.1f} | Vol: {vol:.1f}x ||| Bugün: %{degisim_1:.1f} ({today_status})"
                    
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
            st.markdown("<div style='text-align:center; color:#1e40af; font-weight:700; font-size:0.9rem; margin-bottom:5px;'>⚡ STP KESİŞİM</div>", unsafe_allow_html=True)
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
            st.markdown("<div style='text-align:center; color:#15803d; font-weight:700; font-size:0.8rem; margin-bottom:5px;'>✅ STP TREND</div>", unsafe_allow_html=True)
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
                        btn_label = f"{icon} {row['Sembol']} ({row['Fiyat']}) | {q_tag} | {rs_short}"
                        
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
                        btn_label = f"🔻 {sym} ({row['Fiyat']:.2f}) | RSI: {row['RSI']}"
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
                        btn_label = f"✅ {sym} ({row['Fiyat']:.2f}) | RSI: {row['RSI']}"
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
                    
                    label = f"{icon} {sym} ({row['Fiyat']:.2f}) | {pat}"
                    
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
                    label = f"🪤 {sym} ({row['Fiyat']:.2f}) | {row['Zaman']} | Vol: {row['Hacim_Kat']}"
                    
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
    
    # 1. Fiyat
    if info and info.get('price'):
        display_ticker = st.session_state.ticker.replace(".IS", "").replace("=F", "")
        cls = "delta-pos" if info['change_pct'] >= 0 else "delta-neg"
        st.markdown(f'<div class="stat-box-small" style="margin-bottom:10px;"><p class="stat-label-small">FİYAT: {display_ticker}</p><p class="stat-value-small money-text">{info["price"]:.2f}<span class="stat-delta-small {cls}">{"+" if info["change_pct"]>=0 else ""}{info["change_pct"]:.2f}%</span></p></div>', unsafe_allow_html=True)
    else: st.warning("Fiyat verisi alınamadı.")

    # 2. Price Action Paneli
    render_price_action_panel(st.session_state.ticker)
    
    # 3. Kritik Seviyeler
    render_levels_card(st.session_state.ticker)
    
    # 🦅 YENİ: ICT SNIPER ONAY RAPORU (Sadece Setup Varsa Çıkar)
    render_ict_certification_card(st.session_state.ticker)

    # 4. ICT Paneli
    render_ict_deep_panel(st.session_state.ticker)
   
    # ==============================================================================
    # YENİ: DİPTEN DÖNÜŞ PANELİ (AYI TUZAĞI + POZİTİF UYUMSUZLUK KESİŞİMİ)
    # ==============================================================================
    
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
                'Zaman': row_bt['Zaman'],      # Örn: 2 Mum Önce
                'RSI': int(row_div['RSI']) # Örn: 28
            })
            
    # 3. UI Çizimi (Turkuaz/Cyan Tasarım)
    st.markdown(f"""
    <div style="background: linear-gradient(45deg, #06b6d4, #3b82f6); color: white; padding: 8px; border-radius: 6px; text-align: center; font-weight: 700; font-size: 0.9rem; margin-bottom: 10px; margin-top: 15px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
        ⚓ DİPTEN DÖNÜŞ?
    </div>
    """, unsafe_allow_html=True)
    
    with st.container(height=150):
        if reversal_list:
            # Fiyata göre sıralayalım (veya istersen RSI'a göre)
            reversal_list.sort(key=lambda x: x['RSI']) 
            
            for item in reversal_list:
                # Buton Etiketi: 💎 GARAN (150.20) | RSI:28 | 2 Mum Önce
                label = f"💎 {item['Sembol']} ({item['Fiyat']:.2f}) | RSI:{item['RSI']} | {item['Zaman']}"
                
                if st.button(label, key=f"rev_btn_{item['Sembol']}", use_container_width=True):
                    on_scan_result_click(item['Sembol'])
                    st.rerun()
        else:
            if not (has_bt and has_div):
                st.caption("'Ayı Tuzağı' ve 'RSI Uyumsuzluk' taramalarının ortak sonuçları burada gösterilir.")
            else:
                st.info("Şu an hem tuzağa düşürüp hem uyumsuzluk veren (Kesişim) hisse yok.")
 
    st.markdown("<hr style='margin-top:15px; margin-bottom:10px;'>", unsafe_allow_html=True)

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
