import logging
from bs4 import BeautifulSoup as bs
import re
import requests
from utils import setup_new_datasource_file
from datetime import datetime
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError

logger = logging.getLogger('guildtracker.zetashandler')

class ZetasHandler(object):

	HEADERS = ["timestamp", "player", "toon", "zeta"]
	MODULE_NAME = "zetas"

	FILE_TS_FORMAT = "%Y-%m-%d_%H-%M-%S"
	ENTRY_TS_FORMAT = "%Y-%m-%d %H:%M:%S"
	REPORT_TS_FORMAT = "%Y-%m-%d"
	
	def __init__(self, url, filepath, filename_prefix, token, dbx_path):
		self.url = url
		self.request_data()
		self.filepath = filepath + ZetasHandler.MODULE_NAME + "/"
		self.filename = filename_prefix + "_" + ZetasHandler.MODULE_NAME + "_" + self.request_timestamp.strftime(ZetasHandler.FILE_TS_FORMAT) + '.csv'
		self.token = token
		self.dbx_path = dbx_path + ZetasHandler.MODULE_NAME + "/" + self.filename

	def request_data(self):
		self.request_timestamp = datetime.now()
		
		zeta_data = requests.get(self.url)
		zeta_parser = bs(zeta_data.content, 'lxml')
		zetas_raw = zeta_parser.find_all('td'.split(), {"data-sort-value" : re.compile('.*')})

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

		self.players = players

    #
	#
	#
	def write_data_to_file(self):
		csv_writer = setup_new_datasource_file(ZetasHandler.HEADERS, self.filepath, self.filename)
		entry_timestamp = self.request_timestamp.strftime(ZetasHandler.ENTRY_TS_FORMAT)

		for player in self.players:
			for toon in player['toons']:
				for zeta in toon['zetas']:
					csv_writer.writerow([entry_timestamp, player['name'], toon['toon_name'], zeta])

  	#
  	#
    #
	def upload_file_to_dropbox(self):
	    logger.debug("Creating a Dropbox object...")
	    dbx = dropbox.Dropbox(self.token)

	    try:
	        dbx.users_get_current_account()
	    except AuthError as err:
	        sys.exit("ERROR: Invalid access token; try re-generating an "
	            "access token from the app console on the web.")

	    with open(self.filepath + self.filename, 'rb') as f:
	        logger.debug("Uploading " + self.filepath + self.filename + " to Dropbox as " + self.dbx_path + "...")
	        try:
	            dbx.files_upload(f.read(), self.dbx_path, mode=WriteMode('overwrite'))
	        except ApiError as err:
	            if (err.error.is_path() and
	                    err.error.get_path().reason.is_insufficient_space()):
	                sys.exit("ERROR: Cannot back up; insufficient space.")
	            elif err.user_message_text:
	                logger.debug(err.user_message_text)
	                sys.exit()
	            else:
	                logger.debug(err)
	                sys.exit()
