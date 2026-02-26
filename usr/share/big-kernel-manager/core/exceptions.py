#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Big Kernel Manager - Custom Exceptions

This module defines custom exception classes for better error handling
throughout the application.
"""

from typing import List, Optional


class KernelManagerError(Exception):
    """Base exception for all Kernel Manager errors."""

    pass


class PackageNotFoundError(KernelManagerError):
    """Raised when a package cannot be found in repositories."""

    def __init__(self, package_name: str, message: Optional[str] = None):
        self.package_name = package_name
        self.message = message or f"Package not found: {package_name}"
        super().__init__(self.message)


class InstallationError(KernelManagerError):
    """Raised when package installation fails."""

    def __init__(
        self,
        package_name: str,
        return_code: Optional[int] = None,
        message: Optional[str] = None,
    ):
        self.package_name = package_name
        self.return_code = return_code
        self.message = message or f"Failed to install package: {package_name}"
        if return_code is not None:
            self.message += f" (exit code: {return_code})"
        super().__init__(self.message)


class RemovalError(KernelManagerError):
    """Raised when package removal fails."""

    def __init__(
        self,
        package_name: str,
        return_code: Optional[int] = None,
        message: Optional[str] = None,
    ):
        self.package_name = package_name
        self.return_code = return_code
        self.message = message or f"Failed to remove package: {package_name}"
        if return_code is not None:
            self.message += f" (exit code: {return_code})"
        super().__init__(self.message)


class PrivilegeError(KernelManagerError):
    """Raised when elevated privileges are required but not available."""

    def __init__(self, operation: Optional[str] = None, message: Optional[str] = None):
        self.operation = operation
        self.message = message or "Elevated privileges required"
        if operation:
            self.message = f"Elevated privileges required for: {operation}"
        super().__init__(self.message)


class ConfigurationError(KernelManagerError):
    """Raised when there's a configuration-related error."""

    def __init__(self, config_key: Optional[str] = None, message: Optional[str] = None):
        self.config_key = config_key
        self.message = message or "Configuration error"
        if config_key:
            self.message = f"Configuration error for key: {config_key}"
        super().__init__(self.message)


class NetworkError(KernelManagerError):
    """Raised when a network operation fails."""

    def __init__(self, url: Optional[str] = None, message: Optional[str] = None):
        self.url = url
        self.message = message or "Network error occurred"
        if url:
            self.message += f" (URL: {url})"
        super().__init__(self.message)


class DependencyError(KernelManagerError):
    """Raised when there's a package dependency issue."""

    def __init__(
        self,
        package_name: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        message: Optional[str] = None,
    ):
        self.package_name = package_name
        self.dependencies = dependencies or []
        self.message = message or "Dependency error"
        if package_name:
            self.message = f"Dependency error for: {package_name}"
        if dependencies:
            self.message += f" - Missing: {', '.join(dependencies)}"
        super().__init__(self.message)


class BootloaderError(KernelManagerError):
    """Raised when bootloader configuration fails."""

    def __init__(self, bootloader: Optional[str] = None, message: Optional[str] = None):
        self.bootloader = bootloader
        self.message = message or "Bootloader configuration error"
        if bootloader:
            self.message = f"Error configuring bootloader: {bootloader}"
        super().__init__(self.message)
