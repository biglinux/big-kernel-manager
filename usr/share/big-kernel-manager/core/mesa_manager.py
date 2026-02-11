#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Big Kernel Manager - Mesa Manager

This module provides functionality for managing Mesa drivers
including listing, installing, and switching between different versions.
"""

import re
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
        "packages": ["mesa-amber"],
        "conflicts": ["mesa", "mesa-git", "mesa-tkg-git"],
        "description": "Stable and well-tested version of Mesa"
    },
    {
        "id": "stable",
        "name": "Stable",
        "packages": [
            "mesa", "lib32-mesa",
            "vulkan-radeon", "lib32-vulkan-radeon",
            "vulkan-intel", "lib32-vulkan-intel",
            "vulkan-swrast", "lib32-vulkan-swrast",
            "mesa-utils"
        ],
        "conflicts": ["mesa-amber", "mesa-git", "mesa-tkg-git"],
        "description": "Regular Mesa release (recommended)"
    },
    {
        "id": "tkg-stable",
        "name": "Tkg-Stable",
        "packages": ["mesa-tkg"],
        "conflicts": ["mesa", "mesa-amber", "mesa-git", "mesa-tkg-git"],
        "description": "Enhanced performance build of stable Mesa"
    },
    {
        "id": "tkg-git",
        "name": "Tkg-git",
        "packages": ["mesa-tkg-git"],
        "conflicts": ["mesa", "mesa-amber", "mesa-tkg"],
        "description": "Latest development version with cutting-edge features"
    }
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
            driver_copy["active"] = (driver_copy["id"] == active_driver)
            drivers.append(driver_copy)
        
        return drivers
    
    def _get_active_driver(self) -> str:
        """
        Determine which Mesa driver is currently active.
        
        Returns:
            ID of the active driver, or "stable" if not determined.
        """
        installed_packages = self.package_manager.get_installed_packages()
        installed_names = [pkg["name"] for pkg in installed_packages]
        
        for driver in self.drivers:
            for package in driver["packages"]:
                if package in installed_names:
                    return driver["id"]
        
        return "stable"
    
    def apply_driver(
        self,
        driver_id: str,
        progress_callback: Optional[Callable] = None,
        output_callback: Optional[Callable] = None,
        complete_callback: Optional[Callable] = None
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
            args=(selected_driver, progress_callback, output_callback, complete_callback),
            daemon=True
        ).start()
    
    def _apply_driver_thread(
        self,
        driver: Dict,
        progress_callback: Optional[Callable],
        output_callback: Optional[Callable],
        complete_callback: Optional[Callable]
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
        self._output(output_callback, f"Starting {driver['name']} driver installation...")
        
        try:
            # Step 1: Remove conflicting packages
            if driver["conflicts"]:
                self._progress(progress_callback, 0.2, "Checking for conflicting packages...")
                
                installed_conflicts = [
                    conflict for conflict in driver["conflicts"]
                    if self.package_manager.is_package_installed(conflict)
                ]
                
                if installed_conflicts:
                    self._output(output_callback, f"Removing conflicts: {', '.join(installed_conflicts)}")
                    self._progress(progress_callback, 0.3, "Removing conflicting packages...")
                    
                    # Use -Rdd to skip dependency checks (we're replacing the packages right after)
                    remove_cmd = [self.sudo_command, "pacman", "-Rdd", "--noconfirm"] + installed_conflicts
                    
                    env = os.environ.copy()
                    env["LANG"] = "C"
                    
                    process = subprocess.Popen(
                        remove_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL,
                        text=True,
                        env=env
                    )
                    
                    for line in iter(process.stdout.readline, ""):
                        line = line.strip()
                        if line:
                            self._output(output_callback, line)
                    
                    process.wait()
                    
                    if process.returncode != 0:
                        self._progress(progress_callback, 0.0, "Failed to remove conflicting packages.")
                        self._output(output_callback, "❌ Failed to remove conflicting packages.")
                        if complete_callback:
                            complete_callback(False)
                        return
            
            # Step 2: Install the new packages
            self._progress(progress_callback, 0.5, f"Installing {driver['name']} packages...")
            
            # For packages with multiple items (like stable mesa), filter to those available
            packages_to_install = []
            for pkg in driver["packages"]:
                if self._package_available(pkg):
                    packages_to_install.append(pkg)
                else:
                    self._output(output_callback, f"⚠️ Package {pkg} not available, skipping...")
            
            if not packages_to_install:
                self._output(output_callback, "❌ No packages available to install.")
                if complete_callback:
                    complete_callback(False)
                return
            
            self._output(output_callback, f"Installing: {', '.join(packages_to_install)}")
            
            # Use --noconfirm --ask 4 to auto-resolve replace conflicts
            install_cmd = [self.sudo_command, "pacman", "-S", "--noconfirm", "--ask", "4"] + packages_to_install
            
            env = os.environ.copy()
            env["LANG"] = "C"
            
            process = subprocess.Popen(
                install_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                env=env
            )
            
            progress = 0.5
            for line in iter(process.stdout.readline, ""):
                line = line.strip()
                if line:
                    self._output(output_callback, line)
                    progress = self._parse_progress(line, progress)
                    self._progress(progress_callback, progress, None)
            
            process.wait()
            
            if process.returncode != 0:
                self._progress(progress_callback, 0.0, "Failed to install packages.")
                self._output(output_callback, f"❌ Installation failed (exit code: {process.returncode})")
                if complete_callback:
                    complete_callback(False)
                return
            
            # Success
            self._progress(progress_callback, 1.0, "Driver applied successfully!")
            self._output(output_callback, f"✅ {driver['name']} driver applied successfully!")
            
            if complete_callback:
                complete_callback(True)
                
        except Exception as e:
            self._logger.error(f"Error applying driver: {e}")
            self._progress(progress_callback, 0.0, f"Error: {str(e)}")
            self._output(output_callback, f"❌ Error: {str(e)}")
            if complete_callback:
                complete_callback(False)
    
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