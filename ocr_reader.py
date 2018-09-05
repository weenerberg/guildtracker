#!/usr/bin/python3
from os import listdir, walk, rename, makedirs
from os.path import isfile, isdir, join, dirname, basename, splitext, exists, realpath, normpath
import subprocess
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


for event_type_folder in list(folders_in(BASE_PATH)):
	event_type = basename(event_type_folder)
	print("Event type: " + event_type)
	print("1" + event_type_folder)
	for event_folder in list(folders_in(event_type_folder)):
		print("2" + event_folder)
		event_date = event_folder.split("_")[1]
		for event_score_type in list(folders_in(event_folder)):
			print("3" + event_score_type)
			f = []
			for (dirpath, dirnames, filenames) in walk(event_score_type):
				f.extend(join(dirpath, filename) for filename in filenames)
				break
			for event_score_file in f:
				print("4" + event_score_file)
				
				filename_w_ext = basename(event_score_file)
				filename, file_extension = splitext(filename_w_ext)

				input_file = '/'.join(event_score_file.split('\\'))
				print(input_file)
				output_file = event_score_type + "/preprocessed/" + filename + "_preprocessed" + file_extension
				output_file = '/'.join(output_file.split('\\'))
				print(output_file)

				output_filepath = dirname(realpath(output_file))
				if not exists(output_filepath):
					makedirs(output_filepath)
				cmd = ["C:/Program Files/ImageMagick-7.0.8-Q16/convert", input_file, "-colorspace", "gray", "-negate", "-morphology", "close", "diamond", "-threshold", "55%", output_file]
				fconvert = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				stdout, stderr = fconvert.communicate()
				assert fconvert.returncode == 0, stderr
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