import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
# Page
st.set_page_config(
    page_title="Business Expense Analyzer",
    layout="wide",
    page_icon="📊"
)
st.title("📊 Business Expense Analyzer")
st.caption("Analyze real income & expenses from your small business (built for Merriness Fortune).")
# Helper: Load Data 
@st.cache_data
def load_csv(path):
    try:
        df = pd.read_csv(path)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        return df
    except Exception as e:
        st.warning(f"Could not load {path}: {e}")
        return pd.DataFrame()
# Load default data
expenses = load_csv("data/expenses.csv")
income = load_csv("data/income.csv")
if expenses.empty and income.empty:
    st.error("No data available. Check your CSV files in /data folder.")
    st.stop()
# Sidebar Filters
st.sidebar.header("Filters")
# Date range filter
min_date = min(expenses["date"].min(), income["date"].min())
max_date = max(expenses["date"].max(), income["date"].max())
start_date = st.sidebar.date_input("Start Date", min_date)
end_date = st.sidebar.date_input("End Date", max_date)
if start_date > end_date:
    st.sidebar.error("Start date must be before end date.")
# Apply filter
expenses = expenses[(expenses["date"] >= pd.to_datetime(start_date)) &
                    (expenses["date"] <= pd.to_datetime(end_date))]
income = income[(income["date"] >= pd.to_datetime(start_date)) &
                (income["date"] <= pd.to_datetime(end_date))]
# METRICS 
total_expenses = expenses["amount"].sum()
total_income = income["amount"].sum()
profit = total_income - total_expenses
col1, col2, col3 = st.columns(3)
col1.metric("Total Income", f"${total_income:,.2f}")
col2.metric("Total Expenses", f"${total_expenses:,.2f}")
col3.metric("Profit", f"${profit:,.2f}", delta=f"{profit:,.2f}")
st.markdown("---")
# Expense Breakdown
if "category" in expenses.columns:
    st.subheader("💸 Expense Breakdown by Category")
    category_totals = expenses.groupby("category")["amount"].sum()
    left, right = st.columns([1, 1.2])
    with left:
        st.dataframe(category_totals.rename("Total Amount"))
    with right:
        fig, ax = plt.subplots()
        ax.pie(category_totals, labels=category_totals.index, autopct="%1.1f%%")
        ax.set_title("Expenses by Category")
        st.pyplot(fig)
else:
    st.info("Your expenses.csv file needs a 'category' column to display breakdown charts.")
st.markdown("---")
# Income Over Time
if "date" in income.columns and "amount" in income.columns:
    st.subheader("📈 Income Over Time")
    income_time = income.set_index("date")["amount"].sort_index()
    st.line_chart(income_time)
st.markdown("---")
# Raw Data
st.subheader("📂 Raw Data")
tab1, tab2 = st.tabs(["Expenses", "Income"])
with tab1:
    st.write("Filtered Expenses Data")
    st.dataframe(expenses)
with tab2:
    st.write("Filtered Income Data")
    st.dataframe(income)
