from __future__ import annotations

import logging
import time
from decimal import Decimal, ROUND_DOWN

from .config import BotConfig
from .models import ArbitrageOpportunity, ExchangeClient, OrderResult, OrderSide, Ticker

LOGGER = logging.getLogger(__name__)


class ArbitrageEngine:
    def __init__(self, config: BotConfig, exchanges: list[ExchangeClient]) -> None:
        self.config = config
        self.exchanges = exchanges

    def scan_symbol(self, symbol: str) -> ArbitrageOpportunity | None:
        tickers = [exchange.fetch_ticker(symbol) for exchange in self.exchanges]
        best_buy = min(tickers, key=lambda ticker: ticker.ask)
        best_sell = max(tickers, key=lambda ticker: ticker.bid)

        if best_buy.exchange == best_sell.exchange or best_sell.bid <= best_buy.ask:
            return None

        buy_exchange = self._exchange_by_name(best_buy.exchange)
        sell_exchange = self._exchange_by_name(best_sell.exchange)
        amount = self._safe_amount(symbol, best_buy, best_sell)
        if amount <= 0:
            return None

        gross_profit = (best_sell.bid - best_buy.ask) * amount
        notional_buy = best_buy.ask * amount
        notional_sell = best_sell.bid * amount
        estimated_fees = (notional_buy * buy_exchange.fee_rate) + (notional_sell * sell_exchange.fee_rate)
        estimated_slippage = (notional_buy + notional_sell) * (self.config.slippage_pct / Decimal("100"))
        net_profit = gross_profit - estimated_fees - estimated_slippage
        net_profit_pct = (net_profit / notional_buy) * Decimal("100")

        if net_profit_pct < self.config.min_net_profit_pct:
            return None

        return ArbitrageOpportunity(
            symbol=symbol,
            buy_exchange=best_buy.exchange,
            sell_exchange=best_sell.exchange,
            buy_price=best_buy.ask,
            sell_price=best_sell.bid,
            amount=amount,
            gross_profit=gross_profit,
            estimated_fees=estimated_fees,
            estimated_slippage=estimated_slippage,
            net_profit=net_profit,
            net_profit_pct=net_profit_pct,
        )

    def execute(self, opportunity: ArbitrageOpportunity) -> list[OrderResult]:
        buy_exchange = self._exchange_by_name(opportunity.buy_exchange)
        sell_exchange = self._exchange_by_name(opportunity.sell_exchange)
        LOGGER.info(
            "Executando arbitragem %s: comprar em %s por %s e vender em %s por %s (dry_run=%s)",
            opportunity.symbol,
            opportunity.buy_exchange,
            opportunity.buy_price,
            opportunity.sell_exchange,
            opportunity.sell_price,
            self.config.dry_run,
        )
        buy_order = buy_exchange.create_order(
            opportunity.symbol,
            OrderSide.BUY,
            opportunity.amount,
            opportunity.buy_price,
            self.config.dry_run,
        )
        sell_order = sell_exchange.create_order(
            opportunity.symbol,
            OrderSide.SELL,
            opportunity.amount,
            opportunity.sell_price,
            self.config.dry_run,
        )
        return [buy_order, sell_order]

    def run_once(self) -> list[OrderResult]:
        orders: list[OrderResult] = []
        for symbol in self.config.symbols:
            opportunity = self.scan_symbol(symbol)
            if opportunity is None:
                LOGGER.info("Nenhuma oportunidade rentável para %s", symbol)
                continue
            LOGGER.info(
                "Oportunidade: %s %s -> %s lucro líquido estimado %s (%s%%)",
                symbol,
                opportunity.buy_exchange,
                opportunity.sell_exchange,
                opportunity.net_profit.quantize(Decimal("0.0001")),
                opportunity.net_profit_pct.quantize(Decimal("0.0001")),
            )
            orders.extend(self.execute(opportunity))
        return orders

    def run_forever(self) -> None:
        while True:
            self.run_once()
            time.sleep(self.config.poll_interval_seconds)

    def _safe_amount(self, symbol: str, buy_ticker: Ticker, sell_ticker: Ticker) -> Decimal:
        base_asset = symbol.split("/")[0]
        buy_exchange = self._exchange_by_name(buy_ticker.exchange)
        sell_exchange = self._exchange_by_name(sell_ticker.exchange)
        quote_balance = buy_exchange.fetch_balance(self.config.quote_asset).free
        base_balance = sell_exchange.fetch_balance(base_asset).free
        quote_to_use = min(self.config.max_trade_quote, quote_balance)
        amount_by_quote = quote_to_use / buy_ticker.ask
        return min(amount_by_quote, base_balance).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)

    def _exchange_by_name(self, name: str) -> ExchangeClient:
        for exchange in self.exchanges:
            if exchange.name == name:
                return exchange
        raise KeyError(f"Exchange não encontrada: {name}")
