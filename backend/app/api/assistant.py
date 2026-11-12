from fastapi import APIRouter

from app.agents.base import AgentResponse, ChatRequest
from app.api.deps import AppContainer

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/chat", response_model=AgentResponse)
def chat(container: AppContainer, request: ChatRequest) -> AgentResponse:
    """Run one assistant turn. The assistant can read content and draft pending proposals only."""
    return container.agent.chat(request)
