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
from utils import get_guild_config
from ocr_reader_factory import OcrReaderFactory
from units_handler import UnitsHandler
from handler_factory import HandlerFactory
from dbx_handler import DbxHandler
from datetime import datetime

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
    parser.add_argument('--upload-dbx', action="store_true")
    parser.add_argument('--prod', action="store_true")
    parser.add_argument('--debug', action="store_true")

    return vars(parser.parse_args())


#
#
#
def load_config(filename):
	logger.info("Loading config file: " + filename)
	with open(filename, 'r') as ymlfile:
		return yaml.load(ymlfile)


def folders_in(path_to_parent):
	for fname in listdir(path_to_parent):
		if isdir(join(path_to_parent, fname)):
			yield (join(path_to_parent, fname))

#TODO Fix so top directory is moved as well
def move_directory(root_src_dir, root_dst_dir):
	for src_dir, dirs, files in walk(root_src_dir):
		dst_dir = src_dir.replace(root_src_dir, root_dst_dir, 1)
		if not exists(dst_dir):
			makedirs(dst_dir)
		for file_ in files:
			src_file = join(src_dir, file_)
			dst_file = join(dst_dir, file_)
			if exists(dst_file):
				remove(dst_file)
			logger.info("Moving " + src_file + " to " + dst_dir)
			move(src_file, dst_dir)


def get_all_files_in_folder(folder):
	f = []
	for (dirpath, dirnames, filenames) in walk(folder):
		f.extend(join(dirpath, filename) for filename in filenames)
		break
	return f


def get_all_known_anomalities(mapping):
	retval = []
	for key, value in mapping.items():
		for ano in value:
			retval.append(ano)
	return retval


def get_guild_names(guild_url):
	handler_factory = HandlerFactory("None", "None", "None", "None", "None", "None", "None", True)
	units_handler = handler_factory.get_handler(UnitsHandler.MODULE_NAME, guild_url)
	names = units_handler.get_all_members()
	return names


def parse_date_string(filename):
	logger.info(filename)
	datetime_string = basename(filename).split("_")[1]
	datetime_object = datetime.strptime(datetime_string, '%Y-%m-%d-%H-%M-%S')
	return datetime_object


def add_and_check_for_duplicate(player_round, player_rounds):
	logger.info("Checking for duplicate for " + player_round['name'])
	#logger.info(player_rounds)

	_player_rounds = player_rounds
	if _player_rounds is None:
		logger.info("List is uninitialized. Fixing...")
		_player_rounds = []

	for round in _player_rounds:
		if player_round['name'] == round['name']:
			logger.info("Duplicate found for " + player_round['name'])
			#logger.info(alues: " + )

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
				for _player_round in _player_rounds:
					_player_round.update((k, new_score) for k, v in _player_round.items() if v == old_score)
			else:
				logger.info("Duplicate. Skipping. " + player_round['name'])

			return _player_rounds

	logger.info("No duplicate found for " + player_round['name'] + ". Appending.")
	_player_rounds.append(player_round)
	return _player_rounds


# Get CLI and config file configuration
args = getCLIArguments()
cfg = load_config(args['config_dir'] + 'config.yml')
env_cfg = load_config(args['config_dir'] + 'env_config.yml')


TOKEN = env_cfg['token']

anomalities = load_config(args['config_dir'] + 'knownNameAnomalities.yml')

#Configure input and output
folder_prefix = "" if args['prod'] else "TEST/"

root_path = join(env_cfg['outputBasePath'], folder_prefix)
archive_folder = "archive/datasource/"
ds_folder = "datasource/"


dbx_root_path = join(cfg['dpxBasePath'], folder_prefix)
dbx_archive_datasources_path = join(dbx_root_path, "archive/datasource/")
dbx_datasources_path = join(dbx_root_path, "datasource/")

# Get guild of guilds
guild = args['guild']
guilds = []
if not guild:
	logger.info("No guild specified. Executing all guilds from config.")
	guilds = cfg['guilds']
else:
	logger.info("Will execute for guild: " + guild)
	guilds = get_guild_config(cfg, guild)

#/home/mawe/GuildTrackerWS/ocr_ws/inbox
OCR_BASE_PATH = env_cfg['ocrBasePath']
OCR_INBOX_PATH = join(OCR_BASE_PATH, folder_prefix,'ocr_ws/inbox/')
OCR_ARCHIVE_PATH =  join(OCR_BASE_PATH, folder_prefix, 'ocr_ws/archive/')

