#!/usr/bin/python3
from os import listdir, walk, rename, makedirs, getcwd, remove
from os.path import isfile, isdir, join, dirname, basename, splitext, exists, realpath, normpath
from shutil import copy, copyfile, move, rmtree
import subprocess
import logging
import argparse
import yaml
import csv
import sys
import re
from PIL import Image
from utils import get_guild_config, folders_in, move_directory
from ocr_handler_factory import OcrHandlerFactory
from units_handler import UnitsHandler
from handler_factory import HandlerFactory
from dbx_handler import DbxHandler
from datetime import datetime
from config import Config

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

fh = logging.FileHandler('/var/log/guildtracker/guildtracker.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

#
#
#
def getCLIArguments():
    parser = argparse.ArgumentParser(description='Generates report from swgoh guilds')

    parser.add_argument('-c', '--config-dir', action="store", required=True)
    parser.add_argument('-g', '--guild', action="store")
    parser.add_argument('--save-file', action="store_true")
    parser.add_argument('--send-discord', action="store_true")
    parser.add_argument('--download-dbx', action="store_true")
    parser.add_argument('--retain-dbx', action="store_true")
    parser.add_argument('--upload-dbx', action="store_true")
    parser.add_argument('--prod', action="store_true")
    parser.add_argument('--debug', action="store_true")

    return vars(parser.parse_args())


#
#
#
def get_guild_members(guild_url):
	handler_factory = HandlerFactory("None", "None", "None", "None", "None", "None", "None", True)
	units_handler = handler_factory.get_handler(UnitsHandler.MODULE_NAME, guild_url)
	members = units_handler.get_all_members()
	return members


# Get CLI and config file configuration
args = getCLIArguments()

config = Config(args['config_dir'], args)

# cfg = load_config(args['config_dir'] + 'config.yml')
# env_cfg = load_config(args['config_dir'] + 'env_config.yml')


TOKEN = Config.ENV_CFG['token']

# anomalities = load_config(args['config_dir'] + 'knownNameAnomalities.yml')

# Configure input and output
folder_prefix = "" if args['prod'] else "TEST/"

root_path = join(config.ENV_CFG['outputBasePath'], folder_prefix)
archive_folder = "archive/datasource/"
ds_folder = "datasource/"


dbx_root_path = join(config.CFG['dpxBasePath'], folder_prefix)
dbx_archive_datasources_path = join(dbx_root_path, "archive/datasource/")
dbx_datasources_path = join(dbx_root_path, "datasource/")

# Get guild of guilds
guild = args['guild']
guilds = []

if not guild:
	logger.info("No guild specified. Executing all guilds from config.")
	guilds = config.CFG['guilds']
else:
	logger.info("Will execute for guild: " + guild)
	guilds = get_guild_config(config.CFG, guild)

# /home/mawe/GuildTrackerWS/ocr_ws/inbox
OCR_BASE_PATH = config.ENV_CFG['ocrBasePath']
OCR_INBOX_PATH = join(OCR_BASE_PATH, folder_prefix,'ocr_ws/inbox/')
OCR_ARCHIVE_PATH =  join(OCR_BASE_PATH, folder_prefix, 'ocr_ws/archive/')

DBX_BASE_PATH = config.ENV_CFG['ocrDbxBasePath']
DBX_INBOX_PATH = join(DBX_BASE_PATH, folder_prefix, 'ocr_ws/inbox')

dbx_handler = DbxHandler(TOKEN)


if args['prod'] and args['download_dbx']:
	if not dbx_handler.isFilesAvailable(DBX_INBOX_PATH):
		logger.info("No event types found at " + DBX_INBOX_PATH + "!")
		sys.exit(1)
else:
	if len(list(folders_in(OCR_INBOX_PATH))) == 0:
		logger.info("No event types found at " + OCR_INBOX_PATH + "!")
		sys.exit(1)


for guild_config in guilds:
	guild = guild_config['name']
	webhook = guild_config['discordReportingWebhook-prod'] if args['prod'] else guild_config['discordReportingWebhook-test']
	is_test = not args['prod']

	url = guild_config['guildUnits']['url']
	players = get_guild_members(url)

	names = []
	for player in players:
		names.append(player['data']['name'])

	player_anomalities = config.get_all_known_anomalities()
	names.extend(player_anomalities)
	logger.debug(names)

	ocr_handler_factory = OcrHandlerFactory(guild, players, root_path, dbx_root_path, ds_folder, archive_folder, TOKEN, webhook, is_test)

	if args['prod'] and args['download_dbx']:
		# Fetch all screenshots from dbx to locally and then delete them from dbx
		dbx_handler.get_all_files_and_folders(DBX_INBOX_PATH, OCR_INBOX_PATH)
		if not args['retain_dbx']:
			dbx_handler.delete_sub_folders(DBX_INBOX_PATH)
	else:
		logger.debug("Using what is in place at " + OCR_INBOX_PATH)

	for event_type_folder in list(folders_in(OCR_INBOX_PATH)):
		logger.info("Eventtypefolder: " + event_type_folder)
		event_type = basename(event_type_folder).split("_")[0]
		event_score_type = basename(event_type_folder).split("_")[1]
		logger.debug("Event type: " + event_type)
		logger.debug("Event score type: " + event_score_type)

		ocr_handler = ocr_handler_factory.get_handler(event_type, event_score_type, event_type_folder)

		ocr_handler.execute(Config.ARGS['save_file'], False, Config.ARGS['upload_dbx'], Config.ARGS['send_discord'])
		#total_rounds = []

		# Save rounds to file
		#event_datetime = ocr_handler.get_event_datetime()
		#filename, extension = splitext(basename(event_type_folder))
		#output_file = join(root_path, ds_folder, 'raids/', event_type, filename + "_" + event_datetime.strftime("%Y-%m-%d_%H-%M-%S") + ".csv")
		#logger.debug("Saving file to " + output_file + " with " + str(type(ocr_handler)))
		#saved_file = ocr_handler.write_data_to_file(False)

		# Upload file to Dropbox
		#ocr_handler.dbx_upload()

		#ocr_handler.generate_statistics()

		#if args['send_discord']:
		#	username = Config.CFG['discord']['username']
		#	prefix = Config.CFG['discord'][self.get_module_name()]['text']
		#	suffix = ""
		#	self.send_discord_report(username, prefix, suffix)
		#	text = ocr_handler.generate_report()

		#if args['prod']:
			#logger.info('Moving processed event type ' + event_type_folder + ' to archive: ' + OCR_ARCHIVE_PATH)
			#makedirs(dirname(OCR_ARCHIVE_PATH), exist_ok=True)
			#move_directory(event_type_folder, join(OCR_ARCHIVE_PATH,basename(event_type_folder), event_datetime.strftime("%Y-%m-%d_%H-%M-%S")))
			#rmtree(event_type_folder)

