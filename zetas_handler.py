import logging
import requests
import csv
from bs4 import BeautifulSoup as bs
import re
import requests
from utils import setup_new_datasource_file
from datasource_handler import DatasourceHandler

logger = logging.getLogger('guildtracker.zetashandler')

class ZetasHandler(DatasourceHandler):

	HEADERS = ["timestamp", "player", "toon", "zeta"]
	MODULE_NAME = "zetas"

	def __init__(self, url, guild, ws_base_path, dbx_base_path, ds_folder, archive_folder, dbx_token, webhook=None, is_test=False):
		super().__init__(url, guild, ws_base_path, dbx_base_path, ds_folder, archive_folder, dbx_token, webhook, is_test)
		self.request_data()

	def get_module_name(self):
		return self.MODULE_NAME

	def get_headers(self):
		return self.HEADERS

	def request_data(self):
		super().request_data()
		
		print(self.get_module_name() + ": Request data")
		
		data = requests.get(self.url)
		parser = bs(data.content, 'lxml')
		zetas_raw = parser.find_all('td'.split(), {"data-sort-value" : re.compile('.*')})

		players = []
		for player_zetas_raw in zetas_raw:
			player_name = player_zetas_raw.get("data-sort-value")
			player_zeta_toons = player_zetas_raw.parent.select('td')[2].find_all(class_="guild-member-zeta")

			player_toons = []
			for player_zeta_toon in player_zeta_toons:
				toon_name = player_zeta_toon.find(class_="guild-member-zeta-character").find('div').get("title")
				toon_zetas = player_zeta_toon.find(class_="guild-member-zeta-abilities").findAll(class_="guild-member-zeta-ability")

				zetas = []
				for toon_zeta in toon_zetas:
					zeta = toon_zeta.get("title")
					zetas.append(zeta)

				player_toon = { 'toon_name': toon_name, 'zetas': zetas }
				player_toons.append(player_toon)
			player = { 'name': player_name, 'toons': player_toons }
			players.append(player)

		self.data = players


	def write_data_to_file_helper(self, csv_writer):
		for player in self.data:
			for toon in player['toons']:
				for zeta in toon['zetas']:
					csv_writer.writerow([self.get_entry_timestamp(), player['name'], toon['toon_name'], zeta])

	def generate_report_text(self, prefix, suffix):
	    pass