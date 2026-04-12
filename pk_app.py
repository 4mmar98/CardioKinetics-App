import streamlit as st
import pandas as pd
import numpy as np
import os
import math
import re
import altair as alt

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Cardiokinetics",
    layout="wide"
)

# --- CUSTOM CSS FOR HOSPITAL BLUE THEME (LARGE SIZE) ---
st.markdown("""
<style>
    /* Global Text Styles - Increased Base Size */
    html, body, [class*="css"] {
        font-size: 18px;
        color: #000000;
    }

    /* MAXIMIZE WIDTH: Reduce padding to fit more columns */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }
    
    /* Headers - Hospital Blue Theme & Larger */
    h1 {
        color: #003366; /* Dark Navy Blue */
        font-weight: 800;
        letter-spacing: -0.5px;
        padding-top: 0px;
        font-size: 3.5rem !important; /* Much larger title */
    }
    h2 {
        color: #004080; /* Medium Navy */
        font-weight: 700;
        border-bottom: 3px solid #003366;
        padding-bottom: 10px;
        margin-top: 20px;
        font-size: 2.2rem !important;
    }
    h3 {
        color: #0059b3; /* Bright Blue */
        font-weight: 600;
        font-size: 1.6rem !important;
    }
    
    /* Button Styling - SOLID BLUE BACKGROUND WITH WHITE TEXT */
    div.stButton > button {
        background-color: #003366 !important; 
        color: #FFFFFF !important; 
        font-weight: 800;
        height: 65px; 
        font-size: 1.2rem !important; 
        border: 3px solid #003366 !important;
        border-radius: 10px;
        width: 100%;
        transition: all 0.2s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-top: 10px; 
    }
    
    div.stButton > button:hover {
        background-color: #004080 !important; 
        border-color: #004080 !important;
        color: #FFFFFF !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(0,0,0,0.2);
    }
    
    div.stButton > button:active {
        background-color: #002244 !important; 
        border-color: #002244 !important;
        transform: translateY(0);
        color: #FFFFFF !important;
    }

    /* --- FIXED INPUT STYLING --- */
    div[data-baseweb="input"] {
        min-height: 65px; 
        border-radius: 10px; 
        background-color: #003366; 
        border: 2px solid #003366;
        display: flex;
        align-items: center; 
    }
    
    div[data-baseweb="select"] > div {
        min-height: 65px;
        border-radius: 10px;
        border: 2px solid #003366;
        background-color: #003366; 
        display: flex;
        align-items: center;
    }
    
    div[data-baseweb="input"] input {
        font-size: 1.2rem;
        color: #FFFFFF; 
        caret-color: #FFFFFF; 
        padding-left: 10px;
        height: 100%; 
        min-height: 60px;
    }
    
    div[data-baseweb="select"] div {
        font-size: 1.2rem;
        color: #FFFFFF; 
    }
    
    div[data-baseweb="input"] input[type="number"] {
         color: #FFFFFF;
    }
    
    div[data-baseweb="select"] svg {
        fill: #FFFFFF;
    }

    /* Metric Cards Styling */
    div[data-testid="metric-container"] {
        background-color: #F0F7FF; 
        border: 2px solid #0059b3;
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        transition: all 0.2s ease;
    }
    div[data-testid="metric-container"]:hover {
        border-color: #003366;
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    div[data-testid="metric-container"] label {
        color: #004080;
        font-weight: 700;
        font-size: 1.2rem !important;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #002244;
        font-size: 2.5rem !important; 
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px; 
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        font-size: 1.2rem;
        white-space: pre-wrap;
        background-color: #FFFFFF; 
        border: 2px solid #003366; 
        border-radius: 8px;
        color: #003366; 
        font-weight: 700;
        flex-grow: 1; 
        text-align: center;
    }
    .stTabs [aria-selected="true"] {
        background-color: #003366; 
        color: #FFFFFF; 
        border: 2px solid #003366;
    }
</style>
""", unsafe_allow_html=True)

