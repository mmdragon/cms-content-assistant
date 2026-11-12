"""Wires repositories, services, and the tool registry for one app instance."""

from dataclasses import dataclass, field

from app.agents.service import AgentService, build_provider
from app.config import Settings
from app.repositories.activity import SQLiteActivityRepository
from app.repositories.proposals import SQLiteProposalRepository
from app.repositories.sqlite import SQLiteContentRepository
from app.services.audit import AuditService, Clock, utc_now
from app.services.proposals import ProposalService
from app.tools import build_default_registry
from app.tools.base import ToolContext
from app.tools.registry import ToolRegistry


@dataclass
class Container:
    settings: Settings
    content_repo: SQLiteContentRepository
    proposal_repo: SQLiteProposalRepository
    activity_repo: SQLiteActivityRepository
    audit: AuditService
    proposals: ProposalService
    tools: ToolRegistry
    agent: AgentService = field(init=False)

    def __post_init__(self) -> None:
        self.agent = AgentService(
            build_provider(self.settings),
            self.tools,
            self.tool_context,
            max_tool_calls=self.settings.agent_max_tool_calls,
        )

    def tool_context(self) -> ToolContext:
        return ToolContext(
            content_repo=self.content_repo,
            proposals=self.proposals,
            as_of=self.settings.audit_as_of(),
            site_base_url=self.settings.site_base_url,
        )


def build_container(settings: Settings, clock: Clock = utc_now) -> Container:
    db = settings.database_path
    content_repo = SQLiteContentRepository(db)
    proposal_repo = SQLiteProposalRepository(db)
    activity_repo = SQLiteActivityRepository(db)
    audit = AuditService(activity_repo, clock)
    proposals = ProposalService(content_repo, proposal_repo, audit, clock)
    tools = build_default_registry(audit, timeout_seconds=settings.tool_timeout_seconds)
    return Container(
        settings=settings,
        content_repo=content_repo,
        proposal_repo=proposal_repo,
        activity_repo=activity_repo,
        audit=audit,
        proposals=proposals,
        tools=tools,
    )
