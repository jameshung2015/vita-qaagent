"""File utilities for reading and writing test cases."""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def read_markdown_file(file_path: str) -> str:
    """
    Read markdown file content.

    Args:
        file_path: Path to markdown file

    Returns:
        File content as string
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_markdown_file(file_path: str, content: str) -> None:
    """
    Write content to markdown file.

    Args:
        file_path: Output file path
        content: Content to write
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"Markdown file written to: {file_path}")


def read_json_file(file_path: str) -> Dict[str, Any]:
    """
    Read JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON data
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json_file(file_path: str, data: Any, indent: int = 2) -> None:
    """
    Write data to JSON file.

    Args:
        file_path: Output file path
        data: Data to write
        indent: JSON indentation level
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)

    logger.info(f"JSON file written to: {file_path}")


def write_jsonl_file(file_path: str, records: List[Dict[str, Any]]) -> None:
    """
    Write records to JSONL file (one JSON object per line).

    Args:
        file_path: Output file path
        records: List of records to write
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info(f"JSONL file written to: {file_path} ({len(records)} records)")


def read_jsonl_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Read JSONL file.

    Args:
        file_path: Path to JSONL file

    Returns:
        List of parsed JSON objects
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    logger.info(f"Read {len(records)} records from: {file_path}")
    return records


def generate_output_filename(
    prefix: str,
    suffix: str,
    project_name: Optional[str] = None,
    use_timestamp: bool = True,
) -> str:
    """
    Generate output filename with optional project name and timestamp.

    Args:
        prefix: Filename prefix
        suffix: File extension (e.g., 'md', 'json', 'jsonl')
        project_name: Optional project name to include
        use_timestamp: Whether to include timestamp

    Returns:
        Generated filename
    """
    parts = []

    if project_name:
        parts.append(project_name)

    parts.append(prefix)

    if use_timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        parts.append(timestamp)

    filename = "_".join(parts) + f".{suffix}"
    return filename
