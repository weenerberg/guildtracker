# -*- coding: utf-8 -*-

"""
guildtracker.utils
~~~~~~~~~~~~~~
This module provides utility functions that are used within GuildTracker
"""

import os
import csv

def setup_new_datasource_file(headers, filepath, filename):
    if not os.path.exists(filepath):
        os.makedirs(filepath)
        
    newFile = csv.writer(open(filepath + filename, "w"),lineterminator='\n')
    newFile.writerow(headers)
    return newFile

def rename(dir, pattern, titlePattern):
	for pathAndFilename in glob.iglob(os.path.join(dir, pattern)):
		title, ext = os.path.splitext(os.path.basename(pathAndFilename))
		os.rename(pathAndFilename, os.path.join(dir, titlePattern % title + ext))

def replace_substring_in_folder_filenames(folder, replace, replacement):
	pathiter = (os.path.join(root, filename)
    for root, _, filenames in os.walk(folder)
    for filename in filenames)

	for path in pathiter:
		new_name =  path.replace(replace, replacement)
		if new_name != path:
			os.rename(path, new_name)