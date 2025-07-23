"""
Test cases for file system infrastructure.

These integration tests validate the file system adapter
using real filesystem operations.
"""

import tempfile
from pathlib import Path

from src.infrastructure.file_system import FileSystemAdapter


class TestFileSystemAdapter:
    """Integration tests for FileSystemAdapter."""

    def test_directory_exists_returns_true_for_existing_directory(self):
        """Test that directory_exists returns True for an existing directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = FileSystemAdapter()
            result = adapter.directory_exists(Path(temp_dir))
            assert result is True

    def test_directory_exists_returns_false_for_nonexistent_directory(self):
        """Test that directory_exists returns False for a non-existent directory."""
        adapter = FileSystemAdapter()
        result = adapter.directory_exists(Path("/nonexistent/directory"))
        assert result is False

    def test_directory_exists_returns_false_for_file(self):
        """Test that directory_exists returns False when path points to a file."""
        with tempfile.NamedTemporaryFile() as temp_file:
            adapter = FileSystemAdapter()
            result = adapter.directory_exists(Path(temp_file.name))
            assert result is False

    def test_file_exists_returns_true_for_existing_file(self):
        """Test that file_exists returns True for an existing file."""
        with tempfile.NamedTemporaryFile() as temp_file:
            adapter = FileSystemAdapter()
            result = adapter.file_exists(Path(temp_file.name))
            assert result is True

    def test_file_exists_returns_false_for_nonexistent_file(self):
        """Test that file_exists returns False for a non-existent file."""
        adapter = FileSystemAdapter()
        result = adapter.file_exists(Path("/nonexistent/file.txt"))
        assert result is False

    def test_file_exists_returns_false_for_directory(self):
        """Test that file_exists returns False when path points to a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = FileSystemAdapter()
            result = adapter.file_exists(Path(temp_dir))
            assert result is False

    def test_list_files_returns_empty_for_nonexistent_directory(self):
        """Test that list_files returns empty list for non-existent directory."""
        adapter = FileSystemAdapter()
        result = adapter.list_files(Path("/nonexistent/directory"))
        assert result == []

    def test_list_files_returns_files_in_directory(self):
        """Test that list_files returns files in an existing directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "file1.txt").touch()
            (temp_path / "file2.md").touch()
            (temp_path / "subdir").mkdir()

            adapter = FileSystemAdapter()
            result = adapter.list_files(temp_path)

            # Should return all items (files and directories)
            assert len(result) == 3
            assert any(f.name == "file1.txt" for f in result)
            assert any(f.name == "file2.md" for f in result)
            assert any(f.name == "subdir" for f in result)

    def test_list_files_with_pattern_filters_correctly(self):
        """Test that list_files respects the pattern parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "file1.txt").touch()
            (temp_path / "file2.md").touch()
            (temp_path / "document.md").touch()

            adapter = FileSystemAdapter()
            result = adapter.list_files(temp_path, "*.md")

            # Should return only .md files
            assert len(result) == 2
            assert all(f.suffix == ".md" for f in result)