# --- DATA LOADING FUNCTION ---
@st.cache_data
def load_data():
    def clean_header(c):
        # Remove line breaks from new headers (e.g. SINGLE DOSE\nCmax)
        original = str(c).strip().replace('\n', ' ')
        
        if original.lower() == "auc" or "auc" in original.lower():
            return "Area Under the Curve (AUC) [ng.hr/mL]"
            
        c_title = original.title()
        
        # Restore specific unit capitalization
        c_title = c_title.replace("Ng/Ml", "ng/mL")
        c_title = c_title.replace("Ug/Ml", "µg/mL")
        c_title = c_title.replace("Mg/L", "mg/L")
        c_title = c_title.replace("Ng.Hr/Ml", "ng.hr/mL") 
        c_title = c_title.replace("Ng*H/Ml", "ng.hr/mL")
        c_title = c_title.replace("Ml/Min", "mL/min")
        c_title = c_title.replace("L/Min", "L/min")
        c_title = c_title.replace("Iv", "IV")
        
        # Clean up the newly added 9 columns from Excel
        c_title = c_title.replace("Css,Max", "Css,max")
        c_title = c_title.replace("Css,Min", "Css,min")
        c_title = c_title.replace("Css,Avg", "Css,avg")
        c_title = c_title.replace("Lod", "LOD")
        c_title = c_title.replace("Det. Window", "Detection Window")
        c_title = c_title.replace("Single Dose", "Single Dose")
        c_title = c_title.replace("R (Accum. Factor)", "Accumulation Factor (R)")
        c_title = c_title.replace("(H)", "(h)")
        c_title = c_title.replace("(Days)", "(days)")
        
        return c_title

    file_options = ["top_20_antihypertensive.xlsx", "drug_data.xlsx"]
    selected_file = None
    
    for f in file_options:
        if os.path.exists(f):
            selected_file = f
            break
            
    if selected_file:
        try:
            df = pd.read_excel(selected_file)
            rename_map = {"Drug": "Name", "Drug Class": "Class", "Dosage (mg)": "Dose"}
            df = df.rename(columns=rename_map)
            df.columns = [clean_header(c) for c in df.columns]
            
            if 'Name' not in df.columns:
                st.error(f"Error: '{selected_file}' must have a column labeled 'Name' (or 'Drug').")
                return pd.DataFrame() 
            if 'Class' not in df.columns:
                df['Class'] = "Uncategorized"
                
            return df
        except Exception as e:
            st.error(f"Error reading Excel file: {e}")
            return pd.DataFrame()
    else:
        st.warning("⚠️ No data file found. Displaying mock data.")
        INITIAL_DATA = [
            {"Name": "Lisinopril", "Class": "ACE Inhibitor", "Half-Life": "12h", "Cmax": "40 ng/mL", "Area Under the Curve (AUC) [ng.hr/mL]": "500 ng·h/mL", "Bioavailability": "25%", "Clearance": "50 mL/min"},
        ]
        return pd.DataFrame(INITIAL_DATA)

df = load_data()

def extract_numeric(val_str):
    if isinstance(val_str, (int, float)):
        return float(val_str)
    val_str = str(val_str)
    if '±' in val_str:
        val_str = val_str.split('±')[0]
    match = re.search(r"[-+]?\d*\.?\d+", val_str)
    if match:
        return float(match.group())
    return None

# --- NAVIGATION & HEADER ---
if 'current_view' not in st.session_state:
    st.session_state.current_view = "Table View"

top_left, top_right = st.columns([1, 2])

with top_left:
    st.title("Cardiokinetics")
    search_term = st.text_input("Search", placeholder="Search by Drug Name or Class...", label_visibility="collapsed")

with top_right:
    st.markdown("<br>", unsafe_allow_html=True)
    nav_btn1, nav_btn2, nav_btn3, nav_btn4, nav_btn5 = st.columns(5, gap="medium")
    
    with nav_btn1:
        if st.button("Table View", use_container_width=True): st.session_state.current_view = "Table View"
    with nav_btn2:
        if st.button("Drugs by Class", use_container_width=True): st.session_state.current_view = "Drugs by Class"
    with nav_btn3:
        if st.button("Individual View", use_container_width=True): st.session_state.current_view = "Individual Drug View"
    with nav_btn4:
        if st.button("PK Calculator", use_container_width=True): st.session_state.current_view = "PK Calculator"
    with nav_btn5:
        if st.button("PK Graph", use_container_width=True): st.session_state.current_view = "PK Graph"

st.markdown("---")
view_option = st.session_state.current_view

