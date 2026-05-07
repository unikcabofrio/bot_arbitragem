from __future__ import annotations

import argparse
import logging

from .config import load_config
from .engine import ArbitrageEngine
from .exchanges import build_exchange


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bot de arbitragem automatizada entre exchanges.")
    parser.add_argument("--config", default="config.yaml", help="Caminho do arquivo YAML de configuração.")
    parser.add_argument("--once", action="store_true", help="Executa apenas uma varredura e encerra.")
    parser.add_argument("--log-level", default="INFO", help="Nível de log: DEBUG, INFO, WARNING, ERROR.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    config = load_config(args.config)
    exchanges = [build_exchange(exchange_config) for exchange_config in config.exchanges]
    engine = ArbitrageEngine(config, exchanges)
    if args.once:
        engine.run_once()
    else:
        engine.run_forever()


if __name__ == "__main__":
    main()
