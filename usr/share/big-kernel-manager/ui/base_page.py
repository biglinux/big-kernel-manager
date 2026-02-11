#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Big Kernel Manager - Base Page

This module provides a base class for UI pages (Kernel, Mesa)
containing shared functionality for progress handling, dialogs,
and toast notifications.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

from utils.i18n import _


class BasePage(Gtk.Box):
    """Base class for management pages with shared UI functionality."""
    
    def __init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=12):
        """Initialize the base page."""
        super().__init__(orientation=orientation, spacing=spacing)
        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.set_margin_start(24)
        self.set_margin_end(24)
        
        # Progress tracking
        self._progress_bar = None
        self._progress_label = None
        self._progress_container = None
        self._terminal_view = None
        self._terminal_buffer = None
        
        # Loading spinner
        self._loading_box = None
    
    def _show_loading(self):
        """Show a centered loading spinner overlay."""
        if self._loading_box is not None:
            return
        
        self._loading_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._loading_box.set_valign(Gtk.Align.CENTER)
        self._loading_box.set_halign(Gtk.Align.CENTER)
        self._loading_box.set_vexpand(True)
        
        spinner = Gtk.Spinner()
        spinner.set_size_request(32, 32)
        spinner.start()
        self._loading_box.append(spinner)
        
        label = Gtk.Label(label=_("Loading..."))
        label.add_css_class("dim-label")
        self._loading_box.append(label)
        
        self.append(self._loading_box)
    
    def _hide_loading(self):
        """Remove the loading spinner."""
        if self._loading_box is not None:
            self.remove(self._loading_box)
            self._loading_box = None
    
    def _create_progress_container(self) -> Gtk.Box:
        """
        Create a progress container with progress bar and label.
        
        Returns:
            Gtk.Box containing progress widgets
        """
        self._progress_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._progress_container.set_visible(False)
        
        # Progress bar
        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_show_text(True)
        self._progress_container.append(self._progress_bar)
        
        # Progress label
        self._progress_label = Gtk.Label()
        self._progress_label.add_css_class("dim-label")
        self._progress_container.append(self._progress_label)
        
        return self._progress_container
    
    def _create_terminal_expander(self) -> Gtk.Expander:
        """
        Create a terminal expander for showing command output.
        
        Returns:
            Gtk.Expander containing terminal view
        """
        expander = Gtk.Expander(label=_("Terminal Output"))
        expander.set_expanded(False)
        
        # Scrolled window for terminal
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(150)
        scrolled.set_max_content_height(300)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        # Text view for terminal output
        self._terminal_view = Gtk.TextView()
        self._terminal_view.set_editable(False)
        self._terminal_view.set_cursor_visible(False)
        self._terminal_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._terminal_view.add_css_class("terminal")
        self._terminal_buffer = self._terminal_view.get_buffer()
        
        scrolled.set_child(self._terminal_view)
        expander.set_child(scrolled)
        
        return expander
    
    def _show_progress_container(self) -> None:
        """Show the progress container."""
        if self._progress_container:
            self._progress_container.set_visible(True)
    
    def _hide_progress_container(self) -> None:
        """Hide the progress container after a short delay."""
        GLib.timeout_add(500, self._actually_hide_progress_container)
    
    def _actually_hide_progress_container(self) -> bool:
        """Actually hide the progress container."""
        if self._progress_container:
            self._progress_container.set_visible(False)
        return False
    
    def _update_progress(self, fraction: float, text: str = None) -> None:
        """
        Update the progress bar.
        
        Args:
            fraction: Progress fraction (0.0 to 1.0)
            text: Optional text to display
        """
        GLib.idle_add(self._update_progress_idle, fraction, text)
    
    def _update_progress_idle(self, fraction: float, text: str) -> bool:
        """
        Update progress bar from main thread.
        
        Args:
            fraction: Progress fraction
            text: Text to display
            
        Returns:
            False to not repeat
        """
        if self._progress_bar:
            self._progress_bar.set_fraction(fraction)
            if text:
                self._progress_bar.set_text(text)
        
        if self._progress_label and text:
            self._progress_label.set_text(text)
        
        return False
    
    def _output_to_terminal(self, text: str) -> None:
        """
        Add text to the terminal view.
        
        Args:
            text: Text to add to the terminal
        """
        GLib.idle_add(self._output_to_terminal_idle, text)
    
    def _output_to_terminal_idle(self, text: str) -> bool:
        """
        Add text to the terminal view from the main thread.
        
        Args:
            text: Text to add
            
        Returns:
            False to not repeat
        """
        if self._terminal_buffer:
            end_iter = self._terminal_buffer.get_end_iter()
            self._terminal_buffer.insert(end_iter, text + "\n")
            
            # Auto-scroll to bottom
            if self._terminal_view:
                adj = self._terminal_view.get_parent().get_vadjustment()
                if adj:
                    adj.set_value(adj.get_upper())
        
        return False
    
    def _clear_terminal(self) -> None:
        """Clear the terminal buffer."""
        if self._terminal_buffer:
            self._terminal_buffer.set_text("")
    
    def _show_completion_dialog(
        self,
        title: str,
        message: str,
        status: str = "success"
    ) -> None:
        """
        Show a completion dialog.
        
        Args:
            title: Dialog title
            message: Dialog message
            status: Status type ("success", "error", "warning")
        """
        dialog = Adw.MessageDialog.new(self._get_window())
        dialog.set_heading(title)
        dialog.set_body(message)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.set_close_response("ok")
        dialog.present()
    
    def _show_confirmation_dialog(
        self,
        title: str,
        message: str,
        confirm_label: str = "Confirm",
        cancel_label: str = "Cancel",
        destructive: bool = False,
        callback: callable = None
    ) -> None:
        """
        Show a confirmation dialog.
        
        Args:
            title: Dialog title
            message: Dialog message
            confirm_label: Label for confirm button
            cancel_label: Label for cancel button
            destructive: Whether confirm action is destructive
            callback: Function to call with response
        """
        dialog = Adw.MessageDialog.new(self._get_window())
        dialog.set_heading(title)
        dialog.set_body(message)
        dialog.add_response("cancel", cancel_label)
        dialog.add_response("confirm", confirm_label)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        if destructive:
            dialog.set_response_appearance("confirm", Adw.ResponseAppearance.DESTRUCTIVE)
        else:
            dialog.set_response_appearance("confirm", Adw.ResponseAppearance.SUGGESTED)
        
        if callback:
            dialog.connect("response", callback)
        
        dialog.present()
    
    def _get_window(self) -> Gtk.Window:
        """
        Get the parent window.
        
        Returns:
            Parent Gtk.Window or None
        """
        widget = self
        while widget:
            if isinstance(widget, Gtk.Window):
                return widget
            widget = widget.get_parent()
        return None
    
    def _find_toast_overlay(self) -> Adw.ToastOverlay:
        """
        Find the nearest ToastOverlay in the widget hierarchy.
        
        Returns:
            ToastOverlay or None
        """
        widget = self.get_parent()
        while widget:
            if isinstance(widget, Adw.ToastOverlay):
                return widget
            # Check children for ToastOverlay
            if hasattr(widget, 'get_child'):
                child = widget.get_child()
                if isinstance(child, Adw.ToastOverlay):
                    return child
            widget = widget.get_parent()
        return None
    
    def _show_toast(self, message: str, timeout: int = 3) -> None:
        """
        Show a toast notification.
        
        Args:
            message: Toast message
            timeout: Timeout in seconds
        """
        overlay = self._find_toast_overlay()
        if overlay:
            toast = Adw.Toast.new(message)
            toast.set_timeout(timeout)
            overlay.add_toast(toast)
    
    def set_progress_dialog(self, dialog) -> None:
        """Set the progress dialog reference from the parent window."""
        self.progress_dialog = dialog
    
    def _create_badge(self, text: str, style_class: str) -> Gtk.Box:
        """
        Create a styled badge/chip widget.
        
        Args:
            text: Text to display in the badge
            style_class: CSS class for styling (success, warning, accent, danger)
            
        Returns:
            Gtk.Box containing the badge
        """
        badge = Gtk.Label.new(text)
        badge.add_css_class("caption")
        badge.add_css_class("badge")
        
        box = Gtk.Box()
        box.add_css_class(style_class)
        box.add_css_class("badge-box")
        box.set_valign(Gtk.Align.CENTER)
        box.append(badge)
        
        return box
