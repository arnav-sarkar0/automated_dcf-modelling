# dcf_dashboard/src/company_overview.py

import streamlit as st
import yfinance as yf


def get_company_info(ticker: str) -> dict:
    """
    Fetches key company information from Yahoo Finance for a given ticker.
    Returns a dictionary with formatted fields.
    """
    ticker_obj = yf.Ticker(ticker)
    info = ticker_obj.info

    # Use .get() to avoid KeyError if field is missing
    return {
        "name": info.get("longName", "N/A"),
        "price": info.get("currentPrice", None),
        "market_cap": info.get("marketCap", None),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "website": info.get("website", ""),
        "52_week_low": info.get("fiftyTwoWeekLow", None),
        "52_week_high": info.get("fiftyTwoWeekHigh", None),
        "pe_ratio": info.get("trailingPE", None),
        "dividend_yield": info.get("dividendYield", None),
    }


def display_company_overview():
    """
    Streamlit page for displaying company overview.
    """
    st.title("📊 Company Overview")

    # User input for ticker
    ticker = st.text_input("Enter Company Ticker (e.g., AAPL)", "AAPL").upper()

    if not ticker:
        st.warning("Please enter a ticker symbol.")
        return

    try:
        info = get_company_info(ticker)

        st.header(f"{info['name']} ({ticker})")

        # Display key metrics
        col1, col2 = st.columns(2)

        with col1:
            if info["price"] is not None:
                st.metric("Current Price", f"${info['price']:,}")
            if info["market_cap"] is not None:
                st.metric("Market Cap", f"${info['market_cap'] / 1e9:,.2f} B")
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
                st.write(f"**Dividend Yield:** {info['dividend_yield'] * 100:.2f}%")

    except Exception as e:
        st.error(f"Failed to fetch data for ticker '{ticker}': {e}")
