import logging
from collections.abc import Callable

from app.agents.base import AgentProvider, AgentResponse, ChatRequest, ToolRunner
from app.agents.claude import ClaudeAgent, default_client_factory
from app.agents.mock import MockAgent
from app.config import Settings
from app.errors import ProviderUnavailableError
from app.models.activity import Actor, EventType
from app.services.audit import AuditService
from app.tools.base import ToolContext
from app.tools.registry import ToolRegistry

ContextFactory = Callable[[], ToolContext]
logger = logging.getLogger(__name__)


def build_provider(settings: Settings, registry: ToolRegistry) -> AgentProvider:
    if settings.agent_provider == "mock":
        return MockAgent()
    if settings.agent_provider == "claude":
        return ClaudeAgent(
            model=settings.claude_model,
            effort=settings.claude_effort,
            max_iterations=settings.claude_max_iterations,
            max_tokens=settings.claude_max_tokens,
            client_factory=default_client_factory(settings.claude_timeout_seconds),
            tool_specs=registry.describe(),
            use_fallbacks=settings.claude_fallbacks,
        )
    raise ValueError(f"Unsupported agent provider: {settings.agent_provider}")


class AgentService:
    """Runs one assistant turn with a fresh, budgeted ToolRunner per request."""

    def __init__(
        self,
        provider: AgentProvider,
        registry: ToolRegistry,
        context_factory: ContextFactory,
        max_tool_calls: int,
        audit: AuditService,
    ) -> None:
        self._audit = audit
        self._provider = provider
        self._registry = registry
        self._context_factory = context_factory
        self._max_tool_calls = max_tool_calls

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def provider_model(self) -> str | None:
        return getattr(self._provider, "model", None)

    def chat(self, request: ChatRequest) -> AgentResponse:
        runner = ToolRunner(self._registry, self._context_factory(), self._max_tool_calls)
        try:
            return self._provider.respond(request, runner)
        except ProviderUnavailableError as exc:
            self._log_error("provider_unavailable", exc.message, runner)
            raise
        except Exception:
            logger.exception("Assistant turn failed")
            self._log_error("error", "The assistant failed unexpectedly.", runner)
            raise

    def _log_error(self, status: str, message: str, runner: ToolRunner) -> None:
        self._audit.record(
            EventType.ERROR,
            actor=Actor.SYSTEM,
            status=status,
            details={
                "source": "assistant",
                "provider": self._provider.name,
                "message": message,
                "tool_calls_before_error": len(runner.calls),
            },
        )
