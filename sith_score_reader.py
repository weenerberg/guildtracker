import logging
from os.path import isfile, isdir, join, dirname, basename, splitext, exists, realpath, normpath
from os import listdir, walk, rename, makedirs, getcwd
import subprocess
from PIL import Image
from shutil import copy, copyfile
import re
import csv

logger = logging.getLogger('guildtracker.sithscorereader')

class SithScoreReader(object):

	def __init__(self, event_timestamp):
		self.event_timestamp = event_timestamp

	def match_anomality(self, player, mapping):
		for k, v in mapping.items():
		    for ano in v:
		    	#print(ano)
		    	if ano == player:
		    		print("Anomality detected. Fixing. " + player + "->" + k)
		    		return k
		#print("No anomality")	    		
		return player

	def parse_text(self, known_players, known_anomalities, text):
		#Loop over players					
		players_found = 0

		player_rounds = []

		for player in known_players:
			score = ""
			regex = '(?<=' + re.escape(player) + ').*?(\d{1,3}(?:[.,]\d{3})*)$'
			m = re.search(regex, text, re.DOTALL | re.MULTILINE)

			player_round = {}

			if m is not None:
				players_found = players_found + 1
				score = m.group(1)

				player = self.match_anomality(player, known_anomalities)
				if player == None:
					player = "ERROR"

				player_round = {
					'timestamp': self.event_timestamp,
					'event_type': "sith",
					'name': player,
					'score': score.replace(".","").replace(",",""),
					'score_type': "totalscore"
				}
				
			else:
				m = re.search(re.escape(player), text, re.DOTALL | re.MULTILINE)
				if m is not None:
					players_found = players_found + 1
					score = "---"
					player = self.match_anomality(player, known_anomalities)
					player_round = {
						'timestamp': self.event_timestamp,
						'event_type': "sith",
						'name': player,
						'score': score.replace(".","").replace(",",""),
						'score_type': "totalscore"
					}


			if player_round:
				if not any(d['name'] == player_round['name'] for d in player_rounds):
					player_rounds.append(player_round)
				else:
					print("Duplicate. Skipping. " + player_round['name'])
					

		if players_found < 3:
			print("Only " + str(players_found) + " players found in \n" + text)
			print("--------------------")

		return player_rounds

	def dbx_upload(self, dbx_handler, dbx_output_path, file):
		filename = basename(file)
		dbx_handler.upload_file(file, dbx_output_path + filename)

	def save_file(self, output_file, player_rounds):
		makedirs(dirname(output_file), exist_ok=True)

		csv_writer = csv.writer(open(output_file, "w"),lineterminator='\n')
		csv_writer.writerow(["timestamp", "player", "event_type", "score_type", "total_score"])

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


	def execute_ocr(self, path_to_tesseract, path_to_user_words, event_type, score_type, input_file, output_file):
		output_filepath = dirname(realpath(output_file))

		if not exists(output_filepath):
			makedirs(output_filepath)

		im = Image.open(input_file)
		im_width = str(im.size[0])
		im_height = str(im.size[1])


		input_filepath = dirname(realpath(input_file))
		input_filename_w_ext = basename(input_file)
		input_filename, input_filename_extension = splitext(input_filename_w_ext)

		copy_infile = "config/" + event_type.lower() + "_" + score_type.lower() + "_" + im_width +"x" + im_height + ".uzn"
		copy_outfile = input_filepath + "/" + input_filename + ".uzn"
		#print("Copy input: " + copy_infile)
		#print("Copy output: " + copy_outfile)
		copy(copy_infile, copy_outfile)

		stdout = ""
		if True:
			cmd = [path_to_tesseract, input_file, "stdout", "-l", "eng", "--user-words", path_to_user_words, "-c", "-load_system_dawg=F", "-c", "load_freq_dawg=F", "--psm", "4"]
			ftesseract = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			stdout, stderr = ftesseract.communicate()
			assert ftesseract.returncode == 0, stderr
			return self.clean_ocr_output(stdout.decode())
		else:
			copy("test/dummy_tess", tesseract_output_file)
			print(tesseract_output_file)
			#print("Current wdir: " + getcwd())
			cmd = ["type",  "test\\dummy_tess"]
			fconvert = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			stdout, stderr = fconvert.communicate()
			assert fconvert.returncode == 0, stderr
			return self.clean_ocr_output(stdout.decode())

	