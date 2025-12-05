"""Lightweight text extraction using only standard library.

This is a fallback for when the full get_text.py dependencies are not available.
Supports basic file reading and URL fetching without external dependencies
(except urllib which is stdlib).
"""

import os
import re
from typing import Optional
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser


def get_text(source: str) -> str:
    """Extract text from a file or URL using only stdlib.

    This is a simplified version that handles:
    - Plain text files
    - URLs (basic HTTP/HTTPS fetching)
    - Directory listings

    Args:
        source: File path or URL to extract text from

    Returns:
        Extracted text content, or error message
    """
    # Check if it's a URL
    if source.startswith(('http://', 'https://')):
        return _handle_url(source)

    # Check if it's a directory
    if os.path.isdir(source):
        return _handle_directory(source)

    # Handle as file
    return _handle_file(source)


def _handle_file(path: str) -> str:
    """Read a text file from disk.

    Args:
        path: Path to file

    Returns:
        File contents or error message
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"File not found: {path}"
    except PermissionError:
        return f"Permission denied: {path}"
    except UnicodeDecodeError:
        # Try binary mode for non-text files
        return f"Binary file (cannot read as text): {path}"
    except Exception as e:
        return f"Error reading file: {e}"


def _handle_directory(path: str) -> str:
    """List directory contents.

    Args:
        path: Path to directory

    Returns:
        Directory listing as text
    """
    try:
        entries = os.listdir(path)
        if not entries:
            return f"{path}/\n(empty directory)"

        lines = [f"{path}/"]
        for entry in sorted(entries):
            full_path = os.path.join(path, entry)
            if os.path.isdir(full_path):
                lines.append(f"  {entry}/")
            else:
                lines.append(f"  {entry}")

        return '\n'.join(lines)
    except PermissionError:
        return f"Permission denied: {path}"
    except Exception as e:
        return f"Error listing directory: {e}"


class _HTMLTextExtractor(HTMLParser):
    """Simple HTML parser to extract text content using stdlib only."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip_tags = {'script', 'style', 'head', 'meta', 'link'}
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag

    def handle_endtag(self, tag):
        self.current_tag = None

    def handle_data(self, data):
        if self.current_tag not in self.skip_tags:
            text = data.strip()
            if text:
                self.text_parts.append(text)

    def get_text(self):
        return '\n'.join(self.text_parts)


def _strip_html(html_content: str) -> str:
    """Strip HTML tags and extract text content.

    Args:
        html_content: HTML content as string

    Returns:
        Plain text content
    """
    try:
        parser = _HTMLTextExtractor()
        parser.feed(html_content)
        text = parser.get_text()

        # Clean up excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text if text else html_content  # Fallback to raw if parsing fails
    except Exception:
        # If parsing fails, return raw content
        return html_content


def _handle_url(url: str) -> str:
    """Fetch content from a URL and extract text.

    Args:
        url: URL to fetch

    Returns:
        URL content as text or error message
    """
    try:
        with urlopen(url, timeout=30) as response:
            # Read content
            content = response.read()

            # Try to decode as text
            try:
                html = content.decode('utf-8')
            except UnicodeDecodeError:
                # Try other common encodings
                for encoding in ['latin-1', 'iso-8859-1', 'windows-1252']:
                    try:
                        html = content.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    return f"Binary content (cannot decode as text): {url}"

            # Strip HTML tags if it looks like HTML
            if '<html' in html.lower() or '<body' in html.lower():
                return _strip_html(html)
            else:
                # Plain text content
                return html

    except HTTPError as e:
        return f"HTTP Error {e.code}: {url}"
    except URLError as e:
        return f"URL Error: {e.reason}"
    except TimeoutError:
        return f"Request timed out: {url}"
    except Exception as e:
        return f"Error fetching URL: {e}"
