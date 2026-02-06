"""Tests for enrich module."""

import unittest
from pathlib import Path

from src.enrich import _get_file_for_policy, load_policy_metadata

METADATA_DIR = Path("data/rl-scanner-metadata/data")


class TestGetFileForPolicy(unittest.TestCase):
    def test_known_prefixes(self):
        self.assertEqual(_get_file_for_policy("SQ31102"), "vulnerabilities.json")
        self.assertEqual(_get_file_for_policy("SQ34101"), "secrets.json")
        self.assertEqual(_get_file_for_policy("SQ12001"), "licenses.json")
        self.assertEqual(_get_file_for_policy("TH001"), "hunting.json")

    def test_unknown_prefix(self):
        self.assertIsNone(_get_file_for_policy("XX99999"))


class TestLoadPolicyMetadata(unittest.TestCase):
    def test_load_known_policy(self):
        result = load_policy_metadata(["SQ31102"], METADATA_DIR)
        self.assertIn("SQ31102", result)
        self.assertIn("label", result["SQ31102"])
        self.assertIn("description", result["SQ31102"])
        self.assertIn("steps", result["SQ31102"])
        self.assertIsInstance(result["SQ31102"]["steps"], list)

    def test_unknown_policy_returns_empty(self):
        result = load_policy_metadata(["XX99999"], METADATA_DIR)
        self.assertEqual(result, {})

    def test_missing_file_handled(self):
        result = load_policy_metadata(["SQ31102"], Path("/nonexistent/path"))
        self.assertEqual(result, {})

    def test_multiple_policies(self):
        result = load_policy_metadata(["SQ31102", "SQ34101"], METADATA_DIR)
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
