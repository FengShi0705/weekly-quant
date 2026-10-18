import base64
import json
from datetime import date

import pandas as pd
import pytest

from wq import paper, t212
from wq.data import to_base

INSTRUMENTS = [
    {"ticker": "AAPL_US_EQ", "shortName": "AAPL", "currencyCode": "USD", "type": "STOCK"},
    {"ticker": "BARCl_EQ", "shortName": "BARC", "currencyCode": "GBX", "type": "STOCK"},
    {"ticker": "BRK_B_US_EQ", "shortName": "BRK.B", "currencyCode": "USD", "type": "STOCK"},
    {"ticker": "SAPd_EQ", "shortName": "SAP", "currencyCode": "EUR", "type": "STOCK"},
    {"ticker": "SAP_US_EQ", "shortName": "SAP", "currencyCode": "USD", "type": "STOCK"},
    {"ticker": "AAPL_ETF", "shortName": "AAPL", "currencyCode": "USD", "type": "ETF"},
]
UNIVERSE = pd.DataFrame({"currency": ["USD", "GBp", "USD", "EUR", "CHF"]},
                        index=["AAPL", "BARC.L", "BRK-B", "SAP.DE", "NESN.SW"])


class FakeResponse:
    def __init__(self, data, status=200):
        self.status_code, self._data, self.text = status, data, json.dumps(data)

    def json(self):
        return self._data


class FakeT212:
    """Mimics the demo server, including its rejection of quantities with too many decimals."""

    def __init__(self, positions=(), precision=None, open_orders=(), cash=0.0, instruments=INSTRUMENTS):
        self.calls, self.positions, self.next_id = [], list(positions), 100
        self.precision = precision or {}
        self.open_orders = list(open_orders)
        self.cash, self.instruments = cash, instruments

    def request(self, method, url, headers=None, timeout=None, json=None, params=None):
        assert url.startswith(t212.DEMO)
        self.calls.append((method, url.removeprefix(t212.DEMO), json))
        path = url.removeprefix(t212.DEMO)
        if path == "/equity/metadata/instruments":
            return FakeResponse(self.instruments)
        if path == "/equity/positions":
            return FakeResponse(self.positions)
        if path == "/equity/orders":
            return FakeResponse(self.open_orders)
        if path == "/equity/account/summary":
            return FakeResponse({"currency": "GBP", "totalValue": self.cash, "cash": {"availableToTrade": self.cash}})
        if path == "/equity/orders/market":
            allowed = self.precision.get(json["ticker"], 4)
            if round(abs(json["quantity"]) * 10 ** allowed, 6) % 1:
                return FakeResponse({"type": "/api-errors/quantity-precision-mismatch",
                                     "detail": f"invalid quantity precision {allowed}"}, status=400)
            self.next_id += 1
            return FakeResponse({"id": self.next_id})
        raise AssertionError(path)


def client(fake):
    return t212.Client("key", "secret", http=fake, pause=0)


def test_credentials_from_env_or_network_secret(monkeypatch):
    monkeypatch.delenv("T212_API_KEY", raising=False)
    monkeypatch.delenv("T212_API_SECRET", raising=False)
    assert "Authorization" not in t212.Client().headers          # the proxy's network secret signs requests
    monkeypatch.setenv("T212_API_KEY", "k")
    with pytest.raises(RuntimeError):                              # half a key pair is a mistake
        t212.Client()
    monkeypatch.setenv("T212_API_SECRET", "s")
    assert t212.Client().headers["Authorization"] == "Basic " + base64.b64encode(b"k:s").decode()


def test_map_tickers_by_symbol_and_currency():
    mapping, problems = t212.map_tickers(UNIVERSE, INSTRUMENTS)
    assert mapping == {"AAPL": "AAPL_US_EQ", "BARC.L": "BARCl_EQ", "BRK-B": "BRK_B_US_EQ", "SAP.DE": "SAPd_EQ"}
    assert list(problems) == ["NESN.SW"]
    mapping, _ = t212.map_tickers(UNIVERSE, INSTRUMENTS, overrides={"NESN.SW": "NESNz_EQ"})
    assert mapping["NESN.SW"] == "NESNz_EQ"


@pytest.fixture
def spec(tmp_path):
    p = tmp_path / "paper" / "strategies.yaml"
    (tmp_path / "paper" / "t212_practice").mkdir(parents=True)
    p.write_text("start_capital: 10000\nt212_practice: main\nstrategies:\n  main: {}\n")
    pd.DataFrame([
        {"signal_date": "2026-10-16", "ticker": "AAPL", "side": "buy", "shares": 1.23456, "reason": "enter"},
        {"signal_date": "2026-10-16", "ticker": "BARC.L", "side": "sell", "shares": 50, "reason": "exit"},
        {"signal_date": "2026-10-16", "ticker": "NESN.SW", "side": "buy", "shares": 3, "reason": "enter"},
    ]).to_csv(p.parent / "t212_practice" / "pending_orders.csv", index=False)
    return p


