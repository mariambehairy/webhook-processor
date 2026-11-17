from datetime import datetime

from pydantic import BaseModel, Field


class AlertIn(BaseModel):
    event_id: str = Field(..., min_length=1, examples=["evt_98765"])
    source: str = Field(..., min_length=1, examples=["server_1"])
    message: str = Field(..., min_length=1, examples=["High CPU"])
    timestamp: datetime = Field(..., examples=["2026-11-11T08:00:00Z"])


class AlertOut(AlertIn):
    processed_at: datetime


class WebhookResponse(BaseModel):
    status: str
    alert: AlertOut
