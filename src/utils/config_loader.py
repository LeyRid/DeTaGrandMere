"""Configuration file management with YAML/JSON support and environment variable overrides.

This module provides the :class:`ConfigLoader` class for loading simulation
configuration from YAML or JSON files, validating against a schema, and
overriding values from environment variables.

Key features:
- YAML and JSON configuration file loading
- Schema validation with required fields and type checking
- Environment variable overrides (DETAGRANDMERE_* prefix)
- Default value merging for unspecified parameters
- CLI argument integration with config file settings
"""

from __future__ import annotations

import os
import json
import yaml
from typing import Optional, Dict, List, Any


class ConfigLoader:
    """Load and manage simulation configuration from files and environment.

    This class handles loading configuration from YAML/JSON files, validating
    against a schema, applying environment variable overrides, and merging
    with default values for unspecified parameters.

    Parameters
    ----------
    config_path : str, optional
        Path to the configuration file. If None, uses default config.
    env_prefix : str, default="DETAGRANDMERE_"
        Environment variable prefix for overrides.
    """

    # Default configuration values
    DEFAULTS = {
        "solver": {
            "solver_type": "EFIE",
            "tolerance": 1e-6,
            "max_iterations": 1000,
            "preconditioner": "ilu",
            "frequency_hz": 1e9,
        },
        "mesh": {
            "target_edge_length": 0.1,
            "min_edge_length": 0.01,
            "max_iterations_refinement": 5,
        },
        "boundary": {
            "outer_bc": "radiation",
            "inner_bc": "pec",
        },
        "visualization": {
            "colormap": "viridis",
            "show_axes": True,
            "window_size": [800, 600],
        },
        "file_io": {
            "output_dir": "results/",
            "export_formats": ["touchstone", "hdf5"],
            "compression_level": 3,
        },
    }

    # Schema definition for validation
    SCHEMA = {
        "solver": {
            "required": ["solver_type", "tolerance"],
            "types": {"solver_type": str, "tolerance": (int, float), "max_iterations": int},
        },
        "mesh": {
            "required": ["target_edge_length"],
            "types": {"target_edge_length": float, "min_edge_length": float},
        },
        "boundary": {
            "required": [],
            "types": {"outer_bc": str, "inner_bc": str},
        },
        "visualization": {
            "required": [],
            "types": {"colormap": str, "show_axes": bool, "window_size": list},
        },
        "file_io": {
            "required": [],
            "types": {"output_dir": str, "export_formats": list},
        },
    }

    def __init__(self, config_path: Optional[str] = None, env_prefix: str = "DETAGRANDMERE_") -> None:
        """Initialise the configuration loader."""
        self.config_path = config_path
        self.env_prefix = env_prefix
        self._config: Dict[str, Any] = {}
        self._loaded = False

        # Load default configuration
        self._config = {
            section: dict(values) for section, values in self.DEFAULTS.items()
        }

        # Load from file if path provided
        if config_path and os.path.exists(config_path):
            self.load_file(config_path)

    # -------------------------------------------------------------------
    # File loading
