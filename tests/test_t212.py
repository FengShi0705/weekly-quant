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
    def __init__(self, positions=()):
        self.calls, self.positions, self.next_id = [], list(positions), 100

    def request(self, method, url, headers=None, timeout=None, json=None, params=None):
        assert url.startswith(t212.DEMO)
        self.calls.append((method, url.removeprefix(t212.DEMO), json))
        path = url.removeprefix(t212.DEMO)
        if path == "/equity/metadata/instruments":
            return FakeResponse(INSTRUMENTS)
        if path == "/equity/positions":
            return FakeResponse(self.positions)
        if path == "/equity/orders/market":
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
