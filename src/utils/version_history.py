"""Semantic versioning workflow with changelog automation.

This module provides the :class:`SemanticVersion` class for managing
project versions according to SemVer 2.0 specification, along with
the :class:`ChangelogManager` class for automated changelog generation
from git commit messages.

Key features:
- Full SemVer 2.0 compliance with prerelease tags
- Version comparison operators (__eq__, __lt__, __le__, __gt__, __ge__)
- Automated changelog generation from git commits
- Category-based version increment (MAJOR.MINOR.PATCH)
"""

from __future__ import annotations

import os
import re
import json
import subprocess
from typing import Optional, List, Tuple


class SemanticVersion:
    """Semantic versioning (SemVer 2.0) implementation.

    This class provides full SemVer 2.0 support with comparison operators,
    hashability, and string formatting. It supports prerelease tags and
    build metadata as specified in the SemVer specification.

    Parameters
    ----------
    major : int, default=0
        Major version number (breaking changes).
    minor : int, default=0
        Minor version number (new features, backwards compatible).
    patch : int, default=0
        Patch version number (bug fixes, backwards compatible).
    prerelease : str, optional
        Prerelease tag (e.g., "alpha", "beta", "rc1").
    build_metadata : str, optional
        Build metadata (ignored in comparison).

    Examples
    --------
    >>> v1 = SemanticVersion(0, 1, 0)
    >>> v2 = SemanticVersion(0, 2, 0)
    >>> v1 < v2
    True
    >>> v3 = SemanticVersion(1, 0, 0, prerelease="alpha")
    >>> str(v3)
    '1.0.0-alpha'
    """

    def __init__(
        self,
        major: int = 0,
        minor: int = 0,
        patch: int = 0,
        prerelease: Optional[str] = None,
        build_metadata: Optional[str] = None,
    ) -> None:
        """Initialise a semantic version."""
        self.major = major
        self.minor = minor
        self.patch = patch
        self.prerelease = prerelease
        self.build_metadata = build_metadata

    def __str__(self) -> str:
        """Return the version as a string in SemVer format.

        Returns
        -------
        str
            Version string (e.g., "1.2.3-alpha" or "1.2.3+build.123").
        """
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build_metadata:
            version += f"+{self.build_metadata}"
        return version

    def __repr__(self) -> str:
        """Return the version as a constructor call."""
        parts = [str(x) for x in (self.major, self.minor, self.patch)]
        if self.prerelease:
            parts.append(f"prerelease='{self.prerelease}'")
        if self.build_metadata:
            parts.append(f"build_metadata='{self.build_metadata}'")
        return f"SemanticVersion({', '.join(parts)})"

    def __eq__(self, other) -> bool:
        """Check equality between two versions.

        Parameters
        ----------
        other : SemanticVersion or str
            Version to compare against.

        Returns
        -------
        bool
            True if the versions are equal.
        """
        if isinstance(other, str):
            other = SemanticVersion.from_string(other)

        if not isinstance(other, SemanticVersion):
            return NotImplemented

        # Compare core version (ignore build metadata for equality)
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.prerelease == other.prerelease
        )

    def __lt__(self, other) -> bool:
        """Check if this version is less than another.

        Parameters
        ----------
        other : SemanticVersion or str
            Version to compare against.

        Returns
        -------
        bool
            True if this version is less than other.
        """
        if isinstance(other, str):
            other = SemanticVersion.from_string(other)

        if not isinstance(other, SemanticVersion):
            return NotImplemented

        # Compare major.minor.patch
        if (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch):
            return True

        # Handle prerelease: no prerelease > has prerelease
        if self.prerelease is None and other.prerelease is not None:
            return False
        if self.prerelease is not None and other.prerelease is None:
            return True

        # Compare prerelease strings
        if self.prerelease != other.prerelease:
            return self.prerelease < other.prerelease

        return False

    def __le__(self, other) -> bool:
        """Check if this version is less than or equal to another."""
        return self == other or self < other

    def __gt__(self, other) -> bool:
        """Check if this version is greater than another."""
        return not self <= other

    def __ge__(self, other) -> bool:
        """Check if this version is greater than or equal to another."""
        return not self < other

    def __hash__(self) -> int:
        """Return hash value for use in dictionaries and sets.

        Returns
        -------
        int
            Hash of the core version tuple.
        """
        return hash((self.major, self.minor, self.patch, self.prerelease))

    def increment_major(self) -> "SemanticVersion":
        """Increment the major version number.

        Returns
        -------
        SemanticVersion
            New version with incremented major number and reset minor/patch.
        """
        return SemanticVersion(
            major=self.major + 1,
            minor=0,
            patch=0,
            prerelease=None,
            build_metadata=self.build_metadata,
        )

    def increment_minor(self) -> "SemanticVersion":
        """Increment the minor version number.

        Returns
        -------
        SemanticVersion
            New version with incremented minor number and reset patch.
        """
        return SemanticVersion(
            major=self.major,
            minor=self.minor + 1,
            patch=0,
            prerelease=None,
            build_metadata=self.build_metadata,
        )

    def increment_patch(self) -> "SemanticVersion":
        """Increment the patch version number.

        Returns
        -------
        SemanticVersion
            New version with incremented patch number.
        """
        return SemanticVersion(
            major=self.major,
            minor=self.minor,
            patch=self.patch + 1,
            prerelease=None,
            build_metadata=self.build_metadata,
        )

    def set_prerelease(self, tag: str) -> "SemanticVersion":
        """Set the prerelease tag.

        Parameters
        ----------
        tag : str
            Prerelease tag (e.g., "alpha", "beta", "rc1").

        Returns
        -------
        SemanticVersion
            New version with the specified prerelease tag.
        """
        return SemanticVersion(
            major=self.major,
            minor=self.minor,
            patch=self.patch,
            prerelease=tag,
            build_metadata=self.build_metadata,
        )

    @staticmethod
    def from_string(version_str: str) -> "SemanticVersion":
        """Parse a version string into a SemanticVersion object.

        Parameters
        ----------
        version_str : str
            Version string in SemVer format (e.g., "1.2.3-alpha+build.123").

        Returns
        -------
        SemanticVersion
            Parsed version object.

        Raises
        ------
        ValueError
            If the version string does not match SemVer format.
        """
        # SemVer regex pattern
        pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9]+))?(?:\+(.+))?$"
        match = re.match(pattern, version_str)

        if not match:
            raise ValueError(f"Invalid SemVer string: {version_str}")

        major, minor, patch, prerelease, build_metadata = match.groups()

        return SemanticVersion(
            major=int(major),
            minor=int(minor),
            patch=int(patch),
            prerelease=prerelease or None,
            build_metadata=build_metadata or None,
        )


