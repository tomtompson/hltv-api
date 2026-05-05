from typing import TYPE_CHECKING

from app.schemas.base import AuditMixin, HLTVBaseModel

if TYPE_CHECKING:
    from pydantic import HttpUrl


class trophiesDetails(HLTVBaseModel):
    tournament_id: str
    tournament_name: str
    tournament_url: HttpUrl
    tournament_img_url: HttpUrl


class PlayerTrophies(HLTVBaseModel, AuditMixin):
    id: str
    trophy_count: int | None = None
    trophies: list[trophiesDetails] | None = None