# --- VIEW 1: TABLE VIEW ---
if view_option == "Table View":
    if not df.empty:
        if search_term:
            filtered_df = df[
                df['Name'].astype(str).str.contains(search_term, case=False) | 
                df['Class'].astype(str).str.contains(search_term, case=False)
            ]
        else:
            filtered_df = df
        st.write(f"Showing {len(filtered_df)} records")
        st.dataframe(filtered_df, use_container_width=True, hide_index=True, height=800)
    else:
        st.info("No data available to display in table.")

# --- VIEW 2: DRUGS BY CLASS ---
elif view_option == "Drugs by Class":
    st.header("Therapeutic Class Overview")
    if not df.empty:
        drug_classes = df['Class'].unique()
        for drug_class in drug_classes:
            class_subset = df[df['Class'] == drug_class]
            count = len(class_subset)
            with st.expander(f"{drug_class} ({count} Drugs)"):
                display_cols = [c for c in class_subset.columns if c != 'Class']
                st.dataframe(class_subset[display_cols], hide_index=True, use_container_width=True)
    else:
        st.info("No data available to display classes.")

# --- VIEW 3: INDIVIDUAL VIEW ---
elif view_option == "Individual Drug View":
    st.header("Individual Pharmacokinetic Profile")
    if not df.empty:
        if search_term:
            filtered_names = df[df['Name'].astype(str).str.contains(search_term, case=False)]['Name'].unique()
            if len(filtered_names) == 0:
                 st.warning(f"No drugs found matching '{search_term}'")
                 filtered_names = df['Name'].unique()
        else:
            filtered_names = df['Name'].unique()

        selected_drug_name = st.selectbox("Select a Drug:", filtered_names)
        
        if selected_drug_name:
            drug = df[df['Name'] == selected_drug_name].iloc[0]
            st.info(f"**Therapeutic Class:** {drug['Class']}")
            st.subheader("Pharmacokinetic Parameters")
            params = [col for col in df.columns if col not in ['Name', 'Class', 'id', 'ID']]
            cols = st.columns(3)
            for i, param in enumerate(params):
                val = drug[param]
                with cols[i % 3]:
                    st.metric(label=param, value=str(val))
    else:
        st.info("No data available to display individual profiles.")

