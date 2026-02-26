#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Big Kernel Manager - Test Suite

Unit tests for core functionality covering:
- Mesa driver detection and _is_real_package_installed
- _get_active_driver logic
- Kernel package identification (_is_kernel_package)
- Kernel flag assignment (_add_kernel_flags)
- LTS version fetching with urllib
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add the application source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "share", "big-kernel-manager"))


class TestIsRealPackageInstalled(unittest.TestCase):
    """Tests for MesaManager._is_real_package_installed."""

    def _make_manager(self):
        with patch("core.mesa_manager.get_logger"):
            from core.mesa_manager import MesaManager
            return MesaManager()

    @patch("subprocess.run")
    def test_exact_match_returns_true(self, mock_run):
        """Package name matches exactly -> True."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Name            : mesa-tkg-stable\nVersion         : 24.3.4-1\n"
        )
        mgr = self._make_manager()
        self.assertTrue(mgr._is_real_package_installed("mesa-tkg-stable"))

    @patch("subprocess.run")
    def test_virtual_provides_returns_false(self, mock_run):
        """Query for 'mesa' but Name is mesa-tkg-stable -> False."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Name            : mesa-tkg-stable\nVersion         : 24.3.4-1\n"
        )
        mgr = self._make_manager()
        self.assertFalse(mgr._is_real_package_installed("mesa"))

    @patch("subprocess.run")
    def test_not_installed_returns_false(self, mock_run):
        """Package not installed (returncode != 0) -> False."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        mgr = self._make_manager()
        self.assertFalse(mgr._is_real_package_installed("mesa-tkg-git"))

    @patch("subprocess.run")
    def test_lang_c_is_forced(self, mock_run):
        """Verify LANG=C is set in subprocess environment."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        mgr = self._make_manager()
        mgr._is_real_package_installed("mesa")

        call_kwargs = mock_run.call_args
        env = call_kwargs.kwargs.get("env") or call_kwargs[1].get("env")
        self.assertEqual(env.get("LANG"), "C")

    @patch("subprocess.run")
    def test_no_name_field_returns_false(self, mock_run):
        """Output has no Name field -> False."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Version         : 24.3.4-1\nDescription     : Mesa\n"
        )
        mgr = self._make_manager()
        self.assertFalse(mgr._is_real_package_installed("mesa"))


class TestGetActiveDriver(unittest.TestCase):
    """Tests for MesaManager._get_active_driver."""

    def _make_manager(self):
        with patch("core.mesa_manager.get_logger"):
            from core.mesa_manager import MesaManager
            return MesaManager()

    @patch("subprocess.run")
    def test_tkg_stable_detected(self, mock_run):
        """When mesa-tkg-stable is installed, returns 'tkg-stable'."""
        def side_effect(cmd, **kwargs):
            pkg = cmd[2]
            if pkg == "mesa-tkg-stable":
                return MagicMock(
                    returncode=0,
                    stdout=f"Name            : {pkg}\nVersion         : 24.3.4-1\n"
                )
            return MagicMock(returncode=1, stdout="")

        mock_run.side_effect = side_effect
        mgr = self._make_manager()
        self.assertEqual(mgr._get_active_driver(), "tkg-stable")

    @patch("subprocess.run")
    def test_stable_detected(self, mock_run):
        """When only mesa is installed, returns 'stable'."""
        def side_effect(cmd, **kwargs):
            pkg = cmd[2]
            if pkg == "mesa":
                return MagicMock(
                    returncode=0,
                    stdout=f"Name            : {pkg}\nVersion         : 24.3.4-1\n"
                )
            return MagicMock(returncode=1, stdout="")

        mock_run.side_effect = side_effect
        mgr = self._make_manager()
        self.assertEqual(mgr._get_active_driver(), "stable")

    @patch("subprocess.run")
    def test_fallback_to_stable(self, mock_run):
        """When no driver is detected, falls back to 'stable'."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        mgr = self._make_manager()
        self.assertEqual(mgr._get_active_driver(), "stable")


class TestIsKernelPackage(unittest.TestCase):
    """Tests for KernelManager._is_kernel_package."""

    def _make_manager(self):
        with patch("core.kernel_manager.get_logger"):
            from core.kernel_manager import KernelManager
            mgr = KernelManager()
            # Force LTS versions to avoid network call
            mgr._lts_versions = ["66", "612", "614"]
            return mgr

    def test_standard_kernel(self):
        mgr = self._make_manager()
        self.assertTrue(mgr._is_kernel_package("linux612"))
        self.assertTrue(mgr._is_kernel_package("linux66"))
        self.assertTrue(mgr._is_kernel_package("linux"))

    def test_lts_kernel(self):
        mgr = self._make_manager()
        self.assertTrue(mgr._is_kernel_package("linux-lts"))
        self.assertTrue(mgr._is_kernel_package("linux612-lts"))

    def test_xanmod_kernel(self):
        mgr = self._make_manager()
        self.assertTrue(mgr._is_kernel_package("linux-xanmod"))
        self.assertTrue(mgr._is_kernel_package("linux612-xanmod"))

    def test_rt_kernel(self):
        mgr = self._make_manager()
        self.assertTrue(mgr._is_kernel_package("linux612-rt"))

    def test_excludes_modules(self):
        mgr = self._make_manager()
        self.assertFalse(mgr._is_kernel_package("linux612-headers"))
        self.assertFalse(mgr._is_kernel_package("linux612-nvidia"))
        self.assertFalse(mgr._is_kernel_package("linux612-virtualbox"))
        self.assertFalse(mgr._is_kernel_package("linux612-zfs"))

    def test_excludes_non_kernel(self):
        mgr = self._make_manager()
        self.assertFalse(mgr._is_kernel_package("python"))
        self.assertFalse(mgr._is_kernel_package("mesa"))


