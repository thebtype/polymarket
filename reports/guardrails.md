# Trading Guardrails

- Mode: paper
- Reference portfolio: $1000.00
- Max daily loss: 10.00% ($100.00 at current reference portfolio)
- Max position size: 2.00% ($20.00 at current reference portfolio)
- Max consecutive losses: 5
- Min net edge for live trading: 0.20
- Min seconds to expiry for live trading: 120
- Max spread for live trading: 0.015
- Kill switch enabled: True
- Manual re-enable after kill: True
- Dedicated wallet required: True
- Separate execution module required: True

## Operating notes
- Do not go live from monitor code directly; require a separate execution module.
- Stop trading immediately after hitting max daily loss, max consecutive losses, or any unexpected fill behavior.
- Position sizing should scale with current portfolio, not fixed dollars.
- Require a dedicated wallet with isolated permissions before any live order flow.
- Manual re-enable required after any kill-switch trigger.
