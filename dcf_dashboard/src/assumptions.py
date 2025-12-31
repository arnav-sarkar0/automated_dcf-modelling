# dcf_dashboard/src/assumptions.py
from dataclasses import dataclass
from typing import Optional, Dict
import pandas as pd

from .utils import log_assumption
from .metrics import HistoricalMetrics

@dataclass
class Assumptions:
    years: int
    revenue_growth: float          # annual rate
    ebit_margin: float
    tax_rate: float
    da_pct_revenue: float
    capex_pct_revenue: float
    d_nwc_pct_revenue: float
    terminal_growth: float
    use_ebitda_margin: bool = False
    ebitda_margin: Optional[float] = None

DEFAULT_YEARS = 10

def derive_defaults(hist: HistoricalMetrics, tax_rate_default: float = 0.25, terminal_growth_default: float = 0.02) -> Assumptions:
    """
    Derive conservative base-case assumptions from historical metrics.
    """
    if hist.ebitda_margin is None:
        use_ebitda = False
        ebitda_margin = None
    else:
        use_ebitda = True
        ebitda_margin = hist.ebitda_margin

    return Assumptions(
        years=DEFAULT_YEARS,
        revenue_growth=hist.revenue_cagr,
        ebit_margin=hist.ebit_margin,
        tax_rate=tax_rate_default,
        da_pct_revenue=hist.da_pct_revenue,
        capex_pct_revenue=hist.capex_pct_revenue,
        d_nwc_pct_revenue=hist.d_nwc_pct_revenue,
        terminal_growth=terminal_growth_default,
        use_ebitda_margin=use_ebitda,
        ebitda_margin=ebitda_margin
    )

def scenario_presets(base: Assumptions) -> Dict[str, Assumptions]:
    """
    Create Bull/Bear variants around Base with disciplined shifts.
    """
    bull = Assumptions(
        years=base.years,
        revenue_growth=base.revenue_growth + 0.03,
        ebit_margin=min(base.ebit_margin + 0.03, 0.4),
        tax_rate=base.tax_rate,
        da_pct_revenue=max(base.da_pct_revenue - 0.005, 0.0),
        capex_pct_revenue=max(base.capex_pct_revenue - 0.005, 0.0),
        d_nwc_pct_revenue=max(base.d_nwc_pct_revenue - 0.003, 0.0),
        terminal_growth=base.terminal_growth + 0.005,
        use_ebitda_margin=base.use_ebitda_margin,
        ebitda_margin=base.ebitda_margin + 0.02 if base.ebitda_margin is not None else None
    )
    bear = Assumptions(
        years=base.years,
        revenue_growth=max(base.revenue_growth - 0.03, -0.1),
        ebit_margin=max(base.ebit_margin - 0.03, 0.0),
        tax_rate=base.tax_rate,
        da_pct_revenue=base.da_pct_revenue + 0.005,
        capex_pct_revenue=base.capex_pct_revenue + 0.005,
        d_nwc_pct_revenue=base.d_nwc_pct_revenue + 0.003,
        terminal_growth=max(base.terminal_growth - 0.005, 0.0),
        use_ebitda_margin=base.use_ebitda_margin,
        ebitda_margin=base.ebitda_margin - 0.02 if base.ebitda_margin is not None else None
    )
    return {"Base": base, "Bull": bull, "Bear": bear}

def apply_overrides(base: Assumptions, **overrides) -> Assumptions:
    """
    Allow user overrides; log each override to maintain transparency.
    """
    for k, v in overrides.items():
        if hasattr(base, k) and v is not None:
            log_assumption(f"Override {k} = {v}")
            setattr(base, k, v)
    return base