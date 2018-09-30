import logging
from sith_score_reader import SithScoreReader
from raidtickets_lifetime_reader import RaidticketsLifetimeReader
from guildtickets_lifetime_reader import GuildticketsLifetimeReader
from territory_battle_total_score_reader import TerritoryBattleTotalScoreReader
from territory_battle_total_combat_waves_reader import TerritoryBattleTotalCombatWavesReader
from territory_battle_area_score_reader import TerritoryBattleAreaScoreReader

logger = logging.getLogger(__name__)

class OcrReaderFactory(object):

	def __init__(self):
		pass

	def get_reader(self, event_type, score_type):
		if event_type.lower() == "sith":
			if score_type.lower() == "totalscore":
				return SithScoreReader()
		elif event_type.lower() == "tb":
			if score_type.lower() == "totalscore":
				return TerritoryBattleTotalScoreReader()
			elif score_type.lower() == "totalcombatwaves":
				return TerritoryBattleTotalCombatWavesReader()
			elif score_type.lower() == "areascores":
				return TerritoryBattleAreaScoreReader()
		elif event_type.lower() == "raidtickets":
			if score_type.lower() == "lifetime":
				return RaidticketsLifetimeReader()
		elif event_type.lower() == "guildtickets":
			if score_type.lower() == "lifetime":
				return GuildticketsLifetimeReader()
		
		return None