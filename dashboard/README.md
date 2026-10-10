# Keel Dashboard (read-only)

A separate static UI over Keel's event trail and current state. It calls the
Keel server's read-only `/api/state` and `/api/events` with a bearer token.

## Run
1. Start the Keel server (see the repo README). For a browser on another origin,
   set `KEEL_CORS_ORIGINS` to the dashboard origin (or leave the default `*` for
   local dev):
   ```bash
   KEEL_CORS_ORIGINS=http://localhost:8050 python -m keel.server
   ```
2. Start the dashboard (its own process):
   ```bash
   python keel/dashboard/serve.py    # http://localhost:8050 (PORT to override)
   ```
3. Open it, enter the Keel URL (e.g. `http://localhost:8000`) and your bearer
   token (one person / one project), click **Connect**. Tick **auto** to poll
   every 5s.

The token is stored in your browser's `localStorage`. The dashboard never writes
to Keel — it only reads, and all data is scoped to the token's project.
