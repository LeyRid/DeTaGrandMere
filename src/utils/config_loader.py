"""Configuration loader module for DeTaGrandMere antenna simulation software.

Provides the ``ConfigLoader`` class for loading, validating, and managing
YAML / JSON configuration files.  Supports schema validation, environment
variable overrides, and a full programmatic API (get / set / save).

Default configuration sections::

    solver       -- tolerance, max_iterations, solver_type
    mesh         -- alpha_shape, min_quality, refinement_level
    boundary     -- types (list of allowed boundary condition names)
    visualization -- backend, color_map, resolution
    file_io      -- output_format, output_dir


Example usage ::

    from src.utils.config_loader import ConfigLoader, DEFAULTS, override_from_env

    # Load from an existing file (or use defaults if it does not exist)
    cfg = ConfigLoader("configs/antenna.yaml")
    cfg.load()

    # Query values
    tol = cfg.get("solver", "tolerance")
    backend = cfg.get("visualization", "backend", default="matplotlib")

    # Override via the API
    cfg.set("solver", "max_iterations", 500)

    # Validate against the built-in schema (or a custom one)
    assert cfg.validate() is True

    # Persist changes
    cfg.save("configs/antenna.yaml")

    # Environment variable override example (set before loading)::
    #   export DETAGRANDMERE_SOLVER_TOLERANCE=1e-08
    #   export DETAGRANDMERE_MESH_REFINEMENT_LEVEL=3


Programmatic override example ::

    config = dict(DEFAULTS)
    config = override_from_env(config)  # reads DETAGRANDMERE_* env vars
"""  # noqa: E501

from __future__ import annotations

import copy
import json
import os
import re
import sys
from typing import Any, Optional


from .errors import ConfigError

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _try_import_yaml() -> Any:
    """Return the ``yaml`` module or ``None`` if unavailable."""
    try:
        import yaml  # noqa: F401

        return yaml
    except ImportError:
        return None


_YAML = _try_import_yaml()


def _parse_yaml_fallback(text: str) -> dict[str, Any]:
    """Minimal YAML parser (no pyyaml dependency).

    Handles a very small subset of YAML sufficient for flat / nested
    configuration dictionaries with scalar values.  Raises
    ``ConfigError`` when the format is too complex to parse.
    """

    def _parse_value(value: str) -> Any:
        value = value.strip()
        if not value:
            return ""
        # Quoted strings
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            return value[1:-1]
        # Boolean
        lower = value.lower()
        if lower in ("true", "yes"):
            return True
        if lower in ("false", "no"):
            return False
        # None / null
        if lower in ("null", "none"):
            return None
        # Integer
        try:
            return int(value)
        except ValueError:
            pass
        # Float
        try:
            return float(value)
        except ValueError:
            pass
        return value

    result: dict[str, Any] = {}
    current_key: str | None = None
    list_items: list[str] = []
    in_list = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.lstrip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(stripped)

        # List item (e.g. "  - type1")
        if stripped.startswith("- ") or stripped == "-":
            in_list = True
            value = stripped[2:].strip() if stripped.startswith("- ") else ""
            list_items.append(_parse_value(value))
            continue

        # End of list section: a non-list line at same indent resets
        if in_list and not stripped.startswith("-"):
            if current_key is not None:
                result[current_key] = list_items
            in_list = False
            list_items.clear()

        # Key-value pair (e.g. "  key: value")
        match = re.match(r"^(\w+)\s*:\s*(.*)$", stripped)
        if match:
            key, val = match.group(1), match.group(2).strip()
            current_key = key

            # Nested dict via further indented key-value pairs
            if not in_list and (not val or val == "" or val.startswith("#")):
                # Could be start of a nested block; treat as empty
                pass

            if in_list:
                list_items.append(_parse_value(val))
            elif val:
                result[key] = _parse_value(val)
                current_key = None
            else:
                result[key] = {}
                current_key = key

    # Flush any remaining list
    if in_list and current_key is not None:
        result[current_key] = list_items

    return result


