#!/usr/bin/python3
import os
import logging
import time
import argparse
import requests
import csv
import dropbox
import re
import yaml
import json
from datetime import datetime
from shutil import copy, copyfile
from operator import itemgetter
from bs4 import BeautifulSoup as bs
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError
from zetas_handler import ZetasHandler
from arena_ranks_handler import ArenaRanksHandler

# Setup logging
logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

#
#
#
def getCLIArguments():
    parser = argparse.ArgumentParser(description='Generates report from swgoh guilds')

    parser.add_argument('-c', '--config', action="store", required=True)
    parser.add_argument('-e', '--env-config', action="store", required=True)
    parser.add_argument('-g', '--guild', action="store")
    parser.add_argument('--modules', action="store_true")
    parser.add_argument('--zetas', action="store_true")
    parser.add_argument('--units', action="store_true")
    parser.add_argument('--arenaranks', action="store_true")
    parser.add_argument('--unit-mappings', action="store_true")
    parser.add_argument('--zeta-reviews', action="store_true")
    parser.add_argument('--save-file', action="store_true")
    parser.add_argument('--send-discord', action="store_true")
    parser.add_argument('--upload-dbx', action="store_true")
    parser.add_argument('--prod', action="store_true")
    parser.add_argument('--debug', action="store_true")

    return vars(parser.parse_args())

#
#
#
def load_config(filename="config.yml"):
    logger.debug("Loading config file: " + filename)
    with open(filename, 'r') as ymlfile:
        return yaml.load(ymlfile)


# Get CLI and config file configuration
args = getCLIArguments()
cfg = load_config(args['config'])
env_cfg = load_config(args['env_config'])


#
#
#
def request_units(url):
    return requests.get(url).json()

#
#
#
def request_units_mapping(url):
    return requests.get(url).json()


def get_zeta_reviews(url):
    logging.debug("Fetching zeta reviews...")

    url = cfg['global']['zetaReviews']['url']
    zetas = request_zeta_reviews(url)

    if args['save_file']:
        logging.debug("--Writing to file...")
        archive_output_folder = output_path_archive_datasources + "zetaReviews/"
        archive_output_filename = output_file_prefix + "zetaReviews" + "_" + file_timestamp + '.csv'
        output_folder = output_path_datasources + "zetaReviews/"
        output_filename = output_file_prefix + "zetaReviews.csv"

        headers = ["timestamp", "name", "toon", "type", "pvp", "tw", "tb", "pit", "tank", "sith", "versa"]
        write_zeta_reviews_to_file(entry_timestamp, headers, zetas['zetas'], archive_output_folder, archive_output_filename)

        logging.debug("Copying file from: " + archive_output_folder + archive_output_filename + " to " + output_folder + output_filename)
        if not os.path.exists(output_folder):
            logging.debug("Creating new folder: " + output_folder)
            os.makedirs(output_folder)

        copy(archive_output_folder + archive_output_filename, output_folder + output_filename)

        if args['upload_dbx']:
            dpx_archive_dest = dpx_output_path_archive_datasources + "zetaReviews/" + archive_output_filename
            dpx_dest = dpx_output_path_datasources + "zetaReviews/" + output_filename

            logger.info("--Uploading file to Dropbox...")
            upload_file_to_dropbox(TOKEN, archive_output_folder + archive_output_filename, dpx_archive_dest)
            upload_file_to_dropbox(TOKEN, output_folder + output_filename, dpx_dest)


#
#
#
def request_zeta_reviews(url):
    response = requests.get(url)
    logging.debug(response)
    return json.loads(response.content.decode('utf-8'))

#
#
#
def write_units_to_file(timestamp, headers, toons, filepath, filename):
    new_file = setup_new_datasource_file(headers, filepath, filename)
    for toon, players in toons.items():
        for player in players:
            # Ships doesn't have a gear level or url
            gear_level_str = player['gear_level'] if player['combat_type'] == 1 else ""
            url_str = player['url'] if player['combat_type'] == 1 else ""

            new_file.writerow([timestamp, player['player'].encode("utf8"), toon, url_str, player['combat_type'], player['rarity'], player['level'], gear_level_str, player['power']])

#
#
#
def write_unit_mappings_to_file(timestamp, headers, toons, filepath, filename):
    new_file = setup_new_datasource_file(headers, filepath, filename)
    for toon in toons:
        new_file.writerow([timestamp, toon['name'], toon['base_id'], toon['combat_type'], toon['power']])