def test_dry_run_sends_nothing(spec):
    fake = FakeT212(positions=[{"ticker": "BARCl_EQ", "quantity": 40}])
    rows = t212.place(client(fake), spec, UNIVERSE, execute=False)
    assert not [c for c in fake.calls if c[0] == "POST"]
    assert {r["status"] for r in rows} == {"dry run", "skipped: 0 matches for NESN in CHF"}
    assert not (spec.parent / "t212_practice" / "orders_placed.csv").exists()


def test_execute_sells_first_caps_sells_and_never_duplicates(spec):
    fake = FakeT212(positions=[{"ticker": "BARCl_EQ", "quantity": 40}])
    t212.place(client(fake), spec, UNIVERSE, execute=True)
    posts = [c[2] for c in fake.calls if c[0] == "POST"]
    assert posts == [{"ticker": "BARCl_EQ", "quantity": -40.0, "extendedHours": False},
                     {"ticker": "AAPL_US_EQ", "quantity": 1.2346, "extendedHours": False}]
    placed = pd.read_csv(spec.parent / "t212_practice" / "orders_placed.csv")
    assert list(placed["status"]) == ["sent", "sent", "skipped: 0 matches for NESN in CHF"]
    assert t212.place(client(fake), spec, UNIVERSE, execute=True) == []
    assert len([c for c in fake.calls if c[0] == "POST"]) == 2


def test_precision_rejection_is_resent_truncated(spec):
    fake = FakeT212(positions=[{"ticker": "BARCl_EQ", "quantity": 40}], precision={"AAPL_US_EQ": 2})
    t212.place(client(fake), spec, UNIVERSE, execute=True)
    aapl = [c[2]["quantity"] for c in fake.calls if c[0] == "POST" and c[2]["ticker"] == "AAPL_US_EQ"]
    assert aapl == [1.2346, 1.23]                                   # rejected once, then sent at 2 decimals
    placed = pd.read_csv(spec.parent / "t212_practice" / "orders_placed.csv").set_index("ticker")
    assert placed.loc["AAPL", "status"] == "sent" and placed.loc["AAPL", "quantity"] == 1.23


def test_retry_rejected_resends_only_rejected_orders(spec):
    d = spec.parent / "t212_practice"
    pd.DataFrame([
        {"signal_date": "2026-10-16", "sent_on": "2026-10-18", "ticker": "AAPL", "t212_ticker": "AAPL_US_EQ",
         "quantity": 1.2346, "order_id": None, "status": 'error: HTTP 400: {"type":"/api-errors/quantity-precision-mismatch"}'},
        {"signal_date": "2026-10-16", "sent_on": "2026-10-18", "ticker": "BARC.L", "t212_ticker": "BARCl_EQ",
         "quantity": -40.0, "order_id": 555, "status": "sent"},
    ]).to_csv(d / "orders_placed.csv", index=False)
    assert t212.place(client(FakeT212()), spec, UNIVERSE, execute=True) == []    # plain rerun: blocked

    fake = FakeT212(precision={"AAPL_US_EQ": 3})
    t212.place(client(fake), spec, UNIVERSE, execute=True, retry_rejected=True)
    posts = [c[2] for c in fake.calls if c[0] == "POST"]
    assert [p["ticker"] for p in posts] == ["AAPL_US_EQ", "AAPL_US_EQ"]          # BARC (already sent) untouched
    placed = pd.read_csv(d / "orders_placed.csv").set_index("ticker")
    assert placed.loc["AAPL", "status"] == "sent" and placed.loc["AAPL", "quantity"] == 1.234
    assert placed.loc["BARC.L", "order_id"] == 555

    again = FakeT212()
    assert t212.place(client(again), spec, UNIVERSE, execute=True, retry_rejected=True) == []
    assert not [c for c in again.calls if c[0] == "POST"]                         # nothing left to resend


def test_retry_rejected_skips_tickers_with_an_open_order(spec):
    d = spec.parent / "t212_practice"
    pd.DataFrame([{"signal_date": "2026-10-16", "sent_on": "2026-10-18", "ticker": "AAPL",
                   "t212_ticker": "AAPL_US_EQ", "quantity": 1.0, "order_id": None,
                   "status": "error: HTTP 400: rejected"}]).to_csv(d / "orders_placed.csv", index=False)
    fake = FakeT212(open_orders=[{"ticker": "AAPL_US_EQ", "quantity": 1.0}])
    rows = t212.place(client(fake), spec, UNIVERSE, execute=True, retry_rejected=True)
    assert rows[0]["status"] == "skipped: an open order already exists"
    assert not [c for c in fake.calls if c[0] == "POST"]


