"""File and URI loader utilities."""

import os
import logging
import requests
from pathlib import Path
from typing import Union, List
from urllib.parse import urlparse

from .exceptions import FileOperationError

logger = logging.getLogger(__name__)


def is_url(path: str) -> bool:
    """
    Check if a path is a URL.

    Args:
        path: Path or URL string

    Returns:
        True if it's a URL, False otherwise
    """
    try:
        result = urlparse(path)
        return all([result.scheme, result.netloc])
    except:
        return False


def load_content_from_uri(uri: str, timeout: int = 30) -> str:
    """
    Load content from URI (file path or URL).

    Args:
        uri: File path or HTTP(S) URL
        timeout: Timeout for HTTP requests (seconds)

    Returns:
        Content as string

    Raises:
        FileOperationError: If loading fails
    """
    logger.info(f"Loading content from URI: {uri}")

    # Handle URL
    if is_url(uri):
        try:
            response = requests.get(uri, timeout=timeout)
            response.raise_for_status()
            content = response.text
            logger.info(f"Successfully loaded {len(content)} characters from URL: {uri}")
            return content

        except requests.exceptions.Timeout:
            raise FileOperationError(f"Timeout loading URL: {uri}", file_path=uri)
        except requests.exceptions.RequestException as e:
            raise FileOperationError(f"Failed to load URL: {e}", file_path=uri)

    # Handle local file
    else:
        path = Path(uri)

        if not path.exists():
            raise FileOperationError(f"File not found: {uri}", file_path=uri)

        if not path.is_file():
            raise FileOperationError(f"Not a file: {uri}", file_path=uri)

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            logger.info(f"Successfully loaded {len(content)} characters from file: {uri}")
            return content

        except Exception as e:
            raise FileOperationError(f"Failed to read file: {e}", file_path=uri)


def load_multiple_prds(prd_uris: Union[str, List[str]]) -> List[dict]:
    """
    Load multiple PRD files from URIs.

    Args:
        prd_uris: Single URI or list of URIs (file paths or URLs)

    Returns:
        List of dicts with 'uri', 'name', and 'content'

    Raises:
        FileOperationError: If any PRD fails to load
    """
    if isinstance(prd_uris, str):
        prd_uris = [prd_uris]

    prds = []
    errors = []

    for uri in prd_uris:
        try:
            content = load_content_from_uri(uri)

            # Extract name from URI
            if is_url(uri):
                name = Path(urlparse(uri).path).stem or "remote_prd"
            else:
                name = Path(uri).stem

            prds.append({
                "uri": uri,
                "name": name,
                "content": content
            })

        except FileOperationError as e:
            error_msg = f"Failed to load PRD from {uri}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    if errors:
        raise FileOperationError(
            f"Failed to load {len(errors)} PRD(s):\n" + "\n".join(errors)
        )

    logger.info(f"Successfully loaded {len(prds)} PRD document(s)")
    return prds


def merge_prd_contents(prds: List[dict]) -> str:
    """
    Merge multiple PRD contents into a single document.

    Args:
        prds: List of PRD dicts with 'name' and 'content'

    Returns:
        Merged content string
    """
    if len(prds) == 1:
        return prds[0]["content"]

    # Merge with section headers
    sections = []
    for i, prd in enumerate(prds, 1):
        sections.append(f"## PRD {i}: {prd['name']}\n\n{prd['content']}\n")

    merged = "# 合并的PRD文档\n\n" + "\n".join(sections)

    logger.info(f"Merged {len(prds)} PRD documents into single content")
    return merged


def validate_markdown_file(content: str) -> bool:
    """
    Basic validation for markdown content.

    Args:
        content: Markdown content

    Returns:
        True if valid, False otherwise
    """
    if not content or not content.strip():
        return False

    # Check for basic markdown structure (at least one header or paragraph)
    lines = content.strip().split("\n")
    has_content = any(line.strip() for line in lines)

    return has_content
