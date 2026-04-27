from dataclasses import dataclass
from pprint import pprint
from lxml import etree
from app.services.players.profile import HLTVPlayerProfile
from app.services.players.search import HLTVPlayerSearch
from app.services.events.search import HLTVEventsSearch
from app.services.players.personalAchievements import HLTVPlayerPersonalAchievements
from app.services.players.teamAchievements import HLTVPlayerTeamAchievements
from app.services.players.trophies import HLTVPlayersTrophies
from app.services.players.stats import HLTVPlayerStats
from app.services.players.careerStats import HLTVPlayerCareerStats
from app.services.events.profile import HLTVEventProfile
from app.services.events.teamStats import HLTVEventTeamStats
from app.services.teams.search import HLTVTeamSearch
from app.services.teams.profile import HLTVTeamProfile
from app.services.teams.achievements import HLTVTeamAchievements
from app.services.ranking.stats import HLTVRankingStats

from datetime import datetime, timezone
import time

# Retorna o timestamp em UTC
utc_timestamp = time.time()
print(utc_timestamp)
# Saída ex: 1743769015.000206


# Obtém a hora atual UTC com timezone configurado
utc_agora = datetime.now(timezone.utc)
print(utc_agora)