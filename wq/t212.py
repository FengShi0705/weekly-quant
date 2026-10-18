"""Mirror a paper strategy's orders in a Trading 212 *Practice* account through the public API.

Only the Practice (demo) server is reachable from this module; it cannot place real-money orders.
Credentials: either a network secret on the cloud environment (username = API key, password = API
secret, for demo.trading212.com), which the proxy adds to each request so the key never enters the
session; or the T212_API_KEY and T212_API_SECRET environment variables.

Each week's orders are planned from what the Practice account actually holds (positions and cash from
the API), with the mirrored strategy's settings, so any drift from the simulated ledger is corrected by
the strategy's normal rules at the next weekly run. The simulated ledger itself is never adjusted.

State is kept in paper/t212_practice/:
  pending_orders.csv  this week's orders, planned from the real account
  orders_placed.csv   every order sent (or skipped), with the Trading 212 order id
  fills.csv           the fills Trading 212 reported for those orders, with each fee by name
  account.csv         account value per run
  comparison.md/.csv  real fills and account value next to the simulated ledger
"""
import base64
import math
import os
import re
import time
from datetime import date

import pandas as pd
import requests
import yaml

from . import paper, weekly
from .costs import trade_cost
from .data import to_base

DEMO = "https://demo.trading212.com/api/v0"
YAHOO_SUFFIX = re.compile(r"\.(L|DE|PA|AS|MC|MI|SW|CO|ST|HE|TO|T|HK)$")
T212_CCY = {"GBp": "GBX"}
PRECISION_ERROR = re.compile(r"quantity-precision-mismatch.*?invalid quantity precision (\d+)", re.S)


class Client:
    def __init__(self, key=None, secret=None, http=None, pause=1.3):
        key = key or os.environ.get("T212_API_KEY")
        secret = secret or os.environ.get("T212_API_SECRET")
        if bool(key) != bool(secret):
            raise RuntimeError("Set both T212_API_KEY and T212_API_SECRET, or neither (to use a network secret).")
        self.http = http or requests.Session()
        self.headers = {"Content-Type": "application/json"}
        if key:
            self.headers["Authorization"] = "Basic " + base64.b64encode(f"{key}:{secret}".encode()).decode()
        self.pause = pause

    def _call(self, method, path, **kw):
        url = DEMO + path
        assert url.startswith(DEMO), "only the Practice (demo) server is allowed"
        for attempt in range(4):
            r = self.http.request(method, url, headers=self.headers, timeout=30, **kw)
            if r.status_code != 429:
                break
            time.sleep(10 * (attempt + 1))
        if r.status_code in (401, 403):
            raise RuntimeError(f"{method} {path} -> HTTP {r.status_code}: Trading 212 rejected the credentials. "
                               "Add Practice API keys as a network secret for demo.trading212.com "
                               "(username = API key, password = API secret) or as T212_API_KEY/T212_API_SECRET.")
        if r.status_code >= 400:
            raise RuntimeError(f"{method} {path} -> HTTP {r.status_code}: {r.text[:300]}")
        return r.json()

    def instruments(self):
        # Rate limit is 1 request per 50 s, so fetch once per client.
        if getattr(self, "_instruments", None) is None:
            self._instruments = self._call("GET", "/equity/metadata/instruments")
        return self._instruments

    def positions(self):
        return self._call("GET", "/equity/positions")

    def summary(self):
        return self._call("GET", "/equity/account/summary")

    def pending_orders(self):
        return self._call("GET", "/equity/orders")

    def market_order(self, ticker, quantity):
        # Not idempotent: never retry this call automatically.
        r = self.http.request("POST", DEMO + "/equity/orders/market", headers=self.headers, timeout=30,
                              json={"ticker": ticker, "quantity": quantity, "extendedHours": False})
        time.sleep(self.pause)
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
        return r.json()

    def order_history(self, max_pages=10):
        items, cursor = [], None
        for _ in range(max_pages):
            page = self._call("GET", "/equity/history/orders", params={"limit": 50, **({"cursor": cursor} if cursor else {})})
            items += page.get("items", [])
            nxt = page.get("nextPagePath")
            if not nxt:
                break
            cursor = dict(p.split("=") for p in nxt.split("?", 1)[1].split("&")).get("cursor")
            time.sleep(3.1)
        return items