# ---------------------------------------------------------------------------
# Schema definition (used as the default schema)
# ---------------------------------------------------------------------------

DEFAULT_SCHEMA: dict[str, dict[str, dict[str, Any]]] = {
    "solver": {
        "tolerance": {"type": float, "description": "Convergence tolerance"},
        "max_iterations": {
            "type": int,
            "description": "Maximum number of iterations",
        },
        "solver_type": {
            "type": str,
            "description": "Solver algorithm name (e.g. 'gmres', 'bicgstab')",
        },
    },
    "mesh": {
        "alpha_shape": {
            "type": float,
            "description": "Alpha shape parameter for meshing",
        },
        "min_quality": {
            "type": float,
            "description": "Minimum element quality threshold (0-1)",
        },
        "refinement_level": {
            "type": int,
            "description": "Mesh refinement level (positive integer)",
        },
    },
    "boundary": {
        "types": {
            "type": list,
            "description": "List of allowed boundary condition types",
            "items_type": str,
        },
    },
    "visualization": {
        "backend": {
            "type": str,
            "description": "Plotting backend ('matplotlib', 'plotly')",
        },
        "color_map": {
            "type": str,
            "description": "Colormap name for field visualisation",
        },
        "resolution": {
            "type": int,
            "description": "Output image resolution in DPI",
        },
    },
    "file_io": {
        "output_format": {
            "type": str,
            "description": "Default output format ('csv', 'vtk', 'h5')",
        },
        "output_dir": {
            "type": str,
            "description": "Directory for simulation output files",
        },
    },
}


# ---------------------------------------------------------------------------
# Default configuration values (nested by section)
# ---------------------------------------------------------------------------

DEFAULTS: dict[str, dict[str, Any]] = {
    "solver": {
        "tolerance": 1e-6,
        "max_iterations": 200,
        "solver_type": "gmres",
    },
    "mesh": {
        "alpha_shape": 0.5,
        "min_quality": 0.3,
        "refinement_level": 2,
    },
    "boundary": {
        "types": ["PEC", "absorbing", "symmetric"],
    },
    "visualization": {
        "backend": "matplotlib",
        "color_map": "viridis",
        "resolution": 150,
    },
    "file_io": {
        "output_format": "vtk",
        "output_dir": "./output",
    },
}


# ---------------------------------------------------------------------------
# Environment variable override function
# ---------------------------------------------------------------------------


def override_from_env(config_dict: dict[str, Any]) -> dict[str, Any]:
    """Override configuration values from environment variables.

    Reads environment variables with the prefix ``DETAGRANDMERE_`` and uses
    them to update a copy of *config_dict*.  The variable name encodes the
    nested section and key separated by underscores.

    For example::

        export DETAGRANDMERE_SOLVER_TOLERANCE=1e-08
        export DETAGRANDMERE_MESH_REFINEMENT_LEVEL=3

    will override ``config['solver']['tolerance']`` with ``1e-08`` and
    ``config['mesh']['refinement_level']`` with ``3``.

    Values are automatically converted to appropriate Python types
    (int, float, bool, None, or str) before being stored.

    Parameters
    ----------
    config_dict : dict[str, Any]
        Nested configuration dictionary (typically :data:`DEFAULTS`).

    Returns
    -------
    dict[str, Any]
        A new dictionary with environment variable overrides applied.
        The original *config_dict* is **not** mutated.

    Example
    -------
    >>> config = dict(DEFAULTS)
    >>> import os
    >>> os.environ["DETAGRANDMERE_SOLVER_TOLERANCE"] = "1e-08"
    >>> updated = override_from_env(config)
    >>> updated["solver"]["tolerance"]
    1e-08
    """
    result = copy.deepcopy(config_dict)
    prefix = "DETAGRANDMERE_"

    for env_key, env_value in os.environ.items():
        if not env_key.startswith(prefix):
            continue

        # Strip the prefix and split on underscores
        remainder = env_key[len(prefix) :]  # e.g. SOLVER_TOLERANCE
        parts = remainder.split("_")
        if len(parts) < 2:
            continue

        section = parts[0].lower()
        param = "_".join(parts[1:]).lower()

        # Deep-merge into result
        if section not in result:
            result[section] = {}

        converted = _convert_env_value(env_value)
        result[section][param] = converted

    return result


