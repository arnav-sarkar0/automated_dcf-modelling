# dcf_dashboard/src/dcf.py
from dataclasses import dataclass
from typing import Optional, Dict
import pandas as pd
import numpy as np

from .utils import logger

@dataclass
class ValuationInputs:
    rf: float                 # risk-free
    erp: float                # equity risk premium
    beta: float               # levered beta
    cost_of_debt: float       # pre-tax
    tax_rate: float
    equity_value: Optional[float] = None  # optional market cap for sanity checks
    net_debt: Optional[float] = None      # cash - total debt negative -> net cash

@dataclass
class DCFResult:
    wacc: float
    pv_fcff: float
    terminal_value: float
    enterprise_value: float
    equity_value: Optional[float]
    intrinsic_per_share: Optional[float]
    shares_outstanding: Optional[float]
    sensitivity: pd.DataFrame

def compute_wacc(inp: ValuationInputs, equity_weight: float, debt_weight: float) -> float:
    ce = inp.rf + inp.beta * inp.erp
    cd_after_tax = inp.cost_of_debt * (1 - inp.tax_rate)
    return equity_weight * ce + debt_weight * cd_after_tax

def discount_cashflows(forecast_df: pd.DataFrame, wacc: float) -> float:
    years = np.arange(1, len(forecast_df) + 1)
    disc = (1 + wacc) ** years
    return float((forecast_df["fcff"].values / disc).sum())

def terminal_gordon(forecast_df: pd.DataFrame, wacc: float, g: float) -> float:
    if wacc <= g:
        raise ValueError("WACC must be greater than terminal growth rate.")
    fcff_last = float(forecast_df["fcff"].iloc[-1])
    tv = fcff_last * (1 + g) / (wacc - g)
    # Discount back one more period
    years = len(forecast_df)
    return float(tv / ((1 + wacc) ** years))

def run_dcf(
    forecast_df: pd.DataFrame,
    val_inp: ValuationInputs,
    equity_weight: float,
    debt_weight: float,
    terminal_growth: float,
    shares_outstanding: Optional[float] = None,
    exit_multiple: Optional[float] = None,
    exit_metric: Optional[pd.Series] = None  # e.g., EBITDA in final year
) -> DCFResult:
    wacc = compute_wacc(val_inp, equity_weight, debt_weight)
    pv_fcff = discount_cashflows(forecast_df, wacc)
    tv_gg = terminal_gordon(forecast_df, wacc, terminal_growth)

    ev = pv_fcff + tv_gg

    # Optional exit multiple sanity check (not primary)
    if exit_multiple is not None and exit_metric is not None:
        final_metric = float(exit_metric.iloc[-1])
        tv_exit = final_metric * exit_multiple
        tv_exit_disc = tv_exit / ((1 + wacc) ** len(forecast_df))
        # We don't combine; we can present as alternative
        logger.info(f"Exit multiple alternative EV component (discounted): {tv_exit_disc:.2f}")

    eq_value = None
    intrinsic_ps = None
    if val_inp.net_debt is not None:
        eq_value = ev - val_inp.net_debt
        if shares_outstanding is not None and shares_outstanding > 0:
            intrinsic_ps = eq_value / shares_outstanding

    # Sensitivity table over (wacc, g)
    wacc_range = np.round(np.linspace(max(wacc - 0.02, 0.03), wacc + 0.02, 5), 4)
    g_range = np.round(np.linspace(max(terminal_growth - 0.01, 0.0), terminal_growth + 0.01, 5), 4)
    sens_rows = []
    for w in wacc_range:
        for g in g_range:
            try:
                pv = discount_cashflows(forecast_df, w)
                tv = terminal_gordon(forecast_df, w, g)
                ev_s = pv + tv
                sens_rows.append({"wacc": w, "g": g, "enterprise_value": ev_s})
            except Exception:
                sens_rows.append({"wacc": w, "g": g, "enterprise_value": np.nan})
    sensitivity = pd.DataFrame(sens_rows).pivot(index="wacc", columns="g", values="enterprise_value")

    return DCFResult(
        wacc=wacc,
        pv_fcff=pv_fcff,
        terminal_value=tv_gg,
        enterprise_value=ev,
        equity_value=eq_value,
        intrinsic_per_share=intrinsic_ps,
        shares_outstanding=shares_outstanding,
        sensitivity=sensitivity
    )