def map_tickers(universe, instruments, overrides=None):
    """Yahoo ticker -> Trading 212 ticker, matched on symbol and currency. Returns (mapping, problems)."""
    overrides = overrides or {}
    inst = pd.DataFrame(instruments)
    inst = inst[inst["type"] == "STOCK"]
    mapping, problems = {}, {}
    for t, row in universe.iterrows():
        if t in overrides:
            mapping[t] = overrides[t]
            continue
        symbol = YAHOO_SUFFIX.sub("", t).replace("-", ".")
        ccy = T212_CCY.get(row["currency"], row["currency"])
        hits = inst[(inst["shortName"] == symbol) & (inst["currencyCode"] == ccy)]
        if len(hits) == 1:
            mapping[t] = hits["ticker"].iloc[0]
        else:
            problems[t] = f"{len(hits)} matches for {symbol} in {ccy}"
    return mapping, problems


def _state_dir(spec_path):
    d = spec_path.parent / "t212_practice"
    d.mkdir(parents=True, exist_ok=True)
    return d


def sync(client, spec_path):
    """Record fills for orders we placed, and this week's account value."""
    d = _state_dir(spec_path)
    placed_path = d / "orders_placed.csv"
    if placed_path.exists():
        placed = pd.read_csv(placed_path)
        ids = set(placed["order_id"].dropna().astype(int))
        done = set(pd.read_csv(d / "fills.csv")["order_id"]) if (d / "fills.csv").exists() else set()
        rows = []
        for it in client.order_history():
            o, f = it.get("order", {}), it.get("fill") or {}
            if o.get("id") in ids and o.get("id") not in done and f:
                w = f.get("walletImpact", {})
                fees = w.get("taxes", []) or []
                rows.append({"order_id": o["id"], "ticker": o["instrument"]["ticker"], "side": o.get("side"),
                             "filled_at": f.get("filledAt"), "quantity": f.get("quantity"), "price": f.get("price"),
                             "instrument_ccy": o["instrument"].get("currency"), "fx_rate": w.get("fxRate"),
                             "net_value": w.get("netValue"), "account_ccy": w.get("currency"),
                             "fees": sum(abs(x.get("quantity", 0)) for x in fees),
                             "fees_detail": ";".join(f"{x.get('name')}:{x.get('quantity')}" for x in fees)})
        if rows:
            new = pd.DataFrame(rows)
            if (d / "fills.csv").exists():
                new = pd.concat([pd.read_csv(d / "fills.csv"), new], ignore_index=True)
            new.to_csv(d / "fills.csv", index=False)
        print(f"  synced {len(rows)} new fills from Trading 212")
    s = client.summary()
    row = pd.DataFrame([{"date": date.today(), "total_value": s.get("totalValue"),
                         "cash": (s.get("cash") or {}).get("availableToTrade"),
                         "invested_value": (s.get("investments") or {}).get("currentValue"),
                         "currency": s.get("currency")}])
    path = d / "account.csv"
    if path.exists():
        old = pd.read_csv(path)
        row = pd.concat([old[old["date"].astype(str) != str(date.today())], row], ignore_index=True)
    row.to_csv(path, index=False)
    print(f"  Practice account value {s.get('totalValue')} {s.get('currency')}")


def _position_ticker(p):
    return p.get("ticker") or (p.get("instrument") or {}).get("ticker")


