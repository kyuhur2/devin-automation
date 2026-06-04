from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


TaskStatus = Literal[
    "received",
    "session_started",
    "failed",
    "refreshed",
]


class SimulateRequest(BaseModel):
    issue_url: str
    repo: str | None = None


class Task(BaseModel):
    task_id: str
    issue_url: str
    repo: str
    status: TaskStatus
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    devin_session_id: str | None = None
    devin_session_url: str | None = None
    devin_status: str | None = None
    devin_status_detail: str | None = None
    pull_requests: list[dict[str, Any]] = Field(default_factory=list)

    error: str | None = None
    raw_devin_response: dict[str, Any] | None = None  # kept for debugging/demo transparency
