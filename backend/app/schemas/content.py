from pydantic import BaseModel

from app.models.content import ContentSummary


class ContentListResponse(BaseModel):
    items: list[ContentSummary]
    total: int
    limit: int
    offset: int
