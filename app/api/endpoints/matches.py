from fastapi import APIRouter

from app.schemas.matches.liveMatches import LiveMatches
from app.schemas.matches.todayMatches import TodayMatches

from app.services.matches.liveMatches import HLTVLiveMatches
from app.services.matches.todayMatches import HLTVTodayMatches

router = APIRouter()

@router.get("/live_matches", response_model=LiveMatches, response_model_exclude_none=True)
def get_live_matches():
    
    hltv = HLTVLiveMatches()
    found_matches = hltv.get_live_matches()
    return found_matches

@router.get("/todayMatches", response_model=TodayMatches, response_model_exclude_none=True)
def get_today_matches():
    hltv = HLTVTodayMatches()
    found_matches = hltv.get_today_matches()
    return found_matches