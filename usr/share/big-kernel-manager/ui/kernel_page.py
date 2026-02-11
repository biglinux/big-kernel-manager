#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Big Kernel Manager - Kernel Management Page

This module defines the UI for kernel management, allowing users
to install and manage different kernel versions.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

from core.kernel_manager import KernelManager
from ui.base_page import BasePage
from utils.i18n import _


class KernelPage(BasePage):
    """Page for kernel management."""

    def __init__(self):
        """Initialize the kernel management page."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        
        # Initialize kernel manager
        self.kernel_manager = KernelManager()
        
        # Track the running kernel package name
        self._running_kernel_package = ""
        
        # Progress dialog reference (set by window via BasePage.set_progress_dialog)
        self.progress_dialog = None
        
        # Create content
        self._create_content()
        
        # Load available kernels asynchronously (show spinner while loading)
        self._show_loading()
        GLib.idle_add(self._load_kernels_async)
    
    def _create_content(self):
        """Create the UI elements for kernel management with fixed layout."""
        # Create main container as scrolled window to maintain fixed window size
        main_scrolled = Gtk.ScrolledWindow()
        main_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main_scrolled.set_min_content_height(580)
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
        
        # Add header with Adw.PreferencesGroup for better GNOME style
        kernel_group = Adw.PreferencesGroup()
        
        # Create scrolled window for kernels that will resize itself
        self.kernels_scrolled = Gtk.ScrolledWindow()
        self.kernels_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.kernels_scrolled.set_vexpand(True)
        self.kernels_scrolled.set_min_content_height(450)
        
        # Create listbox for kernels with GNOME styling
        self.kernel_listbox = Gtk.ListBox()
        self.kernel_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.kernel_listbox.add_css_class("boxed-list")
        self.kernel_listbox.add_css_class("card")
        
        self.kernels_scrolled.set_child(self.kernel_listbox)
        kernel_group.add(self.kernels_scrolled)
        
        # Add the group to the content box
        content_box.append(kernel_group)
        
        # Set the clamp's child to the content box
        clamp.set_child(content_box)
        main_box.append(clamp)
        
        # Set the main box as the child of the scrolled window
        main_scrolled.set_child(main_box)
        
        # Add the main scrolled window to this widget
        self.append(main_scrolled)
    
    def _load_kernels_async(self):
        """Start loading kernels in a background thread."""
        import threading
        thread = threading.Thread(target=self._load_kernels_thread, daemon=True)
        thread.start()
        return False
    
    def _load_kernels_thread(self):
        """Load kernels in background thread and update UI via idle_add."""
        try:
            kernels = self.kernel_manager.get_available_kernels()
            running_pkg = self.kernel_manager.get_running_kernel_package()
            GLib.idle_add(self._update_kernel_list, kernels, running_pkg)
        except Exception as e:
            print(f"Error loading kernels: {e}")
    
    def _update_kernel_list(self, kernels, running_kernel_package=""):
        """Update the kernel list in the main thread."""
        self._hide_loading()
        self._running_kernel_package = running_kernel_package
        
        # Clear existing items
        while True:
            row = self.kernel_listbox.get_first_child()
            if row is None:
                break
            self.kernel_listbox.remove(row)
        
        # Sort by version (newest first) using version string
        def version_sort_key(k):
            import re
            version = k.get("version", "0")
            numbers = re.findall(r'\d+', version)
            return tuple(int(n) for n in numbers[:4]) if numbers else (0,)
        
        installed_kernels = sorted(
            [k for k in kernels if k.get("installed", False)],
            key=version_sort_key,
            reverse=True
        )
        available_kernels = sorted(
            [k for k in kernels if not k.get("installed", False)],
            key=version_sort_key,
            reverse=True
        )
        
        # Add section header for installed kernels if any
        if installed_kernels:
            header = self._create_section_header(_("Installed Kernels"), len(installed_kernels))
            self.kernel_listbox.append(header)
            
            for kernel in installed_kernels:
                row = self._create_kernel_row(kernel)
                self.kernel_listbox.append(row)
        
        # Add section header for available kernels
        if available_kernels:
            header = self._create_section_header(_("Available Kernels"), len(available_kernels))
            self.kernel_listbox.append(header)
            
            for kernel in available_kernels:
                row = self._create_kernel_row(kernel)
                self.kernel_listbox.append(row)
        
        return False
    
    def _load_kernels(self):
        """Synchronous kernel loading."""
        kernels = self.kernel_manager.get_available_kernels()
        running_pkg = self.kernel_manager.get_running_kernel_package()
        self._update_kernel_list(kernels, running_pkg)
    
    def _create_section_header(self, title, count):
        """Create a section header row."""
        row = Gtk.ListBoxRow()
        row.set_selectable(False)
        row.set_activatable(False)
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(16)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)
        
        label = Gtk.Label()
        label.set_markup(f"<b>{title}</b>")
        label.set_halign(Gtk.Align.START)
        label.add_css_class("heading")
        box.append(label)
        
        count_label = Gtk.Label.new(f"({count})")
        count_label.add_css_class("dim-label")
        box.append(count_label)
        
        row.set_child(box)
        return row
    
    def _create_kernel_row(self, kernel):
        """
        Create a row for a kernel in the list.
        
        Args:
            kernel: Dictionary with kernel information.
            
        Returns:
            Gtk.ListBoxRow: The created row.
        """
        is_installed = kernel.get("installed", False)
        is_running = (kernel["name"] == self._running_kernel_package)
        
        # Create row with kernel name + badges in title
        row = Adw.ActionRow()
        row.set_title(kernel["name"])
        row.set_subtitle(_("Version: {}").format(kernel['version']))
        
        # Prefix: Icon indicating installed status or kernel type
        if is_running:
            icon = Gtk.Image.new_from_icon_name("system-run-symbolic")
            icon.add_css_class("accent")
        elif is_installed:
            icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
            icon.add_css_class("success")
        elif kernel.get("xanmod", False):
            icon = Gtk.Image.new_from_icon_name("application-x-executable-symbolic")
        elif kernel.get("lts", False):
            icon = Gtk.Image.new_from_icon_name("emblem-default-symbolic")
        else:
            icon = Gtk.Image.new_from_icon_name("system-run-symbolic")
        
        row.add_prefix(icon)
        
        # Suffix container with fixed-width sections for alignment
        suffix_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        suffix_box.set_halign(Gtk.Align.END)
        
        # Tags section (fixed width for alignment)
        tags_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        tags_box.set_size_request(160, -1)
        tags_box.set_halign(Gtk.Align.END)
        
        # Running badge
        if is_running:
            running_badge = self._create_badge(_("In Use"), "running")
            tags_box.append(running_badge)
        
        # LTS badge
        if kernel.get("lts", False) or "-lts" in kernel.get("name", ""):
            lts_badge = self._create_badge("LTS", "success")
            tags_box.append(lts_badge)
        
        # RT badge  
        if kernel.get("rt", False) or "-rt" in kernel.get("name", ""):
            rt_badge = self._create_badge("RT", "warning")
            tags_box.append(rt_badge)
        
        # Optimized badge
        if kernel.get("optimized", False):
            opt_badge = self._create_badge(f"v{kernel.get('opt_level', '')}", "accent")
            tags_box.append(opt_badge)
        
        suffix_box.append(tags_box)
        
        # Action button (fixed width for alignment)
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.set_size_request(80, -1)
        button_box.set_halign(Gtk.Align.END)
        button_box.set_valign(Gtk.Align.CENTER)
        
        if is_installed:
            remove_button = Gtk.Button.new_with_label(_("Remove"))
            remove_button.add_css_class("destructive-action")
            remove_button.add_css_class("pill")
            remove_button.set_size_request(70, -1)
            
            # Disable remove button for the running kernel (safety protection)
            if is_running:
                remove_button.set_sensitive(False)
                remove_button.set_tooltip_text(_("Cannot remove the currently running kernel"))
            
            remove_button.connect("clicked", self._on_remove_clicked, kernel)
            button_box.append(remove_button)
        else:
            install_button = Gtk.Button.new_with_label(_("Install"))
            install_button.add_css_class("suggested-action")
            install_button.add_css_class("pill")
            install_button.set_size_request(70, -1)
            install_button.connect("clicked", self._on_install_clicked, kernel)
            button_box.append(install_button)
        
        suffix_box.append(button_box)
        row.add_suffix(suffix_box)
        
        return row
    
    def _on_refresh_clicked(self, button):
        """Callback for refresh button click."""
        self._load_kernels()
    
    def _on_install_clicked(self, button, kernel):
        """Callback for install button click."""
        dialog = Adw.MessageDialog.new(self.get_root())
        dialog.set_heading(_("Install Kernel"))
        dialog.set_body_use_markup(True)
        dialog.set_body(
            _("Are you sure you want to install the <b>{}</b> kernel?\n\n"
              "This will install the kernel and its modules.").format(kernel['name'])
        )
        
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("install", _("Install"))
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        dialog.connect("response", self._on_install_dialog_response, kernel, button)
        dialog.present()

    def _on_install_dialog_response(self, dialog, response, kernel, button):
        """Handle install dialog response."""
        if response != "install":
            return
        
        if not self.progress_dialog:
            print("Warning: Progress dialog not available")
            return
        
        # Show progress dialog with cancel callback
        self.progress_dialog.show_progress(
            _("Installing {}").format(kernel['name']),
            _("Preparing to install {} kernel...").format(kernel['name']),
            cancel_callback=self.kernel_manager.cancel_operation
        )
        
        # Disable button
        button.set_sensitive(False)
        
        # Add initial terminal output
        self.progress_dialog.append_terminal_output(_("Starting installation of {} kernel...").format(kernel['name']))
        self.progress_dialog.append_terminal_output(_("This may take a few minutes. Please wait..."))
        
        # Start installation
        self.kernel_manager.install_kernel(
            kernel,
            progress_callback=self._on_progress_update,
            output_callback=self._on_terminal_output,
            complete_callback=lambda success: GLib.idle_add(
                self._installation_complete, button, success
            )
        )
    
    def _on_remove_clicked(self, button, kernel):
        """
        Callback for remove button click.
        
        Args:
            button: The button that was clicked.
            kernel: The kernel to remove.
        """
        # Safety: prevent removal of running kernel
        if kernel["name"] == self._running_kernel_package:
            self._show_completion_dialog(
                _("Cannot Remove Running Kernel"),
                _("The kernel you are trying to remove is currently in use.\n"
                  "Please boot into a different kernel first."),
                status="warning"
            )
            return
        
        dialog = Adw.MessageDialog.new(self.get_root())
        dialog.set_heading(_("Remove Kernel"))
        dialog.set_body_use_markup(True)
        dialog.set_body(
            _("Are you sure you want to remove the <b>{}</b> kernel?\n\n"
              "This will remove the kernel and its modules.").format(kernel['name'])
        )
        
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("remove", _("Remove"))
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        dialog.connect("response", self._on_remove_dialog_response, kernel, button)
        dialog.present()

    def _on_remove_dialog_response(self, dialog, response, kernel, button):
        """Handle the remove confirmation dialog response."""
        if response != "remove":
            return
        
        if not self.progress_dialog:
            print("Warning: Progress dialog not available")
            return
        
        # Show progress dialog with cancel callback
        self.progress_dialog.show_progress(
            _("Removing {}").format(kernel['name']),
            _("Preparing to remove {} kernel...").format(kernel['name']),
            cancel_callback=self.kernel_manager.cancel_operation
        )
        
        # Disable button during removal
        button.set_sensitive(False)
        
        # Add initial terminal output
        self.progress_dialog.append_terminal_output(_("Starting removal of {} kernel...").format(kernel['name']))
        self.progress_dialog.append_terminal_output(_("This may take a few minutes. Please wait..."))
        
        # Start removal in a separate thread to avoid UI freezing
        self.kernel_manager.remove_kernel(
            kernel,
            progress_callback=self._on_progress_update,
            output_callback=self._on_terminal_output,
            complete_callback=lambda success: GLib.idle_add(
                self._removal_complete, button, success
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
    
    def _installation_complete(self, button, success):
        """Handle installation completion."""
        button.set_sensitive(True)
        
        if self.progress_dialog:
            if success:
                self.progress_dialog.show_success(
                    _("The kernel was installed successfully.\nYou may need to reboot to use the new kernel.")
                )
            else:
                self.progress_dialog.show_error(
                    _("The kernel installation failed.\nPlease check the terminal output for details.")
                )
        
        # Refresh kernel list
        self._load_kernels()
        return False

    def _removal_complete(self, button, success):
        """Handle removal completion."""
        button.set_sensitive(True)
        
        if self.progress_dialog:
            if success:
                self.progress_dialog.show_success(
                    _("The kernel was removed successfully.")
                )
            else:
                self.progress_dialog.show_error(
                    _("The kernel removal failed.\nPlease check the terminal output for details.")
                )
        
        # Refresh kernel list
        self._load_kernels()
        return False