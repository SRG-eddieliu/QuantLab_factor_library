from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Type, Tuple, Dict, Any

import pandas as pd

from .analytics import (
    compute_all_analytics,
    compute_factor_correlation,
    save_correlation_matrix,
    corr_with_ff,
    update_registry,
)
from .data_loader import DataLoader
from .factor_definitions import get_default_factors
from .paths import factors_dir

logger = logging.getLogger(__name__)


def _run_factor_task(
    factor,
    sector_map,
    fwd_returns: pd.DataFrame,
    ff: pd.DataFrame | None,
) -> Tuple[str, pd.DataFrame, dict]:
    """
    Helper to compute a single factor and analytics.
    Uses a fresh DataLoader per task to avoid shared-state issues in threads.
    """
    loader = DataLoader()
    raw_scores = factor.compute(loader, sector_map=sector_map)
    analytics = compute_all_analytics(
        raw_scores,
        fwd_returns,
        factor_name=factor.name,
        write_registry=False,  # registry updated in caller to avoid contention
        ff_factors=ff,
    )
    return factor.name, raw_scores, analytics


def wide_to_long(df: pd.DataFrame, value_name: str = "Value") -> pd.DataFrame:
    out = df.stack().reset_index()
    out.columns = ["Date", "Ticker", value_name]
    out = out.dropna(subset=[value_name])
    out["Date"] = pd.to_datetime(out["Date"]).dt.date
    return out


def save_factor(factor_name: str, factor_df: pd.DataFrame) -> Path:
    factors_dir().mkdir(parents=True, exist_ok=True)
    path = factors_dir() / f"factor_{factor_name}.parquet"
    long_df = wide_to_long(factor_df)
    long_df.to_parquet(path, index=False)
    logger.info("Saved factor %s to %s", factor_name, path)
    return path


def run_all(parallel: bool = False, max_workers: int | None = None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    loader = DataLoader()
    sector_map = None
    try:
        sector_map = loader.load_sector_map()
    except Exception:
        logger.warning("Sector map unavailable; sector neutralization will be skipped.")

    # Save FF time-series factors (benchmark/reference) to factors_dir for downstream usage.
    ff = None
    try:
        ff = loader.load_ff_factors()
        ff_path = factors_dir() / "factor_ff_timeseries.parquet"
        ff_path.parent.mkdir(parents=True, exist_ok=True)
        ff.to_parquet(ff_path)
        logger.info("Saved FF factors to %s", ff_path)
    except Exception as exc:
        logger.warning("FF factors not available: %s", exc)

    price_wide = loader.load_price_wide(dataset="price_daily")
    fwd_returns = loader.forward_returns(price_wide)

    factors = get_default_factors()

    factor_outputs: Dict[str, pd.DataFrame] = {}
    ls_returns: Dict[str, pd.Series] = {}
    analytics_results: Dict[str, dict] = {}

    if parallel:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(_run_factor_task, factor, sector_map, fwd_returns, ff): factor.name for factor in factors}
            for fut in as_completed(futures):
                name, raw_scores, analytics = fut.result()
                factor_outputs[name] = raw_scores
                analytics_results[name] = analytics
    else:
        for factor in factors:
            name, raw_scores, analytics = _run_factor_task(factor, sector_map, fwd_returns, ff)
            factor_outputs[name] = raw_scores
            analytics_results[name] = analytics

    # Persist outputs and registry sequentially to avoid write contention
    for name, raw_scores in factor_outputs.items():
        save_factor(name, raw_scores)

    for name, analytics in analytics_results.items():
        summary = analytics.get("summary", {})
        if summary:
            update_registry(name, summary)
        ls_series = analytics.get("ls_returns")
        if ls_series is not None:
            ls_returns[name] = ls_series

    # Factor correlation matrix
    corr = compute_factor_correlation(factor_outputs)
    if not corr.empty:
        save_correlation_matrix(corr)
    # Correlation of LS PnL vs FF factors
    if ff is not None:
        ff_corr = corr_with_ff(ls_returns, ff)
        if not ff_corr.empty:
            ff_corr_path = factors_dir() / "factor_ff_correlation.parquet"
            ff_corr.to_parquet(ff_corr_path)
            logger.info("Saved factor vs FF correlation to %s", ff_corr_path)


if __name__ == "__main__":
    run_all()
