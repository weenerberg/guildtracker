import logging
import sys
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError
from os.path import isfile, isdir, join, dirname, basename, splitext, exists, realpath, normpath
from os import listdir, walk, rename, makedirs, getcwd
import types

logger = logging.getLogger(__name__)


class DbxHandler(object):

	def __init__(self, token):
		# self.base_path = base_path

		self.dbx = dropbox.Dropbox(token)

	def upload_file(self, src_file, dst_file):

		try:
			self.dbx.users_get_current_account()
		except AuthError as err:
			sys.exit("ERROR: Invalid access token; try re-generating an "
				"access token from the app console on the web.")

		with open(src_file, 'rb') as f:
			logger.info("Uploading " + src_file + " to Dropbox as " + dst_file + "...")
			try:
				self.dbx.files_upload(f.read(), dst_file, mode=WriteMode('overwrite'))
			except ApiError as err:
				if (err.error.is_path() and
						err.error.get_path().reason.is_insufficient_space()):
					sys.exit("ERROR: Cannot back up; insufficient space.")
				elif err.user_message_text:
					logger.error(err.user_message_text)
					sys.exit(0)
				else:
					logger.error(err)
					sys.exit(0)

	def isFilesAvailable(self, dbx_folder):
		try:
			self.dbx.users_get_current_account()
		except AuthError as err:
			sys.exit("ERROR: Invalid access token; try re-generating an "
				"access token from the app console on the web.")

		try:
			response = self.dbx.files_list_folder(dbx_folder, True)
			for file in response.entries:
				logger.info(file)
				if(file.name.lower() == 'screenshots'):
					logger.info(file)
					return True
			return False

		except ApiError as err:
			if err.user_message_text:
				logger.error(err.user_message_text)
				sys.exit(0)
			else:
				logger.error(err)
				sys.exit(0)
	
	def get_all_files_and_folders(self, dbx_folder, dst_folder):

		logger.debug("dbx_folder: " + dbx_folder)
		logger.debug("dst_folder: " + dst_folder)

		try:
			self.dbx.users_get_current_account()
		except AuthError as err:
			sys.exit("ERROR: Invalid access token; try re-generating an "
				"access token from the app console on the web.")

		try:
			response = self.dbx.files_list_folder(dbx_folder, True)
			for file in response.entries:
				sub_path = file.path_lower.split(dbx_folder.lower())[1]
				dst_filepath = dst_folder + sub_path

				if isinstance(file, dropbox.files.FolderMetadata):
					makedirs(dirname(dst_filepath), exist_ok=True)

				elif isinstance(file, dropbox.files.FileMetadata):
					makedirs(dirname(dst_filepath), exist_ok=True)

					logger.debug("Download " + file.path_lower)
					with open(dst_filepath, "wb+") as f:
						metadata, res = self.dbx.files_download(path=file.path_lower)
						f.write(res.content)
				else:
					logger.error("SOMETHING IS SERIOUSLY WRONG!!!")

		except ApiError as err:
			if err.user_message_text:
				logger.error(err.user_message_text)
				sys.exit(0)
			else:
				logger.error(err)
				sys.exit(0)

	def delete_sub_folders(self, dbx_folder):
		try:
			self.dbx.users_get_current_account()
		except AuthError as err:
			sys.exit("ERROR: Invalid access token; try re-generating an "
				"access token from the app console on the web.")

		try:
			logger.info("Deleting from dbx folder: " + dbx_folder)

			response = self.dbx.files_list_folder(dbx_folder, True)

			for file in response.entries:
				if(dbx_folder.lower() == file.path_lower):
					logger.info("Skipping " + file.path_lower)
					continue
				elif isinstance(file, dropbox.files.FolderMetadata) and file.name.lower() == 'screenshots':
					logger.info("Deleting " + file.path_lower)
					response = self.dbx.files_delete(file.path_lower)
				else:
					logger.info("Skipping unknown type: " + str(file))

		except ApiError as err:
			if err.user_message_text:
				logger.error(err.user_message_text)
				sys.exit(0)
			else:
				logger.error(err)
				sys.exit(0)