#    ----------------------------------------------------------------

    def load_file(self, path: str) -> dict:
        """Load configuration from a YAML or JSON file.

        Parameters
        ----------
        path : str
            Path to the configuration file.

        Returns
        -------
        dict
            Loaded configuration dictionary.

        Raises
        ------
        FileNotFoundError
            If the file does not exist.
        ValueError
            If the file format is unsupported or contains invalid data.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file not found: {path}")

        ext = os.path.splitext(path)[1].lower()

        try:
            with open(path, "r") as f:
                if ext == ".yaml" or ext == ".yml":
                    data = yaml.safe_load(f)
                elif ext == ".json":
                    data = json.load(f)
                else:
                    raise ValueError(f"Unsupported config format: {ext}")

            # Merge loaded data into defaults
            self._merge_config(data)
            self.config_path = path
            self._loaded = True

        except (yaml.YAMLError, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to parse configuration file: {e}")

        return self._config

    def save_file(self, path: str) -> str:
        """Save current configuration to a file.

        Parameters
        ----------
        path : str
            Output file path (YAML format).

        Returns
        -------
        str
            Path to the saved file.
        """
        ext = os.path.splitext(path)[1].lower()

        with open(path, "w") as f:
            if ext == ".yaml" or ext == ".yml":
                yaml.dump(self._config, f, default_flow_style=False)
            elif ext == ".json":
                json.dump(self._config, f, indent=2)

        return path

    # -------------------------------------------------------------------
    # Configuration management
#    ----------------------------------------------------------------

    def _merge_config(self, data: dict) -> None:
        """Merge configuration data into the current config.

        Parameters
        ----------
        data : dict
            Configuration dictionary to merge.
        """
        for section, values in data.items():
            if section in self._config and isinstance(values, dict):
                self._config[section].update(values)
            elif section not in self._config:
                self._config[section] = values

    def override_from_env(self) -> None:
        """Override configuration values from environment variables.

        Environment variables should follow the pattern:
        DETAGRANDMERE_<SECTION>_<KEY>=<value>

        For example:
            DETAGRANDMERE_SOLVER_TOLERANCE=1e-08
            DETAGRANDMERE_MESH_TARGET_EDGE_LENGTH=0.05
        """
        for key, value in os.environ.items():
            if not key.startswith(self.env_prefix):
                continue

            # Parse variable name: DETAGRANDMERE_SECTION_KEY -> section.key
            stripped = key[len(self.env_prefix):].lower()
            parts = stripped.split("_", 2)

            if len(parts) >= 3:
                section = parts[0]
                field = parts[1]

                if section in self._config:
                    try:
                        # Convert value to appropriate type
                        current = self._config[section].get(field, "")
                        self._config[section][field] = _convert_value(value, current)
                    except (ValueError, TypeError):
                        # Skip invalid values
                        pass

    def get(self, section: str, key: str, default=None) -> Any:
        """Get a configuration value.

        Parameters
        ----------
        section : str
            Configuration section name (e.g., "solver", "mesh").
        key : str
            Configuration key within the section.
        default : any, optional
            Default value if the key is not found.

        Returns
        -------
        any
            Configuration value or default.
        """
        return self._config.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: Any) -> None:
        """Set a configuration value.

        Parameters
        ----------
        section : str
            Configuration section name.
        key : str
            Configuration key within the section.
        value : any
            Value to set.
        """
        if section not in self._config:
            self._config[section] = {}
        self._config[section][key] = value

    # -------------------------------------------------------------------
    # Validation
#    ----------------------------------------------------------------

    def validate(self) -> dict:
        """Validate the current configuration against the schema.

        Returns
        -------
        dict
            Validation result with keys:
            - 'valid': True if all required fields are present and types match
            - 'errors': list of validation error messages
            - 'warnings': list of warning messages (e.g., deprecated fields)
        """
        errors = []
        warnings = []

        for section, schema in self.SCHEMA.items():
            config_section = self._config.get(section, {})

            # Check required fields
            for req_field in schema.get("required", []):
                if req_field not in config_section:
                    errors.append(f"Missing required field: {section}.{req_field}")

            # Check types
            for field, expected_type in schema.get("types", {}).items():
                if field in config_section:
                    value = config_section[field]
                    if isinstance(expected_type, tuple):
                        if not isinstance(value, expected_type):
                            errors.append(
                                f"Type mismatch: {section}.{field} should be "
                                f"{expected_type}, got {type(value)}"
                            )
                    else:
                        if not isinstance(value, expected_type):
                            errors.append(
                                f"Type mismatch: {section}.{field} should be "
                                f"{expected_type}, got {type(value)}"
                            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }


def _convert_value(value_str: str, current_value: Any) -> Any:
    """Convert a string value to the appropriate Python type.

    Parameters
    ----------
    value_str : str
        String value from environment variable.
    current_value : any
        Current configuration value (used for type hinting).

    Returns
    -------
    any
        Converted value in the appropriate type.
    """
    # Try to convert to numeric types
    try:
        if "." in value_str or "e" in value_str.lower():
            return float(value_str)
        else:
            return int(value_str)
    except ValueError:
        pass

    # Handle boolean values
    if value_str.lower() == "true":
        return True
    if value_str.lower() == "false":
        return False

    # Default: return as string
    return value_str


class ConfigTemplateManager:
    """Manage configuration templates for common antenna types.

    This class provides methods for creating and loading default
    configuration templates for different antenna geometries.
    """

    TEMPLATES = {
        "dipole": {
            "solver": {"frequency_hz": 1e9, "solver_type": "EFIE"},
            "mesh": {"target_edge_length": 0.05},
            "boundary": {"outer_bc": "radiation", "inner_bc": "pec"},
        },
        "patch": {
            "solver": {"frequency_hz": 2.4e9, "solver_type": "CFIE"},
            "mesh": {"target_edge_length": 0.02},
            "boundary": {"outer_bc": "radiation", "inner_bc": "pec"},
        },
        "loop": {
            "solver": {"frequency_hz": 500e6, "solver_type": "MFIE"},
            "mesh": {"target_edge_length": 0.1},
            "boundary": {"outer_bc": "radiation", "inner_bc": "pec"},
        },
    }

    @classmethod
    def get_template(cls, antenna_type: str) -> dict:
        """Get a configuration template for an antenna type.

        Parameters
        ----------
        antenna_type : str
            Antenna type: "dipole", "patch", or "loop".

        Returns
        -------
        dict
            Configuration template dictionary.

        Raises
        ------
        ValueError
            If the antenna type is not supported.
        """
        if antenna_type not in cls.TEMPLATES:
            raise ValueError(
                f"Unknown antenna type: {antenna_type}",
                context={"available": list(cls.TEMPLATES.keys())},
            )

        return dict(cls.TEMPLATES[antenna_type])

    @classmethod
    def save_template(cls, name: str, template: dict, output_dir: str = "configs/templates/") -> str:
        """Save a custom configuration template.

        Parameters
        ----------
        name : str
            Template name (e.g., "my_custom_antenna").
        template : dict
            Template configuration dictionary.
        output_dir : str, default="configs/templates/"
            Directory for saving templates.

        Returns
        -------
        str
            Path to the saved template file.
        """
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"{name}.yaml")

        with open(path, "w") as f:
            yaml.dump(template, f, default_flow_style=False)

        return path
