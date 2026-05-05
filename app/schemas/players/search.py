from typing import TYPE_CHECKING

from app.schemas.base import AuditMixin, HLTVBaseModel

if TYPE_CHECKING:
    from pydantic import HttpUrl


class PlayerSearchResult(HLTVBaseModel):
    id: str
    name: str
    nickname: str
    nationality: str
    flag_url: HttpUrl
    url: HttpUrl


class PlayerSearch(HLTVBaseModel, AuditMixin):
    query: str
    results: list[PlayerSearchResult] | None = None