#
#
#
def write_zeta_reviews_to_file(timestamp, headers, zetas, filepath, filename):
    new_file = setup_new_datasource_file(headers, filepath, filename)
    for zeta in zetas:
        new_file.writerow([timestamp, zeta['name'], zeta['toon'], zeta['type'], zeta['pvp'], zeta['tw'], zeta['tb'], zeta['pit'], zeta['tank'], zeta['sith'], zeta['versa']])

#
#
#
def setup_new_datasource_file(headers, filepath, filename):
    if not os.path.exists(filepath):
        logger.debug("Creating new folder: " + filepath)
        os.makedirs(filepath)

    logger.debug("Writing file: " + filepath + filename)

    newFile = csv.writer(open(filepath + filename, "w"),lineterminator='\n')
    newFile.writerow(headers)
    return newFile

#
#
#
def get_guild_config(cfg, guild_string):
    guilds = cfg['guilds']
    return [next((item for item in guilds if item["name"] == guild_string))]

#
#
#
def upload_file_to_dropbox(token,file,dbx_path):

    logger.debug("File: " + file)
    logger.debug("dbx: " + dbx_path)

    # Create an instance of a Dropbox class, which can make requests to the API.
    logger.debug("Creating a Dropbox object...")
    dbx = dropbox.Dropbox(token)

    # Check that the access token is valid
    try:
        dbx.users_get_current_account()
    except AuthError as err:
        sys.exit("ERROR: Invalid access token; try re-generating an "
            "access token from the app console on the web.")


    with open(file, 'rb') as f:
        logger.debug("Uploading " + file + " to Dropbox as " + dbx_path + "...")
        try:
            dbx.files_upload(f.read(), dbx_path, mode=WriteMode('overwrite'))
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




##############################
#           Main             #
##############################

TOKEN = env_cfg['token']

FILE_TS_FORMAT = "%Y-%m-%d_%H-%M-%S"
ENTRY_TS_FORMAT = "%Y-%m-%d %H:%M:%S"
REPORT_TS_FORMAT = "%Y-%m-%d"

# Get the current date for the filename and entries
timestamp = datetime.now()
file_timestamp = timestamp.strftime(FILE_TS_FORMAT)
entry_timestamp = timestamp.strftime(ENTRY_TS_FORMAT)
report_timestamp = timestamp.strftime(REPORT_TS_FORMAT)

#Configure input and output
output_file_prefix = "" if args['prod'] else "TEST_"
output_folder_prefix = "" if args['prod'] else "TEST/"

output_path_root = env_cfg['outputBasePath'] + output_folder_prefix
output_path_archive = output_path_root + "archive/"
output_path_archive_datasources = output_path_archive + "datasources/"
output_path_datasources = output_path_root + "datasources/"

dpx_output_path_root = cfg['dpxBasePath'] + output_folder_prefix
dpx_output_path_archive = dpx_output_path_root + "archive/"
dpx_output_path_archive_datasources = dpx_output_path_archive + "datasources/"
dpx_output_path_datasources = dpx_output_path_root + "datasource/"

# Get guild or guilds
guild = args['guild']
guilds = []
if not guild:
    print("No guild specified")
    guilds = cfg['guilds']
    print(guilds)
else:
    guilds = get_guild_config(cfg, guild)
    print(guilds)

