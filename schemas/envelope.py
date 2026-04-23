from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime, timezone
import uuid


class EventEnvelope(BaseModel):
    schema_version: str = "1.0"
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: Literal["telemetry", "ioc", "alert", "hunt_finding", "action"]
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    producer: str = "inspector"
    severity: Literal["low", "medium", "high", "critical"]
    data: Optional[dict] = None