def synthetic_instruments(universe):
    out = []
    for t, ccy in universe["currency"].items():
        sym = t212.YAHOO_SUFFIX.sub("", t)
        out.append({"ticker": f"{sym}_EQ", "shortName": sym, "currencyCode": t212.T212_CCY.get(ccy, ccy),
                    "type": "STOCK"})
    return out


def test_account_holdings_maps_positions_and_cash():
    fake = FakeT212(positions=[{"instrument": {"ticker": "AAPL_US_EQ"}, "quantity": 2.5},
                               {"ticker": "XYZ_US_EQ", "quantity": 1}], cash=123.45)
    shares, cash, unmanaged = t212.account_holdings(client(fake), UNIVERSE)
    assert shares == {"AAPL": 2.5} and cash == 123.45 and unmanaged == {"XYZ_US_EQ": 1.0}


def test_sync_records_the_real_holdings(spec):
    fake = FakeT212(positions=[{"instrument": {"ticker": "AAPL_US_EQ"}, "quantity": 2.5},
                               {"ticker": "XYZ_US_EQ", "quantity": 1}], cash=123.45)
    t212.sync(client(fake), spec, UNIVERSE)
    d = spec.parent / "t212_practice"
    held = pd.read_csv(d / "holdings.csv").set_index("ticker")["shares"].to_dict()
    assert held == {"AAPL": 2.5, "XYZ_US_EQ": 1.0, "CASH": 123.45}
    assert len(pd.read_csv(d / "account.csv")) == 1
    t212.sync(client(fake), spec, UNIVERSE)                       # a second run the same day replaces the row
    assert len(pd.read_csv(d / "account.csv")) == 1
    assert [c[1] for c in fake.calls].count("/equity/account/summary") == 2   # one summary request per run


def test_practice_orders_are_planned_from_the_real_account(cfg, signal_market, tmp_path):
    close, volume, fx, universe = signal_market
    cfg["data"]["cache_dir"] = tmp_path / "no_cache"
    cfg["portfolio"]["hold_rank"] = 20                             # the synthetic universe has only 60 stocks
    spec = tmp_path / "paper" / "strategies.yaml"
    spec.parent.mkdir()
    spec.write_text("start_capital: 10000\nt212_practice: main\nstrategies:\n  main: {}\n")
    week = close.loc[:"2019-12-13"]
    args = (week, volume.loc[week.index], fx.loc[week.index], universe)
    paper.run(cfg, *args, spec)
    main, real_dir = spec.parent / "main", spec.parent / "t212_practice"
    simulated = pd.read_csv(main / "pending_orders.csv")
    inst = synthetic_instruments(universe)

    # Same holdings as the simulated ledger (all cash): the same orders, from the same saved scores.
    t212.plan_from_account(client(FakeT212(cash=10000, instruments=inst)), cfg, spec, *args)
    pd.testing.assert_frame_equal(pd.read_csv(real_dir / "pending_orders.csv"), simulated)

    # Drift: the account holds a stock the strategy ranks last, and less cash. The plan sells all of it
    # and spends no more than the account has.
    scores = pd.read_csv(main / "reports" / str(date.today()) / "all_scores.csv", index_col=0)["score"]
    worst = scores.idxmin()
    fake = FakeT212(positions=[{"ticker": f"{t212.YAHOO_SUFFIX.sub('', worst)}_EQ", "quantity": 7}],
                    cash=4000, instruments=inst)
    result = t212.plan_from_account(client(fake), cfg, spec, *args)
    real = pd.read_csv(real_dir / "pending_orders.csv").set_index("ticker")
    assert real.loc[worst, "side"] == "sell" and real.loc[worst, "shares"] == 7
    buys = sum(o["value"] for o in result["orders"] if o["side"] == "buy")
    sells = sum(o["value"] for o in result["orders"] if o["side"] == "sell")
    assert buys <= 4000 + sells
    assert pd.read_csv(main / "pending_orders.csv").equals(simulated)          # simulated ledger untouched
    assert pd.read_csv(main / "holdings.csv").set_index("ticker")["shares"].to_dict() == {"CASH": 10000}

    # Orders still open in the account: plan nothing.
    (real_dir / "pending_orders.csv").unlink()
    busy = FakeT212(cash=4000, instruments=inst, open_orders=[{"ticker": "S000_EQ", "quantity": 1}])
    assert t212.plan_from_account(client(busy), cfg, spec, *args) is None
    assert not (real_dir / "pending_orders.csv").exists()


