#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Big Kernel Manager - Application Class

This module defines the main application class for the Big Kernel Manager.
"""

import os
import json
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gio, Adw, Gdk

from core.constants import APP_ID, APP_NAME, CONFIG_DIR, SETTINGS_FILE
from core.logging_config import init_app_logging, get_logger
from ui.window import KernelManagerWindow


class SettingsManager:
    """Settings manager for the Big Kernel Manager application."""

    def __init__(self):
        """Initialize the settings manager."""
        self.settings_file = SETTINGS_FILE
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self._settings = self._load_settings()
        self._logger = get_logger("SettingsManager")

    def _load_settings(self) -> dict:
        """Load settings from file."""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading settings: {e}")
        return {}

    def _save_settings(self) -> bool:
        """Save settings to file."""
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def get(self, key: str, default=None):
        """Get a setting value."""
        return self._settings.get(key, default)

    def set(self, key: str, value) -> bool:
        """Set a setting value and save."""
        self._settings[key] = value
        return self._save_settings()

    # Backwards compatibility aliases
    def load_setting(self, key: str, default=None):
        """Load a setting value (alias for get)."""
        return self.get(key, default)

    def save_setting(self, key: str, value) -> bool:
        """Save a setting value (alias for set)."""
        return self.set(key, value)


class KernelManagerApplication(Adw.Application):
    """Main application class for Big Kernel Manager."""

    def __init__(self):
        """Initialize the application."""
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self.on_activate)

        # Initialize logging
        self._logger = init_app_logging()
        self._logger.info(f"Starting {APP_NAME}")

        # Initialize settings manager
        self.settings_manager = SettingsManager()

        # Load custom CSS
        self._load_css()

    def _load_css(self) -> None:
        """Load custom CSS styling from file."""
        css_provider = Gtk.CssProvider()

        # Get the path to the CSS file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        css_path = os.path.join(base_dir, "assets", "css", "style.css")

        try:
            css_provider.load_from_path(css_path)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
            self._logger.debug(f"Loaded CSS from {css_path}")
        except Exception as e:
            self._logger.warning(f"Error loading CSS: {e}")

    def on_activate(self, app) -> None:
        """
        Callback for the application activation.

        Args:
            app: The application instance.
        """
        self._logger.info("Application activated")
        win = KernelManagerWindow(application=app)
        win.present()

    def show_error_dialog(self, message: str) -> None:
        """
        Show an error dialog with the given message.

        Args:
            message: Error message to display.
        """
        self._logger.error(f"Error dialog: {message}")
        dialog = Adw.MessageDialog.new(self.get_active_window())
        dialog.set_heading("Error")
        dialog.set_body(message)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.set_close_response("ok")
        dialog.present()
