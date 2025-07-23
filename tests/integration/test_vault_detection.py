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

    def test_scan_real_obsidian_vault_finds_files(self):
        """
        Test that scanning real Obsidian vault finds markdown and asset files.

        Uses the actual test vault at data/_obsidian/ for end-to-end validation.
        """
        # Given: The real test vault path
        vault_path = Path("data/_obsidian")
        file_system = FileSystemAdapter()
        analyzer = VaultAnalyzer(file_system=file_system)

        # When: We scan the real vault
        result = analyzer.scan_vault(vault_path)

        # Then: It should find markdown files
        assert len(result.markdown_files) > 0, (
            "Should find markdown files in test vault"
        )
        assert result.path == vault_path

        # And: All found files should actually exist and be markdown
        for md_file in result.markdown_files:
            assert md_file.exists(), f"Markdown file {md_file} should exist"
            assert md_file.suffix.lower() == ".md", f"File {md_file} should be markdown"

        # And: Should find some asset files (images, etc.)
        assert len(result.asset_files) > 0, "Should find asset files in test vault"

        # And: All asset files should exist
        for asset_file in result.asset_files:
            assert asset_file.exists(), f"Asset file {asset_file} should exist"
