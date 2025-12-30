"""Unit tests for file utilities."""

import pytest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from src.utils.file_utils import (
    read_markdown_file,
    write_markdown_file,
    read_json_file,
    write_json_file,
    read_jsonl_file,
    write_jsonl_file,
    generate_output_filename,
)


class TestFileUtils:
    """Test file utilities."""

    def test_markdown_read_write(self):
        """Test reading and writing markdown files."""
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.md"
            content = "# Test\n\nThis is a test."

            write_markdown_file(str(file_path), content)
            read_content = read_markdown_file(str(file_path))

            assert read_content == content

    def test_json_read_write(self):
        """Test reading and writing JSON files."""
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.json"
            data = {"key": "value", "number": 42}

            write_json_file(str(file_path), data)
            read_data = read_json_file(str(file_path))

            assert read_data == data

    def test_jsonl_read_write(self):
        """Test reading and writing JSONL files."""
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.jsonl"
            records = [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ]

            write_jsonl_file(str(file_path), records)
            read_records = read_jsonl_file(str(file_path))

            assert read_records == records

    def test_generate_output_filename(self):
        """Test filename generation."""
        # Without timestamp
        filename = generate_output_filename(
            prefix="test",
            suffix="json",
            project_name="myproject",
            use_timestamp=False,
        )
        assert filename == "myproject_test.json"

        # With timestamp
        filename = generate_output_filename(
            prefix="test",
            suffix="md",
            project_name="proj",
            use_timestamp=True,
        )
        assert filename.startswith("proj_test_")
        assert filename.endswith(".md")

    def test_read_nonexistent_file(self):
        """Test reading nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            read_markdown_file("/nonexistent/file.md")