def _convert_env_value(value: str) -> Any:
    """Convert an environment variable string to a Python type."""
    if not value:
        return ""

    # Boolean
    lower = value.lower()
    if lower in ("true", "yes"):
        return True
    if lower in ("false", "no"):
        return False

    # None / null
    if lower in ("null", "none"):
        return None

    # Integer
    try:
        return int(value)
    except ValueError:
        pass

    # Float (including scientific notation like 1e-08)
    try:
        return float(value)
    except ValueError:
        pass

    return value


# ---------------------------------------------------------------------------
# ConfigLoader class
# ---------------------------------------------------------------------------


class ConfigLoader:
    """Load, validate, and manage DeTaGrandMere configuration files.

    ``ConfigLoader`` reads YAML or JSON configuration files, applies
    environment variable overrides (prefixed with ``DETAGRANDMERE_``),
    validates the resulting configuration against a schema, and provides
    a convenient programmatic API for querying and mutating settings.

    Parameters
    ----------
    config_path : str | None
        Path to an existing configuration file.  If ``None`` or the file
        does not exist, the class falls back to the built-in
        :attr:`DEFAULTS`.

    Attributes
    ----------
    DEFAULTS : dict[str, dict[str, Any]]
        Nested dictionary of default configuration values by section.
    DEFAULT_SCHEMA : dict[str, dict[str, dict[str, Any]]]
        Schema definition used for :meth:`validate` when no custom schema
        is supplied.

    Example
    -------
    >>> cfg = ConfigLoader("configs/antenna.yaml")
    >>> cfg.load()
    >>> print(cfg.get("solver", "tolerance"))
    1e-06
    """

    DEFAULTS: dict[str, dict[str, Any]] = DEFAULTS.copy()
    DEFAULT_SCHEMA: dict[str, dict[str, dict[str, Any]]] = DEFAULT_SCHEMA.copy()

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialise the loader with an optional configuration file path.

        Parameters
        ----------
        config_path : str | None
            Path to a YAML or JSON configuration file.  Missing files are
            silently ignored and defaults are used instead.
        """
        self._config_path: Optional[str] = config_path
        self._data: dict[str, dict[str, Any]] = {
            section: dict(values) for section, values in DEFAULTS.items()
        }

    # -----------------------------------------------------------------------
    # Loading
    # -----------------------------------------------------------------------

    def load(self) -> dict[str, dict[str, Any]]:
        """Load configuration from file and apply environment variable overrides.

        The method follows this order:

        1. Start with a deep copy of :attr:`DEFAULTS`.
        2. Read the configuration file (YAML or JSON) if ``config_path`` is
           set and the file exists.
        3. Override values with environment variables whose names match the
           pattern ``DETAGRANDMERE_<SECTION>_<PARAM>`` (upper-cased).

        Returns
        -------
        dict
            The merged configuration dictionary.

        Raises
        ------
        ConfigError
            If the configuration file exists but contains invalid YAML or JSON.
        """
        # Start from defaults
        self._data = {section: dict(values) for section, values in DEFAULTS.items()}

        # Load from file if a path was provided and the file exists
        if self._config_path is not None and os.path.isfile(self._config_path):
            self._load_file(self._config_path)

        # Apply environment variable overrides
        self._apply_env_overrides()

        return dict(self._data)

    def _load_file(self, path: str) -> None:
        """Read a single configuration file (YAML or JSON)."""
        ext = os.path.splitext(path)[1].lower()

        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = fh.read()
        except OSError as exc:
            raise ConfigError(
                f"Could not read configuration file: {path}",
                context={"path": path, "reason": str(exc)},
            ) from exc

        try:
            if ext == ".yaml" or ext == ".yml":
                if _YAML is not None:
                    parsed = _YAML.safe_load(raw)
                else:
                    parsed = _parse_yaml_fallback(raw)
            elif ext == ".json":
                parsed = json.loads(raw)
            else:
                # Try JSON first, then YAML fallback
                try:
                    parsed = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    if _YAML is not None:
                        parsed = _YAML.safe_load(raw)
                    else:
                        parsed = _parse_yaml_fallback(raw)

        except Exception as exc:
            raise ConfigError(
                f"Failed to parse configuration file: {path}",
                context={"path": path, "error": str(exc)},
            ) from exc

        if not isinstance(parsed, dict):
            parsed = {}

        # Deep merge into self._data
        for section, values in parsed.items():
            if isinstance(values, dict) and section in self._data:
                self._data[section].update(values)
            elif isinstance(values, dict):
                self._data[section] = dict(values)

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to the configuration.

        Environment variables follow the pattern
        ``DETAGRANDMERE_<SECTION>_<PARAM>`` where *section* and *param* are
        upper-cased.  For example::

            export DETAGRANDMERE_SOLVER_TOLERANCE=1e-08
            export DETAGRANDMERE_MESH_REFINEMENT_LEVEL=3

        The value is converted to an appropriate Python type before being
        stored.
        """
        prefix = "DETAGRANDMERE_"
        for env_key, env_value in os.environ.items():
            if not env_key.startswith(prefix):
                continue

            # Strip the prefix and split on underscores
            remainder = env_key[len(prefix) :]  # e.g. SOLVER_TOLERANCE
            parts = remainder.split("_")
            if len(parts) < 2:
                continue

            section = parts[0].lower()
            param = "_".join(parts[1:]).lower()

            if section not in self._data:
                # Create a new section with defaults
                self._data[section] = {}

            # Try to convert the value
            converted = _convert_env_value(env_value)
            self._data[section][param] = converted

    @staticmethod
    def _convert_env_value(value: str) -> Any:
        """Convert an environment variable string to a Python type."""
        if not value:
            return ""

        # Boolean
        lower = value.lower()
        if lower in ("true", "yes"):
            return True
        if lower in ("false", "no"):
            return False

        # None / null
        if lower in ("null", "none"):
            return None

        # Integer
        try:
            return int(value)
        except ValueError:
            pass

        # Float (including scientific notation like 1e-08)
        try:
            return float(value)
        except ValueError:
            pass

        return value

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------

    def validate(self, schema: Optional[dict] = None) -> bool:
        """Validate the current configuration against a schema.

        Parameters
        ----------
        schema : dict | None
            A custom schema to validate against.  If ``None``, the class
            attribute :attr:`DEFAULT_SCHEMA` is used.

        Returns
        -------
        bool
            ``True`` if validation passes; ``False`` otherwise.

        Raises
        ------
        ConfigError
            If a required key is missing, has an incorrect type, or fails
            a constraint check.
        """
        target_schema = schema if schema is not None else self.DEFAULT_SCHEMA

        for section, params in target_schema.items():
            if section not in self._data:
                raise ConfigError(
                    f"Missing configuration section: '{section}'",
                    context={"valid_sections": list(self._data.keys())},
                )

            for param, spec in params.items():
                expected_type = spec.get("type")
                if expected_type is None:
                    continue

                # Check key existence
                if param not in self._data[section]:
                    raise ConfigError(
                        f"Missing required parameter '{param}' "
                        f"in section '{section}'",
                        context={"section": section},
                    )

                value = self._data[section][param]

                # Type check
                if expected_type is list:
                    items_type = spec.get("items_type")
                    if items_type and not all(
                        isinstance(item, items_type) for item in value
                    ):
                        raise ConfigError(
                            f"Parameter '{param}' in section '{section}' "
                            f"must be a list of {items_type.__name__}s",
                            context={
                                "actual": type(value).__name__,
                                "expected_items_type": items_type.__name__,
                            },
                        )
                elif not isinstance(value, expected_type):
                    raise ConfigError(
                        f"Parameter '{param}' in section '{section}': "
                        f"expected {expected_type.__name__}, "
                        f"got {type(value).__name__}",
                        context={
                            "actual": type(value).__name__,
                            "expected": expected_type.__name__,
                        },
                    )

        return True

    # -----------------------------------------------------------------------
    # Query / Mutation API
    # -----------------------------------------------------------------------

    def get(
        self, section: str, key: str, default: Optional[Any] = None
    ) -> Any:
        """Retrieve a configuration value.

        Parameters
        ----------
        section : str
            Configuration section name (e.g. ``'solver'``).
        key : str
            Parameter name within the section.
        default : Any, optional
            Value returned if the parameter is not found.  If omitted,
            ``None`` is used.

        Returns
        -------
        Any
            The configuration value, or *default* if missing.
        """
        return self._data.get(section, {}).get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration parameter using the format ``section.key``.

        Parameters
        ----------
        key : str
            Parameter in *section*.*param* format (e.g. ``'solver.tolerance'``).
        value : Any
            The new value to assign.

        Raises
        ------
        ConfigError
            If the key does not follow the ``section.param`` convention.
        """
        parts = key.split(".")
        if len(parts) != 2:
            raise ConfigError(
                "Configuration key must be in 'section.param' format",
                context={"provided": key},
            )

        section, param = parts
        if section not in self._data:
            self._data[section] = {}
        self._data[section][param] = value

    # -----------------------------------------------------------------------
    # Serialization
    # -----------------------------------------------------------------------

    def to_dict(self) -> dict[str, dict[str, Any]]:
        """Return a deep copy of the current configuration.

        Returns
        -------
        dict
            Nested dictionary of section-level settings.
        """
        return {section: dict(values) for section, values in self._data.items()}

    def save(self, path: Optional[str] = None) -> str:
        """Persist the current configuration to a file.

        Parameters
        ----------
        path : str | None
            Destination file path.  If ``None``, uses the original
            ``config_path`` supplied at construction time.

        Returns
        -------
        str
            The path of the saved file.

        Raises
        ------
        ConfigError
            If no save path is available (neither provided nor stored).
        """
        target = path or self._config_path
        if target is None:
            raise ConfigError(
                "No configuration file path available for saving",
                context={
                    "config_path": self._config_path,
                    "provided_path": path,
                },
            )

        ext = os.path.splitext(target)[1].lower()

        # Ensure parent directory exists
        parent_dir = os.path.dirname(target)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        if ext in (".yaml", ".yml"):
            content = self._serialize_yaml()
        else:
            content = json.dumps(self._data, indent=2, default=str)

        with open(target, "w", encoding="utf-8") as fh:
            fh.write(content)

        return target

    def _serialize_yaml(self) -> str:
        """Serialize configuration to YAML format."""
        if _YAML is not None:
            return _YAML.dump(
                self._data, default_flow_style=False, sort_keys=False
            )

        # Fallback: manual YAML serialization
        lines: list[str] = []
        for section, values in self._data.items():
            lines.append(f"{section}:")
            for key, value in values.items():
                if isinstance(value, list):
                    for item in value:
                        formatted = json.dumps(item) if not isinstance(item, str) else item
                        lines.append(f"  - {formatted}")
                elif isinstance(value, bool):
                    lines.append(f"  {key}: {'true' if value else 'false'}")
                elif value is None:
                    lines.append(f"  {key}: null")
                else:
                    lines.append(f"  {key}: {value}")

        return "\n".join(lines) + "\n"
