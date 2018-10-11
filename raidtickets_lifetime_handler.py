import logging
from os.path import isfile, isdir, join, dirname, basename, splitext, exists, realpath, normpath
from os import listdir, walk, rename, makedirs, getcwd
import subprocess
from PIL import Image
from shutil import copy, copyfile
import re
import csv
from ocr_handler import OcrHandler

logger = logging.getLogger(__name__)


class RaidticketsLifetimeHandler(OcrHandler):

	HEADERS = ["timestamp", "player", "event_type", "score_type", "total_score", "ordinal", "error"]

	def __init__(self, inbox_path, guild, members, ws_base_path, dbx_base_path, datasource_folder, archive_folder, dbx_token, webhook, is_test):
		super().__init__(inbox_path, guild, members, ws_base_path, dbx_base_path, datasource_folder, archive_folder, dbx_token, webhook, is_test)

	def get_headers(self):
		return self.HEADERS

	def clean_ocr_output(self, text):
		text = text.replace("^\r\n$", "").replace("^\n$", "")
		text = re.sub(r'Leader', '', text)
		text = re.sub(r'Member', '', text)
		text = re.sub(r'Officer', '', text)
		text = re.sub(r'Lifetime Raid', '', text)
		text = re.sub(r'Tickets Produced:', '', text)
		return text

	def generate_report_text(self, prefix, suffix, type):
		return "raidtickets report"

	def get_event_type(self):
		return "raidtickets"

	def get_score_type(self):
		return "lifetime"

	def parse_text(self, file_ordinal, event_datetime, known_players, known_anomalities, text):
		self.__file_timestamp = event_datetime
		# Loop over players
		player_rounds = []

		lines = text.splitlines()

		player_rounds = []

		names = []
		numbers = []

		new_lines = []
		for line in lines:
			if re.match(r'\w.*$', line):
				new_lines.append(line)

		names = new_lines[:len(new_lines)//2]
		numbers = new_lines[len(new_lines)//2:]

		logger.debug('Names found in OCR output: ' + str(names))
		logger.debug('Numbers found in OCR output: ' + str(numbers))

		for idx, name in enumerate(names):
			error = ""

			player_round = {
				'timestamp': event_datetime.strftime("%Y-%m-%d %H:%M:%S"),
				'event_type': 'raidtickets',
				'name': name,
				'score': numbers[idx],
				'score_type': 'lifetime',
				'ordinal': str(file_ordinal).zfill(2) + '_' + str(idx).zfill(3),
				'error': error
			}
			player_rounds.append(player_round)

		if len(names) < 5:
			logger.warning("Only " + str(len(names)) + " players found in \n" + text)

		return player_rounds

	def generate_statistics(self):
		pass

	def write_data_to_file_helper(self, csv_writer):
		for player in self.data:
			csv_writer.writerow([player['timestamp'], player['name'], player['event_type'], player['score_type'], player['score'], player['ordinal'], player['error']])
