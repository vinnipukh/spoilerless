from pydantic import BaseModel, Field


class SeriesResponse(BaseModel):
    id: str
    title: str
    slug: str


class EpisodeResponse(BaseModel):
    id: str
    series_id: str
    season_number: int = Field(ge=1)
    episode_number: int = Field(ge=1)
    episode_order: int = Field(ge=1)
    code: str
    title: str
    visible_from_order: int = Field(ge=1)
    # D-21 additive display shape (07-03): the API always returns the
    # already-masked value in `title` when a boundary is applied (backward
    # compatible), and additionally exposes the masked display_title plus the
    # unlock/view flags so the frontend can render watched/current/locked
    # states without any client-side masking logic (D-08).
    display_title: str | None = None
    is_unlocked: bool | None = None
    is_current_view: bool | None = None
