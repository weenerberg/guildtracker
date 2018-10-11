import logging
from sith_score_handler import SithScoreHandler
from raidtickets_lifetime_handler import RaidticketsLifetimeHandler
from guildtickets_lifetime_handler import GuildticketsLifetimeHandler
from territory_battle_total_score_handler import TerritoryBattleTotalScoreHandler
from territory_battle_total_combat_waves_handler import TerritoryBattleTotalCombatWavesHandler
from territory_battle_area_score_handler import TerritoryBattleAreaScoreHandler
from dbx_handler import DbxHandler

logger = logging.getLogger(__name__)


class OcrHandlerFactory(object):

	def __init__(self, guild, members, ws_base_path, dbx_base_path, datasource_folder, archive_folder, dbx_token, webhook, is_test):
		self.__guild = guild
		self.__members = members
		self.__ws_base_path = ws_base_path
		self.__dbx_base_path = dbx_base_path
		self.__datasource_folder = datasource_folder
		self.__archive_folder = archive_folder
		self.__dbx_handler = DbxHandler(dbx_token)
		self.__webhook = webhook
		self.__is_test = is_test

	def get_handler(self, event_type, score_type, inbox_path):
		if event_type.lower() == "sith":
			if score_type.lower() == "totalscore":
				return SithScoreHandler(						inbox_path, self.__guild, self.__members, self.__ws_base_path, self.__dbx_base_path, self.__datasource_folder, self.__archive_folder, self.__dbx_handler, self.__webhook, self.__is_test)
		elif event_type.lower() == "tb":
			if score_type.lower() == "totalscore":
				return TerritoryBattleTotalScoreHandler(		inbox_path, self.__guild, self.__members, self.__ws_base_path, self.__dbx_base_path, self.__datasource_folder, self.__archive_folder, self.__dbx_handler, self.__webhook, self.__is_test)
			elif score_type.lower() == "totalcombatwaves":
				return TerritoryBattleTotalCombatWavesHandler(	inbox_path, self.__guild, self.__members, self.__ws_base_path, self.__dbx_base_path, self.__datasource_folder, self.__archive_folder, self.__dbx_handler, self.__webhook, self.__is_test)
			elif score_type.lower() == "areascores":
				return TerritoryBattleAreaScoreHandler(			inbox_path, self.__guild, self.__members, self.__ws_base_path, self.__dbx_base_path, self.__datasource_folder, self.__archive_folder, self.__dbx_handler, self.__webhook, self.__is_test)
		elif event_type.lower() == "raidtickets":
			if score_type.lower() == "lifetime":
				return RaidticketsLifetimeHandler(				inbox_path, self.__guild, self.__members, self.__ws_base_path, self.__dbx_base_path, self.__datasource_folder, self.__archive_folder, self.__dbx_handler, self.__webhook, self.__is_test)
		elif event_type.lower() == "guildtickets":
			if score_type.lower() == "lifetime":
				return GuildticketsLifetimeHandler(				inbox_path, self.__guild, self.__members, self.__ws_base_path, self.__dbx_base_path, self.__datasource_folder, self.__archive_folder, self.__dbx_handler, self.__webhook, self.__is_test)

		return None
