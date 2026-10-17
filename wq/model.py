"""Walk-forward model: LightGBM ranker-by-regression blended with a transparent momentum baseline."""
import numpy as np
import pandas as pd

from .features import FEATURES


def baseline_score(df):
    """12-1 and 6-1 momentum with a low-volatility tilt. Inputs are already ranks in [-0.5, 0.5]."""
    return 0.5 * df["mom_12_1"].fillna(0) + 0.3 * df["mom_6_1"].fillna(0) - 0.2 * df["vol_60"].fillna(0)


def train_slice(panel, pred_week, cfg):
    """Rows whose labels were fully realised before the signal date of `pred_week`.

    A label for week t ends at exec(t + h), the trading day after signal(t + h), so it is
    known at signal(T) only if t + h <= T - 1.
    """
    m = cfg["model"]
    hi = pred_week - m["label_horizon_weeks"] - 1
    lo = hi - m["train_window_weeks"] + 1
    wk = panel["week"]
    return panel[(wk >= lo) & (wk <= hi) & panel["label"].notna()]


def fit(train, cfg, seed=0):
    import lightgbm as lgb

    params = dict(cfg["model"]["lgbm"])
    rounds = params.pop("n_estimators")
    params.update(objective="regression", seed=seed, deterministic=True, num_threads=0)
    return lgb.train(params, lgb.Dataset(train[FEATURES], train["label"]), num_boost_round=rounds)


def _rank(s):
    return s.rank(pct=True) - 0.5


def walk_forward(panel, cfg, pred_dates, retrain_every=None, verbose=True, return_model=False):
    """Score every stock on each prediction date using only information available at that date.

    Returns a DataFrame indexed by (date, ticker) with columns ml, baseline, score
    (and the last fitted model if return_model).
    """
    m = cfg["model"]
    retrain_every = retrain_every or m["retrain_every_weeks"]
    w_ml = m["ml_weight"]
    weeks = panel.groupby(level="date")["week"].first()
    model, last_fit, out = None, -10**9, []
    for T in pred_dates:
        if T not in weeks.index:
            continue
        iT = int(weeks.loc[T])
        if model is None or iT - last_fit >= retrain_every:
            train = train_slice(panel, iT, cfg)
            if train["week"].nunique() >= m["min_train_weeks"]:
                model, last_fit = fit(train, cfg), iT
                if verbose:
                    print(f"  fit {T.date()}: {len(train):,} rows, {train['week'].nunique()} weeks")
        X = panel.xs(T, level="date", drop_level=False)
        base = baseline_score(X)
        ml = pd.Series(model.predict(X[FEATURES]), index=X.index) if model is not None else pd.Series(np.nan, index=X.index)
        score = _rank(base) if model is None else w_ml * _rank(ml) + (1 - w_ml) * _rank(base)
        out.append(pd.DataFrame({"ml": ml, "baseline": base, "score": score}))
    scores = pd.concat(out) if out else pd.DataFrame(columns=["ml", "baseline", "score"])
    return (scores, model) if return_model else scores


def information_coefficients(scores, panel):
    """Weekly Spearman correlation between each score and the next week's return."""
    df = scores.join(panel[["fwd_ret_1w"]]).dropna(subset=["fwd_ret_1w"])
    rows = {}
    for d, g in df.groupby(level="date"):
        if len(g) < 10:
            continue
        r = g["fwd_ret_1w"].rank()
        rows[d] = {c: g[c].rank().corr(r) for c in ["ml", "baseline", "score"] if g[c].notna().any()}
    return pd.DataFrame.from_dict(rows, orient="index")


def feature_importance(model):
    return pd.Series(model.feature_importance("gain"), index=FEATURES).sort_values(ascending=False)
