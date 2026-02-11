#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Big Kernel Manager - Progress Dialog Component

Modern modal progress dialog for installation/removal operations.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk

from utils.i18n import _


class ProgressDialog(Gtk.Box):
    """
    Modal progress dialog that overlays the main content.
    Shows operation progress with terminal output and success/failure status.
    """

    def __init__(self, parent_overlay):
        """
        Initialize the progress dialog.
        
        Args:
            parent_overlay: The Gtk.Overlay to add this dialog to.
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.parent_overlay = parent_overlay
        
        # State
        self._is_complete = False
        self._success = False
        
        # Build the UI
        self._build_ui()
        
        # Initially hidden
        self.set_visible(False)
    
    def _build_ui(self):
        """Build the dialog UI."""
        # Background overlay (darkens the content behind)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_halign(Gtk.Align.FILL)
        self.set_valign(Gtk.Align.FILL)
        
        # Add backdrop styling
        self.add_css_class("progress-dialog-backdrop")
        
        # Center container
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        center_box.set_halign(Gtk.Align.CENTER)
        center_box.set_valign(Gtk.Align.CENTER)
        center_box.set_hexpand(True)
        center_box.set_vexpand(True)
        
        # Dialog card
        self.dialog_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.dialog_card.add_css_class("card")
        self.dialog_card.add_css_class("progress-dialog-card")
        self.dialog_card.set_size_request(650, -1)
        self.dialog_card.set_margin_start(24)
        self.dialog_card.set_margin_end(24)
        self.dialog_card.set_margin_top(24)
        self.dialog_card.set_margin_bottom(24)
        
        # Content inside card
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        
        # Header with icon and title
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header_box.set_halign(Gtk.Align.CENTER)
        
        # Status icon (spinner initially, then success/error icon)
        self.status_icon_stack = Gtk.Stack()
        self.status_icon_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.status_icon_stack.set_transition_duration(300)
        
        # Spinner for in-progress
        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(32, 32)
        self.status_icon_stack.add_named(self.spinner, "spinner")
        
        # Success icon
        success_icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
        success_icon.set_pixel_size(32)
        success_icon.add_css_class("success-icon")
        self.status_icon_stack.add_named(success_icon, "success")
        
        # Error icon
        error_icon = Gtk.Image.new_from_icon_name("dialog-error-symbolic")
        error_icon.set_pixel_size(32)
        error_icon.add_css_class("error-icon")
        self.status_icon_stack.add_named(error_icon, "error")
        
        header_box.append(self.status_icon_stack)
        
        # Title
        self.title_label = Gtk.Label()
        self.title_label.add_css_class("title-2")
        self.title_label.set_halign(Gtk.Align.START)
        header_box.append(self.title_label)
        
        content_box.append(header_box)
        
        # Status message
        self.status_label = Gtk.Label()
        self.status_label.add_css_class("dim-label")
        self.status_label.set_halign(Gtk.Align.CENTER)
        self.status_label.set_wrap(True)
        self.status_label.set_max_width_chars(50)
        content_box.append(self.status_label)
        
        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.add_css_class("osd")
        content_box.append(self.progress_bar)
        
        # Terminal expander
        terminal_expander = Gtk.Expander()
        terminal_expander.set_label(_("Show Terminal Output"))
        # Note: caption class removed to prevent small font size
        self.terminal_expander = terminal_expander
        
        # Terminal scrolled window
        terminal_scroll = Gtk.ScrolledWindow()
        terminal_scroll.set_min_content_height(150)
        terminal_scroll.set_max_content_height(200)
        terminal_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        terminal_scroll.set_vexpand(False)
        
        # Terminal view
        self.terminal_view = Gtk.TextView()
        self.terminal_view.set_editable(False)
        self.terminal_view.set_cursor_visible(False)
        self.terminal_view.set_monospace(True)
        self.terminal_view.add_css_class("terminal")
        self.terminal_view.add_css_class("monospace")
        self.terminal_buffer = self.terminal_view.get_buffer()
        
        terminal_scroll.set_child(self.terminal_view)
        terminal_expander.set_child(terminal_scroll)
        content_box.append(terminal_expander)
        
        # Button box for cancel and close buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(8)
        
        # Cancel button (shown during operation)
        self.cancel_button = Gtk.Button(label=_("Cancel"))
        self.cancel_button.add_css_class("destructive-action")
        self.cancel_button.add_css_class("pill")
        self.cancel_button.connect("clicked", self._on_cancel_clicked)
        self.cancel_button.set_visible(True)
        button_box.append(self.cancel_button)
        
        # Close button (shown on completion)
        self.close_button = Gtk.Button(label=_("Close"))
        self.close_button.add_css_class("suggested-action")
        self.close_button.add_css_class("pill")
        self.close_button.connect("clicked", self._on_close_clicked)
        self.close_button.set_visible(False)
        button_box.append(self.close_button)
        
        content_box.append(button_box)
        
        self.dialog_card.append(content_box)
        center_box.append(self.dialog_card)
        self.append(center_box)
        
        # Cancel callback storage
        self._cancel_callback = None
    
    def show_progress(self, title: str, initial_message: str = "", cancel_callback=None):
        """
        Show the progress dialog.
        
        Args:
            title: Title of the operation (e.g., "Installing linux619")
            initial_message: Initial status message
            cancel_callback: Optional callback to call when cancel button is clicked
        """
        self._is_complete = False
        self._success = False
        self._cancel_callback = cancel_callback
        
        # Reset UI
        self.title_label.set_text(title)
        self.status_label.set_text(initial_message or _("Please wait..."))
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("0%")
        self.terminal_buffer.set_text("", 0)
        self.terminal_expander.set_expanded(False)
        
        # Show/hide buttons appropriately
        self.cancel_button.set_visible(True)
        self.close_button.set_visible(False)
        
        # Show spinner
        self.status_icon_stack.set_visible_child_name("spinner")
        self.spinner.start()
        
        # Show dialog
        self.set_visible(True)
    
    def update_progress(self, fraction: float, text: str = None):
        """
        Update the progress bar.
        
        Args:
            fraction: Progress fraction (0.0 to 1.0)
            text: Optional status text
        """
        GLib.idle_add(self._update_progress_idle, fraction, text)
    
    def _update_progress_idle(self, fraction, text):
        """Update progress from main thread."""
        fraction = max(0.0, min(1.0, fraction))
        self.progress_bar.set_fraction(fraction)
        
        percentage = int(fraction * 100)
        if text:
            self.progress_bar.set_text(f"{text}")
            self.status_label.set_text(text)
        else:
            self.progress_bar.set_text(f"{percentage}%")
        
        return False
    
    def append_terminal_output(self, text: str):
        """
        Append text to the terminal output.
        
        Args:
            text: Text to append
        """
        if not text:
            return
            
        if not text.endswith('\n'):
            text += '\n'
        
        GLib.idle_add(self._append_terminal_idle, text)
    
    def _append_terminal_idle(self, text):
        """Append terminal text from main thread."""
        try:
            end_iter = self.terminal_buffer.get_end_iter()
            self.terminal_buffer.insert(end_iter, text)
            
            # Auto-scroll to bottom
            vadj = self.terminal_view.get_vadjustment()
            if vadj:
                vadj.set_value(vadj.get_upper() - vadj.get_page_size())
        except Exception as e:
            print(f"Error appending terminal output: {e}")
        
        return False
    
    def show_success(self, message: str = None):
        """
        Show success state.
        
        Args:
            message: Success message to display
        """
        if message is None:
            message = _("Operation completed successfully!")
        GLib.idle_add(self._show_result_idle, True, message)
    
    def show_error(self, message: str = None):
        """
        Show error state.
        
        Args:
            message: Error message to display
        """
        if message is None:
            message = _("Operation failed. Check terminal output for details.")
        GLib.idle_add(self._show_result_idle, False, message)
    
    def _show_result_idle(self, success: bool, message: str):
        """Show result from main thread."""
        self._is_complete = True
        self._success = success
        
        # Stop spinner
        self.spinner.stop()
        
        # Show appropriate icon
        if success:
            self.status_icon_stack.set_visible_child_name("success")
            self.progress_bar.set_fraction(1.0)
            self.progress_bar.set_text(_("Completed!"))
        else:
            self.status_icon_stack.set_visible_child_name("error")
            self.progress_bar.set_text(_("Failed"))
        
        # Update message
        self.status_label.set_text(message)
        
        # Hide cancel, show close button
        self.cancel_button.set_visible(False)
        self.close_button.set_visible(True)
        
        return False
    
    def _on_cancel_clicked(self, button):
        """Handle cancel button click."""
        # Call the cancel callback if set
        if self._cancel_callback:
            try:
                self._cancel_callback()
            except Exception as e:
                print(f"Error in cancel callback: {e}")
        
        # Show cancelled state
        self.spinner.stop()
        self._is_complete = True
        self._success = False
        self.status_icon_stack.set_visible_child_name("error")
        self.status_label.set_text(_("Operation cancelled by user."))
        self.progress_bar.set_text(_("Cancelled"))
        self.cancel_button.set_visible(False)
        self.close_button.set_visible(True)
    
    def _on_close_clicked(self, button):
        """Handle close button click."""
        self.hide_dialog()
    
    def hide_dialog(self):
        """Hide the dialog."""
        self.spinner.stop()
        self.set_visible(False)
    
    def is_visible(self) -> bool:
        """Check if dialog is visible."""
        return self.get_visible()


def get_progress_dialog_css() -> str:
    """Get the CSS for the progress dialog."""
    return """
/* Progress Dialog Styles */
.progress-dialog-backdrop {
    background-color: rgba(0, 0, 0, 0.6);
}

.progress-dialog-card {
    background-color: @window_bg_color;
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.success-icon {
    color: #2ec27e;
}

.error-icon {
    color: #e01b24;
}

.progress-dialog-card .title-2 {
    font-weight: 700;
    font-size: 18px;
}

.progress-dialog-card .dim-label {
    font-size: 14px;
}

.progress-dialog-card progressbar text {
    font-size: 14px;
}

.progress-dialog-card expander title {
    font-size: 14px;
}
"""
