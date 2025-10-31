"""
Tests for Supabase database configuration.

This module tests the Supabase connection string builder and configuration logic.
"""

import os
import unittest
from unittest.mock import patch

from app.supabase_config import (
    build_supabase_connection_string,
    extract_project_reference,
    get_supabase_connection_string,
)


class TestProjectReferenceExtraction(unittest.TestCase):
    """Test project reference extraction from Supabase URLs."""

    def test_extract_valid_project_reference(self):
        """Should extract project reference from valid Supabase URL."""
        url = "https://jlshmxtbrfckmqfpjboy.supabase.co"
        result = extract_project_reference(url)
        self.assertEqual(result, "jlshmxtbrfckmqfpjboy")

    def test_extract_from_different_project(self):
        """Should extract reference from different project URL."""
        url = "https://abc123xyz.supabase.co"
        result = extract_project_reference(url)
        self.assertEqual(result, "abc123xyz")

    def test_invalid_url_format(self):
        """Should return None for invalid URL format."""
        url = "https://example.com"
        result = extract_project_reference(url)
        self.assertIsNone(result)

    def test_missing_https(self):
        """Should return None when URL missing https."""
        url = "jlshmxtbrfckmqfpjboy.supabase.co"
        result = extract_project_reference(url)
        self.assertIsNone(result)


class TestConnectionStringBuilder(unittest.TestCase):
    """Test Supabase PostgreSQL connection string construction."""

    @patch.dict(
        os.environ,
        {
            "PROJECT_URL": "https://jlshmxtbrfckmqfpjboy.supabase.co",
            "DATABASE_PASSWORD": "u25NVZvZem3k7ftY",
        },
    )
    def test_build_valid_connection_string(self):
        """Should build valid PostgreSQL connection string."""
        result = build_supabase_connection_string()

        self.assertIsNotNone(result)
        self.assertIn("postgresql://", result)
        self.assertIn("jlshmxtbrfckmqfpjboy", result)
        self.assertIn("u25NVZvZem3k7ftY", result)
        self.assertIn("/postgres", result)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_project_url(self):
        """Should return None when PROJECT_URL is missing."""
        result = build_supabase_connection_string()
        self.assertIsNone(result)

    @patch.dict(os.environ, {"PROJECT_URL": "https://abc123.supabase.co"}, clear=True)
    def test_missing_password(self):
        """Should return None when DATABASE_PASSWORD is missing."""
        result = build_supabase_connection_string()
        self.assertIsNone(result)

    @patch.dict(
        os.environ,
        {
            "PROJECT_URL": "https://invalid-url.com",
            "DATABASE_PASSWORD": "password123",
        },
    )
    def test_invalid_project_url(self):
        """Should return None when PROJECT_URL format is invalid."""
        result = build_supabase_connection_string()
        self.assertIsNone(result)


class TestGetSupabaseConnectionString(unittest.TestCase):
    """Test wrapper function for getting Supabase connection string."""

    @patch.dict(
        os.environ,
        {
            "PROJECT_URL": "https://testproject.supabase.co",
            "DATABASE_PASSWORD": "testpass",
        },
    )
    def test_successful_connection_string(self):
        """Should return connection string when configuration is valid."""
        result = get_supabase_connection_string()

        self.assertIsNotNone(result)
        self.assertIn("postgresql://", result)
        self.assertIn("testproject", result)

    @patch.dict(os.environ, {}, clear=True)
    def test_handles_missing_configuration(self):
        """Should return None gracefully when configuration is missing."""
        result = get_supabase_connection_string()
        self.assertIsNone(result)

    @patch(
        "app.supabase_config.build_supabase_connection_string",
        side_effect=Exception("Test error"),
    )
    def test_handles_exceptions(self, mock_build):
        """Should return None and handle exceptions gracefully."""
        result = get_supabase_connection_string()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