def test_compare_real_fills_with_the_model(cfg, signal_market, tmp_path):
    close, _, fx, universe = signal_market
    spec = tmp_path / "paper" / "strategies.yaml"
    d, main = spec.parent / "t212_practice", spec.parent / "main"
    d.mkdir(parents=True)
    main.mkdir()
    spec.write_text("start_capital: 10000\nt212_practice: main\nstrategies:\n  main: {}\n")
    day, us, uk = pd.Timestamp("2019-12-16"), "S000", "S001.L"
    gbp_per_usd = 1 / fx.at[day, "GBP"]
    us_px, uk_px = close.at[day, us] * 1.001, close.at[day, uk] * 0.998     # 10 bps worse, 20 bps worse
    us_val = 2 * us_px * gbp_per_usd
    pd.DataFrame([
        {"order_id": 1, "ticker": "S000_EQ", "side": "BUY", "filled_at": "2019-12-16T14:30:01Z", "quantity": 2,
         "price": us_px, "instrument_ccy": "USD", "fx_rate": gbp_per_usd, "net_value": us_val * 1.0015,
         "account_ccy": "GBP", "fees": us_val * 0.0015, "fees_detail": "CURRENCY_CONVERSION_FEE"},
        {"order_id": 2, "ticker": "S001_EQ", "side": "SELL", "filled_at": "2019-12-16T08:00:02Z", "quantity": -10,
         "price": uk_px, "instrument_ccy": "GBX", "fx_rate": 0.01, "net_value": 10 * uk_px / 100,
         "account_ccy": "GBP", "fees": 0, "fees_detail": ""},
    ]).to_csv(d / "fills.csv", index=False)
    pd.DataFrame([{"signal_date": "2019-12-13", "ticker": us, "order_id": 1, "status": "sent"},
                  {"signal_date": "2019-12-13", "ticker": uk, "order_id": 2, "status": "sent"},
                  {"signal_date": "2019-12-13", "ticker": "S002.DE", "order_id": None, "status": "error: HTTP 400"}]
                 ).to_csv(d / "orders_placed.csv", index=False)
    pd.DataFrame([{"date": "2019-12-21", "total_value": 10050.0}]).to_csv(d / "account.csv", index=False)
    pd.DataFrame([{"date": "2019-12-20", "equity": 10000.0}]).to_csv(main / "nav.csv", index=False)
    # UBS-style drift: the Practice account bought S003 where the simulation holds S006. S000 differs
    # only by rounding, so it isn't listed.
    paper.write_holdings(d / "holdings.csv", {us: 2.0, "S003": 5.0}, 100.0)
    paper.write_holdings(main / "holdings.csv", {us: 2.05, "S006": 3.0}, 80.0)

    trades = t212.compare(spec, cfg, close, fx, universe).set_index("ticker")
    assert trades.loc[us, "vs_close_bps"] == pytest.approx(10, abs=0.1)
    assert trades.loc[us, "real_fees_bps"] == pytest.approx(15, abs=0.1)
    assert trades.loc[us, "model_cost_bps"] == pytest.approx(25, abs=0.1)        # slippage 10 + FX fee 15
    assert trades.loc[uk, "vs_close_bps"] == pytest.approx(20, abs=0.1)          # sold below the close
    assert trades.loc[uk, "real_total_bps"] == pytest.approx(20, abs=0.1)
    assert trades.loc[uk, "model_cost_bps"] == pytest.approx(10, abs=0.1)        # no stamp duty on sells
    assert trades.loc[uk, "value_GBP"] == pytest.approx(10 * uk_px / 100, abs=0.01)
    text = (d / "comparison.md").read_text()
    assert "2 fills" in text and "| 2019-12-21" in text and "50" in text
    last = to_base(close, universe["currency"], fx, "GBP").ffill().iloc[-1]
    diff = t212.holdings_difference(d / "holdings.csv", main / "holdings.csv", last, universe).set_index("ticker")
    assert list(diff.index) == ["S003", "S006", "CASH"]
    assert list(diff["held in"].iloc[:2]) == ["Trading 212 only", "simulated only"]
    assert diff.loc["S003", "difference"] == pytest.approx(5 * last["S003"], abs=0.01)
    assert diff.loc["S006", "difference"] == pytest.approx(-3 * last["S006"], abs=0.01)
    assert diff.loc["CASH", "difference"] == 20
    assert "## Holdings that differ" in text
    assert "Trading 212 only: S003; simulated only: S006" in text


def test_holdings_section_when_both_accounts_match(tmp_path):
    universe = pd.DataFrame({"name": ["Apple"]}, index=["AAPL"])
    paper.write_holdings(tmp_path / "real.csv", {"AAPL": 10.0}, 50.0)
    paper.write_holdings(tmp_path / "sim.csv", {"AAPL": 10.2}, 50.0)
    diff = t212.holdings_difference(tmp_path / "real.csv", tmp_path / "sim.csv", pd.Series({"AAPL": 100.0}), universe)
    assert list(diff["ticker"]) == ["CASH"]
    assert "Both accounts hold the same stocks." in "\n".join(t212._holdings_section(diff, 0.05, "2026-10-23"))
