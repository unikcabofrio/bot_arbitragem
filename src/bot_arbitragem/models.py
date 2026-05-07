from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Protocol


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class Ticker:
    exchange: str
    symbol: str
    bid: Decimal
    ask: Decimal


@dataclass(frozen=True)
class Balance:
    asset: str
    free: Decimal


@dataclass(frozen=True)
class OrderResult:
    exchange: str
    symbol: str
    side: OrderSide
    amount: Decimal
    price: Decimal
    order_id: str
    dry_run: bool


@dataclass(frozen=True)
class ArbitrageOpportunity:
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: Decimal
    sell_price: Decimal
    amount: Decimal
    gross_profit: Decimal
    estimated_fees: Decimal
    estimated_slippage: Decimal
    net_profit: Decimal
    net_profit_pct: Decimal


class ExchangeClient(Protocol):
    name: str
    fee_rate: Decimal

    def fetch_ticker(self, symbol: str) -> Ticker:
        """Return the best bid/ask for a symbol."""

    def fetch_balance(self, asset: str) -> Balance:
        """Return available balance for an asset."""

    def create_order(
        self, symbol: str, side: OrderSide, amount: Decimal, price: Decimal, dry_run: bool
    ) -> OrderResult:
        """Create a limit order, or simulate it when dry_run=True."""
