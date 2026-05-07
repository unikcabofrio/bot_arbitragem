# Bot de Arbitragem Automatizada

Bot em Python para identificar oportunidades de arbitragem entre duas ou mais exchanges e executar ordens de compra/venda de forma automática. Por segurança, o padrão é `dry_run: true`, que simula as ordens sem enviar operações reais.

> Aviso: arbitragem envolve risco de execução parcial, latência, bloqueios de saque, liquidez insuficiente, taxas variáveis e perda financeira. Comece sempre em sandbox ou dry-run.

## Recursos

- Varredura de múltiplos pares (`BTC/USDT`, `ETH/USDT`, etc.).
- Cálculo de lucro líquido estimado com taxas e slippage.
- Limite máximo por operação em moeda de cotação.
- Checagem de saldo disponível na exchange compradora e do ativo-base na exchange vendedora.
- Adaptador `mock` para testes locais sem credenciais.
- Adaptador `ccxt` opcional para exchanges suportadas pela biblioteca CCXT.

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test,yaml]'
```

A configuração funciona com um parser YAML simples embutido. Para suporte YAML completo, instale o extra `yaml`. Para operar com exchanges reais via CCXT:

```bash
pip install -e '.[ccxt]'
```

## Uso rápido em simulação

```bash
bot-arbitragem --config examples/config.mock.yaml --once
```

Para rodar continuamente:

```bash
bot-arbitragem --config examples/config.mock.yaml
```

## Configuração

Copie `examples/config.mock.yaml` para `config.yaml` e ajuste:

```yaml
dry_run: true
symbols:
  - BTC/USDT
quote_asset: USDT
risk:
  min_net_profit_pct: 0.20
  max_trade_quote: 100
  slippage_pct: 0.03
exchanges:
  - name: binance
    adapter: ccxt
    api_key_env: BINANCE_API_KEY
    api_secret_env: BINANCE_API_SECRET
    fee_rate: 0.001
    sandbox: true
  - name: kraken
    adapter: ccxt
    api_key_env: KRAKEN_API_KEY
    api_secret_env: KRAKEN_API_SECRET
    fee_rate: 0.0026
    sandbox: true
```

As credenciais devem ficar em variáveis de ambiente. Use `.env.example` apenas como modelo e nunca faça commit de chaves reais.

## Como liberar operações reais

1. Rode `pytest` e confirme que os testes passam.
2. Execute por várias horas com `dry_run: true`.
3. Use `sandbox: true` quando a exchange suportar sandbox.
4. Configure saldos pequenos nas exchanges.
5. Defina `BOT_DRY_RUN=false` ou `dry_run: false` somente quando estiver pronto.

## Arquitetura

- `bot_arbitragem.config`: carrega e valida YAML.
- `bot_arbitragem.exchanges`: implementa adaptadores `mock` e `ccxt`.
- `bot_arbitragem.engine`: encontra oportunidades, calcula lucro líquido e cria ordens.
- `bot_arbitragem.cli`: interface de linha de comando.
