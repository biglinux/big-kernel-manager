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
        driver_group.set_description(_("Click on a driver version to switch"))
        
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
        
        self.drivers_scrolled.set_child(driver_card)
        driver_group.add(self.drivers_scrolled)
        self.driver_box = driver_card
        driver_group.set_vexpand(False)
        
        # Add the driver group to the content
        content_box.append(driver_group)
        
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
            
            # Make row clickable - activatable for direct switching
            row.set_activatable(True)
            
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
            
            # Connect row activation to driver switching
            row.connect("activated", self._on_driver_row_activated, driver)
            
            self.driver_box.append(row)
    
    def _on_driver_row_activated(self, row, driver):
        """Handle clicking on a driver row to switch to it."""
        is_active = driver.get("active", False)
        
        if is_active:
            # Already active, show toast or do nothing
            return
        
        # Show confirmation dialog directly
        dialog = Adw.MessageDialog.new(self.get_root())
        dialog.set_heading(_("Switch Video Driver"))
        dialog.set_body(
            _("Do you want to switch to the <b>{}</b> driver?\n\n"
              "This will modify your system's video drivers and might require a reboot.").format(driver['name'])
        )
        dialog.set_body_use_markup(True)
        
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("apply", _("Switch"))
        dialog.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        dialog.connect("response", self._on_confirm_dialog_response, driver["id"])
        dialog.present()
    
    def _on_refresh_clicked(self, button):
        """Callback for refresh button click."""
        self._load_mesa_drivers()
    
    def _on_help_clicked(self, button):
        """Show information dialog about the drivers with cards and colors."""
        dialog = Adw.Window()
        dialog.set_default_size(600, 550)
        dialog.set_modal(True)
        dialog.set_transient_for(self.get_root())
        dialog.set_hide_on_close(True)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Header bar
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(
            title=_("Video Drivers Information")
        ))
        content_box.append(header)
        
        # Scrollable content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(24)
        
        # Subtitle
        subtitle = Gtk.Label()
        subtitle.set_markup(
            _("Different driver versions offer various features and performance characteristics:")
        )
        subtitle.set_wrap(True)
        subtitle.set_xalign(0.5)
        subtitle.add_css_class("dim-label")
        subtitle.set_margin_bottom(8)
        main_box.append(subtitle)
        
        # Driver cards data
        drivers_info = [
            {
                "name": "Amber",
                "icon": "emblem-default-symbolic",
                "icon_color": "accent",
                "badge": _("Legacy"),
                "badge_color": "warning",
                "desc": _("Classic OpenGL implementation. Ideal for older hardware "
                         "or applications that require the legacy Mesa pipeline.")
            },
            {
                "name": "Stable",
                "icon": "emblem-ok-symbolic",
                "icon_color": "success",
                "badge": _("Recommended"),
                "badge_color": "success",
                "desc": _("Official stable Mesa release from Manjaro repositories. "
                         "Best balance of performance, compatibility and stability. "
                         "Includes Vulkan drivers for AMD, Intel and software rendering.")
            },
            {
                "name": "TKG-Stable",
                "icon": "system-run-symbolic",
                "icon_color": "accent",
                "badge": _("Performance"),
                "badge_color": "accent",
                "desc": _("Custom build of stable Mesa with performance optimizations. "
                         "May provide better FPS in games while maintaining stability.")
            },
            {
                "name": "TKG-Git",
                "icon": "system-software-update-symbolic",
                "icon_color": "warning",
                "badge": "DEV",
                "badge_color": "warning",
                "desc": _("Bleeding-edge development version built from the latest source code. "
                         "Contains the newest features and driver improvements, "
                         "but may introduce instability or regressions.")
            },
        ]
        
        for info in drivers_info:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            card.add_css_class("card")
            card.set_margin_start(4)
            card.set_margin_end(4)
            
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            inner.set_margin_start(16)
            inner.set_margin_end(16)
            inner.set_margin_top(12)
            inner.set_margin_bottom(12)
            
            # Header row: icon + name + badge
            header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            header_row.set_valign(Gtk.Align.CENTER)
            
            icon = Gtk.Image.new_from_icon_name(info["icon"])
            icon.set_pixel_size(20)
            icon.add_css_class(info["icon_color"])
            header_row.append(icon)
            
            name_label = Gtk.Label()
            name_label.set_markup(f"<b>{info['name']}</b>")
            name_label.set_xalign(0)
            name_label.set_hexpand(True)
            header_row.append(name_label)
            
            # Badge
            badge_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            badge_box.add_css_class("badge-box")
            badge_box.add_css_class(info["badge_color"])
            badge_label = Gtk.Label(label=info["badge"])
            badge_label.add_css_class("badge")
            badge_box.append(badge_label)
            header_row.append(badge_box)
            
            inner.append(header_row)
            
            # Description
            desc_label = Gtk.Label(label=info["desc"])
            desc_label.set_wrap(True)
            desc_label.set_xalign(0)
            desc_label.add_css_class("dim-label")
            inner.append(desc_label)
            
            card.append(inner)
            main_box.append(card)
        
        # Footer advice
        advice_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        advice_box.set_margin_top(8)
        
        advice_icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic")
        advice_icon.set_pixel_size(16)
        advice_icon.add_css_class("accent")
        advice_icon.set_valign(Gtk.Align.START)
        advice_box.append(advice_icon)
        
        advice_label = Gtk.Label()
        advice_label.set_markup(
            "<i>" + _("If unsure, the <b>Stable</b> driver is the safest choice for most users.") + "</i>"
        )
        advice_label.set_wrap(True)
        advice_label.set_xalign(0)
        advice_label.add_css_class("dim-label")
        advice_box.append(advice_label)
        
        main_box.append(advice_box)
        
        scrolled.set_child(main_box)
        content_box.append(scrolled)
        
        # Close button
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(8)
        button_box.set_margin_bottom(16)
        
        close_btn = Gtk.Button(label=_("Close"))
        close_btn.add_css_class("suggested-action")
        close_btn.add_css_class("pill")
        close_btn.set_size_request(120, -1)
        close_btn.connect("clicked", lambda btn: dialog.close())
        button_box.append(close_btn)
        
        content_box.append(button_box)
        
        dialog.set_content(content_box)
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