# Polymarket Gap Bot v1

Read-only monitor for potential pricing gaps between Binance BTC price action and Polymarket BTC markets.

## Current status
- Python scaffold created
- Public Binance and Polymarket Gamma endpoints wired
- Logs market snapshots and positive-edge candidates
- Supports targeting a specific event page via `POLYMARKET_EVENT_SLUG`
- Can auto-discover the latest BTC 5m up/down event from the `btc-up-or-down-5m` series catalog
- Uses configurable market search terms as a fallback when no explicit event slug is supplied

## Run

```bash
python3 -m polymarket_gap_bot.main
```

## Environment variables

- `POLYMARKET_EVENT_SLUG` example: `btc-updown-5m-1775496300`
- `POLYMARKET_SERIES_SLUG` default: `btc-up-or-down-5m`
- `SERIES_SEARCH_LIMIT` default: `1200`
- `MARKET_SEARCH_TERMS` default: `bitcoin,btc,5m,5 minute,5-minute,binance`
- `POLL_INTERVAL_SECONDS` default: `5`
- `MIN_SECONDS_TO_EXPIRY` default: `30`
- `MIN_GROSS_EDGE` default: `0.05`
- `MIN_NET_EDGE` default: `0.03`
- `MAX_SPREAD` default: `0.05`

## Output
- `data/market_snapshots.jsonl`
- `data/signals.csv`

## Important caveats
- The parser currently uses heuristics from question/description text.
- Up/down 5m markets are now detectable from an explicit event slug, but the fair-value model for these contracts is still a placeholder and needs refinement.
- NO-side bid/ask is inferred from YES quotes when explicit values are unavailable.
- This is for signal collection only, not execution.
- The exact Polymarket BTC 5m contract discovery path should be tightened before relying on it.
