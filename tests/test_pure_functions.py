"""Tests for pure functions from the UI layer (no GTK dependency)."""

import sys
import os
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "usr", "share", "big-kernel-manager"),
)

from ui.kernel_card_builder import classify_kernel, version_sort_key


# ------------------------------------------------------------------
# classify_kernel
# ------------------------------------------------------------------


class TestClassifyKernel(unittest.TestCase):
    """Tests for classify_kernel()."""

    def test_standard_kernel(self):
        k = {"name": "linux69", "version": "6.9.1-1"}
        info = classify_kernel(k)
        self.assertFalse(info.is_lts)
        self.assertFalse(info.is_rt)
        self.assertFalse(info.is_xanmod)
        self.assertEqual(info.badge_entries, [])

    def test_lts_by_flag(self):
        k = {"name": "linux66", "version": "6.6.50-1", "lts": True}
        info = classify_kernel(k)
        self.assertTrue(info.is_lts)
        self.assertFalse(info.is_rt)
        self.assertIn(("LTS", "success"), info.badge_entries)

    def test_lts_by_name(self):
        k = {"name": "linux66-lts", "version": "6.6.50-1"}
        info = classify_kernel(k)
        self.assertTrue(info.is_lts)

    def test_rt_by_flag(self):
        k = {"name": "linux-rt", "version": "6.8.0-1", "rt": True}
        info = classify_kernel(k)
        self.assertTrue(info.is_rt)
        self.assertIn(("RT", "warning"), info.badge_entries)

    def test_rt_by_name(self):
        k = {"name": "linux66-rt", "version": "6.6.50-1"}
        info = classify_kernel(k)
        self.assertTrue(info.is_rt)

    def test_xanmod_by_flag(self):
        k = {"name": "linux-xanmod", "version": "6.9.1-1", "xanmod": True}
        info = classify_kernel(k)
        self.assertTrue(info.is_xanmod)
        self.assertIn(("Xanmod", "accent"), info.badge_entries)

    def test_xanmod_by_name(self):
        k = {"name": "linux-xanmod-edge", "version": "6.9.1-1"}
        info = classify_kernel(k)
        self.assertTrue(info.is_xanmod)

    def test_lts_rt_combo(self):
        k = {"name": "linux66-lts-rt", "version": "6.6.50-1"}
        info = classify_kernel(k)
        self.assertTrue(info.is_lts)
        self.assertTrue(info.is_rt)
        self.assertEqual(len(info.badge_entries), 2)

    def test_type_desc_not_empty(self):
        for k in [
            {"name": "linux69"},
            {"name": "linux66-lts"},
            {"name": "linux-rt"},
            {"name": "linux-xanmod"},
        ]:
            info = classify_kernel(k)
            self.assertTrue(len(info.type_desc) > 0, f"Empty type_desc for {k}")

    def test_full_desc_not_empty(self):
        for k in [
            {"name": "linux69"},
            {"name": "linux66-lts"},
            {"name": "linux-rt"},
            {"name": "linux-xanmod"},
        ]:
            info = classify_kernel(k)
            self.assertTrue(len(info.full_desc) > 0, f"Empty full_desc for {k}")

    def test_empty_dict(self):
        info = classify_kernel({})
        self.assertFalse(info.is_lts)
        self.assertFalse(info.is_rt)
        self.assertFalse(info.is_xanmod)

    def test_frozen_dataclass(self):
        info = classify_kernel({"name": "linux69"})
        with self.assertRaises(AttributeError):
            info.is_lts = True


# ------------------------------------------------------------------
# version_sort_key
# ------------------------------------------------------------------


class TestVersionSortKey(unittest.TestCase):
    """Tests for version_sort_key()."""

    def test_simple_version(self):
        self.assertEqual(version_sort_key({"version": "6.9.1-1"}), (6, 9, 1, 1))

    def test_two_part_version(self):
        self.assertEqual(version_sort_key({"version": "6.9"}), (6, 9))

    def test_no_version_key(self):
        self.assertEqual(version_sort_key({}), (0,))

    def test_no_numbers(self):
        self.assertEqual(version_sort_key({"version": "abc"}), (0,))

    def test_long_version_truncated_to_4(self):
        key = version_sort_key({"version": "1.2.3.4.5.6"})
        self.assertEqual(key, (1, 2, 3, 4))

    def test_sorting_order(self):
        kernels = [
            {"version": "6.6.50-1"},
            {"version": "6.9.1-1"},
            {"version": "6.1.100-1"},
            {"version": "6.11.2-1"},
        ]
        sorted_names = sorted(kernels, key=version_sort_key)
        versions = [k["version"] for k in sorted_names]
        self.assertEqual(
            versions,
            ["6.1.100-1", "6.6.50-1", "6.9.1-1", "6.11.2-1"],
        )

    def test_reverse_sorting(self):
        kernels = [
            {"version": "6.6.50-1"},
            {"version": "6.9.1-1"},
            {"version": "6.1.100-1"},
        ]
        sorted_k = sorted(kernels, key=version_sort_key, reverse=True)
        self.assertEqual(sorted_k[0]["version"], "6.9.1-1")
        self.assertEqual(sorted_k[-1]["version"], "6.1.100-1")


# ------------------------------------------------------------------
# _get_category_icon
# ------------------------------------------------------------------


class TestGetCategoryIcon(unittest.TestCase):
    """Tests for _get_category_icon from drivers_hub_page."""

    @classmethod
    def setUpClass(cls):
        from ui.drivers_hub_page import _get_category_icon

        cls._fn = staticmethod(_get_category_icon)

    def test_known_categories(self):
        known = {
            "video": "video-display-symbolic",
            "wifi": "network-wireless-symbolic",
            "bluetooth": "bluetooth-symbolic",
            "printer": "printer-symbolic",
            "scanner": "document-scan-symbolic",
        }
        for cat_id, expected_icon in known.items():
            self.assertEqual(self._fn(cat_id), expected_icon)

    def test_unknown_returns_fallback(self):
        self.assertEqual(
            self._fn("nonexistent_category"),
            "application-x-firmware-symbolic",
        )


# ------------------------------------------------------------------
# _MESA_HUMAN_NAMES
# ------------------------------------------------------------------


class TestMesaHumanNames(unittest.TestCase):
    """Tests for _MESA_HUMAN_NAMES mapping."""

    @classmethod
    def setUpClass(cls):
        from ui.mesa_data import _init_mesa_names, _MESA_HUMAN_NAMES

        _init_mesa_names()
        cls._names = _MESA_HUMAN_NAMES

    def test_stable_present(self):
        self.assertIn("stable", self._names)
        self.assertIn("title", self._names["stable"])
        self.assertIn("desc", self._names["stable"])

    def test_tkg_stable_present(self):
        self.assertIn("tkg-stable", self._names)

    def test_tkg_git_present(self):
        self.assertIn("tkg-git", self._names)

    def test_amber_present(self):
        self.assertIn("amber", self._names)

    def test_all_have_title_and_desc(self):
        for key, val in self._names.items():
            self.assertIn("title", val, f"Missing 'title' for {key}")
            self.assertIn("desc", val, f"Missing 'desc' for {key}")
            self.assertTrue(len(val["title"]) > 0)
            self.assertTrue(len(val["desc"]) > 0)


if __name__ == "__main__":
    unittest.main()
