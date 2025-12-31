# dcf_dashboard/src/__init__.py
"""
src package initializer.

This file makes the 'src' directory a Python package so that
modules like data_loader, metrics, assumptions, forecast, dcf, and utils
can be imported cleanly from app.py and elsewhere.
"""

# Explicitly expose key modules/classes if desired
from .data_loader import DataLoader
from .metrics import compute_historical_metrics
from .assumptions import derive_defaults, scenario_presets, apply_overrides
from .forecast import build_forecast
from .dcf import run_dcf, ValuationInputs