# QuantLab Factor Library

Factor research toolkit that consumes the cleaned Parquet outputs from the data pipeline (`../data/data-processed/*.parquet`) and writes factor signals/analytics to `../data/factors/`. The library ships the factor template, loaders, transforms, analytics, and a worked notebook.

## Layout
- `quantlab_factor_library/paths.py` – resolves repo and external data roots (overridable via `config/config.json`).
- `quantlab_factor_library/data_loader.py` – loads long-format Parquets and pivots to wide price/sector frames; computes forward returns.
- `quantlab_factor_library/base.py` – `FactorBase` ABC enforcing `compute_raw_factor` and `post_process`; shared cleaning via `compute`.
- `quantlab_factor_library/factors/` – starter factors: parameterized Momentum, Volatility, MeanReversion, DollarVolume (liquidity). Instantiate with your lookbacks/windows; `name` can be set explicitly.
- `quantlab_factor_library/transforms.py` – coverage filtering, winsorize, fill (median/sector-median), sector/global neutralize, z-score, drop-all-NaN; also a `clean_factor` helper.
- `quantlab_factor_library/analytics.py` – IC (Spearman, factor rank vs forward-return rank), factor autocorr (lag-1 cross-sectional rank persistence), decile monotonicity, registry updater, step diagnostics saver, factor correlation matrix saver, long-short return builder, FF regression helper.
- `quantlab_factor_library/run_factors.py` – example entrypoint to run the default factor set, save outputs, update analytics registry, and write factor correlation.
- `config/config.json` – optional overrides for `data_root`, `final_dir`, and `factors_dir` (defaults to `../data/*`).
- `notebooks/factor_demo.ipynb` – end-to-end example (load → compute via `compute()` → transparent pipeline → analytics → correlation → save factors/diagnostics).
- Fama-French loader: `DataLoader.load_ff_factors()` reads `data/data-processed/FAMA_FRENCH_FACTORS.parquet` (mktrf, smb, hml, rmw, cma, rf, umd).
- FF regression uses a lightweight OLS (numpy + scipy for p-values) to keep the pipeline lean and fast, instead of pulling in heavier stats packages.

## Usage
```bash
cd quantlab_factor_library
python -m quantlab_factor_library.run_factors
```

Example walkthrough: see `notebooks/factor_demo.ipynb` for loading data, computing factors, running analytics, factor correlation, and saving outputs/diagnostics.

Outputs
- Factor files: `../data/factors/factor_<name>.parquet` with columns `Date`, `Ticker`, `Value`.
- Registry: `../data/factors/factor_analytics_summary.parquet` capturing mean IC, IC t-stat, IC IR (mean IC / IC std), mean autocorr, and decile spread per factor.
- Diagnostics: `../data/factors/factor_step_diagnostics.parquet` (step-level stats) and `../data/factors/factor_correlation.parquet` (factor-to-factor correlation matrix).
- FF factors: `../data/factors/factor_ff_timeseries.parquet` (saved from `load_ff_factors`) for benchmarking/orthogonalization.
- FF benchmarking: use `long_short_returns` + `regress_on_ff` to build factor PnL and regress against FF factors (loaded via `load_ff_factors`).

Default cleaning/neutralization (in `compute` and notebook standard path)
- Coverage filter (drop dates with <30% non-NaN coverage).
- Winsorize (1st/99th pct).
- Fill (cross-sectional median).
- Sector neutralization (using `company_overview` Sector map if available).
- Z-score cross-sectionally, drop all-NaN dates.

Standard vs custom factors
- Custom cross-sectional factors are built via `FactorBase` subclasses (Momentum/Volatility/MeanReversion/DollarVolume).
- Standard Fama-French time-series factors can be loaded via `DataLoader.load_ff_factors()` for benchmarking/orthogonalization alongside custom factors.