# --- VIEW 4: PK CALCULATOR ---
elif view_option == "PK Calculator":
    st.header("Pharmacokinetic Calculator")
    st.markdown("Estimate missing parameters using standard one-compartment models.")
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Bioavailability (F)", "Cmin (Trough)", "Clearance (CL)", "Half-Life / ke", "Steady State", "Therapeutic Window"])
    
    with tab1:
        st.subheader("Calculate Bioavailability (F)")
        st.latex(r"F = \frac{AUC_{oral} \cdot Dose_{IV}}{AUC_{IV} \cdot Dose_{oral}}")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Oral Administration**")
            auc_oral = st.number_input("AUC (Oral)", min_value=0.0, value=0.0, step=0.1, key="bio_auc_oral")
            dose_oral = st.number_input("Dose (Oral)", min_value=0.0, value=0.0, step=1.0, key="bio_dose_oral")
        with col2:
            st.markdown("**IV Administration**")
            auc_iv = st.number_input("AUC (IV)", min_value=0.0, value=0.0, step=0.1, key="bio_auc_iv")
            dose_iv = st.number_input("Dose (IV)", min_value=0.0, value=0.0, step=1.0, key="bio_dose_iv")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Calculate F", use_container_width=True, key="bio_calc_btn"):
            if dose_oral > 0 and auc_iv > 0 and dose_iv > 0:
                f_absolute = (auc_oral * dose_iv) / (auc_iv * dose_oral)
                st.success(f"**Bioavailability (F):** {f_absolute:.4f} ({f_absolute*100:.2f}%)")
            else:
                st.error("Please enter non-zero values for Doses and IV AUC.")

    with tab2:
        st.subheader("Estimate Cmin (Trough Concentration)")
        st.latex(r"C_{min} = C_{max} \cdot e^{-k_e \cdot t} \quad \text{where} \quad k_e = \frac{0.693}{t_{1/2}}")
        cmax = st.number_input("Cmax (Peak Concentration)", min_value=0.0, value=100.0, key="cmin_cmax")
        t_half = st.number_input("Half-Life (t½ in hours)", min_value=0.1, value=12.0, key="cmin_thalf")
        interval = st.number_input("Time since peak / Dosing Interval (hours)", min_value=0.0, value=24.0, key="cmin_interval")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Calculate Cmin", use_container_width=True, key="cmin_calc_btn"):
            if t_half > 0:
                k = 0.693 / t_half
                cmin = cmax * math.exp(-k * interval)
                st.info(f"Elimination Rate Constant (k): {k:.4f} /h")
                st.success(f"**Estimated Trough (Cmin):** {cmin:.2f}")
            else:
                st.error("Half-life must be greater than 0.")

    with tab3:
        st.subheader("Calculate Clearance (CL)")
        st.latex(r"CL = \frac{F \cdot Dose}{AUC}")
        cl_dose = st.number_input("Dose (mg)", min_value=0.0, value=500.0, key="cl_dose")
        cl_f = st.number_input("Bioavailability (F) [0 to 1]", min_value=0.0, max_value=1.0, value=1.0, step=0.05, key="cl_f")
        cl_auc = st.number_input("AUC (mg·h/L)", min_value=0.0, value=100.0, key="cl_auc")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Calculate CL", use_container_width=True, key="cl_calc_btn"):
            if cl_auc > 0:
                clearance = (cl_f * cl_dose) / cl_auc
                st.success(f"**Clearance (CL):** {clearance:.2f} L/h")
            else:
                st.error("AUC must be greater than 0.")

    with tab4:
        st.subheader("Half-Life ↔ Elimination Constant Converter")
        st.latex(r"t_{1/2} = \frac{\ln(2)}{k_e} \approx \frac{0.693}{k_e}")
        calc_mode = st.radio("I want to calculate:", ["Half-Life (t½)", "Elimination Constant (k)"], key="hl_calc_mode")
        if calc_mode == "Half-Life (t½)":
            k_input = st.number_input("Enter Elimination Constant (k) [1/h]", min_value=0.0001, value=0.1, format="%.4f", key="hl_k_input")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Convert to t½", use_container_width=True, key="hl_calc_btn1"):
                st.success(f"**Half-Life:** {0.693/k_input:.2f} hours")
        else:
            t_input = st.number_input("Enter Half-Life (t½) [hours]", min_value=0.1, value=12.0, key="hl_t_input")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Convert to k", use_container_width=True, key="hl_calc_btn2"):
                st.success(f"**Elimination Constant (k):** {0.693/t_input:.4f} /h")

    with tab5:
        st.subheader("Steady State Simulator")
        st.markdown("Estimate peak, trough, and average concentrations at steady state ($C_{ss}$).")
        col1, col2 = st.columns(2)
        with col1:
            ss_dose = st.number_input("Dose (mg)", min_value=0.0, value=100.0, key="ss_dose")
            ss_interval = st.number_input("Dosing Interval (τ in hours)", min_value=1.0, value=24.0, key="ss_interval")
        with col2:
            ss_thalf = st.number_input("Half-Life (t½ in hours)", min_value=0.1, value=12.0, key="ss_thalf")
            ss_vd = st.number_input("Volume of Distribution (Vd in L)", min_value=0.1, value=50.0, key="ss_vd")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Simulate Steady State", use_container_width=True, key="ss_calc_btn"):
            if ss_thalf > 0 and ss_vd > 0:
                k = 0.693 / ss_thalf
                accumulation_factor = 1 / (1 - math.exp(-k * ss_interval))
                cmax_ss = (ss_dose / ss_vd) * accumulation_factor
                cmin_ss = cmax_ss * math.exp(-k * ss_interval)
                cavg_ss = (ss_dose / ss_vd) / (k * ss_interval) 
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Peak (Cmax,ss)", f"{cmax_ss:.2f} mg/L")
                m2.metric("Trough (Cmin,ss)", f"{cmin_ss:.2f} mg/L")
                m3.metric("Average (Cavg,ss)", f"{cavg_ss:.2f} mg/L")
                
                sim_times = []
                sim_concs = []
                c = 0
                for i in range(5): 
                    c += (ss_dose / ss_vd)
                    t_start = i * ss_interval
                    for t_step in np.linspace(0, ss_interval, 20):
                        sim_times.append(t_start + t_step)
                        sim_concs.append(c * math.exp(-k * t_step))
                    c = c * math.exp(-k * ss_interval)
                
                chart_df = pd.DataFrame({"Time (h)": sim_times, "Conc": sim_concs})
                ss_chart = alt.Chart(chart_df).mark_line(color="#FFFFFF", strokeWidth=2).encode(
                    x='Time (h)', y='Conc'
                ).properties(background='#003366', height=300).configure_axis(
                    labelColor='#FFFFFF', titleColor='#FFFFFF', gridColor='#406080'
                ).configure_view(stroke=None)
                st.altair_chart(ss_chart, use_container_width=True)
                st.caption("Simulation of accumulation over 5 dosing intervals.")
            else:
                st.error("Half-life and Vd must be > 0.")

    with tab6:
        st.subheader("Therapeutic Window Checker")
        st.markdown("Check if a measured concentration falls within the safe therapeutic range.")
        col1, col2, col3 = st.columns(3)
        with col1:
            measured_conc = st.number_input("Measured Concentration", min_value=0.0, value=25.0, key="tw_measured")
        with col2:
            min_therapeutic = st.number_input("Min Therapeutic Level", min_value=0.0, value=10.0, key="tw_min")
        with col3:
            max_therapeutic = st.number_input("Max Therapeutic Level", min_value=0.0, value=30.0, key="tw_max")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Check Status", use_container_width=True, key="tw_check_btn"):
            if measured_conc < min_therapeutic:
                st.warning(f"⚠️ **Sub-therapeutic**: {measured_conc} is below the effective range ({min_therapeutic}-{max_therapeutic}).")
            elif measured_conc > max_therapeutic:
                st.error(f"🚨 **Toxic**: {measured_conc} is above the safe range ({min_therapeutic}-{max_therapeutic}).")
            else:
                st.success(f"✅ **Therapeutic**: {measured_conc} is within the target range ({min_therapeutic}-{max_therapeutic}).")

