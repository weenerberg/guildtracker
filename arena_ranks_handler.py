import logging
import dropbox
import re
import requests
from utils import setup_new_datasource_file
from datetime import datetime
from operator import itemgetter
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError
from bs4 import BeautifulSoup as bs
from datasource_handler import DatasourceHandler

logger = logging.getLogger('guildtracker.arenarankshandler')

class ArenaRanksHandler(DatasourceHandler):

	HEADERS = ["timestamp", "player", "url", "arenarank"]
	MODULE_NAME = "arenaranks"

	def __init__(self, url, guild, ws_base_path, dbx_base_path, ds_folder, archive_folder, dbx_token, webhook, is_test):
		super().__init__(url, guild, ws_base_path, dbx_base_path, ds_folder, archive_folder, dbx_token, webhook, is_test)
		self.request_data()

	def get_module_name(self):
		return self.MODULE_NAME

	def get_headers(self):
		return self.HEADERS


	def get_no_players(self):
		print("RUNNING PROD!")
		return 0

	def request_data(self):
		super().request_data()

		print(self.get_module_name() + ": Request data")

		data = requests.get(self.url)
		parser = bs(data.content, 'lxml')

		players_raw = parser.find_all('td'.split(), {"data-sort-value" : re.compile('.*')});

		players = []

		itr = self.get_no_players()

		i = 0
		for player_raw in players_raw:
			if (itr == 0 or i < itr):
				name = player_raw['data-sort-value']
				url = player_raw.find('a')['href']

				player_data = requests.get("https://swgoh.gg" + url)
				player_parser = bs(player_data.content, 'lxml')

				arenarank = player_parser.find(class_="panel-body").select('ul > li')[1].find('h5').get_text(strip=True)

				player = {
					'name': name,
					'url': url,
					'arenarank': int(arenarank)
				}
				players.append(player)

			i+=1
		self.data = players


	def write_data_to_file_helper(self, csv_writer):
		for player in self.data:
			csv_writer.writerow([self.get_entry_timestamp(), player['name'].encode("utf8"), player['url'], player['arenarank']])


	def generate_report_text(self, prefix, suffix):
	    sorted_players = sorted(self.data, key=itemgetter('arenarank'), reverse=False)
	    
	    body = '`'
	    for player in sorted_players:
	        body += '{:<30}'.format(player['name']) + str(player['arenarank']) + '\n'
	    body += '`'
	    return prefix + body + suffix


class TestArenaRanksHandler(ArenaRanksHandler):

	def get_no_players(self):
		print("RUNNING TEST!")
		return 2