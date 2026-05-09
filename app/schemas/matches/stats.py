# app/schemas/matches/stats.py

from typing import List, Optional
from pydantic import HttpUrl

from app.schemas.base import HLTVBaseModel, AuditMixin


class PlayerStatSide(HLTVBaseModel):

    index: int
    side: str
    kd: str
    swing: str
    adr: str
    kast: str
    rating: str


class TeamSideStats(HLTVBaseModel):

    ct_side: List[PlayerStatSide]
    t_side: List[PlayerStatSide]


class MapStats(HLTVBaseModel):

    map_index: int
    team1: TeamSideStats
    team2: TeamSideStats


class TeamInfo(HLTVBaseModel):

    name: str
    id: Optional[str]
    score: str


class EventInfo(HLTVBaseModel):
    """Event information."""

    name: Optional[str]
    id: Optional[str]


class MatchInfo(HLTVBaseModel):
    """Match information."""

    team1: TeamInfo
    team2: TeamInfo
    match_date: Optional[str]
    event: EventInfo


class MatchStatsData(HLTVBaseModel):
    """Complete match statistics."""

    match_info: MatchInfo
    map_pool: List[str]
    map_stats: List[MapStats]


class MatchStats(HLTVBaseModel, AuditMixin):
    """Match stats API response."""

    match_id: str
    stats: MatchStatsData