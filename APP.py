import streamlit as st
import pandas as pd
import altair as alt
import re
from streamlit_option_menu import option_menu
from streamlit_extras.metric_cards import style_metric_cards
import math # تم إضافتها للاستخدام في Lead Age Analysis

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
    if days >= 0:
        return f"Week {math.floor(days / 7) + 1}"
    else:
        return f"Week {math.ceil(days / 7)}" 

# ================== SYNONYMS & MAPS ==================
syn = {
    "created_time": ["created_time", "created time", "creation time", "created", "lead created", "request created"],
    "assign_date": ["assign_date", "assigned date", "assign time", "assigned time", "assigned on"],
    "approval_date": ["approval_date", "approved date", "approval time", "approved on"],
    "completion_date": ["completion_date", "completed date", "completion time", "closed date", "completed on"],
    "uploaded_date": ["uploaded_date", "upload date", "uploaded date", "uploaded on"],
    "assigned_to_chase": ["assigned to chase", "assigned_to_chase", "assigned to", "assigned user (chase)", "assigned chaser"],
}

name_map = {
    "a.williams": "Alfred Williams", "david.smith": "David Smith", "jimmy.daves": "Grayson Saint",
    "e.moore": "Eddie Moore", "aurora.stevens": "Aurora Stevens", "grayson.saint": "Grayson Saint",
    "emma.wilson": "Emma Wilson", "scarlett.mitchell": "Scarlett Mitchell", "lucas.diago": "Lucas Diago",
    "mia.alaxendar": "Mia Alaxendar", "ivy.brooks": "Ivy Brooks", "timothy.williams": "Timothy Williams",
    "sarah.adams": "Sarah Adams", "sara.adams": "Sarah Adams", "samy.youssef": "Samy Youssef",
    "candy.johns": "Candy Johns", "heather.robertson": "Heather Robertson", "a.cabello": "Andrew Cabello",
    "alia.scott": "Alia Scott", "sandra.sebastian": "Sandra Sebastian", "kayla.miller": "Kayla Miller"
}

samy_chasers = {
    "Emma Wilson", "Scarlett Mitchell", "Lucas Diago", "Mia Alaxendar",
    "Candy Johns", "Sandra Sebastian", "Alia Scott",
    "Ivy Brooks", "Heather Robertson", "Samy Youssef",
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
            .astype(str).str.strip().str.lower()
            .map(name_map)
            .fillna(df_cleaned[assigned_col])
        )
        df_cleaned["Chaser Group"] = df_cleaned["Chaser Name"].apply(
            lambda n: "Samy Chasers" if n in samy_chasers else "Andrew Chasers"
        )
    
    # 4. Ensure core columns used for calculation are datetime (already covered in step 2 but redundant check)
    date_actual_cols = [cols_map[k] for k in ["created_time","assign_date","approval_date","completion_date","uploaded_date"] if cols_map[k]]
    for c in date_actual_cols:
         if c in df_cleaned.columns:
            df_cleaned[c] = pd.to_datetime(df_cleaned[c], errors="coerce")

    return df_cleaned

# ================== EXECUTE DATA LOAD ==================
df_cleaned = load_and_clean_data(df_raw, name_map, cols_map, samy_chasers)
st.success("✅ File loaded and cleaned successfully! (Cached for speed)")

# ================== COLUMN DESCRIPTIONS ==================
# (Your column_descriptions dictionary remains here for reference, but skipped for brevity in the final output block)

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


# ================== SIDEBAR FILTERS (FIXED: Handling Date Range TypeError) ==================
st.sidebar.header("🎛 Basic Filters")

# ... (Client, Chaser Name, Chaser Group, Chasing Disposition filters - UNCHANGED) ...
with st.sidebar.expander("👥 Client", expanded=False):
    all_clients = df_cleaned["Client"].unique().tolist()
    select_all_clients = st.checkbox("Select All Clients", value=True, key="all_clients")
    if select_all_clients:
        Client = st.multiselect("Select Client", options=all_clients, default=all_clients)
    else:
        Client = st.multiselect("Select Client", options=all_clients)


