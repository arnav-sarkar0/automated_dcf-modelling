# dcf_dashboard/app.py
import streamlit as st
import pandas as pd
import plotly.express as px

from src.data_loader import DataLoader
from src.metrics import compute_historical_metrics
from src.assumptions import derive_defaults, scenario_presets, apply_overrides
from src.forecast import build_forecast
from src.dcf import ValuationInputs, run_dcf
from src.utils import format_large_number
from src.company_overview import get_company_info  # <-- New import

st.set_page_config(page_title="DCF Valuation Dashboard", layout="wide")
st.title("📊 Automated DCF Valuation Dashboard")

# Sidebar — Company selection and market inputs
ticker = st.sidebar.text_input("Ticker (Yahoo Finance)", value="AAPL").upper()
rf = st.sidebar.number_input("Risk-free rate", value=0.04, step=0.005, format="%.3f")
erp = st.sidebar.number_input("Equity risk premium", value=0.05, step=0.005, format="%.3f")
beta = st.sidebar.number_input("Beta (levered)", value=1.10, step=0.05, format="%.2f")
cost_of_debt = st.sidebar.number_input("Cost of debt (pre-tax)", value=0.05, step=0.005, format="%.3f")
equity_weight = st.sidebar.slider("Equity weight", min_value=0.0, max_value=1.0, value=0.7, step=0.05)
debt_weight = 1.0 - equity_weight

# Load financial statements
loader = DataLoader(ticker)
try:
    statements = loader.load()
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

# Tabs for navigation
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Company Overview", "Historical Financials", "Assumptions", "Forecasts", "Valuation"
])

# -------------------------
# Tab 1: Company Overview
# -------------------------
with tab1:
    st.subheader("Company Overview")
    try:
        info = get_company_info(ticker)
        st.header(f"{info['name']} ({ticker})")

        col1, col2 = st.columns(2)
        with col1:
            if info["price"] is not None:
                st.metric("Current Price", f"${info['price']:,}")
            if info["market_cap"] is not None:
                st.metric("Market Cap", f"${info['market_cap']/1e9:,.2f} B")
            st.write(f"**Sector:** {info['sector']}")
            st.write(f"**Industry:** {info['industry']}")
            if info["website"]:
                st.write(f"[Company Website]({info['website']})")
        with col2:
            if info["52_week_low"] is not None and info["52_week_high"] is not None:
                st.write(f"**52-Week Range:** ${info['52_week_low']:,} - ${info['52_week_high']:,}")
            if info["pe_ratio"] is not None:
                st.write(f"**PE Ratio:** {info['pe_ratio']}")
            if info["dividend_yield"] is not None:
                st.write(f"**Dividend Yield:** {info['dividend_yield']*100:.2f}%")
    except Exception as e:
        st.error(f"Failed to fetch company overview: {e}")

# -------------------------
# Tab 2: Historical Financials
# -------------------------
with tab2:
    st.subheader("Historical Financials")
    st.dataframe(statements.income.style.format(format_large_number))
    st.dataframe(statements.cashflow.style.format(format_large_number))
    st.dataframe(statements.balance.style.format(format_large_number))

# Compute metrics
hist = compute_historical_metrics(statements.income, statements.cashflow, statements.balance, lookback=5)

# -------------------------
# Tab 3: Assumptions
# -------------------------
with tab3:
    st.subheader("Assumptions")
    base = derive_defaults(hist)
    presets = scenario_presets(base)
    scenario_name = st.selectbox("Scenario", options=list(presets.keys()), index=0)
    ass = presets[scenario_name]

    years = st.number_input("Forecast years", value=ass.years, min_value=5, max_value=10, step=1)
    rev_g = st.number_input("Revenue growth", value=ass.revenue_growth, step=0.005, format="%.3f")
    ebit_m = st.number_input("EBIT margin", value=ass.ebit_margin, step=0.005, format="%.3f")
    tax = st.number_input("Tax rate", value=ass.tax_rate, step=0.01, format="%.2f")
    da_pct = st.number_input("D&A % revenue", value=ass.da_pct_revenue, step=0.002, format="%.3f")
    capex_pct = st.number_input("CapEx % revenue", value=ass.capex_pct_revenue, step=0.002, format="%.3f")
    d_nwc_pct = st.number_input("ΔNWC % revenue", value=ass.d_nwc_pct_revenue, step=0.002, format="%.3f")
    term_g = st.number_input("Terminal growth (Gordon)", value=ass.terminal_growth, step=0.002, format="%.3f")

    ass = apply_overrides(ass, years=years, revenue_growth=rev_g, ebit_margin=ebit_m,
                          tax_rate=tax, da_pct_revenue=da_pct,
                          capex_pct_revenue=capex_pct, d_nwc_pct_revenue=d_nwc_pct,
                          terminal_growth=term_g)

# -------------------------
# Tab 4: Forecasts
# -------------------------
with tab4:
    st.subheader("Forecasts")
    last_year = int(sorted(statements.income.index)[-1])
    last_rev = float(statements.income["revenue"].dropna().iloc[-1])
    forecast = build_forecast(last_actual_year=last_year, last_actual_revenue=last_rev, assumptions=ass)
    st.dataframe(forecast.df.style.format(format_large_number))
    fig = px.line(forecast.df.reset_index(), x="year", y="fcff", title="FCFF Forecast")
    st.plotly_chart(fig, use_container_width=True)

# -------------------------
# Tab 5: Valuation
# -------------------------
with tab5:
    st.subheader("Valuation Summary")
    val_inp = ValuationInputs(
        rf=rf, erp=erp, beta=beta, cost_of_debt=cost_of_debt, tax_rate=ass.tax_rate,
        net_debt=None
    )
    if not statements.balance.empty and "cash" in statements.balance.columns and "total_debt" in statements.balance.columns:
        cash_last = float(statements.balance["cash"].dropna().iloc[-1]) if not statements.balance["cash"].dropna().empty else 0.0
        debt_last = float(statements.balance["total_debt"].dropna().iloc[-1]) if not statements.balance["total_debt"].dropna().empty else 0.0
        val_inp.net_debt = debt_last - cash_last

    shares = st.sidebar.number_input("Shares outstanding (if known)", value=0.0, step=1e6, format="%.0f")
    dcf_res = run_dcf(
        forecast_df=forecast.df,
        val_inp=val_inp,
        equity_weight=equity_weight,
        debt_weight=debt_weight,
        terminal_growth=ass.terminal_growth,
        shares_outstanding=shares if shares > 0 else None
    )

    colA, colB, colC = st.columns(3)
    with colA:
        st.metric("WACC", f"{dcf_res.wacc:.2%}")
        st.metric("PV of FCFF", format_large_number(dcf_res.pv_fcff))
    with colB:
        st.metric("Terminal Value", format_large_number(dcf_res.terminal_value))
        st.metric("Enterprise Value", format_large_number(dcf_res.enterprise_value))
    with colC:
        st.metric("Equity Value", format_large_number(dcf_res.equity_value))
        if dcf_res.intrinsic_per_share is not None:
            st.metric("Projected Share Price", f"${dcf_res.intrinsic_per_share:,.2f}")

    st.subheader("Sensitivity Analysis")
    fig = px.imshow(dcf_res.sensitivity, aspect="auto", color_continuous_scale="Blues",
                    labels=dict(x="Terminal Growth (g)", y="WACC", color="EV"))
    st.plotly_chart(fig, use_container_width=True)
