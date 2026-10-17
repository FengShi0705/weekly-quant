"""Walk-forward model: LightGBM ranker-by-regression blended with a transparent momentum baseline."""
import numpy as np
import pandas as pd

from .features import feature_list


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


class RidgeModel:
    """Linear model on the ranked features, for checking whether the trees add anything."""

    def __init__(self, features, alpha):
        self.features, self.alpha = list(features), alpha

    def fit(self, X, y):
        A = np.nan_to_num(X.to_numpy(dtype=float))  # ranks are centred, so 0 = median
        self.coef = np.linalg.solve(A.T @ A + self.alpha * np.eye(A.shape[1]), A.T @ y.to_numpy(dtype=float))
        return self

    def predict(self, X):
        return np.nan_to_num(np.asarray(X, dtype=float)) @ self.coef

    def feature_name(self):
        return self.features

    def feature_importance(self, kind="gain"):
        return np.abs(self.coef)


def fit(train, cfg, seed=0):
    """Train an ensemble of n_seeds LightGBM models that differ only in their random seed.

    With 15 positions, one model's random choices can change a pick and every trade after it;
    averaging several seeds keeps that luck out of the portfolio.
    """
    features = feature_list(cfg)
    if cfg["model"].get("type", "lgbm") == "ridge":
        return [RidgeModel(features, cfg["model"]["ridge_alpha"]).fit(train[features], train["label"])]
    import lightgbm as lgb

    params = dict(cfg["model"]["lgbm"])
    rounds = params.pop("n_estimators")
    params.update(objective="regression", deterministic=True, num_threads=0)
    data = lgb.Dataset(train[features], train["label"], free_raw_data=False)
    return [lgb.train({**params, "seed": seed + i}, data, num_boost_round=rounds)
            for i in range(cfg["model"]["n_seeds"])]


def predict(models, X):
    return np.mean([m.predict(X[m.feature_name()]) for m in models], axis=0)


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
        ml = pd.Series(predict(model, X) if model is not None else np.nan, index=X.index)
        score = _rank(base) if model is None else w_ml * _rank(ml) + (1 - w_ml) * _rank(base)
        out.append(pd.DataFrame({"ml": ml, "baseline": base, "score": score}))
    scores = pd.concat(out) if out else pd.DataFrame(columns=["ml", "baseline", "score"])
    return (scores, model) if return_model else scores


def smooth_scores(scores, weeks):
    """Average each stock's scores over its last `weeks` signal dates (past only) to cut turnover."""
    if weeks <= 1:
        return scores
    return scores.groupby(level="ticker", group_keys=False).transform(
        lambda x: x.rolling(weeks, min_periods=1).mean())


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


def feature_importance(models):
    gain = np.mean([m.feature_importance("gain") for m in models], axis=0)
    return pd.Series(gain, index=models[0].feature_name()).sort_values(ascending=False)
