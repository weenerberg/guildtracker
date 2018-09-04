#!/usr/bin/python3
from os import listdir
from os.path import isfile, isdir, join
import logging
import argparse
import yaml

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

BASE_PATH = "C:/Users/mawe/Dropbox (Personal)/swgoh/GuildTracker/ocr_ws/inbox/"
SITH_EVENT_PATH = BASE_PATH + "sith/"

def folders_in(path_to_parent):
	for fname in listdir(path_to_parent):
		if isdir(join(path_to_parent,fname)):
			yield (join(path_to_parent,fname))

forlist(folders_in(SITH_EVENT_PATH)))
# poll dbx folder for batches of screenshots

# for each file in a batch
# run preprocess - convert
#path = "/path/to/some.pdf"
#cmd = ["convert", "-monochrome", "-compress", "lzw", path, "tif:-"]
#fconvert = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#stdout, stderr = fconvert.communicate()
#assert fconvert.returncode == 0, stderr

# now stdout is TIF image. let's load it with OpenCV
#filebytes = numpy.asarray(bytearray(stdout), dtype=numpy.uint8)
#image = cv2.imdecode(filebytes, cv2.IMREAD_GRAYSCALE)

#spara 
