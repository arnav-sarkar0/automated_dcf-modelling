from dataclasses import dataclass
import pandas as pd
import numpy as np
import yfinance as yf

from .utils import (
    logger,
    ensure_year_index,
    align_fiscal_years,
    validate_fields,
    MANDATORY_INCOME,
    MANDATORY_CASHFLOW,
    MANDATORY_BALANCE,
)

# -------------------------
# Data containers
# -------------------------

@dataclass
class RawStatements:
    income: pd.DataFrame
    cashflow: pd.DataFrame
    balance: pd.DataFrame


@dataclass
class NormalizedStatements:
    income: pd.DataFrame     # revenue, operating_income, pretax_income, tax_expense, net_income
    cashflow: pd.DataFrame   # capex, da, cfo, delta_nwc (optional)
    balance: pd.DataFrame    # current_assets (optional), current_liabilities, cash, total_debt


# -------------------------
# Loader
# -------------------------

class DataLoader:
    """
    Production-grade data loader for yfinance.

    Responsibilities:
        - Fetch financial statements
        - Normalize provider-specific labels & signs
        - Align fiscal years safely (no forward fill)
        - Validate mandatory fields
    """

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.ticker_obj = yf.Ticker(self.ticker)

    # -------------------------
    # Fetch raw data
    # -------------------------

    def fetch_raw(self) -> RawStatements:
        inc = self.ticker_obj.financials
        bs = self.ticker_obj.balance_sheet
        cf = self.ticker_obj.cashflow

        if inc is None or inc.empty:
            raise ValueError("Income statement not available; cannot run DCF.")

        if cf is None or cf.empty:
            logger.warning("Cash flow statement missing; reinvestment metrics may degrade.")

        if bs is None or bs.empty:
            logger.warning("Balance sheet missing; ΔNWC and leverage metrics may degrade.")

        inc = ensure_year_index(inc.T.copy())
        cf = ensure_year_index(cf.T.copy()) if cf is not None and not cf.empty else pd.DataFrame()
        bs = ensure_year_index(bs.T.copy()) if bs is not None and not bs.empty else pd.DataFrame()

        return RawStatements(income=inc, cashflow=cf, balance=bs)

    # -------------------------
    # Normalize Income Statement
    # -------------------------

    def normalize_income(self, inc: pd.DataFrame) -> pd.DataFrame:
        label_map = {
            "Total Revenue": "revenue",
            "Revenue": "revenue",
            "Operating Income": "operating_income",
            "EBIT": "operating_income",
            "Ebit": "operating_income",
            "Income Before Tax": "pretax_income",
            "Income Tax Expense": "tax_expense",
            "Provision for income taxes": "tax_expense",
            "Net Income": "net_income",
            "Net Income Common Stockholders": "net_income",
        }

        normalized = pd.DataFrame(index=inc.index)
        for raw, norm in label_map.items():
            if raw in inc.columns:
                normalized[norm] = inc[raw]

        validate_fields(normalized, MANDATORY_INCOME, "Income Statement")
        return normalized

    # -------------------------
    # Normalize Cash Flow Statement
    # -------------------------

    def normalize_cashflow(self, cf: pd.DataFrame) -> pd.DataFrame:
        if cf is None or cf.empty:
            return pd.DataFrame(index=pd.Index([], name="fiscal_year"))

        label_map = {
            # CapEx
            "Capital Expenditure": "capex",
            "Capital Expenditures": "capex",
            "CapitalExpenditure": "capex",

            # D&A
            "Depreciation": "da",
            "Depreciation And Amortization": "da",
            "Reconciled Depreciation": "da",

            # CFO
            "Operating Cash Flow": "cfo",
            "Total Cash From Operating Activities": "cfo",

            # ΔNWC (preferred source)
            "Change In Working Capital": "delta_nwc",
            "ChangeInWorkingCapital": "delta_nwc",
        }

        normalized = pd.DataFrame(index=cf.index)
        for raw, norm in label_map.items():
            if raw in cf.columns:
                normalized[norm] = cf[raw]

        # 🔑 Normalize CapEx sign (Yahoo reports it negative)
        if "capex" in normalized.columns:
            normalized["capex"] = normalized["capex"].abs()

        validate_fields(normalized, MANDATORY_CASHFLOW, "Cash Flow Statement")
        return normalized

    # -------------------------
    # Normalize Balance Sheet
    # -------------------------

    def normalize_balance(self, bs: pd.DataFrame) -> pd.DataFrame:
        if bs is None or bs.empty:
            return pd.DataFrame(index=pd.Index([], name="fiscal_year"))

        normalized = pd.DataFrame(index=bs.index)

        # -------------------------
        # Current Assets (optional)
        # -------------------------
        for ca_label in [
            "Total Current Assets",
            "Current Assets",
            "CurrentAssets",
        ]:
            if ca_label in bs.columns:
                normalized["current_assets"] = bs[ca_label]
                break

        # -------------------------
        # Current Liabilities (mandatory)
        # -------------------------
        for cl_label in [
            "Total Current Liabilities",
            "Current Liabilities",
            "CurrentLiabilities",
            "Current Liabilities Net Minority Interest",
        ]:
            if cl_label in bs.columns:
                normalized["current_liabilities"] = bs[cl_label]
                break

        # -------------------------
        # Cash
        # -------------------------
        for cash_label in [
            "Cash And Cash Equivalents",
            "Cash",
        ]:
            if cash_label in bs.columns:
                normalized["cash"] = bs[cash_label]
                break

        # -------------------------
        # Debt
        # -------------------------
        if "Total Debt" in bs.columns:
            normalized["total_debt"] = bs["Total Debt"]
        else:
            debt_parts = []
            if "Short Long Term Debt" in bs.columns:
                debt_parts.append(bs["Short Long Term Debt"])
            if "Long Term Debt" in bs.columns:
                debt_parts.append(bs["Long Term Debt"])
            if debt_parts:
                normalized["total_debt"] = sum(debt_parts)

        validate_fields(normalized, MANDATORY_BALANCE, "Balance Sheet")
        return normalized

    # -------------------------
    # Public API
    # -------------------------

    def load(self) -> NormalizedStatements:
        raw = self.fetch_raw()

        inc_n = self.normalize_income(raw.income)
        cf_n = self.normalize_cashflow(raw.cashflow)
        bs_n = self.normalize_balance(raw.balance)

        # Align on common fiscal years only (no forward fill)
        inc_n, cf_n, bs_n = align_fiscal_years([inc_n, cf_n, bs_n])

        return NormalizedStatements(
            income=inc_n,
            cashflow=cf_n,
            balance=bs_n,
        )