for guild_config in guilds:

    print(guild_config)

    # Get Zetas
    if args['zetas']:
        logger.debug("Scraping zetas...")
        url = guild_config['zetas']['url']
        
        zetas_handler = ZetasHandler(url, output_path_datasources, output_file_prefix + guild, TOKEN, dpx_output_path_datasources)

        if args['save_file']:
            zetas_handler.write_data_to_file()

            if args['upload_dbx']:
                zetas_handler.upload_file_to_dropbox()

    # Get Arena Rank
    if args['arenaranks']:
        logging.debug("Scraping arena ranks...")
        url = guild_config['arenaranks']['url']
        webhook = guild_config['discordReportingWebhook-prod'] if args['prod'] else guild_config['discordReportingWebhook-test']
        no_players = 0 if args['prod'] else 2

        arena_ranks_handler = ArenaRanksHandler(url, output_path_datasources, output_file_prefix + guild, TOKEN, dpx_output_path_datasources, webhook, no_players)

        if args['save_file']:
            arena_ranks_handler.write_data_to_file()

            if args['upload_dbx']:
                arena_ranks_handler.upload_file_to_dropbox()

        if args['send_discord']:
            username = cfg['discord']['username']
            intro = cfg['discord']['arenaranks']['text'].format(guild, report_timestamp)
            arena_ranks_handler.send_discord_report(username, intro)

    # Get Guild Units
    if args['units']:
        logging.debug("Scraping guildUnits...")

        url = guild_config['guildUnits']['url']
        toons = request_units(url)

        if args['save_file']:
            logging.debug("--Writing to file...")
            output_folder = output_path_datasources + "units/"
            output_filename = output_file_prefix + guild + "_units" + "_" + file_timestamp + '.csv'
            headers = ["timestamp", "player", "toon", "url", "combat_type", "rarity", "level", "gear_level", "power"]
            write_units_to_file(entry_timestamp, headers, toons, output_folder, output_filename)

            if args['upload_dbx']:
                dpx_dest = dpx_output_path_datasources + "units/" + output_filename

                logger.info("--Uploading file to Dropbox...")
                upload_file_to_dropbox(TOKEN, output_folder + output_filename, dpx_dest)

    # Get Unit Mappings
    if args['unit_mappings']:
        logging.debug("Scraping unit mappings...")

        url = cfg['global']['unitMappings']['url']
        toons = request_units_mapping(url)

        if args['save_file']:
            logging.debug("--Writing to file...")
            archive_output_folder = output_path_archive_datasources + "unitMappings/"
            archive_output_filename = output_file_prefix + "unitMappings" + "_" + file_timestamp + '.csv'
            output_folder = output_path_datasources + "unitMappings/"
            output_filename = output_file_prefix + "unitMappings.csv"

            headers = ["timestamp", "name", "base_id", "combat_type", "power"]
            write_unit_mappings_to_file(entry_timestamp, headers, toons, archive_output_folder, archive_output_filename)

            logging.debug("Copying file from: " + archive_output_folder + archive_output_filename + " to " + output_folder + output_filename)
            if not os.path.exists(output_folder):
                logging.debug("Creating new folder: " + output_folder)
                os.makedirs(output_folder)

            copy(archive_output_folder + archive_output_filename, output_folder + output_filename)

            if args['upload_dbx']:
                dpx_archive_dest = dpx_output_path_archive_datasources + "unit_mappings/" + archive_output_filename
                dpx_dest = dpx_output_path_datasources + "unit_mappings/" + output_filename

                logger.info("--Uploading file to Dropbox...")
                upload_file_to_dropbox(TOKEN, archive_output_folder + archive_output_filename, dpx_archive_dest)
                upload_file_to_dropbox(TOKEN, output_folder + output_filename, dpx_dest)

    # Get Zeta Reviews
    if args['zeta_reviews']:
        logging.debug("Fetching zeta reviews...")

        url = cfg['global']['zetaReviews']['url']
        zetas = request_zeta_reviews(url)

        if args['save_file']:
            logging.debug("--Writing to file...")
            archive_output_folder = output_path_archive_datasources + "zetaReviews/"
            archive_output_filename = output_file_prefix + "zetaReviews" + "_" + file_timestamp + '.csv'
            output_folder = output_path_datasources + "zetaReviews/"
            output_filename = output_file_prefix + "zetaReviews.csv"

            headers = ["timestamp", "name", "toon", "type", "pvp", "tw", "tb", "pit", "tank", "sith", "versa"]
            write_zeta_reviews_to_file(entry_timestamp, headers, zetas['zetas'], archive_output_folder, archive_output_filename)

            logging.debug("Copying file from: " + archive_output_folder + archive_output_filename + " to " + output_folder + output_filename)
            if not os.path.exists(output_folder):
                logging.debug("Creating new folder: " + output_folder)
                os.makedirs(output_folder)

            copy(archive_output_folder + archive_output_filename, output_folder + output_filename)

            if args['upload_dbx']:
                dpx_archive_dest = dpx_output_path_archive_datasources + "zetaReviews/" + archive_output_filename
                dpx_dest = dpx_output_path_datasources + "zetaReviews/" + output_filename

                logger.info("--Uploading file to Dropbox...")
                upload_file_to_dropbox(TOKEN, archive_output_folder + archive_output_filename, dpx_archive_dest)
                upload_file_to_dropbox(TOKEN, output_folder + output_filename, dpx_dest)