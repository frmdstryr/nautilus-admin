# Nautilus Admin - Extension for Nautilus to do administrative operations
# Copyright (C) 2015 Bruno Nova <brunomb.nova@gmail.com>
#               2016 frmdstryr <frmdstryr@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os, subprocess, urlparse, traceback
from gi.repository import Nautilus, GObject, GConf, Gtk, GLib
from gettext import gettext, locale, bindtextdomain, textdomain

ROOT_UID = 0
PKEXEC_PATH="/usr/bin/pkexec"
NAUTILUS_PATH="/usr/bin/nautilus"
GEDIT_PATH="/usr/bin/gedit"
TERMINAL_PATH="/usr/bin/gnome-terminal"

class NautilusAdmin(Nautilus.MenuProvider, GObject.GObject):
	"""Simple Nautilus extension that adds some administrative (root) actions to
	the right-click menu, using 'pkexec' to authenticate the administrator."""
	def __init__(self):
		pass

	def get_file_items(self, window, files):
		"""Returns the menu items to display when one or more files/folders are
		selected."""
		# Don't show when already running as root, or when more than 1 file is selected
		if os.geteuid() == ROOT_UID or len(files) != 1:
			return
		file = files[0]

		# Add the menu items
		items = []
		self._setup_gettext();
		self.window = window
		if file.get_uri_scheme() == "file": # must be a local file/directory
			if file.is_directory():
				if os.path.exists(NAUTILUS_PATH):
					items += [self._create_nautilus_item(file)]
			else:
				if os.path.exists(TERMINAL_PATH) and self._is_executable(file):
					items += [self._create_exec_item(file)]
				if os.path.exists(GEDIT_PATH):
					items += [self._create_gedit_item(file)]

		return items

	def get_background_items(self, window, file):
		"""Returns the menu items to display when no file/folder is selected
		(i.e. when right-clicking the background)."""
		# Don't show when already running as root
		if os.geteuid() == ROOT_UID:
			return

		# Add the menu items
		items = []
		self._setup_gettext();
		self.window = window
		if file.is_directory() and file.get_uri_scheme() == "file":
			if os.path.exists(NAUTILUS_PATH):
				items += [self._create_nautilus_item(file)]

		return items


	def _setup_gettext(self):
		"""Initializes gettext to localize strings."""
		try: # prevent a possible exception
			locale.setlocale(locale.LC_ALL, "")
		except:
			pass
		bindtextdomain("nautilus-admin", "@CMAKE_INSTALL_PREFIX@/share/locale")
		textdomain("nautilus-admin")

	def _create_nautilus_item(self, file):
		"""Creates the 'Open as Administrator' menu item."""
		item = Nautilus.MenuItem(name="NautilusAdmin::Nautilus",
		                         label=gettext("Open as A_dministrator"),
		                         tip=gettext("Open this folder with root privileges"))
		item.connect("activate", self._nautilus_run, file)
		return item

	def _create_exec_item(self, file):
		"""Creates the 'Edit as Administrator' menu item."""
		item = Nautilus.MenuItem(name="NautilusAdmin::ExecAdmin",
		                         label=gettext("Run as A_dministrator"),
		                         tip=gettext("Run this file with root privileges"))
		item.connect("activate", self._exec_run, file)
		return item

	def _create_gedit_item(self, file):
		"""Creates the 'Edit as Administrator' menu item."""
		item = Nautilus.MenuItem(name="NautilusAdmin::Gedit",
		                         label=gettext("Edit as A_dministrator"),
		                         tip=gettext("Open this file in the text editor with root privileges"))
		item.connect("activate", self._gedit_run, file)
		return item

	def _show_warning_dialog(self):
		"""Shows a warning dialog it this is the first time the extension is
		used, and returns True if the user has pressed OK."""
		# Check if this is the first time the extension is used
		conf_dir = GLib.get_user_config_dir() # get "~/.config" path
		conf_file = os.path.join(conf_dir, ".nautilus-admin-warn-shown")
		if os.path.exists(conf_file):
			return True
		else:
			# Show the warning dialog
			self._setup_gettext();
			dialog = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.WARNING,
			                           Gtk.ButtonsType.OK_CANCEL,
			                           gettext("CAUTION!"))
			msg = gettext("Running the File Manager or the Text Editor with Administrator "
			              "privileges <b>is dangerous</b>! <b>You can easily destroy your "
			              "system if you are not careful!</b>\n"
			              "Proceed only if you know what you are doing and understand the risks.")
			dialog.format_secondary_markup(msg)
			response = dialog.run()
			dialog.destroy()

			if response == Gtk.ResponseType.OK:
				# Mark the dialog as shown
				try:
					if not os.path.isdir(conf_dir):
						os.makedirs(conf_dir)
					open(conf_file, "w").close() # create an empty file
				except:
					pass
				return True
			else:
				return False


	def _nautilus_run(self, menu, file):
		"""'Open as Administrator' menu item callback."""
		if self._show_warning_dialog():
			uri = file.get_uri()
			subprocess.Popen([PKEXEC_PATH, NAUTILUS_PATH, "--no-desktop", uri])

	def _is_executable(self, file):
		try:		
			uri = file.get_uri()
			p = urlparse.urlparse(uri)
			path = os.path.abspath(os.path.join(p.netloc, p.path))
			return os.access(path,os.X_OK)
		except:
			return False

	def _exec_run(self, menu, file, gui=True):
		"""'Run as Administrator' menu item callback."""
		if self._show_warning_dialog():
			try:
				uri = file.get_uri()
				p = urlparse.urlparse(uri)
				path = os.path.abspath(os.path.join(p.netloc, p.path))
				#is_app = not os.path.splitext(path)[-1]
				cmd = [PKEXEC_PATH]
				#cmd +=['env','DISPLAY='+os.environ['DISPLAY'],'XAUTHORITY='+os.environ['XAUTHORITY']]
				
				cmd +=[TERMINAL_PATH]
				cmd +=['--working-directory='+os.path.dirname(path)]
				cmd +=['-e',path]

				subprocess.Popen(cmd)
			except:
				traceback.print_exc()

	def _gedit_run(self, menu, file):
		"""'Edit as Administrator' menu item callback."""
		if self._show_warning_dialog():
			uri = file.get_uri()
			subprocess.Popen([PKEXEC_PATH, GEDIT_PATH, uri])