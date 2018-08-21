#!/usr/bin/python3
import os
import logging
import time
import argparse
import requests
import csv
from datetime import datetime
from bs4 import BeautifulSoup as bs
import re
import yaml
from operator import itemgetter
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError
from shutil import copy, copyfile
import json


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
def load_config(filename="config.yml"):
    logger.debug("Loading config file: " + filename)
    with open(filename, 'r') as ymlfile:
        return yaml.load(ymlfile)

#
#
#
def get_arena_ranks(guild_url_path,itr=0):
    guildData = requests.get(guild_url_path)
    guildParser = bs(guildData.content, 'lxml')

    players_raw = guildParser.find_all('td'.split(), {"data-sort-value" : re.compile('.*')});

    players = []

    i = 0
    for player_raw in players_raw:
        if (itr == 0 or i < itr):
            name = player_raw['data-sort-value']
            url = player_raw.find('a')['href']

            playerData = requests.get("https://swgoh.gg" + url)
            playerParser = bs(playerData.content, 'lxml')

            arenarank = playerParser.find(class_="panel-body").select('ul > li')[1].find('h5').get_text(strip=True)

            player = {
                'name': name,
                'url': url,
                'arenarank': int(arenarank)
            }
            players.append(player)

        i+=1
    return players

#
#
#
def get_zetas(zeta_url_path):
    zeta_data = requests.get(zeta_url_path)
    zeta_parser = bs(zeta_data.content, 'lxml')

    zetas_raw = (
            zeta_parser.
            find_all('td'.split(),
            {"data-sort-value" : re.compile('.*')})
        )

    players = []
    for player_zetas_raw in zetas_raw:
        player_name = player_zetas_raw.get("data-sort-value")
        player_zeta_toons = (
                player_zetas_raw.
                parent.
                select('td')[2].
                find_all(class_="guild-member-zeta")
            )


        player_toons = []
        for player_zeta_toon in player_zeta_toons:
            toon_name = player_zeta_toon.find(class_="guild-member-zeta-character").find('div').get("title")
            toon_zetas = player_zeta_toon.find(class_="guild-member-zeta-abilities").findAll(class_="guild-member-zeta-ability")

            zetas = []
            for toon_zeta in toon_zetas:
                zeta = toon_zeta.get("title")
                zetas.append(zeta)


            player_toon = {
                'toon_name': toon_name,
                'zetas': zetas
            }
            player_toons.append(player_toon)
        player = {
            'name': player_name,
            'toons': player_toons
        }
        players.append(player)
    return players

#
#
#
def get_units(url):
    return requests.get(url).json()

#
#
#
def get_units_mapping(url):
    return requests.get(url).json()

#
#
#
def get_zeta_reviews(url):
    response = requests.get(url)
    #response.encoding = "utf-8"
    fixed_text = response.text.replace("\n","").replace("b'","").replace("'","").encode("utf-8")
    return json.loads(fixed_text)

#
#
#
def gen_arenarank_report_text(players):
    sorted_players = sorted(players, key=itemgetter('arenarank'), reverse=False)
    
    text = '`'
    for player in sorted_players:
        text += '{:<30}'.format(player['name']) + str(player['arenarank']) + '\n'
    text += '`'
    return text

#
#
#
def send_discord_report(webhook,text):
    # Post the message to the Discord webhook
    data = {
        "username": "Big bro",
        "content": text
    }
    res = requests.post(discord_webhook_url, data=data)
    logger.debug(res.text)

#
#
#
def write_arenarank_to_file(timestamp,headers,players,filepath,filename):
    new_file = setup_new_datasource_file(headers, filepath, filename)
    for player in players:
        new_file.writerow([timestamp,player['name'].encode("utf8"),player['url'],player['arenarank']])

