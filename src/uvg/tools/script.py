"""PEP 723 script metadata parsing.

Parses inline metadata from Python scripts as defined in PEP 723.
Scripts can declare dependencies inline using a special comment block.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ScriptMetadata:
    """Metadata from a PEP 723 script."""

    dependencies: list[str] = field(default_factory=list)
    requires_python: str | None = None
    description: str | None = None
    authors: list[dict[str, str]] = field(default_factory=list)
    license_text: str | None = None
    raw_metadata: str = ""

    @property
    def has_dependencies(self) -> bool:
        """Check if the script has dependencies."""
        return len(self.dependencies) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {}
        if self.dependencies:
            result["dependencies"] = self.dependencies
        if self.requires_python:
            result["requires-python"] = self.requires_python
        if self.description:
            result["description"] = self.description
        if self.authors:
            result["authors"] = self.authors
        if self.license_text:
            result["license"] = self.license_text
        return result


class ScriptParser:
    """Parses PEP 723 script metadata."""

    METADATA_START = "# /// script"
    METADATA_END = "# ///"

    def parse(self, script_path: Path) -> ScriptMetadata:
        """Parse metadata from a Python script.

        Args:
            script_path: Path to the script file.

        Returns:
            ScriptMetadata instance.

        Raises:
            FileNotFoundError: If script does not exist.
        """
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")

        content = script_path.read_text(encoding="utf-8")
        return self.parse_content(content)

    def parse_content(self, content: str) -> ScriptMetadata:
        """Parse metadata from script content.

        Args:
            content: Script content.

        Returns:
            ScriptMetadata instance.
        """
        metadata = self._extract_metadata(content)
        if not metadata:
            return ScriptMetadata()

        return self._parse_metadata_block(metadata)

    def _extract_metadata(self, content: str) -> str | None:
        """Extract the metadata block from script content.

        Args:
            content: Script content.

        Returns:
            Metadata block string or None.
        """
        lines = content.splitlines()
        in_metadata = False
        metadata_lines: list[str] = []

        for line in lines:
            if line.strip() == self.METADATA_START:
                in_metadata = True
                continue
            if line.strip() == self.METADATA_END:
                if in_metadata:
                    return "\n".join(metadata_lines)
                break
            if in_metadata:
                if line.startswith("# "):
                    metadata_lines.append(line[2:])
                elif line == "#":
                    metadata_lines.append("")
                else:
                    in_metadata = False
                    metadata_lines = []

        return None

    def _parse_metadata_block(self, block: str) -> ScriptMetadata:
        """Parse a TOML metadata block.

        Args:
            block: TOML metadata block.

        Returns:
            ScriptMetadata instance.
        """
        metadata = ScriptMetadata(raw_metadata=block)
        current_list: str | None = None
        in_array = False

        for line in block.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("dependencies"):
                current_list = "dependencies"
                if "[" in line and "]" in line:
                    deps = self._parse_inline_array(line)
                    metadata.dependencies = deps
                    current_list = None
                elif "[" in line:
                    in_array = True
                    deps = self._parse_inline_array(line)
                    metadata.dependencies = deps
                continue

            if current_list == "dependencies" and in_array:
                if "]" in line:
                    in_array = False
                    line = line.rstrip("]").strip()
                if line.startswith('"'):
                    dep = line.strip('", ')
                    if dep:
                        metadata.dependencies.append(dep)
                continue

            if line.startswith("requires-python"):
                metadata.requires_python = self._parse_string_value(line)
                current_list = None
                in_array = False
                continue

            if line.startswith("description"):
                metadata.description = self._parse_string_value(line)
                current_list = None
                in_array = False
                continue

        return metadata

    def _parse_inline_array(self, line: str) -> list[str]:
        """Parse an inline TOML array.

        Args:
            line: Line containing an array.

        Returns:
            List of strings.
        """
        match = re.search(r"\[(.*)\]", line)
        if not match:
            return []

        content = match.group(1)
        items = []
        for item in content.split(","):
            item = item.strip().strip('"').strip("'")
            if item:
                items.append(item)
        return items

    def _parse_string_value(self, line: str) -> str | None:
        """Parse a TOML string value.

        Args:
            line: Line containing a string value.

        Returns:
            String value or None.
        """
        match = re.search(r'=\s*"([^"]*)"', line)
        if match:
            return match.group(1)
        return None


def parse_script(script_path: Path) -> ScriptMetadata:
    """Parse metadata from a PEP 723 script.

    Args:
        script_path: Path to the script file.

    Returns:
        ScriptMetadata instance.
    """
    parser = ScriptParser()
    return parser.parse(script_path)
