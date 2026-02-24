#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Big Kernel Manager - Mesa Manager

This module provides functionality for managing Mesa drivers
including listing, installing, and switching between different versions.
"""

from typing import List, Dict, Optional, Callable

from core.base_manager import BaseManager
from core.package_manager import PackageManager
from core.logging_config import get_logger


# Mesa driver configurations
# Note: stable mesa includes all complementary packages that Manjaro separates,
# while mesa-tkg bundles everything together.
MESA_DRIVERS = [
    {
        "id": "amber",
        "name": "Amber",
        "detect_package": "mesa-amber",
        "packages": ["mesa-amber"],
        "conflicts": [
            "mesa",
            "lib32-mesa",
            "mesa-git",
            "mesa-tkg-stable",
            "mesa-tkg-git",
            "vulkan-intel",
            "lib32-vulkan-intel",
            "vulkan-radeon",
            "lib32-vulkan-radeon",
            "vulkan-swrast",
            "lib32-vulkan-swrast",
            "vulkan-mesa-implicit-layers",
            "lib32-vulkan-mesa-implicit-layers",
            "mesa-utils",
        ],
        "description": "Stable and well-tested version of Mesa",
    },
    {
        "id": "stable",
        "name": "Stable",
        "detect_package": "mesa",
        "packages": [
            "mesa",
            "lib32-mesa",
            "vulkan-radeon",
            "lib32-vulkan-radeon",
            "vulkan-intel",
            "lib32-vulkan-intel",
            "vulkan-swrast",
            "lib32-vulkan-swrast",
            "mesa-utils",
        ],
        "conflicts": ["mesa-amber", "mesa-git", "mesa-tkg-stable", "mesa-tkg-git"],
        "description": "Regular Mesa release (recommended)",
    },
    {
        "id": "tkg-stable",
        "name": "Tkg-Stable",
        "detect_package": "mesa-tkg-stable",
        "packages": ["mesa-tkg-stable"],
        "conflicts": [
            "mesa",
            "lib32-mesa",
            "mesa-amber",
            "mesa-git",
            "mesa-tkg-git",
            "vulkan-intel",
            "lib32-vulkan-intel",
            "vulkan-radeon",
            "lib32-vulkan-radeon",
            "vulkan-swrast",
            "lib32-vulkan-swrast",
            "vulkan-mesa-implicit-layers",
            "lib32-vulkan-mesa-implicit-layers",
            "mesa-utils",
        ],
        "description": "Enhanced performance build of stable Mesa",
    },
    {
        "id": "tkg-git",
        "name": "Tkg-git",
        "detect_package": "mesa-tkg-git",
        "packages": ["mesa-tkg-git"],
        "conflicts": [
            "mesa",
            "lib32-mesa",
            "mesa-amber",
            "mesa-tkg-stable",
            "vulkan-intel",
            "lib32-vulkan-intel",
            "vulkan-radeon",
            "lib32-vulkan-radeon",
            "vulkan-swrast",
            "lib32-vulkan-swrast",
            "vulkan-mesa-implicit-layers",
            "lib32-vulkan-mesa-implicit-layers",
            "mesa-utils",
        ],
        "description": "Latest development version with cutting-edge features",
    },
]


class MesaManager(BaseManager):
    """Manager for handling Mesa drivers."""

    def __init__(self):
        """Initialize the Mesa manager."""
        super().__init__()
        self._logger = get_logger("MesaManager")
        self.package_manager = PackageManager()
        self.drivers = MESA_DRIVERS.copy()

    def get_available_drivers(self) -> List[Dict]:
        """
        Get a list of available Mesa drivers.

        Returns:
            List of available Mesa drivers with their information.
        """
        active_driver = self._get_active_driver()

        drivers = []
        for driver in self.drivers:
            driver_copy = driver.copy()
            driver_copy["active"] = driver_copy["id"] == active_driver
            drivers.append(driver_copy)

        return drivers

    def _get_active_driver(self) -> str:
        """
        Determine which Mesa driver is currently active.

        Uses _is_real_package_installed (pacman -Qi + Name check) instead
        of pacman -Q to avoid false positives from virtual provides
        (e.g. mesa-tkg-stable provides 'mesa', so pacman -Q mesa would
        incorrectly match the stable driver).

        Returns:
            ID of the active driver, or "stable" if not determined.
        """
        for driver in self.drivers:
            detect_pkg = driver.get("detect_package", driver["packages"][0])
            if self._is_real_package_installed(detect_pkg):
                return driver["id"]

        return "stable"

    def apply_driver(
        self,
        driver_id: str,
        progress_callback: Optional[Callable] = None,
        output_callback: Optional[Callable] = None,
        complete_callback: Optional[Callable] = None,
    ) -> None:
        """
        Apply a Mesa driver configuration.

        Args:
            driver_id: ID of the driver to apply.
            progress_callback: Callback function for progress updates.
            output_callback: Callback function for command output.
            complete_callback: Callback function for completion notification.
        """
        # Find the driver by ID
        selected_driver = None
        for driver in self.drivers:
            if driver["id"] == driver_id:
                selected_driver = driver
                break

        if not selected_driver:
            self._logger.error(f"Driver not found: {driver_id}")
            self._output(output_callback, f"Driver not found: {driver_id}")
            if complete_callback:
                complete_callback(False)
            return

        self._logger.info(f"Applying Mesa driver: {selected_driver['name']}")

        # Start thread for applying driver
        import threading

        threading.Thread(
            target=self._apply_driver_thread,
            args=(
                selected_driver,
                progress_callback,
                output_callback,
                complete_callback,
            ),
            daemon=True,
        ).start()

    def _apply_driver_thread(
        self,
        driver: Dict,
        progress_callback: Optional[Callable],
        output_callback: Optional[Callable],
        complete_callback: Optional[Callable],
    ) -> None:
        """
        Thread function for applying a driver.

        Args:
            driver: The driver configuration to apply.
            progress_callback: Callback function for progress updates.
            output_callback: Callback function for command output.
            complete_callback: Callback function for completion notification.
        """
        import subprocess
        import os

        self._progress(progress_callback, 0.1, f"Applying {driver['name']} driver...")
        self._output(
            output_callback, f"Starting {driver['name']} driver installation..."
        )

        try:
            # Step 1: Check for conflicting packages
            installed_conflicts = []
            if driver["conflicts"]:
                self._progress(
                    progress_callback, 0.2, "Checking for conflicting packages..."
                )

                installed_conflicts = [
                    conflict
                    for conflict in driver["conflicts"]
                    if self._is_real_package_installed(conflict)
                ]

                if installed_conflicts:
                    self._output(
                        output_callback,
                        f"Removing conflicts: {', '.join(installed_conflicts)}",
                    )

            # Step 2: Check available packages to install
            self._progress(
                progress_callback, 0.3, f"Checking {driver['name']} packages..."
            )

            # For packages with multiple items (like stable mesa), filter to those available
            packages_to_install = []
            for pkg in driver["packages"]:
                if self._package_available(pkg):
                    packages_to_install.append(pkg)
                else:
                    self._output(
                        output_callback, f"⚠️ Package {pkg} not available, skipping..."
                    )

            if not packages_to_install:
                self._output(output_callback, "❌ No packages available to install.")
                if complete_callback:
                    complete_callback(False)
                return

            self._output(
                output_callback, f"Installing: {', '.join(packages_to_install)}"
            )

            # Step 3: Build a single pkexec command that removes conflicts + installs packages
            # This avoids multiple password prompts by running everything under one auth
            cmd_parts = []
            if installed_conflicts:
                cmd_parts.append(
                    f"pacman -Rdd --noconfirm {' '.join(installed_conflicts)}"
                )
            cmd_parts.append(
                f"pacman -S --noconfirm --ask 4 {' '.join(packages_to_install)}"
            )
            combined_cmd = " && ".join(cmd_parts)

            self._progress(
                progress_callback, 0.4, f"Applying {driver['name']} driver..."
            )

            full_cmd = [self.sudo_command, "bash", "-c", combined_cmd]

            env = os.environ.copy()
            env["LANG"] = "C"

            process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                env=env,
            )

            progress = 0.4
            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    line = line.strip()
                    if line:
                        self._output(output_callback, line)
                        progress = self._parse_progress(line, progress)
                        self._progress(progress_callback, progress, None)

            process.wait()

            if process.returncode != 0:
                self._progress(progress_callback, 0.0, "Failed to apply driver.")
                self._output(
                    output_callback,
                    f"❌ Operation failed (exit code: {process.returncode})",
                )
                if complete_callback:
                    complete_callback(False)
                return

            # Success
            self._progress(progress_callback, 1.0, "Driver applied successfully!")
            self._output(
                output_callback, f"✅ {driver['name']} driver applied successfully!"
            )

            if complete_callback:
                complete_callback(True)

        except Exception as e:
            self._logger.error(f"Error applying driver: {e}")
            self._progress(progress_callback, 0.0, f"Error: {str(e)}")
            self._output(output_callback, f"❌ Error: {str(e)}")
            if complete_callback:
                complete_callback(False)

    def _is_real_package_installed(self, package_name: str) -> bool:
        """
        Check if a package is installed by its exact name, not virtual provides.

        pacman -Q resolves virtual provides (e.g. mesa-tkg-stable provides mesa),
        which causes false positives. This method uses pacman -Qi and verifies
        the Name field matches exactly.

        LANG=C is forced so the "Name" field label is always in English,
        regardless of the user's desktop locale.

        Args:
            package_name: Exact package name to check.

        Returns:
            True if the package is installed with that exact name.
        """
        import os
        import subprocess

        cmd = ["pacman", "-Qi", package_name]
        env = os.environ.copy()
        env["LANG"] = "C"
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, env=env
        )
        if result.returncode != 0:
            return False
        # Verify the Name field matches exactly
        for line in result.stdout.splitlines():
            if line.startswith("Name"):
                actual_name = line.split(":", 1)[1].strip()
                return actual_name == package_name
        return False

    def _package_available(self, package_name: str) -> bool:
        """
        Check if a package is available in the repositories.

        Args:
            package_name: Name of the package to check.

        Returns:
            True if the package exists in repos, False otherwise.
        """
        import subprocess

        cmd = ["pacman", "-Si", package_name]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.returncode == 0
