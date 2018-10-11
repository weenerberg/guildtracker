import logging
import sys
import os
from os.path import join
import requests
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError
from shutil import copy
from utils import setup_new_datasource_file
from datetime import datetime
from config import Config
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class DatasourceHandler(ABC):

	FILE_TS_FORMAT = "%Y-%m-%d_%H-%M-%S"
	ENTRY_TS_FORMAT = "%Y-%m-%d %H:%M:%S"
	REPORT_TS_FORMAT = "%Y-%m-%d"

	def __init__(self, url, guild, ws_base_path, dbx_base_path, datasource_folder, archive_folder, dbx_token, webhook, is_test):
		self.url = url
		self.__guild = guild
		self.__datasource_path = ws_base_path + datasource_folder
		self.__archive_path = ws_base_path + archive_folder
		self.__dbx_datasource_path = dbx_base_path + datasource_folder
		self.__dbx_archive_path = dbx_base_path + archive_folder
		self.__dbx_token = dbx_token
		self.__webhook = webhook
		self.__is_test = is_test

	def get_filename_prefix(self):
		return "TEST_" + self.__guild if self.__is_test else self.__guild

	def get_filepath(self):
		return join(self.__datasource_path, self.get_module_name())

	def get_archive_path(self):
		return join(self.__archive_path, self.get_module_name())

	def get_dbx_filepath(self):
		return join(self.__dbx_datasource_path, self.get_module_name())

	def get_dbx_archive_path(self):
		return join(self.__dbx_archive_path, self.get_module_name())

	def get_filename(self, has_timestamp):
		suffix = "_" + self.__request_timestamp.strftime(self.FILE_TS_FORMAT) if has_timestamp else ""
		return self.get_filename_prefix() + "_" + self.get_module_name() + suffix + ".csv"

	def get_entry_timestamp(self):
		return self.__request_timestamp.strftime(self.ENTRY_TS_FORMAT)

	def get_file_timestamp(self):
		return self.__request_timestamp.strftime(self.FILE_TS_FORMAT)

	def get_report_timestamp(self):
		return self.__request_timestamp.strftime(self.REPORT_TS_FORMAT)

	@abstractmethod
	def get_module_name(self):
		pass

	@abstractmethod
	def get_headers(self):
		pass

	def execute(self, save_file, archive_file, upload_dbx, send_discord=False):
		logger.debug("--------------Executing " + self.get_module_name() + "----------")

		if save_file:
			print("Saving file: " + self.get_filepath() + self.get_filename(False))
			self.write_data_to_file(archive_file)
			if upload_dbx:
				print("Upload to dbx: " + self.get_filepath() + self.get_filename(False))
				self.upload_file_to_dropbox(archive_file)
		if send_discord:
			username = Config.CFG['discord']['username']
			prefix = Config.CFG['discord'][self.get_module_name()]['text']
			suffix = ""
			self.send_discord_report(username, prefix, suffix)

		logger.debug("--------------DONE!----------")

	#
	#
	#
	@abstractmethod
	def request_data(self):
		self.__request_timestamp = datetime.now()

	#
	#
	#
	def write_data_to_file(self, archive_file):
		csv_writer = setup_new_datasource_file(self.get_headers(), self.get_filepath(), self.get_filename(not archive_file))
		self.write_data_to_file_helper(csv_writer)
		print("WROTE TO " + self.get_filepath())
		if archive_file:
			logging.debug("Copying file from: " + self.get_filepath() + self.get_filename(not archive_file) + " to " + self.get_archive_path() + self.get_filename(archive_file))
			if not os.path.exists(self.get_archive_path()):
				logging.debug("Creating new folder: " + self.get_archive_path())
				os.makedirs(self.get_archive_path())

			copy(self.get_filepath() + self.get_filename(not archive_file), self.get_archive_path() + self.get_filename(archive_file))

	@abstractmethod
	def write_data_to_file_helper(self, csv_writer):
		pass

	#
	#
	#
	def upload_file_to_dropbox(self, archive_file):
	    self.__upload_file_to_dropbox_helper(self.__dbx_token, self.get_filepath() + self.get_filename(not archive_file), self.get_dbx_filepath() + self.get_filename(not archive_file))

	    if archive_file:
	    	self.__upload_file_to_dropbox_helper(self.__dbx_token, self.get_archive_path() + self.get_filename(archive_file), self.get_dbx_archive_path() + self.get_filename(archive_file) )

	def __upload_file_to_dropbox_helper(self, token, src_file, dst_file):
		logger.debug("Creating a Dropbox object...")
		dbx = dropbox.Dropbox(token)

		try:
			dbx.users_get_current_account()
		except AuthError as err:
			sys.exit("ERROR: Invalid access token; try re-generating an "
				"access token from the app console on the web.")

		with open(src_file, 'rb') as f:
			logger.debug("Uploading " + src_file + " to Dropbox as " + dst_file + "...")
			try:
				dbx.files_upload(f.read(), dst_file, mode=WriteMode('overwrite'))
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

	@abstractmethod
	def generate_report_text(self, prefix, suffix):
		pass

	def send_discord_report(self, username, prefix="", suffix=""):
		prefix = prefix.format(self.__guild, self.get_report_timestamp())
		text = self.generate_report_text(prefix, suffix)

		data = {
			"username": username,
			"content": text
		}
		res = requests.post(self.__webhook, data=data)
		logger.debug(res.text)