DBX_BASE_PATH = env_cfg['ocrDbxBasePath']
DBX_INBOX_PATH = join(DBX_BASE_PATH, folder_prefix, 'ocr_ws/inbox')

dbx_handler = DbxHandler(dbx_root_path, TOKEN)

ocr_reader_factory = OcrReaderFactory()


#if len(list(folders_in(OCR_BASE_PATH))) == 0:
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
	is_test = not args['prod']

	url = guild_config['guildUnits']['url']
	players = get_guild_names(url)
	player_anomalities = get_all_known_anomalities(anomalities)
	players.extend(player_anomalities)
	logger.debug(players)

	if args['prod'] and args['download_dbx']:
		# Fetch all screenshots from dbx to locally and then delete them from dbx
		dbx_handler.get_all_files_and_folders(DBX_INBOX_PATH, OCR_INBOX_PATH)
		dbx_handler.delete_sub_folders(DBX_INBOX_PATH)
	else:
		logger.debug("Using what is in place at " + OCR_INBOX_PATH)

	for event_type_folder in list(folders_in(OCR_INBOX_PATH)):
		event_type = basename(event_type_folder).split("_")[0]
		event_score_type = basename(event_type_folder).split("_")[1]
		logger.debug("Event type: " + event_type)
		logger.debug("Event score type: " + event_score_type)

		#if len(list(folders_in(event_type_folder))) == 0:
		#	logger.info("No events found in " + event_type_folder + "!")
		#	continue

	    #
	    # JUST DURING TEST
	    #
		#if event_type != "sith":
		#	print("skipping " + event_type)
		#	continue

		#event_date = basename(event_folder).split("_")[1]
		#logger.debug("Event date: " + event_date)

		ocr_reader = ocr_reader_factory.get_reader(event_type, event_score_type)
		total_rounds = []
		
		event_datetime = None
		for event_score_file in get_all_files_in_folder(event_type_folder + "/screenshots"):
			logger.debug("Event score file: " + event_score_file)
		
			event_datetime = parse_date_string(splitext(basename(event_score_file))[0])

			convert_input_file = '/'.join(event_score_file.split('\\'))
			convert_filename_w_ext = basename(convert_input_file)
			convert_input_filename, convert_input_filename_extension = splitext(convert_filename_w_ext)
			convert_output_file = join(event_type_folder, '/preprocessed', convert_input_filename + '_preprocessed' + convert_input_filename_extension)
			convert_output_file = '/'.join(convert_output_file.split('\\'))

			ocr_reader.preprocess_image(env_cfg['convert_path'], convert_input_file, convert_output_file)

			tesseract_input_file = convert_output_file
			tesseract_output_file = join(event_type_folder, '/ocred', convert_input_filename  + ".txt")
			tesseract_output_file = '/'.join(tesseract_output_file.split('\\'))
			
			text = ocr_reader.execute_ocr(env_cfg['tesseract_path'], env_cfg['tesseract_user_words'], args['config_dir'], event_type, event_score_type, tesseract_input_file, tesseract_output_file)

			player_rounds = ocr_reader.parse_text(event_datetime, players, anomalities, text)

			#total_rounds.extend(player_rounds)

			for player_round in player_rounds:
				total_rounds = add_and_check_for_duplicate(player_round, total_rounds)
				logger.info


		filename, extension = splitext(basename(event_type_folder))
		output_file = join(root_path, ds_folder, 'raids/', event_type, filename + "_" + event_datetime.strftime("%Y-%m-%d_%H-%M-%S") + ".csv")
		logger.debug("Saving file to " + output_file + " with " + str(type(ocr_reader)))
		saved_file = ocr_reader.save_file(output_file, player_rounds)
		ocr_reader.dbx_upload(dbx_handler, join(dbx_datasources_path, 'raids/', event_type) + '/', saved_file)

		if args['prod']:
			logger.info('Moving processed event type ' + event_type_folder + ' to archive: ' + OCR_ARCHIVE_PATH)
			makedirs(dirname(OCR_ARCHIVE_PATH), exist_ok=True)
			move_directory(event_type_folder, OCR_ARCHIVE_PATH)
			rmtree(event_type_folder)

