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