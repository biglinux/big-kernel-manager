#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kernel Manager Application - Main Entry Point

This module serves as the entry point for the Kernel Manager application,
which allows users to manage and install different kernel versions and
Mesa drivers on Manjaro Linux.
"""

import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gio, Adw

from ui.application import KernelManagerApplication


def main():
    """Main entry point for the application."""
    app = KernelManagerApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())