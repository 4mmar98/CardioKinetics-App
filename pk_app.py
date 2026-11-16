import streamlit as st
import pandas as pd
import numpy as np
import os
import math
import re
import io
import datetime
import plotly.graph_objects as go

st.set_page_config(page_title="Cardiokinetics", layout="wide", page_icon="💊")

import urllib.parse
import streamlit.components.v1 as components

# ── CONTACT ──
# Feedback from the Contact page is addressed here. Replace with your university email.
CONTACT_EMAIL = "maa117@leicester.ac.uk"

PAGES = ["Home", "Table View", "Drugs by Class", "Individual Drug View",
         "PK Calculator", "PK Graph", "About", "Contact"]
PAGE_ICONS = {"Home": "🏠", "Table View": "📊", "Drugs by Class": "🏷️",
              "Individual Drug View": "💊", "PK Calculator": "🧮", "PK Graph": "📈",
              "About": "ℹ️", "Contact": "✉️"}
NAV_SHORT = {"Home": "Home", "Table View": "Table", "Drugs by Class": "Classes",
             "Individual Drug View": "Profile", "PK Calculator": "Calculator",
             "PK Graph": "PK Graph", "About": "About", "Contact": "Contact"}


def slug(v):
    return re.sub(r"[^a-z0-9]+", "_", v.lower()).strip("_")


def hex_rgba(h, a):
    h = h.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"

if 'theme' not in st.session_state:
    st.session_state.theme = "day"
if 'current_view' not in st.session_state:
    st.session_state.current_view = "Home"
IS_NIGHT = st.session_state.theme == "night"

# ── THEME PALETTE ──
if IS_NIGHT:
    BG_MAIN = "#0F172A"
    BG_CARD = "#1E293B"
    BG_INPUT = "#1E293B"
    BORDER = "#334155"
    TEXT_PRIMARY = "#F1F5F9"
    TEXT_SECONDARY = "#94A3B8"
    CHART_BG = "#1E293B"
    CHART_GRID = "#334155"
    CHART_AXIS = "#CBD5E1"
    HEADING = "#38BDF8"
    NAV_LOGO = "#38BDF8"
    BTN_BG_START = "#1D4ED8"
    BTN_BG_END = "#0891B2"
    BTN_TEXT = "#FFFFFF"
    BTN_SHADOW = "rgba(29,78,216,0.3)"
else:
    BG_MAIN = "#F0F6FC"
    BG_CARD = "#FFFFFF"
    BG_INPUT = "#FFFFFF"
    BORDER = "#D0DCE8"
    TEXT_PRIMARY = "#1A1A2E"
    TEXT_SECONDARY = "#4A5568"
    CHART_BG = "#F8FAFC"
    CHART_GRID = "#D0DCE8"
    CHART_AXIS = "#0C2340"
    HEADING = "#1A6ED8"
    NAV_LOGO = "#1A6ED8"
    BTN_BG_START = "#2563EB"
    BTN_BG_END = "#0EA5E9"
    BTN_TEXT = "#FFFFFF"
    BTN_SHADOW = "rgba(37,99,235,0.2)"

NAVY = "#0C2340"
BLUE = "#0077B6"
TEAL = "#00B4D8"
DARK_TEAL = "#0E8AAB"
SUCCESS = "#059669"
WARNING = "#D97706"
DANGER = "#DC2626"
CORAL = "#E8634A"
PURPLE = "#7C3AED"
BRIGHT = HEADING

CLASS_COLOURS = {"ACE Inhibitor": "#2563EB", "ARB": "#7C3AED", "Calcium Channel Blocker": "#DC2626",
                 "Beta Blocker": "#059669", "Diuretic": "#D97706", "Alpha Blocker": "#DB2777",
                 "MRA": "#0891B2", "Centrally Acting": "#0D9488", "Uncategorized": "#6B7280"}


# ── CLASS NAME NORMALISATION ──
# The source spreadsheet contains inconsistent class labels (trailing spaces,
# non-breaking spaces, and long-form vs short-form names). We canonicalise them
# at load time so grouping, colouring and filtering behave consistently. The
# original .xlsx is never modified.
CLASS_CANONICAL = {
    "angiotensin converting enzyme inhibitor": "ACE Inhibitor",
    "ace inhibitor": "ACE Inhibitor",
    "angiotensin receptor blockers": "ARB",
    "angiotensin receptor blocker": "ARB",
    "arb": "ARB",
    "calcium channel blocker": "Calcium Channel Blocker",
    "beta blocker": "Beta Blocker",
    "diuretics": "Diuretic",
    "diuretic": "Diuretic",
    "alpha blocker": "Alpha Blocker",
    "centrally acting": "Centrally Acting",
    "mra": "MRA",
}


def normalise_class(cls):
    if pd.isna(cls):
        return "Uncategorized"
    # collapse non-breaking spaces + trailing/leading whitespace
    key = str(cls).replace("\xa0", " ").strip().lower()
    key = " ".join(key.split())
    return CLASS_CANONICAL.get(key, str(cls).replace("\xa0", " ").strip())


def get_class_colour(cls):
    canon = normalise_class(cls)
    for k, v in CLASS_COLOURS.items():
        if k.lower() == canon.lower():
            return v
    for k, v in CLASS_COLOURS.items():
        if k.lower() in canon.lower():
            return v
    return "#6B7280"


def sig_figs(val, n=3):
    if val == 0 or pd.isna(val):
        return 0.0
    return round(val, -int(math.floor(math.log10(abs(val))))+(n-1))


