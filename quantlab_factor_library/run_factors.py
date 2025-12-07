from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Type

import pandas as pd

from .analytics import (
    compute_all_analytics,
    compute_factor_correlation,
    save_correlation_matrix,
    corr_with_ff,
)
from .data_loader import DataLoader
from .factors import MeanReversion, Momentum, Volatility, DollarVolume
from .paths import factors_dir

logger = logging.getLogger(__name__)


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


def run_all():
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

    factors = [
        Momentum(lookback_days=252, skip_days=21, name="momentum_12m"),
        Volatility(window=60, name="volatility_60d"),
        MeanReversion(lookback_days=5, name="mean_reversion_5d"),
        DollarVolume(window=20, name="dollar_volume_20d"),
    ]

    factor_outputs = {}
    ls_returns = {}
    analytics_results = {}
    for factor in factors:
        raw_scores = factor.compute(loader, sector_map=sector_map)
        factor_outputs[factor.name] = raw_scores
        save_factor(factor.name, raw_scores)

        analytics_results[factor.name] = compute_all_analytics(
            raw_scores,
            fwd_returns,
            factor_name=factor.name,
            write_registry=True,
            ff_factors=ff,
        )
        ls_series = analytics_results[factor.name].get("ls_returns")
        if ls_series is not None:
            ls_returns[factor.name] = ls_series

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
