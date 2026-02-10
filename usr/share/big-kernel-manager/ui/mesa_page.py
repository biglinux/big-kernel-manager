#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Big Kernel Manager - Mesa Drivers Management Page

This module defines the UI for Mesa drivers management, allowing users
to install and switch between different Mesa driver versions.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
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
        
        # Load available Mesa drivers (synchronous to ensure data is ready before window shows)
        self._load_mesa_drivers()
    
    def _create_content(self):
        """Create the UI elements for Mesa drivers management with fixed layout."""
        # Create main container as scrolled window to maintain fixed window size
        main_scrolled = Gtk.ScrolledWindow()
        main_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main_scrolled.set_min_content_height(550)
        main_scrolled.set_vexpand(True)
        
        # Main content box inside scrolled window
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.set_margin_top(24)
        main_box.set_margin_bottom(24)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)
        
        # Create a ClampView to constrain content width for better readability
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_tightening_threshold(600)
        
        # Inner content container
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        
        # Create a preference group for the drivers
        driver_group = Adw.PreferencesGroup()
        driver_group.set_title(_("Video Drivers"))
        driver_group.set_description(_("Select a video driver version to use"))
        
        # Add info button as a header suffix
        info_button = Gtk.Button.new_from_icon_name("help-about-symbolic")
        info_button.set_tooltip_text(_("Information about video drivers"))
        info_button.set_valign(Gtk.Align.CENTER)
        info_button.connect("clicked", self._on_help_clicked)
        driver_group.set_header_suffix(info_button)
        
        # Create a scrolled window for drivers that will resize itself
        self.drivers_scrolled = Gtk.ScrolledWindow()
        self.drivers_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.drivers_scrolled.set_vexpand(True)
        self.drivers_scrolled.set_min_content_height(300)
        
        # Create a card for the driver options inside the scrolled window
        driver_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        driver_card.add_css_class("card")
        driver_card.set_margin_top(12)
        driver_card.set_margin_start(12)
        driver_card.set_margin_end(12)
        driver_card.set_margin_bottom(12)
        driver_card.set_vexpand(False)
        
        # Create checkbuttons for the driver options
        self.driver_group = None
        self.driver_buttons = {}
        
        self.drivers_scrolled.set_child(driver_card)
        driver_group.add(self.drivers_scrolled)
        self.driver_box = driver_card
        driver_group.set_vexpand(False)
        
        # Add the driver group to the content
        content_box.append(driver_group)
        
        # Add apply button in a button box for better centering
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(16)
        button_box.set_vexpand(False)
        
        self.apply_button = Gtk.Button.new_with_label(_("Apply Changes"))
        self.apply_button.add_css_class("suggested-action")
        self.apply_button.connect("clicked", self._on_apply_clicked)
        button_box.append(self.apply_button)
        
        content_box.append(button_box)
        
        # Set the clamp's child to the content box
        clamp.set_child(content_box)
        main_box.append(clamp)
        
        # Set the main box as the child of the scrolled window
        main_scrolled.set_child(main_box)
        
        # Add the main scrolled window to this widget
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
        """Update the driver list in the main thread."""
        # Clear existing items
        while True:
            child = self.driver_box.get_first_child()
            if child is None:
                break
            self.driver_box.remove(child)
        
        # If no drivers passed, fetch them directly (for synchronous calls)
        if drivers is None:
            drivers = self.mesa_manager.get_available_drivers()
        
        # Create first radio button (will be the group leader)
        first_button = None
        
        for driver in drivers:
            row = Adw.ActionRow()
            row.set_title(driver["name"])
            
            if "description" in driver:
                row.set_subtitle(driver["description"])
            
            is_active = driver.get("active", False)
            
            # Icon based on status and type
            if is_active:
                icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
                icon.add_css_class("success")
            elif "git" in driver["id"]:
                icon = Gtk.Image.new_from_icon_name("system-software-update-symbolic")
            elif "amber" in driver["id"]:
                icon = Gtk.Image.new_from_icon_name("emblem-default-symbolic")
            else:
                icon = Gtk.Image.new_from_icon_name("video-display-symbolic")
            
            row.add_prefix(icon)
            
            # Radio button
            button = Gtk.CheckButton()
            if first_button is None:
                first_button = button
            else:
                button.set_group(first_button)
            
            self.driver_buttons[driver["id"]] = button
            
            if is_active:
                button.set_active(True)
            
            row.add_prefix(button)
            
            # Suffix container for alignment
            suffix_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            suffix_box.set_halign(Gtk.Align.END)
            
            # Type badge
            type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            type_box.set_size_request(80, -1)
            type_box.set_halign(Gtk.Align.END)
            
            if "git" in driver["id"]:
                type_badge = self._create_badge("DEV", "warning")
                type_box.append(type_badge)
            elif "stable" in driver["id"] and "tkg" not in driver["id"]:
                type_badge = self._create_badge(_("STABLE"), "success")
                type_box.append(type_badge)
            
            suffix_box.append(type_box)
            
            # Active status
            status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            status_box.set_size_request(70, -1)
            status_box.set_halign(Gtk.Align.END)
            
            if is_active:
                active_badge = self._create_badge(_("Active"), "accent")
                status_box.append(active_badge)
            
            suffix_box.append(status_box)
            row.add_suffix(suffix_box)
            
            self.driver_box.append(row)
    
    def _on_refresh_clicked(self, button):
        """Callback for refresh button click."""
        self._load_mesa_drivers()
    
    def _on_help_clicked(self, button):
        """Show information dialog about the drivers."""
        dialog = Adw.MessageDialog.new(self.get_root())
        dialog.set_heading(_("Video Drivers Information"))
        dialog.set_body(
            _("Different driver versions offer various features and performance characteristics:") + "\n\n"
            "• " + _("Amber: Stable and well-tested version") + "\n"
            "• " + _("Stable: Regular Mesa release") + "\n"
            "• " + _("Tkg-Stable: Enhanced performance build") + "\n"
            "• " + _("Tkg-git: Latest development version with cutting-edge features") + "\n\n"
            + _("Choose the one that best fits your needs and hardware.")
        )
        dialog.add_response("ok", _("OK"))
        dialog.set_default_response("ok")
        dialog.set_close_response("ok")
        dialog.present()
    
    def _on_apply_clicked(self, button):
        """Apply the selected driver changes."""
        # Find which driver is selected
        selected_driver = None
        for driver_id, btn in self.driver_buttons.items():
            if btn.get_active():
                selected_driver = driver_id
                break
        
        if selected_driver is None:
            return
        
        # Show a confirmation dialog
        dialog = Adw.MessageDialog.new(self.get_root())
        dialog.set_heading(_("Apply Driver Changes"))
        dialog.set_body(
            _("Are you sure you want to apply the selected driver changes?\n\n"
              "This will modify your system's video drivers and might require a reboot.")
        )
        
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("apply", _("Apply Changes"))
        dialog.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        dialog.connect("response", self._on_confirm_dialog_response, selected_driver)
        dialog.present()
    
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
            cancel_callback=self.mesa_manager.cancel_operation
        )
        
        # Disable button during operation
        self.apply_button.set_sensitive(False)
        
        # Add initial terminal output
        self.progress_dialog.append_terminal_output(_("Applying {} driver...").format(selected_driver))
        self.progress_dialog.append_terminal_output(_("This may take a few minutes. Please wait..."))
        
        # Start installation with output_callback
        self.mesa_manager.apply_driver(
            selected_driver,
            progress_callback=self._on_progress_update,
            output_callback=self._on_terminal_output,
            complete_callback=lambda success: GLib.idle_add(
                self._application_complete, success
            )
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
        self.apply_button.set_sensitive(True)
        
        if self.progress_dialog:
            if success:
                self.progress_dialog.show_success(
                    _("The video driver was changed successfully.\nYou may need to reboot for changes to take effect.")
                )
            else:
                self.progress_dialog.show_error(
                    _("The driver change failed.\nPlease check the terminal output for details.")
                )
        
        # Refresh driver list
        self._load_mesa_drivers()
        return False