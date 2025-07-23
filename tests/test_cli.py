"""
Test cases for CLI interface.

Following TDD approach - these tests define the expected behavior
for the Click-based command-line interface.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from src.application.export_use_case import ExportResult
from src.cli import cli, convert_command


class TestCLI:
    """Test suite for CLI interface following TDD methodology."""

    def test_cli_help(self):
        """
        Test CLI help output.

        Should display help information and available commands.
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "convert" in result.output.lower()
        assert "appflowy" in result.output.lower()

    def test_convert_command_help(self):
        """
        Test convert command help output.

        Should display convert command options and usage.
        """
        runner = CliRunner()
        result = runner.invoke(convert_command, ["--help"])

        assert result.exit_code == 0
        assert "vault_path" in result.output.lower()
        assert "output" in result.output.lower()
        assert "verbose" in result.output.lower()

    @patch("src.cli.create_export_use_case")
    def test_convert_command_success(self, mock_create_use_case):
        """
        Test successful vault conversion via CLI.

        Should execute conversion and display success message.
        """
        # Mock the export use case
        mock_use_case = Mock()
        mock_create_use_case.return_value = mock_use_case

        # Mock successful export result
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "export.zip"
            mock_result = ExportResult(
                success=True,
                output_path=output_path,
                files_processed=5,
                assets_processed=2,
                warnings=["Sample warning"],
                errors=[],
                processing_time=1.5,
            )
            mock_use_case.export_vault.return_value = mock_result

            runner = CliRunner()
            with tempfile.TemporaryDirectory() as vault_dir:
                result = runner.invoke(convert_command, [
                    vault_dir,
                    "--output", str(output_path),
                    "--name", "Test Export"
                ])

                assert result.exit_code == 0
                assert "success" in result.output.lower()
                assert "files processed: 5" in result.output.lower()
                assert "1 warning" in result.output.lower()

    @patch("src.cli.create_export_use_case")
    def test_convert_command_with_errors(self, mock_create_use_case):
        """
        Test conversion with errors via CLI.

        Should display error information and return error exit code.
        """
        # Mock the export use case
        mock_use_case = Mock()
        mock_create_use_case.return_value = mock_use_case

        # Mock failed export result
        mock_result = ExportResult(
            success=False,
            files_processed=3,
            warnings=["Warning 1"],
            errors=["Error 1", "Error 2"],
            processing_time=0.5,
        )
        mock_use_case.export_vault.return_value = mock_result

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as vault_dir:
            result = runner.invoke(convert_command, [
                vault_dir,
                "--output", "/tmp/export.zip"
            ])

            assert result.exit_code != 0
            assert "failed" in result.output.lower() or "error" in result.output.lower()
            assert "2 errors" in result.output.lower()

    @patch("src.cli.create_export_use_case")
    def test_convert_command_verbose_mode(self, mock_create_use_case):
        """
        Test conversion with verbose output.

        Should display detailed progress information.
        """
        # Mock the export use case
        mock_use_case = Mock()
        mock_create_use_case.return_value = mock_use_case

        # Mock successful export with progress reporting
        mock_result = ExportResult(
            success=True,
            output_path=Path("/tmp/export.zip"),
            files_processed=2,
            processing_time=1.0,
        )
        mock_use_case.export_vault.return_value = mock_result

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as vault_dir:
            result = runner.invoke(convert_command, [
                vault_dir,
                "--output", "/tmp/export.zip",
                "--verbose"
            ])

            assert result.exit_code == 0
            # Should capture progress messages from the progress callback
            mock_use_case.export_vault.assert_called_once()
            call_args = mock_use_case.export_vault.call_args[0][0]
            assert call_args.progress_callback is not None

    @patch("src.cli.create_export_use_case")
    def test_convert_command_validate_only(self, mock_create_use_case):
        """
        Test validation-only mode via CLI.

        Should run validation without creating package.
        """
        # Mock the export use case
        mock_use_case = Mock()
        mock_create_use_case.return_value = mock_use_case

        # Mock validation result
        mock_result = ExportResult(
            success=True,
            output_path=None,  # No package created
            files_processed=0,
            broken_links=["note1 → missing-note", "note2 → broken-link"],
            processing_time=0.2,
        )
        mock_use_case.export_vault.return_value = mock_result

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as vault_dir:
            result = runner.invoke(convert_command, [
                vault_dir,
                "--validate-only"
            ])

            assert result.exit_code == 0
            assert "validation" in result.output.lower()
            assert "2 broken links" in result.output.lower()
            assert "package" not in result.output.lower()  # No package created

    def test_convert_command_missing_vault(self):
        """
        Test conversion with non-existent vault path.

        Should display error message and return error exit code.
        """
        runner = CliRunner()
        result = runner.invoke(convert_command, [
            "/nonexistent/vault/path",
            "--output", "/tmp/export.zip"
        ])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "does not exist" in result.output.lower()

    @patch("src.cli.create_export_use_case")
    def test_convert_command_with_custom_output_name(self, mock_create_use_case):
        """
        Test conversion with custom package name.

        Should pass package name to export use case.
        """
        # Mock the export use case
        mock_use_case = Mock()
        mock_create_use_case.return_value = mock_use_case

        mock_result = ExportResult(success=True, output_path=Path("/tmp/custom.zip"))
        mock_use_case.export_vault.return_value = mock_result

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as vault_dir:
            result = runner.invoke(convert_command, [
                vault_dir,
                "--output", "/tmp/custom.zip",
                "--name", "My Custom Export"
            ])

            assert result.exit_code == 0
            mock_use_case.export_vault.assert_called_once()
            call_config = mock_use_case.export_vault.call_args[0][0]
            assert call_config.package_name == "My Custom Export"

    @patch("src.cli.create_export_use_case")
    def test_progress_reporting_callback(self, mock_create_use_case):
        """
        Test progress reporting callback functionality.

        Should display progress messages in verbose mode.
        """
        # Mock the export use case
        mock_use_case = Mock()
        mock_create_use_case.return_value = mock_use_case

        # Create a side effect that calls the progress callback
        def mock_export_vault(config):
            if config.progress_callback:
                config.progress_callback("Scanning vault structure...")
                config.progress_callback("Processing file1.md...")
                config.progress_callback("Creating package...")
            return ExportResult(success=True, output_path=Path("/tmp/export.zip"))

        mock_use_case.export_vault.side_effect = mock_export_vault

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as vault_dir:
            result = runner.invoke(convert_command, [
                vault_dir,
                "--output", "/tmp/export.zip",
                "--verbose"
            ])

            assert result.exit_code == 0
            assert "Scanning vault" in result.output
            assert "Processing file1.md" in result.output
            assert "Creating package" in result.output

    def test_convert_command_output_path_validation(self):
        """
        Test output path validation.

        Should validate output directory exists and create if needed.
        """
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as vault_dir:
            # Test with non-existent output directory
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = Path(temp_dir) / "subdir" / "export.zip"

                # Should work - directory should be created
                with patch("src.cli.create_export_use_case") as mock_create:
                    mock_use_case = Mock()
                    mock_create.return_value = mock_use_case
                    mock_use_case.export_vault.return_value = ExportResult(
                        success=True, output_path=output_path
                    )

                    result = runner.invoke(convert_command, [
                        vault_dir,
                        "--output", str(output_path)
                    ])

                    # Should succeed
                    assert result.exit_code == 0

    def test_error_handling_and_formatting(self):
        """
        Test error message formatting and handling.

        Should display user-friendly error messages.
        """
        runner = CliRunner()

        # Test with invalid arguments
        result = runner.invoke(convert_command, [])
        assert result.exit_code != 0
        assert "missing" in result.output.lower() or "required" in result.output.lower()

    @patch("src.cli.create_export_use_case")
    def test_export_summary_formatting(self, mock_create_use_case):
        """
        Test export summary formatting.

        Should display comprehensive export statistics.
        """
        # Mock the export use case
        mock_use_case = Mock()
        mock_create_use_case.return_value = mock_use_case

        # Mock detailed export result
        mock_result = ExportResult(
            success=True,
            output_path=Path("/tmp/detailed-export.zip"),
            files_processed=10,
            assets_processed=5,
            warnings=["Warning 1", "Warning 2", "Warning 3"],
            errors=[],
            broken_links=["note1 → missing"],
            processing_time=2.5,
            vault_info={"total_files": 12, "total_assets": 6, "total_links": 25},
        )
        mock_use_case.export_vault.return_value = mock_result

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as vault_dir:
            result = runner.invoke(convert_command, [
                vault_dir,
                "--output", "/tmp/detailed-export.zip"
            ])

            assert result.exit_code == 0
            assert "Files processed: 10" in result.output
            assert "Assets processed: 5" in result.output
            assert "3 warnings" in result.output
            assert "2.5" in result.output  # Processing time
            assert "1 broken link" in result.output

