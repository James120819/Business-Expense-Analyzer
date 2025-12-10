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
    # income table supports category as well
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
def refresh_data():
    """Clear cache and reload tables."""
    load_table.clear()  # clears streamlit cache for this function
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
# drop id column for display tables (not for internal use)
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
st.markdown("---")
# ===================== MANAGE DATA (CRUD) =====================
st.subheader("🛠 Manage Data")
manage_tab_exp, manage_tab_inc = st.tabs(["Manage Expenses", "Manage Income"])
# ---------- MANAGE EXPENSES ----------
with manage_tab_exp:
    st.markdown("### ➕ Add New Expense")
    with st.form("add_expense_form"):
        exp_date = st.date_input("Date")
        exp_category = st.text_input("Category")
        exp_desc = st.text_input("Description")
        exp_amount = st.number_input("Amount", min_value=0.0, step=1.0)
        submitted = st.form_submit_button("Add Expense")
        if submitted:
            conn = get_connection()
            conn.execute(
                "INSERT INTO expenses (date, category, description, amount) VALUES (?, ?, ?, ?)",
                (str(exp_date), exp_category or None, exp_desc or None, float(exp_amount)),
            )
            conn.commit()
            conn.close()
            refresh_data()
            st.success("Expense added successfully.")
            st.experimental_rerun()
    st.markdown("### ✏️ Edit or 🗑 Delete Expense")
    if not expenses.empty and "id" in expenses.columns:
        # Build label map for the selectbox
        label_map = {}
        for _, row in expenses.iterrows():
            date_str = row["date"].date().isoformat() if isinstance(row["date"], pd.Timestamp) else str(row["date"])
            category_str = row.get("category") or "Uncategorized"
            amount_val = float(row["amount"])
            label_map[row["id"]] = f"{row['id']} | {date_str} | {category_str} | ${amount_val:,.2f}"
        selected_expense_id = st.selectbox(
            "Select an expense to edit or delete",
            options=list(label_map.keys()),
            format_func=lambda x: label_map.get(x, str(x))
        )
        selected_row = expenses[expenses["id"] == selected_expense_id].iloc[0]
        with st.form("edit_expense_form"):
            current_date = selected_row["date"].date() if isinstance(selected_row["date"], pd.Timestamp) else selected_row["date"]
            new_date = st.date_input("Edit Date", value=current_date)
            new_category = st.text_input("Edit Category", value=selected_row.get("category") or "")
            new_desc = st.text_input("Edit Description", value=selected_row.get("description") or "")
            new_amount = st.number_input("Edit Amount", min_value=0.0, value=float(selected_row["amount"]), step=1.0)
            save_changes = st.form_submit_button("Save Changes")
            if save_changes:
                conn = get_connection()
                conn.execute(
                    "UPDATE expenses SET date=?, category=?, description=?, amount=? WHERE id=?",
                    (str(new_date), new_category or None, new_desc or None, float(new_amount), int(selected_expense_id))
                )
                conn.commit()
                conn.close()
                refresh_data()
                st.success("Expense updated successfully.")
                st.experimental_rerun()
        if st.button("🗑 Delete Selected Expense"):
            conn = get_connection()
            conn.execute("DELETE FROM expenses WHERE id=?", (int(selected_expense_id),))
            conn.commit()
            conn.close()
            refresh_data()
            st.warning("Expense deleted.")
            st.experimental_rerun()
    else:
        st.info("No expenses available to manage.")
# ---------- MANAGE INCOME ----------
with manage_tab_inc:
    st.markdown("### ➕ Add New Income")
    with st.form("add_income_form"):
        inc_date = st.date_input("Date", key="income_date")
        inc_source = st.text_input("Source (e.g., Etsy, Squarespace, Vendor Event)")
        inc_category = st.text_input("Category (optional)")
        inc_desc = st.text_input("Description")
        inc_amount = st.number_input("Amount", min_value=0.0, step=1.0, key="income_amount")
        submitted_inc = st.form_submit_button("Add Income")
        if submitted_inc:
            conn = get_connection()
            conn.execute(
                "INSERT INTO income (date, source, category, description, amount) VALUES (?, ?, ?, ?, ?)",
                (str(inc_date), inc_source or None, inc_category or None, inc_desc or None, float(inc_amount)),
            )
            conn.commit()
            conn.close()
            refresh_data()
            st.success("Income record added successfully.")
            st.experimental_rerun()
    st.markdown("### ✏️ Edit or 🗑 Delete Income")
    if not income.empty and "id" in income.columns:
        # Build label map for income selectbox
        income_label_map = {}
        for _, row in income.iterrows():
            date_str = row["date"].date().isoformat() if isinstance(row["date"], pd.Timestamp) else str(row["date"])
            source_str = row.get("source") or "Unknown Source"
            amount_val = float(row["amount"])
            income_label_map[row["id"]] = f"{row['id']} | {date_str} | {source_str} | ${amount_val:,.2f}"
        selected_income_id = st.selectbox(
            "Select an income record to edit or delete",
            options=list(income_label_map.keys()),
            format_func=lambda x: income_label_map.get(x, str(x)),
            key="income_select"
        )
        selected_income_row = income[income["id"] == selected_income_id].iloc[0]
        with st.form("edit_income_form"):
            current_date_inc = selected_income_row["date"].date() if isinstance(selected_income_row["date"], pd.Timestamp) else selected_income_row["date"]
            new_inc_date = st.date_input("Edit Date", value=current_date_inc, key="edit_income_date")
            new_source = st.text_input("Edit Source", value=selected_income_row.get("source") or "")
            new_inc_category = st.text_input("Edit Category", value=selected_income_row.get("category") or "")
            new_inc_desc = st.text_input("Edit Description", value=selected_income_row.get("description") or "")
            new_inc_amount = st.number_input(
                "Edit Amount",
                min_value=0.0,
                value=float(selected_income_row["amount"]),
                step=1.0,
                key="edit_income_amount"
            )
            save_income_changes = st.form_submit_button("Save Changes")
            if save_income_changes:
                conn = get_connection()
                conn.execute(
                    "UPDATE income SET date=?, source=?, category=?, description=?, amount=? WHERE id=?",
                    (str(new_inc_date), new_source or None, new_inc_category or None, new_inc_desc or None, float(new_inc_amount), int(selected_income_id))
                )
                conn.commit()
                conn.close()
                refresh_data()
                st.success("Income record updated successfully.")
                st.experimental_rerun()
        if st.button("🗑 Delete Selected Income"):
            conn = get_connection()
            conn.execute("DELETE FROM income WHERE id=?", (int(selected_income_id),))
            conn.commit()
            conn.close()
            refresh_data()
            st.warning("Income record deleted.")
            st.experimental_rerun()
    else:
        st.info("No income records available to manage.")

