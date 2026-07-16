# Live dry-run dashboard server

Small `aiohttp` server for the VPS/subdomain version of the BTC futures dry-run portfolio page.

It serves:

```text
GET /            live dashboard
GET /api/status  server-side proxy to AWS API Gateway /status
GET /api/config  public frontend config
GET /health      VPS/reverse-proxy health check
```

The browser never needs the AWS status URL. The server reads it from an environment variable and
proxies read-only status snapshots to the frontend.

## Local smoke

Fixture mode:

```powershell
uv run python scripts/portfolio_live/serve_live_dry_run_dashboard.py `
  --fixture `
  --host 127.0.0.1 `
  --port 8080
```

AWS-backed mode:

```powershell
$env:TRADING_FRAMEWORK_STATUS_URL="https://example.execute-api.eu-north-1.amazonaws.com/status"

uv run python scripts/portfolio_live/serve_live_dry_run_dashboard.py `
  --host 127.0.0.1 `
  --port 8080
```

Open:

```text
http://127.0.0.1:8080
```

## VPS process

Example Linux command:

```bash
cd /opt/research-trading-framework
export TRADING_FRAMEWORK_STATUS_URL="https://example.execute-api.eu-north-1.amazonaws.com/status"
uv run python scripts/portfolio_live/serve_live_dry_run_dashboard.py \
  --host 127.0.0.1 \
  --port 8080
```

Keep `--host 127.0.0.1` when nginx/Caddy is the public entry point.

## nginx reverse proxy sketch

```nginx
server {
    server_name dryrun.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Add TLS with Certbot or your VPS provider's preferred certificate flow.

## systemd sketch

```ini
[Unit]
Description=Trading Framework live dry-run dashboard
After=network-online.target

[Service]
WorkingDirectory=/opt/research-trading-framework
Environment=TRADING_FRAMEWORK_STATUS_URL=https://example.execute-api.eu-north-1.amazonaws.com/status
ExecStart=/usr/bin/uv run python scripts/portfolio_live/serve_live_dry_run_dashboard.py --host 127.0.0.1 --port 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Live behavior

The frontend polls `/api/status` every few seconds. Each snapshot updates:

- BTCUSDT candles built from incoming price snapshots,
- simulated fill markers on the price chart,
- paper equity curve,
- current runtime/market/account/position cards,
- last simulated trades and recent orders tables.

The current AWS status API returns the latest state plus bounded recent orders/fills. The browser keeps
the rolling chart history while it remains open. A later backend increment can persist a rolling candle
and equity cache on the VPS if the page needs to survive refreshes with longer history.
