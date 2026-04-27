from typing import Optional, List
from pydantic import HttpUrl

from app.schemas.base import HLTVBaseModel, AuditMixin

class TodayMatchesDetails(HLTVBaseModel):

    match_id: str
    match_url: Optional[HttpUrl] = None

    team1_name: Optional[str] = None
    team1_id: Optional[str] = None
    team1_logo: Optional[str] = None

    team2_name: Optional[str] = None
    team2_id: Optional[str] = None
    team2_logo: Optional[str] = None

    tournament_name: Optional[str] = None
    tournament_id: Optional[str] = None
    tournament_logo: Optional[str] = None

    match_timestamp: Optional[float] = None

class TodayMatches(HLTVBaseModel, AuditMixin):


    match_count: int = 0
    matches: List[TodayMatchesDetails] = [] 