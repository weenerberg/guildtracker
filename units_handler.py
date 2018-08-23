import logging
from bs4 import BeautifulSoup as bs
import re
import requests
from utils import setup_new_datasource_file
from datetime import datetime
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError

logger = logging.getLogger('guildtracker.unitshandler')

class UnitsHandler(object):

	HEADERS = ["timestamp", "player", "toon", "zeta"]
	MODULE_NAME = "units"
	
	FILE_TS_FORMAT = "%Y-%m-%d_%H-%M-%S"
	ENTRY_TS_FORMAT = "%Y-%m-%d %H:%M:%S"
	REPORT_TS_FORMAT = "%Y-%m-%d"

	def __init__(self, url, filepath, filename_prefix, token, dbx_path):
		self.url = url
		self.request_data()
		self.filepath = filepath + UnitsHandler.MODULE_NAME + "/"
		self.filename = filename_prefix + "_" + UnitsHandler.MODULE_NAME + "_" + self.request_timestamp.strftime(UnitsHandler.FILE_TS_FORMAT) + '.csv'
		self.token = token
		self.dbx_path = dbx_path + UnitsHandler.MODULE_NAME+ "/" + self.filename

	def request_data(self):
		self.request_timestamp = datetime.now()
		self.toons = requests.get(url).json()


    #
	#
	#
	def write_data_to_file(self):
	    csv_writer = setup_new_datasource_file(UnitsHandler.HEADERS, self.filepath, self.filename)
	    entry_timestamp = self.request_timestamp.strftime(UnitsHandler.ENTRY_TS_FORMAT)

	    for player in self.players:
	        for toon in player['toons']:
	            for zeta in toon['zetas']:
	                csv_writer.writerow([entry_timestamp, player['name'], toon['toon_name'], zeta])


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
