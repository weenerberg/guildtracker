import logging
import json
import requests
import csv
from utils import setup_new_datasource_file
from datasource_handler import DatasourceHandler

logger = logging.getLogger('guildtracker.unitmappingshandler')

class ZetaReviewsHandler(DatasourceHandler):

	HEADERS = ["timestamp", "name", "toon", "type", "pvp", "tw", "tb", "pit", "tank", "sith", "versa"]
	MODULE_NAME = "zetaReviews"
	
	def __init__(self, url, filename_prefix, ws_base_path, dbx_base_path, ds_folder, archive_folder, dbx_token, webhook, is_test):
		super().__init__(url, filename_prefix, ws_base_path, dbx_base_path, ds_folder, archive_folder, dbx_token, webhook, is_test)	
		self.request_data()

	def get_module_name(self):
		return self.MODULE_NAME

	def get_headers(self):
		return self.HEADERS

	def request_data(self):
		super().request_data()
		response = requests.get(self.url)
		self.data = json.loads(response.content.decode('utf-8'))['zetas']

    #
	#
	#
	def write_data_to_file_helper(self, csv_writer):
		for zeta in self.data:
			csv_writer.writerow([self.get_entry_timestamp(), zeta['name'], zeta['toon'], zeta['type'], zeta['pvp'], zeta['tw'], zeta['tb'], zeta['pit'], zeta['tank'], zeta['sith'], zeta['versa']])

	def generate_report_text(self, prefix, suffix):
	    pass			