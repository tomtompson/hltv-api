from dataclasses import dataclass
from typing import List, Dict, Optional
from fastapi import HTTPException

from app.services.base import HLTVBase
from app.utils.utils import extract_from_url, parse_date
from app.utils.xpath import Teams


@dataclass
class HLTVTeamUpcomingMatches(HLTVBase):
    """
    class for getting upcoming matches for a team.
    
    attributes:
        team_id: hltv team id
    """
    
    team_id: str

    # ==================== INIT METHODS ====================

    def __post_init__(self) -> None:
        """setup upcoming matches with team id."""
        super().__post_init__()
        
        url = f"https://www.hltv.org/team/{self.team_id}/who#tab-matchesBox"
        self.URL = url
        self.response["team_id"] = self.team_id
        
        self.logger.info(f"loading upcoming matches for team {self.team_id}")
        
        # load page
        self.page = self.request_url_page()
        
        self.logger.info(f"team page loaded for {self.team_id}")

    # ==================== MATCH ID METHODS ====================

    def get_upcoming_match_ids(self) -> List[str]:
        """
        get list of upcoming match ids from team page.
        
        returns:
            list of match id strings
        """
        match_ids = []
        
        try:
            self.logger.debug("extracting upcoming match ids")
            
            # get match rows
            upcoming_rows = self.get_elements_by_xpath(Teams.UpcomingMatches.UPCOMING_MATCHES_ROW)
            self.logger.debug(f"found {len(upcoming_rows)} upcoming match rows")
            
            # extract urls from rows
            match_urls = self.get_all_by_xpath(Teams.UpcomingMatches.MATCH_URL, element=upcoming_rows)
            self.logger.debug(f"found {len(match_urls)} match urls")
            
            # extract ids from urls
            for i, url in enumerate(match_urls):
                try:
                    match_id = extract_from_url(url, 'id')
                    if match_id:
                        match_ids.append(match_id)
                    else:
                        self.logger.warning(f"could not extract id from url {i}: {url}")
                        
                except Exception as e:
                    self.logger.error(f"error extracting id from url {i}: {e}")
                    continue
            
            self.logger.info(f"extracted {len(match_ids)} upcoming match ids for team {self.team_id}")
            
        except Exception as e:
            self.logger.error(f"error getting upcoming match ids: {e}")
            
        return match_ids

    # ==================== MATCH PARSING METHODS ====================

    def __parse_single_match(self, match_id: str) -> Optional[Dict]:
        """
        parse data for a single match.
        
        args:
            match_id: hltv match id
            
        returns:
            dict with match data or None if error
        """
        try:
            match_url = f"https://www.hltv.org/matches/{match_id}"
            self.logger.debug(f"fetching match page: {match_url}")
            
            # load match page
            match_page = self.request_url_page(match_url)
            
            # TODO: add match parsing logic here
            # this will depend on your match xpaths
            # for now, return basic structure
            
            match_data = {
                "id": match_id,
                "url": match_url,
                # add more fields as you implement match parsing
            }
            
            self.logger.debug(f"parsed match {match_id}")
            return match_data
            
        except Exception as e:
            self.logger.error(f"error parsing match {match_id}: {e}")
            return None

    def parse_upcoming_matches(self) -> List[Dict]:
        """
        parse all upcoming matches for team.
        
        returns:
            list of match dictionaries
        """
        matches = []
        
        try:
            # get match ids
            match_ids = self.get_upcoming_match_ids()
            
            if not match_ids:
                self.logger.info(f"no upcoming matches found for team {self.team_id}")
                return []
            
            self.logger.info(f"parsing {len(match_ids)} upcoming matches")
            
            # parse each match
            for match_id in match_ids:
                match_data = self.__parse_single_match(match_id)
                if match_data:
                    matches.append(match_data)
                    
            self.logger.info(f"successfully parsed {len(matches)} upcoming matches")
            
        except Exception as e:
            self.logger.error(f"error parsing upcoming matches: {e}")
            
        return matches

    # ==================== PUBLIC METHODS ====================

    def get_team_upcoming_matches(self) -> dict:
        """
        get upcoming matches for team.
        
        returns:
            dict with team id and matches list
        """
        try:
            matches = self.parse_upcoming_matches()
            
            self.response["team_id"] = self.team_id
            self.response["upcoming_matches"] = matches
            self.response["match_count"] = len(matches)
            
            self.logger.info(f"returning {len(matches)} upcoming matches for team {self.team_id}")
            
        except Exception as e:
            self.logger.error(f"error in get_team_upcoming_matches: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"error getting team upcoming matches: {str(e)}"
            )
        
        return self.response