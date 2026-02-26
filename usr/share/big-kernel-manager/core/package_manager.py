#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kernel Manager Application - Package Manager

This module provides a query-only interface to interact with pacman package
manager for listing and checking packages. Actual install/remove operations
are handled by BaseManager._run_pacman_command.
"""

import re
import subprocess


class PackageManager:
    """Interface for querying the pacman package manager."""

    def __init__(self):
        """Initialize the package manager."""
        pass

    def get_installed_packages(self, pattern=None):
        """
        Get a list of installed packages.

        Args:
            pattern: Optional regex pattern to filter packages.

        Returns:
            list: List of installed packages.
        """
        cmd = ["pacman", "-Q"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            return []

        packages = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split()
            if len(parts) >= 2:
                package_name = parts[0]
                package_version = parts[1]

                if pattern and not re.search(pattern, package_name):
                    continue

                packages.append({"name": package_name, "version": package_version})

        return packages

    def get_available_packages(self, pattern=None):
        """
        Get a list of available packages from repositories.

        Args:
            pattern: Optional regex pattern to filter packages.

        Returns:
            list: List of available packages.
        """
        cmd = ["pacman", "-Ss"]
        if pattern:
            cmd.append(pattern)

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            return []

        packages = []

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            if line.startswith(" "):
                continue

            match = re.match(r"([^\s]+)/([^\s]+)\s+([^\s]+)", line)
            if match:
                packages.append(
                    {
                        "name": match.group(2),
                        "version": match.group(3),
                        "repository": match.group(1),
                    }
                )

        return packages

    def is_package_installed(self, package_name):
        """
        Check if a package is installed.

        Note: pacman -Q resolves virtual 'provides'. If you need to check
        the exact real package name, use MesaManager._is_real_package_installed.

        Args:
            package_name: Name of the package.

        Returns:
            bool: True if the package is installed, False otherwise.
        """
        cmd = ["pacman", "-Q", package_name]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.returncode == 0
