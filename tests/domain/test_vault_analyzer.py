"""
Test cases for vault analysis functionality.

Following TDD approach - these tests define the expected behavior
before implementation.
"""

from pathlib import Path
from unittest.mock import Mock

from src.domain.vault_analyzer import VaultAnalyzer


class TestVaultAnalyzer:
    """Test suite for VaultAnalyzer following hexagonal architecture."""

    def test_detect_valid_obsidian_vault_with_obsidian_directory(self):
        """
        Test that a directory with .obsidian/ subdirectory is detected as valid vault.

        This is the primary indicator of an Obsidian vault.
        """
        # Given: A path that contains .obsidian directory
        vault_path = Path("/fake/vault/path")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = True

        analyzer = VaultAnalyzer(file_system=mock_file_system)

        # When: We check if it's a valid vault
        result = analyzer.is_valid_vault(vault_path)

        # Then: It should be detected as a valid vault
        assert result is True
        mock_file_system.directory_exists.assert_called_once_with(
            vault_path / ".obsidian"
        )

    def test_detect_invalid_vault_without_obsidian_directory(self):
        """
        Test that a directory without .obsidian/ subdirectory is not a valid vault.
        """
        # Given: A path that does not contain .obsidian directory
        vault_path = Path("/fake/regular/directory")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = False

        analyzer = VaultAnalyzer(file_system=mock_file_system)

        # When: We check if it's a valid vault
        result = analyzer.is_valid_vault(vault_path)

        # Then: It should not be detected as a valid vault
        assert result is False
        mock_file_system.directory_exists.assert_called_once_with(
            vault_path / ".obsidian"
        )

    def test_detect_invalid_vault_when_path_does_not_exist(self):
        """
        Test that a non-existent path is not detected as a valid vault.
        """
        # Given: A path that does not exist
        vault_path = Path("/nonexistent/path")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = False

        analyzer = VaultAnalyzer(file_system=mock_file_system)

        # When: We check if it's a valid vault
        result = analyzer.is_valid_vault(vault_path)

        # Then: It should not be detected as a valid vault
        assert result is False
