import base64
import json

import pandas as pd
import pytest

from wq import t212

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

    def __init__(self, positions=(), precision=None, open_orders=()):
        self.calls, self.positions, self.next_id = [], list(positions), 100
        self.precision = precision or {}
        self.open_orders = list(open_orders)

    def request(self, method, url, headers=None, timeout=None, json=None, params=None):
        assert url.startswith(t212.DEMO)
        self.calls.append((method, url.removeprefix(t212.DEMO), json))
        path = url.removeprefix(t212.DEMO)
        if path == "/equity/metadata/instruments":
            return FakeResponse(INSTRUMENTS)
        if path == "/equity/positions":
            return FakeResponse(self.positions)
        if path == "/equity/orders":
            return FakeResponse(self.open_orders)
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
    (tmp_path / "paper" / "main").mkdir(parents=True)
    p.write_text("start_capital: 10000\nt212_practice: main\nstrategies:\n  main: {}\n")
    pd.DataFrame([
        {"signal_date": "2026-10-16", "ticker": "AAPL", "side": "buy", "shares": 1.23456, "reason": "enter"},
        {"signal_date": "2026-10-16", "ticker": "BARC.L", "side": "sell", "shares": 50, "reason": "exit"},
        {"signal_date": "2026-10-16", "ticker": "NESN.SW", "side": "buy", "shares": 3, "reason": "enter"},
    ]).to_csv(p.parent / "main" / "pending_orders.csv", index=False)
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
    d.mkdir()
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
    d.mkdir()
    pd.DataFrame([{"signal_date": "2026-10-16", "sent_on": "2026-10-18", "ticker": "AAPL",
                   "t212_ticker": "AAPL_US_EQ", "quantity": 1.0, "order_id": None,
                   "status": "error: HTTP 400: rejected"}]).to_csv(d / "orders_placed.csv", index=False)
    fake = FakeT212(open_orders=[{"ticker": "AAPL_US_EQ", "quantity": 1.0}])
    rows = t212.place(client(fake), spec, UNIVERSE, execute=True, retry_rejected=True)
    assert rows[0]["status"] == "skipped: an open order already exists"
    assert not [c for c in fake.calls if c[0] == "POST"]