# ── CSS ──
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    html,body,[class*="css"] {{ font-family:'Inter',-apple-system,sans-serif; color:{TEXT_PRIMARY}; }}
    .stApp {{ background-color:{BG_MAIN}; }}
    .block-container {{ padding:1.5rem 2rem; max-width:100%; }}
    h1 {{ color:{HEADING} !important; font-weight:900; letter-spacing:-1px; font-size:2.8rem !important; }}
    h2 {{ color:{HEADING} !important; font-weight:700; font-size:1.8rem !important; border-bottom:3px solid {TEAL}; padding-bottom:8px; }}
    h3 {{ color:{TEAL} !important; font-weight:600; font-size:1.4rem !important; }}
    [data-testid="stHeading"], [data-testid="stHeading"] h1, [data-testid="stHeading"] h2, [data-testid="stHeading"] h3,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{ color:{HEADING} !important; }}
    .stMarkdown h3 {{ color:{TEAL} !important; }}
    p,li,span,.stMarkdown {{ color:{TEXT_PRIMARY}; }}
    label,.stRadio label,.stCheckbox label,.stSlider label,.stSelectbox label,.stNumberInput label,.stTextInput label {{ color:{TEXT_PRIMARY} !important; }}

    div.stButton > button {{
        background:linear-gradient(135deg,{BTN_BG_START},{BTN_BG_END}) !important;
        color:{BTN_TEXT} !important; font-weight:700; height:56px; font-size:1rem !important;
        border:none !important; border-radius:12px; width:100%;
        box-shadow:0 2px 8px {BTN_SHADOW}; transition:all 0.25s ease;
    }}
    div.stButton > button:hover {{ transform:translateY(-2px); box-shadow:0 6px 20px {BTN_SHADOW}; color:{BTN_TEXT} !important; }}
    div.stButton > button:active {{ transform:translateY(0); color:{BTN_TEXT} !important; }}

    div[data-baseweb="input"] {{ border-radius:10px; border:2px solid {BORDER}; background:{BG_INPUT} !important; }}
    div[data-baseweb="input"]:focus-within {{ border-color:{TEAL}; box-shadow:0 0 0 3px rgba(0,180,216,0.15); }}
    div[data-baseweb="input"] input {{ font-size:1rem; color:{TEXT_PRIMARY} !important; background:{BG_INPUT} !important; -webkit-text-fill-color:{TEXT_PRIMARY} !important; }}
    input[type="number"] {{ color:{TEXT_PRIMARY} !important; background:{BG_INPUT} !important; -webkit-text-fill-color:{TEXT_PRIMARY} !important; }}
    div[data-baseweb="select"] > div {{ border-radius:10px; border:2px solid {BORDER}; background:{BG_INPUT} !important; }}
    div[data-baseweb="select"] div {{ color:{TEXT_PRIMARY} !important; }}
    div[data-baseweb="select"] svg {{ fill:{TEXT_SECONDARY} !important; }}

    div[data-testid="metric-container"], div[data-testid="stMetric"] {{ background:{BG_CARD}; border:1px solid {BORDER}; border-left:4px solid {TEAL}; padding:18px; border-radius:10px; }}
    div[data-testid="metric-container"] label, div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] p {{ color:{TEXT_SECONDARY} !important; font-weight:600; font-size:0.85rem !important; }}
    div[data-testid="metric-container"] div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] {{ color:{HEADING} !important; font-size:1.8rem !important; font-weight:700; }}

    .stTabs [data-baseweb="tab"] {{ height:48px; font-size:0.95rem; background:{BG_CARD}; border:2px solid {BORDER}; border-radius:10px; color:{TEXT_SECONDARY}; font-weight:600; flex-grow:1; }}
    .stTabs [aria-selected="true"] {{ background:linear-gradient(135deg,{BTN_BG_START},{BTN_BG_END}); color:#FFF; border-color:{BTN_BG_START}; }}
    .streamlit-expanderHeader {{ font-weight:600; color:{HEADING}; }}

    .cbox {{ background:{BG_CARD}; border:1px solid {TEAL}; border-left:4px solid {TEAL}; border-radius:10px; padding:16px 20px; margin-top:12px; color:{TEXT_PRIMARY}; }}
    .cbox-w {{ background:{BG_CARD}; border:1px solid {WARNING}; border-left:4px solid {WARNING}; border-radius:10px; padding:16px 20px; margin-top:12px; color:{TEXT_PRIMARY}; }}
    .cbox-d {{ background:{BG_CARD}; border:1px solid {DANGER}; border-left:4px solid {DANGER}; border-radius:10px; padding:16px 20px; margin-top:12px; color:{TEXT_PRIMARY}; animation:fadeInUp 0.45s ease; }}

    /* ── Animations & polish ── */
    @keyframes fadeInUp {{ from {{ opacity:0; transform:translateY(12px); }} to {{ opacity:1; transform:translateY(0); }} }}
    @keyframes floatY {{ 0%,100% {{ transform:translateY(0); }} 50% {{ transform:translateY(-8px); }} }}
    .block-container {{ animation:fadeInUp 0.5s ease; }}
    .cbox {{ animation:fadeInUp 0.45s ease; }}
    .cbox-w {{ animation:fadeInUp 0.45s ease; }}
    .nav-card {{ transition:transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease; }}
    .nav-card:hover {{ transform:translateY(-6px); box-shadow:0 14px 34px rgba(0,0,0,0.16) !important; }}
    .hero-emoji {{ display:inline-block; animation:floatY 3.2s ease-in-out infinite; }}
    div[data-testid="metric-container"], div[data-testid="stMetric"] {{ transition:transform 0.2s ease, box-shadow 0.2s ease; }}
    div[data-testid="metric-container"]:hover, div[data-testid="stMetric"]:hover {{ transform:translateY(-3px); box-shadow:0 8px 22px rgba(0,0,0,0.10); }}
    .pill {{ display:inline-block; padding:4px 14px; border-radius:20px; font-size:0.8rem; font-weight:600; color:#fff; }}
    .live {{ background:linear-gradient(135deg,{BTN_BG_START}22,{BTN_BG_END}22); border:1px solid {TEAL}; border-radius:12px; padding:18px 22px; margin-top:10px; color:{TEXT_PRIMARY}; font-size:1.05rem; animation:fadeInUp 0.35s ease; }}
    .live .big {{ font-size:1.9rem; font-weight:800; color:{HEADING}; letter-spacing:-0.5px; }}
    .live .sub {{ color:{TEXT_SECONDARY}; font-size:0.85rem; }}
</style>
""", unsafe_allow_html=True)

# ── CSS: visual upgrade (hero, glass cards, nav pills, contact, footer) ──
st.markdown(f"""
<style>
    .stApp {{ background:
        radial-gradient(1100px 560px at 8% -12%, {BTN_BG_START}22, transparent 60%),
        radial-gradient(900px 520px at 108% 6%, {BTN_BG_END}22, transparent 60%),
        {BG_MAIN} !important; background-attachment:fixed !important; }}
    div.stButton > button *, div.stLinkButton a *, div.stFormSubmitButton button *, .stTabs [aria-selected="true"] * {{ color:inherit !important; }}
    .stTabs [aria-selected="true"] {{ color:#fff !important; }}
    .stat .n span {{ color:#fff !important; }}

    /* hero */
    .hero {{ position:relative; overflow:hidden; border-radius:28px; padding:54px 28px 120px; text-align:center;
        background:linear-gradient(120deg,#0B1F4D,#0E3A8A 35%,#0891B2 70%,#06B6D4); background-size:220% 220%;
        animation:heroShift 14s ease infinite; box-shadow:0 30px 60px -24px rgba(14,58,138,.55); }}
    @keyframes heroShift {{ 0%{{background-position:0% 50%}} 50%{{background-position:100% 50%}} 100%{{background-position:0% 50%}} }}
    .hero::before {{ content:""; position:absolute; inset:0; pointer-events:none; background:
        radial-gradient(circle at 18% 22%, rgba(255,255,255,.20), transparent 38%),
        radial-gradient(circle at 82% 72%, rgba(255,255,255,.12), transparent 42%); }}
    .hero .ecg {{ position:absolute; left:0; bottom:16px; width:100%; height:96px; }}
    .hero .ecg path {{ fill:none; stroke-linecap:round; stroke-linejoin:round; }}
    .hero .ecg .base {{ stroke:rgba(255,255,255,.22); stroke-width:2; }}
    .hero .ecg .pulse {{ stroke:#fff; stroke-width:3; stroke-dasharray:160 840; stroke-dashoffset:1000;
        animation:ecg 3.2s linear infinite; filter:drop-shadow(0 0 6px rgba(255,255,255,.9)); }}
    @keyframes ecg {{ to {{ stroke-dashoffset:0; }} }}
    .hero-kicker {{ position:relative; display:inline-block; padding:6px 14px; border-radius:999px; color:#fff;
        background:rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.3); font-size:.8rem; font-weight:600;
        letter-spacing:.4px; backdrop-filter:blur(6px); }}
    .hero-title {{ position:relative; font-size:clamp(2.6rem,6vw,4.6rem); font-weight:900; letter-spacing:-2px;
        line-height:1.05; margin:16px 0 12px; color:#fff; }}
    .hero-title .grad {{ background:linear-gradient(90deg,#fff 0%,#A5F3FC 50%,#fff 100%); background-size:200% auto;
        -webkit-background-clip:text; background-clip:text; color:transparent; -webkit-text-fill-color:transparent;
        animation:shine 6s linear infinite; }}
    @keyframes shine {{ to {{ background-position:200% center; }} }}
    .hero-pill {{ display:inline-block; animation:floatY 3.2s ease-in-out infinite; }}
    .hero-sub {{ position:relative; color:rgba(255,255,255,.9); font-size:1.12rem; max-width:720px; margin:0 auto; line-height:1.6; }}
    .stats {{ position:relative; display:flex; gap:14px; justify-content:center; flex-wrap:wrap; margin-top:30px; }}
    .stat {{ min-width:128px; padding:14px 18px; border-radius:16px; background:rgba(255,255,255,.12);
        border:1px solid rgba(255,255,255,.26); backdrop-filter:blur(8px); transition:transform .25s, background .25s; }}
    .stat:hover {{ transform:translateY(-4px); background:rgba(255,255,255,.2); }}
    .stat .n {{ font-size:2rem; font-weight:900; color:#fff; line-height:1.1; }}
    .stat .l {{ font-size:.74rem; color:rgba(255,255,255,.88); font-weight:700; text-transform:uppercase; letter-spacing:.7px; }}
    @property --num {{ syntax:'<integer>'; initial-value:0; inherits:false; }}
    .count {{ animation:countUp 1.8s cubic-bezier(.2,.8,.2,1) forwards; counter-reset:num var(--num); }}
    .count::after {{ content:counter(num); }}
    @keyframes countUp {{ from {{ --num:0; }} to {{ --num:var(--target); }} }}

    /* section titles */
    .sec {{ margin:34px 0 14px; }}
    .sec .k {{ font-size:.75rem; font-weight:800; letter-spacing:1.4px; text-transform:uppercase; color:{TEAL}; }}
    .sec .t {{ font-size:1.6rem; font-weight:900; color:{HEADING}; letter-spacing:-.5px; }}

    /* module cards */
    .mod-card {{ position:relative; background:{BG_CARD}d9; backdrop-filter:blur(10px); border:1px solid {BORDER};
        border-radius:20px; padding:26px 16px 18px; text-align:center; min-height:224px; display:flex; flex-direction:column;
        align-items:center; transition:transform .35s cubic-bezier(.2,.8,.2,1), box-shadow .35s, border-color .35s;
        animation:fadeInUp .6s both; }}
    .mod-card:hover {{ transform:translateY(-8px); border-color:var(--c); box-shadow:0 24px 44px -20px var(--c); }}
    .mod-icon {{ width:62px; height:62px; border-radius:18px; display:grid; place-items:center; font-size:1.8rem;
        background:linear-gradient(135deg,var(--c),{BTN_BG_END}); box-shadow:0 12px 24px -12px var(--c);
        margin-bottom:14px; transition:transform .45s cubic-bezier(.2,.8,.2,1); }}
    .mod-card:hover .mod-icon {{ transform:rotate(-8deg) scale(1.1); }}
    .mod-title {{ font-weight:800; font-size:1.05rem; color:{HEADING}; margin-bottom:6px; }}
    .mod-desc {{ font-size:.86rem; color:{TEXT_SECONDARY}; line-height:1.5; }}
    div[class*="st-key-home_"] div.stButton > button {{ background:transparent !important; color:{HEADING} !important;
        border:1.5px solid {BORDER} !important; height:42px !important; box-shadow:none !important; font-size:.9rem !important; }}
    div[class*="st-key-home_"] div.stButton > button:hover {{ background:linear-gradient(135deg,{BTN_BG_START},{BTN_BG_END}) !important;
        color:#fff !important; border-color:transparent !important; }}

    /* top navigation */
    header[data-testid="stHeader"] {{ background:transparent !important; }}
    div.stDownloadButton button, div.stFormSubmitButton button {{ background:linear-gradient(135deg,{BTN_BG_START},{BTN_BG_END}) !important;
        color:#fff !important; border:none !important; border-radius:12px !important; height:48px; font-weight:700 !important;
        transition:transform .2s, box-shadow .2s; }}
    div.stDownloadButton button:hover, div.stFormSubmitButton button:hover {{ transform:translateY(-2px); box-shadow:0 8px 20px -8px {BTN_BG_START}; }}
    div.stDownloadButton button * {{ color:inherit !important; }}
    .brand {{ font-weight:900; letter-spacing:-.6px;
        background:linear-gradient(90deg,{BTN_BG_START},{BTN_BG_END}); -webkit-background-clip:text; background-clip:text;
        color:transparent; -webkit-text-fill-color:transparent; }}
    div[class*="st-key-nav_"] div.stButton button {{ background:{BG_CARD}b3 !important; color:{TEXT_PRIMARY} !important;
        border:1px solid {BORDER} !important; height:46px !important; font-size:.84rem !important; font-weight:600 !important;
        box-shadow:none !important; backdrop-filter:blur(8px); border-radius:999px !important; }}
    div[class*="st-key-nav_"] div.stButton button:hover {{ border-color:{TEAL} !important; color:{HEADING} !important; }}
    div[class*="st-key-theme_"] div.stButton button {{ border-radius:999px !important; height:46px !important; }}

    /* contact */
    .contact-hero {{ border-radius:22px; padding:26px 28px; color:#fff; margin-bottom:18px;
        background:linear-gradient(120deg,{BTN_BG_START},{BTN_BG_END}); box-shadow:0 20px 40px -22px {BTN_BG_START}; }}
    .contact-hero .t {{ font-size:1.6rem; font-weight:900; color:#fff; }}
    .contact-hero .s {{ color:rgba(255,255,255,.9); margin-top:4px; }}
    div[data-testid="stForm"] {{ background:{BG_CARD}d9; border:1px solid {BORDER} !important; border-radius:20px; padding:22px; }}
    textarea {{ color:{TEXT_PRIMARY} !important; -webkit-text-fill-color:{TEXT_PRIMARY} !important; background:{BG_INPUT} !important; }}
    div.stLinkButton a {{ background:linear-gradient(135deg,{BTN_BG_START},{BTN_BG_END}) !important; color:#fff !important;
        border:none !important; border-radius:12px !important; height:52px; font-weight:700 !important; }}
    .cta {{ border-radius:20px; padding:20px 24px; background:{BG_CARD}d9; border:1px dashed {TEAL}; }}
    .cta .t {{ font-weight:800; font-size:1.1rem; color:{HEADING}; }}
    .cta .s {{ color:{TEXT_SECONDARY}; font-size:.9rem; }}
    .chip {{ display:inline-block; margin:4px 6px 4px 0; padding:8px 14px; border-radius:14px; background:{BG_CARD};
        border:1px solid {BORDER}; font-size:.85rem; color:{TEXT_SECONDARY}; }}
    .chip b {{ color:{HEADING}; font-size:1rem; }}
    /* button polish: rounded, shine sweep on hover, press feedback */
    div.stButton > button, div.stDownloadButton button, div.stFormSubmitButton button, div.stLinkButton a {{
        position:relative; overflow:hidden; border-radius:14px !important; letter-spacing:.2px; }}
    div.stButton > button::after, div.stDownloadButton button::after, div.stFormSubmitButton button::after, div.stLinkButton a::after {{
        content:""; position:absolute; top:0; left:-130%; width:55%; height:100%; pointer-events:none;
        background:linear-gradient(100deg,transparent,rgba(255,255,255,.38),transparent); transform:skewX(-20deg);
        transition:left .65s ease; }}
    div.stButton > button:hover::after, div.stDownloadButton button:hover::after,
    div.stFormSubmitButton button:hover::after, div.stLinkButton a:hover::after {{ left:150%; }}
    div.stButton > button:active, div.stDownloadButton button:active, div.stFormSubmitButton button:active {{ transform:scale(.97) !important; }}

    /* calculator page */
    .cg {{ font-size:.72rem; font-weight:800; letter-spacing:1.3px; text-transform:uppercase; color:{TEAL}; margin:6px 0 8px 2px; }}
    div[class*="st-key-calc_"] div.stButton > button {{ background:{BG_CARD} !important; color:{TEXT_PRIMARY} !important;
        border:1px solid {BORDER} !important; height:50px !important; font-size:.9rem !important; font-weight:600 !important;
        box-shadow:0 1px 3px rgba(0,0,0,.05) !important; justify-content:flex-start !important; padding-left:16px !important; }}
    div[class*="st-key-calc_"] div.stButton > button:hover {{ border-color:{TEAL} !important; transform:translateX(3px);
        box-shadow:0 8px 18px -10px {BTN_BG_START} !important; }}
    div[class*="st-key-calc_"] div.stButton > button div {{ justify-content:flex-start !important; }}
    .res {{ position:relative; overflow:hidden; border-radius:24px; padding:26px 28px; color:#fff;
        background:linear-gradient(135deg,{BTN_BG_START},{BTN_BG_END}); box-shadow:0 24px 44px -24px {BTN_BG_START};
        animation:fadeInUp .45s ease; }}
    .res::before {{ content:""; position:absolute; width:220px; height:220px; right:-60px; top:-80px; border-radius:50%;
        background:rgba(255,255,255,.12); }}
    .res::after {{ content:""; position:absolute; width:140px; height:140px; right:60px; bottom:-70px; border-radius:50%;
        background:rgba(255,255,255,.08); }}
    .res .rt {{ position:relative; font-size:.78rem; font-weight:800; letter-spacing:1.2px; text-transform:uppercase; color:rgba(255,255,255,.85); }}
    .res .rv {{ position:relative; font-size:clamp(2.2rem,4vw,3.2rem); font-weight:900; letter-spacing:-1px; color:#fff; line-height:1.15; margin-top:4px; }}
    .res .ru {{ font-size:1.1rem; font-weight:700; margin-left:8px; color:rgba(255,255,255,.9); }}
    .res .rs {{ position:relative; margin-top:6px; color:rgba(255,255,255,.9); font-size:.92rem; }}
    .res .rv span, .res .rt span, .res .rs span {{ color:inherit !important; }}
    .res.warn {{ background:linear-gradient(135deg,#B45309,#F59E0B); }}
    .res.bad {{ background:linear-gradient(135deg,#B91C1C,#F43F5E); }}
    .res.good {{ background:linear-gradient(135deg,#047857,#10B981); }}
    div[data-testid="stButtonGroup"] button {{ background:{BG_CARD} !important; color:{TEXT_PRIMARY} !important;
        border-color:{BORDER} !important; }}
    div[data-testid="stButtonGroup"] button[aria-checked="true"] {{ background:linear-gradient(135deg,{BTN_BG_START},{BTN_BG_END}) !important;
        color:#fff !important; border-color:transparent !important; }}
    div[data-testid="stButtonGroup"] button * {{ color:inherit !important; }}
    div[class*="st-key-nav_"] div.stButton button *, div[class*="st-key-theme_"] div.stButton button * {{ color:inherit !important; }}
    div[class*="st-key-theme_"] div.stButton button {{ background:linear-gradient(135deg,{BTN_BG_START},{BTN_BG_END}) !important;
        color:#fff !important; border:none !important; }}
    .formula {{ background:{BG_CARD}; border:1px solid {BORDER}; border-radius:16px; padding:4px 10px; margin:14px 0 6px; }}
    .foot {{ margin-top:40px; padding-top:16px; border-top:1px solid {BORDER}; color:{TEXT_SECONDARY}; font-size:.82rem; }}
</style>
""", unsafe_allow_html=True)

# ── DATA ──


@st.cache_data
def load_data():
    def clean_header(c):
        o = str(c).strip().replace('\n', ' ')
        if "auc" in o.lower():
            return "Area Under the Curve (AUC) [ng.hr/mL]"
        t = o.title()
        for a, b in [("Ng/Ml", "ng/mL"), ("Ug/Ml", "µg/mL"), ("Mg/L", "mg/L"), ("Ng.Hr/Ml", "ng.hr/mL"), ("Ng*H/Ml", "ng.hr/mL"), ("Ml/Min", "mL/min"), ("L/Min", "L/min"), ("Iv", "IV"), ("Css,Max", "Css,max"), ("Css,Min", "Css,min"), ("Css,Avg", "Css,avg"), ("Lod", "LOD"), ("Det. Window", "Detection Window"), ("R (Accum. Factor)", "Accumulation Factor (R)"), ("(H)", "(h)"), ("(Days)", "(days)")]:
            t = t.replace(a, b)
        return t
    for f in ["top_20_antihypertensive.xlsx", "drug_data.xlsx", "top_20_antihypertensive.csv", "drug_data.csv"]:
        if os.path.exists(f):
            try:
                d = pd.read_csv(f) if f.endswith('.csv') else pd.read_excel(f)
                d = d.rename(
                    columns={"Drug": "Name", "Drug Class": "Class", "Dosage (mg)": "Dose"})
                d.columns = [clean_header(c) for c in d.columns]
                if 'Name' not in d.columns:
                    st.error("Need 'Name' column.")
                    return pd.DataFrame()
                if 'Class' not in d.columns:
                    d['Class'] = "Uncategorized"
                else:
                    d['Class'] = d['Class'].apply(normalise_class)
                return d
            except Exception as e:
                st.error(f"Error: {e}")
                return pd.DataFrame()
    return pd.DataFrame([{"Name": "Lisinopril", "Class": "ACE Inhibitor", "Half-Life": "12h", "Cmax": "40 ng/mL", "Area Under the Curve (AUC) [ng.hr/mL]": "500 ng·h/mL", "Bioavailability": "25%", "Clearance": "50 mL/min"}])


df = load_data()


def extract_numeric(v):
    if pd.isna(v) or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    v = str(v)
    if '±' in v:
        v = v.split('±')[0]
    m = re.search(r"[-+]?\d*\.?\d+", v)
    return float(m.group()) if m else None


def extract_with_sd(v):
    if pd.isna(v) or v == "":
        return None, 0.0
    if isinstance(v, (int, float)):
        return float(v), 0.0
    v = str(v)
    if '±' in v:
        p = v.split('±')
        a = re.search(r"[-+]?\d*\.?\d+", p[0])
        b = re.search(r"[-+]?\d*\.?\d+", p[1])
        return (float(a.group()) if a else None, float(b.group()) if b else 0.0)
    m = re.search(r"[-+]?\d*\.?\d+", v)
    return (float(m.group()), 0.0) if m else (None, 0.0)


def style_fig(fig, h=420, x_title="Time (hours)", y_title="Concentration (ng/mL)"):
    """Apply the Cardiokinetics theme to a Plotly figure and enable rich hover."""
    fig.update_layout(
        height=h,
        margin=dict(l=10, r=10, t=56, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=CHART_BG,
        font=dict(family="Inter, sans-serif", color=CHART_AXIS, size=13),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=BG_CARD, bordercolor=BORDER,
                        font=dict(color=TEXT_PRIMARY, family="Inter, sans-serif")),
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left",
                    x=0, bgcolor="rgba(0,0,0,0)", font=dict(color=CHART_AXIS)),
        transition=dict(duration=350, easing="cubic-in-out"),
        dragmode="pan",
    )
    fig.update_xaxes(title_text=x_title, gridcolor=CHART_GRID, zeroline=False,
                     linecolor=BORDER, tickcolor=CHART_AXIS, color=CHART_AXIS)
    fig.update_yaxes(title_text=y_title, gridcolor=CHART_GRID, zeroline=False,
                     linecolor=BORDER, tickcolor=CHART_AXIS, color=CHART_AXIS)
    return fig


PLOTLY_CONFIG = {"displayModeBar": True, "scrollZoom": True, "displaylogo": False,
                 "modeBarButtonsToRemove": ["select2d", "lasso2d"]}


def live_box(label, big, sub=""):
    """Render a live, auto-updating result card for the calculators."""
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="live"><div class="sub">{label}</div><div class="big">{big}</div>{sub_html}</div>',
        unsafe_allow_html=True)


def add_cmax_ref(fig, value, label, color, position="top left"):
    """Draw a horizontal Cmax reference line with a label on a Plotly figure."""
    if value and value > 0:
        tag = f"Cmax {label}".strip()
        fig.add_hline(y=value, line=dict(color=color, width=1.5, dash="dot"),
                      annotation_text=f"{tag} = {value:.1f}",
                      annotation_position=position, annotation_font_color=color)


def add_det_window(fig, value, gmax, label, color):
    """Draw a vertical detection-window line if the value falls within the visible range."""
    if value and 0 < value <= gmax:
        txt = "Detection window" if not label else f"Det. window · {label}"
        fig.add_vline(x=value, line=dict(color=color, width=2, dash="dot"),
                      annotation_text=txt, annotation_position="top",
                      annotation_font_color=color)


def det_window_h(c0, thalf, lod):
    """Hours for a one-compartment curve starting at c0 to fall to the LoD.
    Uses the same k = 0.693 / t½ as the plotted curves, so the line always
    meets the curve exactly at the LoD."""
    try:
        if c0 and thalf and lod and thalf > 0 and lod > 0 and c0 > lod:
            return math.log(c0 / lod) * thalf / 0.693
    except (TypeError, ValueError):
        pass
    return None


def render_det_caption(ph, items, offscreen_hint):
    """Fill the left-column placeholder with the detection window(s) actually drawn."""
    if not items:
        ph.caption("🔴 Detection window: needs a Cmax, a half-life and an LoD above zero.")
        return
    parts, off = [], False
    for lbl, h, visible in items:
        if h is None:
            parts.append(f"{lbl}: Cmax at or below LoD, or no LoD")
        else:
            parts.append(f"{lbl}: ~{h:.0f} h ({h/24:.1f} days)")
            off = off or not visible
    txt = "🔴 Detection window · " + " · ".join(parts) + "."
    if off:
        txt += " " + offscreen_hint
    ph.caption(txt)


def get_drug_params(row):
    p = {}
    cc = [c for c in df.columns if "cmax" in c.lower(
    ) and "css" not in c.lower() and "single" not in c.lower()]
    p['cmax'], p['cmax_sd'] = extract_with_sd(
        row[cc[0]]) if cc else extract_with_sd(row.get("Cmax", None))
    tc = [c for c in df.columns if "half" in c.lower()]
    p['thalf'] = extract_numeric(row[tc[0]]) if tc else None
    ac = [c for c in df.columns if "auc" in c.lower()]
    p['auc'] = extract_numeric(row[ac[0]]) if ac else None
    for tag, kw in [('css_max', [("css,max",), ("css", "max")]), ('css_min', [("css,min",), ("css", "min")]), ('css_avg', [("css,avg",), ("css", "avg")])]:
        cols = []
        for ks in kw:
            cols = [c for c in df.columns if all(k in c.lower() for k in ks)]
            if cols:
                break
        p[tag] = extract_numeric(row[cols[0]]) if cols else None
    sc = [c for c in df.columns if "single" in c.lower() and "cmax" in c.lower()]
    p['sd_cmax'] = extract_numeric(row[sc[0]]) if sc else p['cmax']
    lc = [c for c in df.columns if "lod" in c.lower()]
    p['lod'] = extract_numeric(row[lc[0]]) if lc else None
    dc = [c for c in df.columns if "window" in c.lower() and "(h)" in c.lower()]
    p['det_window'] = extract_numeric(row[dc[0]]) if dc else None
    dd = [c for c in df.columns if "window" in c.lower() and "days" in c.lower()]
    p['det_window_days'] = extract_numeric(row[dd[0]]) if dd else None
    return p


line_colour = TEAL if IS_NIGHT else NAVY

# ── SCIENTIFIC CALCULATOR (runs in the browser) ──
SCI_CALC_HTML = r"""
<style>
  * {{ box-sizing:border-box; font-family:Inter,-apple-system,system-ui,sans-serif; }}
  body {{ margin:0; background:transparent; }}
  .calc {{ background:{card}; border:1px solid {border}; border-radius:24px; padding:16px; box-shadow:0 20px 40px -24px {a}; }}
  .screen {{ background:{screen}; border-radius:16px; padding:14px 16px; margin-bottom:14px; min-height:96px;
            display:flex; flex-direction:column; justify-content:flex-end; align-items:flex-end; overflow:hidden; }}
  .expr {{ color:#94A3B8; font-size:15px; min-height:20px; word-break:break-all; text-align:right; }}
  .out {{ color:#fff; font-size:34px; font-weight:800; letter-spacing:-.5px; word-break:break-all; text-align:right; }}
  .out.err {{ color:#F87171; font-size:20px; }}
  .grid {{ display:grid; grid-template-columns:repeat(5,1fr); gap:8px; }}
  button {{ border:none; border-radius:14px; height:50px; font-size:17px; font-weight:600; cursor:pointer;
           background:{key}; color:{text}; transition:transform .08s, background .15s, box-shadow .15s; }}
  button:hover {{ background:{keyh}; }}
  button:active, button.flash {{ transform:scale(.94); }}
  .fn {{ font-size:14px; color:{fn}; font-weight:700; }}
  .op {{ background:linear-gradient(135deg,{a},{b}); color:#fff; }}
  .op:hover {{ filter:brightness(1.08); background:linear-gradient(135deg,{a},{b}); }}
  .eq {{ background:linear-gradient(135deg,#059669,#10B981); color:#fff; grid-row:span 2; height:auto; font-size:22px; }}
  .clr {{ color:#EF4444; font-weight:800; }}
  .hist {{ margin-top:12px; font-size:13px; color:{muted}; max-height:74px; overflow:auto; }}
  .hist div {{ padding:3px 6px; border-radius:8px; cursor:pointer; display:flex; justify-content:space-between; }}
  .hist div:hover {{ background:{key}; }}
  .hist b {{ color:{text}; }}
</style>
<div class="calc">
  <div class="screen"><div class="expr" id="ex"></div><div class="out" id="out">0</div></div>
  <div class="grid">
    <button class="fn" data-i="ln(">ln</button><button class="fn" data-i="log(">log</button>
    <button class="fn" data-i="exp(">eˣ</button><button class="fn" data-i="^">xʸ</button><button class="fn" data-i="√(">√</button>
    <button class="fn" data-i="ln2">ln2</button><button class="fn" data-i="π">π</button>
    <button class="fn" data-i="(">(</button><button class="fn" data-i=")">)</button><button class="clr" data-a="C">AC</button>
    <button data-i="7">7</button><button data-i="8">8</button><button data-i="9">9</button>
    <button class="op" data-i="÷">÷</button><button data-a="back">⌫</button>
    <button data-i="4">4</button><button data-i="5">5</button><button data-i="6">6</button>
    <button class="op" data-i="×">×</button><button class="fn" data-i="Ans">Ans</button>
    <button data-i="1">1</button><button data-i="2">2</button><button data-i="3">3</button>
    <button class="op" data-i="−">−</button><button class="eq" data-a="eq">=</button>
    <button data-i="0">0</button><button data-i=".">.</button><button class="fn" data-i="E">EXP</button>
    <button class="op" data-i="+">+</button>
  </div>
  <div class="hist" id="hist"></div>
</div>
<script>
  let expr = "", ans = 0, justDone = false;
  const ex = document.getElementById("ex"), out = document.getElementById("out"), hist = document.getElementById("hist");
  const fmt = v => {{ if (!isFinite(v)) throw 0; const a = Math.abs(v);
    return (a !== 0 && (a >= 1e10 || a < 1e-6)) ? v.toExponential(6).replace(/\.?0+e/, "e") : String(+v.toPrecision(10)); }};
  function toJS(s) {{
    let j = s.replace(/×/g,"*").replace(/÷/g,"/").replace(/−/g,"-").replace(/\^/g,"**")
      .replace(/ln2/g,"(Math.LN2)").replace(/log\(/g,"Math.log10(").replace(/ln\(/g,"Math.log(")
      .replace(/exp\(/g,"Math.exp(").replace(/√\(/g,"Math.sqrt(").replace(/π/g,"(Math.PI)")
      .replace(/Ans/g,"("+ans+")").replace(/(\d|\))E(-?\d)/g,"$1e$2");
    const check = j.replace(/Math\.(log10|log|exp|sqrt|PI|LN2)/g,"").replace(/\d+(\.\d+)?e-?\d+/g,"0");
    if (/[^0-9+\-*/().\s]/.test(check)) throw 0;
    return j;
  }}
  function preview() {{
    ex.textContent = expr;
    if (!expr) {{ out.textContent = "0"; out.className = "out"; return; }}
    try {{ const v = Function("return (" + toJS(expr) + ")")(); out.textContent = fmt(v); out.className = "out"; }}
    catch (e) {{ /* keep last good preview while typing */ }}
  }}
  function press(i, a) {{
    if (a === "C") {{ expr = ""; }}
    else if (a === "back") {{ expr = expr.replace(/(ln\(|log\(|exp\(|√\(|ln2|Ans|.)$/, ""); }}
    else if (a === "eq") {{
      if (!expr) return;
      try {{ const v = Function("return (" + toJS(expr) + ")")(); const r = fmt(v);
        const row = document.createElement("div"); row.innerHTML = "<span>" + expr + "</span><b>" + r + "</b>";
        row.onclick = () => {{ expr += r; justDone = false; preview(); }};
        hist.prepend(row); ans = v; ex.textContent = expr + " ="; out.textContent = r; out.className = "out";
        expr = ""; justDone = true; return; }}
      catch (e) {{ out.textContent = "Check the expression"; out.className = "out err"; return; }}
    }}
    else {{
      if (justDone && /^[0-9.(π√lne]/.test(i)) expr = "";
      if (justDone && /^[+×÷−^]/.test(i)) expr = "Ans";
      expr += i;
    }}
    justDone = false; preview();
  }}
  document.querySelectorAll("button").forEach(b => b.addEventListener("click", () => press(b.dataset.i, b.dataset.a)));
  const keymap = {{"*":"×","/":"÷","-":"−","+":"+","^":"^","(":"(",")":")",".":".",",":"."}};
  document.addEventListener("keydown", e => {{
    let i = null, a = null;
    if (/^[0-9]$/.test(e.key)) i = e.key; else if (keymap[e.key]) i = keymap[e.key];
    else if (e.key === "Enter" || e.key === "=") a = "eq"; else if (e.key === "Backspace") a = "back";
    else if (e.key === "Escape" || e.key === "Delete") a = "C"; else return;
    e.preventDefault(); press(i, a);
  }});
</script>
"""

# ── NAV ──


def nav_to(v):
    st.session_state.current_view = v
    st.rerun()


view = st.session_state.current_view

if view != "Home":
    st.markdown(
        f"<style>div.st-key-nav_{slug(view)} div.stButton button {{ background:linear-gradient(135deg,{BTN_BG_START},{BTN_BG_END}) !important;"
        f" color:#fff !important; border-color:transparent !important; box-shadow:0 8px 20px -8px {BTN_BG_START} !important; }}</style>",
        unsafe_allow_html=True)
    nl, nm, nr = st.columns([2, 9, 1])
    with nl:
        st.markdown('<div style="font-size:1.55rem;padding:4px 0 6px;">💊 <span class="brand">Cardiokinetics</span></div>', unsafe_allow_html=True)
        search_term = st.text_input(
            "Search", placeholder="Search by Drug Name or Class...", label_visibility="collapsed")
    with nm:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        cs = st.columns(len(PAGES), gap="small")
        for c, v in zip(cs, PAGES):
            with c:
                if st.button(f"{PAGE_ICONS[v]} {NAV_SHORT[v]}", key=f"nav_{slug(v)}", width='stretch', help=v):
                    nav_to(v)
    with nr:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("☀️" if IS_NIGHT else "🌙", key="theme_top", width='stretch',
                     help="Switch day / night mode"):
            st.session_state.theme = "day" if IS_NIGHT else "night"
            st.rerun()
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
else:
    search_term = ""

# ══════════════════════════════════════════════
#  HOME
# ══════════════════════════════════════════════
if view == "Home":
    _, tc = st.columns([9, 1])
    with tc:
        if st.button("☀️ Day" if IS_NIGHT else "🌙 Night", key="theme_home"):
            st.session_state.theme = "day" if IS_NIGHT else "night"
            st.rerun()
    n_agents = df['Name'].nunique() if not df.empty else 0
    n_classes = df['Class'].nunique() if not df.empty else 0
    n_records = len(df)
    ecg = ("M0 60 H140 L160 60 L172 48 L184 60 H220 L232 60 L244 14 L258 104 L270 40 L282 60 H330 "
           "L352 60 Q366 34 380 60 H520 L540 60 L552 48 L564 60 H600 L612 60 L624 14 L638 104 L650 40 L662 60 H710 "
           "L732 60 Q746 34 760 60 H900 L920 60 L932 48 L944 60 H980 L992 60 L1004 14 L1018 104 L1030 40 L1042 60 H1090 "
           "L1112 60 Q1126 34 1140 60 H1200")
    stats = [(n_agents, "Agents"), (n_classes, "Classes"), (n_records, "Dose records"),
             (12, "Calculators"), (5, "Graph modes")]
    stat_html = "".join(
        f'<div class="stat"><div class="n"><span class="count" style="--target:{n}"></span></div><div class="l">{l}</div></div>'
        for n, l in stats)
    st.markdown(
        '<div class="hero">'
        '<svg class="ecg" viewBox="0 0 1200 120" preserveAspectRatio="none">'
        f'<path class="base" d="{ecg}"/><path class="pulse" pathLength="1000" d="{ecg}"/></svg>'
        '<div class="hero-title"><span class="hero-pill">💊</span> <span class="grad">Cardiokinetics</span></div>'
        '<div class="hero-sub">A digital pharmacokinetic decision-support system for interpreting '
        'therapeutic drug monitoring in hypertension</div>'
        f'<div class="stats">{stat_html}</div>'
        '</div>', unsafe_allow_html=True)

    st.markdown('<div class="sec"><div class="k">Modules</div><div class="t">Where do you want to start?</div></div>',
                unsafe_allow_html=True)
    cards = [("📊", "Table View", "Browse the complete PK database with search and filtering", BLUE),
             ("🏷️", "Drugs by Class", "Explore agents grouped by therapeutic class", PURPLE),
             ("💊", "Individual Drug View", "Full pharmacokinetic profile card for any agent", DARK_TEAL),
             ("🧮", "PK Calculator", "Twelve live-updating calculators plus a therapeutic-window gauge", SUCCESS),
             ("📈", "PK Graph", "Elimination curves, drug comparison, multi-drug screen, TDM overlay", CORAL),
             ("ℹ️", "About", "How to use Cardiokinetics and what each module does", "#64748B")]
    cs = st.columns(6, gap="medium")
    for i, (ic, lb, ds, cl) in enumerate(cards):
        with cs[i]:
            st.markdown(
                f'<div class="mod-card" style="--c:{cl};animation-delay:{i*0.07:.2f}s">'
                f'<div class="mod-icon">{ic}</div><div class="mod-title">{lb}</div>'
                f'<div class="mod-desc">{ds}</div></div>', unsafe_allow_html=True)
            if st.button("Open →", key=f"home_{slug(lb)}", width='stretch'):
                nav_to(lb)

    # ── Explore the database ──
    if not df.empty:
        st.markdown('<div class="sec"><div class="k">Interactive</div><div class="t">Explore the database</div></div>',
                    unsafe_allow_html=True)
        dose_cols = [c for c in df.columns if any(kw in c.lower() for kw in ['dose', 'strength', 'mg'])]
        dose_col = dose_cols[0] if dose_cols else None

        def _lbl(r):
            nm = str(r['Name']).replace("\xa0", " ").strip()
            if dose_col and pd.notna(r[dose_col]):
                try:
                    return f"{nm} {float(r[dose_col]):g} mg"
                except (TypeError, ValueError):
                    return f"{nm} {r[dose_col]}"
            return nm

        recs = []
        for _, r in df.iterrows():
            pp = get_drug_params(r)
            c0 = pp['sd_cmax'] or pp['cmax']
            dose = None
            if dose_col:
                try:
                    dose = float(r[dose_col])
                except (TypeError, ValueError):
                    dose = None
            recs.append(dict(label=_lbl(r), cls=str(r['Class']), t=pp['thalf'], c=c0,
                             dose=dose, lod=pp['lod']))

        t_map, t_spot, t_cls = st.tabs(["🫧  PK landscape", "🔬  Drug spotlight", "🍩  By class"])

        with t_map:
            pts = [x for x in recs if x['t'] and x['c'] and x['t'] > 0 and x['c'] > 0]
            fig = go.Figure()
            for cls in sorted({x['cls'] for x in pts}):
                g = [x for x in pts if x['cls'] == cls]
                fig.add_trace(go.Scatter(
                    x=[x['t'] for x in g], y=[x['c'] for x in g], mode="markers", name=cls,
                    text=[x['label'] for x in g],
                    customdata=[[x['dose'] or 0] for x in g],
                    marker=dict(size=[10 + 3.2 * math.sqrt(x['dose'] or 1) for x in g],
                                color=get_class_colour(cls), opacity=0.82,
                                line=dict(color="#ffffff", width=1.5)),
                    hovertemplate="<b>%{text}</b><br>t½ = %{x:.1f} h<br>Cmax = %{y:.1f} ng/mL<extra>" + cls + "</extra>"))
            style_fig(fig, h=460, x_title="Half-life (h, log scale)", y_title="Single-dose Cmax (ng/mL, log scale)")
            fig.update_xaxes(type="log")
            fig.update_yaxes(type="log")
            fig.update_layout(hovermode="closest")
            st.plotly_chart(fig, width='stretch', config=PLOTLY_CONFIG)
            st.caption("Each bubble is one drug at one dose; bigger bubble = higher dose. "
                       "Click a class in the legend to hide it, double-click to show only that class. "
                       "Scroll to zoom, drag to pan.")

        with t_spot:
            ok = [x for x in recs if x['t'] and x['c'] and x['t'] > 0 and x['c'] > 0]
            if ok:
                sl, sr = st.columns([1, 2], gap="large")
                with sl:
                    pick = st.selectbox("Pick a drug", [x['label'] for x in ok], key="spot_pick")
                    x = next(r for r in ok if r['label'] == pick)
                    col = get_class_colour(x['cls'])
                    dw = det_window_h(x['c'], x['t'], x['lod'])
                    st.markdown(
                        f'<span class="pill" style="background:{col}">{x["cls"]}</span><br><br>'
                        f'<span class="chip">Half-life<br><b>{x["t"]:.1f} h</b></span>'
                        f'<span class="chip">Cmax<br><b>{x["c"]:.1f} ng/mL</b></span>'
                        f'<span class="chip">Detectable for<br><b>{"~%.0f h" % dw if dw else "n/a"}</b></span>',
                        unsafe_allow_html=True)
                    if st.button("Open in PK Graph →", key="spot_open", width='stretch'):
                        nav_to("PK Graph")
                with sr:
                    tmax = max(5 * x['t'], (dw or 0) * 1.1)
                    tp = np.linspace(0, tmax, 160)
                    yy = x['c'] * np.exp(-(0.693 / x['t']) * tp)
                    f2 = go.Figure(go.Scatter(
                        x=tp, y=yy, mode="lines", fill="tozeroy", name=pick,
                        line=dict(color=col, width=3, shape="spline"), fillcolor=hex_rgba(col, 0.18),
                        hovertemplate="t = %{x:.1f} h<br>C = %{y:.2f} ng/mL<extra></extra>"))
                    if x['lod']:
                        f2.add_hline(y=x['lod'], line=dict(color=WARNING, width=2, dash="dash"),
                                     annotation_text=f"LoD {x['lod']:g}", annotation_position="top right",
                                     annotation_font_color=WARNING)
                    if dw:
                        add_det_window(f2, dw, tmax, "", DANGER)
                    f2.update_layout(showlegend=False)
                    st.plotly_chart(style_fig(f2, h=340), width='stretch', config=PLOTLY_CONFIG)

        with t_cls:
            dl_, dr_ = st.columns([3, 2], gap="large")
            with dl_:
                vc = df.groupby('Class')['Name'].nunique().sort_values(ascending=False)
                donut = go.Figure(go.Pie(
                    labels=vc.index.tolist(), values=vc.values.tolist(), hole=0.62,
                    marker=dict(colors=[get_class_colour(c) for c in vc.index],
                                line=dict(color=BG_MAIN, width=3)),
                    pull=[0.04] * len(vc), textinfo="label+value", textfont=dict(color=TEXT_PRIMARY, size=12),
                    hovertemplate="<b>%{label}</b><br>%{value} agents (%{percent})<extra></extra>", sort=False))
                donut.update_layout(
                    height=360, margin=dict(l=0, r=0, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
                    font=dict(family="Inter, sans-serif", color=CHART_AXIS),
                    annotations=[dict(text=f"<b>{n_agents}</b><br>agents", x=0.5, y=0.5,
                                      font=dict(size=22, color=HEADING), showarrow=False)])
                st.plotly_chart(donut, width='stretch', config={"displayModeBar": False})
            with dr_:
                st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
                m1, m2 = st.columns(2)
                m1.metric("Agents", n_agents)
                m2.metric("Classes", n_classes)
                hl = [x for x in recs if x['t']]
                if hl:
                    lg = max(hl, key=lambda r: r['t'])
                    st.metric("Longest half-life", f"{lg['t']:.1f} h", help=lg['label'])

    # ── Feedback call-to-action ──
    st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
    ca, cb = st.columns([4, 1], vertical_alignment="center")
    with ca:
        st.markdown('<div class="cta"><div class="t">💬 Spotted a problem or have an idea?</div>'
                    '<div class="s">Send feedback straight to the developer. It takes about a minute.</div></div>',
                    unsafe_allow_html=True)
    with cb:
        if st.button("✉️ Contact", key="home_contact", width='stretch'):
            nav_to("Contact")

# ══════════════════════════════════════════════
#  ABOUT / HOW TO USE
# ══════════════════════════════════════════════
elif view == "About":
    st.header("About Cardiokinetics")
    st.markdown(f"""
<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:14px;padding:30px;margin-bottom:20px;color:{TEXT_PRIMARY};">

**Cardiokinetics** is a digital pharmacokinetic decision support system developed as part of a PhD programme at the University of Leicester. It is designed to help clinicians interpret therapeutic drug monitoring (TDM) results in the context of hypertension by providing dynamic, interactive pharmacokinetic simulations.

**⚠️ This is a research tool under active development. It is not validated for clinical use and should not replace clinical judgement.**

</div>

### 📊 Table View
Browse all 20 antihypertensive agents with their complete pharmacokinetic parameters. Use the search bar to filter by drug name or class. Drugs are sorted alphabetically, then by ascending dose.

### 🏷️ Drugs by Class
View agents grouped into their therapeutic classes (ACE Inhibitors, ARBs, CCBs, Beta-Blockers, Diuretics, Alpha-Blockers). Useful for comparing pharmacokinetic properties within a class.

### 💊 Individual Drug View
Select any drug to see its complete parameter card — half-life, Cmax, AUC, bioavailability, clearance, steady-state values, and detection window.

### 🧮 PK Calculator
Twelve automated calculators based on standard one-compartment pharmacokinetic equations:
- **Bioavailability (F)** — from oral and IV AUC/dose data
- **Cmin (Trough)** — predict trough from Cmax, half-life, and dosing interval
- **Clearance** — from dose, bioavailability, and AUC
- **Half-Life ↔ ke** — bidirectional conversion
- **Steady State Simulator** — predict Css,max, Css,min, Css,avg with accumulation graph
- **Therapeutic Window** — select a drug, enter a measured concentration, and the system checks it against the expected range
- **Volume of Distribution (Vd)** — from dose, bioavailability, ke, and AUC
- **Loading Dose** — dose needed to immediately reach a target concentration
- **Maintenance Dose Rate** — dosing rate to sustain a target Css,avg
- **IV Infusion Css** — steady-state concentration from a constant infusion rate
- **Time to Steady State** — estimated time to plateau based on half-life
- **ke (2-point)** — back-calculate elimination rate constant and half-life from two measured TDM concentrations

### 📈 PK Graph
The core clinical module with five visualisation modes:
- **Standard Elimination** — mono-exponential decay curve with LoD overlay, detection window, Quick Point Calculator, and TDM result plotting
- **Accumulation Comparison** — single-dose vs. steady-state curves with computed accumulation factor
- **Steady State Oscillation** — saw-tooth pattern showing concentration oscillation across multiple dosing intervals
- **Drug Comparison** — overlay two drugs' elimination curves on one chart
- **Multi-Drug Screen** — select up to 5 drugs and visualise all their elimination curves with a single LoD threshold

### 🌙 Day / Night Mode
Click the ☀️/🌙 button in the top-right corner to switch between light and dark themes.

### 📥 Downloads & Reports
Most graph modes include a "Download Data (CSV)" button for exporting chart data (rounded to 3 significant figures). The Standard Elimination mode also includes a "Generate Report" button that produces a downloadable clinical summary.
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  CONTACT
# ══════════════════════════════════════════════
elif view == "Contact":
    st.markdown('<div class="contact-hero"><div class="t">✉️ Contact &amp; feedback</div>'
                '<div class="s">Found a bug, a number that looks wrong, or have an idea for a new feature? '
                'Tell me below.</div></div>', unsafe_allow_html=True)
    configured = "@" in CONTACT_EMAIL
    fl, fr = st.columns([3, 2], gap="large")
    with fl:
        with st.form("contact_form", clear_on_submit=False):
            c1, c2 = st.columns(2)
            cf_name = c1.text_input("Your name (optional)")
            cf_reply = c2.text_input("Your email, if you'd like a reply (optional)")
            cf_kind = st.segmented_control(
                "What is it about?", ["💡 Suggestion", "🐞 Problem", "❓ Question", "🙌 Other"],
                default="💡 Suggestion")
            cf_page = st.selectbox("Which part of the app?", ["General"] + [p for p in PAGES if p not in ("Home", "Contact")])
            cf_msg = st.text_area("Message", height=170, max_chars=1500,
                                  placeholder="Describe the suggestion or problem. For a problem, say which drug "
                                              "and settings you used, what you expected, and what happened.")
            cf_send = st.form_submit_button("Prepare email ✉️", width='stretch')
        if cf_send:
            if not cf_msg.strip():
                st.warning("Please write a message first.")
            else:
                kind = (cf_kind or "Feedback").split(" ", 1)[-1]
                subject = f"[Cardiokinetics] {kind}: {cf_page}"
                body = (f"{cf_msg.strip()}\n\n---\nType: {kind}\nArea: {cf_page}\n"
                        f"Name: {cf_name or '-'}\nReply to: {cf_reply or '-'}\n"
                        f"Theme: {st.session_state.theme}\nSent: {datetime.datetime.now():%Y-%m-%d %H:%M}")
                st.session_state.cf_mail = (subject, body)
                st.toast("Email ready. Click the button below to open it.", icon="✉️")
        if st.session_state.get("cf_mail"):
            subject, body = st.session_state.cf_mail
            if configured:
                url = (f"mailto:{CONTACT_EMAIL}?subject={urllib.parse.quote(subject)}"
                       f"&body={urllib.parse.quote(body)}")
                st.link_button("📨 Open in my email app", url, width='stretch')
                st.caption("Your email app opens with everything filled in. Nothing is sent until you press Send there.")
                with st.expander("Email app didn't open?"):
                    st.markdown(f"Send it to **{CONTACT_EMAIL}** with this subject and text:")
                    st.code(f"Subject: {subject}\n\n{body}", language=None)
            else:
                st.info("The contact address hasn't been set up yet. Set CONTACT_EMAIL near the top of pk_app.py.")
    with fr:
        st.markdown(f"""<div class="cbox"><b>What happens next</b><br><br>
1️⃣ Fill in the form and press <b>Prepare email</b>.<br>
2️⃣ Press <b>Open in my email app</b>. Your usual email app opens with the message ready.<br>
3️⃣ Check it and press <b>Send</b>.<br><br>
<span style="color:{TEXT_SECONDARY};font-size:.88rem;">Please don't include any patient-identifiable information.</span></div>""",
                    unsafe_allow_html=True)
        if configured:
            st.markdown(f'<div class="cbox">📮 Or email directly: <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></div>',
                        unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  TABLE VIEW
# ══════════════════════════════════════════════
elif view == "Table View":
    if not df.empty:
        filt = df[df['Name'].astype(str).str.contains(search_term, case=False) | df['Class'].astype(
            str).str.contains(search_term, case=False)] if search_term else df.copy()
        dose_cols = [c for c in filt.columns if any(
            kw in c.lower() for kw in ['dose', 'strength', 'mg'])]
        if dose_cols:
            filt['_sd'] = filt[dose_cols[0]].apply(extract_numeric).fillna(0)
            filt = filt.sort_values(['Name', '_sd'], ascending=[
                                    True, True]).drop(columns=['_sd'])
        else:
            filt = filt.sort_values('Name')
        st.markdown(f"Showing **{len(filt)}** of {len(df)} records")
        st.dataframe(filt, width='stretch',
                     hide_index=True, height=750)

# ══════════════════════════════════════════════
#  DRUGS BY CLASS
# ══════════════════════════════════════════════
elif view == "Drugs by Class":
    st.header("Therapeutic Class Overview")
    if not df.empty:
        for dc in df['Class'].unique():
            sub = df[df['Class'] == dc]
            clr = get_class_colour(dc)
            with st.expander(f"🏷️ {dc} — {len(sub)} drug(s)"):
                st.markdown(
                    f'<div style="height:3px;background:{clr};border-radius:2px;margin-bottom:12px;"></div>', unsafe_allow_html=True)
                st.dataframe(sub[[c for c in sub.columns if c != 'Class']],
                             hide_index=True, width='stretch')

# ══════════════════════════════════════════════
#  INDIVIDUAL DRUG VIEW
# ══════════════════════════════════════════════
elif view == "Individual Drug View":
    st.header("Individual Pharmacokinetic Profile")
    if not df.empty:
        names = df[df['Name'].astype(str).str.contains(
            search_term, case=False)]['Name'].unique() if search_term else df['Name'].unique()
        if len(names) == 0:
            names = df['Name'].unique()
        sel = st.selectbox("Select a Drug:", names)
        if sel:
            drug = df[df['Name'] == sel].iloc[0]
            clr = get_class_colour(drug['Class'])
            st.markdown(
                f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-left:5px solid {clr};border-radius:10px;padding:16px 20px;margin-bottom:16px;"><span style="font-weight:700;color:{HEADING};font-size:1.2rem;">{sel}</span><span style="display:inline-block;margin-left:12px;padding:3px 12px;background:{clr};color:white;border-radius:20px;font-size:0.8rem;font-weight:600;">{drug["Class"]}</span></div>', unsafe_allow_html=True)
            params = [c for c in df.columns if c not in [
                'Name', 'Class', 'id', 'ID']]
            cols = st.columns(3)
            for i, p in enumerate(params):
                with cols[i % 3]:
                    st.metric(label=p, value=str(drug[p]))

# ══════════════════════════════════════════════
#  PK CALCULATOR
# ══════════════════════════════════════════════
elif view == "PK Calculator":
    CALC_GROUPS = [
        ("Absorption & distribution", [("bio", "💊", "Bioavailability (F)"), ("vd", "📦", "Volume of distribution"),
                                       ("cl", "🚿", "Clearance")]),
        ("Elimination", [("hl", "⏳", "Half-life ↔ ke"), ("ke2", "📉", "ke from 2 levels"),
                         ("cmin", "🔻", "Trough (Cmin)")]),
        ("Dosing", [("ld", "💉", "Loading dose"), ("md", "🔁", "Maintenance dose"), ("inf", "💧", "IV infusion Css")]),
        ("Steady state", [("ss", "〰️", "Steady-state simulator"), ("tss", "🎯", "Time to steady state"),
                          ("tw", "🚦", "Therapeutic window")]),
        ("Tools", [("sci", "🧮", "Scientific calculator")]),
    ]
    CALC_NAMES = {k: (ic, t) for _, items in CALC_GROUPS for k, ic, t in items}
    if "calc_sel" not in st.session_state:
        st.session_state.calc_sel = "bio"
    csel = st.session_state.calc_sel

    st.markdown('<div class="contact-hero"><div class="t">🧮 PK Calculator</div>'
                '<div class="s">Pick a calculation. Results and charts update instantly as you move the inputs.</div></div>',
                unsafe_allow_html=True)
    st.markdown(
        f"<style>div.st-key-calc_{csel} div.stButton > button {{ background:linear-gradient(135deg,{BTN_BG_START},{BTN_BG_END}) !important;"
        f" color:#fff !important; border-color:transparent !important; box-shadow:0 10px 22px -10px {BTN_BG_START} !important; }}</style>",
        unsafe_allow_html=True)
    gcols = st.columns([1, 1, 1, 1, 0.9], gap="medium")
    for gc, (gname, items) in zip(gcols, CALC_GROUPS):
        with gc:
            st.markdown(f'<div class="cg">{gname}</div>', unsafe_allow_html=True)
            for k, ic, t in items:
                if st.button(f"{ic}  {t}", key=f"calc_{k}", width='stretch'):
                    st.session_state.calc_sel = k
                    st.rerun()

    ic, title = CALC_NAMES[csel]
    hl_, hr_ = st.columns([4, 1], vertical_alignment="bottom")
    with hl_:
        st.markdown(f'<div class="sec"><div class="k">Calculator</div><div class="t">{ic} {title}</div></div>',
                    unsafe_allow_html=True)
    with hr_:
        if csel not in ("sci", "tw"):
            st.toggle("🎚️ Sliders", value=True, key="calc_sliders",
                      help="On: drag sliders. Off: type exact numbers.")

    def ci(label, key, lo, hi, val, step, fmt="%.2f", help=None):
        """Calculator input: slider or number box (switchable); keeps its value when switching."""
        store = f"cv_{key}"
        cur = st.session_state.get(store, val)
        if st.session_state.get("calc_sliders", True):
            cur = float(min(max(cur, lo), hi))
            v = st.slider(label, min_value=float(lo), max_value=float(hi), value=cur, step=float(step),
                          format=fmt, key=f"{key}_s", help=help)
        else:
            v = st.number_input(label, min_value=float(lo), value=float(cur), step=float(step),
                                format=fmt, key=f"{key}_n", help=help)
        st.session_state[store] = v
        return v

    def res(title, value, unit="", sub="", tone=""):
        st.markdown(f'<div class="res {tone}"><div class="rt">{title}</div>'
                    f'<div class="rv">{value}<span class="ru">{unit}</span></div>'
                    f'<div class="rs">{sub}</div></div>', unsafe_allow_html=True)

    def formula(tex):
        with st.container(border=True):
            st.latex(tex)

    def mini(fig, h=280, x="Time (hours)", y="Concentration"):
        fig.update_layout(showlegend=False)
        st.plotly_chart(style_fig(fig, h=h, x_title=x, y_title=y), width='stretch',
                        config={"displayModeBar": False})

    def decay_fig(c0, k, tmax, colour=TEAL):
        tp = np.linspace(0, tmax, 160)
        return go.Figure(go.Scatter(
            x=tp, y=c0 * np.exp(-k * tp), mode="lines", fill="tozeroy", line=dict(color=colour, width=3, shape="spline"),
            fillcolor=hex_rgba(colour, 0.15), hovertemplate="t = %{x:.1f} h<br>C = %{y:.2f}<extra></extra>"))

    if csel == "sci":
        L, R = st.columns([1.15, 1], gap="large")
    else:
        L, R = st.columns([1, 1.25], gap="large")

    # ── Bioavailability ──
    if csel == "bio":
        with L:
            with st.container(border=True):
                st.markdown("**Oral dose**")
                ao = ci("AUC, oral", "bio_ao", 0, 2000, 80, 1, "%.0f")
                do = ci("Dose, oral (mg)", "bio_do", 0, 1000, 100, 1, "%.0f")
                st.markdown("**IV reference**")
                ai = ci("AUC, IV", "bio_ai", 0, 2000, 100, 1, "%.0f")
                di = ci("Dose, IV (mg)", "bio_di", 0, 1000, 100, 1, "%.0f")
        with R:
            if do > 0 and ai > 0 and di > 0 and ao > 0:
                fv = (ao * di) / (ai * do)
                res("Bioavailability", f"{fv*100:.1f}", "%", f"F = {fv:.3f}", "warn" if fv > 1 else "")
                if fv > 1:
                    st.caption("F above 100% usually means an input is off (check AUC units or doses).")
                g = go.Figure(go.Indicator(
                    mode="gauge", value=min(fv * 100, 150),
                    gauge={'axis': {'range': [0, 100], 'tickcolor': CHART_AXIS, 'ticksuffix': "%"},
                           'bar': {'color': BTN_BG_START, 'thickness': 0.35}, 'bgcolor': hex_rgba(BTN_BG_END, .12),
                           'borderwidth': 0}))
                g.update_layout(height=210, margin=dict(l=30, r=30, t=20, b=0), paper_bgcolor="rgba(0,0,0,0)",
                                font=dict(color=CHART_AXIS, family="Inter, sans-serif"))
                st.plotly_chart(g, width='stretch', config={"displayModeBar": False})
            else:
                res("Bioavailability", "–", "", "Enter non-zero AUC and dose values.")
            formula(r"F = \frac{AUC_{oral} \cdot Dose_{IV}}{AUC_{IV} \cdot Dose_{oral}}")

    # ── Volume of distribution ──
    elif csel == "vd":
        with L:
            with st.container(border=True):
                vd_dose = ci("Dose (mg)", "vd_dose", 0, 2000, 500, 5, "%.0f")
                vd_f = ci("Bioavailability F", "vd_f", 0.01, 1, 1, 0.01)
                vd_ke = ci("ke (1/h)", "vd_ke", 0.001, 1, 0.05, 0.001, "%.3f")
                vd_auc = ci("AUC (mg·h/L)", "vd_auc", 1, 2000, 100, 1, "%.0f")
                wt = ci("Body weight (kg)", "vd_wt", 30, 150, 70, 1, "%.0f")
        with R:
            if vd_dose > 0:
                vd = (vd_dose * vd_f) / (vd_ke * vd_auc)
                res("Volume of distribution", f"{vd:,.1f}", "L", f"≈ {vd/wt:.2f} L/kg for a {wt:.0f} kg patient")
                ref = go.Figure(go.Bar(
                    x=[vd / wt, 0.08, 0.2, 0.6], y=["This drug", "Plasma", "Extracellular water", "Total body water"],
                    orientation="h", marker_color=[BTN_BG_START, "#94A3B8", "#94A3B8", "#94A3B8"],
                    hovertemplate="%{y}: %{x:.2f} L/kg<extra></extra>"))
                ref.update_yaxes(autorange="reversed")
                mini(ref, h=230, x="L/kg", y="")
                st.caption("Grey bars are typical physiological volumes, for comparison.")
            else:
                res("Volume of distribution", "–", "", "Enter a non-zero dose.")
            formula(r"V_d=\frac{Dose \cdot F}{k_e \cdot AUC}")

    # ── Clearance ──
    elif csel == "cl":
        with L:
            with st.container(border=True):
                cd_ = ci("Dose (mg)", "cl_dose", 0, 2000, 500, 5, "%.0f")
                cf = ci("Bioavailability F", "cl_f", 0, 1, 1, 0.01)
                ca = ci("AUC (mg·h/L)", "cl_auc", 1, 2000, 100, 1, "%.0f")
        with R:
            clv = (cf * cd_) / ca if ca > 0 else 0
            res("Clearance", f"{clv:.2f}", "L/h", f"= {clv*1000/60:.0f} mL/min")
            st.markdown(f'<span class="chip">Per day<br><b>{clv*24:.0f} L</b></span>'
                        f'<span class="chip">mL/min<br><b>{clv*1000/60:.0f}</b></span>', unsafe_allow_html=True)
            formula(r"CL=\frac{F\cdot Dose}{AUC}")

    # ── Half-life <-> ke ──
    elif csel == "hl":
        with L:
            with st.container(border=True):
                hmode = st.segmented_control("Start from", ["Half-life", "ke"], default="Half-life", key="hl_mode")
                if hmode == "ke":
                    kk = ci("ke (1/h)", "hl_k", 0.001, 2, 0.1, 0.001, "%.3f")
                    th = 0.693 / kk
                else:
                    th = ci("Half-life (h)", "hl_t", 0.5, 200, 12, 0.5, "%.1f")
                    kk = 0.693 / th
        with R:
            if hmode == "ke":
                res("Half-life", f"{th:.2f}", "h", f"from ke = {kk:.4f} /h")
            else:
                res("Elimination rate ke", f"{kk:.4f}", "/h", f"from t½ = {th:.1f} h")
            f = decay_fig(100, kk, 5 * th)
            hx = [th * n for n in range(1, 6)]
            f.add_trace(go.Scatter(x=hx, y=[100 / 2 ** n for n in range(1, 6)], mode="markers+text",
                                   text=[f"{100/2**n:g}%" for n in range(1, 6)], textposition="top right",
                                   marker=dict(size=10, color=CORAL, line=dict(color="#fff", width=1.5)),
                                   hovertemplate="after %{x:.1f} h: %{y:.1f}% left<extra></extra>"))
            mini(f, y="% of starting level")
            formula(r"k_e=\frac{\ln 2}{t_{1/2}}\approx\frac{0.693}{t_{1/2}}")

    # ── ke from two levels ──
    elif csel == "ke2":
        with L:
            with st.container(border=True):
                c1_ = ci("First level C1 (ng/mL)", "ke2_c1", 0.1, 500, 100, 0.1, "%.1f")
                t1_ = ci("Time of C1 (h)", "ke2_t1", 0, 96, 2, 0.5, "%.1f")
                c2_ = ci("Second level C2 (ng/mL)", "ke2_c2", 0.1, 500, 25, 0.1, "%.1f")
                t2_ = ci("Time of C2 (h)", "ke2_t2", 0, 168, 10, 0.5, "%.1f")
        with R:
            if t2_ > t1_ and c1_ > c2_ > 0:
                k2 = math.log(c1_ / c2_) / (t2_ - t1_)
                res("Elimination rate ke", f"{k2:.4f}", "/h", f"half-life = {0.693/k2:.2f} h")
                tp = np.linspace(0, max(t2_ * 1.4, t2_ + 2), 120)
                c0 = c1_ * math.exp(k2 * t1_)
                f = go.Figure(go.Scatter(x=tp, y=c0 * np.exp(-k2 * tp), mode="lines",
                                         line=dict(color=TEAL, width=3, dash="dot"), hoverinfo="skip"))
                f.add_trace(go.Scatter(x=[t1_, t2_], y=[c1_, c2_], mode="markers+text", text=["C1", "C2"],
                                       textposition="top right", marker=dict(size=14, color=CORAL, line=dict(color="#fff", width=2)),
                                       hovertemplate="t = %{x} h<br>C = %{y} ng/mL<extra></extra>"))
                f.update_yaxes(type="log")
                mini(f, y="Concentration (log scale)")
            else:
                res("Elimination rate ke", "–", "", "Needs t2 later than t1 and C2 lower than C1.", "warn")
            formula(r"k_e=\frac{\ln(C_1/C_2)}{t_2-t_1}")

    # ── Trough ──
    elif csel == "cmin":
        with L:
            with st.container(border=True):
                cm = ci("Peak Cmax (ng/mL)", "cmin_cm", 0.1, 1000, 100, 0.5, "%.1f")
                th = ci("Half-life (h)", "cmin_th", 0.5, 200, 12, 0.5, "%.1f")
                iv = ci("Dosing interval (h)", "cmin_iv", 1, 168, 24, 1, "%.0f")
        with R:
            kk = 0.693 / th
            cmin_v = cm * math.exp(-kk * iv)
            res("Trough Cmin", f"{cmin_v:.2f}", "ng/mL", f"{cmin_v/cm*100:.0f}% of peak remains at the next dose")
            f = decay_fig(cm, kk, iv)
            f.add_trace(go.Scatter(x=[iv], y=[cmin_v], mode="markers", marker=dict(size=14, color=CORAL,
                                   line=dict(color="#fff", width=2)), hovertemplate="Cmin %{y:.2f}<extra></extra>"))
            mini(f)
            formula(r"C_{min}=C_{max}\cdot e^{-k_e\cdot \tau}")

    # ── Loading dose ──
    elif csel == "ld":
        with L:
            with st.container(border=True):
                ld_ct = ci("Target concentration (mg/L)", "ld_ct", 0.01, 50, 2, 0.01)
                ld_vd = ci("Vd (L)", "ld_vd", 1, 1000, 50, 1, "%.0f")
                ld_f = ci("Bioavailability F", "ld_f", 0.01, 1, 1, 0.01)
                wt = ci("Body weight (kg)", "ld_wt", 30, 150, 70, 1, "%.0f")
        with R:
            ldv = (ld_ct * ld_vd) / ld_f
            res("Loading dose", f"{ldv:,.1f}", "mg", f"≈ {ldv/wt:.2f} mg/kg")
            formula(r"LD=\frac{C_{target} \cdot V_d}{F}")

    # ── Maintenance dose ──
    elif csel == "md":
        with L:
            with st.container(border=True):
                md_cl = ci("Clearance (L/h)", "md_cl", 0.1, 100, 5, 0.1, "%.1f")
                md_css = ci("Target Css,avg (mg/L)", "md_css", 0.01, 50, 1, 0.01)
                md_f = ci("Bioavailability F", "md_f", 0.01, 1, 1, 0.01)
        with R:
            mdr = (md_cl * md_css) / md_f
            res("Maintenance dose rate", f"{mdr:.2f}", "mg/h", f"= {mdr*24:.0f} mg per day")
            st.markdown("".join(f'<span class="chip">Every {h} h<br><b>{mdr*h:.0f} mg</b></span>' for h in (6, 8, 12, 24)),
                        unsafe_allow_html=True)
            formula(r"\text{Dose rate}=\frac{CL \cdot C_{ss,avg}}{F}")

    # ── IV infusion ──
    elif csel == "inf":
        with L:
            with st.container(border=True):
                r0 = ci("Infusion rate R₀ (mg/h)", "inf_r0", 0.1, 200, 10, 0.1, "%.1f")
                icl = ci("Clearance (L/h)", "inf_cl", 0.1, 100, 5, 0.1, "%.1f")
                ivd = ci("Vd (L), for the curve", "inf_vd", 1, 1000, 50, 1, "%.0f")
        with R:
            css_i = r0 / icl
            ki = icl / ivd
            t90 = math.log(10) / ki
            res("Steady-state concentration", f"{css_i:.2f}", "mg/L", f"90% of this is reached after ~{t90:.1f} h")
            tp = np.linspace(0, max(5 * 0.693 / ki, t90 * 1.2), 160)
            f = go.Figure(go.Scatter(x=tp, y=css_i * (1 - np.exp(-ki * tp)), mode="lines", fill="tozeroy",
                                     line=dict(color=TEAL, width=3), fillcolor=hex_rgba(TEAL, .15),
                                     hovertemplate="t = %{x:.1f} h<br>C = %{y:.2f} mg/L<extra></extra>"))
            f.add_hline(y=css_i, line=dict(color=SUCCESS, width=2, dash="dash"), annotation_text="Css",
                        annotation_position="right", annotation_font_color=SUCCESS)
            mini(f, y="Concentration (mg/L)")
            formula(r"C_{ss}=\frac{R_0}{CL}")

    # ── Steady-state simulator ──
    elif csel == "ss":
        with L:
            with st.container(border=True):
                sd = ci("Dose (mg)", "ss_dose", 1, 2000, 100, 1, "%.0f")
                tau = ci("Dosing interval τ (h)", "ss_tau", 1, 72, 24, 1, "%.0f")
                sh = ci("Half-life (h)", "ss_th", 0.5, 200, 12, 0.5, "%.1f")
                sv = ci("Vd (L)", "ss_vd", 1, 1000, 50, 1, "%.0f")
                ncy = st.slider("Doses to plot", 3, 12, 6, key="ss_cyc2")
        with R:
            kk = 0.693 / sh
            af = 1 / (1 - math.exp(-kk * tau))
            cmx = (sd / sv) * af
            cmn = cmx * math.exp(-kk * tau)
            cav = (sd / sv) / (kk * tau)
            res("Steady state", f"{cav:.2f}", "mg/L avg",
                f"peak {cmx:.2f} · trough {cmn:.2f} · accumulation ×{af:.2f}")
            ts, cs_ = [], []
            c_ = 0
            for i in range(ncy):
                c_ += sd / sv
                for t in np.linspace(0, tau, 40):
                    ts.append(i * tau + t)
                    cs_.append(c_ * math.exp(-kk * t))
                c_ *= math.exp(-kk * tau)
            f = go.Figure(go.Scatter(x=ts, y=cs_, mode="lines", line=dict(color=TEAL, width=2.5),
                                     hovertemplate="t = %{x:.1f} h<br>C = %{y:.2f}<extra></extra>"))
            for yv, lb, col in [(cmx, "Css,max", DANGER), (cav, "Css,avg", SUCCESS), (cmn, "Css,min", WARNING)]:
                f.add_hline(y=yv, line=dict(color=col, width=1.5, dash="dot"), annotation_text=lb,
                            annotation_position="right", annotation_font_color=col)
            mini(f, h=300, y="Concentration (mg/L)")
            formula(r"C_{ss,avg}=\frac{Dose}{V_d\,k_e\,\tau}\qquad R=\frac{1}{1-e^{-k_e\tau}}")

    # ── Time to steady state ──
    elif csel == "tss":
        with L:
            with st.container(border=True):
                th = ci("Half-life (h)", "tss_th", 0.5, 200, 12, 0.5, "%.1f")
                nn = st.slider("Number of half-lives", 1, 7, 5, key="tss_n2")
        with R:
            res("Time to steady state", f"~{nn*th:.0f}", "h",
                f"≈ {nn*th/24:.1f} days · {100*(1-0.5**nn):.1f}% of steady state reached")
            ns = list(range(1, 8))
            f = go.Figure(go.Bar(
                x=[f"{n}×t½" for n in ns], y=[100 * (1 - 0.5 ** n) for n in ns],
                marker_color=[BTN_BG_START if n == nn else hex_rgba(BTN_BG_END, .35) for n in ns],
                text=[f"{100*(1-0.5**n):.1f}%" for n in ns], textposition="outside",
                hovertemplate="%{x} = %{customdata:.0f} h<extra></extra>", customdata=[n * th for n in ns]))
            f.update_yaxes(range=[0, 112])
            mini(f, h=280, x="", y="% of steady state")
            formula(r"t_{ss}\approx n \cdot t_{1/2}\quad(n=4\text{–}5)")

    # ── Therapeutic window ──
    elif csel == "tw":
        with L:
            with st.container(border=True):
                if not df.empty:
                    tw_d = st.selectbox("Drug", df['Name'].unique(), key="tw_d2")
                    tw_m = st.number_input("Measured concentration (ng/mL)", min_value=0.0, value=0.0,
                                           step=0.1, key="tw_m2")
        with R:
            if df.empty:
                st.info("No data loaded.")
            elif tw_m <= 0:
                res("Therapeutic window", "–", "", "Enter a measured concentration to check it.")
            else:
                pp = get_drug_params(df[df['Name'] == tw_d].iloc[0])
                if pp['css_min'] and pp['css_max']:
                    lo, hi = pp['css_min'], pp['css_max']
                    if tw_m < lo:
                        res("Sub-therapeutic", f"{tw_m:g}", "ng/mL", f"below Css,min ({lo})", "warn")
                    elif tw_m > hi:
                        res("Supra-therapeutic", f"{tw_m:g}", "ng/mL", f"above Css,max ({hi})", "bad")
                    else:
                        res("Within range", f"{tw_m:g}", "ng/mL", f"between Css,min ({lo}) and Css,max ({hi})", "good")
                    gauge = go.Figure(go.Indicator(
                        mode="gauge", value=tw_m,
                        gauge={'axis': {'range': [0, hi * 1.4], 'tickcolor': CHART_AXIS},
                               'bar': {'color': HEADING, 'thickness': 0.25},
                               'steps': [{'range': [0, lo], 'color': WARNING + "55"},
                                         {'range': [lo, hi], 'color': SUCCESS + "55"},
                                         {'range': [hi, hi * 1.4], 'color': DANGER + "55"}]}))
                    gauge.update_layout(height=230, margin=dict(l=30, r=30, t=20, b=0), paper_bgcolor="rgba(0,0,0,0)",
                                        font=dict(color=CHART_AXIS, family="Inter, sans-serif"))
                    st.plotly_chart(gauge, width='stretch', config={"displayModeBar": False})
                else:
                    st.info(f"No Css range data for {tw_d}.")

    # ── Scientific calculator ──
    elif csel == "sci":
        with L:
            components.html(SCI_CALC_HTML.format(
                card=BG_CARD, border=BORDER, text=TEXT_PRIMARY, muted=TEXT_SECONDARY, a=BTN_BG_START, b=BTN_BG_END,
                key=("#273449" if IS_NIGHT else "#F1F5F9"), keyh=("#334155" if IS_NIGHT else "#E2E8F0"),
                screen=("#0B1220" if IS_NIGHT else "#0F172A"), fn=("#38BDF8" if IS_NIGHT else BTN_BG_START)), height=560)
        with R:
            st.markdown(f"""<div class="cbox"><b>Handy PK relationships</b><br><br>
k<sub>e</sub> = 0.693 / t½ &nbsp;·&nbsp; t½ = 0.693 / k<sub>e</sub><br>
C(t) = C₀ · e<sup>−k·t</sup><br>
CL = k<sub>e</sub> · V<sub>d</sub><br>
C<sub>ss,avg</sub> = F · Dose / (CL · τ)<br>
Accumulation R = 1 / (1 − e<sup>−k·τ</sup>)<br><br>
<span style="color:{TEXT_SECONDARY};font-size:.88rem;">Tip: use <b>ln2</b> for 0.693…, <b>Ans</b> for the last answer,
and your keyboard (numbers, + − * / ^, Enter, Backspace, Esc).</span></div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  PK GRAPH
# ══════════════════════════════════════════════
elif view == "PK Graph":
    st.header("Concentration–Time Graph & Analysis")
    c1, c2 = st.columns([1, 2])
    used_cmax = None
    used_cmax_sd = 0.0
    k = None
    val_thalf = None
    cmax_txt = "Reported"
    calc_pt = None
    lod = 0.0
    tdm_pt = None
    tdm_c = 0.0
    tdm_t = 0.0
    cmp_params = None
    cmp_name = None
    multi_drugs = []
    show_det = True
    show_cmax = True
    det_caption = None
    SLIDER_HINT = "Raise the Time slider to bring it into view."

    with c1:
        st.subheader("Select Drug")
        drug_map = {}
        dc = [c for c in df.columns if any(kw in c.lower() for kw in [
                                           'dose', 'strength', 'mg'])]
        pdc = dc[0] if dc else None
        def dlabel(r):
            """Drug name plus dose, e.g. 'Amlodipine 10 mg', for legends and captions."""
            nm = str(r['Name']).replace("\xa0", " ").strip()
            if pdc and pd.notna(r[pdc]):
                try:
                    return f"{nm} {float(r[pdc]):g} mg"
                except (TypeError, ValueError):
                    return f"{nm} {r[pdc]}"
            return nm

        for idx, row in df.iterrows():
            lb = str(row['Name'])
            if pdc and pd.notna(row[pdc]):
                lb = f"{lb} — {row[pdc]}"
            o = lb
            cn = 1
            while lb in drug_map:
                cn += 1
                lb = f"{o} ({cn})"
            if search_term:
                if search_term.lower() in str(row['Name']).lower() or search_term.lower() in str(row['Class']).lower():
                    drug_map[lb] = idx
            else:
                drug_map[lb] = idx

        if not drug_map:
            st.warning("No drugs found.")
            sel = None
        else:
            sel = st.selectbox("Choose Drug:", list(drug_map.keys()))

        if sel:
            di = drug_map[sel]
            dr = df.loc[di]
            cc = get_class_colour(dr['Class'])
            st.markdown(
                f'<span style="padding:3px 12px;background:{cc};color:white;border-radius:20px;font-size:0.8rem;font-weight:600;">{dr["Class"]}</span>', unsafe_allow_html=True)
            p = get_drug_params(dr)
            val_thalf = p['thalf']
            dn1 = dlabel(dr)

            gm = st.radio("Mode:", ["Standard Elimination", "Accumulation Comparison",
                          "Steady State Oscillation", "Drug Comparison", "Multi-Drug Screen"])
            g_time = st.slider("Time (hours)", 6, 720, 48)

            tog1, tog2 = st.columns(2)
            with tog1:
                show_det = st.checkbox(
                    "Detection window", value=True,
                    help="Mark when the plotted curve falls to the limit of detection (LoD).")
            with tog2:
                show_cmax = st.checkbox(
                    "Cmax reference", value=True,
                    help="Mark the peak concentration (Cmax) on each curve.")

            # Filled in by the graph code below, so the caption always shows the
            # same value as the line drawn on the chart.
            det_caption = st.empty()

            if gm == "Drug Comparison":
                ol = [l for l in drug_map.keys() if l != sel]
                if ol:
                    cmp_lb = st.selectbox("Compare with:", ol, key="cmp")
                    cmp_params = get_drug_params(df.loc[drug_map[cmp_lb]])
                    cmp_name = dlabel(df.loc[drug_map[cmp_lb]])

            if gm == "Multi-Drug Screen":
                ol = [l for l in drug_map.keys() if l != sel]
                multi_sel = st.multiselect(
                    "Add drugs (up to 4 more):", ol, max_selections=4, key="multi")
                multi_drugs = [(dlabel(df.loc[drug_map[l]]), get_drug_params(
                    df.loc[drug_map[l]])) for l in multi_sel]

            if val_thalf and val_thalf > 0:
                k = 0.693/val_thalf
                used_cmax = p['sd_cmax']
                if gm == "Standard Elimination":
                    src = st.radio(
                        "Cmax:", ["Reported", "From AUC"], horizontal=True)
                    if src == "From AUC":
                        if p['auc']:
                            used_cmax = p['auc']*k
                            used_cmax_sd = 0.0
                            cmax_txt = "Calculated"
                        else:
                            used_cmax = p['cmax']
                            used_cmax_sd = p['cmax_sd']
                    else:
                        used_cmax = p['cmax']
                        used_cmax_sd = p['cmax_sd']
                    if used_cmax and used_cmax > 0:
                        with st.expander("🔬 Quick Point Calculator"):
                            q1, q2 = st.tabs(["Find Conc.", "Find Time"])
                            with q1:
                                it = st.number_input("Time (h)", min_value=0.0, value=float(
                                    val_thalf), step=1.0, key="qt")
                                oc = used_cmax*np.exp(-k*it)
                                st.markdown(f"**Conc:** `{oc:.2f} ng/mL`")
                                calc_pt = pd.DataFrame(
                                    {'Time (hours)': [it], 'Concentration (ng/mL)': [oc]})
                            with q2:
                                ic = st.number_input(
                                    "Target (ng/mL)", min_value=0.0, value=float(used_cmax/2), step=1.0, key="qc")
                                if 0 < ic < used_cmax:
                                    ot = -(1/k)*np.log(ic/used_cmax)
                                    st.markdown(f"**Time:** `{ot:.2f} h`")
                                    calc_pt = pd.DataFrame(
                                        {'Time (hours)': [ot], 'Concentration (ng/mL)': [ic]})
                        with st.expander("🩸 Plot TDM Result"):
                            tdm_c = st.number_input(
                                "Measured (ng/mL)", min_value=0.0, value=0.0, step=0.1, key="tc")
                            tdm_t = st.number_input(
                                "Time post-dose (h)", min_value=0.0, value=0.0, step=0.5, key="tdm_time")
                            if tdm_c > 0 and tdm_t > 0:
                                tdm_pt = pd.DataFrame(
                                    {'Time (hours)': [tdm_t], 'Concentration (ng/mL)': [tdm_c]})
                        lod_def = float(p['lod']) if p['lod'] else 0.0
                        lod = st.number_input(
                            "LoD (ng/mL)", min_value=0.0, value=lod_def, step=0.1)

    with c2:
        if sel and val_thalf and val_thalf > 0:
            k = 0.693/val_thalf

            # ── STANDARD ELIMINATION ──
            if gm == "Standard Elimination":
                st.subheader("Standard Elimination (Single Dose)")
                if used_cmax and used_cmax > 0:
                    tp = np.linspace(0, g_time, 100)
                    concs = used_cmax*np.exp(-k*tp)
                    cd = pd.DataFrame(
                        {"Time (hours)": tp, "Concentration (ng/mL)": concs})
                    fig = go.Figure()
                    # ± SD confidence band
                    if used_cmax_sd > 0:
                        upper = (used_cmax+used_cmax_sd)*np.exp(-k*tp)
                        lower = np.maximum(
                            0, (used_cmax-used_cmax_sd)*np.exp(-k*tp))
                        cd['U'] = upper
                        cd['L'] = lower
                        fig.add_trace(go.Scatter(
                            x=np.concatenate([tp, tp[::-1]]),
                            y=np.concatenate([upper, lower[::-1]]),
                            fill="toself", fillcolor="rgba(0,180,216,0.15)",
                            line=dict(color="rgba(0,0,0,0)"), hoverinfo="skip",
                            name="± SD", showlegend=True))
                    # main elimination curve (animated draw via line_shape spline)
                    fig.add_trace(go.Scatter(
                        x=tp, y=concs, mode="lines", name=dn1,
                        line=dict(color=line_colour, width=3, shape="spline"),
                        hovertemplate="t = %{x:.1f} h<br>C = %{y:.2f} ng/mL<extra></extra>"))
                    if calc_pt is not None:
                        fig.add_trace(go.Scatter(
                            x=calc_pt['Time (hours)'], y=calc_pt['Concentration (ng/mL)'],
                            mode="markers", name="Quick point",
                            marker=dict(color=DANGER, size=13,
                                        line=dict(color="#fff", width=1.5)),
                            hovertemplate="t = %{x:.1f} h<br>C = %{y:.2f} ng/mL<extra>Quick point</extra>"))
                    if tdm_pt is not None:
                        fig.add_trace(go.Scatter(
                            x=tdm_pt['Time (hours)'], y=tdm_pt['Concentration (ng/mL)'],
                            mode="markers", name="TDM result",
                            marker=dict(color=PURPLE, size=16, symbol="diamond",
                                        line=dict(color="#fff", width=1.5)),
                            hovertemplate="t = %{x:.1f} h<br>C = %{y:.2f} ng/mL<extra>TDM result</extra>"))
                    if lod > 0:
                        fig.add_hline(y=lod, line=dict(color=WARNING, width=2, dash="dash"),
                                      annotation_text=f"LoD {lod:g}", annotation_position="top right",
                                      annotation_font_color=WARNING)
                    if show_cmax:
                        add_cmax_ref(fig, used_cmax, f"({cmax_txt})", TEAL)
                    if show_det:
                        dw_sd = det_window_h(used_cmax, val_thalf, lod)
                        add_det_window(fig, dw_sd, g_time, "", DANGER)
                        render_det_caption(det_caption, [
                            (f"{dn1} (single dose, LoD {lod:g})", dw_sd,
                             dw_sd is not None and dw_sd <= g_time)], SLIDER_HINT)
                    st.plotly_chart(
                        style_fig(fig), width='stretch', config=PLOTLY_CONFIG)
                    st.markdown(
                        f"**Cmax ({cmax_txt})** = {used_cmax:.2f} ng/mL · **t½** = {val_thalf}h")
                    # Clinical interpretation
                    if tdm_pt is not None:
                        exp = used_cmax*np.exp(-k*tdm_t)
                        if tdm_c < exp*0.1:
                            st.markdown(
                                f'<div class="cbox-d"><strong>🔴</strong> Measured ({tdm_c:.1f}) at {tdm_t:.1f}h far below predicted ({exp:.1f}). <strong>Inconsistent with recent dosing.</strong></div>', unsafe_allow_html=True)
                        elif tdm_c < exp*0.5:
                            st.markdown(
                                f'<div class="cbox-w"><strong>🟡</strong> Measured ({tdm_c:.1f}) below predicted ({exp:.1f}). May indicate <strong>partial adherence</strong>.</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(
                                f'<div class="cbox"><strong>🟢</strong> Measured ({tdm_c:.1f}) consistent with predicted ({exp:.1f}). <strong>Compatible with recent dosing.</strong></div>', unsafe_allow_html=True)
                    elif lod > 0 and used_cmax > lod:
                        dt = -(1/k)*np.log(lod/used_cmax)
                        st.markdown(
                            f'<div class="cbox"><strong>📋 Detection Window:</strong> ~<strong>{dt:.1f}h ({dt/24:.1f} days)</strong> after last dose.</div>', unsafe_allow_html=True)
                    # Download
                    dl = cd[["Time (hours)", "Concentration (ng/mL)"]].copy()
                    dl["Time (hours)"] = dl["Time (hours)"].apply(sig_figs)
                    dl["Concentration (ng/mL)"] = dl["Concentration (ng/mL)"].apply(sig_figs)
                    st.download_button("📥 Download CSV", dl.to_csv(
                        index=False), "elimination.csv", "text/csv", width='stretch')
                    # ── GENERATE REPORT ──
                    report_lines = [
                        f"CARDIOKINETICS — Clinical PK Report",
                        f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        f"{'='*50}",
                        f"Drug: {dn1}",
                        f"Class: {dr['Class']}",
                        f"Cmax ({cmax_txt}): {used_cmax:.2f} ng/mL",
                        f"Half-Life: {val_thalf} h",
                        f"ke: {k:.4f} /h",
                        f"LoD: {lod} ng/mL" if lod > 0 else "LoD: Not specified",
                    ]
                    if lod > 0 and used_cmax > lod:
                        dw = -(1/k)*np.log(lod/used_cmax)
                        report_lines.append(
                            f"Estimated Detection Window: {dw:.1f} h ({dw/24:.1f} days)")
                    if tdm_pt is not None:
                        exp = used_cmax*np.exp(-k*tdm_t)
                        report_lines += [f"\nTDM Result:", f"  Measured: {tdm_c:.1f} ng/mL at {tdm_t:.1f}h post-dose", f"  Predicted: {exp:.1f} ng/mL",
                                         f"  Ratio: {tdm_c/exp:.2f}" if exp > 0 else "",
                                         f"  Interpretation: {'Consistent with dosing' if tdm_c >= exp*0.5 else 'Below expected — partial adherence suspected' if tdm_c >= exp*0.1 else 'Far below expected — non-adherence suspected'}"]
                    report_lines += [f"\n{'='*50}", f"Note: Based on population-average PK parameters.",
                                     f"One-compartment model. Not validated for clinical use."]
                    st.download_button("📋 Generate Report", "\n".join(
                        report_lines), "pk_report.txt", "text/plain", width='stretch')

            # ── ACCUMULATION COMPARISON ──
            elif gm == "Accumulation Comparison":
                st.subheader("Accumulation Comparison")
                if p['sd_cmax'] and p['css_max']:
                    tp = np.linspace(0, g_time, 100)
                    sd_curve = p['sd_cmax']*np.exp(-k*tp)
                    ss_curve = p['css_max']*np.exp(-k*tp)
                    cd = pd.concat([pd.DataFrame({"Time (hours)": tp, "Concentration (ng/mL)": sd_curve, "Profile": "Single Dose"}),
                                    pd.DataFrame({"Time (hours)": tp, "Concentration (ng/mL)": ss_curve, "Profile": "Steady State"})])
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=tp, y=ss_curve, mode="lines", name="Steady State",
                                             line=dict(
                                                 color=CORAL, width=3, shape="spline"),
                                             hovertemplate="t = %{x:.1f} h<br>C = %{y:.2f} ng/mL<extra>Steady State</extra>"))
                    fig.add_trace(go.Scatter(x=tp, y=sd_curve, mode="lines", name="Single Dose",
                                             line=dict(
                                                 color=TEAL, width=3, shape="spline"),
                                             hovertemplate="t = %{x:.1f} h<br>C = %{y:.2f} ng/mL<extra>Single Dose</extra>"))
                    if show_cmax:
                        add_cmax_ref(
                            fig, p['css_max'], "(Css,max)", CORAL, position="top right")
                        add_cmax_ref(
                            fig, p['sd_cmax'], "(single dose)", TEAL, position="bottom left")
                    if show_det:
                        dw_sd = det_window_h(p['sd_cmax'], p['thalf'], p['lod'])
                        dw_ss = det_window_h(p['css_max'], p['thalf'], p['lod'])
                        add_det_window(fig, dw_sd, g_time, "single dose", TEAL)
                        add_det_window(fig, dw_ss, g_time, "steady state", CORAL)
                        render_det_caption(det_caption, [
                            ("single dose", dw_sd, dw_sd is not None and dw_sd <= g_time),
                            ("steady state", dw_ss, dw_ss is not None and dw_ss <= g_time)],
                            SLIDER_HINT)
                    st.plotly_chart(
                        style_fig(fig), width='stretch', config=PLOTLY_CONFIG)
                    af = round(p['css_max']/p['sd_cmax'], 2)
                    st.markdown(
                        f'<div class="cbox"><strong>R = {af}</strong> — steady-state peak is {af}× higher than single dose. TDM matching single-dose but below steady state suggests <strong>intermittent adherence</strong>.</div>', unsafe_allow_html=True)
                else:
                    st.warning("Missing Css,max or Cmax data.")

            # ── SAW-TOOTH OSCILLATION ──
            elif gm == "Steady State Oscillation":
                st.subheader("Steady State Oscillation (Saw-Tooth)")
                if p['css_max'] and p['css_min']:
                    try:
                        tau = -math.log(p['css_min']/p['css_max'])/k
                    except:
                        tau = 24.0
                    if pd.isna(tau) or tau <= 0:
                        tau = 24.0
                    n_int = st.slider("Dosing intervals", 1, 10, 5, key="ni")
                    ts, cs = [], []
                    for i in range(n_int):
                        for t in np.linspace(0, tau, 40):
                            ts.append(i*tau+t)
                            cs.append(p['css_max']*np.exp(-k*t))
                    cd = pd.DataFrame(
                        {"Time (hours)": ts, "Concentration (ng/mL)": cs})
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=ts, y=cs, mode="lines", name="Concentration",
                                             line=dict(
                                                 color=line_colour, width=3),
                                             hovertemplate="t = %{x:.1f} h<br>C = %{y:.2f} ng/mL<extra></extra>"))
                    ref = [(p['css_max'], "Css,max", DANGER),
                           (p['css_min'], "Css,min", WARNING)]
                    if p['css_avg']:
                        ref.append((p['css_avg'], "Css,avg", SUCCESS))
                    for yval, lbl, clr in ref:
                        fig.add_hline(y=yval, line=dict(color=clr, width=2, dash="dash"),
                                      annotation_text=lbl, annotation_position="right",
                                      annotation_font_color=clr)
                    if show_cmax and p['sd_cmax']:
                        add_cmax_ref(
                            fig, p['sd_cmax'], "(single dose)", TEAL, position="bottom left")
                    if show_det:
                        # measured from the LAST dose, starting at steady-state Css,max
                        dw_ss = det_window_h(p['css_max'], p['thalf'], p['lod'])
                        last_dose = (n_int - 1) * tau
                        x_det = last_dose + dw_ss if dw_ss is not None else None
                        add_det_window(fig, x_det, max(ts), "after last dose", DANGER)
                        render_det_caption(det_caption, [
                            ("after the last steady-state dose", dw_ss,
                             x_det is not None and x_det <= max(ts))],
                            "It falls beyond the plotted dosing intervals.")
                    fig.update_yaxes(range=[0, p['css_max']*1.2])
                    st.plotly_chart(style_fig(fig, x_title=f"Time (hours) — τ = {tau:.1f}h"),
                                    width='stretch', config=PLOTLY_CONFIG)
                    st.markdown(
                        f'<div class="cbox"><strong>Saw-Tooth:</strong> {n_int} intervals of τ ≈ {tau:.1f}h. Concentration oscillates between Css,max ({p["css_max"]}) and Css,min ({p["css_min"]}).</div>', unsafe_allow_html=True)
                else:
                    st.warning("Missing Css data.")

            # ── DRUG COMPARISON (solid lines, single legend with names) ──
            elif gm == "Drug Comparison":
                st.subheader("Drug Comparison")
                if cmp_params and cmp_params['thalf'] and (cmp_params['sd_cmax'] or cmp_params['cmax']):
                    tp = np.linspace(0, g_time, 100)
                    c1v = p['sd_cmax'] or p['cmax'] or 0
                    c2v = cmp_params['sd_cmax'] or cmp_params['cmax'] or 0
                    k1 = 0.693/p['thalf']
                    k2 = 0.693/cmp_params['thalf']
                    y1 = c1v*np.exp(-k1*tp)
                    y2 = c2v*np.exp(-k2*tp)
                    cd = pd.concat([pd.DataFrame({"Time (hours)": tp, "Concentration (ng/mL)": y1, "Drug": dn1}),
                                    pd.DataFrame({"Time (hours)": tp, "Concentration (ng/mL)": y2, "Drug": cmp_name})])
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=tp, y=y1, mode="lines", name=dn1,
                                             line=dict(
                                                 color=TEAL, width=3, shape="spline"),
                                             hovertemplate="t = %{x:.1f} h<br>C = %{y:.2f} ng/mL<extra>"+dn1+"</extra>"))
                    fig.add_trace(go.Scatter(x=tp, y=y2, mode="lines", name=cmp_name,
                                             line=dict(
                                                 color=CORAL, width=3, shape="spline"),
                                             hovertemplate="t = %{x:.1f} h<br>C = %{y:.2f} ng/mL<extra>"+cmp_name+"</extra>"))
                    if show_cmax:
                        add_cmax_ref(
                            fig, c1v, f"· {dn1}", TEAL, position="top left")
                        add_cmax_ref(
                            fig, c2v, f"· {cmp_name}", CORAL, position="bottom left")
                    if show_det:
                        dw1 = det_window_h(c1v, p['thalf'], p['lod'])
                        dw2 = det_window_h(c2v, cmp_params['thalf'], cmp_params['lod'])
                        add_det_window(fig, dw1, g_time, dn1, TEAL)
                        add_det_window(fig, dw2, g_time, cmp_name, CORAL)
                        render_det_caption(det_caption, [
                            (dn1, dw1, dw1 is not None and dw1 <= g_time),
                            (cmp_name, dw2, dw2 is not None and dw2 <= g_time)],
                            SLIDER_HINT)
                    st.plotly_chart(
                        style_fig(fig), width='stretch', config=PLOTLY_CONFIG)
                    longer = dn1 if p['thalf'] > cmp_params['thalf'] else cmp_name
                    st.markdown(
                        f'<div class="cbox"><strong>{dn1}</strong> (t½={p["thalf"]:.1f}h) vs <strong>{cmp_name}</strong> (t½={cmp_params["thalf"]:.1f}h). <strong>{longer}</strong> has the longer detection window.</div>', unsafe_allow_html=True)
                    dl = cd.copy()
                    dl["Time (hours)"] = dl["Time (hours)"].apply(sig_figs)
                    dl["Concentration (ng/mL)"] = dl["Concentration (ng/mL)"].apply(sig_figs)
                    st.download_button("📥 Download CSV", dl.to_csv(
                        index=False), "comparison.csv", "text/csv", width='stretch')
                else:
                    st.warning("Select a second drug with valid PK data.")

            # ── MULTI-DRUG SCREEN ──
            elif gm == "Multi-Drug Screen":
                st.subheader("Multi-Drug Adherence Screen")
                all_drugs = [(dn1, p)]+multi_drugs
                palette = [TEAL, CORAL, PURPLE, SUCCESS, "#F472B6"]
                if len(all_drugs) >= 2:
                    tp = np.linspace(0, g_time, 100)
                    frames = []
                    for i, (name, pp) in enumerate(all_drugs):
                        if pp['thalf'] and pp['thalf'] > 0 and (pp['sd_cmax'] or pp['cmax']):
                            kk = 0.693/pp['thalf']
                            cv = pp['sd_cmax'] or pp['cmax']
                            frames.append(pd.DataFrame(
                                {"Time (hours)": tp, "Concentration (ng/mL)": cv*np.exp(-kk*tp), "Drug": name}))
                    if frames:
                        cd = pd.concat(frames)
                        fig = go.Figure()
                        for i, frame in enumerate(frames):
                            nm = frame['Drug'].iloc[0]
                            fig.add_trace(go.Scatter(
                                x=frame['Time (hours)'], y=frame['Concentration (ng/mL)'],
                                mode="lines", name=nm,
                                line=dict(color=palette[i % len(
                                    palette)], width=3, shape="spline"),
                                hovertemplate="t = %{x:.1f} h<br>C = %{y:.2f} ng/mL<extra>"+nm+"</extra>"))
                        if lod > 0:
                            fig.add_hline(y=lod, line=dict(color=WARNING, width=2, dash="dash"),
                                          annotation_text=f"LoD {lod:g}", annotation_position="top right",
                                          annotation_font_color=WARNING)
                        valid = [(nm, pp) for nm, pp in all_drugs
                                 if pp['thalf'] and pp['thalf'] > 0 and (pp['sd_cmax'] or pp['cmax'])]
                        if show_cmax and valid:
                            cx, cy, cc, ctxt = [], [], [], []
                            for i, (nm, pp) in enumerate(valid):
                                cv = pp['sd_cmax'] or pp['cmax']
                                cx.append(0)
                                cy.append(cv)
                                cc.append(palette[i % len(palette)])
                                ctxt.append(f"{nm} · Cmax {cv:.1f} ng/mL")
                            fig.add_trace(go.Scatter(
                                x=cx, y=cy, mode="markers", name="Cmax",
                                marker=dict(color=cc, size=11, symbol="circle",
                                            line=dict(color="#fff", width=1.5)),
                                text=ctxt, hovertemplate="%{text}<extra></extra>",
                                showlegend=False))
                        multi_dw = []
                        for i, (nm, pp) in enumerate(valid):
                            lod_i = lod if lod > 0 else pp['lod']
                            dwi = det_window_h(pp['sd_cmax'] or pp['cmax'], pp['thalf'], lod_i)
                            multi_dw.append((nm, dwi, dwi is not None and dwi <= g_time))
                            if show_det:
                                add_det_window(fig, dwi, g_time, nm,
                                               palette[i % len(palette)])
                        if show_det:
                            render_det_caption(det_caption, multi_dw, SLIDER_HINT)
                        st.plotly_chart(
                            style_fig(fig), width='stretch', config=PLOTLY_CONFIG)
                        # Interpretation (same values as the lines on the chart)
                        if multi_dw:
                            lines = [f"<strong>{nm}</strong>: detectable for ~{h:.0f}h ({h/24:.1f} days)"
                                     if h is not None else f"<strong>{nm}</strong>: Cmax at or below LoD"
                                     for nm, h, _ in multi_dw]
                            st.markdown(
                                f'<div class="cbox"><strong>📋 Detection Windows (each drug\'s LoD):</strong><br>{"<br>".join(lines)}</div>', unsafe_allow_html=True)
                        dl = cd.copy()
                        dl["Time (hours)"] = dl["Time (hours)"].apply(sig_figs)
                        dl["Concentration (ng/mL)"] = dl["Concentration (ng/mL)"].apply(sig_figs)
                        st.download_button("📥 Download CSV", dl.to_csv(
                            index=False), "multi_drug.csv", "text/csv", width='stretch')
                else:
                    st.info(
                        "Add at least one more drug in the \"Add drugs\" box on the left to compare.")


# ══════════════════════════════════════════════
#  FOOTER
# ══════════════════════════════════════════════
if view not in ("Home", "Contact"):
    fa, fb = st.columns([5, 1], vertical_alignment="center")
    with fa:
        st.markdown('<div class="foot">💊 Cardiokinetics · research tool under development, not validated for '
                    'clinical use. Questions, problems or ideas? Get in touch →</div>', unsafe_allow_html=True)
    with fb:
        if st.button("✉️ Feedback", key="foot_contact", width='stretch'):
            nav_to("Contact")
