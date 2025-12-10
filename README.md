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

## Default factors (methodology)

| Category | Factors (concise methodology) |
| --- | --- |
| Momentum & trend | `momentum_12m` 12-1m return; `residual_momentum_12m` market-neutral momentum; `efficiency_ratio_252d` total return ÷ sum(|daily returns|); `industry_momentum` sector 6–1m return mapped to members; `max_daily_return_1m` 21d max daily return (lottery tilt); `high52w_proximity` price / 252d high − 1 |
| Reversal & path | `mean_reversion_5d` negative 5d return; `vwap_dev_21d` price vs 21d VWAP; `hurst_252d` Hurst exponent on 252d returns (trend vs mean-revert) |
| Volatility & tail | `volatility_60d` std of returns; `downside_vol_60d` std of negative returns; `residual_vol_252d` std of market residuals; `ivol_60d` short-window idio vol; `atr_14d` average true range; `skewness_60d`/`kurtosis_60d` rolling moments; `beta_252d` market beta; `downside_beta_252d` beta on down days; `coskewness_252d` beta to squared market returns |
| Liquidity/flow | `dollar_volume_20d` price×vol avg; `amihud_illiq_20d` / `amihud_illiq_log_20d` mean(|ret|/dollar vol); `amihud_illiq_252d` yearly window; `turnover` volume ÷ shares; `obv` cumulative signed volume |
| Value | `earnings_yield` TTM NI / mkt cap; `book_to_price` book equity per share / price; `ev_to_ebitda_inv` (price×shares + debt − cash) / EBITDA inverted; `cashflow_yield` op CF / mkt cap; `free_cashflow_yield` (op CF − capex) / mkt cap; `accruals` (NI − CFO) / assets |
| Quality/profitability | `size_log_mktcap` log(price×shares); `profitability_roe` NI/equity; `roa` NI/assets; `gross_profitability` gross profit/assets; `leverage` liabilities/assets |
| Growth/investment | `sales_growth` YoY revenue; `sales_growth_accel` QoQ YoY delta; `asset_growth` YoY assets; `investment_to_assets` Δ(PPE+inventory over 4q)/assets; `rd_intensity` R&D/revenue |
| Capital actions | `net_issuance` YoY share change (annual); `net_buyback_yield` negative 4q share growth; `dividend_yield_ttm` trailing 12m dividends/price; `dividend_growth` YoY dividend growth |
| Composite quality | `piotroski_fscore` 0–9 from profitability, leverage/liquidity, dilution, margins, turnover |
| Estimates/events | `analyst_revision_eps_30d` net EPS estimate revisions; `earnings_surprise` % surprise; `sue` standardized surprise over 8q std (quarterly) |
| Forensic/integrity | `benford_chi2_d1`, `benford_chi2_d2` chi-square distance to Benford digits on quarterly fundamentals (lower = cleaner) |

## Outputs
- Factors: `../data/factors/factor_<name>.parquet` (long format: Date, Ticker, Value).
- Registry: `../data/factors/factor_analytics_summary.parquet` (mean IC, IC t-stat, IC IR, mean autocorr, decile spread, LS stats, FF alpha/betas).
- Correlation: `../data/factors/factor_correlation.parquet` (and FF corr) with CSV mirrors in `diagnostics/` for quick inspection.
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
- FF regression uses lightweight OLS (numpy + scipy for p-values) to keep the pipeline lean.

## References
- Analytics registry (CSV): [`diagnostics/factor_analytics_summary.csv`](diagnostics/factor_analytics_summary.csv)
- Rolling analytics (CSV): [`diagnostics/factor_rolling_analytics.csv`](diagnostics/factor_rolling_analytics.csv)
- Correlation matrices (CSV): [`diagnostics/factor_correlation.csv`](diagnostics/factor_correlation.csv) and [`diagnostics/factor_ff_correlation.csv`](diagnostics/factor_ff_correlation.csv)
