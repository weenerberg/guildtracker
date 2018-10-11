import logging
import yaml
from os.path import join

logger = logging.getLogger(__name__)


class Config(object):

	ENV_CFG = None
	CFG = None
	ANOMALITIES = None
	ARGS = None

	def __init__(self, config_dir, cmd_args):
		self.config_dir = config_dir
		Config.ENV_CFG = self.__load_config('env_config.yml')
		Config.CFG = self.__load_config('config.yml')
		Config.ANOMALITIES = self.__load_config('knownNameAnomalities.yml')
		Config.ARGS = cmd_args

		logger.info("ENV_CFG: %s" % Config.ENV_CFG)
		logger.info("CFG: %s" % Config.CFG)
		logger.info("ANOMALITIES: %s" % Config.ANOMALITIES)
		logger.info("ARGS: %s" % Config.ARGS)

	#
	#
	#
	def __load_config(self, filename):
		logger.info("Loading config file: " + join(self.config_dir, filename))
		with open(join(self.config_dir, filename), 'r') as ymlfile:
			return yaml.load(ymlfile)

	def get_all_known_anomalities(self):
		retval = []
		for key, value in Config.ANOMALITIES.items():
			for ano in value:
				retval.append(ano)
		return retval