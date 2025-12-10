import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
# ===================== CONFIG =====================
DB_PATH = "business.db"
st.set_page_config(
    page_title="Business Expense Analyzer",
    layout="wide",
    page_icon="📊"
)
st.title("📊 Business Expense Analyzer")
st.caption(
    "SQL-backed dashboard for analyzing real income and expenses "
    "from my small business (Merriness Fortune)."
)
# ===================== DB HELPERS =====================
def get_connection():
    """Create a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)
def ensure_columns(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """
    Make sure the DataFrame has all columns in `columns`.
    If any are missing, add them with empty/NaN values.
    Then return DataFrame with columns ordered as in `columns`.
    """
    for col in columns:
        if col not in df.columns:
            df[col] = None
    return df[columns]
def init_db():
    """
    Create the database and tables if they don't exist.
    If tables are empty, seed them from the CSV files in /data.
    """
    conn = get_connection()
    cur = conn.cursor()
    # ----- Create tables -----
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            category TEXT,
            description TEXT,
            amount REAL NOT NULL
        )
        """
    )
    # NOTE: includes category now to match CSV
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            source TEXT,
            category TEXT,
            description TEXT,
            amount REAL NOT NULL
        )
        """
    )
    # ----- Check if tables have data -----
    cur.execute("SELECT COUNT(*) FROM expenses")
    expenses_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM income")
    income_count = cur.fetchone()[0]
    # ----- Seed expenses from CSV if empty -----
    if expenses_count == 0 and os.path.exists("data/expenses.csv"):
        exp_df = pd.read_csv("data/expenses.csv")
        exp_df = ensure_columns(
            exp_df, ["date", "category", "description", "amount"]
        )
        exp_df.to_sql("expenses", conn, if_exists="append", index=False)
    # ----- Seed income from CSV if empty -----
    if income_count == 0 and os.path.exists("data/income.csv"):
        inc_df = pd.read_csv("data/income.csv")
        # support both with or without category/source in the CSV
        inc_df = ensure_columns(
            inc_df, ["date", "source", "category", "description", "amount"]
        )
        inc_df.to_sql("income", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()
@st.cache_data
def load_table(table_name: str) -> pd.DataFrame:
    """Load a table from SQLite into a pandas DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df
# ===================== INITIALIZE & LOAD =====================
init_db()
expenses = load_table("expenses")
income = load_table("income")
if expenses.empty and income.empty:
    st.error(
        "No data available. Check your SQLite database or the CSV files "
        "in the /data folder."
    )
    st.stop()
# drop id column for display
if "id" in expenses.columns:
    expenses_display = expenses.drop(columns=["id"])
else:
    expenses_display = expenses.copy()
if "id" in income.columns:
    income_display = income.drop(columns=["id"])
else:
    income_display = income.copy()
# ===================== SIDEBAR FILTERS =====================
st.sidebar.header("Filters")
dates = []
if not expenses.empty:
    dates.append(expenses["date"].min())
    dates.append(expenses["date"].max())
if not income.empty:
    dates.append(income["date"].min())
    dates.append(income["date"].max())
min_date = min(dates)
max_date = max(dates)
start_date = st.sidebar.date_input("Start Date", min_date)
end_date = st.sidebar.date_input("End Date", max_date)
if start_date > end_date:
    st.sidebar.error("Start date must be before end date.")
# filter by date
expenses_filtered = expenses[
    (expenses["date"] >= pd.to_datetime(start_date))
    & (expenses["date"] <= pd.to_datetime(end_date))
]
income_filtered = income[
    (income["date"] >= pd.to_datetime(start_date))
    & (income["date"] <= pd.to_datetime(end_date))
]
# ===================== METRICS =====================
total_expenses = float(expenses_filtered["amount"].sum()) if not expenses_filtered.empty else 0.0
total_income = float(income_filtered["amount"].sum()) if not income_filtered.empty else 0.0
profit = total_income - total_expenses
col1, col2, col3 = st.columns(3)
col1.metric("Total Income", f"${total_income:,.2f}")
col2.metric("Total Expenses", f"${total_expenses:,.2f}")
col3.metric("Profit", f"${profit:,.2f}", delta=f"{profit:,.2f}")
st.markdown("---")
# ===================== EXPENSE BREAKDOWN =====================
if (
    not expenses_filtered.empty
    and "category" in expenses_filtered.columns
):
    st.subheader("💸 Expense Breakdown by Category")
    category_totals = expenses_filtered.groupby("category")["amount"].sum()
    left, right = st.columns([1, 1.2])
    with left:
        st.dataframe(category_totals.rename("Total Amount"))
    with right:
        fig, ax = plt.subplots()
        ax.pie(category_totals, labels=category_totals.index, autopct="%1.1f%%")
        ax.set_title("Expenses by Category")
        st.pyplot(fig)
else:
    st.info("No categorized expenses available for the selected date range.")
st.markdown("---")
# ===================== INCOME OVER TIME =====================
if not income_filtered.empty and "date" in income_filtered.columns:
    st.subheader("📈 Income Over Time")
    income_time = income_filtered.set_index("date")["amount"].sort_index()
    st.line_chart(income_time)
else:
    st.info("No income records available for the selected date range.")
st.markdown("---")

# ===================== RAW DATA =====================
st.subheader("📂 Raw Data (from SQLite database)")
tab1, tab2 = st.tabs(["Expenses", "Income"])
with tab1:
    st.write("Filtered Expenses Data")
    df_exp = expenses_filtered.drop(columns=["id"]) if "id" in expenses_filtered.columns else expenses_filtered
    st.dataframe(df_exp)
with tab2:
    st.write("Filtered Income Data")
    df_inc = income_filtered.drop(columns=["id"]) if "id" in income_filtered.columns else income_filtered
    st.dataframe(df_inc)
