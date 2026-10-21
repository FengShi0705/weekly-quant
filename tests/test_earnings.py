import numpy as np
import pandas as pd

from wq import earnings
from wq.features import daily_calendar, weekly_calendar

DAYS = pd.bdate_range("2020-01-01", "2020-12-31")


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def test_reaction_day_follows_the_announcement_time():
    # Tue 2020-03-03: before 14:00 UTC (European morning, US pre-market) moves that day's close;
    # a US after-close release moves the next day's; a date-only row (midnight UTC) counts that day.
    assert earnings.reaction_day(ts("2020-03-03 06:00"), DAYS) == pd.Timestamp("2020-03-03")
    assert earnings.reaction_day(ts("2020-03-03 11:30"), DAYS) == pd.Timestamp("2020-03-03")
    assert earnings.reaction_day(ts("2020-03-03 21:00"), DAYS) == pd.Timestamp("2020-03-04")
    assert earnings.reaction_day(ts("2020-03-03 00:00"), DAYS) == pd.Timestamp("2020-03-03")
    # Friday after the close, and a Saturday release, both land on Monday.
    assert earnings.reaction_day(ts("2020-03-06 21:00"), DAYS) == pd.Timestamp("2020-03-09")
    assert earnings.reaction_day(ts("2020-03-07 10:00"), DAYS) == pd.Timestamp("2020-03-09")


def _market(seed=0):
    rng = np.random.default_rng(seed)
    px = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.01, (len(DAYS), 3)), axis=0)),
                      index=DAYS, columns=["A", "B", "C"])
    raw = pd.DataFrame({"ticker": ["A", "A", "B", "A"],
                        "ts": [ts("2020-02-04 21:00"), ts("2020-05-05 21:00"), ts("2020-03-10 06:00"), ts("2020-11-01 21:00")],
                        "surprise": [12.0, -3.0, 250.0, np.nan]})
    return px, raw


def test_ear_is_the_market_adjusted_three_close_return():
    px, raw = _market()
    sig = weekly_calendar(DAYS).index
    f = earnings.features(raw, px, sig)
    # A's release after the close on 4 Feb reacts on 5 Feb; the window is 4 Feb close -> 6 Feb close,
    # first known at the 6 Feb close, so it first shows on Friday 7 Feb.
    mkt = (1 + px.pct_change().mean(axis=1).fillna(0)).cumprod()
    a, b = pd.Timestamp("2020-02-04"), pd.Timestamp("2020-02-06")
    want = (px.loc[b, "A"] / px.loc[a, "A"] - 1) - (mkt[b] / mkt[a] - 1)
    assert (pd.Timestamp("2020-01-31"), "A") not in f.index or np.isnan(f.loc[(pd.Timestamp("2020-01-31"), "A"), "ear"])
    got = f.loc[(pd.Timestamp("2020-02-07"), "A")]
    assert np.isclose(got["ear"], want)
    assert np.isclose(got["sue"], np.log1p(12.0))
    assert np.isclose(got["earn_age"], 2 / earnings.WINDOW)            # 5 Feb -> 7 Feb
    # B's surprise is clipped at 100; past 65 trading days an announcement no longer counts.
    assert np.isclose(f.loc[(pd.Timestamp("2020-03-13"), "B"), "sue"], np.log1p(100.0))
    assert np.isnan(f.loc[(pd.Timestamp("2020-07-31"), "B"), "ear"])


def test_features_ignore_the_future():
    px, raw = _market()
    sig = daily_calendar(DAYS).index
    cut = pd.Timestamp("2020-05-06")                     # A's May window (5-7 May) is not complete yet
    f = earnings.features(raw, px, sig)
    shocked = px.copy()
    shocked.loc[shocked.index > cut] *= np.random.default_rng(1).uniform(0.5, 2.0, (int((shocked.index > cut).sum()), 3))
    raw2 = pd.concat([raw, pd.DataFrame({"ticker": ["C"], "ts": [ts("2020-05-07 06:00")], "surprise": [5.0]})])
    g = earnings.features(raw2, shocked, sig)
    a = f[f.index.get_level_values("date") <= cut]
    b = g[g.index.get_level_values("date") <= cut].reindex(a.index)
    pd.testing.assert_frame_equal(a, b)
    # Still February's announcement for A until the May window closes on 7 May.
    assert np.isclose(f.loc[(cut, "A"), "sue"], np.log1p(12.0))
    assert np.isclose(f.loc[(pd.Timestamp("2020-05-07"), "A"), "sue"], -np.log1p(3.0))
