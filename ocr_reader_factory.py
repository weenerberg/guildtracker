import logging
from sith_score_reader import SithScoreReader
from raidtickets_lifetime_reader import RaidticketsLifetimeReader
from guildtickets_lifetime_reader import GuildticketsLifetimeReader
from territory_battle_total_score_reader import TerritoryBattleTotalScoreReader
from territory_battle_total_combat_waves_reader import TerritoryBattleTotalCombatWavesReader
from territory_battle_area_score_reader import TerritoryBattleAreaScoreReader

logger = logging.getLogger('guildtracker.handlerfactory')

class OcrReaderFactory(object):

	def __init__(self):
		pass

	def get_reader(self, event_type, score_type, event_timestamp):
		if event_type.lower() == "sith":
			if score_type.lower() == "totalscore":
				return SithScoreReader(event_timestamp)
		elif event_type.lower() == "tb":
			if score_type.lower() == "totalscore":
				return TerritoryBattleTotalScoreReader(event_timestamp)
			elif score_type.lower() == "totalcombatwaves":
				return TerritoryBattleTotalCombatWavesReader(event_timestamp)
			elif score_type.lower() == "areascores":
				return TerritoryBattleAreaScoreReader(event_timestamp)
		elif event_type.lower() == "raidtickets":
			if score_type.lower() == "lifetime":
				return RaidticketsLifetimeReader(event_timestamp)
		elif event_type.lower() == "guildtickets":
			if score_type.lower() == "lifetime":
				return GuildticketsLifetimeReader(event_timestamp)
		
		return None