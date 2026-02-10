#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kernel Manager Application - Package Manager

This module provides an interface to interact with pacman package manager
for installing and managing packages.
"""

import os
import re
import subprocess
import threading
import time


class PackageManager:
    """Interface for the pacman package manager."""

    def __init__(self):
        """Initialize the package manager."""
        self.sudo_command = "pkexec"  # Using polkit for privilege escalation
    
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
                
            # Parse package name and version
            parts = line.split()
            if len(parts) >= 2:
                package_name = parts[0]
                package_version = parts[1]
                
                # Apply pattern filter if provided
                if pattern and not re.search(pattern, package_name):
                    continue
                    
                packages.append({
                    "name": package_name,
                    "version": package_version
                })
                
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
        current_package = None
        
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
                
            # New package entry starts with repo/name version
            if line.startswith(" "):
                # This is a description line, skip
                continue
                
            # Parse package information
            match = re.match(r"([^\s]+)/([^\s]+)\s+([^\s]+)", line)
            if match:
                repo = match.group(1)
                package_name = match.group(2)
                package_version = match.group(3)
                
                packages.append({
                    "name": package_name,
                    "version": package_version,
                    "repository": repo
                })
                
        return packages
    
    def is_package_installed(self, package_name):
        """
        Check if a package is installed.
        
        Args:
            package_name: Name of the package.
            
        Returns:
            bool: True if the package is installed, False otherwise.
        """
        cmd = ["pacman", "-Q", package_name]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.returncode == 0
    
    def install_package(self, package_name, progress_callback=None, complete_callback=None):
        """
        Install a package using pacman.
        
        Args:
            package_name: Name of the package to install.
            progress_callback: Callback function for progress updates.
            complete_callback: Callback function for completion notification.
        """
        # Run installation in a separate thread
        threading.Thread(
            target=self._install_package_thread,
            args=(package_name, progress_callback, complete_callback),
            daemon=True
        ).start()
    
    def _install_package_thread(self, package_name, progress_callback, complete_callback):
        """
        Thread function for package installation.
        
        Args:
            package_name: Name of the package to install.
            progress_callback: Callback function for progress updates.
            complete_callback: Callback function for completion notification.
        """
        if progress_callback:
            progress_callback(0.1, f"Installing {package_name}...")
        
        # Command for installing the package
        cmd = [self.sudo_command, "pacman", "-S", "--noconfirm", package_name]
        
        try:
            # Start the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Initialize progress tracking variables
            download_size = None
            downloaded = 0
            installing = False
            progress = 0.1
            
            # Process output line by line
            for line in iter(process.stdout.readline, ""):
                # Parse progress information
                if "Downloading" in line and "%" in line:
                    # Extract download percentage
                    match = re.search(r"\((\d+)/(\d+)\)", line)
                    if match:
                        current = int(match.group(1))
                        total = int(match.group(2))
                        progress = 0.1 + (current / total) * 0.4  # 10%-50% for downloading
                        
                        if progress_callback:
                            progress_callback(progress, f"Downloading packages ({current}/{total})...")
                
                elif "Installing" in line:
                    installing = True
                    if progress_callback:
                        progress_callback(0.5, "Installing packages...")
                
                elif installing and "installing" in line.lower():
                    # Rough estimation of installation progress
                    progress = min(0.5 + progress * 0.1, 0.9)  # 50%-90% for installing
                    if progress_callback:
                        progress_callback(progress, "Installing...")
            
            # Wait for process to complete
            process.wait()
            
            # Check if installation was successful
            success = process.returncode == 0
            
            # Final progress update
            if progress_callback:
                if success:
                    progress_callback(1.0, "Installation complete!")
                else:
                    progress_callback(0.0, "Installation failed.")
            
            # Notify completion
            if complete_callback:
                complete_callback(success)
                
        except Exception as e:
            # Handle exceptions
            if progress_callback:
                progress_callback(0.0, f"Error: {str(e)}")
            
            if complete_callback:
                complete_callback(False)
    
    def remove_package(self, package_name, progress_callback=None, complete_callback=None):
        """
        Remove a package using pacman.
        
        Args:
            package_name: Name of the package to remove.
            progress_callback: Callback function for progress updates.
            complete_callback: Callback function for completion notification.
        """
        # Run removal in a separate thread
        threading.Thread(
            target=self._remove_package_thread,
            args=(package_name, progress_callback, complete_callback),
            daemon=True
        ).start()
    
    def _remove_package_thread(self, package_name, progress_callback, complete_callback):
        """
        Thread function for package removal.
        
        Args:
            package_name: Name of the package to remove.
            progress_callback: Callback function for progress updates.
            complete_callback: Callback function for completion notification.
        """
        if progress_callback:
            progress_callback(0.1, f"Removing {package_name}...")
        
        # Command for removing the package
        cmd = [self.sudo_command, "pacman", "-R", "--noconfirm", package_name]
        
        try:
            # Start the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Process output line by line
            for line in iter(process.stdout.readline, ""):
                # Update progress (simple approximation)
                if "removing" in line.lower():
                    if progress_callback:
                        progress_callback(0.5, "Removing packages...")
            
            # Wait for process to complete
            process.wait()
            
            # Check if removal was successful
            success = process.returncode == 0
            
            # Final progress update
            if progress_callback:
                if success:
                    progress_callback(1.0, "Removal complete!")
                else:
                    progress_callback(0.0, "Removal failed.")
            
            # Notify completion
            if complete_callback:
                complete_callback(success)
                
        except Exception as e:
            # Handle exceptions
            if progress_callback:
                progress_callback(0.0, f"Error: {str(e)}")
            
            if complete_callback:
                complete_callback(False)
    
    def update_system(self, progress_callback=None, complete_callback=None):
        """
        Update the entire system.
        
        Args:
            progress_callback: Callback function for progress updates.
            complete_callback: Callback function for completion notification.
        """
        # Run system update in a separate thread
        threading.Thread(
            target=self._update_system_thread,
            args=(progress_callback, complete_callback),
            daemon=True
        ).start()
    
    def _update_system_thread(self, progress_callback, complete_callback):
        """
        Thread function for system update.
        
        Args:
            progress_callback: Callback function for progress updates.
            complete_callback: Callback function for completion notification.
        """
        if progress_callback:
            progress_callback(0.0, "Updating system...")
        
        # Command for updating the system
        cmd = [self.sudo_command, "pacman", "-Syu", "--noconfirm"]
        
        try:
            # Start the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Initialize progress tracking variables
            downloading = False
            installing = False
            progress = 0.0
            
            # Process output line by line
            for line in iter(process.stdout.readline, ""):
                # Parse progress information
                if "Synchronizing package databases" in line:
                    if progress_callback:
                        progress_callback(0.1, "Synchronizing package databases...")
                
                elif "Downloading" in line and "%" in line:
                    downloading = True
                    # Extract download percentage if possible
                    match = re.search(r"\((\d+)/(\d+)\)", line)
                    if match:
                        current = int(match.group(1))
                        total = int(match.group(2))
                        progress = 0.1 + (current / total) * 0.4  # 10%-50% for downloading
                        
                        if progress_callback:
                            progress_callback(progress, f"Downloading packages ({current}/{total})...")
                
                elif "Installing" in line:
                    installing = True
                    if progress_callback:
                        progress_callback(0.5, "Installing packages...")
                
                elif installing and "installing" in line.lower():
                    # Rough estimation of installation progress
                    progress = min(0.5 + progress * 0.1, 0.9)  # 50%-90% for installing
                    if progress_callback:
                        progress_callback(progress, "Installing...")
            
            # Wait for process to complete
            process.wait()
            
            # Check if update was successful
            success = process.returncode == 0
            
            # Final progress update
            if progress_callback:
                if success:
                    progress_callback(1.0, "Update complete!")
                else:
                    progress_callback(0.0, "Update failed.")
            
            # Notify completion
            if complete_callback:
                complete_callback(success)
                
        except Exception as e:
            # Handle exceptions
            if progress_callback:
                progress_callback(0.0, f"Error: {str(e)}")
            
            if complete_callback:
                complete_callback(False)