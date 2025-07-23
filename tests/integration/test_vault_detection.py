"""
Integration test cases for vault detection functionality.

These tests use real filesystem operations and the actual test data
to validate end-to-end behavior.
"""

from pathlib import Path

from src.domain.vault_analyzer import VaultAnalyzer
from src.infrastructure.file_system import FileSystemAdapter


class TestVaultDetectionIntegration:
    """Integration tests for vault detection using real filesystem."""

    def test_detect_real_obsidian_vault_in_test_data(self):
        """
        Test that the real Obsidian vault in test data is correctly detected.

        Uses the actual test vault at data/_obsidian/ for validation.
        """
        # Given: The real test vault path
        vault_path = Path("data/_obsidian")
        file_system = FileSystemAdapter()
        analyzer = VaultAnalyzer(file_system=file_system)

        # When: We check if it's a valid vault
        result = analyzer.is_valid_vault(vault_path)

        # Then: It should be detected as a valid vault
        assert result is True, f"Test vault at {vault_path} should be detected as valid"

        # And: The .obsidian directory should actually exist
        obsidian_dir = vault_path / ".obsidian"
        assert obsidian_dir.exists(), (
            f".obsidian directory should exist at {obsidian_dir}"
        )
        assert obsidian_dir.is_dir(), f"{obsidian_dir} should be a directory"
