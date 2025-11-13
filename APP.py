import streamlit as st
import pandas as pd
import altair as alt
import re
from streamlit_option_menu import option_menu
from streamlit_extras.metric_cards import style_metric_cards
import math

# ================== PAGE CONFIG ==================
st.set_page_config(
    page_title="DR Chase Leads Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================== HELPER FUNCTIONS ==================
def norm(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(s).strip().lower())

def find_col(df_cols, candidates):
    cand_norm = {norm(c) for c in candidates}
    for c in df_cols:
        if norm(c) in cand_norm:
            return c
    return None

def categorize_weeks(days):
    if pd.isna(days):
        return None
    # 🆕 (FIXED) "Week 0" (0-6 days), "Week 1" (7-13 days), "Week -1" (-1 to -7 days)
    # math.floor() بتظبط الحالتين
    return f"Week {math.floor(days / 7)}"

# ================== SYNONYMS & MAPS ==================
syn = {
    "created_time": ["created_time", "created time", "creation time", "created", "lead created", "request created"],
    "assign_date": ["assign_date", "assigned date", "assign time", "assigned time", "assigned on"],
    "approval_date": ["approval_date", "approved date", "approval time", "approved on"],
    "completion_date": ["completion_date", "completed date", "completion time", "closed date", "completed on"],
    "uploaded_date": ["uploaded_date", "upload date", "uploaded date", "uploaded on"],
    "assigned_to_chase": ["assigned to chase", "assigned_to_chase", "assigned to", "assigned user (chase)", "assigned chaser"],
}

# (تم تعديل المفاتيح لتكون كلها lowercase لتتوافق مع دالة التنظيف)
name_map = {
    "a.williams": "Alfred Williams", "david.smith": "David Smith", "jimmy.daves": "Grayson Saint",
    "e.moore": "Eddie Moore", "aurora.stevens": "Aurora Stevens", "grayson.saint": "Grayson Saint",
    "emma.wilson": "Emma Wilson", "scarlett.mitchell": "Scarlett Mitchell", "lucas.diago": "Lucas Diago",
    "mia.alaxendar": "Mia Alaxendar", "ivy.brooks": "Ivy Brooks", "timothy.williams": "Timothy Williams",
    "sarah.adams": "Sarah Adams", "sara.adams": "Sarah Adams", "samy.youssef": "Samy Youssef",
    "candy.johns": "Candy Johns", "heather.robertson": "Heather Robertson", "a.cabello": "Andrew Cabello",
    "alia.scott": "Alia Scott", "sandra.sebastian": "Sandra Sebastian", 
    "katty.crater": "Katty Crater", # 👈 تم التعديل هنا
    "kayla.miller": "Kayla Miller"
}


samy_chasers = {
    "Emma Wilson", "Scarlett Mitchell", "Lucas Diago", "Mia Alaxendar",
    "Candy Johns", "Sandra Sebastian", "Alia Scott",
    "Ivy Brooks", "Heather Robertson", "Samy Youssef", "Katty Crater",
    "Sarah Adams", "Timothy Williams"
}

# ⚠️ Load Raw Data (Initial Check)
try:
    df_raw = pd.read_csv("Dr_Chase_Leads.csv", low_memory=False)
except FileNotFoundError:
    st.error("⚠️ خطأ: لم يتم العثور على الملف 'Dr_Chase_Leads.csv'. يرجى التأكد من وجود الملف في نفس المجلد.")
    st.stop()
df_raw.columns = df_raw.columns.str.strip()

cols_map = {
    "created_time": find_col(df_raw.columns, syn["created_time"]),
    "assign_date": find_col(df_raw.columns, syn["assign_date"]),
    "approval_date": find_col(df_raw.columns, syn["approval_date"]),
    "completion_date": find_col(df_raw.columns, syn["completion_date"]),
    "uploaded_date": find_col(df_raw.columns, syn["uploaded_date"]),
    "assigned_to_chase": find_col(df_raw.columns, syn["assigned_to_chase"]),
}

# ================== DATA CLEANING & CACHING FUNCTION ==================
@st.cache_data
def load_and_clean_data(df, name_map, cols_map, samy_chasers):
    df_cleaned = df.copy()
    
    # 1. Remove columns
    columns_to_remove = [
        "Is Converted From Lead", "Height", "Weight", "Waist Size", "Dr Phone Number", "Dr Fax",
        "Dr Alternative Phone", "Dr Address", "Dr City", "Dr ZIP Code", "NPI", "Dr Info Extra Comments",
        "Dr. Name", "Exception", "Initial Agent", "Full Name", "Last Name", "Secondary Phone", "Address",
        "Gender", "ZIP Code", "City", "Phase","First Name","LOMN?","Source","Brace Size","Extra Comments" ,"CBA","Primary Phone"
    ]
    df_cleaned = df_cleaned.drop(columns=[c for c in columns_to_remove if c in df_cleaned.columns], errors="ignore")

    # 2. Date Conversion
    date_columns_original = [
        "Created Time", "Assigned date", "Completion Date", "Approval date",
        "Denial Date", "Modified Time", "Date of Sale", "Upload Date", 
    ]

    for col in date_columns_original:
        if col in df_cleaned.columns:
            # Convert to datetime (day first format is assumed: DD/MM/YYYY)
            df_cleaned[col] = pd.to_datetime(
                df_cleaned[col], 
                errors="coerce", 
                dayfirst=True, 
                infer_datetime_format=True
            )

            # Create additional split columns for date/time (used for st.dataframe)
            df_cleaned[col + " (Date)"] = df_cleaned[col].dt.date
            if df_cleaned[col].dt.time.notna().any():
                df_cleaned[col + " (Time)"] = df_cleaned[col].dt.time

    # 3. Chaser Name Mapping and Grouping
    assigned_col = cols_map["assigned_to_chase"]
    if assigned_col and assigned_col in df_cleaned.columns:
        df_cleaned["Chaser Name"] = (
            df_cleaned[assigned_col]
            .astype(str).str.strip().str.lower() # <-- This lowercases the key
            .map(name_map)                       # <-- This maps using the (now) lowercase key
            .fillna(df_cleaned[assigned_col])    # <-- This fills if map fails
        )
        df_cleaned["Chaser Group"] = df_cleaned["Chaser Name"].apply(
            lambda n: "Samy Chasers" if n in samy_chasers else "Andrew Chasers"
        )
    
    # 4. Ensure core columns used for calculation are datetime
    date_actual_cols = [cols_map[k] for k in ["created_time","assign_date","approval_date","completion_date","uploaded_date"] if cols_map[k]]
    for c in date_actual_cols:
        if c in df_cleaned.columns:
            df_cleaned[c] = pd.to_datetime(df_cleaned[c], errors="coerce")
            
    # 5. Clean MCN and Chasing Disposition for merging
    if "MCN" in df_cleaned.columns:
        df_cleaned["MCN_clean"] = df_cleaned["MCN"].astype(str).str.strip()
        
    if "Chasing Disposition" in df_cleaned.columns:
        df_cleaned["Chasing Disposition_clean"] = df_cleaned["Chasing Disposition"].fillna('').astype(str).str.strip().str.lower()
    
    return df_cleaned


@st.cache_data
def load_oplan_data(file_path="O_Plan_Leads.csv"):
    """Loads and cleans the O Plan leads file."""
    try:
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip()
        
        # 1. Find "Closing Status" column (case-insensitive)
        closing_status_syns = ["Closing Status", "closing status", "status"]
        actual_closing_col = find_col(df.columns, closing_status_syns) # 👈 Use find_col
        
        if actual_closing_col:
            df["Closing Status_clean"] = df[actual_closing_col].fillna('').astype(str).str.strip().str.lower()
        else:
            st.warning("Column 'Closing Status' not found in O_Plan_Leads.csv. Cannot perform conflict check.")
            
        # 2. Find "Assign To" column (case-insensitive)
        assign_to_syns = ["Assign To", "Assign to", "assigned to", "agent", "Assigned To"]
        actual_assign_col = find_col(df.columns, assign_to_syns) # 👈 Use find_col
        
        if actual_assign_col:
            df["Assign To_clean"] = df[actual_assign_col].fillna("Unassigned").astype(str).str.strip()
        else:
            st.warning("Column 'Assign To' not found in O_Plan_Leads.csv. Cannot perform agent analysis.")
        
        # 3. Find "MCN" column (case-insensitive)
        mcn_syns = ["MCN", "mcn"]
        actual_mcn_col = find_col(df.columns, mcn_syns) # 👈 Use find_col

        if actual_mcn_col:
            df["MCN_clean"] = df[actual_mcn_col].astype(str).str.strip()
        else:
            st.warning("Column 'MCN' not found in O_Plan_Leads.csv. Cannot perform conflict check.")
            
        st.success("✅ O Plan file loaded successfully! (Cached for speed)")
        return df
    except FileNotFoundError:
        st.error(f"⚠️ خطأ: لم يتم العثور على الملف '{file_path}'. يرجى التأكد من وجود الملف في نفس المجلد.")
        return pd.DataFrame() # Return empty dataframe on error
    except Exception as e:
        st.error(f"An error occurred while loading O_Plan_Leads.csv: {e}")
        return pd.DataFrame()


# ================== EXECUTE DATA LOAD ==================
df_cleaned = load_and_clean_data(df_raw, name_map, cols_map, samy_chasers)
df_oplan = load_oplan_data("O_Plan_Leads.csv") # 🆕 Load O Plan data


# ================== COLUMN DESCRIPTIONS ==================
column_descriptions = {
    # ... (all your column descriptions are here, no changes) ...
    "Assigned To Chase": "Username of the chaser assigned to the lead (mapped later to full names).",
    "Dr Chase Lead Number": "Unique ID assigned to each lead in the DR Chase system.",
    "Created Time": "Timestamp when the lead was first created.",
    "Modified Time": "Timestamp of the most recent modification.",
    "Source": "Where the lead originated (e.g., CRM, referral, etc.).",
    "Brace Size": "Medical brace size requested or required (e.g., Small, Medium, Large).",
    "Extra Comments": "Additional notes about the lead, such as waist size or doctor instructions.",
    "Dr Name": "Name of the doctor associated with the lead.",
    "Dr State": "State where the doctor is located.",
    "Dr Specialty": "Doctor’s medical specialty (e.g., Internal Medicine, Orthopedics).",
    "Confirmation Call Type": "Type of call used to confirm details (e.g., Doctor Call, Patient Call).",
    "Closer Name": "Agent responsible for closing the lead.",
    "Team Leader": "Team Leader supervising the chaser/closer.",
    "L Codes": "Medical billing or insurance codes associated with the product (e.g., L1852).",
    "Client": "Client associated with the lead (e.g., PPO-Braces chasing).",
    "CBA": "Zipcode classification or market quality indicator (e.g., Good Zipcode).",
    "Validator": "Agent responsible for validating the lead details.",
    "Validation": "Validation status of the lead (e.g., Valid, Invalid).",
    "Next Follow-up Date": "Planned date for the next follow-up.",
    "Follow Up Attempts": "Number of follow-up attempts made.",
    "Validation Comments": "Notes left by validators during validation checks.",
    "Chasing Disposition": "Final chasing result (e.g., Dead Lead, Successful Chase).",
    "Type Of Sale": "Category of the lead (e.g., Normal Chase, Red Flag).",
    "Why is it a red chase?": "Explanation for red chase categorization.",
    "Supervisor": "Supervisor responsible for overseeing the team.",
    "Initial Status Received On": "First status received from doctor’s office or patient (e.g., Pending Fax).",
    "Dr Office DB Updated?": "Whether the doctor office database was updated (Yes/No).",
    "Pharmacy Name": "Pharmacy involved in the case (if applicable).",
    "Completion Date": "Date when the lead was completed/closed.",
    "CN?": "Indicates whether a CN (Certificate of Necessity) is present (Yes/No).",
    "QA Agent": "Quality Assurance agent who checked the case.",
    "Uploaded?": "Whether the required documents were uploaded (Yes/No).",
    "Upload Date": "Date when documents were uploaded.",
    "QA Comments": "Feedback or notes from QA agent.",
    "Approval date": "Date when the lead was approved.",
    "Denial Date": "Date when the lead was denied (if applicable).",
    "Assigned date": "Date the lead was assigned to a chaser.",
    "Days Spent As Pending QA": "Number of days lead stayed in Pending QA status.",
    "Primary Phone": "Patient’s primary phone number.",
    "Date of Birth": "Patient’s date of birth.",
    "Date of Sale": "Date when the sale was confirmed.",
    "Insurance": "Type of insurance associated with the lead (e.g., PPO).",
    "MCN": "Medical Case Number associated with the patient/lead.",
    "PPO ID -If any-": "Insurance PPO ID if available.",
    "Products": "Products linked to the lead (e.g., braces, medical items).",
    "State": "Patient’s state of residence.",
    "Chasing Comments": "Additional notes from chasers about follow-ups.",
    "Primary Insurance": "Primary insurance provider (e.g., Medicare).",
    "Last Modified By": "User who last modified the lead record.",
    "Chaser Name": "Mapped name of the chaser assigned to the lead.",
    "Chaser Group": "Group classification (e.g., Samy Chasers, Andrew Chasers)."
}


# ================== SIDEBAR MENU ==================
with st.sidebar:
    selected = option_menu(
        menu_title="Main Menu",
        options=["Dataset Overview", "Data Analysis"],
        icons=["table", "bar-chart"],
        menu_icon="cast",
        default_index=0,
        orientation="vertical"
    )

# --- Function for tabular view (USED IN BOTH TABS) ---
def table(df_filtered):
    with st.expander("📊 Tabular Data View"):
        default_cols = [
            "MCN","Chaser Name","Chaser Group","Date of Sale (Date)","Created Time (Date)","Assigned date (Date)",
            "Approval date (Date)","Denial Date (Date)","Completion Date (Date)",
            "Upload Date (Date)","Client","Chasing Disposition","Insurance","Type Of Sale","Products"
        ]
        shwdata_defaults = [c for c in default_cols if c in df_filtered.columns]

        shwdata = st.multiselect(
            "Filter Columns:",
            df_filtered.columns.tolist(),
            default=shwdata_defaults
        )
        st.dataframe(df_filtered[shwdata], use_container_width=True)


# ================== SIDEBAR FILTERS ==================
st.sidebar.header("🎛 Basic Filters")

# --- Client Filter ---
with st.sidebar.expander("👥 Client", expanded=False):
    if "Client" in df_cleaned.columns:
        all_clients = df_cleaned["Client"].unique().tolist()
        select_all_clients = st.checkbox("Select All Clients", value=True, key="all_clients")
        if select_all_clients:
            Client = st.multiselect("Select Client", options=all_clients, default=all_clients)
        else:
            Client = st.multiselect("Select Client", options=all_clients)
    else:
        st.warning("Column 'Client' not found.")
        Client = [] 


# --- Chaser Name Filter ---
with st.sidebar.expander("🧑‍💼 Chaser Name", expanded=False):
    if "Chaser Name" in df_cleaned.columns:
        all_Chaser_Name=df_cleaned["Chaser Name"].unique().tolist()
        select_all_Chaser_Name = st.checkbox("Select All Chaser Name ", value=True, key="all_Chaser_Name")
        if select_all_Chaser_Name:
            Chaser_Name = st.multiselect("Select Chaser Name", options=all_Chaser_Name, default=all_Chaser_Name)   
        else:
            Chaser_Name  = st.multiselect("Select  Chaser Name ", options=all_Chaser_Name)
    else:
        st.warning("Column 'Chaser Name' not found.")
        Chaser_Name = []


# --- Chaser Group Filter ---
with st.sidebar.expander("👨‍👩‍👧‍👦 Chaser Group", expanded=False):
    if "Chaser Group" in df_cleaned.columns:
        all_Chaser_Group=df_cleaned["Chaser Group"].unique().tolist()
        select_all_Chaser_Group = st.checkbox("Select All Chaser Group ", value=True, key="all_Chaser_Group")
        if select_all_Chaser_Group:
            Chaser_Group = st.multiselect("Select Chaser Group", options=all_Chaser_Group, default=all_Chaser_Group)   
        else:
            Chaser_Group  = st.multiselect("Select  Chaser Group ", options=all_Chaser_Group)
    else:
        st.warning("Column 'Chaser Group' not found.")
        Chaser_Group = []


# --- Chasing Disposition Filter ---
with st.sidebar.expander("👥 Chasing Disposition", expanded=False):
    if "Chasing Disposition" in df_cleaned.columns:
        all_Chasing_Disposition=df_cleaned["Chasing Disposition"].unique().tolist()
        select_all_Chasing_Disposition = st.checkbox("Select All Chaser Disposition ", value=True, key="all_Chasing_Disposition")
        if select_all_Chasing_Disposition:
            Chasing_Disposition = st.multiselect("Select Chaser Disposition", options=all_Chasing_Disposition, default=all_Chasing_Disposition)   
        else:
            Chasing_Disposition  = st.multiselect("Select  Chaser Disposition ", options=all_Chasing_Disposition)
    else:
        st.warning("Column 'Chasing Disposition' not found.")
        Chasing_Disposition = []


# --- Date Range Filter ---
with st.sidebar.expander("📅 Date Range", expanded=False):
    date_cols_for_range = [
        "Created Time", "Assigned date", "Completion Date", "Approval date",
        "Denial Date", "Modified Time", "Date of Sale", "Upload Date"
    ]
    
    valid_date_cols = [c for c in date_cols_for_range if c in df_cleaned.columns]
    
    date_range = None
    if valid_date_cols:
        all_dates = pd.concat([df_cleaned[c].dropna() for c in valid_date_cols])
        
        if not all_dates.empty:
            min_ts = all_dates.min()
            max_ts = all_dates.max()
            
            min_date = min_ts.date()
            max_date = max_ts.date()
            
            date_range = st.date_input(
                "Select date range (based on Available Dates)",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
        else:
            st.warning("No valid dates found in the dataset.")
            default_date = pd.Timestamp.now().date()
            date_range = (default_date, default_date)
            st.date_input("Select date range (No Data Available)", value=date_range, disabled=True)
    else:
        st.warning("No date columns found for filtering.")
        default_date = pd.Timestamp.now().date()
        date_range = (default_date, default_date)


# --- Apply filters using .query() ---
# 🆕 (FIXED) 1. 
query_parts_kpi = []
if Client and "Client" in df_cleaned.columns:
    query_parts_kpi.append("Client in @Client")
if Chaser_Name and "Chaser Name" in df_cleaned.columns:
    query_parts_kpi.append("`Chaser Name` in @Chaser_Name")
if Chaser_Group and "Chaser Group" in df_cleaned.columns:
    query_parts_kpi.append("`Chaser Group` in @Chaser_Group")

# 🆕 (FIXED) 2. 
if query_parts_kpi:
    final_query_kpi = " and ".join(query_parts_kpi)
    df_kpi = df_cleaned.query(final_query_kpi)
else:
    df_kpi = df_cleaned.copy()

# 🆕 (FIXED) 3. 
query_parts_main = query_parts_kpi.copy() # 
if Chasing_Disposition and "Chasing Disposition" in df_cleaned.columns:
    query_parts_main.append("`Chasing Disposition` in @Chasing_Disposition") # 

# 🆕 (FIXED) 4. 
if query_parts_main:
    final_query_main = " and ".join(query_parts_main)
    df_filtered = df_cleaned.query(final_query_main)
else:
    df_filtered = df_kpi.copy() # 
    

# Apply date filter (on Created Time by default)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    if "Created Time" in df_filtered.columns:
        # 
        df_filtered = df_filtered[
            (df_filtered["Created Time"].dt.date >= start_date)
            & (df_filtered["Created Time"].dt.date <= end_date)
        ]
        # 🆕 (FIX) 
        df_kpi = df_kpi[
            (df_kpi["Created Time"].dt.date >= start_date)
            & (df_kpi["Created Time"].dt.date <= end_date)
        ]
# ================== MAIN DASHBOARD (Dataset Overview) ==================
if selected == "Dataset Overview":
    st.title("📋 Dataset Overview – General Inspection")
    st.info("This page is for **quick inspection** of the dataset, showing key metrics, summaries, and descriptions of columns.")

    st.subheader("🔍 Data Inspection")
    st.markdown(f""" The dataset contains **{len(df_filtered)} rows**
                      and **{len(df_filtered.columns)} columns**.
                    """)
    table(df_filtered)

   # --- KPIs Section ---
    st.subheader("📌 Key Performance Indicators")
    
    # --- حساب القيم ---
    # 🆕 (FIXED) 
    total_leads = len(df_kpi)
    total_completed = df_kpi["Completion Date"].notna().sum() if "Completion Date" in df_kpi.columns else 0
    total_assigned = df_kpi["Assigned date"].notna().sum() if "Assigned date" in df_kpi.columns else 0
    total_uploaded = df_kpi["Upload Date"].notna().sum() if "Upload Date" in df_kpi.columns else 0
    total_approval = df_kpi["Approval date"].notna().sum() if "Approval date" in df_kpi.columns else 0
    total_denial = df_kpi["Denial Date"].notna().sum() if "Denial Date" in df_kpi.columns else 0
    
    total_pending_shipping = 0
    if "Chasing Disposition_clean" in df_kpi.columns: # 👈 (FIXED)
        total_pending_shipping = df_kpi[ # 👈 (FIXED)
            df_kpi["Chasing Disposition_clean"].eq("pending shipping") # 👈 (FIXED)
        ].shape[0]

    # Derived metrics
    total_not_assigned = total_leads - total_assigned
    
    # Percentages
    pct_completed = (total_completed / total_leads * 100) if total_leads > 0 else 0
    pct_assigned = (total_assigned / total_leads * 100) if total_leads > 0 else 0
    pct_not_assigned = (total_not_assigned / total_leads * 100) if total_leads > 0 else 0
    pct_uploaded = (total_uploaded / total_completed * 100) if total_completed > 0 else 0
    pct_approval = (total_approval / total_leads * 100) if total_leads > 0 else 0
    pct_denial = (total_denial / total_leads * 100) if total_leads > 0 else 0
    pct_pending_shipping = (total_pending_shipping / total_leads * 100) if total_leads > 0 else 0
    
    # --- KPIs Layout (8 بطاقات) ---
    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)
    col7, col8 = st.columns(2) 
    
    with col1:
        st.metric("📊 Total Leads", f"{total_leads:,}")
    with col2:
        st.metric("🧑‍💼 Assigned", f"{total_assigned:,} ({pct_assigned:.1f}%)")
    with col3:
        st.metric("🚫 Not Assigned", f"{total_not_assigned:,} ({pct_not_assigned:.1f}%)")
    with col4:
        st.metric("✅ Completed", f"{total_completed:,} ({pct_completed:.1f}%)")
    with col5:
        st.metric("✔ Approved", f"{total_approval:,} ({pct_approval:.1f}%)")
    with col6:
        st.metric("❌ Denied", f"{total_denial:,} ({pct_denial:.1f}%)")
    with col7:
        st.metric("📤 Uploaded", f"{total_uploaded:,} ({pct_uploaded:.1f}%)")
    with col8:
        st.metric("🚚 Total Upload to Client (Pending Shipping)", 
                 f"{total_pending_shipping:,} ({pct_pending_shipping:.1f}%)")
        
    
        # ✅ Apply custom style
    style_metric_cards(
        background_color="#0E1117",
        border_left_color="#00BFFF",
        border_color="#444",
        box_shadow="2px 2px 10px rgba(0,0,0,0.5)"
    )
        
    
    
    # --- Dates summary (table) ---
    date_cols = df_filtered.select_dtypes(include=["datetime64[ns]"]).columns
    if len(date_cols) > 0:
        st.markdown("### 📅 Date Ranges in Dataset")
        date_summary = pd.DataFrame({
            "Column": date_cols,
            "First Date": [df_filtered[c].min() for c in date_cols],
            "Last Date": [df_filtered[c].max() for c in date_cols],
        })
        st.table(date_summary)


    # --- Numeric summary (table) ---
    num_cols = df_filtered.select_dtypes(include=["int64", "float64"]).columns
    if len(num_cols) > 0:
        st.markdown("### 🔢 Numeric Columns Summary")
        num_summary = pd.DataFrame({
            "Column": num_cols,
            "Min": [df_filtered[c].min() for c in num_cols],
            "Max": [df_filtered[c].max() for c in num_cols],
            "Mean": [round(df_filtered[c].mean(), 2) for c in num_cols]
        })
        st.table(num_summary)

    # --- Column Descriptions ---
    st.subheader("📖 Column Descriptions")
    st.info("Choose a column to see what it represents and explore its distribution.")

    description_columns = [
        "Chaser Name", "Chaser Group", "Date of Sale (Date)", "Created Time (Date)",
        "Assigned date (Date)", "Approval date (Date)", "Denial Date (Date)",
        "Completion Date (Date)", "Upload Date (Date)", "Client",
        "Chasing Disposition", "Insurance", "Type Of Sale", "Products","Days Spent As Pending QA"
    ]

    valid_desc_cols = [c for c in description_columns if c in df_cleaned.columns]

    selected_col = st.selectbox(
        "Select a column to view description",
        valid_desc_cols
    )

    desc = column_descriptions.get(selected_col, "No description available for this column.")
    

    # --- Force date conversion for known date columns ---
    date_columns_for_vis = [
        "Date of Sale (Date)", "Created Time (Date)", "Assigned date (Date)",
        "Approval date (Date)", "Denial Date (Date)",
        "Completion Date (Date)", "Upload Date (Date)"
    ]

    for col in date_columns_for_vis:
        if col in df_filtered.columns:
            df_filtered[col] = pd.to_datetime(df_filtered[col], errors="coerce")

    # --- Extra Visualization (same logic you already have) ---
    if selected_col in df_filtered.select_dtypes(include=["object"]).columns:
        st.markdown(f"### 📊 Distribution of {selected_col}")
        chart_data = df_filtered[selected_col].value_counts().reset_index()
        chart_data.columns = [selected_col, "Count"]

        chart = (
            alt.Chart(chart_data)
            .mark_bar(color="#16eff7")
            .encode(
                x=alt.X(selected_col, sort="-y"),
                y="Count",
                tooltip=[selected_col, "Count"]
            )
        )
        st.altair_chart(chart, use_container_width=True)

    elif selected_col in df_filtered.select_dtypes(include=["number"]).columns:
        st.markdown(f"### 📊 Distribution of {selected_col}")

        chart = (
            alt.Chart(df_filtered)
            .mark_bar(color="#0eff87")
            .encode(
                x=alt.X(selected_col, bin=alt.Bin(maxbins=30)),
                y='count()',
                tooltip=[selected_col, "count()"]
            )
        )
        st.altair_chart(chart, use_container_width=True)




    elif selected_col in df_filtered.select_dtypes(include=["datetime64[ns]"]).columns:
        st.markdown(f"### 📈 Time Series of {selected_col}")
        ts_data = df_filtered[selected_col].value_counts().reset_index()
        ts_data.columns = [selected_col, "Count"]
        ts_data = ts_data.sort_values(selected_col)

        chart = (
            alt.Chart(ts_data)
            .mark_line(point=True, color="#ff7f0e")
            .encode(
                x=selected_col,
                y="Count",
                tooltip=[selected_col, "Count"]
            )
        )
        st.altair_chart(chart, use_container_width=True)


# ================== MAIN DASHBOARD (Data Analysis) ==================
elif selected == "Data Analysis":
    st.title("📊 Data Analysis – Advanced Insights")
    st.info("This page is for **deeper analysis** including time-series trends, insights summaries, and lead age analysis by Chaser / Client.")

    # --- Allowed columns for analysis ---
    allowed_columns = [
        "Created Time (Date)",
        "Assigned date (Date)",
        "Approval date (Date)",
        "Denial Date (Date)",
        "Completion Date (Date)",
        "Upload Date (Date)",
        "Date of Sale (Date)",
    ]
    
    available_columns = [c for c in allowed_columns if c in df_filtered.columns]
    
    if not available_columns:
        st.warning("⚠️ None of the predefined analysis columns are available in the dataset.")
        st.stop()
        
    time_col = st.selectbox("Select column for analysis", available_columns)
    original_time_col = time_col.replace(" (Date)", "") 
    
    # Prepare df_ts
    df_ts = df_kpi.copy()
    if original_time_col in df_ts.columns:
        df_ts = df_ts[df_ts[original_time_col].notna()].copy()

        today = pd.Timestamp.now().normalize()
        future_mask = df_ts[original_time_col].dt.normalize() > today
        df_ts = df_ts.loc[~future_mask].copy()

    st.markdown(f""" The working dataset for analysis contains **{len(df_ts)} rows**
                      and **{len(df_ts.columns)} columns**.
                    """)
    table(df_filtered) 
            
    total_leads = len(df_filtered)
    
    # --- Aggregation frequency ---
    freq = st.radio("Aggregation level:", ["Daily", "Weekly", "Monthly"], horizontal=True)
    period_map = {"Daily": "D", "Weekly": "W", "Monthly": "M"}
    
    if original_time_col in df_ts.columns:
        df_ts["Period"] = df_ts[original_time_col].dt.to_period(period_map[freq]).dt.to_timestamp()
    else:
        df_ts = pd.DataFrame() 

    # --- Grouping option ---
    group_by = st.selectbox("Break down by:", ["None", "Client", "Chaser Name", "Chaser Group"])
    if group_by == "None":
        ts_data = df_ts.groupby("Period").size().reset_index(name="Lead Count")
    else:
        ts_data = df_ts.groupby(["Period", group_by]).size().reset_index(name="Lead Count")

    if not ts_data.empty:
        # 📈 Historical Time Series
        st.subheader("📈 Historical Time Series")

        if group_by == "None":
            chart = (
                alt.Chart(ts_data)
                .mark_line(point=True, color="#007bff")
                .encode(x="Period:T", y="Lead Count", tooltip=["Period:T", "Lead Count"])
                .properties(height=400)
            )
        else:
            chart = (
                alt.Chart(ts_data)
                .mark_line(point=True)
                .encode(
                    x="Period:T",
                    y="Lead Count",
                    color=group_by,
                    tooltip=["Period:T", "Lead Count", group_by]
                )
                .properties(height=400)
            )
        st.altair_chart(chart, use_container_width=True)


        # 🏆 Top performers
        if group_by in ["Chaser Name", "Client"]:
            st.subheader(f"🏆 Top {group_by}s by Leads")
            top_table = ts_data.groupby(group_by)["Lead Count"].sum().reset_index()
            top_table = top_table.sort_values("Lead Count", ascending=False).head(40)
            st.table(top_table)
        
        
        # ================== Chasing Disposition Distribution (MODIFIED: Compact Metric) ==================
        if "Chasing Disposition" in df_ts.columns:
            st.subheader("📊 Chasing Disposition Distribution")

            metric_options_disp = [
                "Total Leads (with Created Time (Date))",
                "Total Assigned",
                "Not Assigned",
                "Total Approved",
                "Total Denied",
                "Total Completed",
                "Total Uploaded"
            ]
            metric_option = st.selectbox(
                "Select metric to display by Chasing Disposition:",
                metric_options_disp
            )

            metrics_by_disp = df_ts.groupby("Chasing Disposition").agg({
                "Created Time (Date)": "count",
                "Assigned date": lambda x: x.notna().sum(),
                "Approval date": lambda x: x.notna().sum(),
                "Denial Date": lambda x: x.notna().sum(),
                "Completion Date": lambda x: x.notna().sum(),
                "Upload Date": lambda x: x.notna().sum(),
            }).reset_index()

            metrics_by_disp["Not Assigned"] = (
                metrics_by_disp["Created Time (Date)"] - metrics_by_disp["Assigned date"]
            )

            metric_map = {
                "Total Leads (with Created Time (Date))": "Created Time (Date)",
                "Total Assigned": "Assigned date",
                "Not Assigned": "Not Assigned",
                "Total Approved": "Approval date",
                "Total Denied": "Denial Date",
                "Total Completed": "Completion Date",
                "Total Uploaded": "Upload Date"
            }

            selected_col = metric_map[metric_option]
            
            chart_data = metrics_by_disp[["Chasing Disposition", selected_col]].rename(columns={selected_col: "Count"})

            total_selected_metric = chart_data["Count"].sum()
            
            col_metric, col_spacer = st.columns([1, 4])
            with col_metric:
                st.metric(label=f"Total Count for: {metric_option}", value=f"{total_selected_metric:,}")
            
            total_for_percentage = total_selected_metric
            
            if total_for_percentage > 0:
                chart_data["Percentage"] = (chart_data["Count"] / total_for_percentage * 100).round(1)
                chart_data["Label"] = chart_data["Count"].apply(lambda x: f'{x:,}') 
            else:
                chart_data["Percentage"] = 0.0
                chart_data["Label"] = chart_data["Count"].apply(lambda x: f'{x:,}')


            chart_disp = (
                alt.Chart(chart_data)
                .mark_bar()
                .encode(
                    x=alt.X("Chasing Disposition", sort="-y", title="Chasing Disposition"),
                    y=alt.Y("Count", title=selected_col.replace(" (Date)", "")),
                    color="Chasing Disposition",
                    tooltip=["Chasing Disposition", "Count", alt.Tooltip("Percentage", format=".1f", title="Percentage (%)")]
                )
                .properties(height=400)
            )
            
            text = chart_disp.mark_text(
                align='center',    
                baseline='bottom', 
                dy=-5,             
                color='white',     
                fontSize=12
            ).encode(
                text=alt.Text("Label") 
            )

            final_chart = chart_disp + text
            st.altair_chart(final_chart, use_container_width=True)


            # ================== Client Distribution (MODIFIED: Compact Metric) ==================
        if "Client" in df_ts.columns:
            st.subheader("👥 Client Distribution")
        
            metric_options_client = [
                "Total Leads (with Created Time (Date))",
                "Total Assigned",
                "Not Assigned",
                "Total Approved",
                "Total Denied",
                "Total Completed",
                "Total Uploaded"
            ]
            metric_option_client = st.selectbox(
                "Select metric to display by Client:",
                metric_options_client,
                key="client_metric"
            )
        
            metrics_by_client = df_ts.groupby("Client").agg({
                "Created Time (Date)": "count",
                "Assigned date": lambda x: x.notna().sum(),
                "Approval date": lambda x: x.notna().sum(),
                "Denial Date": lambda x: x.notna().sum(),
                "Completion Date": lambda x: x.notna().sum(),
                "Upload Date": lambda x: x.notna().sum(),
            }).reset_index()
        
            metrics_by_client["Not Assigned"] = metrics_by_client["Created Time (Date)"] - metrics_by_client["Assigned date"]
        
            metric_map = {
                "Total Leads (with Created Time (Date))": "Created Time (Date)",
                "Total Assigned": "Assigned date",
                "Not Assigned": "Not Assigned",
                "Total Approved": "Approval date",
                "Total Denied": "Denial Date",
                "Total Completed": "Completion Date",
                "Total Uploaded": "Upload Date"
            }
            
            selected_col_client = metric_map[metric_option_client]
        
            chart_data_client = metrics_by_client[["Client", selected_col_client]].rename(columns={selected_col_client: "Count"})

            total_selected_metric_client = chart_data_client["Count"].sum()
            
            col_metric_client, col_spacer_client = st.columns([1, 4]) 
            with col_metric_client:
                st.metric(label=f"Total Count for: {metric_option_client}", value=f"{total_selected_metric_client:,}")
            
            total_for_percentage_client = total_selected_metric_client
            
            if total_for_percentage_client > 0:
                chart_data_client["Percentage"] = (chart_data_client["Count"] / total_for_percentage_client * 100).round(1)
                chart_data_client["Label"] = chart_data_client["Count"].apply(lambda x: f'{x:,}') 
            else:
                chart_data_client["Percentage"] = 0.0
                chart_data_client["Label"] = chart_data_client["Count"].apply(lambda x: f'{x:,}')
        
            chart_disp_client = (
                alt.Chart(chart_data_client)
                .mark_bar()
                .encode(
                    x=alt.X("Client", sort="-y"),
                    y=alt.Y("Count", title=selected_col_client.replace(" (Date)", "")),
                    color="Client",
                    tooltip=["Client", "Count", alt.Tooltip("Percentage", format=".1f", title="Percentage (%)")]
                )
                .properties(height=400)
            )

            text_client = chart_disp_client.mark_text(
                align='center',    
                baseline='bottom', 
                dy=-5,             
                color='white',     
                fontSize=12
            ).encode(
                text=alt.Text("Label") 
            )
            
            final_chart_client = chart_disp_client + text_client
            st.altair_chart(final_chart_client, use_container_width=True)

        
        
        # 📝 Insights Summary
        st.subheader("📝 Insights Summary")
        
        df_time = df_ts[df_ts[original_time_col].notna()].copy()
        total_time_leads = len(df_time)
        
        st.write(f"Based on **{time_col}**, there are **{total_time_leads} leads** with this date.")
        
        if total_time_leads > 0:
            total_assigned = df_time["Assigned date"].notna().sum() if "Assigned date" in df_time.columns else 0
            total_not_assigned = total_time_leads - total_assigned
            total_approval = df_time["Approval date"].notna().sum() if "Approval date" in df_time.columns else 0
            total_denial = df_time["Denial Date"].notna().sum() if "Denial Date" in df_time.columns else 0
            total_uploaded = df_time["Upload Date"].notna().sum() if "Upload Date" in df_time.columns else 0
            total_completed = df_time["Completion Date"].notna().sum() if "Completion Date" in df_time.columns else 0
            
            total_pending_shipping = 0
            if "Chasing Disposition_clean" in df_time.columns:
                total_pending_shipping = df_time[ # 
                    df_time["Chasing Disposition_clean"].eq("pending shipping") # 
                ].shape[0]

            # Show stats
            st.markdown(f"""
                - ✅ Total Leads (with {time_col}): **{total_time_leads}**
                - 🧑‍💼 Assigned: **{total_assigned}**
                - 🚫 Not Assigned: **{total_not_assigned}**
                - ✔ Approved: **{total_approval}**
                - ❌ Denied: **{total_denial}**
                - 📌 Completed: **{total_completed}**
                - 📤 Uploaded: **{total_uploaded}**
                - 🚚 Total Upload to Client (Pending Shipping): **{total_pending_shipping}**
                """)           
            
            st.subheader("🚨 Data Quality Warnings")
            today = pd.Timestamp.now().normalize()


            # 🚨 Leads with Pending Shipping but no Upload Date
            if "Chasing Disposition_clean" in df_filtered.columns and "Upload Date" in df_filtered.columns:
                mask_shipping = (
                    df_filtered["Chasing Disposition_clean"].eq("pending shipping") # 
                    & df_filtered["Upload Date"].isna()
                )
                
                pending_shipping = df_filtered[mask_shipping]
                
                if not pending_shipping.empty:
                    st.warning(f"⚠️ Found {len(pending_shipping)} leads with **Pending Shipping** but missing **Upload Date**.")
                    with st.expander("🔍 View Pending Shipping Leads Without Upload Date"):
                        st.dataframe(
                            pending_shipping[[
                                "MCN",
                                "Created Time (Date)",
                                "Assigned date (Date)",
                                "Completion Date (Date)",
                                "Upload Date (Date)",
                                "Chasing Disposition",
                                "Chaser Name",
                                "Client"
                            ]],
                            use_container_width=True
                        )
                
            # 🚨 Leads pending too long (Fax / Dr Call)
            if "Created Time (Date)" in df_filtered.columns and "Chasing Disposition_clean" in df_filtered.columns:
                today = pd.Timestamp.now().normalize()
                
                if "Days Since Created" not in df_filtered.columns: # Avoid re-creating column
                    df_filtered["Days Since Created"] = (
                        today - pd.to_datetime(df_filtered["Created Time (Date)"], errors="coerce")
                    ).dt.days
                
                pending_mask = (
                    (df_filtered["Days Since Created"] > 5) &
                    (df_filtered["Chasing Disposition_clean"].isin(["pending fax", "pending dr call"])) 
                )
                pending_leads = df_filtered[pending_mask]
                
                if not pending_leads.empty:
                    st.warning(f"⚠️ Found {len(pending_leads)} leads pending for more than 5 days (Fax/Dr Call).")
                    with st.expander("🔍 View Pending Leads > 5 Days (Fax/Dr Call)"): 
                        st.dataframe(
                            pending_leads[[
                                "MCN",
                                "Created Time (Date)",
                                "Days Since Created",
                                "Chasing Disposition",
                                "Assigned date (Date)",
                                "Upload Date (Date)",
                                "Completion Date (Date)",
                                "Chaser Name",
                                "Client"
                            ]],
                            use_container_width=True
                        )

            # 🚨 Leads pending too long (Faxed)
            if "Created Time (Date)" in df_filtered.columns and "Chasing Disposition_clean" in df_filtered.columns:
                today = pd.Timestamp.now().normalize()
                
                if "Days Since Created" not in df_filtered.columns: # Avoid re-creating column
                    df_filtered["Days Since Created"] = (
                        today - pd.to_datetime(df_filtered["Created Time (Date)"], errors="coerce")
                    ).dt.days
                
                pending_mask = (
                    (df_filtered["Days Since Created"] > 7) &
                    (df_filtered["Chasing Disposition_clean"].isin(["faxed"])) # 
                )
                pending_leads_faxed = df_filtered[pending_mask] # 
                
                if not pending_leads_faxed.empty: # 
                    st.warning(f"⚠️ Found {len(pending_leads_faxed)} leads pending for more than 7 days (Faxed).") # 
                    with st.expander("🔍 View Pending Leads > 7 Days (Faxed)"): # 
                        st.dataframe(
                            pending_leads_faxed[[ # 
                                "MCN",
                                "Created Time (Date)",
                                "Days Since Created",
                                "Chasing Disposition",
                                "Assigned date (Date)",
                                "Upload Date (Date)",
                                "Completion Date (Date)",
                                "Chaser Name",
                                "Client",
                                "Next Follow-up Date"
                            ]],
                            use_container_width=True
                        )
            
            # --- Row-level logic checks with expanders ---
            if "Completion Date" in df_time.columns and "Assigned date" in df_time.columns:
                bad_rows = df_time[df_time["Completion Date"].notna() & df_time["Assigned date"].isna()]
                if not bad_rows.empty:
                    st.warning(f"⚠️ Found {len(bad_rows)} leads with **Completion Date** but no **Assigned date**.")
                    with st.expander("🔍 View Leads Missing Assigned Date"):
                        st.dataframe(
                            bad_rows[["MCN", "Client", "Chaser Name", "Created Time", "Assigned date", "Completion Date"]],
                            use_container_width=True
                        )
            
            if "Completion Date" in df_time.columns and "Approval date" in df_time.columns:
                bad_rows2 = df_time[df_time["Completion Date"].notna() & df_time["Approval date"].isna()]
                if not bad_rows2.empty:
                    st.warning(f"⚠️ Found {len(bad_rows2)} leads with **Completion Date** but no **Approval date**.")
                    with st.expander("🔍 View Leads Missing Approval Date"):
                        st.dataframe(
                            bad_rows2[["MCN", "Client", "Chaser Name", "Created Time", "Approval date", "Completion Date"]],
                            use_container_width=True
                        )
            
            # --- Extra checks for Uploaded Date ---
            if "Upload Date" in df_time.columns and "Completion Date" in df_time.columns:
                bad_uploaded = df_time[df_time["Upload Date"].notna() & df_time["Completion Date"].isna()]
                if not bad_uploaded.empty:
                    st.warning(f"⚠️ Found {len(bad_uploaded)} leads with **Upload Date** but no **Completion Date**.")
                    with st.expander("🔍 View Leads Missing Completion Date after Upload"):
                        st.dataframe(
                            bad_uploaded[["MCN", "Client", "Chaser Name", "Upload Date", "Completion Date"]],
                            use_container_width=True
                        )
            
            if "Upload Date" in df_time.columns and "Assigned date" in df_time.columns:
                bad_uploaded_assigned = df_time[df_time["Upload Date"].notna() & df_time["Assigned date"].isna()]
                if not bad_uploaded_assigned.empty:
                    st.warning(f"⚠️ Found {len(bad_uploaded_assigned)} leads with **Upload Date** but no **Assigned date**.")
                    with st.expander("🔍 View Leads Missing Assigned Date after Upload"):
                        st.dataframe(
                            bad_uploaded_assigned[["MCN", "Client", "Chaser Name", "Upload Date", "Assigned date"]],
                            use_container_width=True
                        )
            
            if "Upload Date" in df_time.columns and "Approval date" in df_time.columns:
                bad_uploaded_approval = df_time[df_time["Upload Date"].notna() & df_time["Approval date"].isna()]
                if not bad_uploaded_approval.empty:
                    st.warning(f"⚠️ Found {len(bad_uploaded_approval)} leads with **Upload Date** but no **Approval date**.")
                    with st.expander("🔍 View Leads Missing Approval Date after Upload"):
                        st.dataframe(
                            bad_uploaded_approval[["MCN", "Client", "Chaser Name", "Upload Date", "Approval date"]],
                            use_container_width=True
                        )
            
            
            # 🚨 (NEW) Check for conflicting dispositions between Dr. Chase and O Plan
            if (not df_oplan.empty and 
                "MCN_clean" in df_filtered.columns and 
                "MCN_clean" in df_oplan.columns and 
                "Closing Status_clean" in df_oplan.columns and  # 
                "Chasing Disposition_clean" in df_filtered.columns):
                
                # 1. Define the conflicting statuses (CORRECTED)
                dr_chase_bad_dispos = ["dr denied", "rejected by dr chase", "dead lead"] # 
                oplan_closing_dispo = "doctor chase" 

                # 2. Find leads in O Plan with the closing status
                oplan_conflicts = df_oplan[
                    df_oplan["Closing Status_clean"].eq(oplan_closing_dispo) # 
                ]
                
                # 3. Find leads in Dr. Chase (from the filtered list) with the bad status
                dr_chase_conflicts = df_filtered[
                    df_filtered["Chasing Disposition_clean"].isin(dr_chase_bad_dispos)
                ]

                # 4. Find the intersection (the MCNs present in both lists)
                conflicting_leads = pd.merge(
                    dr_chase_conflicts[["MCN_clean", "Chasing Disposition", "Chaser Name", "Client"]],
                    oplan_conflicts[["MCN_clean", "Closing Status"]], # 
                    on="MCN_clean",
                    how="inner",
                    suffixes=('_DrChase', '_OPlan')
                )
                
                # 5. Display the warning if any conflicts are found
                if not conflicting_leads.empty:
                    st.warning(f"⚠️ Found {len(conflicting_leads)} leads marked as Denied/Dead in Dr. Chase but '{oplan_closing_dispo}' in O Plan.")
                    with st.expander("🔍 View Conflicting Leads"):
                        st.dataframe(conflicting_leads, use_container_width=True)
                
                else:
                    st.success("✅ تم فحص التطابق: لا يوجد أي تضارب بين ملف Dr. Chase وملف O Plan بخصوص الحالات المرفوضة.")


            
            # ================== Lead Age Analysis ==================
        st.subheader("⏳ Lead Age Analysis")
        st.info("Analysis of how long it takes for leads to get Approved / Denied. Includes weekly distribution, averages/medians, and grouped comparisons.")
        
        if "Created Time" in df_ts.columns:
            df_lead_age = df_ts.copy()
        
            # حساب Lead Age من Approval و Denial
            if "Approval date" in df_lead_age.columns:
                df_lead_age["Lead Age (Approval)"] = (
                    (df_lead_age["Approval date"] - df_lead_age["Created Time"]).dt.days
                )
            if "Denial Date" in df_lead_age.columns:
                df_lead_age["Lead Age (Denial)"] = (
                    (df_lead_age["Denial Date"] - df_lead_age["Created Time"]).dt.days
                )
            
            # --- KPIs Section ---
            # 🆕 (FIXED) Filter for positive ages before calculating mean/median
            positive_approval_ages = df_lead_age[df_lead_age["Lead Age (Approval)"] >= 0]["Lead Age (Approval)"]
            positive_denial_ages = df_lead_age[df_lead_age["Lead Age (Denial)"] >= 0]["Lead Age (Denial)"]

            total_approved = positive_approval_ages.notna().sum() # Count only positive approvals
            total_denied = positive_denial_ages.notna().sum() # Count only positive denials
            avg_approval_age = positive_approval_ages.mean(skipna=True)
            avg_denial_age = positive_denial_ages.mean(skipna=True)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("✔️ Total Approved (Week 0+)", f"{total_approved:,}")
            with col2:
                st.metric("❌ Total Denied (Week 0+)", f"{total_denied:,}")
            with col3:
                st.metric("⏳ Avg Approval Age (Week 0+)", f"{avg_approval_age:.1f} days" if not pd.isna(avg_approval_age) else "N/A")
            with col4:
                st.metric("⏳ Avg Denial Age (Week 0+)", f"{avg_denial_age:.1f} days" if not pd.isna(avg_denial_age) else "N/A")
        
            style_metric_cards(
                background_color="#0E1117",
                border_left_color={
                    "✔️ Total Approved (Week 0+)": "#28a745", # 🆕 Title updated
                    "❌ Total Denied (Week 0+)": "#dc3545", # 🆕 Title updated
                    "⏳ Avg Approval Age (Week 0+)": "#17a2b8", # 🆕 Title updated
                    "⏳ Avg Denial Age (Week 0+)": "#ffc107", # 🆕 Title updated
                },
                border_color="#444",
                box_shadow="2px 2px 10px rgba(0,0,0,0.5)"
            )
        
            # 📋 Full Lead Age Table (hidden by default)
            with st.expander("📋 View Full Lead Age Table (Includes Negatives)"):
                st.dataframe(
                    df_lead_age[[
                        "Created Time (Date)",
                        "Approval date",
                        "Denial Date",
                        "Lead Age (Approval)",
                        "Lead Age (Denial)",
                        "Chaser Name",
                        "Client",
                        "MCN"
                    ]],
                    use_container_width=True
                )
        
            # 🚨 Check for leads with both Approval & Denial
            both_dates = df_lead_age[df_lead_age["Approval date"].notna() & df_lead_age["Denial Date"].notna()]
            if not both_dates.empty:
                st.warning(f"⚠️ Found {len(both_dates)} leads with BOTH Approval & Denial dates. Please review.")
                with st.expander("🔍 View Leads with BOTH Approval & Denial"):
                    cols_to_show = [
                        "Created Time (Date)",
                        "Approval date",
                        "Denial Date",
                        "Lead Age (Approval)",
                        "Lead Age (Denial)",
                        "Chaser Name",
                        "Client",
                        "MCN"
                    ]
                    available_cols = [c for c in cols_to_show if c in both_dates.columns]
                    st.dataframe(both_dates[available_cols], use_container_width=True)
            
            
            # 📊 Lead Age Distribution – Approval
            if "Lead Age (Approval)" in df_lead_age.columns:
                df_lead_age["Approval Category"] = df_lead_age["Lead Age (Approval)"].dropna().apply(categorize_weeks)
                approval_summary_all = df_lead_age["Approval Category"].value_counts().reset_index()
                approval_summary_all.columns = ["Category", "Count"]

                # 1. (Chart) Show positive-only chart
                with st.expander("📊 Lead Age Distribution – Approval (Week 0+)"):
                    approval_summary_positive = approval_summary_all[
                        ~approval_summary_all["Category"].astype(str).str.contains("Week -")
                    ].copy()
                    
                    category_order_positive = sorted(
                        approval_summary_positive["Category"].dropna().unique(),
                        key=lambda x: int(x.split()[1])
                    )
        
                    chart_approval = (
                        alt.Chart(approval_summary_positive)
                        .mark_bar(color="#28a745") 
                        .encode(
                            x=alt.X("Category", sort=category_order_positive), 
                            y="Count",
                            tooltip=["Category", "Count"]
                        )
                    )
                    st.altair_chart(chart_approval, use_container_width=True)
                    
                # 2. (Warning Table) Show negative-only data
                negative_approval = df_lead_age[
                    df_lead_age["Approval Category"].astype(str).str.contains("Week -", na=False)
                ]
                if not negative_approval.empty:
                    st.warning(f"⚠️ Found {len(negative_approval)} approvals with negative week categories (before Week 0).")
                    with st.expander("🔍 View Negative Week Approvals"): # 👈 This is no longer nested
                        st.dataframe(
                            negative_approval[[
                                "Created Time", "Approval date", "Lead Age (Approval)",
                                "Approval Category", "Chaser Name", "Client", "MCN"
                            ]],
                            use_container_width=True
                        )

        
            # 📊 Lead Age Distribution – Denial
            if "Lead Age (Denial)" in df_lead_age.columns:
                df_lead_age["Denial Category"] = df_lead_age["Lead Age (Denial)"].dropna().apply(categorize_weeks)
                denial_summary_all = df_lead_age["Denial Category"].value_counts().reset_index()
                denial_summary_all.columns = ["Category", "Count"]

                # 1. (Chart) Show positive-only chart
                with st.expander("📊 Lead Age Distribution – Denial (Week 0+)"):
                    denial_summary_positive = denial_summary_all[
                        ~denial_summary_all["Category"].astype(str).str.contains("Week -")
                    ].copy()
                    
                    category_order_positive = sorted(
                        denial_summary_positive["Category"].dropna().unique(),
                        key=lambda x: int(x.split()[1])
                    )
        
                    chart_denial = (
                        alt.Chart(denial_summary_positive)
                        .mark_bar(color="#dc3545") 
                        .encode(
                            x=alt.X("Category", sort=category_order_positive),
                            y="Count",
                            tooltip=["Category", "Count"]
                        )
                    )
                    st.altair_chart(chart_denial, use_container_width=True)
                
                # 2. (Warning Table) Show negative-only data
                negative_denial = df_lead_age[
                    df_lead_age["Denial Category"].astype(str).str.contains("Week -", na=False)
                ]
                if not negative_denial.empty:
                    st.warning(f"⚠️ Found {len(negative_denial)} denials with negative week categories (before Week 0).")
                    with st.expander("🔍 View Negative Week Denials"): # 👈 This is no longer nested
                        st.dataframe(
                            negative_denial[[
                                "Created Time", "Denial Date", "Lead Age (Denial)",
                                "Denial Category", "Chaser Name", "Client", "MCN"
                            ]],
                            use_container_width=True
                        )

        
            # 📊 Grouped Bar Chart – Approval vs Denial per Chaser
            if "Chaser Name" in df_lead_age.columns:
                st.markdown("### 📊 Approval vs Denial Lead Age by Chaser (Week 0+)")
                
                # 🆕 Filter for positive-only data *before* melting
                df_lead_age_positive = df_lead_age.copy()
                if "Lead Age (Approval)" in df_lead_age_positive.columns:
                    df_lead_age_positive["Lead Age (Approval)"] = df_lead_age_positive["Lead Age (Approval)"].apply(lambda x: x if x >= 0 else pd.NA)
                if "Lead Age (Denial)" in df_lead_age_positive.columns:
                    df_lead_age_positive["Lead Age (Denial)"] = df_lead_age_positive["Lead Age (Denial)"].apply(lambda x: x if x >= 0 else pd.NA)

                grouped_chaser = pd.melt(
                    df_lead_age_positive, # 👈 Use the positive-only DF
                    id_vars=["Chaser Name"],
                    value_vars=["Lead Age (Approval)", "Lead Age (Denial)"],
                    var_name="Type",
                    value_name="Days"
                ).dropna()
        
                chart_grouped_chaser = (
                    alt.Chart(grouped_chaser)
                    .mark_bar()
                    .encode(
                        x="Chaser Name",
                        y="mean(Days)",
                        color="Type",
                        tooltip=["Chaser Name", "Type", "mean(Days)"]
                    )
                )
                st.altair_chart(chart_grouped_chaser, use_container_width=True)
        
            # 📊 Grouped Bar Chart – Approval vs Denial per Client
            if "Client" in df_lead_age.columns:
                st.markdown("### 📊 Approval vs Denial Lead Age by Client (Week 0+)")
                
                # 🆕 We can reuse df_lead_age_positive from above
                grouped_client = pd.melt(
                    df_lead_age_positive, # 👈 Use the positive-only DF
                    id_vars=["Client"],
                    value_vars=["Lead Age (Approval)", "Lead Age (Denial)"],
                    var_name="Type",
                    value_name="Days"
                ).dropna()
        
                chart_grouped_client = (
                    alt.Chart(grouped_client)
                    .mark_bar()
                    .encode(
                        x="Client",
                        y="mean(Days)",
                        color="Type",
                        tooltip=["Client", "Type", "mean(Days)"]
                    )
                )
                st.altair_chart(chart_grouped_client, use_container_width=True)


        
        
            # ================== DUPLICATES CHECK WITH PRODUCT (MODIFIED: Removed Grouped by Key Dates) ==================
        st.subheader("🔍 Duplicate Leads by MCN (Considering Product)")
        
        if "MCN" in df_filtered.columns and "Products" in df_filtered.columns:
            # --- Duplicates with same MCN and same Product ---
            dup_same_product = df_filtered[df_filtered.duplicated(subset=["MCN", "Products"], keep=False)].copy()
        
            if not dup_same_product.empty:
                st.warning(f"⚠️ Found {dup_same_product['MCN'].nunique()} unique MCNs duplicated with SAME Product "
                           f"(total {len(dup_same_product)} rows).")
                
                required_cols = [
                    "MCN", 
                    "Products", 
                    "Created Time", 
                    "Date of Sale", 
                    "Dr Name", 
                    "Client", 
                    "Chaser Name", 
                    "Chasing Disposition"
                ]
                
                available_dup_cols = [c for c in required_cols if c in df_filtered.columns]
                
                st.markdown("### 📋 Duplicate Leads (MCN & Product) Details")
                st.dataframe(
                    dup_same_product.sort_values(["MCN", "Products", "Created Time"])[available_dup_cols],
                    use_container_width=True
                )
                
            else:
                st.success("✅ No duplicate MCNs found with SAME product.")
        
            # --- Duplicates with different Product ---
            dup_diff_product_check = df_filtered[df_filtered.duplicated(subset=["MCN"], keep=False)].copy()
            
            dup_diff_product_grouped = dup_diff_product_check.groupby("MCN")["Products"].nunique().reset_index()
            mcn_with_diff_products = dup_diff_product_grouped[dup_diff_product_grouped["Products"] > 1]["MCN"]

            dup_diff_product = dup_diff_product_check[dup_diff_product_check["MCN"].isin(mcn_with_diff_products)].copy() 
            
            if not dup_diff_product.empty:
                st.info(f"ℹ️ Found {len(mcn_with_diff_products)} MCNs with DIFFERENT Products (not real dups).")
        
                with st.expander("📋 View MCNs with Different Products"):
                    cols_to_show_old = [
                        "MCN","Products","Chaser Name","Chaser Group","Date of Sale (Date)","Created Time (Date)",
                        "Assigned date (Date)","Approval date (Date)","Denial Date (Date)",
                        "Completion Date (Date)","Upload Date (Date)","Client",
                        "Chasing Disposition","Insurance","Type Of Sale"
                    ]
                    available_cols_for_diff_dups = [c for c in cols_to_show_old if c in dup_diff_product.columns]
                    
                    merged = dup_diff_product.merge(dup_diff_product_grouped[["MCN"]], on="MCN")
                    st.dataframe(
                        merged.sort_values(["MCN", "Products"])[available_cols_for_diff_dups],
                        use_container_width=True
                    )
        
        else:
            st.info("ℹ️ Columns **MCN** and/or **Products** not found in dataset.")


# --- 🔽🔽🔽Agent Performance on Dr Chase Leads Section🔽🔽🔽 ---
    st.markdown("---")
    st.subheader("📊 Agent Performance on Dr Chase Leads")
    
    df_merged_final = pd.DataFrame()
    if (not df_oplan.empty and 
        "MCN_clean" in df_ts.columns and 
        "MCN_clean" in df_oplan.columns):
        
        df_merged_final = pd.merge(
            df_ts, 
            df_oplan, # 
            on="MCN_clean", 
            how="inner", # 
            suffixes=('_DrChase', '_OPlan') # 
        )
            
    if not df_merged_final.empty:
        st.markdown(f"Found **{len(df_merged_final)}** matching leads between the two files.")
        with st.expander("🔍 View Merged Data"):
            st.dataframe(df_merged_final, use_container_width=True)
            
    else:
        st.warning("Could not find any matching leads (MCN) between the filtered Dr. Chase data and the O Plan file.")
    # --- 🔼🔼🔼 END OF NEW MERGE SECTION 🔼🔼🔼 ---


# --- 🔽🔽🔽 START OF NEW SECTION (Discrepancy Analysis) 🔽🔽🔽 ---
    st.markdown("---")
    st.subheader("📊Difference in (Dr. Chase vs. O Plan)")
    # 1. 
    df_discrepancy_analysis = pd.DataFrame()
    if (not df_oplan.empty and 
        "MCN_clean" in df_ts.columns and 
        "MCN_clean" in df_oplan.columns):
        
        # 
        # 
        df_ts_mcn = df_ts[["MCN_clean"]].drop_duplicates()
        df_oplan_mcn = df_oplan[["MCN_clean"]].drop_duplicates()

        # 
        # 
        df_discrepancy_analysis = pd.merge(
            df_ts_mcn, 
            df_oplan_mcn, 
            on="MCN_clean", 
            how="outer", # 
            indicator=True # 
        )

        # 2. 
        df_chase_only = df_discrepancy_analysis[df_discrepancy_analysis['_merge'] == 'left_only']
        
        # 3. 
        df_oplan_only = df_discrepancy_analysis[df_discrepancy_analysis['_merge'] == 'right_only']

        # 4. 
        df_matched = df_discrepancy_analysis[df_discrepancy_analysis['_merge'] == 'both']

        # 5. 
        st.markdown("### 📈 Discrepancy KPIs")
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        kpi_col1.metric("✅ Leads in Both Files", len(df_matched))
        kpi_col2.metric("⚠️ Leads in Dr. Chase ONLY", len(df_chase_only))
        kpi_col3.metric("⚠️ Leads in O Plan ONLY", len(df_oplan_only))
        style_metric_cards(
            background_color="#0E1117",
            border_left_color="#FF4B4B", 
            border_color="#444",
            box_shadow="2px 2px 10px rgba(0,0,0,0.5)"
        )

        # 6. 
        if not df_chase_only.empty:
            with st.expander(f"🔍 View {len(df_chase_only)} Leads: In Dr. Chase ONLY (Not in O Plan)"):
                # 
                st.dataframe(df_chase_only[["MCN_clean"]], use_container_width=True)

        if not df_oplan_only.empty:
            with st.expander(f"🔍 View {len(df_oplan_only)} Leads: In O Plan ONLY (Not in Dr. Chase)"):
                # 
                st.dataframe(df_oplan_only[["MCN_clean"]], use_container_width=True)
            
    else:
        st.warning("Could not perform Discrepancy analysis. Ensure 'O_Plan_Leads.csv' is loaded and contains an 'MCN' column.")
    # --- 🔼🔼🔼 END OF NEW SECTION 🔼🔼🔼 ---

