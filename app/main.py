import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status

from app import database
from app.schemas import AlertIn, AlertOut, WebhookResponse

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("webhook")

PROCESSING_DELAY_SECONDS = 3


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await database.create_pool()
    yield
    await app.state.pool.close()


app = FastAPI(title="Webhook Processor", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook", response_model=WebhookResponse)
async def receive_webhook(alert: AlertIn, request: Request, response: Response):
    pool = request.app.state.pool

    # Idempotency: senders often retry. Skip the heavy work if already processed.
    existing = await database.get_alert(pool, alert.event_id)
    if existing:
        logger.info("Duplicate event %s ignored", alert.event_id)
        return {"status": "duplicate", "alert": dict(existing)}

    logger.info("Processing event %s from %s", alert.event_id, alert.source)
    # Simulated heavy processing. asyncio.sleep (not time.sleep) so the event
    # loop stays free to serve other requests during the delay.
    await asyncio.sleep(PROCESSING_DELAY_SECONDS)

    row = await database.insert_alert(pool, alert)
    if row is None:
        # Another request with the same event_id won the race while we slept.
        existing = await database.get_alert(pool, alert.event_id)
        return {"status": "duplicate", "alert": dict(existing)}

    response.status_code = status.HTTP_201_CREATED
    return {"status": "processed", "alert": dict(row)}


@app.get("/alerts", response_model=list[AlertOut])
async def get_alerts(request: Request):
    rows = await database.list_alerts(request.app.state.pool)
    return [dict(r) for r in rows]
