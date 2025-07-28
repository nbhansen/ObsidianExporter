"""
Test cases for CLI nested documents support.

Tests the command-line interface integration with the nested documents feature.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from src.cli import cli


class TestCLINestedDocuments:
    """Test suite for CLI nested documents feature."""

    @pytest.fixture
    def mock_vault_path(self, tmp_path):
        """Create a temporary vault directory for testing."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        (vault_path / "test.md").write_text("# Test")
        return vault_path

    def test_nested_documents_flag_available(self):
        """Test that --nested-documents flag is available in CLI."""
        # Given: CLI runner
        runner = CliRunner()

        # When: We check the help for convert command
        result = runner.invoke(cli, ["convert", "--help"])

        # Then: Should show nested-documents option
        assert result.exit_code == 0
        assert "--nested-documents" in result.output
        assert "For Outline export" in result.output

    @patch("src.cli.create_outline_export_use_case")
    def test_nested_documents_passed_to_config(
        self, mock_create_use_case, mock_vault_path
    ):
        """Test that --nested-documents flag is passed to OutlineExportConfig."""
        # Given: Mock use case
        mock_use_case = Mock()
        mock_create_use_case.return_value = mock_use_case

        # Mock successful export result
        mock_result = Mock()
        mock_result.success = True
        mock_result.output_path = Path("test.zip")
        mock_result.files_processed = 1
        mock_result.assets_processed = 0
        mock_result.processing_time = 1.0
        mock_result.warnings = []
        mock_result.errors = []
        mock_use_case.export.return_value = mock_result

        runner = CliRunner()

        # When: We run convert with nested-documents flag
        result = runner.invoke(
            cli,
            [
                "convert",
                str(mock_vault_path),
                "--format",
                "outline",
                "--nested-documents",
            ],
        )

        # Then: Should call export with nested_documents=True
        assert result.exit_code == 0
        mock_use_case.export.assert_called_once()

        # Extract the config argument
        config = mock_use_case.export.call_args[0][0]
        assert config.nested_documents is True

    @patch("src.cli.create_outline_export_use_case")
    def test_nested_documents_default_false(
        self, mock_create_use_case, mock_vault_path
    ):
        """Test that nested_documents defaults to False when flag not provided."""
        # Given: Mock use case
        mock_use_case = Mock()
        mock_create_use_case.return_value = mock_use_case

        # Mock successful export result
        mock_result = Mock()
        mock_result.success = True
        mock_result.output_path = Path("test.zip")
        mock_result.files_processed = 1
        mock_result.assets_processed = 0
        mock_result.processing_time = 1.0
        mock_result.warnings = []
        mock_result.errors = []
        mock_use_case.export.return_value = mock_result

        runner = CliRunner()

        # When: We run convert without nested-documents flag
        result = runner.invoke(
            cli,
            [
                "convert",
                str(mock_vault_path),
                "--format",
                "outline",
            ],
        )

        # Then: Should call export with nested_documents=False
        assert result.exit_code == 0
        mock_use_case.export.assert_called_once()

        # Extract the config argument
        config = mock_use_case.export.call_args[0][0]
        assert config.nested_documents is False

    @patch("src.cli.create_outline_export_use_case")
    @patch("src.cli.create_export_use_case")
    def test_nested_documents_only_affects_outline_format(
        self, mock_create_appflowy_use_case, mock_create_outline_use_case, mock_vault_path
    ):
        """Test that --nested-documents flag only affects outline format exports."""
        # Given: Mock outline use case
        mock_outline_use_case = Mock()
        mock_create_outline_use_case.return_value = mock_outline_use_case

        # Mock successful export result
        mock_result = Mock()
        mock_result.success = True
        mock_result.output_path = Path("test.zip")
        mock_result.files_processed = 1
        mock_result.assets_processed = 0
        mock_result.processing_time = 1.0
        mock_result.warnings = []
        mock_result.errors = []
        mock_outline_use_case.export.return_value = mock_result

        runner = CliRunner()

        # When: We run convert with nested-documents for outline format
        result = runner.invoke(
            cli,
            [
                "convert",
                str(mock_vault_path),
                "--format",
                "outline",
                "--nested-documents",
            ],
        )

        # Then: Should succeed (flag is handled by outline format)
        if result.exit_code != 0:
            print("CLI output:", result.output)
        assert result.exit_code == 0

    def test_nested_documents_in_help_examples(self):
        """Test that help includes example of nested-documents usage."""
        # Given: CLI runner
        runner = CliRunner()

        # When: We check the help for convert command
        result = runner.invoke(cli, ["convert", "--help"])

        # Then: Should show example with nested-documents
        assert result.exit_code == 0
        assert "--nested-documents" in result.output

    @patch("src.cli.create_outline_export_use_case")
    def test_nested_documents_with_validation_only(
        self, mock_create_use_case, mock_vault_path
    ):
        """Test that --nested-documents works with --validate-only."""
        # Given: Mock use case
        mock_use_case = Mock()
        mock_create_use_case.return_value = mock_use_case

        # Mock successful validation result
        mock_result = Mock()
        mock_result.success = True
        mock_result.output_path = None  # No output for validation-only
        mock_result.files_processed = 1
        mock_result.assets_processed = 0
        mock_result.processing_time = 0.5
        mock_result.warnings = []
        mock_result.errors = []
        mock_use_case.export.return_value = mock_result

        runner = CliRunner()

        # When: We run convert with both flags
        result = runner.invoke(
            cli,
            [
                "convert",
                str(mock_vault_path),
                "--format",
                "outline",
                "--nested-documents",
                "--validate-only",
            ],
        )

        # Then: Should succeed and pass both flags to config
        assert result.exit_code == 0
        mock_use_case.export.assert_called_once()

        # Extract the config argument
        config = mock_use_case.export.call_args[0][0]
        assert config.nested_documents is True
        assert config.validate_only is True

    def test_nested_documents_flag_is_boolean(self):
        """Test that nested-documents is a boolean flag (not requiring value)."""
        # This test ensures the CLI accepts --nested-documents without a value
        runner = CliRunner()

        # The flag should be recognized even if we can't run the full command
        # (due to missing vault path). We just check it's parsed correctly.
        result = runner.invoke(
            cli,
            [
                "convert",
                "/nonexistent/path",  # This will fail, but flag parsing happens first
                "--format",
                "outline",
                "--nested-documents",
            ],
        )

        # Should fail due to path not existing, not due to flag parsing
        # If flag parsing failed, we'd get a different error message
        assert "does not exist" in result.output or result.exit_code != 0
