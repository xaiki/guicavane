#!/usr/bin/env python
# encoding: utf-8

"""
Player. Handles the download and starts the player.
"""

import os
from gi.repository import Gtk
import time
import gobject
import subprocess

import Downloaders
from pycavane import api
from Constants import HOSTS_GUI_FILE, HOSTS_VIEW_COLUMN_OBJECT


class Player(object):
    """
    Class that takes care of the downloading and correctly
    playing the file.
    """

    def __init__(self, gui_manager, file_object,
                 file_path=None, download_only=False, choose_host=False):
        self.gui_manager = gui_manager
        self.config = self.gui_manager.config
        self.file_object = file_object
        self.download_only = download_only
        self.choose_host = choose_host

        self.file_path = file_path
        if not self.file_path:
            self.file_path = self.config.get_key("cache_dir")

        self.file_path = os.path.join(self.file_path, self.get_filename())

        # Builder for the hosts selection
        self.hosts_builder = Gtk.Builder()
        self.hosts_builder.add_from_file(HOSTS_GUI_FILE)
        self.hosts_builder.connect_signals(self)

        glade_objects = ["hosts_window", "hosts_icon_view",
                         "hosts_icon_view_model"]

        for glade_object in glade_objects:
            setattr(self, glade_object, self.hosts_builder.get_object(glade_object))

        self.gui_manager.background_task(self.get_hosts, self.display_hosts,
            status_message="Fetching hosts...", unfreeze=False)

    def get_hosts(self):
        """ Returns a list with the avaliable downloaders for the file. """

        result = []
        avaliable_downloaders = Downloaders.get_avaliable()

        hosts = self.file_object.file_hosts
        hosts["dummy"] = ""

        for host in hosts:
            if host in avaliable_downloaders:
                result.append(Downloaders.get(host, self.gui_manager, hosts[host]))

        return result

    def display_hosts(self, (is_error, result)):
        """ Shows up the hosts selecting window. """

        if is_error:
            self.gui_manager.report_error("Error displaying hosts: %s" % result)
            gobject.idle_add(self.gui_manager.progress.hide)
            return

        gobject.idle_add(self.gui_manager.set_status_message, "")

        if len(result) == 0:
            self.gui_manager.report_error("No host found")
            self.gui_manager.unfreeze()
        elif len(result) == 1:
            gobject.idle_add(self.gui_manager.set_status_message,
                "Only one host found, starting download...")
            self.downloader = result[0]
            self.downloader.process_url(self.play, self.file_path)
        else:
            megaupload = [x for x in result if x.name == "Megaupload"]
            if not self.choose_host and len(megaupload) != 0 and \
                   self.config.get_key("automatic_megaupload"):

                gobject.idle_add(self.gui_manager.set_status_message,
                    "Automatically starting with megaupload")
                self.downloader = megaupload[0]
                self.downloader.process_url(self.play, self.file_path)
            else:
                for downloader in result:
                    icon = downloader.icon
                    name = downloader.name
                    self.hosts_icon_view_model.append([icon, name, downloader])

                self.hosts_window.show_all()

    def play(self):
        """ Starts the playing of the file on file_path. """

        self.gui_manager.background_task(self.pre_download,
            self.open_player, unfreeze=False)

    def pre_download(self):
        """ Downloads some content to start safely the player. """

        # Download the subtitle
        gobject.idle_add(self.gui_manager.set_status_message, "Downloading subtitles...")
        try:
            self.file_object.get_subtitle(filename=self.file_path.replace(".mp4", ""))
        except:
            gobject.idle_add(self.gui_manager.set_status_message, "Subtitle not found")

        # Wait for the file to exists
        gobject.idle_add(self.gui_manager.set_status_message, "Wait please...")
        while not os.path.exists(self.file_path):
            time.sleep(1)

        # Show the progress bar box
        gobject.idle_add(self.gui_manager.progress.set_fraction, 0.0)
        gobject.idle_add(self.gui_manager.progress_box.show)
        gobject.idle_add(self.gui_manager.set_status_message, "Filling cache...")

        if self.downloader.file_size != 0:
            # Waits %1 of the total download
            percent = self.downloader.file_size * 0.01

            while self.downloader.downloaded_size < percent:
                self._update_progress()
                time.sleep(1)
        else:
            # Waits 2MB, just an arbitrary amount
            while self.downloader.downloaded_size < 2 * 1024 * 1024:
                gobject.idle_add(self.gui_manager.progress.pulse)
                time.sleep(0.5)

    def open_player(self, (is_error, result)):
        """ Fires up a new process with the player runing. """

        if is_error:
            self.gui_manager.report_error("Error pre downloading: %s" % result)
            return

        if self.download_only:
            message = "Downloading: %s"
        else:
            message = "Playing: %s"

        gobject.idle_add(self.gui_manager.set_status_message,
                         message % self.file_object.name)

        player_location = self.config.get_key("player_location")
        player_args = self.config.get_key("player_arguments").split()
        player_cmd = [player_location] + player_args + [self.file_path]

        if not self.download_only:
            self.player_process = subprocess.Popen(player_cmd)

        self.gui_manager.background_task(self.update, self.on_finish)

    def update(self):
        """ Updates the GUI with downloading data. """

        stop = False
        speed_list = []
        last_downloaded = 0

        while not stop:
            downloaded_size = self.downloader.downloaded_size

            speed_list.append((downloaded_size - last_downloaded) / 1024.0)
            last_downloaded = downloaded_size

            list_offset = len(speed_list) - 30 if len(speed_list) > 30 else 0
            speed_list = speed_list[list_offset:]
            speed_avarage = sum(speed_list) / len(speed_list)

            if speed_avarage > 0:
                remaining_size = (self.downloader.file_size - downloaded_size) / 1024.0
                remaining_time = (remaining_size / speed_avarage) / 60
            else:
                remaining_time = 0

            if remaining_time >= 1:  # if it's more than a minute
                if remaining_time == 1:
                    remaining_message = "%d minute left" % remaining_time
                else:
                    remaining_message = "%d minutes left" % remaining_time
            else:
                if (remaining_time * 60) > 10:
                    remaining_message = "%d seconds left" % (remaining_time * 60)
                elif remaining_time != 0:
                    remaining_message = "a few seconds left"
                else:
                    remaining_message = ""

            if downloaded_size < self.downloader.file_size:
                gobject.idle_add(self.gui_manager.progress_label.set_text, \
                    "%.2fKB/s - %s" % (speed_avarage, remaining_message))
            else:
                gobject.idle_add(self.gui_manager.progress_label.set_text, "")

            if self.downloader.file_size != 0:
                self._update_progress()
                time.sleep(1)
            else:
                gobject.idle_add(self.gui_manager.progress.pulse)
                time.sleep(1)

            stop = downloaded_size == self.downloader.file_size

            if not self.download_only:
                stop |= self.player_process.poll() != None

            last_downloaded = downloaded_size

    def _update_progress(self):
        """ Updates the progress bar using the downloaded size and the
        total file size if posible. """

        downloaded_size = self.downloader.downloaded_size
        file_size = self.downloader.file_size

        fraction = downloaded_size / file_size
        gobject.idle_add(self.gui_manager.progress.set_fraction, fraction)
        gobject.idle_add(self.gui_manager.progress.set_text,
            "%.2f%%" % (fraction * 100))

    def on_finish(self, (is_error, result)):
        assert not is_error, str(result)

        self.downloader.stop_downloading = True

        # Hide the progress
        gobject.idle_add(self.gui_manager.progress_box.hide)

        downloaded_size = self.downloader.downloaded_size
        file_size = self.downloader.file_size

        if downloaded_size >= file_size:
            if self.config.get_key("automatic_marks"):
                self.gui_manager.marks.add(self.file_object.id)
                self.gui_manager.refresh_marks()

    def get_filename(self):
        """ Returns the file path of the file. """

        if isinstance(self.file_object, api.Movie):
            return self.file_object.name.replace(os.sep, "_")

        # If isn't a movie it must be an episode
        assert isinstance(self.file_object, api.Episode)

        result = self.config.get_key("filename_template")
        result = result.replace("<show>", self.file_object.show)
        result = result.replace("<season>", "%.2d" % int(self.file_object.season))
        result = result.replace("<episode>", "%s" % str(self.file_object.number))
        result = result.replace("<name>", self.file_object.name)
        for char in '\/:?*"<>|%.':
            result = result.replace(char, "_")
        result = result + ".mp4"

        return result

    # ================================
    # =         CALLBACKS            =
    # ================================

    def _on_hosts_cancel(self, button):
        """ Called when the user press the cancel button on the
        hosts window. """

        self.hosts_window.hide()
        self.gui_manager.unfreeze()

    def _on_host_select(self, *args):
        """ Called whe the user presses the ok button or double
        clicks on the host. """

        cursor = self.hosts_icon_view.get_cursor()
        if cursor == None:
            return

        path = cursor[0]
        self.downloader = self.hosts_icon_view_model[path][HOSTS_VIEW_COLUMN_OBJECT]

        self.hosts_window.hide()
        self.downloader.process_url(self.play, self.file_path)