def account_holdings(client, universe, overrides=None):
    """The Practice account's positions as {yahoo_ticker: shares}, its free cash, and anything unmapped."""
    mapping, _ = map_tickers(universe, client.instruments(), overrides)
    to_yahoo = {v: k for k, v in mapping.items()}
    shares, unmanaged = {}, {}
    for p in client.positions():
        tk, qty = _position_ticker(p), float(p.get("quantity", 0))
        if tk in to_yahoo:
            shares[to_yahoo[tk]] = qty
        elif qty:
            unmanaged[tk] = qty
    cash = float((client.summary().get("cash") or {}).get("availableToTrade", 0.0))
    return shares, cash, unmanaged


def plan_from_account(client, cfg, spec_path, close_local, volume, fx_usd, universe):
    """Plan this week's orders from what the Practice account actually holds.

    Uses the mirrored strategy's settings and score history, so the scores are the ones the simulated
    ledger traded on; only the holdings and cash differ. Writes paper/t212_practice/pending_orders.csv.
    """
    spec = yaml.safe_load(spec_path.read_text())
    strategy = spec.get("t212_practice")
    if not strategy:
        print("  no strategy is set to mirror in Trading 212 (t212_practice in strategies.yaml)")
        return None
    if client.pending_orders():
        print("  the Practice account still has open orders; not planning new ones until they fill or are cancelled")
        return None
    d = _state_dir(spec_path)
    c = paper.strategy_configs(cfg, spec_path)[strategy]
    c["paths"]["reports"] = d / "reports"
    c["paper_dir"] = d
    overrides_path = spec_path.parent / "t212_overrides.yaml"
    overrides = yaml.safe_load(overrides_path.read_text()) if overrides_path.exists() else {}
    shares, cash, unmanaged = account_holdings(client, universe, overrides)
    if unmanaged:
        print(f"  positions outside the strategy universe, left alone: {unmanaged}")
    print(f"  planning from the Practice account: {len(shares)} positions, {cash:,.2f} free cash")
    result = weekly.plan(c, close_local, volume, fx_usd, universe, shares, cash)
    pending = d / "pending_orders.csv"
    if pending.exists():
        pending.unlink()
    paper.save_pending(c, result)
    return result


def _send(client, ticker, qty):
    """Send one market order; returns (order_id, quantity sent, status).

    Instruments allow different numbers of decimals. If Trading 212 rejects the quantity's precision
    (HTTP 400, so no order was created), resend once, truncated to the precision it reports.
    """
    try:
        return client.market_order(ticker, qty).get("id"), qty, "sent"
    except RuntimeError as e:
        m = PRECISION_ERROR.search(str(e))
        if not m:
            return None, qty, f"error: {e}"
        n = int(m.group(1))
        cut = math.trunc(qty * 10 ** n) / 10 ** n
        if cut == 0:
            return None, qty, f"error: {e}"
        try:
            return client.market_order(ticker, cut).get("id"), cut, "sent"
        except RuntimeError as e2:
            return None, cut, f"error: {e2}"


def _resend_rejected(client, placed_path, signal, execute):
    """Resend this week's orders that Trading 212 explicitly rejected (HTTP 400, no order id).

    A 400 means no order was created, so resending can't duplicate one. Tickers that already have an
    open order are skipped as a further guard.
    """
    placed = pd.read_csv(placed_path)
    rejected = ((placed["signal_date"].astype(str) == signal) & placed["order_id"].isna()
                & placed["status"].astype(str).str.startswith("error: HTTP 400"))
    if not rejected.any():
        print(f"  no rejected orders for signal {signal} to resend")
        return []
    open_tickers = {_position_ticker(o) for o in client.pending_orders()}
    rows = []
    for i in placed.index[rejected]:
        tk, qty = placed.at[i, "t212_ticker"], float(placed.at[i, "quantity"])
        if tk in open_tickers:
            status, oid = "skipped: an open order already exists", None
        elif not execute:
            status, oid = "dry run (resend)", None
        else:
            oid, qty, status = _send(client, tk, qty)
            placed.loc[i, ["order_id", "quantity", "sent_on"]] = [oid, qty, str(date.today())]
        if execute:
            placed.loc[i, "status"] = status
        rows.append({"ticker": placed.at[i, "ticker"], "t212_ticker": tk, "quantity": qty, "status": status})
    print(pd.DataFrame(rows).to_string(index=False))
    if execute:
        placed.to_csv(placed_path, index=False)
    return rows


