#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Big Kernel Manager - Base Manager

This module provides a base class for all manager classes (Kernel, Mesa, Package)
containing shared functionality for progress handling, output callbacks, and
thread management.
"""

import os
import subprocess
import threading
import time
from typing import Callable, Optional, List

from core.constants import SUDO_COMMAND, PROGRESS_UPDATE_INTERVAL, STATUS_UPDATE_INTERVAL


class BaseManager:
    """Base class for package/kernel/mesa managers with shared functionality."""
    
    def __init__(self):
        """Initialize the base manager."""
        self.sudo_command = SUDO_COMMAND
        self._current_process = None
        self._cancelled = False
    
    def cancel_operation(self):
        """Cancel the current operation by terminating the subprocess."""
        self._cancelled = True
        if self._current_process and self._current_process.poll() is None:
            try:
                # Send SIGTERM to process group
                import signal
                self._current_process.terminate()
                # Give it a moment to terminate gracefully
                try:
                    self._current_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate
                    self._current_process.kill()
                    self._current_process.wait()
            except Exception as e:
                print(f"Error terminating process: {e}")
    
    def _run_pacman_command(
        self,
        args: List[str],
        progress_callback: Optional[Callable] = None,
        output_callback: Optional[Callable] = None,
        complete_callback: Optional[Callable] = None,
        operation_name: str = "Operation"
    ) -> None:
        """
        Run a pacman command in a background thread with progress tracking.
        
        Args:
            args: List of arguments to pass to pacman
            progress_callback: Callback for progress updates (fraction, text)
            output_callback: Callback for terminal output
            complete_callback: Callback for completion (success: bool)
            operation_name: Name of the operation for progress messages
        """
        thread = threading.Thread(
            target=self._execute_command_thread,
            args=(args, progress_callback, output_callback, complete_callback, operation_name),
            daemon=True
        )
        thread.start()
    
    def _execute_command_thread(
        self,
        args: List[str],
        progress_callback: Optional[Callable],
        output_callback: Optional[Callable],
        complete_callback: Optional[Callable],
        operation_name: str
    ) -> None:
        """
        Thread function for executing pacman commands.
        
        Args:
            args: List of arguments for pacman
            progress_callback: Callback for progress updates
            output_callback: Callback for terminal output
            complete_callback: Callback for completion notification
            operation_name: Name of the operation
        """
        # Reset cancellation flag
        self._cancelled = False
        
        cmd = [self.sudo_command, "pacman"] + args
        
        self._output(output_callback, f"Starting {operation_name}...")
        self._output(output_callback, f"Command: {' '.join(cmd)}")
        self._progress(progress_callback, 0.1, f"Starting {operation_name}...")
        
        try:
            # Create environment with consistent locale
            my_env = os.environ.copy()
            my_env["LANG"] = "C"
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=my_env
            )
            
            # Store process reference for cancellation
            self._current_process = process
            
            # Process output
            progress = 0.1
            last_progress_update = time.time()
            last_line_time = time.time()
            
            for line in iter(process.stdout.readline, ""):
                # Check for cancellation
                if self._cancelled:
                    self._output(output_callback, "⚠️ Operation cancelled by user.")
                    break
                
                line = line.strip()
                if line:
                    self._output(output_callback, line)
                    last_line_time = time.time()
                    progress = self._parse_progress(line, progress)
                
                # Periodic progress updates
                current_time = time.time()
                if current_time - last_progress_update > PROGRESS_UPDATE_INTERVAL:
                    self._progress(progress_callback, progress, None)
                    last_progress_update = current_time
                
                # Status message if no output for a while
                if current_time - last_line_time > STATUS_UPDATE_INTERVAL:
                    self._output(output_callback, f"Still working... ({progress:.0%} complete)")
                    last_line_time = current_time
                
                time.sleep(0.01)
            
            # Wait for process to complete (if not cancelled)
            if not self._cancelled:
                process.wait()
                success = process.returncode == 0
            else:
                success = False
            
            # Clear process reference
            self._current_process = None
            
            if self._cancelled:
                self._progress(progress_callback, 0.0, "Operation cancelled")
                self._output(output_callback, "❌ Operation was cancelled.")
                if complete_callback:
                    complete_callback(False)
            elif success:
                self._progress(progress_callback, 1.0, f"{operation_name} complete!")
                self._output(output_callback, f"✅ {operation_name} completed successfully.")
                if complete_callback:
                    complete_callback(success)
            else:
                self._progress(progress_callback, 0.0, f"{operation_name} failed.")
                self._output(output_callback, f"❌ {operation_name} failed (exit code: {process.returncode})")
                if complete_callback:
                    complete_callback(success)
                
        except Exception as e:
            self._current_process = None
            error_msg = f"Error: {str(e)}"
            self._progress(progress_callback, 0.0, error_msg)
            self._output(output_callback, f"❌ {error_msg}")
            if complete_callback:
                complete_callback(False)
    
    def _parse_progress(self, line: str, current_progress: float) -> float:
        """
        Parse a line of output to estimate progress.
        
        Args:
            line: Output line to parse
            current_progress: Current progress value
            
        Returns:
            Updated progress value
        """
        line_lower = line.lower()
        
        # Download phase (10-50%)
        if "downloading" in line_lower or "download" in line_lower:
            import re
            percent_match = re.search(r'(\d+)%', line)
            if percent_match:
                percent = float(percent_match.group(1))
                return 0.1 + (percent / 100.0) * 0.4
            
            match = re.search(r"\((\d+)/(\d+)\)", line)
            if match:
                current = int(match.group(1))
                total = int(match.group(2))
                return 0.1 + (current / total) * 0.4
        
        # Install/remove phase (50-90%)
        elif "installing" in line_lower or "removing" in line_lower:
            return max(current_progress, 0.5)
        
        # Post-transaction (80-90%)
        elif "running post-transaction hooks" in line_lower:
            return 0.8
        
        # Bootloader update (90%)
        elif "generating grub configuration" in line_lower:
            return 0.9
        
        # Checking phases (20-40%)
        elif "checking dependencies" in line_lower:
            return 0.2
        elif "checking for file conflicts" in line_lower:
            return 0.4
        elif "synchronizing package databases" in line_lower:
            return 0.1
        
        return current_progress
    
    def _progress(
        self,
        callback: Optional[Callable],
        fraction: float,
        text: Optional[str]
    ) -> None:
        """
        Send progress update if callback is provided.
        
        Args:
            callback: Progress callback function
            fraction: Progress fraction (0.0 to 1.0)
            text: Optional text to display
        """
        if callback:
            callback(fraction, text)
    
    def _output(self, callback: Optional[Callable], text: str) -> None:
        """
        Send output text if callback is provided.
        
        Args:
            callback: Output callback function
            text: Text to output
        """
        if callback:
            callback(text)
