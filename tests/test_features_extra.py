import numpy as np
import pandas as pd

from tests.conftest import make_market
from wq import features_extra as fe
from wq.backtest import prepare
from wq.features import weekly_calendar


def inputs(close, volume, fx, universe, cfg):
    _, cal, px = prepare(cfg, close, volume, fx, universe)
    rng = np.random.default_rng(3)
    div = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    for t in close.columns[::2]:                              # half the stocks pay twice a year
        for d in pd.date_range("2011-03-15", "2019-12-31", freq="182D"):
            div.loc[div.index[div.index.searchsorted(d)], t] = 0.01 + rng.uniform(0, 0.01)
    ts = [pd.Timestamp(d, tz="UTC") for d in pd.date_range("2011-02-01 21:00", "2019-12-31", freq="91D")]
    earn = pd.DataFrame({"ticker": close.columns[0], "ts": ts, "surprise": 1.0})
    return px, div, earn, cal


def test_every_set_ignores_the_future(cfg):
    close, volume, fx, universe = make_market(n=24, seed=4)
    px, div, earn, cal = inputs(close, volume, fx, universe, cfg)
    cut = cal.index[300]
    shocked = close.copy()
    after = shocked.index > cut
    shocked.loc[after] *= np.random.default_rng(9).uniform(0.5, 2.0, size=(after.sum(), close.shape[1]))
    vol2 = volume.copy()
    vol2.loc[after] *= 7
    px2, _, _, _ = inputs(shocked, vol2, fx, universe, cfg)
    div2 = div.copy()
    div2.loc[after] = 0.05                                    # dividends after the cut change
    earn2 = pd.concat([earn, pd.DataFrame({"ticker": [close.columns[1]], "ts": [pd.Timestamp(cut, tz="UTC") + pd.Timedelta(days=2)],
                                           "surprise": [5.0]})])
    sig = cal.index[:301]
    a = fe.build("all", px, close, volume, universe, div, earn, sig)
    b = fe.build("all", px2, shocked, vol2, universe, div2, earn2, sig)
    pd.testing.assert_frame_equal(a, b)
    assert a.drop(columns="earn_next_1w").notna().mean().min() > 0.4      # every feature is populated
    covered = a.xs(close.columns[0], level="ticker")["earn_next_1w"]       # the one stock with earnings dates
    assert covered.notna().mean() > 0.9 and covered.sum() > 10


def test_information_discreteness_and_peer_returns(cfg):
    idx = pd.bdate_range("2015-01-01", periods=300)
    smooth = pd.Series(100 * 1.002 ** np.arange(300), index=idx)          # 0.2% every day
    jumpy = pd.Series(100.0, index=idx)
    jumpy.iloc[100:] = 100 * 1.002 ** 200                                 # one jump, same total
    px = pd.DataFrame({"A": smooth, "B": jumpy})
    sig = pd.DatetimeIndex([idx[-1]])
    f = fe.shape(px, pd.DataFrame(1.0, index=idx, columns=px.columns), sig)
    i = f["info_disc"].loc[idx[-1]]
    assert np.isclose(i["A"], -1.0)                           # all up days: continuous information
    assert i["B"] > -0.05                                     # one big day: discrete
    uni = pd.DataFrame({"sector": ["X", "X"], "country": ["US", "US"]}, index=["A", "B"])
    p = fe.peer(px, uni)
    assert np.allclose(p["sec_rel_1m"].iloc[-1].sum(), 0.0)  # relative returns net out within a sector


def test_expected_earnings_and_dividend_flags():
    sig = pd.DatetimeIndex(["2020-04-24", "2020-05-01", "2020-05-08"])
    # last year's announcement on 2019-04-30: projected 2020-04-28, inside next week of 24 Apr only
    f = fe._expected_flag(pd.DatetimeIndex(["2019-04-30"]), sig, (364,), -3, 10)
    assert list(f) == [1.0, 0.0, 0.0]                         # 1 May's window starts on 29 Apr
    g = fe._expected_flag(pd.DatetimeIndex(["2019-05-20"]), sig, (364,), 0, 28)
    assert list(g) == [1.0, 1.0, 1.0]


def test_seasonality_uses_complete_past_months_only():
    idx = pd.bdate_range("2014-01-01", "2020-06-30")
    r = pd.Series(0.0, index=idx)
    r[idx.month == 3] = 0.01                                  # every March is strong
    px = pd.DataFrame({"A": 100 * (1 + r).cumprod()})
    s = fe._seasonality(px, pd.DatetimeIndex(["2020-02-28", "2020-06-26"]))
    assert s.loc["2020-02-28", "A"] > 0.15                    # coming month March: past Marches
    assert abs(s.loc["2020-06-26", "A"]) < 1e-9               # coming month July: flat
