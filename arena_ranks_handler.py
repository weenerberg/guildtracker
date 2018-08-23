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

logger = logging.getLogger('guildtracker.arenarankshandler')

class ArenaRanksHandler(object):

	HEADERS = ["timestamp", "player", "url", "arenarank"]
	MODULE_NAME = "arenaranks"


	FILE_TS_FORMAT = "%Y-%m-%d_%H-%M-%S"
	ENTRY_TS_FORMAT = "%Y-%m-%d %H:%M:%S"
	REPORT_TS_FORMAT = "%Y-%m-%d"
	
	def __init__(self, url, filepath, filename_prefix, token, dbx_path, webhook, itr):
		self.url = url
		self.request_data(itr)
		self.filepath = filepath + ArenaRanksHandler.MODULE_NAME + "/"
		self.filename = filename_prefix + "_" + ArenaRanksHandler.MODULE_NAME + "_" + self.request_timestamp.strftime(ArenaRanksHandler.FILE_TS_FORMAT) + '.csv'
		self.token = token
		self.dbx_path = dbx_path + ArenaRanksHandler.MODULE_NAME+ "/" + self.filename
		self.webhook = webhook

	def request_data(self,itr):
		self.request_timestamp = datetime.now()

		guild_data = requests.get(self.url)
		guild_parser = bs(guild_data.content, 'lxml')

		players_raw = guild_parser.find_all('td'.split(), {"data-sort-value" : re.compile('.*')});

		players = []

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
		self.players = players

	#
	#
	#
	def write_data_to_file(self):
		csv_writer = setup_new_datasource_file(ArenaRanksHandler.HEADERS, self.filepath, self.filename)
		entry_timestamp = self.request_timestamp.strftime(ArenaRanksHandler.ENTRY_TS_FORMAT)

		for player in self.players:
			csv_writer.writerow([entry_timestamp, player['name'].encode("utf8"), player['url'], player['arenarank']])

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

	#
	#
	#
	def generate_report_text(self, prefix):
	    sorted_players = sorted(self.players, key=itemgetter('arenarank'), reverse=False)
	    
	    text = '`'
	    for player in sorted_players:
	        text += '{:<30}'.format(player['name']) + str(player['arenarank']) + '\n'
	    text += '`'
	    return prefix + text

	#
	#
	#
	def send_discord_report(self, username, report_prefix):
		text = self.generate_report_text(report_prefix)
		data = {
			"username": username,
			"content": text
		}
		res = requests.post(self.webhook, data=data)
		logger.debug(res.text)
