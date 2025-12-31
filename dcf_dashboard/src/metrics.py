# dcf_dashboard/src/metrics.py
from dataclasses import dataclass
from typing import Dict, Optional
import pandas as pd
import numpy as np

from .utils import logger, log_assumption

@dataclass
class HistoricalMetrics:
    revenue_cagr: float
    ebit_margin: float
    ebitda_margin: float
    capex_pct_revenue: float
    da_pct_revenue: float
    d_nwc_pct_revenue: float
    lookback_years: int

def compute_cagr(series: pd.Series) -> Optional[float]:
    """
    Compute CAGR from first to last non-NaN value in series.
    Requires at least 3 data points by design (interview-grade discipline).
    """
    s = series.dropna()
    if len(s) < 3:
        return None
    start = s.iloc[0]
    end = s.iloc[-1]
    n_periods = len(s) - 1
    if start <= 0 or end <= 0:
        # If negative revenue appears (rare), we avoid CAGR and return None.
        return None
    try:
        return (end / start) ** (1 / n_periods) - 1
    except Exception:
        return None

def median_over_years(series: pd.Series, min_years: int = 3) -> Optional[float]:
    s = series.dropna()
    if len(s) < min_years:
        return None
    return float(np.median(s))

def compute_historical_metrics(
    inc: pd.DataFrame,
    cf: pd.DataFrame,
    bs: pd.DataFrame,
    lookback: int = 5,
    min_years: int = 3
) -> HistoricalMetrics:
    """
    Compute medians for margins and capital intensity, and CAGR for revenue.
    We do not forward-fill. Align years upstream.
    """
    if "revenue" not in inc.columns:
        raise ValueError("Revenue missing; cannot compute historical metrics.")

    # Constrain to lookback most recent years
    years = sorted(inc.index)[-lookback:] if len(inc.index) > lookback else sorted(inc.index)
    inc_lb = inc.loc[years]
    cf_lb = cf.loc[years] if not cf.empty else pd.DataFrame(index=years)
    bs_lb = bs.loc[years] if not bs.empty else pd.DataFrame(index=years)

    revenue = inc_lb.get("revenue")
    ebit = inc_lb.get("operating_income")
    pretax = inc_lb.get("pretax_income")
    tax_exp = inc_lb.get("tax_expense")
    net_inc = inc_lb.get("net_income")

    # D&A, CapEx, CFO from cash flow
    da = cf_lb.get("da")
    capex = cf_lb.get("capex")
    cfo = cf_lb.get("cfo")

    # EBITDA approximation: EBIT + D&A (if D&A missing, EBITDA margin may be None)
    ebit_margin = median_over_years(ebit / revenue) if ebit is not None and revenue is not None else None
    ebitda_margin = None
    if ebit is not None and da is not None and revenue is not None:
        ebitda_margin = median_over_years((ebit + da) / revenue)

    capex_pct = None
    if capex is not None and revenue is not None:
        capex_pct = median_over_years(capex / revenue)

    da_pct = None
    if da is not None and revenue is not None:
        da_pct = median_over_years(da / revenue)

    # ΔNWC % revenue:
    # ΔNWC_t = (CA_t - CL_t) - (CA_{t-1} - CL_{t-1})
    '''d_nwc_pct = None
    if "current_assets" in bs_lb.columns and "current_liabilities" in bs_lb.columns and revenue is not None:
        nwc = bs_lb["current_assets"] - bs_lb["current_liabilities"]
        d_nwc = nwc.diff()
        # Align to revenue index and divide; earliest year delta is NaN by construction.
        d_nwc_pct = median_over_years(d_nwc / revenue)
    else:
        # Mandatory fallback logic
        log_assumption("current_assets missing or current_liabilities missing -> assume ΔNWC % revenue = 0 for forecasts.")
        d_nwc_pct = 0.0'''
    
    # -------------------------
    # ΔNWC % Revenue
    # -------------------------
    d_nwc_pct = None

    # 1️⃣ Prefer cash-flow ΔNWC (BEST SOURCE)
    if "delta_nwc" in cf_lb.columns and revenue is not None:
        d_nwc_pct = median_over_years(cf_lb["delta_nwc"] / revenue)

    # 2️⃣ Fallback: balance sheet ΔNWC
    elif (
        "current_assets" in bs_lb.columns
        and "current_liabilities" in bs_lb.columns
        and revenue is not None
    ):
        nwc = bs_lb["current_assets"] - bs_lb["current_liabilities"]
        d_nwc = nwc.diff()
        d_nwc_pct = median_over_years(d_nwc / revenue)

    # 3️⃣ Final fallback: assume stable NWC
    else:
        log_assumption(
            "ΔNWC unavailable from cash flow and balance sheet → assume ΔNWC % revenue = 0."
        )
        d_nwc_pct = 0.0


    # Revenue CAGR over the lookback window
    rev_cagr = compute_cagr(revenue) if revenue is not None else None

    return HistoricalMetrics(
        revenue_cagr=rev_cagr if rev_cagr is not None else 0.0,  # conservative: default zero growth if unstable
        ebit_margin=ebit_margin if ebit_margin is not None else 0.0,
        ebitda_margin=ebitda_margin if ebitda_margin is not None else None,
        capex_pct_revenue=capex_pct if capex_pct is not None else 0.0,
        da_pct_revenue=da_pct if da_pct is not None else 0.0,
        d_nwc_pct_revenue=d_nwc_pct if d_nwc_pct is not None else 0.0,
        lookback_years=len(years)
    )