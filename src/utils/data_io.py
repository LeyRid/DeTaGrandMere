"""Data I/O utilities for Touchstone and HDF5 formats.

This module provides high-level interfaces for exporting and importing
simulation data in standard file formats:

- **Touchstone**: S-parameter files (.s1p through .s4p) per IEC 61746-3
- **HDF5**: Hierarchical field data with compression support

Both exporters include metadata embedding (date, version, simulation
parameters) and read-back validation for data integrity.

Example usage::

    from src.utils.data_io import HDF5Exporter, HDF5Importer

    # Export field data to HDF5
    exporter = HDF5Exporter(compression=True)
    exporter.export_fields(
        near_field=E_near,
        far_field=E_far,
        frequencies=freqs,
        output_file="simulation_results.h5",
    )

    # Import and validate
    importer = HDF5Importer()
    data = importer.import_hdf5("simulation_results.h5")
"""

from __future__ import annotations

import os
import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    import h5py
    HAS_HDF5 = True
except ImportError:
    HAS_HDF5 = False
    h5py = None  # type: ignore[misc]


class HDF5Exporter:
    """Export simulation data to HDF5 format.

    Parameters
    ----------
    compression : bool, default=True
        Use gzip compression for field data arrays.
    compression_level : int, default=4
        Compression level (1-9). Higher = slower but smaller files.
    """

    def __init__(self, compression: bool = True, compression_level: int = 4) -> None:
        """Initialise the HDF5 exporter."""
        if not HAS_HDF5:
            raise ImportError(
                "h5py is required for HDF5 export. Install with: pip install h5py"
            )

        self.compression = compression
        self.compression_level = compression_level

    def export_fields(
        self,
        near_field: np.ndarray,
        far_field: np.ndarray,
        frequencies: np.ndarray,
        output_file: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """Export field data to an HDF5 file with hierarchical organization.

        Parameters
        ----------
        near_field : np.ndarray
            Near-field E/H data, shape ``(N_points, 3)`` for each component.
        far_field : np.ndarray
            Far-field E_theta/E_phi data, shape ``(N_angles,)``.
        frequencies : np.ndarray
            Frequency array in Hz with shape ``(N_freq,)``.
        output_file : str
            Path for the output HDF5 file (e.g., 'results.h5').
        metadata : dict, optional
            Arbitrary metadata dictionary for the HDF5 root group.

        Returns
        -------
        str
            Full path of the written file.

        Raises
        ------
        ImportError
            If h5py is not installed.
        OSError
            If file writing fails.
        """
        near_field = np.asarray(near_field)
        far_field = np.asarray(far_field)
        frequencies = np.asarray(frequencies)

        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)

        with h5py.File(output_file, "w") as hf:
            # Write metadata group
            meta_grp = hf.create_group("metadata")
            meta_grp.attrs["version"] = "1.0"
            meta_grp.attrs["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            meta_grp.attrs["description"] = "CaAD electromagnetic simulation results"

            if metadata:
                for key, val in metadata.items():
                    meta_grp.attrs[key] = str(val)

            # Write frequency data
            freqs_ds = hf.create_dataset("frequencies", data=frequencies)
            freqs_ds.attrs["unit"] = "Hz"

            # Write near-field data (E and H components)
            nf_grp = hf.create_group("near_field")
            if self.compression:
                kwargs = {"compression": "gzip", "compression_opts": self.compression_level}
            else:
                kwargs = {}

            E_near = near_field[:, :3]  # E-field (x, y, z)
            H_near = near_field[:, 3:] if near_field.shape[1] > 3 else np.zeros_like(E_near)
            hf.create_dataset("near_field/E_field", data=E_near, **kwargs)
            hf.create_dataset("near_field/H_field", data=H_near, **kwargs)

            # Write far-field data
            ff_grp = hf.create_group("far_field")
            if self.compression:
                kwargs = {"compression": "gzip", "compression_opts": self.compression_level}
            else:
                kwargs = {}
            hf.create_dataset("far_field/E_theta", data=np.real(far_field), **kwargs)
            hf.create_dataset("far_field/E_phi", data=np.imag(far_field), **kwargs)

        logger.info("Wrote HDF5 file: %s (%d freq points)", output_file, len(frequencies))
        return output_file

    def export_sparams(
        self,
        frequencies: np.ndarray,
        s_params: np.ndarray,
        output_file: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """Export S-parameter data to an HDF5 file.

        Parameters
        ----------
        frequencies : np.ndarray
            Frequency array in Hz with shape ``(N_freq,)``.
        s_params : np.ndarray
            S-parameter matrix with shape ``(N_freq, N_ports, N_ports)``.
        output_file : str
            Path for the output HDF5 file (e.g., 'sparams.h5').
        metadata : dict, optional
            Arbitrary metadata dictionary.

        Returns
        -------
        str
            Full path of the written file.
        """
        frequencies = np.asarray(frequencies)
        s_params = np.asarray(s_params)

        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)

        with h5py.File(output_file, "w") as hf:
            meta_grp = hf.create_group("metadata")
            meta_grp.attrs["version"] = "1.0"
            meta_grp.attrs["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            if metadata:
                for key, val in metadata.items():
                    meta_grp.attrs[key] = str(val)

            hf.create_dataset("frequencies", data=frequencies)
            hf.create_dataset("s_parameters", data=s_params)

        logger.info("Wrote S-parameter HDF5 file: %s (%d points)", output_file, len(frequencies))
        return output_file


class HDF5Importer:
    """Import simulation data from HDF5 files.

    Parameters
    ----------
    validate : bool, default=True
        Validate data integrity after import (shape checks, NaN detection).
    """

    def __init__(self, validate: bool = True) -> None:
        """Initialise the HDF5 importer."""
        if not HAS_HDF5:
            raise ImportError(
                "h5py is required for HDF5 import. Install with: pip install h5py"
            )
        self.validate = validate

    def import_hdf5(self, input_file: str) -> dict:
        """Import all data from an HDF5 file.

        Parameters
        ----------
        input_file : str
            Path to the HDF5 file (e.g., 'results.h5').

        Returns
        -------
        dict
            Dictionary with keys matching the HDF5 structure:
            - 'metadata': dict of attributes from metadata group
            - 'frequencies': np.ndarray of frequencies in Hz
            - 'near_field/E_field': np.ndarray
            - 'near_field/H_field': np.ndarray
            - 'far_field/E_theta': np.ndarray
            - 'far_field/E_phi': np.ndarray

        Raises
        ------
        FileNotFoundError
            If the input file does not exist.
        ValueError
            If the HDF5 structure is invalid or data is corrupted.
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"HDF5 file not found: {input_file}")

        result: dict = {}

        with h5py.File(input_file, "r") as hf:
            # Read metadata
            if "metadata" in hf:
                meta_grp = hf["metadata"]
                result["metadata"] = {
                    k: v for k, v in meta_grp.attrs.items()
                }

            # Read frequencies
            if "frequencies" in hf:
                freqs = np.array(hf["frequencies"])
                result["frequencies"] = freqs

            # Read near-field data
            if "near_field" in hf:
                nf_grp = hf["near_field"]
                if "E_field" in nf_grp:
                    result["near_field/E_field"] = np.array(nf_grp["E_field"])
                if "H_field" in nf_grp:
                    result["near_field/H_field"] = np.array(nf_grp["H_field"])

            # Read far-field data
            if "far_field" in hf:
                ff_grp = hf["far_field"]
                if "E_theta" in ff_grp:
                    result["far_field/E_theta"] = np.array(ff_grp["E_theta"])
                if "E_phi" in ff_grp:
                    result["far_field/E_phi"] = np.array(ff_grp["E_phi"])

            # Read S-parameters if present
            if "s_parameters" in hf:
                result["s_parameters"] = np.array(hf["s_parameters"])

        # Validate if requested
        if self.validate:
            self._validate_result(result)

        logger.info("Read HDF5 file: %s (%d datasets)", input_file, len(result))
        return result

    def import_partial(
        self,
        input_file: str,
        datasets: list[str],
    ) -> dict:
        """Import only specific datasets from an HDF5 file.

        Parameters
        ----------
        input_file : str
            Path to the HDF5 file.
        datasets : list[str]
            List of dataset paths to load (e.g., ['frequencies', 'near_field/E_field']).

        Returns
        -------
        dict
            Dictionary with only the requested datasets.
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"HDF5 file not found: {input_file}")

        result: dict = {}

        with h5py.File(input_file, "r") as hf:
            for ds_path in datasets:
                try:
                    result[ds_path] = np.array(hf[ds_path])
                except (KeyError, TypeError):
                    logger.warning("Dataset '%s' not found in %s", ds_path, input_file)

        return result

    def _validate_result(self, result: dict) -> None:
        """Validate imported data for consistency."""
        for key, value in result.items():
            if isinstance(value, np.ndarray):
                if np.any(np.isnan(value)) or np.any(np.isinf(value)):
                    raise ValueError(f"Dataset '{key}' contains NaN or Inf values")
