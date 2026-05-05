from typing import TYPE_CHECKING

from app.schemas.base import AuditMixin, HLTVBaseModel

if TYPE_CHECKING:
    from pydantic import HttpUrl


class TeamAchievementsDetails(HLTVBaseModel):
    id: str
    tournament_name: str
    placement: str
    team_event_stats: HttpUrl


class TeamAchievements(HLTVBaseModel, AuditMixin):
    id: str
    achievement_count: int | None
    team_achievements: list[TeamAchievementsDetails] | None
