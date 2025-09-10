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

# ================== HELPER FUNCTIONS ==================
def norm(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(s).strip().lower())

def find_col(df_cols, candidates):
    cand_norm = {norm(c) for c in candidates}
    for c in df_cols:
        if norm(c) in cand_norm:
            return c
    return None

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
    "Denial Date", "Modified Time", "Date of Sale", "Upload Date"
]

for col in date_columns:
    if col in df_cleaned.columns:
        df_cleaned[col] = pd.to_datetime(df_cleaned[col], errors="coerce", dayfirst=True)
        df_cleaned[col + " (Date)"] = df_cleaned[col].dt.date

# ================== SIDEBAR FILTERS ==================
st.sidebar.header("🎛 Filters")

# --- Clients ---
all_clients = df_cleaned["Client"].dropna().unique().tolist()
Client = st.sidebar.multiselect("Select Client(s)", all_clients, default=all_clients)

# --- Chaser Names ---
all_chasers = df_cleaned["Chaser Name"].dropna().unique().tolist()
Chaser_Name = st.sidebar.multiselect("Select Chaser(s)", all_chasers, default=all_chasers)

# --- Chaser Groups ---
if "Chaser Group" in df_cleaned.columns:
    all_groups = df_cleaned["Chaser Group"].dropna().unique().tolist()
    Chaser_Group = st.sidebar.multiselect("Select Chaser Group(s)", all_groups, default=all_groups)
else:
    Chaser_Group = []

# --- Date Range ---
min_date = pd.to_datetime(df_cleaned[date_columns].min().min()).date()
max_date = pd.to_datetime(df_cleaned[date_columns].max().max()).date()
date_range = st.sidebar.date_input("Select date range", value=(min_date, max_date))

# ================== APPLY FILTERS ==================
df_filtered = df_cleaned.copy()
if Client: df_filtered = df_filtered[df_filtered["Client"].isin(Client)]
if Chaser_Name: df_filtered = df_filtered[df_filtered["Chaser Name"].isin(Chaser_Name)]
if Chaser_Group: df_filtered = df_filtered[df_filtered["Chaser Group"].isin(Chaser_Group)]

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    if "Created Time" in df_filtered.columns:
        df_filtered = df_filtered[
            (df_filtered["Created Time"].dt.date >= start_date) &
            (df_filtered["Created Time"].dt.date <= end_date)
        ]

# ================== MAIN DASHBOARD ==================
st.title("📊 DR Chase Leads Dashboard")

# --- Dataset Summary ---
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

# --- Numeric Columns Summary ---
st.subheader("🔢 Numeric Columns Summary")
num_cols = df_filtered.select_dtypes(include=["int64","float64"]).columns
if len(num_cols) > 0:
    num_summary = pd.DataFrame({
        "Column": num_cols,
        "Min": [df_filtered[c].min() for c in num_cols],
        "Max": [df_filtered[c].max() for c in num_cols],
        "Mean": [round(df_filtered[c].mean(), 2) for c in num_cols]
    })
    st.table(num_summary)

# --- Column Descriptions ---
st.subheader("📖 Column Descriptions")
desc_cols = ["Chaser Name","Chaser Group","Created Time","Assigned date","Approval date","Completion Date","Upload Date","Client"]
selected_col = st.selectbox("Select a column to view description", desc_cols)
st.info(f"**{selected_col}**: Description about this column.")

# --- Distribution of Chaser Name ---
if "Chaser Name" in df_filtered.columns:
    st.subheader("📊 Distribution of Chaser Name")
    chaser_counts = df_filtered["Chaser Name"].value_counts().reset_index()
    chaser_counts.columns = ["Chaser Name","Count"]
    chart = alt.Chart(chaser_counts).mark_bar().encode(
        x=alt.X("Chaser Name", sort="-y"),
        y="Count",
        tooltip=["Chaser Name","Count"]
    )
    st.altair_chart(chart, use_container_width=True)

# ================== TIME SERIES ==================
st.subheader("📈 Time Series Analysis")
date_candidates = [c for c in df_filtered.columns if "date" in c.lower()]
time_col = st.selectbox("Select date column", date_candidates)

df_ts = df_filtered.dropna(subset=[time_col]).copy()
freq = st.radio("Aggregation level:", ["Daily","Weekly","Monthly"], horizontal=True)
period_map = {"Daily":"D","Weekly":"W","Monthly":"M"}
df_ts["Period"] = df_ts[time_col].dt.to_period(period_map[freq]).dt.to_timestamp()

group_by = st.selectbox("Break down by:", ["None","Client","Chaser Name","Chaser Group"])
if group_by == "None":
    ts_data = df_ts.groupby("Period").size().reset_index(name="Lead Count")
else:
    ts_data = df_ts.groupby(["Period",group_by]).size().reset_index(name="Lead Count")

if not ts_data.empty:
    if group_by == "None":
        chart = alt.Chart(ts_data).mark_line(point=True).encode(x="Period:T",y="Lead Count")
    else:
        chart = alt.Chart(ts_data).mark_line(point=True).encode(x="Period:T",y="Lead Count",color=group_by)
    st.altair_chart(chart, use_container_width=True)

# --- Insights Summary ---
st.subheader("📝 Insights Summary")
total_time_leads = len(df_ts)
st.write(f"Based on **{time_col}**, there are **{total_time_leads} leads**.")

# ================== LEAD AGE ANALYSIS ==================
st.subheader("⏳ Lead Age Analysis")
if "Created Time" in df_ts.columns and "Completion Date" in df_ts.columns:
    df_lead_age = df_ts.copy()
    df_lead_age["Lead Age (Days)"] = (df_lead_age["Completion Date"] - df_lead_age["Created Time"]).dt.days

    # Full Lead Age Table
    st.markdown("### 📋 Full Lead Age Table")
    st.dataframe(df_lead_age[["Created Time","Completion Date","Lead Age (Days)","Chaser Name","Client"]])

    # Lead Age Distribution
    st.markdown("### 📊 Lead Age Distribution")
    age_summary = df_lead_age["Lead Age (Days)"].dropna().astype(int).value_counts(bins=10).reset_index()
    age_summary.columns = ["Range","Count"]
    st.bar_chart(age_summary.set_index("Range"))

    # Average & Median by Chaser
    st.markdown("### 📊 Average & Median Lead Age by Chaser")
    avg_chaser = df_lead_age.groupby("Chaser Name")["Lead Age (Days)"].agg(["mean","median"]).reset_index()
    st.dataframe(avg_chaser)

    # Average & Median by Client
    st.markdown("### 📊 Average & Median Lead Age by Client")
    avg_client = df_lead_age.groupby("Client")["Lead Age (Days)"].agg(["mean","median"]).reset_index()
    st.dataframe(avg_client)

# ================== TOP CHASERS ==================
st.subheader("🏆 Top Chaser Names by Leads")
if "Chaser Name" in df_ts.columns:
    top_chasers = df_ts["Chaser Name"].value_counts().reset_index().head(5)
    top_chasers.columns = ["Chaser Name","Lead Count"]
    st.table(top_chasers)

# ================== DOWNLOAD ==================
st.download_button(
    label="💾 Download Filtered CSV",
    data=df_filtered.to_csv(index=False).encode("utf-8"),
    file_name="Dr_Chase_Leads_Filtered.csv",
    mime="text/csv"
)
