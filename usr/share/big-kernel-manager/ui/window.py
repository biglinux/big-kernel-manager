#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Big Kernel Manager - Main Window

This module defines the main application window with tabs for
kernel and Mesa driver management.
"""

import os
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gio, Adw, GLib, Gdk

from core.constants import APP_NAME, CONFIG_DIR, WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT
from core.logging_config import get_logger
from ui.kernel_page import KernelPage
from ui.mesa_page import MesaPage
from ui.progress_dialog import ProgressDialog, get_progress_dialog_css
from utils.i18n import _


class KernelManagerWindow(Adw.ApplicationWindow):
    """Main window for the Big Kernel Manager application."""

    def __init__(self, **kwargs):
        """Initialize the main window with tabs for different functionalities."""
        super().__init__(**kwargs)
        
        self._logger = get_logger("Window")
        
        # Set up window properties
        self.set_title(APP_NAME)
        self.set_default_size(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)
        self.set_resizable(False)
        
        # Initialize settings
        self._init_settings()
        
        # Build UI
        self._build_ui()
        
        # Show warning popup on startup if enabled
        GLib.idle_add(self._check_show_warning_dialog)
    
    def _init_settings(self):
        """Initialize settings for the application."""
        if hasattr(self.get_application(), "settings_manager"):
            self.settings_manager = self.get_application().settings_manager
        else:
            # Fallback - import and create SettingsManager directly
            from ui.application import SettingsManager
            self.settings_manager = SettingsManager()
    
    def _build_ui(self):
        """Build the main UI components."""
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Create overlay for backdrop effect
        self.overlay = Gtk.Overlay()
        main_box.append(self.overlay)
        
        # Create backdrop for dimming when dialog is open
        self._create_backdrop()
        
        # Create content
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.set_vexpand(True)
        
        content = Adw.ToolbarView()
        
        # Create header bar
        header = self._create_header()
        content.add_top_bar(header)
        
        # Create stack for pages
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(200)
        self.stack.set_vexpand(True)
        
        # Create pages
        self.kernel_page = KernelPage()
        self.mesa_page = MesaPage()
        
        self.stack.add_titled(self.kernel_page, "kernel", _("Kernel"))
        self.stack.add_titled(self.mesa_page, "mesa", _("Mesa Drivers"))
        
        # Create stack switcher
        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(self.stack)
        stack_switcher.set_halign(Gtk.Align.CENTER)
        header.set_title_widget(stack_switcher)
        
        # Toast overlay for notifications
        toast_overlay = Adw.ToastOverlay()
        toast_overlay.set_child(self.stack)
        content.set_content(toast_overlay)
        
        content_box.append(content)
        
        # Add to overlay
        self.overlay.set_child(content_box)
        self.overlay.add_overlay(self.backdrop)
        
        # Create and add progress dialog
        self.progress_dialog = ProgressDialog(self.overlay)
        self.overlay.add_overlay(self.progress_dialog)
        
        # Pass progress dialog reference to pages
        self.kernel_page.set_progress_dialog(self.progress_dialog)
        self.mesa_page.set_progress_dialog(self.progress_dialog)
        
        # Load progress dialog CSS
        self._load_progress_dialog_css()
        
        self.set_content(main_box)
    
    def _create_header(self) -> Adw.HeaderBar:
        """Create the header bar with controls."""
        header = Adw.HeaderBar()
        
        # Create hamburger menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_tooltip_text(_("Menu"))
        
        # Create menu model
        menu = Gio.Menu()
        menu.append(_("Refresh"), "app.refresh")
        menu.append(_("About"), "app.about")
        
        menu_button.set_menu_model(menu)
        header.pack_end(menu_button)
        
        # Create actions
        self._setup_actions()
        
        return header
    
    def _setup_actions(self):
        """Setup application actions for the menu."""
        # Refresh action
        refresh_action = Gio.SimpleAction.new("refresh", None)
        refresh_action.connect("activate", self._on_refresh_activated)
        self.get_application().add_action(refresh_action)
        
        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about_activated)
        self.get_application().add_action(about_action)
    
    def _on_refresh_activated(self, action, param):
        """Handle refresh action from menu."""
        if self.stack.get_visible_child_name() == "kernel":
            self.kernel_page._on_refresh_clicked(None)
        else:
            self.mesa_page._on_refresh_clicked(None)
    
    def _on_about_activated(self, action, param):
        """Show the About dialog."""
        from core.constants import APP_NAME, APP_VERSION, APP_AUTHOR, APP_WEBSITE, APP_ID
        
        about = Adw.AboutWindow(
            transient_for=self,
            application_name=APP_NAME,
            application_icon=APP_ID,
            version=APP_VERSION,
            developer_name=APP_AUTHOR,
            website=APP_WEBSITE,
            issue_url="https://github.com/communitybig/big-kernel-manager/issues",
            copyright="© 2024 BigLinux Team",
            license_type=Gtk.License.GPL_3_0,
            developers=[APP_AUTHOR],
            artists=[APP_AUTHOR],
        )
        about.present()
    
    def _create_backdrop(self):
        """Create the backdrop overlay for dialogs."""
        self.backdrop = Gtk.Box()
        self.backdrop.set_hexpand(True)
        self.backdrop.set_vexpand(True)
        
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"box.backdrop { background-color: rgba(0, 0, 0, 0.5); }")
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.backdrop.add_css_class("backdrop")
        self.backdrop.set_visible(False)
    
    def _load_progress_dialog_css(self):
        """Load CSS for the progress dialog."""
        css_provider = Gtk.CssProvider()
        css_data = get_progress_dialog_css()
        css_provider.load_from_data(css_data.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    

    def _check_show_warning_dialog(self) -> bool:
        """Check whether to show the warning dialog on startup."""
        try:
            show_warning = self.settings_manager.get("show-kernel-warning-on-startup", True)
            if show_warning:
                self.show_warning_dialog()
        except Exception as e:
            self._logger.warning(f"Error checking warning dialog setting: {e}")
            self.show_warning_dialog()
        return False
    
    def show_warning_dialog(self):
        """Show a detailed warning dialog about kernel and Mesa changes."""
        self.backdrop.set_visible(True)
        
        dialog = Adw.Window()
        dialog.set_default_size(700, 500)
        dialog.set_modal(True)
        dialog.set_transient_for(self)
        dialog.set_hide_on_close(True)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Header bar
        header_bar = Adw.HeaderBar()
        header_bar.set_title_widget(Gtk.Label(label=_("Kernel and Mesa Management")))
        content_box.append(header_bar)
        
        # Scrollable content
        outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer_box.set_vexpand(True)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        
        main_box = self._create_warning_content()
        scrolled.set_child(main_box)
        outer_box.append(scrolled)
        
        # Bottom controls
        bottom_area = self._create_warning_controls(dialog)
        outer_box.append(bottom_area)
        
        content_box.append(outer_box)
        dialog.set_content(content_box)
        dialog.connect("close-request", self._on_dialog_closed)
        dialog.present()
    
    def _create_warning_content(self) -> Gtk.Box:
        """Create the warning dialog content with cards and colors."""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        main_box.set_spacing(16)
        
        # Introduction
        intro_label = Gtk.Label()
        intro_label.set_wrap(True)
        intro_label.set_xalign(0.5)
        intro_label.add_css_class("dim-label")
        intro_label.set_markup(
            _("Changing your system's kernel or Mesa drivers can impact system stability. "
              "Please review the following recommendations:")
        )
        main_box.append(intro_label)
        
        # Kernel Management card
        kernel_items = [
            ("emblem-important-symbolic", "warning",
             "<b>" + _("Always keep at least one working kernel") + "</b> " + _("installed as a fallback")),
            ("emblem-ok-symbolic", "success",
             _("LTS kernels offer better stability, while newer kernels provide newer hardware support")),
            ("system-run-symbolic", "accent",
             _("Test your system thoroughly after kernel changes")),
            ("go-previous-symbolic", "",
             _("If a new kernel causes issues, you can select the previous kernel from the boot menu")),
            ("dialog-information-symbolic", "",
             _("Real-time (RT) kernels are specialized for low-latency tasks but may not be suitable for general use")),
        ]
        kernel_card = self._create_info_card(
            _("Kernel Management"), "system-software-install-symbolic", "accent",
            _("Tips"), "accent", kernel_items
        )
        main_box.append(kernel_card)
        
        # Mesa Drivers card
        mesa_items = [
            ("video-display-symbolic", "accent",
             _("Mesa drivers provide 3D graphics acceleration for AMD, Intel, and some NVIDIA GPUs")),
            ("dialog-warning-symbolic", "warning",
             _("Changing Mesa versions may affect graphics performance and application compatibility")),
            ("emblem-ok-symbolic", "success",
             _("The stable version is recommended for most users")),
            ("system-software-update-symbolic", "",
             _("Development versions may offer better performance but with less stability")),
            ("edit-undo-symbolic", "",
             _("If graphics issues occur after a change, you can switch back to the previous driver")),
        ]
        mesa_card = self._create_info_card(
            _("Mesa Driver Management"), "preferences-desktop-display-symbolic", "success",
            _("Tips"), "success", mesa_items
        )
        main_box.append(mesa_card)
        
        # Footer advice
        advice_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        advice_box.set_margin_top(4)
        
        advice_icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic")
        advice_icon.set_pixel_size(16)
        advice_icon.add_css_class("accent")
        advice_icon.set_valign(Gtk.Align.START)
        advice_box.append(advice_icon)
        
        advice_label = Gtk.Label()
        advice_label.set_markup(
            "<i>" + _("If unsure, the <b>LTS kernel</b> and <b>Stable Mesa</b> drivers "
                      "are the safest choices for most users.") + "</i>"
        )
        advice_label.set_wrap(True)
        advice_label.set_xalign(0)
        advice_label.add_css_class("dim-label")
        advice_box.append(advice_label)
        
        main_box.append(advice_box)
        
        return main_box
    
    def _create_info_card(self, title, icon_name, icon_color, badge_text, badge_color, items):
        """Create a styled card with icon header and item list."""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.add_css_class("card")
        card.set_margin_start(4)
        card.set_margin_end(4)
        
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        inner.set_margin_start(16)
        inner.set_margin_end(16)
        inner.set_margin_top(12)
        inner.set_margin_bottom(12)
        
        # Header row: icon + title + badge
        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_row.set_valign(Gtk.Align.CENTER)
        
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(20)
        icon.add_css_class(icon_color)
        header_row.append(icon)
        
        name_label = Gtk.Label()
        name_label.set_markup(f"<b>{title}</b>")
        name_label.set_xalign(0)
        name_label.set_hexpand(True)
        header_row.append(name_label)
        
        # Badge
        badge_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        badge_container.add_css_class("badge-box")
        badge_container.add_css_class(badge_color)
        badge_lbl = Gtk.Label(label=badge_text)
        badge_lbl.add_css_class("badge")
        badge_container.append(badge_lbl)
        header_row.append(badge_container)
        
        inner.append(header_row)
        
        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(4)
        sep.set_margin_bottom(4)
        inner.append(sep)
        
        # Items with icons
        for item_icon, item_color, item_text in items:
            item_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            item_row.set_margin_start(4)
            item_row.set_margin_bottom(4)
            
            item_img = Gtk.Image.new_from_icon_name(item_icon)
            item_img.set_pixel_size(14)
            if item_color:
                item_img.add_css_class(item_color)
            else:
                item_img.add_css_class("dim-label")
            item_img.set_valign(Gtk.Align.START)
            item_img.set_margin_top(3)
            item_row.append(item_img)
            
            item_label = Gtk.Label()
            item_label.set_markup(item_text)
            item_label.set_wrap(True)
            item_label.set_xalign(0)
            item_row.append(item_label)
            
            inner.append(item_row)
        
        card.append(inner)
        return card
    
    def _add_section(self, parent: Gtk.Box, title: str, items: list):
        """Add a section with title and items to the parent box (legacy fallback)."""
        title_label = Gtk.Label()
        title_label.set_markup(f"<b>{title}</b>")
        title_label.set_xalign(0)
        title_label.set_margin_top(12)
        parent.append(title_label)
        
        for item in items:
            item_label = Gtk.Label()
            item_label.set_wrap(True)
            item_label.set_xalign(0)
            item_label.set_markup(item)
            item_label.set_margin_start(12)
            item_label.set_margin_bottom(4)
            parent.append(item_label)
    
    def _create_warning_controls(self, dialog) -> Gtk.Box:
        """Create the warning dialog bottom controls."""
        bottom_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        bottom_area.set_margin_start(24)
        bottom_area.set_margin_end(24)
        bottom_area.set_margin_top(12)
        bottom_area.set_margin_bottom(12)
        
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        bottom_area.append(separator)
        
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        controls_box.set_margin_top(12)
        controls_box.set_margin_bottom(12)
        
        # Switch
        switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        switch_box.set_hexpand(True)
        
        switch_label = Gtk.Label(label=_("Show this warning on startup"))
        switch_label.set_halign(Gtk.Align.START)
        
        current_value = self.settings_manager.get("show-kernel-warning-on-startup", True)
        show_on_startup_switch = Gtk.Switch()
        show_on_startup_switch.set_active(current_value)
        show_on_startup_switch.set_valign(Gtk.Align.CENTER)
        show_on_startup_switch.connect("notify::active", self._on_warning_switch_toggled)
        
        switch_box.append(switch_label)
        switch_box.append(show_on_startup_switch)
        controls_box.append(switch_box)
        
        # Close button
        close_button = Gtk.Button(label=_("Close"))
        close_button.add_css_class("suggested-action")
        close_button.add_css_class("pill")
        close_button.set_size_request(100, -1)
        close_button.connect("clicked", lambda btn: self._close_dialog(dialog))
        close_button.set_halign(Gtk.Align.END)
        controls_box.append(close_button)
        
        bottom_area.append(controls_box)
        return bottom_area
    
    def _close_dialog(self, dialog):
        """Close the dialog and hide the backdrop."""
        self.backdrop.set_visible(False)
        dialog.close()
    
    def _on_dialog_closed(self, dialog) -> bool:
        """Handle dialog close event."""
        self.backdrop.set_visible(False)
        return False
    
    def _on_warning_switch_toggled(self, switch, param):
        """Handle toggling the switch in the warning dialog."""
        try:
            value = switch.get_active()
            success = self.settings_manager.set("show-kernel-warning-on-startup", value)
            if success:
                self._logger.debug(f"Saved warning on startup setting: {value}")
            else:
                self._logger.warning("Failed to save warning on startup setting")
        except Exception as e:
            self._logger.error(f"Error toggling warning setting: {e}")