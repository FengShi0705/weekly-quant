import numpy as np
import pandas as pd

from wq import attention


def views(seed=0):
    days = pd.date_range("2015-07-01", "2017-12-31", freq="D")
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"A": rng.poisson(1000, len(days)).astype(float),
                         "B": rng.poisson(50, len(days)).astype(float)}, index=days)


def test_spike_shows_after_it_happens_and_not_before():
    v = views()
    v.loc["2017-03-06":"2017-03-09", "A"] = 20000.0              # Mon-Thu spike
    sig = pd.DatetimeIndex(["2017-03-03", "2017-03-10", "2017-05-26"])
    f = attention.features(v, sig)
    before, after, later = (f.loc[(d, "A"), "attn_1w"] for d in sig)
    assert abs(before) < 0.2                                     # nothing yet on Friday 3 Mar
    assert after > 2.0                                           # 4 of the last 5 days at 20x
    assert abs(later) < 0.2
    assert f.loc[(pd.Timestamp("2017-03-10"), "A"), "attn_level"] > f.loc[(pd.Timestamp("2017-03-10"), "B"), "attn_level"]


def test_features_ignore_the_signal_day_and_later():
    v = views()
    sig = pd.DatetimeIndex(["2017-06-02", "2017-06-09"])
    a = attention.features(v, sig)
    w = v.copy()
    w.loc["2017-06-02":] *= 50                                   # from the signal day on
    b = attention.features(w, sig)
    pd.testing.assert_series_equal(a.loc[pd.Timestamp("2017-06-02")]["attn_1w"], b.loc[pd.Timestamp("2017-06-02")]["attn_1w"])
    assert (b.loc[pd.Timestamp("2017-06-09")]["attn_1w"] > a.loc[pd.Timestamp("2017-06-09")]["attn_1w"] + 2).all()


def test_missing_until_a_year_of_views():
    f = attention.features(views(), pd.DatetimeIndex(["2016-03-04", "2016-09-02"]))
    assert pd.Timestamp("2016-03-04") not in f.index.get_level_values("date")
    assert f.loc[pd.Timestamp("2016-09-02")]["attn_1w"].notna().all()