#
#
#
def write_zetas_to_file(timestamp,headers,players,filepath,filename):
    new_file = setup_new_datasource_file(headers, filepath, filename)
    for player in players:
        for toon in player['toons']:
            for zeta in toon['zetas']:
                new_file.writerow([timestamp, player['name'].encode("utf8"), toon['toon_name'], zeta])

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
def getCLIArguments():
    parser = argparse.ArgumentParser(description='Generates report from swgoh guilds')

    parser.add_argument('--guild', action="store", required=True)
    parser.add_argument('--zetas', action="store_true", default=False)
    parser.add_argument('--units', action="store_true", default=False)
    parser.add_argument('--arenaranks', action="store_true", default=False)
    parser.add_argument('--unit-mappings', action="store_true", default=False)
    parser.add_argument('--zeta-reviews', action="store_true", default=False)
    parser.add_argument('--save-file', action="store_true", default=False)
    parser.add_argument('--send-discord', action="store_true", default=False)
    parser.add_argument('--upload-dbx', action="store_true", default=False)
    parser.add_argument('--config', action="store")
    parser.add_argument('--env-config', action="store")
    parser.add_argument('--prod', action="store_true", default=False)
    parser.add_argument('--debug', action="store_true", default=False)

    return vars(parser.parse_args())

#
#
#
def get_guild_config(cfg, guild_string):
    guilds = cfg['guilds']
    return next((item for item in guilds if item["name"] == guild_string))

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

# Get CLI and config file configuration
args = getCLIArguments()
cfg = load_config(args['config'])

env_cfg = load_config(args['env_config'])
TOKEN = env_cfg['token']

logger.debug(print(cfg))
logger.debug("Token: " + TOKEN)

guild = args['guild']
guild_config = get_guild_config(cfg, guild)

# Specify the headers of the csv output
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

#
# Get Zetas
#
if args['zetas']:
    logger.debug("Scraping zetas...")
    url = guild_config['zetas']['url']
    players = get_zetas(url)

    if args['save_file']:
        logger.debug("--Writing to file...")

        output_folder = output_path_datasources + "zetas/"
        output_filename = output_file_prefix + guild + "_zetas" + "_" + file_timestamp + '.csv'
        headers = ["timestamp", "player", "toon", "zeta"]

        write_zetas_to_file(entry_timestamp, headers, players, output_folder, output_filename)

        if args['upload_dbx']:
            dpx_dest = dpx_output_path_datasources + "zetas/" + output_filename

            logger.info("--Uploading file to Dropbox...")
            upload_file_to_dropbox(TOKEN, output_folder + output_filename, dpx_dest)
#
# Get Arena Rank
#
if args['arenaranks']:
    logging.debug("Scraping arena ranks...")

    url = guild_config['arenaranks']['url']
    noPlayers = 0 if args['prod'] else 2
    players = get_arena_ranks(url, noPlayers)

    if args['save_file']:
        logging.debug("--Writing to file...")
        output_folder = output_path_datasources + "arenaranks/"
        output_filename = output_file_prefix + guild + "_arenaranks" + "_" + file_timestamp + '.csv'
        headers = ["timestamp", "player", "url", "arenarank"]
        write_arenarank_to_file(entry_timestamp, headers, players, output_folder, output_filename)

        if args['upload_dbx']:
            dpx_dest = dpx_output_path_datasources + "arenaranks/" + output_filename

            logger.debug("--Uploading file to Dropbox...")
            upload_file_to_dropbox(TOKEN, output_folder + output_filename, dpx_dest)

    if args['send_discord']:
        logging.debug("--Sending arena ranks to Discord...")
        intro = cfg['discord']['arenaranks']['text'].format(guild, report_timestamp)
        text = gen_arenarank_report_text(players)
        discord_webhook_url = guild_config['discordReportingWebhook-prod'] if args['prod'] else guild_config['discordReportingWebhook-test']
        send_discord_report(discord_webhook_url, intro + text)

#
# Get Guild Units
#
if args['units']:
    logging.debug("Scraping guildUnits...")

    url = guild_config['guildUnits']['url']
    toons = get_units(url)

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

#
# Get Unit Mappings
#
if args['unit_mappings']:
    logging.debug("Scraping unit mappings...")

    url = cfg['global']['unitMappings']['url']
    toons = get_units_mapping(url)

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

#
# Get Zeta Reviews
#
if args['zeta_reviews']:
    logging.debug("Fetching zeta reviews...")

    url = cfg['global']['zetaReviews']['url']
    zetas = get_zeta_reviews(url)

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