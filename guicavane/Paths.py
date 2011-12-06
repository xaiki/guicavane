#!/usr/bin/env python
# coding: utf-8

import os
import sys
import tempfile

# Directory separator
SEP = os.sep

if sys.platform == "win32":
    HOME_DIR = os.path.join(os.environ["HOME"], "/.guicavane")
    MAIN_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    VLC_LOCATION = os.path.join(os.environ["ProgramFiles"], "VideoLAN", "VLC", "vlc.exe")
else:
    HOME_DIR = os.path.join(os.environ["HOME"], "/.guicavane")
    MAIN_DIR = os.path.dirname(__file__)
    VLC_LOCATION = "/usr/bin/vlc"

HOME_DIR = os.path.expanduser("~")

TEMP_DIR = tempfile.gettempdir()

CONFIG_DIR = os.path.join(HOME_DIR, ".guicavane")
CONFIG_FILE = os.path.join(CONFIG_DIR, "guicavane.conf")

MARKS_FILE = os.path.join(CONFIG_DIR, "marks.slist")
FAVORITES_FILE = os.path.join(CONFIG_DIR, "favorites.slist")

IMAGES_DIR = os.path.join(MAIN_DIR, "Images")
HOSTS_IMAGES_DIR = os.path.join(IMAGES_DIR, "hosts")

GUI_DIR = os.path.join(MAIN_DIR, "Glade")