with st.sidebar.expander("🧑‍💼 Chaser Name", expanded=False):
    all_Chaser_Name=df_cleaned["Chaser Name"].unique().tolist()
    select_all_Chaser_Name = st.checkbox("Select All Chaser Name ", value=True, key="all_Chaser_Name")
    if select_all_Chaser_Name:
        Chaser_Name = st.multiselect("Select Chaser Name", options=all_Chaser_Name, default=all_Chaser_Name)   
    else:
        Chaser_Name  = st.multiselect("Select  Chaser Name ", options=all_Chaser_Name)
            

with st.sidebar.expander("👨‍👩‍👧‍👦 Chaser Group", expanded=False):
    all_Chaser_Group=df_cleaned["Chaser Group"].unique().tolist()
    select_all_Chaser_Group = st.checkbox("Select All Chaser Group ", value=True, key="all_Chaser_Group")
    if select_all_Chaser_Group:
        Chaser_Group = st.multiselect("Select Chaser Group", options=all_Chaser_Group, default=all_Chaser_Group)   
    else:
        Chaser_Group  = st.multiselect("Select  Chaser Group ", options=all_Chaser_Group)


with st.sidebar.expander("👥 Chasing Disposition", expanded=False):
    all_Chasing_Disposition=df_cleaned["Chasing Disposition"].unique().tolist()
    select_all_Chasing_Disposition = st.checkbox("Select All Chaser Disposition ", value=True, key="all_Chasing_Disposition")
    if select_all_Chasing_Disposition:
        Chasing_Disposition = st.multiselect("Select Chaser Disposition", options=all_Chasing_Disposition, default=all_Chasing_Disposition)   
    else:
        Chasing_Disposition  = st.multiselect("Select  Chaser Disposition ", options=all_Chasing_Disposition)


with st.sidebar.expander("📅 Date Range", expanded=False):
    date_cols_for_range = [
        "Created Time", "Assigned date", "Completion Date", "Approval date",
        "Denial Date", "Modified Time", "Date of Sale", "Upload Date"
    ]
    
    valid_date_cols = [c for c in date_cols_for_range if c in df_cleaned.columns]
    
    if valid_date_cols:
        # **FIX**: Combine all date values into one Series, drop NaT, and get min/max Timestamp
        all_dates = pd.concat([df_cleaned[c].dropna() for c in valid_date_cols])
        
        if not all_dates.empty:
            min_ts = all_dates.min()
            max_ts = all_dates.max()
            
            # Convert Timestamp to datetime.date for st.date_input
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
df_filtered = df_cleaned.query(
    "Client in @Client and `Chaser Name` in @Chaser_Name and `Chaser Group` in @Chaser_Group and `Chasing Disposition` in @Chasing_Disposition"
)

