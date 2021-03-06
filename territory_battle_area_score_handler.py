import logging
from os.path import isfile, isdir, join, dirname, basename, splitext, exists, realpath, normpath
from os import listdir, walk, rename, makedirs, getcwd
import subprocess
from PIL import Image
from shutil import copy, copyfile
import re
import csv
from ocr_handler import OcrHandler

logger = logging.getLogger(__name__)

known_areas = ['Contested Airspace', 'Forward Trenches', 'Imperial Fleet Staging Area', 'Imperial Flank']
class TerritoryBattleAreaScoreHandler(OcrHandler):

	def __init__(self, event_timestamp):
		self.event_timestamp = event_timestamp

	def match_anomality(self, player, mapping):
		for k, v in mapping.items():
		    for ano in v:
		    	if ano == player:
		    		logger.info("Anomality detected. Fixing. " + player + "->" + k)
		    		return k    		
		return player

	def parse_text(self, known_players, known_anomalities, text):
		#Loop over players					
		players_found = 0

		player_rounds = []

		print(text)

		for area in known_areas:
			regex = '(?<=' + re.escape(area) + ').*?(\d{1,3}(?:[ .,]\d{3})*) / (\d{1,3}(?:[ .,]\d{3})*)'
			m = re.search(regex, text, re.DOTALL | re.MULTILINE)

			player_round = {}

			if m is not None:
				players_found = players_found + 1
				score = m.group(1)
				max_score = m.group(2)
				area = self.match_anomality(area, known_anomalities)
				if area == None:
					area = "ERROR"

				player_round = {
					'timestamp': self.event_timestamp,
					'event_type': "tb",
					'name': area,
					'score': score.replace(".","").replace(",","").replace(" ",""),
					'max_score': max_score.replace(".","").replace(",","").replace(" ",""),
					'score_type': "areascore"
				}
				
			

			if player_round:
				if not any(d['name'] == player_round['name'] for d in player_rounds):
					player_rounds.append(player_round)
				else:
					logger.info("Duplicate. Skipping. " + player_round['name'])
					

		if players_found < 3:
			logger.warning("Only " + str(players_found) + " players found in \n" + text)

		return player_rounds

	def dbx_upload(self, dbx_handler, dbx_output_path, file):
		filename = basename(file)
		dbx_handler.upload_file(file, dbx_output_path + filename)

	def save_file(self, output_file, player_rounds):
		logger.info("Saving file to " + output_file)
		makedirs(dirname(output_file), exist_ok=True)

		csv_writer = csv.writer(open(output_file, "w"), lineterminator='\n')
		csv_writer.writerow(["timestamp", "player", "event_type", "score_type", "score_1"])

		for player in player_rounds:
			csv_writer.writerow([player['timestamp'], player['name'], player['event_type'], player['score_type'], player['score']])	

		return output_file

	def clean_ocr_output(self, text):
		text = text.replace(" ies ", " ").replace(" iss ", " ").replace(" ives "," ").replace(" vies "," ").replace(" ues ", " ")
		text = text.replace("Lvl 85", " ").replace("Lvi 85 "," ")
		#text = text.replace("\r\n"," ").replace("\n"," ")
		text = text.replace("HA3 "," ").replace("HAS "," ")

		text = re.sub(r'[§«=—-]',' ', text)
		text = re.sub(r'\s$','', text)
		text = re.sub(r'#\d{1,2}',' ',text)
		return text

	def preprocess_image(self, path_to_convert, input_file, output_file):
		output_filepath = dirname(realpath(output_file))

		if not exists(output_filepath):
			makedirs(output_filepath)

		cmd = [path_to_convert, input_file, "-colorspace", "gray", "-negate", "-morphology", "close", "diamond", "-threshold", "55%", output_file]
		fconvert = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = fconvert.communicate()
		assert fconvert.returncode == 0, stderr


	def execute_ocr(self, path_to_tesseract, path_to_user_words, path_to_uzn, event_type, score_type, input_file, output_file):
		output_filepath = dirname(realpath(output_file))

		if not exists(output_filepath):
			makedirs(output_filepath)

		im = Image.open(input_file)
		im_width = str(im.size[0])
		im_height = str(im.size[1])


		input_filepath = dirname(realpath(input_file))
		input_filename_w_ext = basename(input_file)
		input_filename, input_filename_extension = splitext(input_filename_w_ext)

		copy_infile = path_to_uzn + event_type.lower() + "_" + score_type.lower() + "_" + im_width +"x" + im_height + ".uzn"
		copy_outfile = input_filepath + "/" + input_filename + ".uzn"
		
		copy(copy_infile, copy_outfile)

		cmd = [path_to_tesseract, input_file, "stdout", "-l", "eng", "--user-words", path_to_user_words, "-c", "-load_system_dawg=F", "-c", "load_freq_dawg=F", "--psm", "4"]
		ftesseract = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = ftesseract.communicate()
		assert ftesseract.returncode == 0, stderr
		
		return self.clean_ocr_output(stdout.decode())

	