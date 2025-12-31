import logging
import pandas as pd
import numpy as np

# Configure logger
logger = logging.getLogger("dcf")
logger.setLevel(logging.INFO)

if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

# Mandatory fields for validation
MANDATORY_INCOME = ["revenue", "operating_income", "pretax_income", "tax_expense", "net_income"]
MANDATORY_CASHFLOW = ["capex", "da", "cfo"]
MANDATORY_BALANCE = ["current_liabilities", "cash", "total_debt"]

def ensure_year_index(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure index is fiscal year as int.
    YFinance returns columns as dates; rows already years for statements.
    """
    idx = df.index
    if np.issubdtype(idx.dtype, np.integer):
        return df
    try:
        years = pd.to_datetime(idx).year
    except Exception:
        years = pd.Index([int(str(x)[:4]) for x in idx], dtype=int)
    df = df.copy()
    df.index = pd.Index(years, name="fiscal_year")
    return df

def align_fiscal_years(dfs):
    """
    Intersect fiscal years across provided DataFrames; drop non-common years.
    No forward-fill performed.
    """
    if not dfs:
        return dfs
    years = set(dfs[0].index)
    for d in dfs[1:]:
        years = years.intersection(set(d.index))
    common = sorted(years)
    aligned = [df.loc[common] for df in dfs]
    return aligned

def validate_fields(df: pd.DataFrame, required, statement_name: str) -> None:
    """
    Validate presence of mandatory fields in a normalized statement.
    Logs warnings if missing.
    """
    missing = [c for c in required if c not in df.columns]
    if missing:
        logger.warning(f"{statement_name}: missing fields {missing} after normalization.")

def log_assumption(msg: str) -> None:
    """
    Log explicit assumptions instead of silently filling values.
    """
    logger.warning(f"Assumption: {msg}")

def format_large_number(value: float) -> str:
    """
    Format numbers into Millions or Billions for readability.
    - >= 1B → show in Billions
    - >= 1M → show in Millions
    - else → show raw with commas
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "-"
    abs_val = abs(value)
    if abs_val >= 1e9:
        return f"{value/1e9:,.2f} B"
    elif abs_val >= 1e6:
        return f"{value/1e6:,.2f} M"
    else:
        return f"{value:,.0f}"