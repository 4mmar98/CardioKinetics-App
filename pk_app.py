import streamlit as st
import pandas as pd
import numpy as np
import os
import math
import re
import io
import datetime
import altair as alt

st.set_page_config(page_title="Cardiokinetics", layout="wide", page_icon="💊")

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
                 "Beta Blocker": "#059669", "Diuretic": "#D97706", "Alpha Blocker": "#DB2777", "MRA": "#0891B2", "Uncategorized": "#6B7280"}


def get_class_colour(cls):
    for k, v in CLASS_COLOURS.items():
        if k.lower() in str(cls).lower():
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
    h1 {{ color:{HEADING}; font-weight:900; letter-spacing:-1px; font-size:2.8rem !important; }}
    h2 {{ color:{HEADING}; font-weight:700; font-size:1.8rem !important; border-bottom:3px solid {TEAL}; padding-bottom:8px; }}
    h3 {{ color:{TEAL}; font-weight:600; font-size:1.4rem !important; }}
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
    .cbox-d {{ background:{BG_CARD}; border:1px solid {DANGER}; border-left:4px solid {DANGER}; border-radius:10px; padding:16px 20px; margin-top:12px; color:{TEXT_PRIMARY}; }}
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


def style_chart(ch, h=400):
    return ch.properties(background=CHART_BG, height=h).configure_axis(labelColor=CHART_AXIS, titleColor=CHART_AXIS, gridColor=CHART_GRID, labelFontSize=12, titleFontSize=14, grid=True).configure_view(stroke=BORDER, strokeWidth=1)


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

# ── NAV ──


def nav_to(v): st.session_state.current_view = v


view = st.session_state.current_view

if view != "Home":
    nl, nm, nr = st.columns([2, 8, 1])
    with nl:
        st.markdown(
            f'<div style="padding:4px 0;"><span style="font-size:1.6rem;font-weight:900;color:{NAV_LOGO};">💊 Cardiokinetics</span></div>', unsafe_allow_html=True)
        search_term = st.text_input(
            "Search", placeholder="Search by Drug Name or Class...", label_visibility="collapsed")
    with nm:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        views = ["Home", "Table View", "Drugs by Class",
                 "Individual Drug View", "PK Calculator", "PK Graph", "About"]
        icons = ["🏠", "📊", "🏷️", "💊", "🧮", "📈", "ℹ️"]
        cs = st.columns(len(views), gap="small")
        for c, v, ic in zip(cs, views, icons):
            with c:
                if st.button(f"{ic} {v}", key=f"n_{v}", use_container_width=True):
                    nav_to(v)
        _cs = st.columns(len(views), gap="small")
        for _c, _v in zip(_cs, views):
            with _c:
                clr = TEAL if view == _v else (
                    BORDER if not IS_NIGHT else "#334155")
                st.markdown(
                    f'<div style="height:3px;background:{clr};border-radius:2px;margin-top:-8px;"></div>', unsafe_allow_html=True)
    with nr:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("☀️" if IS_NIGHT else "🌙", key="tt", use_container_width=True):
            st.session_state.theme = "day" if IS_NIGHT else "night"
            st.rerun()
    st.markdown("---")
else:
    search_term = ""

