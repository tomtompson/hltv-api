# app/services/matches/match_stats.py

from dataclasses import dataclass

from fastapi import HTTPException

from app.services.base import HLTVBase
from app.utils.utils import extract_from_url
from app.utils.xpath import Matches


@dataclass
class HLTVMatchStats(HLTVBase):
    """Class for getting detailed match statistics from HLTV.

    Attributes:
        match_id: HLTV match ID
    """

    match_id: str

    # ==================== INIT METHODS ====================

    def __post_init__(self) -> None:
        """Set up match stats with match ID."""
        super().__post_init__()

        self.URL = f"https://www.hltv.org/matches/{self.match_id}/na-vs-na"
        self.response["match_id"] = self.match_id

        self.logger.info(f"loading match stats for match {self.match_id}")

        self.page = self.request_url_page()

        self.logger.info(f"match page loaded for {self.match_id}")

    # ==================== PARSING METHODS ====================

    def __parse_match_info(self) -> dict:
        """
        Parse basic match information (teams, scores, date, event).

        Returns:
            dict: match info with team names, IDs, scores, date, and event details.
        """
        data = {}

        try:
            # Team 1 info
            team1_name = self.get_text_by_xpath(Matches.MatchStats.TEAM1_NAME)
            team1_id = self.get_text_by_xpath(Matches.MatchStats.TEAM1_ID, attribute="href")
            team1_id = extract_from_url(team1_id, "id") if team1_id else None
            team1_score = self.get_text_by_xpath(Matches.MatchStats.TEAM1_SCORE)

            # Team 2 info
            team2_name = self.get_text_by_xpath(Matches.MatchStats.TEAM2_NAME)
            team2_id = self.get_text_by_xpath(Matches.MatchStats.TEAM2_ID, attribute="href")
            team2_id = extract_from_url(team2_id, "id") if team2_id else None
            team2_score = self.get_text_by_xpath(Matches.MatchStats.TEAM2_SCORE)

            # Match date and event
            match_date = self.get_text_by_xpath(Matches.MatchStats.MATCH_DATE)
            event_name = self.get_text_by_xpath(Matches.MatchStats.EVENT_NAME)
            event_id = self.get_text_by_xpath(Matches.MatchStats.EVENT_ID, attribute="href")
            event_id = extract_from_url(event_id, "id") if event_id else None

            data = {
                "team1": {
                    "name": team1_name or "",
                    "id": team1_id,
                    "score": team1_score or "0",
                },
                "team2": {
                    "name": team2_name or "",
                    "id": team2_id,
                    "score": team2_score or "0",
                },
                "match_date": match_date,
                "event": {
                    "name": event_name,
                    "id": event_id,
                },
            }

            self.logger.debug(
                f"match info: {team1_name} vs {team2_name}, score: {team1_score}-{team2_score}",
            )

        except Exception as e:
            self.logger.exception(f"error parsing match info: {e}")
            data = {
                "team1": {"name": "", "id": None, "score": "0"},
                "team2": {"name": "", "id": None, "score": "0"},
                "match_date": None,
                "event": {"name": None, "id": None},
            }

        return data

    def __parse_map_pool(self) -> list[str]:
        """
        Parse the map pool for the series.

        Returns:
            list[str]: list of map names in the series.
        """
        maps = []

        try:
            # Try to get individual map names first
            map1 = self.get_text_by_xpath(Matches.MatchStats.MAP1_NAME)
            map2 = self.get_text_by_xpath(Matches.MatchStats.MAP2_NAME)
            map3 = self.get_text_by_xpath(Matches.MatchStats.MAP3_NAME)
            map4 = self.get_text_by_xpath(Matches.MatchStats.MAP4_NAME)
            map5 = self.get_text_by_xpath(Matches.MatchStats.MAP5_NAME)

            maps = [m for m in [map1, map2, map3, map4, map5] if m]

            if not maps:
                # Fallback: try generic map pool
                maps = self.get_all_by_xpath(Matches.MatchStats.MAP_POOL)

            self.logger.debug(f"found {len(maps)} maps: {maps}")

        except Exception as e:
            self.logger.exception(f"error parsing map pool: {e}")

        return maps

    def __parse_player_stats_by_map(self) -> list[dict]:
        """
        Parse player statistics for each map and side (CT/T).

        Returns:
            list[dict]: list of map stats dicts with team1_stats and team2_stats.
        """
        map_stats_list = []

        try:
            # Get all map containers (each has 6 tables: 3 for team1, 3 for team2)
            map_containers = self.get_elements_by_xpath(
                Matches.MatchStats.MAP_CONTAINERS,
            )

            self.logger.debug(f"found {len(map_containers)} map containers")

            for map_idx, map_container in enumerate(map_containers):
                try:
                    map_stats = self.__parse_single_map_stats(map_container, map_idx)
                    if map_stats:
                        map_stats_list.append(map_stats)
                except Exception as e:
                    self.logger.exception(
                        f"error parsing map {map_idx} stats: {e}",
                    )
                    continue

        except Exception as e:
            self.logger.exception(f"error parsing player stats by map: {e}")

        return map_stats_list

    def __parse_single_map_stats(self, map_element, map_idx: int) -> dict | None:
        """
        Parse statistics for a single map.

        Args:
            map_element: lxml element for the map container.
            map_idx (int): map index (0-based).

        Returns:
            dict | None: map stats dict with team1 and team2 player stats by side.
        """
        try:
            map_data = {
                "map_index": map_idx,
                "team1": {"ct_side": [], "t_side": []},
                "team2": {"ct_side": [], "t_side": []},
            }

            # Parse Team 1 CT side
            ct_players_t1 = self.__parse_team_side_stats(
                map_element,
                Matches.MatchStats.TEAM1_CT_PLAYER_KD,
                Matches.MatchStats.TEAM1_CT_PLAYER_SWING,
                Matches.MatchStats.TEAM1_CT_PLAYER_ADR,
                Matches.MatchStats.TEAM1_CT_PLAYER_KAST,
                Matches.MatchStats.TEAM1_CT_PLAYER_RATING,
                "ct",
            )
            map_data["team1"]["ct_side"] = ct_players_t1

            # Parse Team 1 T side
            t_players_t1 = self.__parse_team_side_stats(
                map_element,
                Matches.MatchStats.TEAM1_T_PLAYER_KD,
                Matches.MatchStats.TEAM1_T_PLAYER_SWING,
                Matches.MatchStats.TEAM1_T_PLAYER_ADR,
                Matches.MatchStats.TEAM1_T_PLAYER_KAST,
                Matches.MatchStats.TEAM1_T_PLAYER_RATING,
                "t",
            )
            map_data["team1"]["t_side"] = t_players_t1

            # Parse Team 2 CT side
            ct_players_t2 = self.__parse_team_side_stats(
                map_element,
                Matches.MatchStats.TEAM2_CT_PLAYER_KD,
                Matches.MatchStats.TEAM2_CT_PLAYER_SWING,
                Matches.MatchStats.TEAM2_CT_PLAYER_ADR,
                Matches.MatchStats.TEAM2_CT_PLAYER_KAST,
                Matches.MatchStats.TEAM2_CT_PLAYER_RATING,
                "ct",
            )
            map_data["team2"]["ct_side"] = ct_players_t2

            # Parse Team 2 T side
            t_players_t2 = self.__parse_team_side_stats(
                map_element,
                Matches.MatchStats.TEAM2_T_PLAYER_KD,
                Matches.MatchStats.TEAM2_T_PLAYER_SWING,
                Matches.MatchStats.TEAM2_T_PLAYER_ADR,
                Matches.MatchStats.TEAM2_T_PLAYER_KAST,
                Matches.MatchStats.TEAM2_T_PLAYER_RATING,
                "t",
            )
            map_data["team2"]["t_side"] = t_players_t2

            self.logger.debug(
                f"map {map_idx}: T1 CT={len(ct_players_t1)}, T1 T={len(t_players_t1)}, "
                f"T2 CT={len(ct_players_t2)}, T2 T={len(t_players_t2)}",
            )

            return map_data

        except Exception as e:
            self.logger.exception(f"error parsing single map stats: {e}")
            return None

    def __parse_team_side_stats(
        self,
        map_element,
        kd_xpath: str,
        swing_xpath: str,
        adr_xpath: str,
        kast_xpath: str,
        rating_xpath: str,
        side: str,
    ) -> list[dict]:
        """
        Parse player stats for a specific team and side.

        Args:
            map_element: lxml element for the map.
            kd_xpath (str): XPath for K/D ratio.
            swing_xpath (str): XPath for swing stat.
            adr_xpath (str): XPath for ADR.
            kast_xpath (str): XPath for KAST.
            rating_xpath (str): XPath for rating.
            side (str): "ct" or "t".

        Returns:
            list[dict]: list of player stats dicts.
        """
        players_stats = []

        try:
            kd_list = self.get_all_by_xpath(kd_xpath, element=map_element)
            swing_list = self.get_all_by_xpath(swing_xpath, element=map_element)
            adr_list = self.get_all_by_xpath(adr_xpath, element=map_element)
            kast_list = self.get_all_by_xpath(kast_xpath, element=map_element)
            rating_list = self.get_all_by_xpath(rating_xpath, element=map_element)

            # Zip all stats together
            for idx, (kd, swing, adr, kast, rating) in enumerate(
                zip(kd_list, swing_list, adr_list, kast_list, rating_list, strict=False),
            ):
                player_stat = {
                    "index": idx,
                    "side": side,
                    "kd": kd or "",
                    "swing": swing or "",
                    "adr": adr or "",
                    "kast": kast or "",
                    "rating": rating or "",
                }
                players_stats.append(player_stat)

            self.logger.debug(f"parsed {len(players_stats)} players for {side} side")

        except Exception as e:
            self.logger.exception(f"error parsing team side stats ({side}): {e}")

        return players_stats

    def __parse_all_match_stats(self) -> dict:
        """
        Parse all match statistics.

        Returns:
            dict: complete match stats with info, maps, and player stats.
        """
        self.logger.info(f"parsing all stats for match {self.match_id}")

        try:
            match_info = self.__parse_match_info()
            map_pool = self.__parse_map_pool()
            map_stats = self.__parse_player_stats_by_map()

            all_stats = {
                "match_info": match_info,
                "map_pool": map_pool,
                "map_stats": map_stats,
            }

            self.logger.info(
                f"stats parsed: {len(map_pool)} maps, {len(map_stats)} map stats entries",
            )
            return all_stats

        except Exception as e:
            self.logger.exception(f"error parsing all match stats: {e}")
            return {
                "match_info": {
                    "team1": {"name": "", "id": None, "score": "0"},
                    "team2": {"name": "", "id": None, "score": "0"},
                    "match_date": None,
                    "event": {"name": None, "id": None},
                },
                "map_pool": [],
                "map_stats": [],
            }

    # ==================== PUBLIC METHODS ====================

    def get_match_stats(self) -> dict:
        """
        Get complete match statistics.

        Returns:
            dict: match_id and detailed stats including teams, maps, and player performance.
        """
        try:
            match_stats = self.__parse_all_match_stats()

            self.response["match_id"] = self.match_id
            self.response["stats"] = match_stats

            self.logger.info(f"match stats retrieved successfully for {self.match_id}")
            return self.response

        except Exception as e:
            self.logger.exception(f"error getting match stats: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"failed to retrieve match stats: {str(e)}",
            )
