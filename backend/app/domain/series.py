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