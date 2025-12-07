from __future__ import annotations

from typing import List

from .factors import MeanReversion, Momentum, Volatility, DollarVolume


def get_default_factors() -> List:
    """
    Central place to declare the default factor set used by run_factors and demos.
    Modify or extend this list to add/remove factors without changing runner code.
    """
    return [
        Momentum(lookback_days=252, skip_days=21, name="momentum_12m"),
        Volatility(window=60, name="volatility_60d"),
        MeanReversion(lookback_days=5, name="mean_reversion_5d"),
        DollarVolume(window=20, name="dollar_volume_20d"),
    ]
