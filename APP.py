import streamlit as st
import pandas as pd
import altair as alt
import re
from streamlit_extras.metric_cards import style_metric_cards

# ================== PAGE CONFIG ==================
st.set_page_config(
    page_title="DR Chase Leads Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================== LOAD DATA ==================
df = pd.read_csv("Dr_Chase_Leads.csv", low_memory=False)
df.columns = df.columns.str.strip()
st.success("✅ File loaded successfully!")

# ================== CLEAN DATA ==================
columns_to_remove = [
    "Is Converted From Lead", "Height", "Weight", "Waist Size", "Dr Phone Number", "Dr Fax",
    "Dr Alternative Phone", "Dr Address", "Dr City", "Dr ZIP Code", "NPI", "Dr Info Extra Comments",
    "Dr. Name", "Exception", "Initial Agent", "Full Name", "Last Name", "Secondary Phone", "Address",
    "Gender", "ZIP Code", "City", "Phase","First Name","LOMN?","Source","Brace Size","Extra Comments" ,"CBA","Primary Phone"
]
df_cleaned = df.drop(columns=[c for c in columns_to_remove if c in df.columns], errors="ignore")

date_columns = [
    "Created Time", "Assigned date", "Completion Date", "Approval date",
    "Denial Date", "Modified Time", "Date of Sale", "Upload Date", 
]
for col in date_columns:
    if col in df_cleaned.columns:
        df_cleaned[col] = pd.to_datetime(df_cleaned[col], errors="coerce", dayfirst=True)
        df_cleaned[col + " (Date)"] = df_cleaned[col].dt.date

df_filtered = df_cleaned.copy()

# ================== SIDEBAR FILTERS ==================
st.sidebar.header("🎛 Basic Filters")

with st.sidebar.expander("👥 Client", expanded=False):
    all_clients = df_cleaned["Client"].dropna().unique().tolist()
    Client = st.multiselect("Select Client", options=all_clients, default=all_clients)

with st.sidebar.expander("🧑‍💼 Chaser Name", expanded=False):
    all_chasers = df_cleaned["Chaser Name"].dropna().unique().tolist()
    Chaser_Name = st.multiselect("Select Chaser Name", options=all_chasers, default=all_chasers)

with st.sidebar.expander("👨‍👩‍👧‍👦 Chaser Group", expanded=False):
    all_groups = df_cleaned["Chaser Group"].dropna().unique().tolist()
    Chaser_Group = st.multiselect("Select Chaser Group", options=all_groups, default=all_groups)

with st.sidebar.expander("👥 Chasing Disposition", expanded=False):
    all_disp = df_cleaned["Chasing Disposition"].dropna().unique().tolist()
    Chasing_Disposition = st.multiselect("Select Chaser Disposition", options=all_disp, default=all_disp)

with st.sidebar.expander("📅 Date Range", expanded=False):
    min_date = pd.to_datetime(df_cleaned[date_columns].min().min()).date()
    max_date = pd.to_datetime(df_cleaned[date_columns].max().max()).date()
    date_range = st.date_input("Select date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

# --- Apply filters ---
df_filtered = df_cleaned.query(
    "Client in @Client and `Chaser Name` in @Chaser_Name and `Chaser Group` in @Chaser_Group and `Chasing Disposition` in @Chasing_Disposition"
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    if "Created Time" in df_filtered.columns:
        df_filtered = df_filtered[
            (df_filtered["Created Time"].dt.date >= start_date) &
            (df_filtered["Created Time"].dt.date <= end_date)
        ]

# ================== MAIN DASHBOARD ==================
st.title("📊 DR Chase Leads Dashboard (One Page)")
st.info("All dataset overview and analysis are combined here.")

# --- Dataset Summary / KPIs ---
st.subheader("📑 Dataset Summary")
total_leads = len(df_filtered)
total_completed = df_filtered["Completion Date"].notna().sum()
total_assigned = df_filtered["Assigned date"].notna().sum()
total_uploaded = df_filtered["Upload Date"].notna().sum()
total_approval = df_filtered["Approval date"].notna().sum()
total_denial = df_filtered["Denial Date"].notna().sum()
total_not_assigned = total_leads - total_assigned

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📊 Total Leads", f"{total_leads:,}")
    st.metric("✅ Completed", f"{total_completed:,}")
with col2:
    st.metric("🧑‍💼 Assigned", f"{total_assigned:,}")
    st.metric("📤 Uploaded", f"{total_uploaded:,}")
with col3:
    st.metric("🚫 Not Assigned", f"{total_not_assigned:,}")
    st.metric("✔ Approvals / ❌ Denials", f"{total_approval:,} / {total_denial:,}")

style_metric_cards()

# ================== Data Analysis ==================
st.subheader("📈 Data Analysis")
date_candidates = [c for c in df_filtered.columns if ("date" in c.lower()) or pd.api.types.is_datetime64_any_dtype(df_filtered[c])]
if date_candidates:
    time_col = st.selectbox("Select date column for time series analysis", date_candidates)
    df_filtered[time_col] = pd.to_datetime(df_filtered[time_col], errors="coerce")
    df_ts = df_filtered.dropna(subset=[time_col])

    freq = st.radio("Aggregation level:", ["Daily", "Weekly", "Monthly"], horizontal=True)
    period_map = {"Daily": "D", "Weekly": "W", "Monthly": "M"}
    df_ts["Period"] = df_ts[time_col].dt.to_period(period_map[freq]).dt.to_timestamp()

    group_by = st.selectbox("Break down by:", ["None", "Client", "Chaser Name", "Chaser Group"])
    if group_by == "None":
        ts_data = df_ts.groupby("Period").size().reset_index(name="Lead Count")
    else:
        ts_data = df_ts.groupby(["Period", group_by]).size().reset_index(name="Lead Count")

    if not ts_data.empty:
        chart = alt.Chart(ts_data).mark_line(point=True).encode(
            x="Period:T", y="Lead Count",
            color=group_by if group_by != "None" else alt.value("#007bff"),
            tooltip=["Period:T", "Lead Count"] + ([group_by] if group_by != "None" else [])
        )
        st.altair_chart(chart, use_container_width=True)

# ================== Lead Age Analysis ==================
st.subheader("⏳ Lead Age Analysis")
if "Created Time" in df_filtered.columns and "Completion Date" in df_filtered.columns:
    df_lead_age = df_filtered.copy()
    df_lead_age["Lead Age (Days)"] = (df_lead_age["Completion Date"] - df_lead_age["Created Time"]).dt.days

    def categorize_weeks(days):
        if pd.isna(days): return "Not Completed"
        if days <= 7: return "Week 1"
        if days <= 14: return "Week 2"
        if days <= 21: return "Week 3"
        if days <= 28: return "Week 4"
        return "Week 5+"
    df_lead_age["Lead Age Category"] = df_lead_age["Lead Age (Days)"].apply(categorize_weeks)

    st.dataframe(df_lead_age[["MCN","Client","Chaser Name","Created Time","Completion Date","Lead Age (Days)","Lead Age Category"]])

    age_summary = df_lead_age["Lead Age Category"].value_counts().reset_index()
    age_summary.columns = ["Lead Age Category","Count"]
    st.table(age_summary)

    chart_age = alt.Chart(age_summary).mark_bar().encode(
        x="Lead Age Category", y="Count", tooltip=["Lead Age Category","Count"]
    )
    st.altair_chart(chart_age, use_container_width=True)

# ================== DOWNLOAD ==================
st.download_button(
    label="💾 Download Filtered CSV",
    data=df_filtered.to_csv(index=False).encode("utf-8"),
    file_name="Dr_Chase_Leads_Filtered.csv",
    mime="text/csv"
)