# ══════════════════════════════════════════════
#  HOME
# ══════════════════════════════════════════════
if view == "Home":
    _, tc = st.columns([9, 1])
    with tc:
        if st.button("☀️ Day" if IS_NIGHT else "🌙 Night", key="ht"):
            st.session_state.theme = "day" if IS_NIGHT else "night"
            st.rerun()
    st.markdown(f"""
    <div style="text-align:center;padding:30px 20px 20px;">
        <div style="font-size:4rem;font-weight:900;color:{HEADING};letter-spacing:-2px;">💊 Cardiokinetics</div>
        <div style="font-size:1.3rem;color:{TEXT_SECONDARY};margin-top:12px;max-width:700px;margin:12px auto;line-height:1.6;">
            A digital pharmacokinetic decision support system for interpreting therapeutic drug monitoring in hypertension</div>
        <div style="margin-top:20px;"><span style="padding:6px 16px;background:linear-gradient(135deg,{TEAL},{BLUE});color:white;border-radius:20px;font-size:0.85rem;font-weight:600;">
            20 Antihypertensive Agents · 12 PK Calculators · 5 Graph Modes</span></div>
    </div>""", unsafe_allow_html=True)
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    cards = [("📊", "Table View", "Browse the complete PK database with search and filtering", BLUE),
             ("🏷️", "Drugs by Class",
              "Explore agents grouped by therapeutic class", PURPLE),
             ("💊", "Individual Drug View",
              "Full pharmacokinetic profile card for any agent", DARK_TEAL),
             ("🧮", "PK Calculator",
              "Eleven calculators plus therapeutic window checker", SUCCESS),
             ("📈", "PK Graph", "Elimination curves, drug comparison, multi-drug screen, TDM overlay", CORAL),
             ("ℹ️", "About", "How to use Cardiokinetics and what each module does", TEXT_SECONDARY)]
    cs = st.columns(6, gap="medium")
    for i, (ic, lb, ds, cl) in enumerate(cards):
        with cs[i]:
            st.markdown(f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-top:5px solid {cl};border-radius:14px;padding:28px 16px;text-align:center;min-height:260px;box-shadow:0 2px 12px rgba(0,0,0,0.06);display:flex;flex-direction:column;justify-content:center;"><div style="font-size:3rem;margin-bottom:10px;">{ic}</div><div style="font-size:1.15rem;font-weight:800;color:{HEADING};margin-bottom:8px;">{lb}</div><div style="font-size:0.9rem;color:{TEXT_SECONDARY};line-height:1.5;">{ds}</div></div>', unsafe_allow_html=True)
            if st.button(f"Open {lb}", key=f"h_{lb}", use_container_width=True):
                nav_to(lb)

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
        st.dataframe(filt, use_container_width=True,
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
                             hide_index=True, use_container_width=True)

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
    st.header("Pharmacokinetic Calculator")
    t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12 = st.tabs(
        ["Bioavailability", "Cmin", "Clearance", "t½ / ke", "Steady State", "Therapeutic Window",
         "Vd", "Loading Dose", "Maintenance Dose", "IV Infusion Css", "Time to Steady State", "ke (2-point)"])
    with t1:
        st.subheader("Bioavailability (F)")
        st.latex(
            r"F = \frac{AUC_{oral} \cdot Dose_{IV}}{AUC_{IV} \cdot Dose_{oral}}")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Oral**")
            ao = st.number_input("AUC (Oral)", min_value=0.0,
                                 value=0.0, step=0.1, key="bo")
            do = st.number_input("Dose (Oral)", min_value=0.0,
                                 value=0.0, step=1.0, key="do")
        with c2:
            st.markdown("**IV**")
            ai = st.number_input("AUC (IV)", min_value=0.0,
                                 value=0.0, step=0.1, key="bi")
            di = st.number_input("Dose (IV)", min_value=0.0,
                                 value=0.0, step=1.0, key="di")
        if st.button("Calculate F", use_container_width=True, key="bf"):
            if do > 0 and ai > 0 and di > 0:
                fv = (ao*di)/(ai*do)
                st.success(f"**F:** {fv:.4f} ({fv*100:.2f}%)")
            else:
                st.error("Enter non-zero values.")
    with t2:
        st.subheader("Cmin (Trough)")
        st.latex(r"C_{min}=C_{max}\cdot e^{-k_e\cdot t}")
        cm = st.number_input("Cmax", min_value=0.0, value=100.0, key="cm")
        th = st.number_input("t½ (h)", min_value=0.1, value=12.0, key="th")
        iv = st.number_input("Interval (h)", min_value=0.0,
                             value=24.0, key="iv")
        if st.button("Calculate", use_container_width=True, key="cb"):
            ke = 0.693/th
            st.success(f"**Cmin:** {cm*math.exp(-ke*iv):.2f} (ke={ke:.4f}/h)")
    with t3:
        st.subheader("Clearance")
        st.latex(r"CL=\frac{F\cdot Dose}{AUC}")
        cd = st.number_input("Dose (mg)", min_value=0.0, value=500.0, key="cd")
        cf = st.number_input("F [0-1]", min_value=0.0,
                             max_value=1.0, value=1.0, step=0.05, key="cf")
        ca = st.number_input("AUC", min_value=0.0, value=100.0, key="ca")
        if st.button("Calculate", use_container_width=True, key="cc"):
            if ca > 0:
                st.success(f"**CL:** {(cf*cd)/ca:.2f} L/h")
    with t4:
        st.subheader("t½ ↔ ke")
        mode = st.radio("Calculate:", ["t½", "ke"], key="hm", horizontal=True)
        if mode == "t½":
            ki = st.number_input("k (1/h)", min_value=0.0001,
                                 value=0.1, format="%.4f", key="hk")
            if st.button("Convert", use_container_width=True, key="h1"):
                st.success(f"**t½:** {0.693/ki:.2f} h")
        else:
            ti = st.number_input("t½ (h)", min_value=0.1,
                                 value=12.0, key="ht2")
            if st.button("Convert", use_container_width=True, key="h2"):
                st.success(f"**ke:** {0.693/ti:.4f} /h")
    with t5:
        st.subheader("Steady State Simulator")
        c1, c2 = st.columns(2)
        with c1:
            sd = st.number_input(
                "Dose (mg)", min_value=0.0, value=100.0, key="sd")
            st_ = st.number_input("τ (h)", min_value=1.0, value=24.0, key="st")
        with c2:
            sh = st.number_input("t½ (h)", min_value=0.1, value=12.0, key="sh")
            sv = st.number_input("Vd (L)", min_value=0.1, value=50.0, key="sv")
        if st.button("Simulate", use_container_width=True, key="sb"):
            ke = 0.693/sh
            af = 1/(1-math.exp(-ke*st_))
            cmx = (sd/sv)*af
            cmn = cmx*math.exp(-ke*st_)
            cav = (sd/sv)/(ke*st_)
            m1, m2, m3 = st.columns(3)
            m1.metric("Css,max", f"{cmx:.2f}")
            m2.metric("Css,min", f"{cmn:.2f}")
            m3.metric("Css,avg", f"{cav:.2f}")
            ts, cs = [], []
            c_ = 0
            for i in range(5):
                c_ += (sd/sv)
                t0 = i*st_
                for t in np.linspace(0, st_, 20):
                    ts.append(t0+t)
                    cs.append(c_*math.exp(-ke*t))
                c_ *= math.exp(-ke*st_)
            st.altair_chart(style_chart(alt.Chart(pd.DataFrame({"Time (h)": ts, "Conc": cs})).mark_line(
                color=line_colour, strokeWidth=2.5).encode(x='Time (h)', y='Conc'), 300), use_container_width=True)
    with t6:
        st.subheader("Therapeutic Window Checker")
        st.markdown("Select a drug and enter the measured concentration.")
        if not df.empty:
            tw_d = st.selectbox(
                "Select Drug:", df['Name'].unique(), key="tw_d")
            tw_m = st.number_input(
                "Measured Concentration (ng/mL)", min_value=0.0, value=0.0, step=0.1, key="tw_m")
            if st.button("Check", use_container_width=True, key="tw_b"):
                if tw_m > 0:
                    pp = get_drug_params(df[df['Name'] == tw_d].iloc[0])
                    if pp['css_min'] and pp['css_max']:
                        if tw_m < pp['css_min']:
                            st.warning(
                                f"⚠️ **Sub-therapeutic**: {tw_m} ng/mL is below Css,min ({pp['css_min']}).")
                        elif tw_m > pp['css_max']:
                            st.error(
                                f"🚨 **Supra-therapeutic**: {tw_m} ng/mL exceeds Css,max ({pp['css_max']}).")
                        else:
                            st.success(
                                f"✅ **Within range**: {tw_m} ng/mL is between Css,min ({pp['css_min']}) and Css,max ({pp['css_max']}).")
                    else:
                        st.info(f"No Css range data for {tw_d}.")
    with t7:
        st.subheader("Volume of Distribution (Vd)")
        st.latex(r"V_d=\frac{Dose \cdot F}{k_e \cdot AUC}")
        vd_dose = st.number_input("Dose (mg)", min_value=0.0, value=500.0, key="vd_dose")
        vd_f = st.number_input("F [0-1]", min_value=0.01, max_value=1.0, value=1.0, step=0.05, key="vd_f")
        vd_ke = st.number_input("ke (1/h)", min_value=0.0001, value=0.05, format="%.4f", key="vd_ke")
        vd_auc = st.number_input("AUC", min_value=0.01, value=100.0, key="vd_auc")
        if st.button("Calculate Vd", use_container_width=True, key="vd_b"):
            vd = (vd_dose*vd_f)/(vd_ke*vd_auc)
            st.success(f"**Vd:** {vd:.2f} L")
    with t8:
        st.subheader("Loading Dose")
        st.latex(r"LD=\frac{C_{target} \cdot V_d}{F}")
        ld_ct = st.number_input("Target Concentration (mg/L)", min_value=0.0, value=2.0, key="ld_ct")
        ld_vd = st.number_input("Vd (L)", min_value=0.01, value=50.0, key="ld_vd")
        ld_f = st.number_input("F [0-1]", min_value=0.01, max_value=1.0, value=1.0, step=0.05, key="ld_f")
        if st.button("Calculate Loading Dose", use_container_width=True, key="ld_b"):
            ld = (ld_ct*ld_vd)/ld_f
            st.success(f"**Loading Dose:** {ld:.2f} mg")
    with t9:
        st.subheader("Maintenance Dose Rate")
        st.latex(r"\text{Dose Rate}=\frac{CL \cdot C_{ss,avg}}{F}")
        md_cl = st.number_input("Clearance (L/h)", min_value=0.01, value=5.0, key="md_cl")
        md_css = st.number_input("Target Css,avg (mg/L)", min_value=0.0, value=1.0, key="md_css")
        md_f = st.number_input("F [0-1]", min_value=0.01, max_value=1.0, value=1.0, step=0.05, key="md_f")
        if st.button("Calculate Dose Rate", use_container_width=True, key="md_b"):
            mdr = (md_cl*md_css)/md_f
            st.success(f"**Maintenance Dose Rate:** {mdr:.3f} mg/h")
    with t10:
        st.subheader("IV Infusion Steady-State Concentration")
        st.latex(r"C_{ss}=\frac{R_0}{CL}")
        inf_r0 = st.number_input("Infusion Rate R₀ (mg/h)", min_value=0.0, value=10.0, key="inf_r0")
        inf_cl = st.number_input("Clearance (L/h)", min_value=0.01, value=5.0, key="inf_cl")
        if st.button("Calculate Css", use_container_width=True, key="inf_b"):
            css_inf = inf_r0/inf_cl
            st.success(f"**Css:** {css_inf:.3f} mg/L")
    with t11:
        st.subheader("Time to Steady State")
        st.latex(r"t_{ss}\approx n \cdot t_{1/2}\quad(n=4\text{–}5)")
        tss_th = st.number_input("t½ (h)", min_value=0.1, value=12.0, key="tss_th")
        tss_n = st.slider("Number of half-lives (n)", 3, 6, 5, key="tss_n")
        if st.button("Calculate Time to Steady State", use_container_width=True, key="tss_b"):
            tss = tss_n*tss_th
            st.success(f"**Time to Steady State:** ~{tss:.1f} h ({tss/24:.1f} days)")
    with t12:
        st.subheader("ke from Two Measured Concentrations")
        st.latex(r"k_e=\frac{\ln(C_1/C_2)}{t_2-t_1}")
        ke2_c1 = st.number_input("C1 (ng/mL)", min_value=0.0001, value=100.0, key="ke2_c1")
        ke2_t1 = st.number_input("t1 (h)", min_value=0.0, value=2.0, key="ke2_t1")
        ke2_c2 = st.number_input("C2 (ng/mL)", min_value=0.0001, value=25.0, key="ke2_c2")
        ke2_t2 = st.number_input("t2 (h)", min_value=0.0, value=10.0, key="ke2_t2")
        if st.button("Calculate ke", use_container_width=True, key="ke2_b"):
            if ke2_t2 > ke2_t1 and ke2_c1 > 0 and ke2_c2 > 0:
                ke2 = math.log(ke2_c1/ke2_c2)/(ke2_t2-ke2_t1)
                st.success(f"**ke:** {ke2:.4f} /h → **t½:** {0.693/ke2:.2f} h")
            else:
                st.error("t2 must be greater than t1, and concentrations must be positive.")

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

    with c1:
        st.subheader("Select Drug")
        drug_map = {}
        dc = [c for c in df.columns if any(kw in c.lower() for kw in [
                                           'dose', 'strength', 'mg'])]
        pdc = dc[0] if dc else None
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
            dn1 = str(dr['Name'])

            gm = st.radio("Mode:", ["Standard Elimination", "Accumulation Comparison",
                          "Steady State Oscillation", "Drug Comparison", "Multi-Drug Screen"])
            g_time = st.slider("Time (hours)", 6, 720, 48)

            if gm == "Drug Comparison":
                ol = [l for l in drug_map.keys() if l != sel]
                if ol:
                    cmp_lb = st.selectbox("Compare with:", ol, key="cmp")
                    cmp_params = get_drug_params(df.loc[drug_map[cmp_lb]])
                    cmp_name = str(df.loc[drug_map[cmp_lb]]['Name'])

            if gm == "Multi-Drug Screen":
                ol = [l for l in drug_map.keys() if l != sel]
                multi_sel = st.multiselect(
                    "Add drugs (up to 4 more):", ol, max_selections=4, key="multi")
                multi_drugs = [(str(df.loc[drug_map[l]]['Name']), get_drug_params(
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
                    ch = alt.Chart(cd).mark_line(color=line_colour, strokeWidth=3).encode(
                        x='Time (hours)', y='Concentration (ng/mL)', tooltip=['Time (hours)', 'Concentration (ng/mL)'])
                    if used_cmax_sd > 0:
                        cd['U'] = (used_cmax+used_cmax_sd)*np.exp(-k*tp)
                        cd['L'] = np.maximum(
                            0, (used_cmax-used_cmax_sd)*np.exp(-k*tp))
                        ch = alt.Chart(cd).mark_area(opacity=0.15, color=TEAL).encode(
                            x='Time (hours)', y='L', y2='U')+ch
                    if calc_pt is not None:
                        ch += alt.Chart(calc_pt).mark_circle(color=DANGER, size=200).encode(
                            x='Time (hours)', y='Concentration (ng/mL)')
                    if tdm_pt is not None:
                        ch += alt.Chart(tdm_pt).mark_point(color=PURPLE, size=300, shape="diamond",
                                                           filled=True).encode(x='Time (hours)', y='Concentration (ng/mL)')
                    if lod > 0:
                        ch += alt.Chart(pd.DataFrame({'y': [lod]})).mark_rule(
                            color=WARNING, strokeDash=[5, 5], strokeWidth=2).encode(y='y')
                    if p['det_window'] and p['det_window'] <= g_time:
                        ch += alt.Chart(pd.DataFrame({'x': [p['det_window']]})).mark_rule(
                            color=DANGER, strokeDash=[3, 3], strokeWidth=2).encode(x='x')
                    st.altair_chart(style_chart(ch), use_container_width=True)
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
                        index=False), "elimination.csv", "text/csv", use_container_width=True)
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
                        report_lines), "pk_report.txt", "text/plain", use_container_width=True)

            # ── ACCUMULATION COMPARISON ──
            elif gm == "Accumulation Comparison":
                st.subheader("Accumulation Comparison")
                if p['sd_cmax'] and p['css_max']:
                    tp = np.linspace(0, g_time, 100)
                    cd = pd.concat([pd.DataFrame({"Time (hours)": tp, "Concentration (ng/mL)": p['sd_cmax']*np.exp(-k*tp), "Profile": "Single Dose"}),
                                    pd.DataFrame({"Time (hours)": tp, "Concentration (ng/mL)": p['css_max']*np.exp(-k*tp), "Profile": "Steady State"})])
                    ch = alt.Chart(cd).mark_line(strokeWidth=3).encode(x='Time (hours)', y='Concentration (ng/mL)', color=alt.Color('Profile:N', scale=alt.Scale(
                        domain=['Single Dose', 'Steady State'], range=[TEAL, CORAL])), tooltip=['Time (hours)', 'Concentration (ng/mL)', 'Profile'])
                    st.altair_chart(style_chart(ch).configure_legend(
                        titleColor=CHART_AXIS, labelColor=CHART_AXIS, orient='top-right'), use_container_width=True)
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
                    base = alt.Chart(cd).mark_line(color=line_colour, strokeWidth=3).encode(x=alt.X(
                        'Time (hours)', title=f'Time (hours) — τ = {tau:.1f}h'), y=alt.Y('Concentration (ng/mL)', scale=alt.Scale(domain=[0, p['css_max']*1.2])))
                    rl = [{'y': p['css_max'], 'label': 'Css,max'},
                          {'y': p['css_min'], 'label': 'Css,min'}]
                    if p['css_avg']:
                        rl.append({'y': p['css_avg'], 'label': 'Css,avg'})
                    rdf = pd.DataFrame(rl)
                    dom = ['Css,max', 'Css,avg', 'Css,min']
                    rng = [DANGER, SUCCESS, WARNING]
                    rc = alt.Chart(rdf).mark_rule(strokeDash=[4, 4], strokeWidth=2).encode(
                        y='y', color=alt.Color('label:N', scale=alt.Scale(domain=dom, range=rng)))
                    tc = alt.Chart(rdf).mark_text(align='left', dx=5, dy=-8, fontWeight='bold', fontSize=12).encode(
                        y='y', text='label', color=alt.Color('label:N', scale=alt.Scale(domain=dom, range=rng)))
                    st.altair_chart(style_chart(
                        base+rc+tc).configure_legend(disable=True), use_container_width=True)
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
                    cd = pd.concat([pd.DataFrame({"Time (hours)": tp, "Concentration (ng/mL)": c1v*np.exp(-k1*tp), "Drug": dn1}),
                                    pd.DataFrame({"Time (hours)": tp, "Concentration (ng/mL)": c2v*np.exp(-k2*tp), "Drug": cmp_name})])
                    ch = alt.Chart(cd).mark_line(strokeWidth=3).encode(x='Time (hours)', y='Concentration (ng/mL)',
                                                                       color=alt.Color('Drug:N', scale=alt.Scale(domain=[dn1, cmp_name], range=[
                                                                                       TEAL, CORAL]), legend=alt.Legend(title=None)),
                                                                       tooltip=['Time (hours)', 'Concentration (ng/mL)', 'Drug'])
                    st.altair_chart(style_chart(ch).configure_legend(titleColor=CHART_AXIS, labelColor=CHART_AXIS,
                                    orient='top-right', labelFontSize=13, symbolStrokeWidth=3), use_container_width=True)
                    longer = dn1 if p['thalf'] > cmp_params['thalf'] else cmp_name
                    st.markdown(
                        f'<div class="cbox"><strong>{dn1}</strong> (t½={p["thalf"]:.1f}h) vs <strong>{cmp_name}</strong> (t½={cmp_params["thalf"]:.1f}h). <strong>{longer}</strong> has the longer detection window.</div>', unsafe_allow_html=True)
                    dl = cd.copy()
                    dl["Time (hours)"] = dl["Time (hours)"].apply(sig_figs)
                    dl["Concentration (ng/mL)"] = dl["Concentration (ng/mL)"].apply(sig_figs)
                    st.download_button("📥 Download CSV", dl.to_csv(
                        index=False), "comparison.csv", "text/csv", use_container_width=True)
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
                        names = [f[0] for f in all_drugs if f[1]['thalf']]
                        ch = alt.Chart(cd).mark_line(strokeWidth=3).encode(x='Time (hours)', y='Concentration (ng/mL)',
                                                                           color=alt.Color('Drug:N', scale=alt.Scale(
                                                                               domain=names, range=palette[:len(names)]), legend=alt.Legend(title=None)),
                                                                           tooltip=['Time (hours)', 'Concentration (ng/mL)', 'Drug'])
                        if lod > 0:
                            ch += alt.Chart(pd.DataFrame({'y': [lod]})).mark_rule(
                                color=WARNING, strokeDash=[5, 5], strokeWidth=2).encode(y='y')
                        st.altair_chart(style_chart(ch).configure_legend(titleColor=CHART_AXIS, labelColor=CHART_AXIS,
                                        orient='top-right', labelFontSize=12, symbolStrokeWidth=3), use_container_width=True)
                        # Interpretation
                        if lod > 0:
                            lines = []
                            for name, pp in all_drugs:
                                if pp['thalf'] and pp['thalf'] > 0 and (pp['sd_cmax'] or pp['cmax']):
                                    cv = pp['sd_cmax'] or pp['cmax']
                                    kk = 0.693/pp['thalf']
                                    if cv > lod:
                                        dw = -(1/kk)*np.log(lod/cv)
                                        lines.append(
                                            f"**{name}**: detectable for ~{dw:.0f}h ({dw/24:.1f} days)")
                                    else:
                                        lines.append(
                                            f"**{name}**: Cmax below LoD")
                            st.markdown(
                                f'<div class="cbox"><strong>📋 Detection Windows (LoD = {lod} ng/mL):</strong><br>{"<br>".join(lines)}</div>', unsafe_allow_html=True)
                        dl = cd.copy()
                        dl["Time (hours)"] = dl["Time (hours)"].apply(sig_figs)
                        dl["Concentration (ng/mL)"] = dl["Concentration (ng/mL)"].apply(sig_figs)
                        st.download_button("📥 Download CSV", dl.to_csv(
                            index=False), "multi_drug.csv", "text/csv", use_container_width=True)
                else:
                    st.info(
                        "Select at least one additional drug from the sidebar to compare.")
