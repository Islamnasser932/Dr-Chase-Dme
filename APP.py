import streamlit as st
import pandas as pd
import altair as alt
import re
from streamlit_extras.metric_cards import style_metric_cards

# ================== PAGE CONFIG ==================
st.set_page_config(
    page_title="DR Chase Leads Dashboard (Single Page)",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================== LOAD DATA ==================
DATA_PATH = "Dr_Chase_Leads.csv"
try:
    df = pd.read_csv(DATA_PATH, low_memory=False)
except FileNotFoundError as e:
    st.error(f"CSV file not found at `{DATA_PATH}` — put the file in the same folder as this script or update DATA_PATH.")
    st.stop()

df.columns = df.columns.str.strip()

# ================== HELPERS ==================
def norm(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(s).strip().lower())

def find_col(df_cols, candidates):
    cand_norm = {norm(c) for c in candidates}
    for c in df_cols:
        if norm(c) in cand_norm:
            return c
    return None

# synonyms to try find alternate column names
syn = {
    "created_time": ["created_time", "created time", "creation time", "created", "lead created", "request created"],
    "assign_date": ["assign_date", "assigned date", "assign time", "assigned time", "assigned on"],
    "approval_date": ["approval_date", "approved date", "approval time", "approved on"],
    "completion_date": ["completion_date", "completed date", "completion time", "closed date", "completed on"],
    "uploaded_date": ["uploaded_date", "upload date", "uploaded date", "uploaded on"],
    "assigned_to_chase": ["assigned to chase", "assigned_to_chase", "assigned to", "assigned user (chase)", "assigned chaser"],
}

cols_map = {
    "created_time": find_col(df.columns, syn["created_time"]) or ("Created Time" if "Created Time" in df.columns else None),
    "assign_date": find_col(df.columns, syn["assign_date"]) or ("Assigned date" if "Assigned date" in df.columns else None),
    "approval_date": find_col(df.columns, syn["approval_date"]) or ("Approval date" if "Approval date" in df.columns else None),
    "completion_date": find_col(df.columns, syn["completion_date"]) or ("Completion Date" if "Completion Date" in df.columns else None),
    "uploaded_date": find_col(df.columns, syn["uploaded_date"]) or ("Upload Date" if "Upload Date" in df.columns else None),
    "assigned_to_chase": find_col(df.columns, syn["assigned_to_chase"]) or None,
}

# ================== CLEANING & DERIVED COLUMNS ==================
# drop some noisy columns if present
columns_to_remove = [
    "Is Converted From Lead", "Height", "Weight", "Waist Size", "Dr Phone Number", "Dr Fax",
    "Dr Alternative Phone", "Dr Address", "Dr City", "Dr ZIP Code", "NPI", "Dr Info Extra Comments",
    "Dr. Name", "Exception", "Initial Agent", "Full Name", "Last Name", "Secondary Phone", "Address",
    "Gender", "ZIP Code", "City", "Phase","First Name","LOMN?","Source","Brace Size","Extra Comments" ,"CBA","Primary Phone"
]
df_cleaned = df.drop(columns=[c for c in columns_to_remove if c in df.columns], errors="ignore").copy()

# Force convert known date-like columns to datetime
known_date_cols = [
    cols_map.get("created_time"),
    cols_map.get("assign_date"),
    cols_map.get("approval_date"),
    cols_map.get("completion_date"),
    cols_map.get("uploaded_date"),
    "Denial Date", "Modified Time", "Date of Sale", "Upload Date", "Assigned date", "Approval date", "Completion Date", "Created Time"
]
known_date_cols = [c for c in known_date_cols if c and c in df_cleaned.columns]
for c in known_date_cols:
    df_cleaned[c] = pd.to_datetime(df_cleaned[c], errors="coerce", dayfirst=True)
    # also create (Date) column for UX
    df_cleaned[c + " (Date)"] = df_cleaned[c].dt.date

# standard mapped names (if assigned col exists)
name_map = {
    "a.williams": "Alfred Williams",
    "david.smith": "David Smith",
    "jimmy.daves": "Grayson Saint",
    "e.moore": "Eddie Moore",
    "aurora.stevens": "Aurora Stevens",
    "grayson.saint": "Grayson Saint",
    "emma.wilson": "Emma Wilson",
    "scarlett.mitchell": "Scarlett Mitchell",
    "lucas.diago": "Lucas Diago",
    "mia.alaxendar": "Mia Alaxendar",
    "ivy.brooks": "Ivy Brooks",
    "timothy.williams": "Timothy Williams",
    "sarah.adams": "Sarah Adams",
    "sara.adams": "Sarah Adams",
    "samy.youssef": "Samy Youssef",
    "candy.johns": "Candy Johns",
    "heather.robertson": "Heather Robertson",
    "a.cabello": "Andrew Cabello",
    "alia.scott": "Alia Scott",
    "sandra.sebastian": "Sandra Sebastian",
    "kayla.miller": "Kayla Miller"
}
assigned_col = cols_map.get("assigned_to_chase")
if assigned_col and assigned_col in df_cleaned.columns:
    df_cleaned["Chaser Name"] = (
        df_cleaned[assigned_col].astype(str).str.strip().str.lower().map(name_map).fillna(df_cleaned[assigned_col])
    )

# fallback ensure the column exists (sometimes already present)
if "Chaser Name" not in df_cleaned.columns and assigned_col and assigned_col in df_cleaned.columns:
    df_cleaned["Chaser Name"] = df_cleaned[assigned_col]

# create Chaser Group simple mapping if not present
if "Chaser Group" not in df_cleaned.columns:
    samy_chasers = {
        "Emma Wilson", "Scarlett Mitchell", "Lucas Diago", "Mia Alaxendar",
        "Candy Johns", "Sandra Sebastian", "Alia Scott",
        "Ivy Brooks", "Heather Robertson", "Samy Youssef",
        "Sarah Adams", "Timothy Williams"
    }
    if "Chaser Name" in df_cleaned.columns:
        df_cleaned["Chaser Group"] = df_cleaned["Chaser Name"].apply(
            lambda n: "Samy Chasers" if n in samy_chasers else "Andrew Chasers"
        )

# safe references to common columns
CREATED = cols_map.get("created_time") or ("Created Time" if "Created Time" in df_cleaned.columns else None)
ASSIGNED = cols_map.get("assign_date") or ("Assigned date" if "Assigned date" in df_cleaned.columns else None)
APPROVAL = cols_map.get("approval_date") or ("Approval date" if "Approval date" in df_cleaned.columns else None)
COMPLETION = cols_map.get("completion_date") or ("Completion Date" if "Completion Date" in df_cleaned.columns else None)
UPLOAD = cols_map.get("uploaded_date") or ("Upload Date" if "Upload Date" in df_cleaned.columns else None)

# ================== SIDEBAR FILTERS ==================
st.sidebar.header("🎛 Filters")

# Client filter with select-all
clients = df_cleaned["Client"].dropna().unique().tolist() if "Client" in df_cleaned.columns else []
select_all_clients = st.sidebar.checkbox("Select All Clients", value=True, key="sel_all_clients")
Client = st.sidebar.multiselect("Client", options=clients, default=clients if select_all_clients else [])

# Chaser Name filter with select-all
chasers = df_cleaned["Chaser Name"].dropna().unique().tolist() if "Chaser Name" in df_cleaned.columns else []
select_all_chasers = st.sidebar.checkbox("Select All Chasers", value=True, key="sel_all_chasers")
Chaser_Name = st.sidebar.multiselect("Chaser Name", options=chasers, default=chasers if select_all_chasers else [])

# Chaser Group with select-all
groups = df_cleaned["Chaser Group"].dropna().unique().tolist() if "Chaser Group" in df_cleaned.columns else []
select_all_groups = st.sidebar.checkbox("Select All Groups", value=True, key="sel_all_groups")
Chaser_Group = st.sidebar.multiselect("Chaser Group", options=groups, default=groups if select_all_groups else [])

# Chasing Disposition with select-all (if present)
disps = df_cleaned["Chasing Disposition"].dropna().unique().tolist() if "Chasing Disposition" in df_cleaned.columns else []
select_all_disps = st.sidebar.checkbox("Select All Dispositions", value=True, key="sel_all_disps")
Chasing_Disposition = st.sidebar.multiselect("Chasing Disposition", options=disps, default=disps if select_all_disps else [])

# Date range filter - pick which date column to apply the date range on
available_date_cols = [c for c in known_date_cols]  # already filtered to present columns
if not available_date_cols:
    available_date_cols = [c for c in df_cleaned.columns if "date" in c.lower()][:1]  # fallback

if available_date_cols:
    date_filter_col = st.sidebar.selectbox("Apply date range to", available_date_cols, index=available_date_cols.index(CREATED) if CREATED in available_date_cols else 0)
    min_date = pd.to_datetime(df_cleaned[date_filter_col].min()).date() if df_cleaned[date_filter_col].notna().any() else pd.Timestamp.now().date()
    max_date = pd.to_datetime(df_cleaned[date_filter_col].max()).date() if df_cleaned[date_filter_col].notna().any() else pd.Timestamp.now().date()
    date_range = st.sidebar.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
else:
    date_filter_col = None
    date_range = None

# ================== APPLY SIDEBAR FILTERS ==================
df_filtered = df_cleaned.copy()

if clients:
    if Client:
        df_filtered = df_filtered[df_filtered["Client"].isin(Client)]
if chasers:
    if Chaser_Name:
        df_filtered = df_filtered[df_filtered["Chaser Name"].isin(Chaser_Name)]
if groups:
    if Chaser_Group:
        df_filtered = df_filtered[df_filtered["Chaser Group"].isin(Chaser_Group)]
if disps:
    if Chasing_Disposition:
        df_filtered = df_filtered[df_filtered["Chasing Disposition"].isin(Chasing_Disposition)]

# apply date range filter to the chosen date column
if date_filter_col and isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    mask = df_filtered[date_filter_col].notna()
    mask &= (df_filtered[date_filter_col].dt.date >= start_date) & (df_filtered[date_filter_col].dt.date <= end_date)
    df_filtered = df_filtered.loc[mask]

# ================== MAIN (SINGLE PAGE) LAYOUT ==================
st.title("📊 DR Chase Leads Dashboard — Single Page")
st.info("This single-page view combines Dataset Overview, Time Series analysis, Insights and Lead Age analysis. Filters on the left affect everything below.")

# ---------------- Dataset Summary ----------------
st.subheader("📑 Dataset Summary")
total_leads = len(df_filtered)
total_assigned = df_filtered[ASSIGNED].notna().sum() if ASSIGNED else 0
total_uploaded = df_filtered[UPLOAD].notna().sum() if UPLOAD else 0
total_approval = df_filtered[APPROVAL].notna().sum() if APPROVAL else 0
total_denial = df_filtered["Denial Date"].notna().sum() if "Denial Date" in df_filtered.columns else 0
total_completed = df_filtered[COMPLETION].notna().sum() if COMPLETION else 0
total_not_assigned = total_leads - total_assigned

pct = lambda x: (x / total_leads * 100) if total_leads > 0 else 0

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📊 Total Leads", f"{total_leads:,}")
    st.metric("🧑‍💼 Assigned", f"{total_assigned:,} ({pct(total_assigned):.1f}%)")
with col2:
    st.metric("🚫 Not Assigned", f"{total_not_assigned:,} ({pct(total_not_assigned):.1f}%)")
    st.metric("✔ Approvals", f"{total_approval:,} ({pct(total_approval):.1f}%)")
with col3:
    st.metric("📤 Uploaded", f"{total_uploaded:,} ({pct(total_uploaded):.1f}%)")
    st.metric("✅ Completed", f"{total_completed:,} ({pct(total_completed):.1f}%)")

style_metric_cards(
    background_color="#0d47a1",
    border_left_color="#ff6b6b",
    box_shadow="3px 3px 10px rgba(0,0,0,0.2)"
)

# ---------------- Numeric Summary ----------------
st.subheader("🔢 Numeric Columns Summary")
num_cols = df_filtered.select_dtypes(include=["int64", "float64"]).columns.tolist()
if num_cols:
    num_summary = pd.DataFrame({
        "Column": num_cols,
        "Min": [df_filtered[c].min() for c in num_cols],
        "Max": [df_filtered[c].max() for c in num_cols],
        "Mean": [round(df_filtered[c].mean(), 2) for c in num_cols]
    })
    st.table(num_summary)
else:
    st.write("No numeric columns detected in filtered data.")

# ---------------- Column Descriptions ----------------
st.subheader("📖 Column Descriptions")
default_desc_cols = ["Chaser Name","Chaser Group","Created Time","Assigned date","Approval date","Completion Date","Upload Date","Client"]
available_desc_cols = [c for c in default_desc_cols if c in df_filtered.columns]
if available_desc_cols:
    selected_col = st.selectbox("Select a column to view description", available_desc_cols)
    # simple static descriptions (can be extended)
    column_descriptions = {
        "Chaser Name": "Mapped name of the chaser assigned to the lead.",
        "Chaser Group": "Group classification (e.g., Samy Chasers).",
        "Created Time": "When the lead was created.",
        "Assigned date": "When the lead was assigned.",
        "Approval date": "When the lead was approved.",
        "Completion Date": "When the lead was completed.",
        "Upload Date": "When documents were uploaded.",
        "Client": "Client associated with the lead."
    }
    st.info(column_descriptions.get(selected_col, "No description available."))

# ---------------- Distribution (Chaser Name) ----------------
if "Chaser Name" in df_filtered.columns:
    st.subheader("📊 Distribution of Chaser Name")
    ch_counts = df_filtered["Chaser Name"].value_counts().reset_index()
    ch_counts.columns = ["Chaser Name", "Count"]
    bar = alt.Chart(ch_counts).mark_bar().encode(
        x=alt.X("Chaser Name:N", sort="-y"),
        y="Count:Q",
        tooltip=["Chaser Name", "Count"]
    ).properties(height=300)
    st.altair_chart(bar, use_container_width=True)

# ---------------- Time-Series & Filters (Data Analysis) ----------------
st.markdown("---")
st.subheader("📈 Time Series & Filters (Data Analysis)")

# — time column selection for the time-series (and for insights subset)
date_candidates = [c for c in df_filtered.columns if ("date" in c.lower()) or pd.api.types.is_datetime64_any_dtype(df_filtered[c])]
# make unique preserving order
seen = set()
date_candidates = [x for x in date_candidates if not (x in seen or seen.add(x))]
if not date_candidates:
    st.warning("No date-like columns detected. At least one datetime column is required for time series analysis.")
else:
    time_col = st.selectbox("Select date column for time series analysis", date_candidates, index=date_candidates.index(CREATED) if CREATED in date_candidates else 0)

    # convert if not datetime
    if not pd.api.types.is_datetime64_any_dtype(df_filtered[time_col]):
        df_filtered[time_col] = pd.to_datetime(df_filtered[time_col], errors="coerce", dayfirst=True)

    # drop future dates for plotting
    today = pd.Timestamp.now().normalize()
    future_mask = df_filtered[time_col] > today
    if future_mask.any():
        st.warning(f"Detected {future_mask.sum()} rows with future `{time_col}`. Ignoring them in time-series.")
    df_ts = df_filtered.loc[~future_mask].copy()

    # search filters that affect df_ts (MCN & Chaser/Client free-text)
    st.markdown("🔍 Search (applies to all charts below)")
    mcns = st.text_input("Enter MCN (optional)").strip()
    search_term = st.text_input("Enter Chaser Name or Client (partial match allowed)").strip().lower()

    if mcns:
        df_ts = df_ts[df_ts["MCN"].astype(str).str.contains(mcns, case=False, na=False)]
    if search_term:
        df_ts = df_ts[
            df_ts.get("Chaser Name", "").astype(str).str.lower().str.contains(search_term, na=False) |
            df_ts.get("Client", "").astype(str).str.lower().str.contains(search_term, na=False)
        ]

    # aggregation level & period
    freq = st.radio("Aggregation level:", ["Daily", "Weekly", "Monthly"], horizontal=True)
    period_map = {"Daily":"D","Weekly":"W","Monthly":"M"}
    df_ts["Period"] = df_ts[time_col].dt.to_period(period_map[freq]).dt.to_timestamp()

    # group by option
    group_by = st.selectbox("Break down by:", ["None", "Client", "Chaser Name", "Chaser Group"])
    if group_by == "None":
        ts_data = df_ts.groupby("Period").size().reset_index(name="Lead Count")
    else:
        ts_data = df_ts.groupby(["Period", group_by]).size().reset_index(name="Lead Count")

    # plot historical time series
    if not ts_data.empty:
        st.markdown("### 📈 Historical Time Series")
        if group_by == "None":
            chart = alt.Chart(ts_data).mark_line(point=True, color="#007bff").encode(
                x="Period:T", y="Lead Count:Q", tooltip=["Period:T", "Lead Count"]
            ).properties(height=350)
        else:
            chart = alt.Chart(ts_data).mark_line(point=True).encode(
                x="Period:T", y="Lead Count:Q", color=group_by, tooltip=["Period:T", "Lead Count", group_by]
            ).properties(height=350)
        st.altair_chart(chart, use_container_width=True)

    # -------------- Insights Summary (based on selected time_col) --------------
    st.subheader("📝 Insights Summary")
    df_time = df_ts[df_ts[time_col].notna()].copy()
    total_time_leads = len(df_time)
    st.write(f"Based on **{time_col}** there are **{total_time_leads} leads** (after current filters).")

    if total_time_leads > 0:
        # per-row logical counts inside this subset
        assigned_count = df_time[ASSIGNED].notna().sum() if ASSIGNED else 0
        not_assigned_count = total_time_leads - assigned_count
        approval_count = df_time[APPROVAL].notna().sum() if APPROVAL else 0
        denial_count = df_time["Denial Date"].notna().sum() if "Denial Date" in df_time.columns else 0
        uploaded_count = df_time[UPLOAD].notna().sum() if UPLOAD else 0
        completed_count = df_time[COMPLETION].notna().sum() if COMPLETION else 0

        st.markdown(f"""
        - ✅ Total leads (with {time_col}): **{total_time_leads}**
        - 🧑‍💼 Assigned: **{assigned_count}**
        - 🚫 Not Assigned: **{not_assigned_count}**
        - ✔ Approved: **{approval_count}**
        - ❌ Denied: **{denial_count}**
        - 📤 Uploaded: **{uploaded_count}**
        - 📌 Completed: **{completed_count}**
        """)

        # ROW-LEVEL WARNINGS (per-row checks)
        # 1) Completed but no Assigned
        if COMPLETION and ASSIGNED:
            missing_assigned_after_completed = df_time[df_time[COMPLETION].notna() & df_time[ASSIGNED].isna()]
            if not missing_assigned_after_completed.empty:
                st.warning(f"⚠️ Found {len(missing_assigned_after_completed)} leads with **{time_col} present and Completion Date** but **no Assigned date**.")
                with st.expander("🔍 View leads with Completion but missing Assigned"):
                    cols_to_show = ["MCN","Client","Chaser Name", CREATED, ASSIGNED, APPROVAL, UPLOAD, COMPLETION]
                    cols_to_show = [c for c in cols_to_show if c in missing_assigned_after_completed.columns]
                    st.dataframe(missing_assigned_after_completed[cols_to_show].sort_values(COMPLETION, ascending=False), use_container_width=True)

        # 2) Completed but no Approval
        if COMPLETION and APPROVAL:
            missing_approval_after_completed = df_time[df_time[COMPLETION].notna() & df_time[APPROVAL].isna()]
            if not missing_approval_after_completed.empty:
                st.warning(f"⚠️ Found {len(missing_approval_after_completed)} leads with **Completion Date** but **no Approval date**.")
                with st.expander("🔍 View leads with Completion but missing Approval"):
                    cols_to_show = ["MCN","Client","Chaser Name", CREATED, ASSIGNED, APPROVAL, UPLOAD, COMPLETION]
                    cols_to_show = [c for c in cols_to_show if c in missing_approval_after_completed.columns]
                    st.dataframe(missing_approval_after_completed[cols_to_show].sort_values(COMPLETION, ascending=False), use_container_width=True)

        # 3) Upload present but no Completion
        if UPLOAD and COMPLETION:
            uploaded_no_completion = df_time[df_time[UPLOAD].notna() & df_time[COMPLETION].isna()]
            if not uploaded_no_completion.empty:
                st.warning(f"⚠️ Found {len(uploaded_no_completion)} leads with **Upload Date** but **no Completion Date**.")
                with st.expander("🔍 View leads uploaded but not completed"):
                    cols_to_show = ["MCN","Client","Chaser Name", CREATED, ASSIGNED, APPROVAL, UPLOAD, COMPLETION]
                    cols_to_show = [c for c in cols_to_show if c in uploaded_no_completion.columns]
                    st.dataframe(uploaded_no_completion[cols_to_show].sort_values(UPLOAD, ascending=False), use_container_width=True)

        # 4) Upload present but no Assigned
        if UPLOAD and ASSIGNED:
            uploaded_no_assigned = df_time[df_time[UPLOAD].notna() & df_time[ASSIGNED].isna()]
            if not uploaded_no_assigned.empty:
                st.warning(f"⚠️ Found {len(uploaded_no_assigned)} leads with **Upload Date** but **no Assigned date**.")
                with st.expander("🔍 View leads uploaded but missing assigned"):
                    cols_to_show = ["MCN","Client","Chaser Name", CREATED, ASSIGNED, APPROVAL, UPLOAD, COMPLETION]
                    cols_to_show = [c for c in cols_to_show if c in uploaded_no_assigned.columns]
                    st.dataframe(uploaded_no_assigned[cols_to_show].sort_values(UPLOAD, ascending=False), use_container_width=True)

        # 5) Upload present but no Approval
        if UPLOAD and APPROVAL:
            uploaded_no_approval = df_time[df_time[UPLOAD].notna() & df_time[APPROVAL].isna()]
            if not uploaded_no_approval.empty:
                st.warning(f"⚠️ Found {len(uploaded_no_approval)} leads with **Upload Date** but **no Approval date**.")
                with st.expander("🔍 View leads uploaded but missing approval"):
                    cols_to_show = ["MCN","Client","Chaser Name", CREATED, ASSIGNED, APPROVAL, UPLOAD, COMPLETION]
                    cols_to_show = [c for c in cols_to_show if c in uploaded_no_approval.columns]
                    st.dataframe(uploaded_no_approval[cols_to_show].sort_values(UPLOAD, ascending=False), use_container_width=True)

    else:
        st.write("No leads found for the selected date column/filters.")

    # Top performers (by leads) — dynamic with group_by
    if group_by in ["Chaser Name", "Client"]:
        st.subheader(f"🏆 Top {group_by}s by Leads")
        top_table = df_ts.groupby(group_by).size().reset_index(name="Lead Count").sort_values("Lead Count", ascending=False).head(10)
        st.table(top_table)

# ---------------- Lead Age Analysis ----------------
st.markdown("---")
st.subheader("⏳ Lead Age Analysis")

if CREATED and COMPLETION and CREATED in df_filtered.columns and COMPLETION in df_filtered.columns:
    df_lead_age = df_filtered.copy()
    df_lead_age["Lead Age (Days)"] = (df_lead_age[COMPLETION] - df_lead_age[CREATED]).dt.days

    # categorize into weeks (Not Completed if NaN)
    def categorize_weeks(days):
        if pd.isna(days):
            return "Not Completed"
        days = int(days)
        week = (days // 7) + 1
        if week <= 20:
            return f"Week {week}"
        return f"Week {week}"

    df_lead_age["Lead Age Category"] = df_lead_age["Lead Age (Days)"].apply(categorize_weeks)

    # Full lead age table
    st.markdown("### 📋 Full Lead Age Table")
    show_cols = [CREATED, COMPLETION, "Lead Age (Days)", "Lead Age Category", "Chaser Name", "Client", "MCN"]
    show_cols = [c for c in show_cols if c in df_lead_age.columns]
    st.dataframe(df_lead_age[show_cols].sort_values(CREATED, ascending=False), use_container_width=True)

    # Lead Age Distribution — ordered by week, Not Completed first
    st.markdown("### 📊 Lead Age Distribution")
    cats = df_lead_age["Lead Age Category"].dropna().unique().tolist()
    weeks = sorted([c for c in cats if c.startswith("Week")], key=lambda x: int(x.split()[1]) if len(x.split())>1 else 999)
    category_order = ["Not Completed"] + weeks
    age_summary = df_lead_age["Lead Age Category"].value_counts().reindex(category_order).fillna(0).reset_index()
    age_summary.columns = ["Lead Age Category", "Count"]
    st.table(age_summary)

    chart_age = alt.Chart(age_summary).mark_bar().encode(
        x=alt.X("Lead Age Category", sort=category_order),
        y="Count",
        tooltip=["Lead Age Category", "Count"]
    ).properties(height=300)
    st.altair_chart(chart_age, use_container_width=True)

    # Trend: median lead age over time (grouped by the same freq selected earlier)
    if CREATED in df_lead_age.columns:
        st.markdown("### 📈 Median Lead Age Over Time")
        df_age_time = df_lead_age.dropna(subset=["Lead Age (Days)"]).copy()
        # use same period_map as above (default to Monthly if not set)
        freq_for_trend = period_map.get(freq, "M")
        try:
            df_age_time["Period"] = df_age_time[CREATED].dt.to_period(period_map[freq]).dt.to_timestamp()
            trend = df_age_time.groupby("Period")["Lead Age (Days)"].median().reset_index()
            trend.columns = ["Period", "Median Lead Age (Days)"]
            line = alt.Chart(trend).mark_line(point=True).encode(x="Period:T", y="Median Lead Age (Days):Q", tooltip=["Period:T","Median Lead Age (Days)"]).properties(height=300)
            st.altair_chart(line, use_container_width=True)
        except Exception:
            st.write("Could not compute median lead age trend (check date coverage).")

    # Average & Median lead age per Chaser / Client plus color highlights for fastest/slowest
    st.markdown("### 📊 Average & Median Lead Age by Chaser / Client")
    st.info(
        "- 📈 If **Median is low** but **Average is high** → Most leads are closed quickly, but a few are very delayed.\n"
        "- ⏳ If **Both are high** → Team generally takes longer to close leads.\n"
        "- 🚀 If **Both are low** → Good performance: consistently fast closes.\n\n"
        "🟢 Green highlights fastest (lowest median). 🔴 Red highlights slowest (highest median)."
    )

    col1, col2 = st.columns(2)
    with col1:
        if "Chaser Name" in df_lead_age.columns:
            avg_chaser = df_lead_age.groupby("Chaser Name")["Lead Age (Days)"].agg(["mean","median"]).reset_index()
            avg_chaser.columns = ["Chaser Name", "Average Age (Days)", "Median Age (Days)"]
            avg_chaser = avg_chaser.sort_values("Median Age (Days)")
            # highlight using Styler
            def highlight_min_max(s, col):
                is_min = s == avg_chaser[col].min()
                is_max = s == avg_chaser[col].max()
                return ["background-color: #d4f7df" if v else "background-color: #fddede" if is_max.iat[i] else "" for i, v in enumerate(is_min)]
            # safer: create a Styler for median column only
            sty = avg_chaser.style.apply(lambda col: ["background-color: #d4f7df" if v==avg_chaser["Median Age (Days)"].min() else ("background-color: #fddede" if v==avg_chaser["Median Age (Days)"].max() else "") for v in col], subset=["Median Age (Days)"])
            st.dataframe(sty, use_container_width=True)
            # chart
            chart_chaser = alt.Chart(avg_chaser).mark_bar().encode(
                x=alt.X("Chaser Name:N", sort="-y"),
                y="Median Age (Days):Q",
                tooltip=["Chaser Name","Average Age (Days)","Median Age (Days)"]
            ).properties(height=300)
            st.altair_chart(chart_chaser, use_container_width=True)

            st.markdown("### 📦 Lead Age Spread by Chaser")
            box_chart_chaser = alt.Chart(df_lead_age.dropna(subset=["Lead Age (Days)"])).mark_boxplot(extent="min-max").encode(
                x="Chaser Name:N",
                y="Lead Age (Days):Q",
                color="Chaser Name:N",
                tooltip=["Chaser Name","Lead Age (Days)"]
            ).properties(height=400)
            st.altair_chart(box_chart_chaser, use_container_width=True)

    with col2:
        if "Client" in df_lead_age.columns:
            avg_client = df_lead_age.groupby("Client")["Lead Age (Days)"].agg(["mean","median"]).reset_index()
            avg_client.columns = ["Client", "Average Age (Days)", "Median Age (Days)"]
            avg_client = avg_client.sort_values("Median Age (Days)")

            sty_c = avg_client.style.apply(lambda col: ["background-color: #d4f7df" if v==avg_client["Median Age (Days)"].min() else ("background-color: #fddede" if v==avg_client["Median Age (Days)"].max() else "") for v in col], subset=["Median Age (Days)"])
            st.dataframe(sty_c, use_container_width=True)

            chart_client = alt.Chart(avg_client).mark_bar().encode(
                x=alt.X("Client:N", sort="-y"),
                y="Median Age (Days):Q",
                tooltip=["Client","Average Age (Days)","Median Age (Days)"]
            ).properties(height=300)
            st.altair_chart(chart_client, use_container_width=True)

            st.markdown("### 📦 Lead Age Spread by Client")
            box_chart_client = alt.Chart(df_lead_age.dropna(subset=["Lead Age (Days)"])).mark_boxplot(extent="min-max").encode(
                x="Client:N",
                y="Lead Age (Days):Q",
                color="Client:N",
                tooltip=["Client","Lead Age (Days)"]
            ).properties(height=400)
            st.altair_chart(box_chart_client, use_container_width=True)

else:
    st.info("Created Time and Completion Date columns are required for Lead Age analysis. Please ensure these columns exist and are parsed as datetime.")

# ---------------- Top Chasers by Leads ----------------
st.markdown("---")
st.subheader("🏆 Top Chaser Names by Leads (current filters)")
if "Chaser Name" in df_filtered.columns:
    top = df_filtered["Chaser Name"].value_counts().reset_index().rename(columns={"index":"Chaser Name","Chaser Name":"Lead Count"})
    st.table(top.head(10))
else:
    st.write("No Chaser Name column available.")

# ---------------- DOWNLOAD ----------------
st.download_button(
    label="💾 Download Filtered CSV",
    data=df_filtered.to_csv(index=False).encode("utf-8"),
    file_name="Dr_Chase_Leads_Filtered.csv",
    mime="text/csv"
)
