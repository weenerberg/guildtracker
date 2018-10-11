import logging
from os.path import isfile, isdir, join, dirname, basename, splitext, exists, realpath, normpath
from os import makedirs
import subprocess
from PIL import Image
from shutil import copy
from datetime import datetime
from utils import setup_new_datasource_file, get_all_files_in_folder
from config import Config
from dbx_handler import DbxHandler
import requests
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


#
#
#
class OcrHandler(ABC):

	FILE_TS_FORMAT = "%Y-%m-%d_%H-%M-%S"
	ENTRY_TS_FORMAT = "%Y-%m-%d %H:%M:%S"
	REPORT_TS_FORMAT = "%Y-%m-%d"

	def __init__(self, inbox_path, guild, members, ws_base_path, dbx_base_path, datasource_folder, archive_folder, dbx_handler, webhook, is_test):
		self.data = []
		self.__inbox_path = inbox_path
		self.__guild = guild
		self.members = members
		self.__datasource_path = join(ws_base_path, datasource_folder)
		self.__archive_path = join(ws_base_path, archive_folder)
		self.__dbx_datasource_path = join(dbx_base_path, datasource_folder)
		self.__dbx_archive_path = join(dbx_base_path, archive_folder)
		self.__webhook = webhook
		self.__is_test = is_test
		self.__dbx_handler = dbx_handler
		self.request_data()

	def get_entry_timestamp(self):
		return self.get_event_datetime().strftime(self.ENTRY_TS_FORMAT)

	def get_file_timestamp(self):
		return self.__request_timestamp.strftime(self.FILE_TS_FORMAT)

	# TODO chang to using the filename date
	def get_report_timestamp(self):
		return self.get_event_datetime().strftime(self.REPORT_TS_FORMAT)

	#
	#
	#
	def get_filename_prefix(self):
		return "TEST_" + self.__guild if self.__is_test else self.__guild

	#
	#
	#
	def get_filepath(self):
		return join(self.__datasource_path, "raids", self.get_event_type() + "_" + self.get_score_type())

	#
	#
	#
	def get_archive_path(self):
		return join(self.__archive_path, "raids", self.get_event_type() + "_" + self.get_score_type())

	#
	#
	#
	def get_dbx_filepath(self):
		return join(self.__dbx_datasource_path, "raids", self.get_event_type() + "_" + self.get_score_type())

	#
	#
	#
	def get_dbx_archive_path(self):
		return join(self.__dbx_archive_path, "raids", self.get_event_type() + "_" + self.get_score_type())

	#
	#
	#
	def get_event_datetime(self):
		return self.event_datetime

	def set_event_datetime(self, event_datetime):
		self.event_datetime = event_datetime

	@abstractmethod
	def get_event_type(self):
		pass

	@abstractmethod
	def get_score_type(self):
		pass

	#
	#
	#
	def get_filename(self, has_timestamp):
		suffix = "_" + self.get_file_timestamp() if has_timestamp else ""
		return self.get_filename_prefix() + "_" + self.get_event_type() + "_" + self.get_score_type() + suffix + ".csv"

	#
	#
	#
	@abstractmethod
	def get_headers(self):
		pass

	def get_data(self):
		return self.data

	#
	#
	#
	def match_anomality(self, player, mapping):
		for k, v in mapping.items():
			for ano in v:
				if ano == player:
					logger.info("Anomality detected. Fixing. " + player + "->" + k)
					return k
		return player

	#
	#
	#
	def parse_date_string(self, filename):
		logger.info(filename)
		datetime_string = basename(filename).split("_")[1]
		datetime_object = datetime.strptime(datetime_string, '%Y-%m-%d-%H-%M-%S')
		return datetime_object

	def add_and_check_for_duplicate(self, player_round):
		logger.info("Checking for duplicate for " + player_round['name'])

		if self.data is None:
			logger.info("List is uninitialized. Fixing...")
			self.data = []

		for round in self.data:
			if player_round['name'] == round['name']:
				logger.info("Duplicate found for " + player_round['name'])

				old_score = 0
				new_score = 0

				try:
					old_score = int(round['score'])
				except:
					old_score = 0

				try:
					new_score = int(player_round['score'])
				except:
					new_score = 0

				if new_score > old_score:
					logger.info(player_round['name'] + ": New score " + player_round['score'] + " is bigger than the old score " + round['score'])
					for _player_round in self.get_data():
						_player_round.update((k, new_score) for k, v in _player_round.items() if v == old_score)
				else:
					logger.info("Duplicate. Skipping. " + player_round['name'])

				return

		logger.info("No duplicate found for " + player_round['name'] + ". Appending.")
		self.get_data().append(player_round)

	#
	#
	#
	def execute(self, save_file, archive_file, upload_dbx, send_discord=False):
		logger.info("--------------Executing " + self.get_event_type() + "_" + self.get_score_type() + "----------")

		if save_file:
			logger.info("Saving file: " + self.get_filepath() + self.get_filename(False))
			self.write_data_to_file(archive_file)
			if upload_dbx:
				logger.info("Upload to dbx: " + self.get_filepath() + self.get_filename(False))
				self.dbx_upload()
		if send_discord:
			self.generate_statistics()

			username = Config.CFG['discord']['username']

			type = 'total'
			prefix = Config.CFG['discord'][self.get_event_type() + "_" + self.get_score_type()][type]['text']
			suffix = ""
			self.send_discord_report(username, type, prefix, suffix)

			type = 'over'
			prefix = Config.CFG['discord'][self.get_event_type() + "_" + self.get_score_type()][type]['text']
			suffix = ""
			self.send_discord_report(username, type, prefix, suffix)

			type = 'under'
			prefix = Config.CFG['discord'][self.get_event_type() + "_" + self.get_score_type()][type]['text']
			suffix = ""
			self.send_discord_report(username, type, prefix, suffix)

		logger.info("--------------DONE!----------")

	#
	#
	#
	def request_data(self):
		self.__request_timestamp = datetime.now()
		self.__process_files(self.__inbox_path)

	#
	#
	#
	def __process_files(self, event_type_folder):
		logger.info("START: " + event_type_folder)
		file_ordinal = 0

		for event_score_file in get_all_files_in_folder(join(event_type_folder, "screenshots")):
			logger.info("Event score file: %s" % event_score_file)
			file_ordinal += 1

			event_datetime = self.parse_date_string(splitext(basename(event_score_file))[0])
			self.set_event_datetime(event_datetime)

			convert_input_file = '/'.join(event_score_file.split('\\'))
			convert_filename_w_ext = basename(convert_input_file)
			convert_input_filename, convert_input_filename_extension = splitext(convert_filename_w_ext)
			convert_output_file = join(event_type_folder, 'preprocessed', convert_input_filename + '_preprocessed' + convert_input_filename_extension)
			convert_output_file = '/'.join(convert_output_file.split('\\'))

			logger.info("preproc: " + convert_output_file)
			self.preprocess_image(Config.ENV_CFG['convert_path'], convert_input_file, convert_output_file)

			tesseract_exe_path = Config.ENV_CFG['tesseract_path']
			tesseract_user_words_path = Config.ENV_CFG['tesseract_user_words']
			tesseract_input_file = convert_output_file
			tesseract_output_file = join(event_type_folder, '/ocred', convert_input_filename  + ".txt")
			tesseract_output_file = '/'.join(tesseract_output_file.split('\\'))

			text = self.execute_ocr(tesseract_exe_path, tesseract_user_words_path, Config.ARGS['config_dir'], tesseract_input_file, tesseract_output_file)
			logger.info(text)

			names = []
			for player in self.members:
				names.append(player['data']['name'])

			player_rounds = self.parse_text(file_ordinal, self.get_event_datetime(), names, Config.ANOMALITIES, text)

			# TODO do this directly in the loop above...
			for player_round in player_rounds:
				self.add_and_check_for_duplicate(player_round)

		self.data.sort(key=lambda k: k['ordinal'])

		self.__validate()

	#
	#
	#
	def __validate(self):
		previous_round = None
		for current_round in self.data:

			current_score = int(current_round['score']) if current_round['score'] != '---' else 0
			previous_score = int(previous_round['score']) if previous_round and previous_round['score'] != '---' else 0

			error = None
			if previous_round and current_score > previous_score:
				logger.info("An inconsistency found:")
				logger.info("Current: " + str(current_round))
				logger.info("Previous: " + str(previous_round))

				error = 100

			if previous_round and current_score != 0 and current_score < previous_score/5:
				logger.info("A possible inconsistency found:")
				logger.info("Current: " + str(current_round))
				logger.info("Previous: " + str(previous_round))

				error = 50
				# total_rounds[:] = [d for d in total_rounds if d.get('name') != current_round['name']]

			if error:
				for _round in self.data:
					if _round['name'] == current_round['name']:
						current_round.update({'error': error})

			previous_round = current_round

	#
	#
	#
	def preprocess_image(self, path_to_convert, input_file, output_file):
		makedirs(dirname(output_file), exist_ok=True)

		cmd = [path_to_convert, input_file, "-colorspace", "gray", "-negate", "-morphology", "close", "diamond", "-threshold", "55%", output_file]
		fconvert = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = fconvert.communicate()
		assert fconvert.returncode == 0, stderr

	#
	#
	#
	def execute_ocr(self, path_to_tesseract, path_to_user_words, path_to_uzn, input_file, output_file):
		makedirs(dirname(output_file), exist_ok=True)

		im = Image.open(input_file)
		im_width = str(im.size[0])
		im_height = str(im.size[1])

		input_filepath = dirname(realpath(input_file))
		input_filename_w_ext = basename(input_file)
		input_filename, input_filename_extension = splitext(input_filename_w_ext)

		copy_infile = join(path_to_uzn, self.get_event_type().lower() + "_" + self.get_score_type().lower() + "_" + im_width +"x" + im_height + ".uzn")
		copy_outfile = join(input_filepath, input_filename + ".uzn")

		copy(copy_infile, copy_outfile)

		cmd = [path_to_tesseract, input_file, "stdout", "-l", "eng", "--user-words", path_to_user_words, "-c", "-load_system_dawg=F", "-c", "load_freq_dawg=F", "--psm", "4"]
		ftesseract = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = ftesseract.communicate()
		assert ftesseract.returncode == 0, stderr

		return self.clean_ocr_output(stdout.decode())

	#
	#
	#
	@abstractmethod
	def parse_text(self, file_ordinal, event_datetime, known_players, known_anomalities, text):
		pass

	#
	#
	#
	@abstractmethod
	def clean_ocr_output(self, text):
		pass

	#
	#
	#
	def write_data_to_file(self, do_archive_file):
		csv_writer = setup_new_datasource_file(self.get_headers(), join(self.get_filepath(), self.get_filename(not do_archive_file)))
		self.write_data_to_file_helper(csv_writer)
		print("WROTE TO " + self.get_filepath())
		if do_archive_file:
			logging.debug("Copying file from: " + self.get_filepath() + self.get_filename(not do_archive_file) + " to " + self.get_archive_path() + self.get_filename(do_archive_file))
			if not os.path.exists(self.get_archive_path()):
				logging.debug("Creating new folder: " + self.get_archive_path())
				os.makedirs(self.get_archive_path())

			copy(self.get_filepath() + self.get_filename(not do_archive_file), self.get_archive_path() + self.get_filename(do_archive_file))

	#
	#
	#
	@abstractmethod
	def write_data_to_file_helper(self, csv_writer):
		pass

	#
	#
	#
	def dbx_upload(self):
		filepath = join(self.get_filepath(), self.get_filename(True))
		dbx_filepath = join(self.get_dbx_filepath(), self.get_filename(True))

		self.__dbx_handler.upload_file(filepath, dbx_filepath)

	#
	#
	#
	@abstractmethod
	def generate_statistics(self):
		pass

	#
	#
	#
	@abstractmethod
	def generate_report_text(self, prefix, suffix):
		pass

	#
	#
	#
	def send_discord_report(self, username, type, prefix="", suffix=""):
		prefix = prefix.format(self.__guild, self.get_report_timestamp())
		text = self.generate_report_text(prefix, suffix, type)

		logger.info("Report text: " + text)

		data = {
			"username": username,
			"content": text
		}
		res = requests.post(self.__webhook, data=data)
		logger.info(res.text)
