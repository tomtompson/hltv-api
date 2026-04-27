from dataclasses import dataclass
from typing import List, Dict, Optional
from fastapi import HTTPException
from datetime import datetime, timezone, timedelta
import re
import pytz

from app.services.base import HLTVBase
from app.utils.xpath import Matches


@dataclass
class HLTVTodayMatches(HLTVBase):
    """
    class for getting today's and tomorrow's matches from hltv,
    with proper timezone handling for users.
    """

    def __post_init__(self) -> None:
        """setup today matches fetch."""
        super().__post_init__()
        self.URL = "https://www.hltv.org/matches"
        self.logger.info("loading today matches")
        self.page = self.request_url_page()
        self.logger.info("matches page loaded successfully")

    def _get_day_sections(self) -> List:
        """get all day sections from matches page."""
        sections = self.get_elements_by_xpath(Matches.TodayMatches.DAY_SECTION)
        self.logger.info(f"found {len(sections)} day sections")
        return sections

    def _get_day_headline_from_section(self, section_element) -> Optional[str]:
        """Extract day headline from a section element."""
        headline = self.get_text_by_xpath(".//div[contains(@class, 'matches-list-headline')]/text()", element=section_element)
        if headline:
            return headline
        
        all_text = section_element.xpath(".//text()")
        for text in all_text:
            text = text.strip()
            if text and re.search(r'\w+ - \d{4}-\d{2}-\d{2}', text):
                return text
        
        return None

    def _combine_date_and_time(self, day_headline: str, time_text: str) -> Optional[float]:
        """
        Combina data do cabeçalho com hora do match para criar timestamp em UTC.
        """
        try:
            if not day_headline or not time_text:
                return None
            
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', day_headline)
            if not date_match:
                return None
            
            date_str = date_match.group(1)
            time_parts = time_text.strip().split(':')
            
            if len(time_parts) < 2:
                return None
            
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            
            # A hora na página está em UTC+1 (CET)
            dt_str = f"{date_str} {hour:02d}:{minute:02d}:00"
            dt_utc_plus_1 = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            
            # Converter para UTC (subtrair 1 hora)
            dt_utc = dt_utc_plus_1 - timedelta(hours=1)
            
            return dt_utc.timestamp() * 1000
            
        except Exception as e:
            self.logger.error(f"Error combining date and time: {e}")
            return None

    def _format_timestamp_utc(self, timestamp_ms: float) -> str:
        """Converte timestamp UTC para string formatada em UTC"""
        if not timestamp_ms:
            return None
        
        dt_utc = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        return dt_utc.strftime("%Y-%m-%d %H:%M UTC")

    def _get_user_local_date(self, timestamp_ms: float, user_timezone: str = None) -> Dict:
        """
        Retorna a data local do usuário para um timestamp.
        Se user_timezone não for fornecido, usa UTC.
        """
        if not timestamp_ms:
            return None
        
        dt_utc = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        
        if user_timezone:
            try:
                user_tz = pytz.timezone(user_timezone)
                dt_local = dt_utc.astimezone(user_tz)
            except:
                dt_local = dt_utc
        else:
            dt_local = dt_utc
        
        return {
            "date": dt_local.strftime("%Y-%m-%d"),
            "display_date": dt_local.strftime("%A, %d %B %Y"),
            "time": dt_local.strftime("%H:%M"),
            "timezone": user_timezone or "UTC",
            "weekday": dt_local.strftime("%A").lower()
        }

    def _parse_match_data(self, match_element, day_headline: str = None, section_timestamp: float = None) -> Optional[Dict]:
        """parse data from a single match element."""
        try:
            match_id = match_element.get('data-match-id')
            
            # Team information
            team1_name = self.get_text_by_xpath(Matches.TodayMatches.TEAM_NAME, element=match_element) or "TBD"
            team2_name = self.get_text_by_xpath(Matches.TodayMatches.TEAM_NAME, pos=1, element=match_element) or "TBD"
            
            team1_id = match_element.get('team1') or ""
            team2_id = match_element.get('team2') or ""
            
            team1_logo = self.get_text_by_xpath(Matches.TodayMatches.TEAM_LOGO, element=match_element)
            team2_logo = self.get_text_by_xpath(Matches.TodayMatches.TEAM_LOGO, pos=1, element=match_element)
            
            tournament_name = self.get_text_by_xpath(Matches.TodayMatches.TOURNAMENT_NAME, element=match_element)
            tournament_id = match_element.get('data-event-id')
            tournament_logo = self.get_text_by_xpath(Matches.TodayMatches.TOURNAMENT_LOGO, element=match_element)
            
            time_text = self.get_text_by_xpath(Matches.TodayMatches.MATCH_TIME, element=match_element)
            match_timestamp_attr = self.get_text_by_xpath(Matches.TodayMatches.MATCH_TIMESTAMP, element=match_element)
            match_type = self.get_text_by_xpath(Matches.TodayMatches.MATCH_TYPE, element=match_element)
            
            match_url = self.get_text_by_xpath(Matches.TodayMatches.MATCH_URL, element=match_element)
            if match_url and not match_url.startswith('http'):
                match_url = f"https://www.hltv.org{match_url}"

            # Timestamp strategy: section_timestamp > attribute > combined
            match_timestamp = None
            
            if section_timestamp:
                match_timestamp = section_timestamp
            elif match_timestamp_attr:
                try:
                    match_timestamp = float(match_timestamp_attr)
                except (ValueError, TypeError):
                    pass
            elif day_headline and time_text:
                match_timestamp = self._combine_date_and_time(day_headline, time_text)
            
            # Identificar se é TBD
            is_tbd = not (team1_id and team2_id and team1_name != "TBD" and team2_name != "TBD")
            
            # Formatar horário UTC para debug
            match_time_utc = self._format_timestamp_utc(match_timestamp) if match_timestamp else None
            
            # Log do horário para debug
            if match_timestamp:
                self.logger.info(f"Match {match_id}: {team1_name} vs {team2_name} -> UTC: {match_time_utc}")
            
            return {
                "match_id": match_id,
                "match_url": match_url,
                "team1_name": team1_name,
                "team1_id": team1_id,
                "team1_logo": team1_logo,
                "team2_name": team2_name,
                "team2_id": team2_id,
                "team2_logo": team2_logo,
                "tournament_name": tournament_name,
                "tournament_id": tournament_id,
                "tournament_logo": tournament_logo,
                "match_timestamp": match_timestamp,  # SEMPRE UTC
                "match_type": match_type,
                "display_time": time_text,
                "display_date": day_headline,
                "is_tbd": is_tbd,
                "match_status": "tbd" if is_tbd else "scheduled"
            }
        
        except Exception as e:
            self.logger.error(f"error parsing match {match_id if 'match_id' in locals() else 'unknown'}: {e}")
            return None

    def _parse_day_section(self, section_element) -> Optional[List]:
        """parse matches from a single day section."""
        try:
            day_headline = self._get_day_headline_from_section(section_element)
            self.logger.info(f"Day section headline: '{day_headline}'")
            
            zone_wrappers = section_element.xpath(".//div[contains(@class, 'zone-entry-wrapper')]")
            matches = []
            
            for zone_wrapper in zone_wrappers:
                match_zone_wrappers = zone_wrapper.xpath(".//div[contains(@class, 'match-zone-wrapper')]")
                
                for match_zone in match_zone_wrappers:
                    section_timestamp = match_zone.get('data-zonedgrouping-entry-unix')
                    section_timestamp = float(section_timestamp) if section_timestamp else None
                    
                    match_wrappers = match_zone.xpath(".//div[contains(@class, 'match-wrapper')]")
                    
                    for match_wrapper in match_wrappers:
                        match_data = self._parse_match_data(
                            match_wrapper, 
                            day_headline=day_headline,
                            section_timestamp=section_timestamp
                        )
                        if match_data:
                            matches.append(match_data)

            return matches
        
        except Exception as e:
            self.logger.error(f"error parsing day section: {e}")
            return None

    def _parse_today_and_tomorrow(self) -> List[Dict]:
        """
        Parse matches from today and tomorrow (HLTV timezone).
        Returns all matches without separation - separation happens in frontend.
        """
        all_matches = []
        day_sections = self._get_day_sections()

        # Define HLTV timezone (CET - UTC+1)
        hlvt_tz = pytz.timezone('CET')
        now_hlvt = datetime.now(hlvt_tz)
        
        # Get today and tomorrow dates in HLTV timezone
        today_hlvt = now_hlvt.date()
        tomorrow_hlvt = today_hlvt + timedelta(days=1)
        
        self.logger.info(f"HLTV today: {today_hlvt}, HLTV tomorrow: {tomorrow_hlvt}")
        
        sections_parsed = 0
        for section in day_sections:
            # Extract date from section headline
            day_headline = self._get_day_headline_from_section(section)
            if not day_headline:
                continue

            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', day_headline)
            if not date_match:
                continue

            section_date_str = date_match.group(1)
            section_date = datetime.strptime(section_date_str, "%Y-%m-%d").date()

            # Only parse today and tomorrow
            if section_date == today_hlvt or section_date == tomorrow_hlvt:
                self.logger.info(f"Parsing section for date: {section_date_str}")
                section_matches = self._parse_day_section(section)
                if section_matches:
                    all_matches.extend(section_matches)
                    sections_parsed += 1
            
            # Stop after parsing tomorrow
            if sections_parsed >= 2:
                break

        return all_matches

    def get_today_matches(self, user_timezone: str = None) -> dict:
        """
        Get matches for today and tomorrow, with optional user timezone.
        
        Args:
            user_timezone: IANA timezone string (e.g., "America/Sao_Paulo", "America/Los_Angeles")
                          If None, uses UTC for separation.
        """
        try:
            # Get all matches from today and tomorrow (HLTV timezone)
            matches = self._parse_today_and_tomorrow()
            
            # If no user timezone provided, use UTC
            if not user_timezone:
                user_timezone = "UTC"
            
            # Group matches by user's local date
            grouped_matches = {}
            
            for match in matches:
                if not match.get('match_timestamp'):
                    continue
                
                # Get user's local date for this match
                local_info = self._get_user_local_date(match['match_timestamp'], user_timezone)
                local_date = local_info['date']
                
                if local_date not in grouped_matches:
                    grouped_matches[local_date] = {
                        "date": local_date,
                        "display_date": local_info['display_date'],
                        "weekday": local_info['weekday'],
                        "matches": []
                    }
                
                # Add local time to match for frontend
                match_with_local = match.copy()
                match_with_local['local_time'] = local_info['time']
                match_with_local['local_date'] = local_info['date']
                match_with_local['local_timezone'] = user_timezone
                
                grouped_matches[local_date]['matches'].append(match_with_local)
            
            # Convert to list and sort by date
            grouped_list = list(grouped_matches.values())
            grouped_list.sort(key=lambda x: x['date'])
            
            self.response["matches"] = matches  # Raw matches (UTC)
            self.response["matches_by_local_date"] = grouped_list  # Grouped by user's local date
            self.response["match_count"] = len(matches)
            self.response["timezone"] = {
                "backend": "UTC",
                "user": user_timezone,
                "hltv_server": "CET (UTC+1)"
            }
            self.response["date_range"] = {
                "hltv_today": datetime.now(pytz.timezone('CET')).strftime("%Y-%m-%d"),
                "hltv_tomorrow": (datetime.now(pytz.timezone('CET')) + timedelta(days=1)).strftime("%Y-%m-%d")
            }
            
            self.logger.info(f"returning {len(matches)} matches for user timezone: {user_timezone}")
            self.logger.info(f"grouped into {len(grouped_list)} local dates")
            
        except Exception as e:
            self.logger.error(f"error in get_today_matches: {e}")
            raise HTTPException(status_code=500, detail=str(e))

        return self.response