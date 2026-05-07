from decimal import Decimal

from bot_arbitragem.config import BotConfig, ExchangeConfig
from bot_arbitragem.engine import ArbitrageEngine
from bot_arbitragem.exchanges import MockExchangeClient


def make_engine(min_profit_pct: str = "0.20") -> ArbitrageEngine:
    config = BotConfig(
        symbols=["BTC/USDT"],
        quote_asset="USDT",
        min_net_profit_pct=Decimal(min_profit_pct),
        max_trade_quote=Decimal("100"),
        poll_interval_seconds=1,
        dry_run=True,
        slippage_pct=Decimal("0.03"),
        exchanges=[
            ExchangeConfig(
                name="cheap",
                mock_bid=Decimal("29950"),
                mock_ask=Decimal("30000"),
                balances={"USDT": Decimal("100"), "BTC": Decimal("0")},
            ),
            ExchangeConfig(
                name="expensive",
                mock_bid=Decimal("30200"),
                mock_ask=Decimal("30250"),
                balances={"USDT": Decimal("0"), "BTC": Decimal("0.01")},
            ),
        ],
    )
    exchanges = [MockExchangeClient(exchange) for exchange in config.exchanges]
    return ArbitrageEngine(config, exchanges)


def test_scan_symbol_returns_profitable_opportunity() -> None:
    engine = make_engine()

    opportunity = engine.scan_symbol("BTC/USDT")

    assert opportunity is not None
    assert opportunity.buy_exchange == "cheap"
    assert opportunity.sell_exchange == "expensive"
    assert opportunity.amount == Decimal("0.00333333")
    assert opportunity.net_profit > Decimal("0")


def test_scan_symbol_filters_opportunity_below_minimum_profit() -> None:
    engine = make_engine(min_profit_pct="5")

    opportunity = engine.scan_symbol("BTC/USDT")

    assert opportunity is None


def test_run_once_creates_dry_run_buy_and_sell_orders() -> None:
    engine = make_engine()

    orders = engine.run_once()

    assert len(orders) == 2
    assert {order.side.value for order in orders} == {"buy", "sell"}
    assert all(order.dry_run for order in orders)
