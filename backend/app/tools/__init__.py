"""Agent tools. `build_default_registry` returns the complete allowlist."""

from typing import Any

from app.services.audit import AuditService
from app.tools.audit_tools import (
    CHECK_INTERNAL_LINKS,
    CHECK_METADATA,
    FIND_DUPLICATE_TITLES,
    FIND_OUTDATED_CONTENT,
)
from app.tools.base import Tool
from app.tools.content_tools import GET_CONTENT_BY_ID, SEARCH_CONTENT
from app.tools.proposal_tools import CREATE_EDIT_PROPOSAL
from app.tools.registry import ToolRegistry

READ_TOOLS: tuple[Tool[Any, Any], ...] = (
    SEARCH_CONTENT,
    GET_CONTENT_BY_ID,
    FIND_OUTDATED_CONTENT,
    FIND_DUPLICATE_TITLES,
    CHECK_METADATA,
    CHECK_INTERNAL_LINKS,
)
PROPOSAL_TOOLS: tuple[Tool[Any, Any], ...] = (CREATE_EDIT_PROPOSAL,)


def build_default_registry(audit: AuditService, **kwargs: Any) -> ToolRegistry:
    return ToolRegistry([*READ_TOOLS, *PROPOSAL_TOOLS], audit, **kwargs)
