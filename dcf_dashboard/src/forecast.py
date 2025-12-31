# dcf_dashboard/src/forecast.py
from dataclasses import dataclass
import pandas as pd

from .assumptions import Assumptions

@dataclass
class ForecastOutputs:
    df: pd.DataFrame  # columns: revenue, ebit, nopat, da, capex, d_nwc, fcff

def build_forecast(last_actual_year: int, last_actual_revenue: float, assumptions: Assumptions) -> ForecastOutputs:
    """
    Build forward 5-10Y forecast using stable percentage-of-revenue model for capital items.
    No historical forward-fill; starts from last actual revenue.
    """
    years = [last_actual_year + i for i in range(1, assumptions.years + 1)]
    rows = []

    revenue = last_actual_revenue
    for y in years:
        revenue = revenue * (1 + assumptions.revenue_growth)
        if assumptions.use_ebitda_margin and assumptions.ebitda_margin is not None:
            # If EBITDA margin is provided, derive EBIT by subtracting DA% (not perfect, but consistent)
            ebitda = assumptions.ebitda_margin * revenue
            da = assumptions.da_pct_revenue * revenue
            ebit = max(ebitda - da, 0.0)
        else:
            ebit = assumptions.ebit_margin * revenue
            da = assumptions.da_pct_revenue * revenue

        nopat = ebit * (1 - assumptions.tax_rate)
        capex = assumptions.capex_pct_revenue * revenue
        d_nwc = assumptions.d_nwc_pct_revenue * revenue

        fcff = nopat + da - capex - d_nwc

        rows.append({
            "year": y,
            "revenue": revenue,
            "ebit": ebit,
            "nopat": nopat,
            "da": da,
            "capex": capex,
            "d_nwc": d_nwc,
            "fcff": fcff
        })

    df = pd.DataFrame(rows).set_index("year")
    return ForecastOutputs(df=df)