class TestAddKernelFlags(unittest.TestCase):
    """Tests for KernelManager._add_kernel_flags."""

    def _make_manager(self):
        with patch("core.kernel_manager.get_logger"):
            from core.kernel_manager import KernelManager
            mgr = KernelManager()
            mgr._lts_versions = ["66", "612", "614"]
            return mgr

    def test_rt_flag(self):
        mgr = self._make_manager()
        kernel = {"name": "linux612-rt", "version": "6.12.10-1"}
        mgr._add_kernel_flags(kernel)
        self.assertTrue(kernel.get("rt"))

    def test_explicit_lts_flag(self):
        mgr = self._make_manager()
        kernel = {"name": "linux-lts", "version": "6.6.70-1"}
        mgr._add_kernel_flags(kernel)
        self.assertTrue(kernel.get("lts"))

    def test_implicit_lts_flag_from_version_list(self):
        mgr = self._make_manager()
        kernel = {"name": "linux66", "version": "6.6.70-1"}
        mgr._add_kernel_flags(kernel)
        self.assertTrue(kernel.get("lts"))

    def test_non_lts_kernel_no_flag(self):
        mgr = self._make_manager()
        kernel = {"name": "linux613", "version": "6.13.1-1"}
        mgr._add_kernel_flags(kernel)
        self.assertFalse(kernel.get("lts", False))

    def test_xanmod_flag(self):
        mgr = self._make_manager()
        kernel = {"name": "linux-xanmod", "version": "6.12.10-1"}
        mgr._add_kernel_flags(kernel)
        self.assertTrue(kernel.get("xanmod"))

    def test_optimized_flag(self):
        mgr = self._make_manager()
        kernel = {"name": "linux-xanmod-x64v3", "version": "6.12.10-1"}
        mgr._add_kernel_flags(kernel)
        self.assertTrue(kernel.get("optimized"))
        self.assertEqual(kernel.get("opt_level"), "3")

    def test_xanmod_not_flagged_as_lts(self):
        """Xanmod kernels should not get implicit LTS flag."""
        mgr = self._make_manager()
        kernel = {"name": "linux-xanmod", "version": "6.12.10-1"}
        mgr._add_kernel_flags(kernel)
        self.assertFalse(kernel.get("lts", False))


class TestGetLtsKernelVersions(unittest.TestCase):
    """Tests for KernelManager._get_lts_kernel_versions with urllib."""

    def _make_manager(self):
        with patch("core.kernel_manager.get_logger"):
            from core.kernel_manager import KernelManager
            mgr = KernelManager()
            return mgr

    @patch("core.kernel_manager.urlopen")
    def test_parses_lts_versions(self, mock_urlopen):
        """Verify LTS versions are parsed from XML feed."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss><channel>
  <item><title>6.12.10: longterm</title></item>
  <item><title>6.6.70: longterm</title></item>
  <item><title>6.14.1: mainline</title></item>
  <item><title>6.1.120: longterm</title></item>
</channel></rss>"""

        mock_response = MagicMock()
        mock_response.read.return_value = xml
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        mgr = self._make_manager()
        versions = mgr._get_lts_kernel_versions()
        self.assertIn("612", versions)
        self.assertIn("66", versions)
        self.assertIn("61", versions)
        self.assertNotIn("614", versions)  # mainline, not longterm

    @patch("core.kernel_manager.urlopen")
    def test_fallback_on_error(self, mock_urlopen):
        """On network error, returns DEFAULT_LTS_VERSIONS."""
        mock_urlopen.side_effect = Exception("Connection refused")
        mgr = self._make_manager()
        versions = mgr._get_lts_kernel_versions()
        from core.constants import DEFAULT_LTS_VERSIONS
        self.assertEqual(versions, DEFAULT_LTS_VERSIONS)


class TestPackageManager(unittest.TestCase):
    """Tests for PackageManager methods."""

    @patch("subprocess.run")
    def test_is_package_installed_true(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        from core.package_manager import PackageManager
        pm = PackageManager()
        self.assertTrue(pm.is_package_installed("linux612"))

    @patch("subprocess.run")
    def test_is_package_installed_false(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        from core.package_manager import PackageManager
        pm = PackageManager()
        self.assertFalse(pm.is_package_installed("linux999"))

    @patch("subprocess.run")
    def test_get_installed_packages(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="linux612 6.12.10-1\nmesa 24.3.4-1\n"
        )
        from core.package_manager import PackageManager
        pm = PackageManager()
        packages = pm.get_installed_packages()
        self.assertEqual(len(packages), 2)
        self.assertEqual(packages[0]["name"], "linux612")
        self.assertEqual(packages[0]["version"], "6.12.10-1")
        self.assertEqual(packages[1]["name"], "mesa")


if __name__ == "__main__":
    unittest.main()
