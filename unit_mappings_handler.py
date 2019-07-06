import logging
import json
import requests
import csv
from utils import setup_new_datasource_file
from datasource_handler import DatasourceHandler

logger = logging.getLogger('guildtracker.unitmappingshandler')

class UnitMappingsHandler(DatasourceHandler):

    HEADERS = ["timestamp", "name", "base_id", "combat_type", "power"]
    MODULE_NAME = "unitMappings"

    def __init__(self, url, filename_prefix, ws_base_path, dbx_base_path, ds_folder, archive_folder, dbx_token, webhook, is_test):
        super().__init__(url, filename_prefix, ws_base_path, dbx_base_path, ds_folder, archive_folder, dbx_token, webhook, is_test)
        self.request_data()

    def get_module_name(self):
        return self.MODULE_NAME

    def get_headers(self):
        return self.HEADERS

    def request_data(self):
        super().request_data()
        self.data = []
        for u in self.url:
            self.data.append(requests.get(u).json())

    def write_data_to_file_helper(self, csv_writer):
        for type in self.data:
            for toon in type:
                csv_writer.writerow([self.get_entry_timestamp(), toon['name'], toon['base_id'], toon['combat_type'], toon['power']])

    def generate_report_text(self, prefix, suffix):
        pass