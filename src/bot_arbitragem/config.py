from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any



@dataclass(frozen=True)
class ExchangeConfig:
    name: str
    adapter: str = "mock"
    api_key_env: str | None = None
    api_secret_env: str | None = None
    fee_rate: Decimal = Decimal("0.001")
    sandbox: bool = True
    mock_bid: Decimal | None = None
    mock_ask: Decimal | None = None
    balances: dict[str, Decimal] | None = None


@dataclass(frozen=True)
class BotConfig:
    symbols: list[str]
    quote_asset: str
    min_net_profit_pct: Decimal
    max_trade_quote: Decimal
    poll_interval_seconds: float
    dry_run: bool
    slippage_pct: Decimal
    exchanges: list[ExchangeConfig]


def _decimal(value: Any, default: str | None = None) -> Decimal:
    if value is None:
        if default is None:
            raise ValueError("Valor decimal obrigatório ausente")
        value = default
    return Decimal(str(value))


def _bool_from_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "sim", "on"}


def load_config(path: str | Path) -> BotConfig:
    raw = _load_yaml(Path(path))

    risk = raw.get("risk", {})
    exchanges = []
    for item in raw.get("exchanges", []):
        balances = item.get("balances") or {}
        exchanges.append(
            ExchangeConfig(
                name=item["name"],
                adapter=item.get("adapter", "mock"),
                api_key_env=item.get("api_key_env"),
                api_secret_env=item.get("api_secret_env"),
                fee_rate=_decimal(item.get("fee_rate"), "0.001"),
                sandbox=bool(item.get("sandbox", True)),
                mock_bid=_decimal(item["mock_bid"]) if "mock_bid" in item else None,
                mock_ask=_decimal(item["mock_ask"]) if "mock_ask" in item else None,
                balances={asset: _decimal(amount) for asset, amount in balances.items()},
            )
        )

    if len(exchanges) < 2:
        raise ValueError("Configure pelo menos duas exchanges para arbitragem.")

    return BotConfig(
        symbols=list(raw.get("symbols", [])),
        quote_asset=raw.get("quote_asset", "USDT"),
        min_net_profit_pct=_decimal(risk.get("min_net_profit_pct"), "0.25"),
        max_trade_quote=_decimal(risk.get("max_trade_quote"), "25"),
        poll_interval_seconds=float(raw.get("poll_interval_seconds", 10)),
        dry_run=_bool_from_env("BOT_DRY_RUN", bool(raw.get("dry_run", True))),
        slippage_pct=_decimal(risk.get("slippage_pct"), "0.05"),
        exchanges=exchanges,
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    if importlib.util.find_spec("yaml") is not None:
        yaml = importlib.import_module("yaml")
        return yaml.safe_load(content) or {}
    return _parse_simple_yaml(content)


def _parse_simple_yaml(content: str) -> dict[str, Any]:
    """Parse the small YAML subset used by the example configuration.

    This fallback keeps local tests and dry-runs dependency-free. Production
    deployments should install PyYAML, which supports the full YAML syntax.
    """
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any] | list[Any]]] = [(-1, root)]

    lines = content.splitlines()
    for index, raw_line in enumerate(lines):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if line.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError("Lista YAML encontrada em local inválido.")
            item_text = line[2:].strip()
            if ":" in item_text:
                key, value = _split_key_value(item_text)
                item: dict[str, Any] = {key: _parse_scalar(value)}
                parent.append(item)
                stack.append((indent, item))
            else:
                parent.append(_parse_scalar(item_text))
            continue

        key, value = _split_key_value(line)
        if value == "":
            next_container: dict[str, Any] | list[Any]
            next_container = [] if _next_meaningful_line_is_list(lines, index) else {}
            if isinstance(parent, dict):
                parent[key] = next_container
            else:
                raise ValueError("Mapeamento YAML encontrado em local inválido.")
            stack.append((indent, next_container))
        elif isinstance(parent, dict):
            parent[key] = _parse_scalar(value)
        else:
            raise ValueError("Mapeamento YAML encontrado dentro de lista escalar.")
    return root


def _next_meaningful_line_is_list(lines: list[str], current_index: int) -> bool:
    current_line = lines[current_index]
    current_indent = len(current_line) - len(current_line.lstrip(" "))
    for line in lines[current_index + 1 :]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        return indent > current_indent and line.strip().startswith("- ")
    return False


def _split_key_value(line: str) -> tuple[str, str]:
    key, separator, value = line.partition(":")
    if separator == "":
        raise ValueError(f"Linha YAML inválida: {line}")
    return key.strip(), value.strip()


def _parse_scalar(value: str) -> Any:
    if value == "true":
        return True
    if value == "false":
        return False
    if value.startswith("[") and value.endswith("]"):
        inside = value[1:-1].strip()
        if not inside:
            return []
        return [_parse_scalar(item.strip()) for item in inside.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value
