#!/usr/bin/python3
import logging
import argparse
import yaml
from handler_factory import HandlerFactory
from zetas_handler import ZetasHandler
from arena_ranks_handler import ArenaRanksHandler
from units_handler import UnitsHandler
from unit_mappings_handler import UnitMappingsHandler
from zeta_reviews_handler import ZetaReviewsHandler
from utils import get_guild_config

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
cfg = load_config(args['config_dir'] + 'config.yml')
env_cfg = load_config(args['config_dir'] + 'env_config.yml')



#
#
#
#def get_guild_config(cfg, guild_string):
#    guilds = cfg['guilds']
#    return [next((item for item in guilds if item["name"] == guild_string))]


##############################
#           Main             #
##############################

TOKEN = env_cfg['token']

#Configure input and output
folder_prefix = "" if args['prod'] else "TEST/"

root_path = env_cfg['outputBasePath'] + folder_prefix
archive_folder = "archive/datasource/"
ds_folder = "datasource/"

dbx_root_path = cfg['dpxBasePath'] + folder_prefix
dbx_archive_datasources_path = dbx_root_path + "archive/datasource/"
dbx_datasources_path = dbx_root_path + "datasource/"

# Get guild or guilds
guild = args['guild']
guilds = []
if not guild:
    logger.info("No guild specified. Executing all guilds from config.")
    guilds = cfg['guilds']
else:
    guilds = get_guild_config(cfg, guild)

for guild_config in guilds:
    guild = guild_config['name']
    webhook = guild_config['discordReportingWebhook-prod'] if args['prod'] else guild_config['discordReportingWebhook-test']
    is_test = not args['prod']

    handler_factory = HandlerFactory(guild, root_path, dbx_root_path, ds_folder, archive_folder, TOKEN, webhook, is_test)

    # Get Zetas
    if args['zetas']:
        logger.debug("Scraping zetas...")
        url = guild_config['zetas']['url']

        zetas_handler = handler_factory.get_handler(ZetasHandler.MODULE_NAME, url)
        zetas_handler.execute(args['save_file'], False, args['upload_dbx'])

    # Get Arena Rank
    if args['arenaranks']:
        logger.debug("Scraping arena ranks...")
        url = guild_config['arenaranks']['url']

        arena_ranks_handler = handler_factory.get_handler(ArenaRanksHandler.MODULE_NAME, url)
        arena_ranks_handler.execute(args['save_file'], False, args['upload_dbx'])

        if args['send_discord']:
            username = cfg['discord']['username']
            prefix = cfg['discord']['arenaranks']['text']
            arena_ranks_handler.send_discord_report(username, prefix)

    # Get Guild Units
    if args['units']:
        logger.debug("Reading guildUnits...")
        url = guild_config['guildUnits']['url']

        units_handler = handler_factory.get_handler(UnitsHandler.MODULE_NAME, url)
        units_handler.execute(args['save_file'], False, args['upload_dbx'])

    # Get Unit Mappings
    if args['unit_mappings']:
        logger.debug("Reading unit mappings...")
        url = cfg['global']['unitMappings']['url']

        units_mapping_handler = handler_factory.get_handler(UnitMappingsHandler.MODULE_NAME, url)
        units_mapping_handler.execute(args['save_file'], True, args['upload_dbx'])

    # Get Zeta Reviews
    if args['zeta_reviews']:
        logger.debug("Reading zeta reviews...")
        url = cfg['global']['zetaReviews']['url']

        zeta_reviews_handler = handler_factory.get_handler(ZetaReviewsHandler.MODULE_NAME, url)
        zeta_reviews_handler.execute(args['save_file'], True, args['upload_dbx'])
