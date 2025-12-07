from __future__ import annotations

import abc
from typing import Optional

import pandas as pd

from . import transforms


class FactorBase(abc.ABC):
    """
    Base class enforcing compute_raw_factor + post_process contract.
    """

    name: str = "factor_base"

    @abc.abstractmethod
    def compute_raw_factor(self, data_loader) -> pd.DataFrame:
        """Return a wide DataFrame (index=date, cols=tickers) of raw factor values."""

    @abc.abstractmethod
    def post_process(self, raw_factor: pd.DataFrame) -> pd.DataFrame:
        """Optional shifting/smoothing specific to the factor."""

    def compute(
        self,
        data_loader,
        sector_map: Optional[pd.Series] = None,
        winsor_limits: tuple[float, float] = (0.01, 0.99),
        min_coverage: float = 0.3,
        fill_method: str = "median",
        neutralize_method: str = "sector",
    ) -> pd.DataFrame:
        raw = self.compute_raw_factor(data_loader)
        post = self.post_process(raw)
        cleaned = transforms.clean_factor(
            post,
            sector_map=sector_map,
            winsor_limits=winsor_limits,
            min_coverage=min_coverage,
            fill_method=fill_method,
            neutralize_method=neutralize_method,
        )
        return cleaned
