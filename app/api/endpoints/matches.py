from typing import Annotated

from fastapi import APIRouter, Query

from app.schemas.matches.liveMatches import LiveMatches
from app.schemas.matches.todayMatches import TodayMatches
from app.services.matches.liveMatches import HLTVLiveMatches
from app.services.matches.todayMatches import HLTVTodayMatches
from app.utils.utils import get_common_timezones

router = APIRouter()


@router.get("/live", response_model=LiveMatches, response_model_exclude_none=True)
def get_live_matches():

    hltv = HLTVLiveMatches()
    return hltv.get_live_matches()


@router.get("/today/", response_model=TodayMatches, response_model_exclude_none=True)
def get_today_matches(
    timezone: Annotated[str, Query(description="list of timezones  (first is used)", enum=get_common_timezones())] = "UTC",
):
    hltv = HLTVTodayMatches()
    return hltv.get_today_matches(user_timezone=timezone)
