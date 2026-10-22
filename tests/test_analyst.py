import numpy as np
import pandas as pd

from wq import analyst


def raw():
    ts = pd.to_datetime(["2020-03-02 14:00", "2020-03-10 15:00", "2020-03-13 13:00", "2020-03-20 09:00",
                         "2020-01-02 12:00"]).tz_localize("UTC")
    return pd.DataFrame({"ticker": ["A", "A", "A", "A", "A"], "ts": ts,
                         "action": ["up", "down", "up", "up", "down"],
                         "pt": [110.0, 90.0, 0.0, 120.0, 80.0], "pt_prior": [100.0, 100.0, 0.0, 100.0, 100.0]})


def test_counts_and_targets_use_only_earlier_days():
    sig = pd.DatetimeIndex(["2020-03-13", "2020-03-20", "2020-03-27"])
    f = analyst.features(raw(), sig)
    # 13 Mar: actions of 2 and 10 Mar (the 13 Mar one is same-day, so not yet known).
    a = f.loc[(pd.Timestamp("2020-03-13"), "A")]
    assert a["rev_net_4w"] == 0.0                                   # +1 - 1
    assert np.isclose(a["pt_rev_4w"], (np.log(1.1) + np.log(0.9)) / 2)
    assert a["rev_net_13w"] == -1.0                                 # plus January's downgrade
    # 20 Mar: adds 13 Mar's upgrade (no usable target); 20 Mar's is same-day again.
    b = f.loc[(pd.Timestamp("2020-03-20"), "A")]
    assert b["rev_net_4w"] == 1.0
    assert np.isclose(b["pt_rev_4w"], (np.log(1.1) + np.log(0.9)) / 2)
    c = f.loc[(pd.Timestamp("2020-03-27"), "A")]
    assert c["rev_net_4w"] == 2.0
    assert np.isclose(c["pt_rev_4w"], (np.log(1.1) + np.log(0.9) + np.log(1.2)) / 3)


def test_old_actions_drop_out_and_future_ones_are_ignored():
    sig = pd.DatetimeIndex(["2020-04-24", "2020-03-06"])
    f = analyst.features(raw(), sig)
    late = f.loc[(pd.Timestamp("2020-04-24"), "A")]
    assert late["rev_net_4w"] == 0.0 and np.isnan(late["pt_rev_4w"])   # nothing since 27 Mar
    assert late["rev_net_13w"] == 2.0                                   # January's has rolled off
    r2 = pd.concat([raw(), pd.DataFrame({"ticker": ["A"], "ts": pd.to_datetime(["2020-03-06 08:00"]).tz_localize("UTC"),
                                         "action": ["down"], "pt": [50.0], "pt_prior": [100.0]})])
    a = analyst.features(raw(), sig).loc[(pd.Timestamp("2020-03-06"), "A")]
    b = analyst.features(r2, sig).loc[(pd.Timestamp("2020-03-06"), "A")]
    pd.testing.assert_series_equal(a, b)
