import logging
from operator import itemgetter
import re
from ocr_handler import OcrHandler

logger = logging.getLogger(__name__)


class SithScoreHandler(OcrHandler):

	HEADERS = ["timestamp", "player", "event_type", "score_type", "total_score", "ordinal", "error"]
	
	def __init__(self, inbox_path, guild, members, ws_base_path, dbx_base_path, datasource_folder, archive_folder, dbx_token, webhook, is_test):
		super().__init__(inbox_path, guild, members, ws_base_path, dbx_base_path, datasource_folder, archive_folder, dbx_token, webhook, is_test)

	def get_event_type(self):
		return "sith"

	def get_score_type(self):
		return "totalscore"

	def get_headers(self):
		return self.HEADERS

	#def get_file_timestamp(self):
	#	return self.__file_timestamp

	def clean_ocr_output(self, text):
		text = text.replace(" ies ", " ").replace(" iss ", " ").replace(" ives "," ").replace(" vies "," ").replace(" ues ", " ")
		text = text.replace("Lvl 85", " ").replace("Lvi 85 "," ")
		text = text.replace("HA3 "," ").replace("HAS "," ")

		text = re.sub(r'[§«=—-]', ' ', text)
		text = re.sub(r'\s$', '', text)
		text = re.sub(r'#\d{1,2}', ' ', text)
		text = re.sub(r'([,\.]) (\d)', r'\1\2', text)
		text = re.sub(r'(\d) (\d)', r'\1,\2', text)
		return text

	def parse_text(self, file_ordinal, event_datetime, known_players, known_anomalities, text):
		self.__file_timestamp = event_datetime
		# Loop over players
		players_found = 0
		player_rounds = []

		for player in known_players:
			score = ""
			error = ""
			regex = '(?<=' + re.escape(player) + ').*?(\d{1,3}(?:[.,]\d{3})*)$'
			m = re.search(regex, text, re.DOTALL | re.MULTILINE)

			player_round = {}

			if m is not None:
				players_found = players_found + 1
				score = m.group(1)
				internal_ordinal = text.find(player)

				player = self.match_anomality(player, known_anomalities)
				if player is None:
					player = "ERROR"

				player_round = {
					'timestamp': event_datetime.strftime("%Y-%m-%d %H:%M:%S"),
					'event_type': "sith",
					'name': player,
					'score': score.replace(".", "").replace(",", ""),
					'score_type': "totalscore",
					'ordinal': str(file_ordinal).zfill(2) + '_' + str(internal_ordinal).zfill(3),
					'error': error
				}

			else:
				m = re.search(re.escape(player), text, re.DOTALL | re.MULTILINE)
				if m is not None:
					players_found = players_found + 1
					score = "---"
					internal_ordinal = text.find(player)

					player = self.match_anomality(player, known_anomalities)
					player_round = {
						'timestamp': event_datetime.strftime("%Y-%m-%d %H:%M:%S"),
						'event_type': "sith",
						'name': player,
						'score': score.replace(".","").replace(",",""),
						'score_type': "totalscore",
						'ordinal': str(file_ordinal).zfill(2) + '_' + str(internal_ordinal).zfill(3),
						'error': error
					}

			if player_round:
				player_rounds.append(player_round)

		if players_found < 3:
			logger.warning("Only " + str(players_found) + " players found in \n" + text)

		return player_rounds

	def generate_statistics(self):
		total_score = 0
		max_score = 0
		for round in self.get_data():
			current_score = int(round['score']) if round['score'] != '---' else 0
			if current_score > max_score:
				max_score = current_score

			total_score += current_score

		logger.info("Max score: %d" % max_score)

		max_netto_score = 0
		for round in self.get_data():
			current_score = int(round['score']) if round['score'] != '---' else 0
			gp = 0
			for player in self.members:
				if player['data']['name'] == round['name']:
					gp = player['data']['galactic_power']
					logger.info("Found GP for " + round['name'])
					break
			brutto_score = (30.0 * current_score)/max_score
			netto_score = 1000000*current_score/(gp-150000.0)**2
			if netto_score > max_netto_score:
				max_netto_score = netto_score

			round.update({'score_brutto': brutto_score})
			round.update({'score_netto': netto_score})
			logger.info("Player: " + round['name'])
			logger.info("--GP: %d" % gp)
			logger.info("--Score: %d" % current_score)
			logger.info("--Brutto: %.2f" % brutto_score)
			logger.info("--Netto: %.2f" % netto_score)

		logger.info("Max Netto Score: %f" % max_netto_score)
		normalization_factor = 30/max_netto_score

		for round in self.get_data():
			old_netto_score = float(round['score_netto'])
			normalized_netto_score = normalization_factor * old_netto_score
			round.update({'score_netto': normalized_netto_score})

			logger.info("Player: " + round['name'])
			logger.info("--Norm netto: %.2f" % normalized_netto_score)

			logger.info(round)

	def write_data_to_file_helper(self, csv_writer):
		for player in self.get_data():
			csv_writer.writerow([player['timestamp'], player['name'], player['event_type'], player['score_type'], player['score'], player['ordinal'], player['error']])

	def generate_report_text(self, prefix, suffix, type):
		if type is 'total':
			sorted_players = sorted(self.data, key=itemgetter('ordinal'), reverse=False)

			body = '`'
			body += '{:<18}'.format('Name') + '{:>8}'.format('Score') + '{:>7}'.format('Brutto') + '{:>5}'.format('Netto') + '\n'
			for player in sorted_players:
				score = 0
				try:
					score = int(player['score'])
				except:
					score = -10

				if score == 0:
					score = -10

				score_brutto = float(player['score_brutto'])
				score_netto = float(player['score_netto'])

				body += '{:<18}'.format(player['name']) + '{:8d} {:5.2f} {:5.2f}'.format(score, score_brutto, score_netto) + '\n'
			body += '`'
			return prefix + body + suffix + '\n'
		elif type is 'over':
			sorted_players = sorted(self.data, key=itemgetter('score_netto'), reverse=True)

			body = '`'
			body += '{:<18}'.format('Name') + '{:>8}'.format('Score') + '{:>6}'.format('Netto') + '\n'

			i = 0
			for player in sorted_players:
				i += 1
				score = 0
				try:
					score = int(player['score'])
				except:
					score = -10

				if score == 0:
					score = -10

				score_netto = float(player['score_netto'])

				body += '{:<18}'.format(player['name']) + '{:8d} {:5.2f}'.format(score, score_netto) + '\n'
				if i > 5:
					break

			body += '`'
			return prefix + body + suffix + '\n'
		elif type is 'under':
			sorted_players = sorted(self.data, key=itemgetter('score_netto'), reverse=False)

			body = '`'
			body += '{:<18}'.format('Name') + '{:>8}'.format('Score') + '{:>6}'.format('Netto') + '\n'

			i = 0
			for player in sorted_players:
				i += 1
				score = 0
				try:
					score = int(player['score'])
				except:
					score = -10

				if score == 0:
					score = -10

				score_netto = float(player['score_netto'])

				body += '{:<18}'.format(player['name']) + '{:8d} {:5.2f}'.format(score, score_netto) + '\n'
				if i > 5:
					break

			body += '`'
			return prefix + body + suffix + '\n'
