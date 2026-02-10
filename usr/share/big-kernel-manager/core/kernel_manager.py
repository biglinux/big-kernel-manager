#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Big Kernel Manager - Kernel Manager

This module provides functionality for managing Linux kernels
including listing, installing, and removing kernels.
"""

import os
import platform
import re
import threading
import requests
from xml.etree import ElementTree
from typing import List, Dict, Optional, Callable

from core.base_manager import BaseManager
from core.package_manager import PackageManager
from core.constants import (
    KERNEL_PATTERNS,
    EXCLUDED_PATTERNS,
    KERNEL_ORG_FEED_URL,
    DEFAULT_LTS_VERSIONS
)
from core.logging_config import get_logger


class KernelManager(BaseManager):
    """Manager for handling Linux kernels."""

    def __init__(self):
        """Initialize the kernel manager."""
        super().__init__()
        self._logger = get_logger("KernelManager")
        self.package_manager = PackageManager()
        
        # Use patterns from constants
        self.kernel_patterns = KERNEL_PATTERNS
        self.excluded_patterns = EXCLUDED_PATTERNS
        
        # LTS versions - lazy loaded to avoid blocking startup
        self._lts_versions = None
    
    @property
    def lts_versions(self) -> List[str]:
        """Get LTS versions, fetching from kernel.org if not cached."""
        if self._lts_versions is None:
            self._lts_versions = self._get_lts_kernel_versions()
        return self._lts_versions
    
    def get_running_kernel(self) -> str:
        """
        Get the currently running kernel version string.
        
        Returns:
            The running kernel release string (e.g. "6.12.10-1-MANJARO").
        """
        return platform.release()
    
    def get_running_kernel_package(self) -> str:
        """
        Get the package name of the currently running kernel.
        
        Returns:
            The package name of the running kernel, or empty string if not found.
        """
        running_version = self.get_running_kernel()
        
        # Get installed kernels and match by version
        installed = self.get_installed_kernels()
        for kernel in installed:
            pkg_version = kernel.get("version", "")
            # The running kernel version often starts with the package version
            if pkg_version and running_version.startswith(pkg_version.split("-")[0]):
                return kernel["name"]
        
        # Fallback: try to determine from the release string
        # e.g. "6.12.10-1-MANJARO" -> look for linux612
        version_match = re.match(r"(\d+)\.(\d+)", running_version)
        if version_match:
            major = version_match.group(1)
            minor = version_match.group(2)
            possible_name = f"linux{major}{minor}"
            for kernel in installed:
                if kernel["name"] == possible_name:
                    return possible_name
        
        return ""
    
    def _get_lts_kernel_versions(self) -> List[str]:
        """
        Get a list of current LTS kernel versions from kernel.org.
        
        Returns:
            List of LTS kernel versions as strings (e.g. "612" for 6.12).
        """
        lts_versions = []
        try:
            # Use short timeout to avoid blocking startup
            response = requests.get(KERNEL_ORG_FEED_URL, timeout=1)
            if response.status_code == 200:
                root = ElementTree.fromstring(response.content)
                for item in root.findall(".//item"):
                    title = item.find("title")
                    if title is not None and ": longterm" in title.text:
                        version_match = re.match(r"(\d+\.\d+).*: longterm", title.text)
                        if version_match:
                            version = version_match.group(1)
                            numeric_version = version.replace(".", "")
                            lts_versions.append(numeric_version)
            
            self._logger.debug(f"Fetched LTS versions: {lts_versions}")
            return lts_versions
        except Exception as e:
            self._logger.warning(f"Failed to get LTS kernel versions: {e}")
            return DEFAULT_LTS_VERSIONS.copy()
    
    def get_installed_kernels(self) -> List[Dict]:
        """
        Get a list of installed kernels.
        
        Returns:
            List of installed kernels with their information.
        """
        installed_packages = self.package_manager.get_installed_packages()
        
        kernels = []
        for package in installed_packages:
            if self._is_kernel_package(package["name"]):
                kernel = {
                    "name": package["name"],
                    "version": package["version"],
                    "installed": True
                }
                self._add_kernel_flags(kernel)
                kernels.append(kernel)
        
        return kernels
    
    def get_available_kernels(self) -> List[Dict]:
        """
        Get a list of available kernels from repositories.
        
        Returns:
            List of available kernels with their information.
        """
        available_kernels = []
        
        for pattern in self.kernel_patterns:
            packages = self._search_kernel_packages(pattern)
            available_kernels.extend(packages)
        
        # Get installed kernels to mark them
        installed_kernels = self.get_installed_kernels()
        installed_names = [k["name"] for k in installed_kernels]
        
        # Filter out duplicates and excluded patterns
        filtered_kernels = []
        seen_kernels = set()
        
        for kernel in available_kernels:
            kernel_name = kernel["name"]
            
            if any(re.search(exclude, kernel_name) for exclude in self.excluded_patterns):
                continue
                
            kernel_key = f"{kernel_name}-{kernel['version']}"
            if kernel_key in seen_kernels:
                continue
                
            seen_kernels.add(kernel_key)
            kernel["installed"] = kernel_name in installed_names
            self._add_kernel_flags(kernel)
            filtered_kernels.append(kernel)
        
        return sorted(filtered_kernels, key=lambda k: (k["name"], k["version"]))
    
    def _search_kernel_packages(self, pattern: str) -> List[Dict]:
        """
        Search for kernel packages matching a pattern.
        
        Args:
            pattern: Regex pattern to search for.
            
        Returns:
            List of matching packages.
        """
        import subprocess
        
        cmd = ["pacman", "-Ss", f"^{pattern}"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            return []
        
        packages = []
        for line in result.stdout.strip().split("\n"):
            if not line or line.startswith(" "):
                continue
            
            match = re.match(r"([^\s]+)/([^\s]+)\s+([^\s]+)", line)
            if match:
                package_name = match.group(2)
                package_version = match.group(3)
                
                if self._is_kernel_package(package_name):
                    packages.append({
                        "name": package_name,
                        "version": package_version,
                        "repository": match.group(1)
                    })
                
        return packages
    
    def _is_kernel_package(self, package_name: str) -> bool:
        """
        Check if a package is a true kernel package (not a module).
        
        Args:
            package_name: Name of the package.
            
        Returns:
            True if it's a kernel package, False otherwise.
        """
        is_kernel = any(re.match(pattern, package_name) for pattern in self.kernel_patterns)
        is_excluded = any(re.search(exclude, package_name) for exclude in self.excluded_patterns)
        return is_kernel and not is_excluded
    
    def _add_kernel_flags(self, kernel: Dict) -> None:
        """
        Add flags to identify kernel types (RT, LTS, etc.)
        
        Args:
            kernel: Kernel dictionary to update with flags.
        """
        kernel_name = kernel["name"]
        
        # RT flag
        if "-rt" in kernel_name:
            kernel["rt"] = True
        
        # LTS flag
        if "-lts" in kernel_name:
            kernel["lts"] = True
        elif "xanmod" not in kernel_name and re.match(r"^linux\d+$", kernel_name):
            version_match = re.match(r"^linux(\d+)$", kernel_name)
            if version_match and version_match.group(1) in self.lts_versions:
                kernel["lts"] = True
        
        # XanMod flag
        if "xanmod" in kernel_name:
            kernel["xanmod"] = True
        
        # Optimized build flags
        match = re.search(r"-x64v(\d)", kernel_name)
        if match:
            kernel["optimized"] = True
            kernel["opt_level"] = match.group(1)
    
    def _get_kernel_modules(self, kernel_name: str) -> List[str]:
        """
        Get a list of module packages that should be installed with the kernel.
        
        Args:
            kernel_name: Name of the kernel.
            
        Returns:
            List of module package names.
        """
        return [f"{kernel_name}-headers"]
    
    def install_kernel(
        self,
        kernel: Dict,
        progress_callback: Optional[Callable] = None,
        output_callback: Optional[Callable] = None,
        complete_callback: Optional[Callable] = None
    ) -> None:
        """
        Install a kernel and its associated modules.
        
        Args:
            kernel: The kernel to install (dict with at least "name").
            progress_callback: Callback function for progress updates.
            output_callback: Callback function for command output.
            complete_callback: Callback function for completion notification.
        """
        kernel_name = kernel["name"]
        modules = self._get_kernel_modules(kernel_name)
        packages = [kernel_name] + modules
        
        self._logger.info(f"Installing kernel: {kernel_name}")
        
        # Use base manager's run_pacman_command
        args = ["-S", "--noconfirm"] + packages
        self._run_pacman_command(
            args=args,
            progress_callback=progress_callback,
            output_callback=output_callback,
            complete_callback=complete_callback,
            operation_name=f"Installing {kernel_name}"
        )
    
    def remove_kernel(
        self,
        kernel: Dict,
        progress_callback: Optional[Callable] = None,
        output_callback: Optional[Callable] = None,
        complete_callback: Optional[Callable] = None
    ) -> None:
        """
        Remove a kernel and its modules.
        
        Args:
            kernel: The kernel to remove (dict with at least "name").
            progress_callback: Callback function for progress updates.
            output_callback: Callback function for command output.
            complete_callback: Callback function for completion notification.
        """
        kernel_name = kernel["name"]
        modules = self._get_kernel_modules(kernel_name)
        packages = [kernel_name] + modules
        
        # Filter for installed packages only
        installed_packages = [
            pkg for pkg in packages 
            if self.package_manager.is_package_installed(pkg)
        ]
        
        if not installed_packages:
            self._output(output_callback, "No packages to remove.")
            if complete_callback:
                complete_callback(True)
            return
        
        self._logger.info(f"Removing kernel: {kernel_name}")
        
        # Use base manager's run_pacman_command
        args = ["-R", "--noconfirm"] + installed_packages
        self._run_pacman_command(
            args=args,
            progress_callback=progress_callback,
            output_callback=output_callback,
            complete_callback=complete_callback,
            operation_name=f"Removing {kernel_name}"
        )