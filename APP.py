import streamlit as st
import pandas as pd
import altair as alt
import re
from streamlit_option_menu import option_menu
from streamlit_extras.metric_cards import style_metric_cards

# ================== PAGE CONFIG ==================
st.set_page_config(
    page_title="DR Chase Leads Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

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


# ================== SYNONYMS ==================
syn = {
    "created_time": ["created_time", "created time", "creation time", "created", "lead created", "request created"],
    "assign_date": ["assign_date", "assigned date", "assign time", "assigned time", "assigned on"],
    "approval_date": ["approval_date", "approved date", "approval time", "approved on"],
    "completion_date": ["completion_date", "completed date", "completion time", "closed date", "completed on"],
    "uploaded_date": ["uploaded_date", "upload date", "uploaded date", "uploaded on"],
    "assigned_to_chase": ["assigned to chase", "assigned_to_chase", "assigned to", "assigned user (chase)", "assigned chaser"],
}

cols_map = {
    "created_time": find_col(df.columns, syn["created_time"]),
    "assign_date": find_col(df.columns, syn["assign_date"]),
    "approval_date": find_col(df.columns, syn["approval_date"]),
    "completion_date": find_col(df.columns, syn["completion_date"]),
    "uploaded_date": find_col(df.columns, syn["uploaded_date"]),
    "assigned_to_chase": find_col(df.columns, syn["assigned_to_chase"]),
}

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
        # Convert to datetime (day first format)
        df_cleaned[col] = pd.to_datetime(df_cleaned[col], errors="coerce", dayfirst=True)

        # Create additional split columns for better readability
        df_cleaned[col + " (Date)"] = df_cleaned[col].dt.date
        if df_cleaned[col].dt.time.notna().any():  # only if time part exists
            df_cleaned[col + " (Time)"] = df_cleaned[col].dt.time

# ================== NAME MAP ==================
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

assigned_col = cols_map["assigned_to_chase"]
if assigned_col and assigned_col in df_cleaned.columns:
    df_cleaned["Chaser Name"] = (
        df_cleaned[assigned_col]
        .astype(str).str.strip().str.lower()
        .map(name_map)
        .fillna(df_cleaned[assigned_col])
    )

    samy_chasers = {
        "Emma Wilson", "Scarlett Mitchell", "Lucas Diago", "Mia Alaxendar",
        "Candy Johns", "Sandra Sebastian", "Alia Scott",
        "Ivy Brooks", "Heather Robertson", "Samy Youssef",
        "Sarah Adams", "Timothy Williams"
    }
    df_cleaned["Chaser Group"] = df_cleaned["Chaser Name"].apply(
        lambda n: "Samy Chasers" if n in samy_chasers else "Andrew Chasers"
    )

# Convert dates
date_actual_cols = [cols_map[k] for k in ["created_time","assign_date","approval_date","completion_date","uploaded_date"] if cols_map[k]]
for c in date_actual_cols:
    df_cleaned[c] = pd.to_datetime(df_cleaned[c], errors="coerce")

# ================== COLUMN DESCRIPTIONS ==================
column_descriptions = {
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

df_filtered = df_cleaned.copy()
#switcher

# ================== SIDEBAR FILTERS ==================
st.sidebar.header("🎛 Basic Filters")

with st.sidebar.expander("👥 Client", expanded=False):
    all_clients = df_cleaned["Client"].dropna().unique().tolist()
    select_all_clients = st.checkbox("Select All Clients", value=True, key="all_clients")
    if select_all_clients:
        Client = st.multiselect("Select Client", options=all_clients, default=all_clients)
    else:
        Client = st.multiselect("Select Client", options=all_clients)


with st.sidebar.expander("🧑‍💼 Chaser Name", expanded=False):
    all_Chaser_Name-df_cleaned["Chaser Name"].dropna().unique().tolist()
    select_all_Chaser_Name = st.checkbox("Select All Chaser Name ", value=True, key="all_Chaser_Name")
    if select_all_Chaser_Name:
        Chaser Name = st.multiselect("Select Chaser Name"", options=all_Chaser_Name, default=all_Chaser_Name)    
    else:
        Chaser Name  = st.multiselect("Select  Chaser Name ", options=all_Chaser_Name)
             


with st.sidebar.expander("👨‍👩‍👧‍👦 Chaser Group", expanded=False):
    Chaser_Group = st.multiselect(
        "Select Chaser Group",
        options=df_cleaned["Chaser Group"].unique(),
        default=df_cleaned["Chaser Group"].unique(),
    )

with st.sidebar.expander("👥 Chasing Disposition", expanded=False):
    Chasing_Disposition = st.multiselect(
        "Select Chasing Disposition",
        options=df_cleaned["Chasing Disposition"].unique(),
        default=df_cleaned["Chasing Disposition"].unique(),
    )
    
with st.sidebar.expander("📅 Date Range", expanded=False):
    min_date = pd.to_datetime(df_cleaned[date_columns].min().min()).date()
    max_date = pd.to_datetime(df_cleaned[date_columns].max().max()).date()

    date_range = st.date_input(
        "Select date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    

# --- Apply filters using .query() ---
df_filtered = df_cleaned.query(
    "Client in @Client and `Chaser Name` in @Chaser_Name and `Chaser Group` in @Chaser_Group and `Chasing Disposition` in @Chasing_Disposition"
)

# Apply date filter (on Created Time by default, but you can change to Completion Date, etc.)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    if "Created Time" in df_filtered.columns:
        df_filtered = df_filtered[
            (df_filtered["Created Time"].dt.date >= start_date)
            & (df_filtered["Created Time"].dt.date <= end_date)
        ]

# ================== MAIN DASHBOARD ==================
if selected == "Dataset Overview":
    st.title("📊 DR Chase Leads Dashboard")
    st.info("Use the filters below to explore the dataset.")

    # --- Column filter ---
# --- Function for tabular view ---
    def table(df_filtered):
        with st.expander("📊 Tabular"):
            shwdata = st.multiselect(
                "Filter Columns:",
                df_filtered.columns,
                default=["Chaser Name","Chaser Group","Date of Sale (Date)","Created Time (Date)","Assigned date (Date)",
                         "Approval date (Date)","Denial Date (Date)","Completion Date (Date)",
                         "Upload Date (Date)","Client","Chasing Disposition","Insurance","Type Of Sale","Products"]  # show first 6 columns by default
            )
            st.dataframe(df_filtered[shwdata], use_container_width=True)

    # --- Inside your DR Chase Leads app ---
    if selected == "Dataset Overview":
        st.subheader("🔍 Data Inspection")
        st.markdown(f""" The dataset contains **{len(df_filtered)} rows**
                        and **{len(df_filtered.columns)} columns**.
                    """)
        # Show tabular selector
        table(df_filtered)

                
    # --- Dataset Summary / Description ---
# --- Dataset Summary / KPIs ---
    st.subheader("📑 Dataset Summary")

    total_leads = len(df_filtered)

    # Use dates to calculate counts
    total_completed = df_filtered["Completion Date"].notna().sum() if "Completion Date" in df_filtered.columns else 0
    total_assigned = df_filtered["Assigned date"].notna().sum() if "Assigned date" in df_filtered.columns else 0
    total_uploaded = df_filtered["Upload Date"].notna().sum() if "Upload Date" in df_filtered.columns else 0
    total_approval = df_filtered["Approval date"].notna().sum() if "Approval date" in df_filtered.columns else 0
    total_denial = df_filtered["Denial Date"].notna().sum() if "Denial Date" in df_filtered.columns else 0

    # Derived metrics
    total_not_assigned = total_leads - total_assigned

    # Percentages
    pct_completed = (total_completed / total_leads * 100) if total_leads > 0 else 0
    pct_assigned = (total_assigned / total_leads * 100) if total_leads > 0 else 0
    pct_not_assigned = (total_not_assigned / total_leads * 100) if total_leads > 0 else 0
    pct_uploaded = (total_uploaded / total_leads * 100) if total_leads > 0 else 0
    pct_approval = (total_approval / total_leads * 100) if total_leads > 0 else 0
    pct_denial = (total_denial / total_leads * 100) if total_leads > 0 else 0

    # --- Display KPIs in styled cards ---
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("📊 Total Leads", f"{total_leads:,}")
        st.metric("✅ Completed", f"{total_completed:,} ({pct_completed:.1f}%)")

    with col2:
        st.metric("🧑‍💼 Assigned", f"{total_assigned:,} ({pct_assigned:.1f}%)")
        st.metric("📤 Uploaded", f"{total_uploaded:,} ({pct_uploaded:.1f}%)")

    with col3:
        st.metric("🚫 Not Assigned", f"{total_not_assigned:,} ({pct_not_assigned:.1f}%)")
        st.metric("✔ Approvals / ❌ Denials", f"{total_approval:,} ({pct_approval:.1f}%) / {total_denial:,} ({pct_denial:.1f}%)")

    # --- Style metric cards ---
    style_metric_cards(
        background_color="#121270",  # Dark blue background
        border_left_color="#f20045", # Pink/red accent bar
        box_shadow="3px 3px 10px rgba(0,0,0,0.3)"  # soft shadow
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

        # ✅ Restrict to specific columns
    description_columns = [
        "Chaser Name", "Chaser Group", "Date of Sale (Date)", "Created Time (Date)",
        "Assigned date (Date)", "Approval date (Date)", "Denial Date (Date)",
        "Completion Date (Date)", "Upload Date (Date)", "Client",
        "Chasing Disposition", "Insurance", "Type Of Sale", "Products","Days Spent As Pending QA"
    ]

    # Keep only the ones that exist in df_cleaned
    valid_desc_cols = [c for c in description_columns if c in df_cleaned.columns]

    selected_col = st.selectbox(
        "Select a column to view description",
        valid_desc_cols
    )

    # Provide actual descriptions
    column_descriptions = {
        "Chaser Name": " chaser Name assigned to the lead.",
        "Chaser Group": "Group classification (Samy Chasers or Andrew Chasers).",
        "Date of Sale (Date)": "The confirmed sale date of the lead.",
        "Created Time (Date)": "When the lead was created.",
        "Assigned date (Date)": "When the lead was assigned to a chaser.",
        "Approval date (Date)": "When the lead was approved.",
        "Denial Date (Date)": "When the lead was denied.",
        "Completion Date (Date)": "When the lead was completed.",
        "Upload Date (Date)": "When documents were uploaded.",
        "Client": "Client associated with the lead (e.g., PPO-Braces chasing).",
        "Chasing Disposition": "Final chasing result (e.g., Dead Lead, Successful Chase).",
        "Insurance": "Insurance provider associated with the patient.",
        "Type Of Sale": "Category of the lead (e.g., Normal Chase, Red Flag).",
        "Products": "Products linked to the lead (e.g., braces, medical items).",
        "Days Spent As Pending QA": "Number of days lead stayed in Pending QA status."
    }

    desc = column_descriptions.get(selected_col, "No description available for this column.")
    st.info(f"**{selected_col}**: {desc}")

    # --- Force date conversion for known date columns ---
    date_columns = [
        "Date of Sale (Date)", "Created Time (Date)", "Assigned date (Date)",
        "Approval date (Date)", "Denial Date (Date)",
        "Completion Date (Date)", "Upload Date (Date)"
    ]

    for col in date_columns:
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
                x=alt.X(selected_col, bin=alt.Bin(maxbins=30)),  # bins for histogram
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




elif selected == "Data Analysis":
    st.title("📊 DR Chase Leads Dashboard - Data Analysis")
    st.info("Advanced analysis: time series with search filter, insights, and lead age analysis.")

    # --- Candidate date columns ---
    date_candidates = [
        c for c in df_filtered.columns
        if ("date" in c.lower()) or pd.api.types.is_datetime64_any_dtype(df_filtered[c])
    ]
    if not date_candidates:
        st.warning("No date-like columns detected in the filtered dataframe.")
    else:
        time_col = st.selectbox("Select date column for time series analysis", date_candidates)

        # Convert column
        df_filtered[time_col] = pd.to_datetime(df_filtered[time_col], errors="coerce", dayfirst=True)

        today = pd.Timestamp.now().normalize()
        future_mask = df_filtered[time_col] > today
        if future_mask.any():
            st.warning(f"⚠️ Detected {future_mask.sum()} rows with future {time_col} values.")
            if st.checkbox("Show rows with future dates"):
                st.dataframe(df_filtered.loc[future_mask])

        df_ts = df_filtered.loc[~future_mask].copy()

        # --- Search filters ---
        st.subheader("🔍 Search Filter")

        # 1) Search by MCN
        mcn_search = st.text_input("Enter MCN (optional)").strip()
        if mcn_search:
            df_ts = df_ts[df_ts["MCN"].astype(str).str.contains(mcn_search, case=False, na=False)]

        # 2) Search by Chaser Name / Client
        search_term = st.text_input("Enter Chaser Name or Client (partial match allowed)").strip().lower()
        if search_term:
            df_ts = df_ts[
                df_ts["Chaser Name"].str.lower().str.contains(search_term, na=False)
                | df_ts["Client"].str.lower().str.contains(search_term, na=False)
            ]

        # --- Aggregation frequency ---
        freq = st.radio("Aggregation level:", ["Daily", "Weekly", "Monthly"], horizontal=True)
        period_map = {"Daily": "D", "Weekly": "W", "Monthly": "M"}
        df_ts["Period"] = df_ts[time_col].dt.to_period(period_map[freq]).dt.to_timestamp()

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

            # 📝 Insights Summary
            st.subheader("📝 Insights Summary")

            first_val, last_val = ts_data["Lead Count"].iloc[0], ts_data["Lead Count"].iloc[-1]
            trend = "increased 📈" if last_val > first_val else "decreased 📉"
            st.write(f"Overall, leads {trend} from **{first_val}** at the start to **{last_val}** at the end.")

            peak_row = ts_data.loc[ts_data["Lead Count"].idxmax()]
            low_row = ts_data.loc[ts_data["Lead Count"].idxmin()]
            st.write(f"Highest leads: **{peak_row['Lead Count']}** on **{peak_row['Period'].date()}**")
            st.write(f"Lowest leads: **{low_row['Lead Count']}** on **{low_row['Period'].date()}**")

            if group_by != "None":
                contrib = ts_data.groupby(group_by)["Lead Count"].sum().reset_index()
                top_group = contrib.sort_values("Lead Count", ascending=False).iloc[0]
                share = top_group["Lead Count"] / contrib["Lead Count"].sum() * 100
                st.write(f"**{top_group[group_by]}** contributed the most overall "
                         f"with **{top_group['Lead Count']} leads** (~{share:.1f}%).")

            # 🏆 Top performers
            if group_by in ["Chaser Name", "Client"]:
                st.subheader(f"🏆 Top {group_by}s by Leads")
                top_table = ts_data.groupby(group_by)["Lead Count"].sum().reset_index()
                top_table = top_table.sort_values("Lead Count", ascending=False).head(5)
                st.table(top_table)

        # ================== Lead Age Analysis ==================
        st.subheader("⏳ Lead Age Analysis")

        if "Created Time" in df_ts.columns and "Completion Date" in df_ts.columns:
            df_lead_age = df_ts.copy()
            df_lead_age["Lead Age (Days)"] = (
                (df_lead_age["Completion Date"] - df_lead_age["Created Time"]).dt.days
            )

            # Categorize into weeks
            def categorize_weeks(days):
                if pd.isna(days):
                    return "Not Completed"
                elif days <= 7:
                    return "Week 1"
                elif days <= 14:
                    return "Week 2"
                elif days <= 21:
                    return "Week 3"
                elif days <= 28:
                    return "Week 4"
                elif days <= 35:
                    return "Week 5"
                elif days <= 42:
                    return "Week 6"
                elif days <= 49:
                    return "Week 7"
                elif days <= 56:
                    return "Week 8"
                elif days <= 63:
                    return "Week 9"
                elif days <= 70:
                    return "Week 10"
                elif days <= 77:
                    return "Week 11"
                elif days <= 84:
                    return "Week 12"
                elif days <= 91:
                    return "Week 13"
                elif days <= 98:
                    return "Week 14"
                elif days <= 105:
                    return "Week 15"
                elif days <= 112:
                    return "Week 16"
                else:
                    return "Week 17"

            df_lead_age["Lead Age Category"] = df_lead_age["Lead Age (Days)"].apply(categorize_weeks)


             # 📋 Full lead age table
            st.markdown("### 📋 Full Lead Age Table")
            st.dataframe(
                df_lead_age[["Created Time", "Completion Date", "Lead Age (Days)", "Lead Age Category", "Chaser Name", "Client", "MCN"]],
                use_container_width=True
            )
            
            # 📊 Lead Age Distribution
            st.markdown("### 📊 Lead Age Distribution")

            # Not Completed first
            categories = df_lead_age["Lead Age Category"].dropna().unique()
            weeks = sorted([c for c in categories if c.startswith("Week")], key=lambda x: int(x.split()[1]))
            category_order = ["Not Completed"] + weeks  
            
            color_scale = alt.Scale(
            domain=["Not Completed"] + weeks,
            range=["#C99927"] + ["#16e261"] * len(weeks)
             )

            age_summary = (
                df_lead_age["Lead Age Category"]
                .value_counts()
                .reindex(category_order)   
                .reset_index()
            )
            age_summary.columns = ["Lead Age Category", "Count"]

            st.table(age_summary)

            chart_age = (
                alt.Chart(age_summary)
                .mark_bar()
                .encode(
                    x=alt.X("Lead Age Category", sort=category_order),
                    y="Count",
                    color=alt.Color("Lead Age Category", scale=color_scale, legend=None),
                    tooltip=["Lead Age Category", "Count"]
                )
            )
            st.altair_chart(chart_age, use_container_width=True)



            
            # 📊 Average + Median lead age per Chaser / Client
            st.markdown("### 📊 Average & Median Lead Age by Chaser / Client")
            # 📖 Explanation with Emojis
            st.info("""
            
            - 📈 If **Median is low** but **Average is high** → Most leads are closed quickly, but a few leads are extremely delayed.  
            - ⏳ If **Both are high** → The team generally takes **longer** to close leads.  
            - 🚀 If **Both are low** → Excellent performance; leads are closed **consistently fast**.
            ---
            - 🟢 Who usually closes leads **faster** (lower Median).  
            - 🔴 Who sometimes delays leads too much (**high Average compared to Median**).
            """)
            col1, col2 = st.columns(2)

            with col1:
                if "Chaser Name" in df_lead_age.columns:
                    avg_chaser = df_lead_age.groupby("Chaser Name")["Lead Age (Days)"].agg(["mean", "median"]).reset_index()
                    avg_chaser.columns = ["Chaser Name", "Average Age (Days)", "Median Age (Days)"]
                    avg_chaser = avg_chaser.sort_values("Median Age (Days)")

                    # Color formatting
                    def highlight_chaser(val, colname):
                        if pd.isna(val):
                            return ""
                        if val == avg_chaser[colname].min():
                            return "background-color: #67C090"  # green
                        elif val == avg_chaser[colname].max():
                            return "background-color: #E62727"  # red
                        return ""

                    st.dataframe(
                        avg_chaser.style.applymap(lambda v: highlight_chaser(v, "Median Age (Days)"), subset=["Median Age (Days)"])
                    )

                    # Chart
                    chart_chaser = (
                        alt.Chart(avg_chaser)
                        .mark_bar()
                        .encode(
                            x="Chaser Name",
                            y="Median Age (Days)",
                            tooltip=["Chaser Name", "Average Age (Days)", "Median Age (Days)"]
                        )
                    )
                    st.altair_chart(chart_chaser, use_container_width=True)

                            # 📦 Boxplot of Lead Age by Chaser
                    st.markdown("### 📦 Lead Age Spread by Chaser")
                    box_chart_chaser = (
                        alt.Chart(df_lead_age.dropna(subset=["Lead Age (Days)"]))
                        .mark_boxplot(extent="min-max")
                        .encode(
                            x="Chaser Name",
                            y="Lead Age (Days):Q",
                            color="Chaser Name",
                            tooltip=["Chaser Name", "Lead Age (Days)"]
                        )
                        .properties(height=400)
                    )
                    st.altair_chart(box_chart_chaser, use_container_width=True)

    
            
            with col2:
                if "Client" in df_lead_age.columns:
                    avg_client = df_lead_age.groupby("Client")["Lead Age (Days)"].agg(["mean", "median"]).reset_index()
                    avg_client.columns = ["Client", "Average Age (Days)", "Median Age (Days)"]
                    avg_client = avg_client.sort_values("Median Age (Days)")

                    # Color formatting
                    def highlight_client(val, colname):
                        if pd.isna(val):
                            return ""
                        if val == avg_client[colname].min():
                            return "background-color: #67C090"  # green
                        elif val == avg_client[colname].max():
                            return "background-color: #E62727"  # red
                        return ""

                    st.dataframe(
                        avg_client.style.applymap(lambda v: highlight_client(v, "Median Age (Days)"), subset=["Median Age (Days)"])
                    )

                    # Chart
                    chart_client = (
                        alt.Chart(avg_client)
                        .mark_bar()
                        .encode(
                            x="Client",
                            y="Median Age (Days)",
                            tooltip=["Client", "Average Age (Days)", "Median Age (Days)"]
                        )
                    )
                    st.altair_chart(chart_client, use_container_width=True)
                    
                    
                     # 📦 Boxplot of Lead Age by Client
                    st.markdown("### 📦 Lead Age Spread by Client")
                    box_chart_client = (
                        alt.Chart(df_lead_age.dropna(subset=["Lead Age (Days)"]))
                        .mark_boxplot(extent="min-max")
                        .encode(
                            x="Client",
                            y="Lead Age (Days):Q",
                            color="Client",
                            tooltip=["Client", "Lead Age (Days)"]
                        )
                        .properties(height=400)
                    )
                    st.altair_chart(box_chart_client, use_container_width=True)

        else:
            st.info("Created Time and Completion Date columns are required for lead age analysis.")
            
                               



# ================== DOWNLOAD ==================
st.download_button(
    label="💾 Download Filtered CSV",
    data=df_cleaned.to_csv(index=False).encode("utf-8"),
    file_name="Dr_Chase_Leads_Filtered.csv",
    mime="text/csv"
)











