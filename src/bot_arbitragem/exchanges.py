from __future__ import annotations

import importlib
import importlib.util
import itertools
from decimal import Decimal

from .config import ExchangeConfig
from .models import Balance, ExchangeClient, OrderResult, OrderSide, Ticker


class MockExchangeClient:
    def __init__(self, config: ExchangeConfig) -> None:
        if config.mock_bid is None or config.mock_ask is None:
            raise ValueError(f"Exchange mock {config.name} exige mock_bid e mock_ask.")
        self.name = config.name
        self.fee_rate = config.fee_rate
        self._bid = config.mock_bid
        self._ask = config.mock_ask
        self._balances = config.balances or {}
        self._ids = itertools.count(1)

    def fetch_ticker(self, symbol: str) -> Ticker:
        return Ticker(exchange=self.name, symbol=symbol, bid=self._bid, ask=self._ask)

    def fetch_balance(self, asset: str) -> Balance:
        return Balance(asset=asset, free=self._balances.get(asset, Decimal("0")))

    def create_order(
        self, symbol: str, side: OrderSide, amount: Decimal, price: Decimal, dry_run: bool
    ) -> OrderResult:
        prefix = "dry" if dry_run else "mock"
        return OrderResult(
            exchange=self.name,
            symbol=symbol,
            side=side,
            amount=amount,
            price=price,
            order_id=f"{prefix}-{next(self._ids)}",
            dry_run=dry_run,
        )


class CcxtExchangeClient:
    def __init__(self, config: ExchangeConfig) -> None:
        if importlib.util.find_spec("ccxt") is None:
            raise RuntimeError("Instale a dependência opcional com: pip install 'bot-arbitragem[ccxt]'")

        ccxt = importlib.import_module("ccxt")
        if not hasattr(ccxt, config.name):
            raise ValueError(f"Exchange CCXT não suportada: {config.name}")

        exchange_class = getattr(ccxt, config.name)
        api_key = _read_secret(config.api_key_env)
        api_secret = _read_secret(config.api_secret_env)
        params = {"enableRateLimit": True}
        if api_key:
            params["apiKey"] = api_key
        if api_secret:
            params["secret"] = api_secret

        self._exchange = exchange_class(params)
        if config.sandbox and hasattr(self._exchange, "set_sandbox_mode"):
            self._exchange.set_sandbox_mode(True)
        self.name = config.name
        self.fee_rate = config.fee_rate

    def fetch_ticker(self, symbol: str) -> Ticker:
        ticker = self._exchange.fetch_ticker(symbol)
        return Ticker(
            exchange=self.name,
            symbol=symbol,
            bid=Decimal(str(ticker["bid"])),
            ask=Decimal(str(ticker["ask"])),
        )

    def fetch_balance(self, asset: str) -> Balance:
        balance = self._exchange.fetch_balance()
        free = balance.get("free", {}).get(asset, 0)
        return Balance(asset=asset, free=Decimal(str(free)))

    def create_order(
        self, symbol: str, side: OrderSide, amount: Decimal, price: Decimal, dry_run: bool
    ) -> OrderResult:
        if dry_run:
            return OrderResult(self.name, symbol, side, amount, price, "dry-run", True)
        order = self._exchange.create_limit_order(symbol, side.value, float(amount), float(price))
        return OrderResult(self.name, symbol, side, amount, price, str(order.get("id")), False)


def _read_secret(env_name: str | None) -> str | None:
    if env_name is None:
        return None
    import os

    return os.getenv(env_name)


def build_exchange(config: ExchangeConfig) -> ExchangeClient:
    adapter = config.adapter.lower()
    if adapter == "mock":
        return MockExchangeClient(config)
    if adapter == "ccxt":
        return CcxtExchangeClient(config)
    raise ValueError(f"Adapter de exchange inválido: {config.adapter}")