def place(client, spec_path, universe, execute=False, retry_rejected=False):
    """Send this week's planned orders (paper/t212_practice/pending_orders.csv) to the Practice account,
    sells first.

    Each week's orders are sent once. With retry_rejected, only the latest week's orders that
    Trading 212 explicitly rejected are sent again.
    """
    d = _state_dir(spec_path)
    placed_path = d / "orders_placed.csv"
    if retry_rejected:
        if not placed_path.exists():
            print("  no orders have been sent yet")
            return []
        signal = str(pd.read_csv(placed_path)["signal_date"].astype(str).max())
        return _resend_rejected(client, placed_path, signal, execute)
    pending_path = d / "pending_orders.csv"
    if not pending_path.exists():
        print("  no orders planned for the Practice account this week")
        return []
    pending = pd.read_csv(pending_path)
    signal = str(pending["signal_date"].iloc[0])
    if placed_path.exists() and signal in set(pd.read_csv(placed_path)["signal_date"].astype(str)):
        print(f"  orders for signal {signal} were already sent; not sending again")
        return []

    overrides_path = spec_path.parent / "t212_overrides.yaml"
    overrides = yaml.safe_load(overrides_path.read_text()) if overrides_path.exists() else {}
    mapping, problems = map_tickers(universe.loc[universe.index.isin(pending["ticker"])], client.instruments(),
                                    overrides)
    held = {_position_ticker(p): float(p["quantity"]) for p in client.positions()}

    rows = []
    for o in sorted(pending.itertuples(), key=lambda o: o.side != "sell"):
        tk = mapping.get(o.ticker)
        qty = round(float(o.shares), 4)
        if o.side == "sell":
            qty = -min(qty, held.get(tk, 0.0))
        row = {"signal_date": signal, "sent_on": date.today(), "ticker": o.ticker, "t212_ticker": tk,
               "quantity": qty, "order_id": None, "status": None}
        if tk is None:
            row["status"] = f"skipped: {problems.get(o.ticker, 'not mapped')}"
        elif qty == 0:
            row["status"] = "skipped: nothing held to sell"
        elif not execute:
            row["status"] = "dry run"
        else:
            row["order_id"], row["quantity"], row["status"] = _send(client, tk, qty)
        rows.append(row)
    df = pd.DataFrame(rows)
    print(df[["ticker", "t212_ticker", "quantity", "status"]].to_string(index=False))
    if execute:
        (pd.concat([pd.read_csv(placed_path), df], ignore_index=True) if placed_path.exists() else df).to_csv(
            placed_path, index=False)
    return rows


def _real_value(row):
    """Trade value in account currency from a fill: price x quantity converted with the fill's FX rate.

    The fxRate's direction isn't documented, so take whichever conversion agrees with netValue (which
    also includes fees, so it's only a guide). If neither is close, use netValue itself.
    """
    gross, fx, net = abs(row["price"] * row["quantity"]), row["fx_rate"], abs(row["net_value"])
    if not fx or pd.isna(fx):
        return net
    best = min((gross * fx, gross / fx), key=lambda v: abs(v - net))
    return best if abs(best / net - 1) < 0.05 else net


