# Webhook Processor

A FastAPI service that receives alert webhooks, simulates heavy processing
(3-second delay), persists them in PostgreSQL, and exposes them via a REST API.

**Stack:** Python 3.12, FastAPI, asyncpg, PostgreSQL 16, Docker Compose.

## Run

Requires Docker and Docker Compose.

```bash
git clone https://github.com/mariambehairy/webhook-processor
cd webhook-processor
docker compose up --build
```

The API is then available at http://localhost:8000 (interactive docs at
http://localhost:8000/docs). The database table is created automatically on startup.

To stop: `docker compose down` (add `-v` to also delete the stored data).

## Endpoints

### `POST /webhook`

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"event_id": "evt_98765", "source": "server_1", "message": "High CPU", "timestamp": "2026-11-11T08:00:00Z"}'
```

- `201 Created` - alert processed (after ~3 seconds) and stored.
- `200 OK` with `"status": "duplicate"` - this `event_id` was already processed; nothing is re-processed or duplicated.
- `422` - invalid or missing fields.

### `GET /alerts`

```bash
curl http://localhost:8000/alerts
```

Returns a JSON list of all processed alerts, in the order they were processed.

### `GET /health`

Simple liveness check.

## Design decisions

- **Non-blocking delay:** the simulated processing uses `await asyncio.sleep(3)`,
  not `time.sleep`, so the server can keep handling other requests meanwhile.
  You can verify by sending several different webhooks at once: they all finish in about 3 seconds total, not 3 seconds each.
- **Idempotency:** `event_id` has a `UNIQUE` constraint, and the insert uses
  `ON CONFLICT DO NOTHING`. Webhook senders commonly retry, so duplicates are
  handled safely, including two identical requests arriving at the same time.
- **Persistence:** PostgreSQL data lives in a named Docker volume (`pgdata`),
  so alerts survive container restarts.
- **Startup ordering:** the database has a healthcheck, the app waits for it, and
  the app also retries its initial connection.
