# QuantLab Factor Library

Factor research toolkit that reads cleaned Parquet outputs from the data pipeline (`../data/data-processed/*.parquet`) and writes factor signals/analytics to `../data/factors/`. Includes templates, loaders, transforms, analytics, and an example notebook.

## Quickstart
- Configure paths in `config/config.json` if needed (`data_root`, `final_dir`, `factors_dir`); defaults point to `../data`.
- Factor cleaning defaults can also be tweaked in `config/config.json` under `factor_defaults` (winsor_limits, min_coverage, fill_method, neutralize_method); per-factor calls can still override.
- Create env: `conda env create -f quantlab_env/environment.yml` (includes numpy, pandas, pyarrow, scipy, etc.).
- Run default factors:  
  `python -m quantlab_factor_library.run_factors`
- Example : [`notebooks/factor_parallel_demo.ipynb`](notebooks/factor_parallel_demo.ipynb)
- Cleaning defaults and per-factor overrides can be tweaked in `config/config.json` (`factor_defaults` and `factor_overrides`, including forward_fill flags for fundamentals); per-factor calls can still override in code.

## Modular run steps
You no longer need to run end-to-end every time:
- `compute_factors(parallel=False, max_workers=4)`: compute/clean factors, save factor files and LS PnL; returns factors, ls_returns, ff, fwd_returns.
- `run_analytics_only(factors, fwd_returns, ff=None)`: IC/IR, LS stats, FF regression; writes diagnostics/registry.
- `compute_correlations_only(factors, ls_returns=None, ff=None)`: factor cross-corr and LS vs FF correlation.
- `run_time_effects(factors, fwd_returns, window=252, step=21)`: rolling IC/IC IR over time.
Use the notebooks to see the sequence; re-run analytics/correlations/rolling without recomputing factors.

## What’s inside
| Path | Purpose |
| --- | --- |
| `quantlab_factor_library/paths.py` | Resolve repo/data roots (configurable via `config/config.json`). |
| `quantlab_factor_library/data_loader.py` | Load long-format parquet, pivot to wide price/sector, compute forward returns; load FF factors. |
| `quantlab_factor_library/base.py` | `FactorBase` enforcing `compute_raw_factor` + `post_process`; shared cleaning via `compute`. |
| `quantlab_factor_library/factors/` | Parameterized starters: Momentum, Volatility, MeanReversion, DollarVolume. |
| `quantlab_factor_library/factor_definitions.py` | Single place to declare the default factor set; `run_factors` and demos import from here. |
| `quantlab_factor_library/transforms.py` | Coverage filter, winsorize, fill (median/sector-median), neutralize (sector/global), z-score, drop-all-NaN; `clean_factor` helper. |
| `quantlab_factor_library/analytics.py` | IC (Spearman), autocorr, decile monotonicity, LS diagnostic (Sharpe/max DD/mean/std), FF regression (alpha/betas + t-stats/p-values), factor correlation, diagnostics/registry writers. |
| `quantlab_factor_library/run_factors.py` | Runs default factors, saves outputs, updates analytics registry, writes correlations/FF time series; optional `parallel=True` (ThreadPool via `concurrent.futures`) to fan out per-factor computations. |
| `notebooks/factor_demo.ipynb` | End-to-end demo (load → compute → transparent pipeline → analytics → correlation → save factors/diagnostics). |
| `notebooks/factor_parallel_demo.ipynb` | Same as above with optional parallel run snippet. |
| `config/config.json` | Optional path overrides. |
| FF loader | `DataLoader.load_ff_factors()` reads `data/data-processed/FAMA_FRENCH_FACTORS.parquet` (mktrf, smb, hml, rmw, cma, rf, umd). |
| Note | FF regression uses lightweight OLS (numpy + scipy for p-values) to keep the pipeline lean. |

## Default factors (methodology)
- Momentum variants: 12-1m momentum; residual momentum (market-neutralized); efficiency ratio (path smoothness).
- Volatility/risks: volatility (60d), downside vol (60d), residual vol (252d) and idiosyncratic vol (60d), ATR (14d), return skew/kurtosis, downside beta (252d).
- Liquidity/flow: dollar volume (20d), Amihud illiquidity (20d, 252d) plus log variant, turnover, OBV, VWAP deviation (21d).
- Price action: mean reversion (5d), 52w high proximity, max daily return (21d), industry momentum (6–1m), coskewness (252d), Hurst exponent (252d).
- Value/quality: size (log mkt cap), earnings yield, book-to-price, EV/EBITDA inverse, cashflow yield, free cashflow yield, accruals, ROA, ROE/profitability, leverage, gross profitability, Piotroski F-score.
- Growth/investment: sales growth, sales growth acceleration (quarterly), asset growth, R&D intensity, investment-to-assets, net issuance (annual shares), net buyback yield (quarterly shares), dividend yield, dividend growth.
- Events/estimates: analyst revisions (30d), earnings surprise %, standardized unexpected earnings (SUE, quarterly only).
- Forensic/integrity: Benford chi-square D1/D2 on quarterly fundamentals.

## Outputs
- Factors: `../data/factors/factor_<name>.parquet` (long format: Date, Ticker, Value).
- Registry: `../data/factors/factor_analytics_summary.parquet` (mean IC, IC t-stat, IC IR, mean autocorr, decile spread, LS stats, FF alpha/betas).
- Diagnostics: `../data/factors/factor_step_diagnostics.parquet` (IC/IR, decile spreads, LS stats, FF betas/t-stats/p-values) and `../data/factors/factor_correlation.parquet`. Reference copies (parquet + CSV) are git-tracked at [`diagnostics/factor_step_diagnostics.parquet`](diagnostics/factor_step_diagnostics.parquet) and [`diagnostics/factor_step_diagnostics.csv`](diagnostics/factor_step_diagnostics.csv) for quick inspection in a browser.
- FF time series: `../data/factors/factor_ff_timeseries.parquet` for benchmarking/orthogonalization.

## Default cleaning/neutralization (used by `compute` and the notebook)
- Coverage filter (drop dates with <30% non-NaN coverage).
- Winsorize (1st/99th pct).
- Fill (cross-sectional median).
- Sector neutralization (fallback to global if sector map missing).
- Z-score cross-sectionally; drop all-NaN dates.

## Extending
- Build new factors by subclassing `FactorBase` or parameterizing existing classes (e.g., Momentum with different lookback/skip).
- Use FF factors for benchmarking/orthogonalization via `load_ff_factors()` and `regress_on_ff`.
