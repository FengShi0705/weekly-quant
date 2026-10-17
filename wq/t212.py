"""Mirror a paper strategy's orders in a Trading 212 *Practice* account through the public API.

Only the Practice (demo) server is reachable from this module; it cannot place real-money orders.
Credentials: either a network secret on the cloud environment (username = API key, password = API
secret, for demo.trading212.com), which the proxy adds to each request so the key never enters the
session; or the T212_API_KEY and T212_API_SECRET environment variables.

State is kept next to the paper strategy, in paper/t212_practice/:
  orders_placed.csv   every order sent (or skipped), with the Trading 212 order id
  fills.csv           the fills Trading 212 reported for those orders
  account.csv         weekly account value from Trading 212
"""
import base64
import os
import re
import time
from datetime import date

import pandas as pd
import requests
import yaml

DEMO = "https://demo.trading212.com/api/v0"
YAHOO_SUFFIX = re.compile(r"\.(L|DE|PA|AS|MC|MI|SW|CO|ST|HE|TO|T|HK)$")
T212_CCY = {"GBp": "GBX"}


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
        return self._call("GET", "/equity/metadata/instruments")

    def positions(self):
        return self._call("GET", "/equity/positions")

    def summary(self):
        return self._call("GET", "/equity/account/summary")

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
                rows.append({"order_id": o["id"], "ticker": o["instrument"]["ticker"], "side": o.get("side"),
                             "filled_at": f.get("filledAt"), "quantity": f.get("quantity"), "price": f.get("price"),
                             "instrument_ccy": o["instrument"].get("currency"), "fx_rate": w.get("fxRate"),
                             "net_value": w.get("netValue"), "account_ccy": w.get("currency"),
                             "taxes": sum(x.get("quantity", 0) for x in w.get("taxes", []) or [])})
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
    (pd.concat([pd.read_csv(path), row], ignore_index=True) if path.exists() else row).to_csv(path, index=False)
    print(f"  Practice account value {s.get('totalValue')} {s.get('currency')}")


def place(client, spec_path, universe, execute=False):
    """Send the mirrored strategy's pending orders to the Practice account (sells first)."""
    spec = yaml.safe_load(spec_path.read_text())
    strategy = spec.get("t212_practice")
    if not strategy:
        print("  no strategy is set to mirror in Trading 212 (t212_practice in strategies.yaml)")
        return []
    d = _state_dir(spec_path)
    pending_path = spec_path.parent / strategy / "pending_orders.csv"
    if not pending_path.exists():
        print(f"  {strategy}: no pending orders this week")
        return []
    pending = pd.read_csv(pending_path)
    signal = str(pending["signal_date"].iloc[0])
    placed_path = d / "orders_placed.csv"
    if placed_path.exists() and signal in set(pd.read_csv(placed_path)["signal_date"].astype(str)):
        print(f"  orders for signal {signal} were already sent; not sending again")
        return []

    overrides_path = spec_path.parent / "t212_overrides.yaml"
    overrides = yaml.safe_load(overrides_path.read_text()) if overrides_path.exists() else {}
    mapping, problems = map_tickers(universe.loc[universe.index.isin(pending["ticker"])], client.instruments(),
                                    overrides)
    held = {p["ticker"]: float(p["quantity"]) for p in client.positions()}

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
            try:
                row["order_id"] = client.market_order(tk, qty).get("id")
                row["status"] = "sent"
            except RuntimeError as e:
                row["status"] = f"error: {e}"
        rows.append(row)
    df = pd.DataFrame(rows)
    print(df[["ticker", "t212_ticker", "quantity", "status"]].to_string(index=False))
    if execute:
        (pd.concat([pd.read_csv(placed_path), df], ignore_index=True) if placed_path.exists() else df).to_csv(
            placed_path, index=False)
    return rows
