import logging
from zetas_handler import ZetasHandler
from arena_ranks_handler import ArenaRanksHandler, TestArenaRanksHandler
from units_handler import UnitsHandler
from unit_mappings_handler import UnitMappingsHandler
from zeta_reviews_handler import ZetaReviewsHandler

logger = logging.getLogger(__name__)

class HandlerFactory(object):

	
	def __init__(self, guild, ws_base_path, dbx_base_path, datasource_folder, archive_folder, dbx_token, webhook, is_test):
		self.__guild = guild
		self.__ws_base_path = ws_base_path
		self.__dbx_base_path = dbx_base_path
		self.__datasource_folder = datasource_folder
		self.__archive_folder = archive_folder
		self.__dbx_token = dbx_token
		self.__webhook = webhook
		self.__is_test = is_test

	def get_handler(self, type, url):
		if type == ZetasHandler.MODULE_NAME:
			return ZetasHandler(url, self.__guild, self.__ws_base_path, self.__dbx_base_path, self.__datasource_folder, self.__archive_folder, self.__dbx_token, self.__webhook, self.__is_test)
		elif type == ArenaRanksHandler.MODULE_NAME:
			if self.__is_test:
				return TestArenaRanksHandler(url, self.__guild, self.__ws_base_path, self.__dbx_base_path, self.__datasource_folder, self.__archive_folder, self.__dbx_token, self.__webhook, self.__is_test)
			else:
				return ArenaRanksHandler(url, self.__guild, self.__ws_base_path, self.__dbx_base_path, self.__datasource_folder, self.__archive_folder, self.__dbx_token, self.__webhook, self.__is_test)
		elif type == UnitsHandler.MODULE_NAME:
			return UnitsHandler(url, self.__guild, self.__ws_base_path, self.__dbx_base_path, self.__datasource_folder, self.__archive_folder, self.__dbx_token, self.__webhook, self.__is_test)
		elif type == UnitMappingsHandler.MODULE_NAME:
			return UnitMappingsHandler(url, self.__guild, self.__ws_base_path, self.__dbx_base_path, self.__datasource_folder, self.__archive_folder, self.__dbx_token, self.__webhook, self.__is_test)
		elif type == ZetaReviewsHandler.MODULE_NAME:
			return ZetaReviewsHandler(url, self.__guild, self.__ws_base_path, self.__dbx_base_path, self.__datasource_folder, self.__archive_folder, self.__dbx_token, self.__webhook, self.__is_test)
