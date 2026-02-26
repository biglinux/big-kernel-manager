#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Big Kernel Manager - Mesa Drivers Management Page

This module defines the UI for Mesa drivers management, allowing users
to install and switch between different Mesa driver versions.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from core.mesa_manager import MesaManager
from ui.base_page import BasePage
from utils.i18n import _


class MesaPage(BasePage):
    """Page for Mesa drivers management."""

    def __init__(self):
        """Initialize the Mesa drivers management page."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # Initialize Mesa manager
        self.mesa_manager = MesaManager()

        # Progress dialog reference (set by window via BasePage.set_progress_dialog)
        self.progress_dialog = None

        # Create content
        self._create_content()

        # Load available Mesa drivers asynchronously (show spinner while loading)
        self._show_loading()
        GLib.idle_add(self._load_mesa_drivers_async)

    # Extended descriptions per driver id (combines old description + info)
    DRIVER_INFO = {
        "amber": {
            "icon": "emblem-default-symbolic",
            "icon_color": "warning",
            "badge": None,  # Will be set with _() at runtime
            "badge_color": "warning",
            "desc": None,  # Will be set with _() at runtime
        },
        "stable": {
            "icon": "emblem-ok-symbolic",
            "icon_color": "success",
            "badge": None,
            "badge_color": "success",
            "desc": None,
        },
        "tkg-stable": {
            "icon": "system-run-symbolic",
            "icon_color": "accent",
            "badge": None,
            "badge_color": "accent",
            "desc": None,
        },
        "tkg-git": {
            "icon": "system-software-update-symbolic",
            "icon_color": "warning",
            "badge": None,
            "badge_color": "warning",
            "desc": None,
        },
    }

    def _init_driver_info(self):
        """Initialize translatable driver info strings."""
        info = self.DRIVER_INFO
        info["amber"]["badge"] = _("Legacy")
        info["amber"]["desc"] = _(
            "Classic OpenGL implementation for very old hardware. "
            "Only use if your GPU does not support modern Mesa drivers."
        )
        info["stable"]["badge"] = _("Recommended")
        info["stable"]["desc"] = _(
            "Official stable Mesa release. Best balance of performance, "
            "compatibility and stability. Includes Vulkan drivers for "
            "AMD, Intel and software rendering."
        )
        info["tkg-stable"]["badge"] = _("Performance")
        info["tkg-stable"]["desc"] = _(
            "Custom build with performance patches. May provide better FPS "
            "in games, but can cause issues with system updates. Use with caution."
        )
        info["tkg-git"]["badge"] = "DEV"
        info["tkg-git"]["desc"] = _(
            "Bleeding-edge development version. Contains the newest features "
            "but is unstable and may break with updates. Not recommended for daily use."
        )

    def _create_content(self):
        """Create the UI elements for Mesa drivers management."""
        self._init_driver_info()

        # Create main container as scrolled window
        main_scrolled = Gtk.ScrolledWindow()
        main_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main_scrolled.set_min_content_height(550)
        main_scrolled.set_vexpand(True)

        # Main content box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.set_margin_top(24)
        main_box.set_margin_bottom(24)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_tightening_threshold(600)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # The 2x2 grid of driver cards
        self.driver_grid = Gtk.Grid()
        self.driver_grid.set_column_spacing(12)
        self.driver_grid.set_row_spacing(12)
        self.driver_grid.set_column_homogeneous(True)

        content_box.append(self.driver_grid)

        clamp.set_child(content_box)
        main_box.append(clamp)
        main_scrolled.set_child(main_box)
        self.append(main_scrolled)

    def _load_mesa_drivers_async(self):
        """Start loading Mesa drivers in a background thread."""
        import threading

        thread = threading.Thread(target=self._load_mesa_drivers_thread, daemon=True)
        thread.start()
        return False

    def _load_mesa_drivers_thread(self):
        """Load Mesa drivers in background thread and update UI via idle_add."""
        try:
            drivers = self.mesa_manager.get_available_drivers()
            GLib.idle_add(self._update_driver_list, drivers)
        except Exception as e:
            print(f"Error loading Mesa drivers: {e}")

    def _load_mesa_drivers(self):
        """Synchronous Mesa driver loading."""
        drivers = self.mesa_manager.get_available_drivers()
        self._update_driver_list(drivers)

    def _update_driver_list(self, drivers=None):
        """Update the 2x2 driver grid."""
        self._hide_loading()
        # Clear grid
        while True:
            child = self.driver_grid.get_first_child()
            if child is None:
                break
            self.driver_grid.remove(child)

        if drivers is None:
            drivers = self.mesa_manager.get_available_drivers()

        for i, driver in enumerate(drivers):
            col = i % 2
            row = i // 2

            driver_id = driver["id"]
            is_active = driver.get("active", False)
            info = self.DRIVER_INFO.get(driver_id, {})

            # Clickable card button
            card_button = Gtk.Button()
            card_button.add_css_class("flat")
            card_button.add_css_class("driver-card")
            if is_active:
                card_button.add_css_class("driver-card-active")
            card_button.set_vexpand(False)
            card_button.set_tooltip_text(_("Select driver: {}").format(driver["name"]))
            card_button.connect("clicked", self._on_card_clicked, driver)

            # Card content
            card_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            card_inner.set_margin_start(14)
            card_inner.set_margin_end(14)
            card_inner.set_margin_top(12)
            card_inner.set_margin_bottom(12)

            # Header: icon + name + badge
            header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            header_row.set_valign(Gtk.Align.CENTER)

            icon = Gtk.Image.new_from_icon_name(
                info.get("icon", "video-display-symbolic")
            )
            icon.set_pixel_size(18)
            icon_color = info.get("icon_color", "accent")
            icon.add_css_class(icon_color)
            header_row.append(icon)

            name_label = Gtk.Label()
            name_label.set_markup(f"<b>{driver['name']}</b>")
            name_label.set_xalign(0)
            name_label.set_hexpand(True)
            header_row.append(name_label)

            # Badge
            badge_text = info.get("badge", "")
            badge_color = info.get("badge_color", "accent")
            if badge_text:
                badge = self._create_badge(badge_text, badge_color)
                header_row.append(badge)

            card_inner.append(header_row)

            # Separator
            sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            sep.set_margin_top(2)
            sep.set_margin_bottom(2)
            card_inner.append(sep)

            # Description
            desc_text = info.get("desc", driver.get("description", ""))
            desc_label = Gtk.Label(label=desc_text)
            desc_label.set_wrap(True)
            desc_label.set_xalign(0)
            desc_label.add_css_class("dim-label")
            card_inner.append(desc_label)

            # Active indicator at the bottom
            if is_active:
                active_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                active_row.set_margin_top(4)
                active_row.set_halign(Gtk.Align.START)

                check_icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
                check_icon.set_pixel_size(14)
                check_icon.add_css_class("success")
                active_row.append(check_icon)

                active_label = Gtk.Label(label=_("Active"))
                active_label.add_css_class("success")
                active_label.set_markup(f"<small><b>{_('Active')}</b></small>")
                active_row.append(active_label)

                card_inner.append(active_row)

            card_button.set_child(card_inner)
            self.driver_grid.attach(card_button, col, row, 1, 1)

    def _on_card_clicked(self, button, driver):
        """Handle clicking on a driver card to switch to it."""
        is_active = driver.get("active", False)

        if is_active:
            return

        dialog = Adw.MessageDialog.new(self.get_root())
        dialog.set_heading(_("Change Video Driver"))
        dialog.set_body(
            _(
                "Do you want to change to the <b>{}</b> driver?\n\n"
                "This will modify your system's video drivers.\n"
                "<b>A system reboot will be required</b> for the changes to take effect."
            ).format(driver["name"])
        )
        dialog.set_body_use_markup(True)

        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("apply", _("Apply"))
        dialog.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        dialog.connect("response", self._on_confirm_dialog_response, driver["id"])
        dialog.present()

    def _on_refresh_clicked(self, button):
        """Callback for refresh button click."""
        self._load_mesa_drivers()

    def _on_confirm_dialog_response(self, dialog, response, selected_driver):
        """Handle the confirmation dialog response."""
        if response != "apply":
            return

        if not self.progress_dialog:
            print("Warning: Progress dialog not available")
            return

        # Show progress dialog with cancel callback
        self.progress_dialog.show_progress(
            _("Applying {}").format(selected_driver),
            _("Preparing to apply {} driver...").format(selected_driver),
            cancel_callback=self.mesa_manager.cancel_operation,
        )

        # Add initial terminal output
        self.progress_dialog.append_terminal_output(
            _("Applying {} driver...").format(selected_driver)
        )
        self.progress_dialog.append_terminal_output(
            _("This may take a few minutes. Please wait...")
        )

        # Start installation with output_callback
        self.mesa_manager.apply_driver(
            selected_driver,
            progress_callback=self._on_progress_update,
            output_callback=self._on_terminal_output,
            complete_callback=lambda success: GLib.idle_add(
                self._application_complete, success
            ),
        )

    def _on_progress_update(self, fraction, text=None):
        """Update the progress bar via the modal dialog."""
        if self.progress_dialog:
            self.progress_dialog.update_progress(fraction, text)

    def _on_terminal_output(self, text):
        """Add text to the terminal view via the modal dialog."""
        if self.progress_dialog and text:
            self.progress_dialog.append_terminal_output(text)

    def _application_complete(self, success):
        """Handle application completion."""
        if self.progress_dialog:
            if success:
                self.progress_dialog.show_success(
                    _(
                        "The video driver was changed successfully!\n\n"
                        "⚠️ You must reboot your system for the new driver to become active."
                    )
                )
            else:
                self.progress_dialog.show_error(
                    _(
                        "The driver change failed.\nPlease check the terminal output for details."
                    )
                )

        # Refresh driver list
        self._show_loading()
        self._load_mesa_drivers_async()
        return False
