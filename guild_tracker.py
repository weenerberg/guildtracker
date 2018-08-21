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

def load_config(filename='config_0.2.3.yml'):
    print("Loading config file: " + filename)
    with open(filename, 'r') as ymlfile:
        return yaml.load(ymlfile)

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

def get_units(url):
    # Get data from API, parse to JSON
    return requests.get(url).json()

def get_units_mapping(url):
    # Get data from API, parse to JSON
    return requests.get(url).json()

def gen_arenarank_report_text(players,timestamp):
    sorted_players = sorted(players, key=itemgetter('arenarank'), reverse=False)
    text = "Below is the arena rank per " + timestamp + "\n\n"
    text += '`'
    for player in sorted_players:
        text += '{:<30}'.format(player['name']) + str(player['arenarank']) + '\n'
    text += '`'
    return text

def send_discord_report(webhook,text):
    # Post the message to the Discord webhook
    data = {
        "username": "Big bro",
        "content": text
    }
    res = requests.post(discord_webhook_url, data=data)
    print(res.text)

def write_arenarank_to_file(timestamp,headers,players,filepath,filename):
    if not os.path.exists(filepath):
        os.makedirs(filepath)

    newFile = csv.writer(open(filepath+filename, "w"),lineterminator='\n')
    newFile.writerow(headers)

    for player in players:
        # Write all values to file
        newFile.writerow([timestamp,player['name'].encode("utf8"),player['url'],player['arenarank']])


def write_zetas_to_file(timestamp,headers,players,filepath,filename):

    if not os.path.exists(filepath):
        os.makedirs(filepath)

    new_file = csv.writer(open(filepath+filename, "w"),lineterminator='\n')
    new_file.writerow(headers)

    for player in players:
        for toon in player['toons']:
            for zeta in toon['zetas']:
                new_file.writerow([timestamp, player['name'].encode("utf8"), toon['toon_name'], zeta])


def write_units_to_file(timestamp,headers,toons,filepath,filename):
    if not os.path.exists(filepath):
        print("Creating new folder: " + filepath)
        os.makedirs(filepath)

    print("Writing file: " + filepath+filename)

    newFile = csv.writer(open(filepath+filename, "w"),lineterminator='\n')
    newFile.writerow(headers)

    for toon, players in toons.items():
        for player in players:
            # Ships doesn't have a gear level or url
            gear_level_str = player['gear_level'] if player['combat_type'] == 1 else ""
            url_str = player['url'] if player['combat_type'] == 1 else ""

            newFile.writerow([timestamp, player['player'].encode("utf8"), toon, url_str, player['combat_type'], player['rarity'], player['level'], gear_level_str, player['power']])


#def validateGuildConfig(cfg,guild_string):

def getCLIArguments():
    parser = argparse.ArgumentParser(description='Generates report from swgoh guilds')

    parser.add_argument('--guild', action="store", required=True)
    parser.add_argument('--zetas', action="store_true", default=False)
    parser.add_argument('--units', action="store_true", default=False)
    parser.add_argument('--arenarank', action="store_true", default=False)
    parser.add_argument('--unit-mappings', action="store_true", default=False)
    parser.add_argument('--save-file', action="store_true", default=False)
    parser.add_argument('--send-discord', action="store_true", default=False)
    parser.add_argument('--upload-dbx', action="store_true", default=False)
    parser.add_argument('--config', action="store")
    parser.add_argument('--env-config', action="store")
    parser.add_argument('--prod', action="store_true", default=False)
    parser.add_argument('--debug', action="store_true", default=False)

    return vars(parser.parse_args())


def get_guild_config(cfg, guild_string):
    guilds = cfg['guilds']
    return next((item for item in guilds if item["name"] == guild_string))