# Apply date filter (on Created Time by default)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    if "Created Time" in df_filtered.columns:
        # Note: we compare the datetime.date objects from the filter with the .dt.date of the dataframe column
        df_filtered = df_filtered[
            (df_filtered["Created Time"].dt.date >= start_date)
            & (df_filtered["Created Time"].dt.date <= end_date)
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

    # ... (KPIs, Date Summary, Numeric Summary, Column Descriptions - UNCHANGED) ...

# ================== MAIN DASHBOARD (Data Analysis) ==================
elif selected == "Data Analysis":
    st.title("📊 Data Analysis – Advanced Insights")
    st.info("This page provides **deeper analysis** including time-series trends, insights summaries, and lead age analysis by Chaser / Client.")

    # --- Allowed columns for analysis ---
    allowed_columns = [
        "Created Time (Date)", "Assigned date (Date)", "Approval date (Date)",
        "Denial Date (Date)", "Completion Date (Date)", "Upload Date (Date)",
        "Date of Sale (Date)",
    ]
    available_columns = [c for c in allowed_columns if c in df_filtered.columns]
    
    if not available_columns:
        st.warning("⚠️ None of the predefined analysis columns are available in the dataset.")
        st.markdown(f""" The dataset contains **{len(df_filtered)} rows** and **{len(df_filtered.columns)} columns**. """)
        table(df_filtered)
        st.stop() 

    time_col = st.selectbox("Select column for time series analysis", available_columns)
    original_col = time_col.replace(" (Date)", "") # e.g., 'Created Time'
    
    df_ts = df_filtered.copy()
    
    if original_col in df_ts.columns:
        # Filter out NaT values for time series accuracy
        df_ts = df_ts[df_ts[original_col].notna()].copy()

        today = pd.Timestamp.now().normalize()
        future_mask = df_ts[original_col].dt.normalize() > today
        if future_mask.any():
             st.warning(f"⚠️ Detected {future_mask.sum()} rows with future {original_col} values.")
             if st.checkbox("Show rows with future dates"):
                  st.dataframe(df_ts.loc[future_mask])
        
        df_ts = df_ts.loc[~future_mask].copy() # Filter out future dates

    st.markdown(f""" The working dataset for analysis contains **{len(df_ts)} rows**
                     and **{len(df_ts.columns)} columns**.
                 """)
    table(df_ts)

    if not df_ts.empty and original_col in df_ts.columns:
        # --- Time Series Aggregation ---
        freq = st.radio("Aggregation level:", ["Daily", "Weekly", "Monthly"], horizontal=True)
        period_map = {"Daily": "D", "Weekly": "W", "Monthly": "M"}
        df_ts["Period"] = df_ts[original_col].dt.to_period(period_map[freq]).dt.to_timestamp()
        
        # ... (Time series chart logic - UNCHANGED) ...
        group_by = st.selectbox("Break down by:", ["None", "Client", "Chaser Name", "Chaser Group"])
        if group_by == "None":
            ts_data = df_ts.groupby("Period").size().reset_index(name="Lead Count")
        else:
            ts_data = df_ts.groupby(["Period", group_by]).size().reset_index(name="Lead Count")
        
        # 📈 Historical Time Series (Chart logic)
        st.subheader("📈 Historical Time Series")
        x_axis_format = "%Y-%m-%d" 
        if freq == "Weekly":
            x_axis_format = "%Y-%W" 
        elif freq == "Monthly":
            x_axis_format = "%Y-%m" 
            
        # (Altair chart code for Time Series remains unchanged)

        # 🏆 Top performers (Table logic)

        # ================== Chasing Disposition Distribution (FIXED: Added Data Labels & Percentage) ==================
        if "Chasing Disposition" in df_ts.columns:
            st.subheader("📊 Chasing Disposition Distribution")

            metric_option = st.selectbox(
                "Select metric to display by Chasing Disposition:",
                [
                    "Total Leads (with Created Time (Date))", "Total Assigned", "Not Assigned",
                    "Total Approved", "Total Denied", "Total Completed", "Total Uploaded"
                ]
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
                "Total Leads (with Created Time (Date))": "Created Time (Date)", "Total Assigned": "Assigned date",
                "Not Assigned": "Not Assigned", "Total Approved": "Approval date",
                "Total Denied": "Denial Date", "Total Completed": "Completion Date", "Total Uploaded": "Upload Date"
            }

            selected_col = metric_map[metric_option]
            chart_data = metrics_by_disp[["Chasing Disposition", selected_col]].rename(columns={selected_col: "Count"})
            
            # ✅ FIX: Calculate Percentage and Label for Data Labels
            total_for_percentage = chart_data["Count"].sum() 
            
            if total_for_percentage > 0:
                chart_data["Percentage"] = (chart_data["Count"] / total_for_percentage * 100).round(1)
                chart_data["Label"] = chart_data.apply(
                    lambda row: f'{row["Count"]:,} ({row["Percentage"]}%)', axis=1
                )
            else:
                chart_data["Percentage"] = 0.0
                chart_data["Label"] = chart_data["Count"].apply(lambda x: f'{x:,} (0.0%)')


            # --- Bar chart ---
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
            
            # --- Text Layer (Data Label) ---
            text = chart_disp.mark_text(
                align='left', 
                baseline='middle', 
                dx=5,  # Slight offset right
                angle=270, # Rotated
                color='white',
                fontSize=10
            ).encode(
                text=alt.Text("Label") # Use the combined label
            )

            # --- Final Chart ---
            final_chart = chart_disp + text
            st.altair_chart(final_chart, use_container_width=True)

        # ... (Client Distribution, Insights Summary, Lead Age Analysis, Duplicates Check - UNCHANGED) ...