def compare(spec_path, cfg, close_local, fx_usd, universe):
    """Real Practice fills and account value next to what the simulation assumes.

    Per fill: price paid vs that stock's close on the fill day (the simulated/backtest fill price), and
    Trading 212's actual fees vs the cost model's estimate for the same trade. Plus the Practice
    account's value next to the simulated ledger's. Writes comparison.csv and comparison.md.
    """
    spec = yaml.safe_load(spec_path.read_text())
    strategy = spec.get("t212_practice")
    d = _state_dir(spec_path)
    if not (d / "fills.csv").exists():
        print("  no Trading 212 fills yet to compare")
        return None
    base = cfg["account"]["base_currency"]
    fills = pd.read_csv(d / "fills.csv")
    placed = pd.read_csv(d / "orders_placed.csv").dropna(subset=["order_id"])
    placed["order_id"] = placed["order_id"].astype("int64")
    fills = fills.merge(placed[["order_id", "signal_date", "ticker"]].rename(columns={"ticker": "yahoo"}),
                        on="order_id", how="left")
    px = to_base(close_local, universe["currency"], fx_usd, base).ffill()
    local = close_local.ffill()

    rows = []
    for _, f in fills.iterrows():
        t = f["yahoo"]
        if pd.isna(t) or t not in px.columns:
            continue
        day = pd.Timestamp(str(f["filled_at"])[:10])
        close = px[t].loc[:day]
        if close.empty or close.index[-1] != day:
            continue                                          # no close for the fill day yet
        qty = abs(float(f["quantity"]))
        side = "buy" if str(f["side"]).upper() == "BUY" or float(f["quantity"]) > 0 else "sell"
        value = _real_value(f)
        sign = 1 if side == "buy" else -1
        model = trade_cost(value, qty, universe.loc[t, "country"], universe.loc[t, "currency"], side, cfg)
        # Compare in the quote currency, so FX moves during the day don't count as cost. If the fill
        # price isn't in the quote currency's units, compare in base currency instead.
        ratio = float(f["price"]) / local.at[day, t]
        if abs(math.log(ratio)) > 0.2:
            ratio = value / qty / close.iloc[-1]
        timing = sign * (ratio - 1) * 1e4
        fees = abs(float(f.get("fees", 0) or 0))
        rows.append({"signal_date": f["signal_date"], "fill_day": day.date(), "ticker": t, "side": side,
                     "shares": qty, f"value_{base}": round(value, 2),
                     "vs_close_bps": round(timing, 1), "real_fees_bps": round(fees / value * 1e4, 1),
                     "real_total_bps": round(timing + fees / value * 1e4, 1),
                     "model_cost_bps": round(model / value * 1e4, 1), "fees_detail": f.get("fees_detail", "")})
    trades = pd.DataFrame(rows)
    trades.to_csv(d / "comparison.csv", index=False)

    lines = [f"# Trading 212 Practice vs simulation ({strategy})", ""]
    if len(trades):
        w = trades[f"value_{base}"]
        avg = lambda c: (trades[c] * w).sum() / w.sum()
        real, model = avg("real_total_bps"), avg("model_cost_bps")
        lines += [f"**{len(trades)} fills.** Value-weighted cost per trade: real **{real:.0f} bps** "
                  f"(price vs the day's close {avg('vs_close_bps'):+.0f} bps + fees {avg('real_fees_bps'):.0f} bps) "
                  f"against the model's **{model:.0f} bps**: {real / model:.1f}x the model "
                  "(the go-live rule asks for no more than about 2x).", "",
                  "Price vs close is noisy for any single trade (orders sent at the weekend fill at the "
                  "open, the model assumes the close); only the average over many trades means much.", "",
                  trades.drop(columns=["fees_detail"]).to_markdown(index=False), ""]
    sim_nav = spec_path.parent / strategy / "nav.csv"
    if (d / "account.csv").exists() and sim_nav.exists():
        acct = pd.read_csv(d / "account.csv", parse_dates=["date"]).sort_values("date")
        sim = pd.read_csv(sim_nav, parse_dates=["date"]).sort_values("date")
        both = pd.merge_asof(acct, sim[["date", "equity"]], on="date", direction="backward")
        both = both.rename(columns={"total_value": "Trading 212", "equity": "simulated"})
        both["difference"] = both["Trading 212"] - both["simulated"]
        both["date"] = both["date"].dt.date
        lines += ["## Account value", "",
                  both[["date", "Trading 212", "simulated", "difference"]].round(2).to_markdown(index=False), ""]
    text = "\n".join(lines)
    (d / "comparison.md").write_text(text)
    print(text)
    return trades
