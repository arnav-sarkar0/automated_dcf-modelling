# Automated DCF Valuation Dashboard

An interactive Python-based dashboard to perform **Discounted Cash Flow (DCF)** valuations for publicly listed companies. This project leverages **Yahoo Finance** data, calculates historical metrics, allows user-defined assumptions, builds forecasts, and computes intrinsic share price using a modular and production-ready approach.

---

## Features

- **Company Overview**
  - Ticker, sector, industry, market cap, share price
  - Mini historical stock price chart
  - Shares outstanding

- **Historical Financials**
  - Income statement, balance sheet, cash flow statement
  - Key historical metrics: revenue growth, EBIT margin, CapEx, D&A, ΔNWC

- **Assumptions**
  - Forecast years, revenue growth, EBIT margin, tax rate, D&A, CapEx, ΔNWC, terminal growth
  - Scenario selection: Base / Custom

- **Forecasts**
  - 5–10 year forward revenue, EBIT, NOPAT, FCFF
  - FCFF plotted dynamically
  - Supports linear growth forecasts

- **Valuation**
  - DCF-based Enterprise Value, Equity Value, and intrinsic share price
  - Sensitivity analysis for WACC vs Terminal growth

- **Modular Design**
  - Data Loader
  - Metrics Computation
  - Forecast Engine
  - DCF Calculator
  - Streamlit UI

---


