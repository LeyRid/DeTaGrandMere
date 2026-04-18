"""
Semantic versioning and changelog management for the deTAGrandMere project.

This module provides classes for managing semantic versioning (SemVer 2.0)
and maintaining a structured changelog in Markdown format. The SemanticVersion
class handles version parsing, comparison, and increment operations, while
ChangelogManager maintains categorized change entries across versions.

Example usage::

    from src.utils.version_history import SemanticVersion, ChangelogManager

    # Version management
    v = SemanticVersion(major=0, minor=1, patch=0)
    print(v)           # "0.1.0"
    v_new = v.increment_minor()
    print(v_new)       # "0.2.0"

    # Changelog management
    cm = ChangelogManager("CHANGELOG.md")
    cm.add_entry("0.2.0", "feat", "Added dipole solver")
    cm.add_entry("0.2.0", "fix", "Corrected mesh refinement")
    cm.add_entry("0.1.0", "feat", "Initial release")
    cm.save()
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone


class SemanticVersion:
    """Represent and manipulate a semantic version number per SemVer 2.0.

    Semantic versions follow the format MAJOR.MINOR.PATCH where:
    - MAJOR is incremented for incompatible API changes
    - MINOR is incremented for backwards-compatible functionality
    - PATCH is incremented for backwards-compatible bug fixes

    A prerelease tag (alpha, beta, rc) can be appended to indicate
    pre-release status.

    Parameters
    ----------
    major : int or str, optional
        Major version number. Default is 0.
    minor : int or str, optional
        Minor version number. Default is 1.
    patch : int or str, optional
        Patch version number. Default is 0.
    prerelease : str or None, optional
        Prerelease identifier. Can be "alpha", "beta", or "rc". Default is None.

    Examples
    --------
    >>> v = SemanticVersion("1.2.3")
    >>> print(v)
    1.2.3
    >>> v_minor = v.increment_minor()
    >>> print(v_minor)
    1.3.0
    >>> SemanticVersion("1.0.0") < SemanticVersion("2.0.0")
    True
    """

    def __init__(
        self,
        major: int | str = 0,
        minor: int | str = 1,
        patch: int | str = 0,
        prerelease: str | None = None
    ) -> None:
        """Initialize a semantic version.

        Can be initialized with individual components or parsed from a
        version string in "MAJOR.MINOR.PATCH" format.

        Parameters
        ----------
        major : int or str, optional
            Major version number. If a single positional argument is passed
            and it is a string, it will be parsed as "MAJOR.MINOR.PATCH".
        minor : int or str, optional
            Minor version number. Default is 1.
        patch : int or str, optional
            Patch version number. Default is 0.
        prerelease : str or None, optional
            Prerelease tag. Valid values: "alpha", "beta", "rc". Default is None.

        Raises
        ------
        ValueError
            If the version string cannot be parsed or contains invalid components.
        """
        self.prerelease: str | None = prerelease

        # Handle case where first argument is a full version string
        if isinstance(major, str) and minor == 1 and patch == 0:
            # Only treat as version string if it looks like one
            if re.match(r"^\d+\.\d+\.\d+", major):
                parts = major.split(".")
                self.major = int(parts[0])
                self.minor = int(parts[1]) if len(parts) > 1 else 0
                self.patch = int(parts[2]) if len(parts) > 2 else 0
                return

        self.major: int = int(major)
        self.minor: int = int(minor)
        self.patch: int = int(patch)

    def increment_major(self) -> SemanticVersion:
        """Bump the major version number and reset minor and patch to zero.

        Returns
        -------
        SemanticVersion
            A new SemanticVersion instance with incremented major version.

        Examples
        --------
        >>> v = SemanticVersion("1.2.3")
        >>> v_new = v.increment_major()
        >>> print(v_new)
        2.0.0
        """
        return SemanticVersion(
            major=self.major + 1,
            minor=0,
            patch=0,
            prerelease=None
        )

    def increment_minor(self) -> SemanticVersion:
        """Bump the minor version number and reset patch to zero.

        Returns
        -------
        SemanticVersion
            A new SemanticVersion instance with incremented minor version.

        Examples
        --------
        >>> v = SemanticVersion("1.2.3")
        >>> v_new = v.increment_minor()
        >>> print(v_new)
        1.3.0
        """
        return SemanticVersion(
            major=self.major,
            minor=self.minor + 1,
            patch=0,
            prerelease=None
        )

    def increment_patch(self) -> SemanticVersion:
        """Bump the patch version number.

        Returns
        -------
        SemanticVersion
            A new SemanticVersion instance with incremented patch version.

        Examples
        --------
        >>> v = SemanticVersion("1.2.3")
        >>> v_new = v.increment_patch()
        >>> print(v_new)
        1.2.4
        """
        return SemanticVersion(
            major=self.major,
            minor=self.minor,
            patch=self.patch + 1,
            prerelease=None
        )

    def __str__(self) -> str:
        """Return the version as a formatted MAJOR.MINOR.PATCH string.

        Returns
        -------
        str
            Version string in "MAJOR.MINOR.PATCH" format. If a prerelease tag
            is set, it is appended with a hyphen (e.g., "1.0.0-alpha").

        Examples
        --------
        >>> str(SemanticVersion(1, 2, 3))
        '1.2.3'
        >>> str(SemanticVersion(0, 1, 0, prerelease="alpha"))
        '0.1.0-alpha'
        """
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease is not None:
            base += f"-{self.prerelease}"
        return base

    def __repr__(self) -> str:
        """Return a detailed representation of the version object.

        Returns
        -------
        str
            String representation showing class name and all components.
        """
        pre = f", prerelease='{self.prerelease}'" if self.prerelease is not None else ""
        return f"SemanticVersion(major={self.major}, minor={self.minor}, patch={self.patch}{pre})"

    def __eq__(self, other: object) -> bool:
        """Compare this version with another for equality.

        Parameters
        ----------
        other : object
            Another SemanticVersion instance or a string representation.

        Returns
        -------
        bool
            True if the versions are equal, False otherwise.

        Examples
        --------
        >>> SemanticVersion("1.0.0") == SemanticVersion("1.0.0")
        True
        >>> SemanticVersion("1.0.0") == SemanticVersion("1.0.1")
        False
        """
        if isinstance(other, str):
            other = SemanticVersion(other)
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.prerelease == other.prerelease
        )

    def __lt__(self, other: object) -> bool:
        """Compare this version with another for less-than ordering.

        Versions are compared by major, minor, and patch in that order.
        Prerelease versions are considered lower than the corresponding
        release version (e.g., "1.0.0-alpha" < "1.0.0").

        Parameters
        ----------
        other : object
            Another SemanticVersion instance or a string representation.

        Returns
        -------
        bool
            True if this version is less than the other, False otherwise.

        Examples
        --------
        >>> SemanticVersion("0.9.0") < SemanticVersion("1.0.0")
        True
        >>> SemanticVersion("1.0.0") < SemanticVersion("1.0.1")
        True
        """
        if isinstance(other, str):
            other = SemanticVersion(other)
        if not isinstance(other, SemanticVersion):
            return NotImplemented

        # Prerelease is always less than the release version
        self_pre = 0 if self.prerelease is not None else 1
        other_pre = 0 if other.prerelease is not None else 1

        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

        # Same version numbers; prerelease is lower
        return self_pre < other_pre

    def __le__(self, other: object) -> bool:
        """Less than or equal comparison."""
        if isinstance(other, str):
            other = SemanticVersion(other)
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        return self == other or self < other

    def __gt__(self, other: object) -> bool:
        """Greater than comparison."""
        if isinstance(other, str):
            other = SemanticVersion(other)
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        return not self <= other

    def __ge__(self, other: object) -> bool:
        """Greater than or equal comparison."""
        if isinstance(other, str):
            other = SemanticVersion(other)
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        return not self < other

    def __hash__(self) -> int:
        """Return a hash value for use in sets and dictionary keys.

        Returns
        -------
        int
            Hash of the version tuple (major, minor, patch, prerelease).
        """
        return hash((self.major, self.minor, self.patch, self.prerelease))


class ChangelogManager:
    """Manage a structured Markdown changelog for versioned releases.

    Maintains categorized change entries organized by version and category.
    Supports adding entries, generating formatted sections, and persisting
    the changelog to a Markdown file.

    Parameters
    ----------
    changelog_path : str, optional
        File path where the changelog will be saved. Default is "CHANGELOG.md".

    Examples
    --------
    >>> cm = ChangelogManager("CHANGELOG.md")
    >>> cm.add_entry("0.2.0", "feat", "Added new solver")
    >>> cm.add_entry("0.2.0", "fix", "Fixed mesh generation bug")
    >>> section = cm.generate_section("0.2.0")
    >>> print(section[:50])
    ## [0.2.0] - 2026-04-18

    ### Features
    """

    def __init__(self, changelog_path: str = "CHANGELOG.md") -> None:
        """Initialize the changelog manager.

        Parameters
        ----------
        changelog_path : str, optional
            Path to the changelog Markdown file. Default is "CHANGELOG.md".
        """
        self.changelog_path: str = changelog_path
        # Dictionary mapping version strings to lists of entries
        # Each entry is a dict with 'category', 'message', and 'date'
        self.entries: dict[str, list[dict[str, str | None]]] = {}

    def add_entry(
        self,
        version: str,
        category: str,
        message: str,
        date: str | None = None
    ) -> None:
        """Add a changelog entry for a specific version and category.

        Appends a new entry to the changelog organized by version. Valid
        categories are: feat, fix, docs, perf, refactor, test. Entries
        are stored in a dictionary keyed by version string.

        Parameters
        ----------
        version : str
            Semantic version string (e.g., "0.2.0", "1.0.0-alpha").
        category : str
            Change category. Must be one of: "feat", "fix", "docs",
            "perf", "refactor", "test".
        message : str
            Description of the change.
        date : str or None, optional
            Date string in YYYY-MM-DD format. Defaults to today's date.

        Raises
        ------
        ValueError
            If the category is not one of the recognized types.

        Examples
        --------
        >>> cm = ChangelogManager()
        >>> cm.add_entry("0.1.0", "feat", "Initial release")
        >>> cm.add_entry("0.2.0", "fix", "Fixed import error")
        """
        valid_categories = {"feat", "fix", "docs", "perf", "refactor", "test"}
        if category not in valid_categories:
            raise ValueError(
                f"Invalid category '{category}'. Must be one of: {', '.join(sorted(valid_categories))}"
            )

        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        entry = {
            "category": category,
            "message": message,
            "date": date,
        }

        if version not in self.entries:
            self.entries[version] = []
        self.entries[version].append(entry)

    def generate_section(self, version_str: str) -> str:
        """Generate a Markdown section for a specific version with categorized entries.

        Groups all entries for the given version by category and formats them
        as a structured Markdown heading with sub-sections for each category.

        Parameters
        ----------
        version_str : str
            Semantic version string (e.g., "0.2.0").

        Returns
        -------
        str
            Markdown-formatted section containing the categorized changelog
            entries for the specified version.

        Notes
        -----
        Categories with no entries are omitted from the output. The version
        date is determined from the earliest entry's date, or defaults to
        today if no entries exist.
        """
        lines: list[str] = []
        lines.append(f"## [{version_str}]")

        # Determine version date from entries
        entries = self.entries.get(version_str, [])
        dates = [e["date"] for e in entries if e.get("date")]
        version_date = dates[0] if dates else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        lines.append(f"### {version_date}")
        lines.append("")

        # Category labels
        category_labels = {
            "feat": "Features",
            "fix": "Bug Fixes",
            "docs": "Documentation",
            "perf": "Performance",
            "refactor": "Refactoring",
            "test": "Tests",
        }

        # Group entries by category
        grouped: dict[str, list[dict]] = {}
        for entry in entries:
            cat = entry["category"]
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(entry)

        # Write each category group
        for cat_key in ["feat", "fix", "docs", "perf", "refactor", "test"]:
            cat_entries = grouped.get(cat_key, [])
            if not cat_entries:
                continue

            lines.append(f"### {category_labels[cat_key]}")
            lines.append("")
            for entry in cat_entries:
                lines.append(f"- {entry['message']}")
            lines.append("")

        return "\n".join(lines)

    def save(self) -> None:
        """Write the complete changelog to the Markdown file.

        Generates a full Markdown changelog file with all version sections,
        sorted in descending version order (newest first). Writes the file
        to the path specified by ``self.changelog_path``.

        Raises
        ------
        OSError
            If the file cannot be written due to permission or path issues.

        Notes
        -----
        The generated file includes:
        - A top-level "Changelog" heading
        - All version sections sorted by semantic version (newest first)
        - Categorized entries within each version section
        """
        # Sort versions in descending order (newest first)
        sorted_versions = sorted(
            self.entries.keys(),
            key=lambda v: SemanticVersion(v),
            reverse=True
        )

        lines: list[str] = []
        lines.append("# Changelog")
        lines.append("")
        lines.append("All notable changes to this project will be documented in this file.")
        lines.append("")
        lines.append("The format is based on [Keep a Changelog](https://keepachangelog.com/),")
        lines.append("and this project adheres to [Semantic Versioning](https://semver.org/).")
        lines.append("")

        for version_str in sorted_versions:
            section = self.generate_section(version_str)
            lines.append(section)
            lines.append("---")
            lines.append("")

        output_path = self.changelog_path
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