# --- VIEW 5: PK GRAPH ---
elif view_option == "PK Graph":
    st.header("Concentration-Time Graph")
    col1, col2 = st.columns([1, 2])
    
    used_cmax = None
    k = None
    val_thalf = None
    cmax_origin_text = "Reported"
    calc_point = None 
    lod = 0.0 
    
    with col1:
        st.subheader("Select Drug")
        drug_choices = {}
        dose_cols = [c for c in df.columns if any(k in c.lower() for k in ['dose', 'strength', 'mg'])]
        primary_dose_col = dose_cols[0] if dose_cols else None
        
        for index, row in df.iterrows():
            label = str(row['Name'])
            if primary_dose_col and pd.notna(row[primary_dose_col]):
                label = f"{label} - {row[primary_dose_col]}"
            original_label = label
            count = 1
            while label in drug_choices:
                count += 1
                label = f"{original_label} ({count})"
            if search_term:
                s_term = search_term.lower()
                if (s_term in str(row['Name']).lower() or s_term in str(row['Class']).lower() or s_term in label.lower()):
                    drug_choices[label] = index
            else:
                drug_choices[label] = index
        
        if not drug_choices:
             st.warning("No drugs found matching criteria.")
             selected_graph_drug_label = None
        else:
             selected_graph_drug_label = st.selectbox("Choose a Drug to Plot:", list(drug_choices.keys()))
        
        st.markdown("---")
        plot_source = st.radio("Source for Peak Concentration ($C_{max}$):", ["Use Reported $C_{max}$", "Calculate from AUC ($C_0 = AUC \cdot k$)"])
        g_time = st.slider("Time Duration to Plot (hours)", 6, 72, 24)

        if selected_graph_drug_label:
            idx = drug_choices[selected_graph_drug_label]
            drug_row = df.loc[idx]
            
            cmax_col = [c for c in df.columns if "cmax" in c.lower()][0] if [c for c in df.columns if "cmax" in c.lower()] else "Cmax"
            half_life_col = [c for c in df.columns if "half" in c.lower()][0] if [c for c in df.columns if "half" in c.lower()] else "Half-Life"
            auc_col = [c for c in df.columns if "auc" in c.lower()][0] if [c for c in df.columns if "auc" in c.lower()] else "Area Under the Curve (AUC) [ng.hr/mL]"
            
            val_cmax = extract_numeric(drug_row.get(cmax_col, None))
            val_thalf = extract_numeric(drug_row.get(half_life_col, None))
            val_auc = extract_numeric(drug_row.get(auc_col, None))
            
            if val_thalf and val_thalf > 0:
                k = 0.693 / val_thalf
                used_cmax = val_cmax
                if "Calculate from AUC" in plot_source:
                    if val_auc:
                        used_cmax = val_auc * k
                        cmax_origin_text = "Calculated"
                    else:
                        st.warning("⚠️ No valid AUC found. Using Reported Cmax.")
                        used_cmax = val_cmax
                
                if used_cmax and used_cmax > 0:
                    st.markdown("---")
                    with st.expander("Quick Point Calculator", expanded=False): 
                        calc_tab1, calc_tab2 = st.tabs(["Find Conc.", "Find Time"])
                        with calc_tab1:
                            in_time = st.number_input("Time (h)", min_value=0.0, value=val_thalf, step=1.0, key="calc_t")
                            out_conc = used_cmax * np.exp(-k * in_time)
                            st.markdown(f"**Conc:** `{out_conc:.2f} ng/mL`")
                            calc_point = pd.DataFrame({'Time (hours)': [in_time], 'Concentration (ng/mL)': [out_conc]})
                        with calc_tab2:
                            in_conc = st.number_input("Target Conc (ng/mL)", min_value=0.0, value=used_cmax/2, step=1.0, key="calc_c")
                            if in_conc >= used_cmax:
                                st.error(f"Target must be < Peak ({used_cmax:.2f})")
                            elif in_conc <= 0:
                                st.error("Target must be > 0")
                            else:
                                out_time = -(1/k) * np.log(in_conc / used_cmax)
                                st.markdown(f"**Time:** `{out_time:.2f} hours`")
                                calc_point = pd.DataFrame({'Time (hours)': [out_time], 'Concentration (ng/mL)': [in_conc]})
                        
                        st.markdown("---")
                        lod = st.number_input("Limit of Detection (LoD) [ng/mL]", min_value=0.0, value=0.0, step=0.1, help="Show a horizontal line for the Limit of Detection", key="lod_input")

    with col2:
        st.subheader("Elimination Curve")
        if selected_graph_drug_label:
            if used_cmax and used_cmax > 0 and k:
                time_points = np.linspace(0, g_time, num=100)
                concentrations = used_cmax * np.exp(-k * time_points)
                chart_data = pd.DataFrame({"Time (hours)": time_points, "Concentration (ng/mL)": concentrations})
                
                base_chart = alt.Chart(chart_data).mark_line(color="#FFFFFF", strokeWidth=3).encode(
                    x='Time (hours)', y='Concentration (ng/mL)', tooltip=['Time (hours)', 'Concentration (ng/mL)']
                )
                final_chart = base_chart
                if calc_point is not None:
                    point_chart = alt.Chart(calc_point).mark_circle(color="red", size=200, opacity=1).encode(
                        x='Time (hours)', y='Concentration (ng/mL)', tooltip=['Time (hours)', 'Concentration (ng/mL)']
                    )
                    final_chart = final_chart + point_chart
                if lod > 0:
                    lod_df = pd.DataFrame({'y': [lod]})
                    lod_line = alt.Chart(lod_df).mark_rule(color='#FFA500', strokeDash=[5, 5], strokeWidth=2).encode(y='y')
                    final_chart = final_chart + lod_line

                final_chart = final_chart.properties(background='#003366', height=400).configure_axis(
                    labelColor='#FFFFFF', titleColor='#FFFFFF', gridColor='#406080',
                    labelFontSize=12, titleFontSize=14, grid=True
                ).configure_view(stroke=None)
                
                st.altair_chart(final_chart, use_container_width=True)
                st.markdown(f"**Plotting Parameters:** Cmax ({cmax_origin_text}) = {used_cmax:.2f} ng/mL, Half-Life = {val_thalf}h")
            elif not val_thalf:
                st.error("Could not extract valid numerical Half-Life for this drug to plot.")
            else:
                st.error("Invalid or missing Cmax value (Reported or Calculated). Cannot plot.")
