from decimal import Decimal

from bot_arbitragem.config import load_config


def test_load_config_reads_yaml(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
dry_run: true
symbols: [BTC/USDT]
quote_asset: USDT
risk:
  min_net_profit_pct: 0.5
  max_trade_quote: 50
  slippage_pct: 0.01
exchanges:
  - name: a
    adapter: mock
    mock_bid: 10
    mock_ask: 11
    balances:
      USDT: 100
  - name: b
    adapter: mock
    mock_bid: 12
    mock_ask: 13
    balances:
      BTC: 1
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.symbols == ["BTC/USDT"]
    assert config.min_net_profit_pct == Decimal("0.5")
    assert config.max_trade_quote == Decimal("50")
    assert config.exchanges[0].balances == {"USDT": Decimal("100")}
