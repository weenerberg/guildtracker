# -*- coding: utf-8 -*-

"""
guildtracker.utils
~~~~~~~~~~~~~~
This module provides utility functions that are used within GuildTracker
"""

import os
import csv
import shutil
import logging

logger = logging.getLogger(__name__)

def setup_new_datasource_file(headers, filepath):
	os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
	newFile = csv.writer(open(filepath, "w"),lineterminator='\n')
	newFile.writerow(headers)
	return newFile


#
#
#
def folders_in(path_to_parent):
	for fname in os.listdir(path_to_parent):
		if os.path.isdir(os.path.join(path_to_parent, fname)):
			yield (os.path.join(path_to_parent, fname))


#
#TODO Fix so top directory is moved as well
#
def move_directory(root_src_dir, root_dst_dir):
	for src_dir, dirs, files in os.walk(root_src_dir):
		dst_dir = src_dir.replace(root_src_dir, root_dst_dir, 1)
		if not os.path.exists(dst_dir):
			os.makedirs(dst_dir)
		for file_ in files:
			src_file = os.path.join(src_dir, file_)
			dst_file = os.path.join(dst_dir, file_)
			if os.path.exists(dst_file):
				os.remove(dst_file)
			logger.debug("Moving " + src_file + " to " + dst_dir)
			shutil.move(src_file, dst_dir)


#
#
#
def get_all_files_in_folder(folder):
	f = []
	for (dirpath, dirnames, filenames) in os.walk(folder):
		f.extend(os.path.join(dirpath, filename) for filename in filenames)
		break
	f.sort()
	return f


#
#
#
def rename(dir, pattern, titlePattern):
	for pathAndFilename in glob.iglob(os.path.join(dir, pattern)):
		title, ext = os.path.splitext(os.path.basename(pathAndFilename))
		os.rename(pathAndFilename, os.path.join(dir, titlePattern % title + ext))


#
#
#
def replace_substring_in_folder_filenames(folder, replace, replacement):
	pathiter = (os.path.join(root, filename)
    for root, _, filenames in os.walk(folder)
    for filename in filenames)

	for path in pathiter:
		new_name =  path.replace(replace, replacement)
		if new_name != path:
			os.rename(path, new_name)


#
#
#
def get_guild_config(cfg, guild_string):
    guilds = cfg['guilds']
    return [next((item for item in guilds if item["name"] == guild_string))]


#
#
#
def rolling_window(seq, window_size):
	it = iter(seq)
	win = [it.next() for cnt in xrange(window_size)] # First window
	yield win
	for e in it: # Subsequent windows
		win[:-1] = win[1:]
		win[-1] = e
		yield win
