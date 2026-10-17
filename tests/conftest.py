"""Synthetic markets for testing the pipeline's mechanics. These are not market data."""
import copy

import numpy as np
import pandas as pd
import pytest

from wq.config import load_config

COUNTRIES = [("US", "US", "USD", ""), ("UK", "UK", "GBp", ".L"), ("DE", "EU", "EUR", ".DE")]


def make_market(n=60, start="2011-01-03", end="2019-12-31", drift_dispersion=0.0, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start, end)
    rows, closes = [], {}
    mu = rng.normal(0, drift_dispersion / 252, n)
    for i in range(n):
        country, region, ccy, suffix = COUNTRIES[i % 3]
        t = f"S{i:03d}{suffix}"
        rows.append({"ticker": t, "name": t, "country": country, "sector": f"Sec{i % 6}", "region": region,
                     "currency": ccy,
                     "lot_size": 1, "brokers": "t212|ibkr"})
        r = mu[i] + rng.normal(0, 0.25 / np.sqrt(252), len(idx))
        p = 100 * np.exp(np.cumsum(r))
        closes[t] = p * (100 if ccy == "GBp" else 1)
    close = pd.DataFrame(closes, index=idx)
    volume = pd.DataFrame(1e6, index=idx, columns=close.columns)
    fx = pd.DataFrame({"GBP": 1.3 * np.exp(np.cumsum(rng.normal(0, 0.005, len(idx)))),
                       "EUR": 1.15 * np.exp(np.cumsum(rng.normal(0, 0.005, len(idx))))}, index=idx)
    universe = pd.DataFrame(rows).set_index("ticker")
    return close, volume, fx, universe


@pytest.fixture
def cfg():
    c = copy.deepcopy(load_config("config.yaml"))
    c["model"]["lgbm"]["n_estimators"] = 60
    c["model"]["n_seeds"] = 1
    c["model"]["retrain_every_weeks"] = 8
    c["backtest"]["start"] = "2015-06-01"
    c["universe"]["regions"] = ["US", "UK", "EU"]
    return c


@pytest.fixture(scope="session")
def noise_market():
    return make_market(drift_dispersion=0.0, seed=1)


@pytest.fixture(scope="session")
def signal_market():
    return make_market(drift_dispersion=0.3, seed=2)
