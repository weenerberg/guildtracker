import logging
import json
import requests
import csv
from utils import setup_new_datasource_file
from datasource_handler import DatasourceHandler

logger = logging.getLogger(__name__)

class UnitsHandler(DatasourceHandler):

	HEADERS = ["timestamp", "player", "toon", "url", "combat_type", "rarity", "level", "gear", "power"]
	MODULE_NAME = "units"

	def __init__(self, url, filename_prefix, ws_base_path, dbx_base_path, ds_folder, archive_folder, dbx_token, webhook, is_test):
		super().__init__(url, filename_prefix, ws_base_path, dbx_base_path, ds_folder, archive_folder, dbx_token, webhook, is_test)
		self.request_data()
		
	def get_module_name(self):
		return self.MODULE_NAME

	def get_headers(self):
		return self.HEADERS

	def request_data(self):
		super().request_data()
		self.data = requests.get(self.url).json()

	def write_data_to_file_helper(self, csv_writer):
		players = self.data['players']
		for player in players:
			for unit in player['units']:
				csv_writer.writerow([self.get_entry_timestamp(), player['data']['name'], unit['data']['base_id'], player['data']['url'], 'n/a', unit['data']['rarity'], unit['data']['level'], unit['data']['gear_level'], unit['data']['power']])

	def generate_report_text(self, prefix, suffix):
	    pass

	def get_all_member_names(self):
		retval = []
		players = self.data['players']
		for player in players:
			retval.append(player['data']['name'])
		return retval

	def get_all_members(self):
		retval = []
		players = self.data['players']
		return players