class ChangelogManager:
    """Manage changelog entries and automated generation.

    This class provides methods for managing the project changelog,
    including adding entries, generating sections by category, and
    saving formatted changelog files.

    Parameters
    ----------
    changelog_path : str, default="CHANGELOG.md"
        Path to the changelog file.
    """

    def __init__(self, changelog_path: str = "CHANGELOG.md") -> None:
        """Initialise the changelog manager."""
        self.changelog_path = changelog_path
        self.entries: List[dict] = []

    # -------------------------------------------------------------------
    # Entry management
#    ----------------------------------------------------------------

    def add_entry(
        self,
        category: str,
        description: str,
        version: Optional[str] = None,
    ) -> None:
        """Add a changelog entry.

        Parameters
        ----------
        category : str
            Entry category: "feat", "fix", "docs", "perf", "refactor", "test".
        description : str
            Description of the change.
        version : str, optional
            Version this entry applies to. If None, uses current version.

        Raises
        ------
        ValueError
            If the category is not one of the allowed values.
        """
        valid_categories = {"feat", "fix", "docs", "perf", "refactor", "test"}
        if category not in valid_categories:
            raise ValueError(
                f"Invalid category: {category}. Allowed: {valid_categories}"
            )

        self.entries.append({
            "category": category,
            "description": description,
            "version": version or "0.1.0",
            "timestamp": _get_current_timestamp(),
        })

    def generate_section(self, version: str) -> str:
        """Generate a changelog section for a specific version.

        Parameters
        ----------
        version : str
            Version string to generate the section for.

        Returns
        -------
        str
            Formatted markdown section for this version.
        """
        # Filter entries for this version
        version_entries = [e for e in self.entries if e["version"] == version]

        if not version_entries:
            return f"## [{version}] - {_get_current_date()}\n\nNo changes recorded.\n"

        # Group by category
        categories = {}
        for entry in version_entries:
            cat = entry["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(entry)

        # Generate markdown
        lines = [f"## [{version}] - {_get_current_date()}"]

        category_labels = {
            "feat": "Features",
            "fix": "Bug Fixes",
            "docs": "Documentation",
            "perf": "Performance Improvements",
            "refactor": "Code Refactoring",
            "test": "Tests",
        }

        for cat in ["feat", "fix", "docs", "perf", "refactor", "test"]:
            if cat in categories:
                lines.append(f"\n### {category_labels[cat]}")
                for entry in categories[cat]:
                    lines.append(f"- {entry['description']}")

        return "\n".join(lines) + "\n"

    def save(self, version: str) -> str:
        """Save the changelog to disk.

        Parameters
        ----------
        version : str
            Version string for the section header.

        Returns
        -------
        str
            Path to the saved changelog file.
        """
        content = self.generate_section(version)

        # Read existing changelog if it exists
        if os.path.exists(self.changelog_path):
            with open(self.changelog_path, "r") as f:
                existing = f.read()
            content = content + "\n" + existing

        with open(self.changelog_path, "w") as f:
            f.write(content)

        return self.changelog_path


def _get_current_timestamp() -> str:
    """Get the current timestamp in ISO format.

    Returns
    -------
    str
        Timestamp string (YYYY-MM-DDTHH:MM:SS).
    """
    from datetime import datetime
    return datetime.now().isoformat()


def _get_current_date() -> str:
    """Get the current date in YYYY-MM-DD format.

    Returns
    -------
    str
        Date string.
    """
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")


class GitChangelogGenerator:
    """Generate changelog entries from git commit messages.

    This class parses git log output to automatically generate
    changelog entries based on conventional commit message format.

    Supported commit types:
    - feat: New features
    - fix: Bug fixes
    - docs: Documentation changes
    - perf: Performance improvements
    - refactor: Code refactoring
    - test: Test additions or corrections
    """

    @staticmethod
    def generate_from_git(
        git_path: str = ".",
        since_tag: Optional[str] = None,
    ) -> List[dict]:
        """Generate changelog entries from git commits.

        Parameters
        ----------
        git_path : str, default="."
            Path to the git repository root.
        since_tag : str, optional
            Git tag to start from. If None, uses all history.

        Returns
        -------
        list[dict]
            Changelog entries with keys:
            - 'category': commit type (feat, fix, etc.)
            - 'description': commit message subject
            - 'version': inferred version from tag
        """
        # Build git log command
        cmd = ["git", "-C", git_path, "log"]

        if since_tag:
            cmd.extend(["--since", since_tag])

        cmd.extend([
            "--pretty=format:%s%n%h%n%an%n%ad",
            "--date=short",
        ])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return []

            # Parse commit messages
            entries = []
            commits = result.stdout.strip().split("\n\n")

            for commit_block in commits:
                lines = commit_block.split("\n")
                if len(lines) < 3:
                    continue

                subject = lines[0]
                hash_ = lines[1]
                author = lines[2]

                # Parse conventional commit format
                match = re.match(r"^(\w+)(?:\(([^)]+)\))?: (.+)$", subject)
                if match:
                    category, scope, description = match.groups()
                    entries.append({
                        "category": category,
                        "description": f"{description} ({hash_[:7]})",
                        "author": author,
                    })

            return entries

        except subprocess.SubprocessError:
            return []
