from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]
    app: str
    version: str
    environment: str
    agent_provider: str
    agent_model: str | None = None
    demo_mode: bool
