from collections.abc import Callable

from app.agents.base import AgentProvider, AgentResponse, ChatRequest, ToolRunner
from app.agents.mock import MockAgent
from app.config import Settings
from app.tools.base import ToolContext
from app.tools.registry import ToolRegistry

ContextFactory = Callable[[], ToolContext]


def build_provider(settings: Settings) -> AgentProvider:
    if settings.agent_provider == "mock":
        return MockAgent()
    raise ValueError(f"Unsupported agent provider: {settings.agent_provider}")


class AgentService:
    """Runs one assistant turn with a fresh, budgeted ToolRunner per request."""

    def __init__(
        self,
        provider: AgentProvider,
        registry: ToolRegistry,
        context_factory: ContextFactory,
        max_tool_calls: int,
    ) -> None:
        self._provider = provider
        self._registry = registry
        self._context_factory = context_factory
        self._max_tool_calls = max_tool_calls

    @property
    def provider_name(self) -> str:
        return self._provider.name

    def chat(self, request: ChatRequest) -> AgentResponse:
        runner = ToolRunner(self._registry, self._context_factory(), self._max_tool_calls)
        return self._provider.respond(request, runner)
