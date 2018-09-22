#!/usr/bin/python3
from os import listdir, walk, rename, makedirs, getcwd
from os.path import isfile, isdir, join, dirname, basename, splitext, exists, realpath, normpath
from shutil import copy, copyfile, move
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
		if isdir(join(path_to_parent,fname)):
			yield (join(path_to_parent,fname))


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


# Get CLI and config file configuration
args = getCLIArguments()
cfg = load_config(args['config_dir'] + 'config.yml')
env_cfg = load_config(args['config_dir'] + 'env_config.yml')


TOKEN = env_cfg['token']

anomalities = load_config(args['config_dir'] + 'knownNameAnomalities.yml')

#Configure input and output
folder_prefix = "" if args['prod'] else "TEST/"

root_path = env_cfg['outputBasePath'] + folder_prefix
archive_folder = "archive/datasource/"
ds_folder = "datasource/"


dbx_root_path = cfg['dpxBasePath'] + folder_prefix
dbx_archive_datasources_path = dbx_root_path + "archive/datasource/"
dbx_datasources_path = dbx_root_path + "datasource/"

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
OCR_INBOX_PATH = OCR_BASE_PATH + folder_prefix + 'ocr_ws/inbox/'
OCR_ARCHIVE_PATH =  OCR_BASE_PATH + folder_prefix + 'ocr_ws/archive/'

DBX_BASE_PATH = env_cfg['ocrDbxBasePath']
DBX_INBOX_PATH = DBX_BASE_PATH + folder_prefix + 'ocr_ws/inbox'

dbx_handler = DbxHandler(dbx_root_path, TOKEN)

ocr_reader_factory = OcrReaderFactory()


#if len(list(folders_in(OCR_BASE_PATH))) == 0:
if args['prod']:
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

	if args['prod']:
		# Fetch all screenshots from dbx to locally and then delete them from dbx
		dbx_handler.get_all_files_and_folders(DBX_INBOX_PATH, OCR_INBOX_PATH)
		dbx_handler.delete_sub_folders(DBX_INBOX_PATH)
	else:
		logger.debug("Test mode. Using what is in place at " + OCR_INBOX_PATH)

	for event_type_folder in list(folders_in(OCR_INBOX_PATH)):
		event_type = basename(event_type_folder)
		logger.debug("Event type: " + event_type)

		if len(list(folders_in(event_type_folder))) == 0:
			logger.info("No events found in " + event_type_folder + "!")
			continue

	    #
	    # JUST DURING TEST
	    #
		#if event_type != "sith":
		#	print("skipping " + event_type)
		#	continue

		for event_folder in list(folders_in(event_type_folder)):
			event_date = basename(event_folder).split("_")[1]
			logger.debug("Event date: " + event_date)

			ocr_reader = None
			player_rounds = []
			for event_score_type_folder in list(folders_in(event_folder)):
				score_type = basename(event_score_type_folder).split("_")[1]
				logger.debug("Score type: " + score_type)

				ocr_reader = ocr_reader_factory.get_reader(event_type, score_type, event_date)

				files = get_all_files_in_folder(event_score_type_folder)
				for event_score_file in files:
					logger.debug("Event score file: " + event_score_file)
				
					convert_input_file = '/'.join(event_score_file.split('\\'))

					convert_filename_w_ext = basename(convert_input_file)
					convert_input_filename, convert_input_filename_extension = splitext(convert_filename_w_ext)
					convert_output_file = event_score_type_folder + "/preprocessed/" + convert_input_filename + "_preprocessed" + convert_input_filename_extension
					convert_output_file = '/'.join(convert_output_file.split('\\'))

					convert = env_cfg['convert_path']

					ocr_reader.preprocess_image(convert, convert_input_file, convert_output_file)

					tesseract_input_file = convert_output_file
					tesseract_output_file = event_score_type_folder + "/ocred/" + convert_input_filename  + ".txt"
					tesseract_output_file = '/'.join(tesseract_output_file.split('\\'))
					
					tesseract_path = env_cfg['tesseract_path']
					user_words_path = env_cfg['tesseract_user_words']
					uzn_path = args['config_dir']

					text = ocr_reader.execute_ocr(tesseract_path, user_words_path, uzn_path, event_type, score_type, tesseract_input_file, tesseract_output_file)

					player_rounds.extend(ocr_reader.parse_text(players, anomalities, text))


			
			filename, extension = splitext(basename(event_folder))
			output_file = root_path + ds_folder + 'raids/' + event_type + "/" + filename + ".csv"
			logger.debug("Saving file to " + output_file + " with " + str(type(ocr_reader)))
			saved_file = ocr_reader.save_file(output_file, player_rounds)
			ocr_reader.dbx_upload(dbx_handler, dbx_datasources_path + 'raids/' + event_type + '/', saved_file)
			
		if args['prod']:
			logger.info('Moving processed event type ' + event_type_folder + ' to archive: ' + OCR_ARCHIVE_PATH)
			makedirs(dirname(OCR_ARCHIVE_PATH), exist_ok=True)
			move(event_type_folder, OCR_ARCHIVE_PATH)
					