def upload_file_to_dropbox(token,file,dbx_path):

    print("File: " + file)
    print("dbx: " + dbx_path)

    # Create an instance of a Dropbox class, which can make requests to the API.
    print("Creating a Dropbox object...")
    dbx = dropbox.Dropbox(token)

    # Check that the access token is valid
    try:
        dbx.users_get_current_account()
    except AuthError as err:
        sys.exit("ERROR: Invalid access token; try re-generating an "
            "access token from the app console on the web.")


    with open(file, 'rb') as f:
        # We use WriteMode=overwrite to make sure that the settings in the file
        # are changed on upload
        print("Uploading " + file + " to Dropbox as " + dbx_path + "...")
        try:
            dbx.files_upload(f.read(), dbx_path, mode=WriteMode('overwrite'))
        except ApiError as err:
            # This checks for the specific error where a user doesn't have
            # enough Dropbox space quota to upload this file
            if (err.error.is_path() and
                    err.error.get_path().reason.is_insufficient_space()):
                sys.exit("ERROR: Cannot back up; insufficient space.")
            elif err.user_message_text:
                print(err.user_message_text)
                sys.exit()
            else:
                print(err)
                sys.exit()


def setup_logging():
    # Setup logging
    logger = logging.getLogger('report_generator')
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

##############################
#   Main                     #
##############################

# Get CLI and config file configuration
args = getCLIArguments()
cfg = load_config(args['config'])

user_cfg = args['env_config']
TOKEN = user_cfg['token']

logger = setup_logging()
logger.debug(print(cfg))

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
output_base_path = cfg['outputBasePath']
guild_output_base_path = output_base_path + guild + "/"


#
# Get Zetas
#
if args['zetas']:
    print("Scraping zetas...")
    url = guild_config['zetas']['url']
    players = get_zetas(url)
    if args['save_file']:
        print("--Writing to file...")
        output_folder = guild_output_base_path + "zetas/"
        output_file = guild + "_zetas" + "_" + file_timestamp + '.csv'
        headers = ["timestamp", "player", "toon", "zeta"]
        write_zetas_to_file(entry_timestamp, headers, players, output_folder, output_file)

    if args['upload_dbx']:
        print("--Uploading file to Dropbox...")
        output_folder = guild_output_base_path + "zetas/"
        output_file = guild + "_zetas" + "_" + file_timestamp + '.csv'
        upload_file_to_dropbox(TOKEN,output_folder + output_file, "/a")
#
# Get Arena Rank
#
if args['arenarank']:
    print("Scraping arena rank...")

    url = guild_config['arenarank']['url']
    noPlayers = 0 if args['prod'] else 2
    players = get_arena_ranks(url, noPlayers)

    if args['save_file']:
        print("--Writing to file...")
        output_folder = guild_output_base_path + "arenarank/"
        output_file = guild + "_arenarank" + "_" + file_timestamp + '.csv'
        headers = ["timestamp", "player", "url", "arenarank"]
        write_arenarank_to_file(entry_timestamp, headers, players, output_folder, output_file)

    if args['send_discord']:
        print("--Writing to Discord...")
        text = gen_arenarank_report_text(players, report_timestamp)
        discord_webhook_url = guild_config['discordReportingWebhook-prod'] if args['prod'] else guild_config['discordReportingWebhook-test']
        send_discord_report(discord_webhook_url, text)

#
# Get Guild Units
#
if args['units']:
    print("Scraping guildUnits...")

    url = guild_config['guildUnits']['url']
    toons = get_units(url)

    if args['save_file']:
        print("--Writing to file...")
        output_folder = guild_output_base_path + "guildUnits/"
        output_file = guild + "_guildUnits" + "_" + file_timestamp + '.csv'
        headers = ["timestamp", "player", "toon", "url", "combat_type", "rarity", "level", "gear_level", "power"]
        write_units_to_file(entry_timestamp, headers, toons, output_folder, output_file)


#
# Get Guild Units
#
if args['unit_mappings']:
    print("Scraping unit mappings...")

    url = cfg['global']['unitMappings']['url']
    toons = get_units(url)

    if args['save_file']:
        print("--Writing to file...")
        output_folder = guild_output_base_path + "guildUnits/"
        output_file = guild + "_guildUnits" + "_" + file_timestamp + '.csv'
        headers = ["timestamp", "player", "toon", "url", "combat_type", "rarity", "level", "gear_level", "power"]
        write_units_to_file(entry_timestamp, headers, toons, output_folder, output_file)