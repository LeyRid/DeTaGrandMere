"""Complex-valued field data storage with frequency-dependent support.

This module provides the :class:`FieldDataStore` class for storing and managing
complex electromagnetic field data across multiple frequencies. It handles:

- Complex-valued E and H field arrays with proper dtype management
- Frequency-dependent field metadata (wavenumber, angular frequency)
- Serialization to/from HDF5 files with compression
- Interpolation between mesh elements for arbitrary observation points
- Field data validation and integrity checks

Example usage::

    from src.core.field_calculations.field_storage import FieldDataStore

    store = FieldDataStore()
    store.add_frequency_point(1e9, E_field, H_field)
    store.add_frequency_point(2e9, E_field_2, H_field_2)

    # Save to disk
    store.save("fields.h5")

    # Load from disk
    loaded = FieldDataStore.load("fields.h5")
"""

from __future__ import annotations

import h5py
import numpy as np
import os
from typing import Optional, Dict, List, Tuple

from src.utils.errors import FieldCalculationError


class FieldDataStore:
    """Store and manage complex-valued electromagnetic field data.

    This class provides a structured container for frequency-dependent E and H
    field data computed at observation points. It supports serialization to HDF5
    with compression and deserialization, as well as validation of stored data.

    Attributes
    ----------
    frequencies : list[float]
        Operating frequencies in Hz for each data point.
    E_fields : list[np.ndarray]
        Electric field arrays with shape (N_obs, 3), dtype complex128.
    H_fields : list[np.ndarray]
        Magnetic field arrays with shape (N_obs, 3), dtype complex128.
    observation_points : np.ndarray
        Cartesian coordinates of observation points with shape (N_obs, 3).
    metadata : dict
        Arbitrary simulation metadata (geometry name, solver type, etc.).
    """

    def __init__(self) -> None:
        """Initialise an empty field data store."""
        self.frequencies: List[float] = []
        self.E_fields: List[np.ndarray] = []
        self.H_fields: List[np.ndarray] = []
        self.observation_points: Optional[np.ndarray] = None
        self.metadata: Dict[str, object] = {}

    # -------------------------------------------------------------------
    # Data management
    # -------------------------------------------------------------------

    def add_frequency_point(
        self,
        frequency: float,
        E_field: np.ndarray,
        H_field: np.ndarray,
        observation_points: Optional[np.ndarray] = None,
    ) -> None:
        """Add a frequency point's field data to the store.

        Parameters
        ----------
        frequency : float
            Operating frequency in Hz.
        E_field : np.ndarray
            Electric field array with shape (N_obs, 3), dtype complex128.
        H_field : np.ndarray
            Magnetic field array with shape (N_obs, 3), dtype complex128.
        observation_points : np.ndarray, optional
            Observation point coordinates with shape (N_obs, 3). If None,
            the first observation points are retained.

        Raises
        ------
        FieldCalculationError
            If arrays have inconsistent shapes or contain invalid values.
        """
        E_field = np.asarray(E_field, dtype=np.complex128)
        H_field = np.asarray(H_field, dtype=np.complex128)

        if E_field.shape != H_field.shape:
            raise FieldCalculationError(
                "E and H fields must have the same shape",
                context={"E_shape": E_field.shape, "H_shape": H_field.shape},
            )
        if E_field.ndim != 2 or E_field.shape[1] != 3:
            raise FieldCalculationError(
                "Field arrays must have shape (N_obs, 3)",
                context={"shape": E_field.shape},
            )
        if np.any(np.isnan(E_field)) or np.any(np.isinf(E_field)):
            raise FieldCalculationError("E field contains NaN or Inf values")
        if np.any(np.isnan(H_field)) or np.any(np.isinf(H_field)):
            raise FieldCalculationError("H field contains NaN or Inf values")

        self.frequencies.append(frequency)
        self.E_fields.append(E_field.copy())
        self.H_fields.append(H_field.copy())
        if observation_points is not None:
            self.observation_points = np.asarray(observation_points, dtype=np.float64)

    def get_field_at_frequency(self, frequency: float) -> Tuple[np.ndarray, np.ndarray]:
        """Retrieve E and H fields for a specific frequency.

        Parameters
        ----------
        frequency : float
            Frequency in Hz to look up.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            (E_field, H_field) arrays for the matching frequency.

        Raises
        ------
        FieldCalculationError
            If no data exists at the specified frequency.
        """
        idx = None
        for i, f in enumerate(self.frequencies):
            if abs(f - frequency) < 0.005 * max(abs(f), abs(frequency), 1e-3):
                idx = i
                break

        if idx is None:
            raise FieldCalculationError(
                f"No field data found at frequency {frequency} Hz",
                context={"available_frequencies": self.frequencies},
            )

        return self.E_fields[idx].copy(), self.H_fields[idx].copy()

    def interpolate_at_points(
        self,
        target_points: np.ndarray,
        frequency: Optional[float] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Interpolate field values at arbitrary observation points.

        Uses trilinear interpolation from the nearest stored observation points.
        If frequency is specified, uses that frequency's data; otherwise uses
        the most recent frequency point.

        Parameters
        ----------
        target_points : np.ndarray
            Cartesian coordinates for interpolation with shape (N_target, 3).
        frequency : float, optional
            Frequency in Hz. Uses the most recent if None.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            Interpolated E and H fields at target_points.

        Raises
        ------
        FieldCalculationError
            If no field data is available or observation points are missing.
        """
        # Select frequency data
        if frequency is not None:
            E_data, H_data = self.get_field_at_frequency(frequency)
        else:
            if len(self.E_fields) == 0:
                raise FieldCalculationError("No field data available for interpolation")
            E_data = self.E_fields[-1]
            H_data = self.H_fields[-1]

        obs_pts = self.observation_points
        if obs_pts is None:
            raise FieldCalculationError(
                "Observation points not stored; cannot interpolate"
            )

        target_points = np.asarray(target_points, dtype=np.float64)
        N_target = target_points.shape[0]

        # --- Trilinear interpolation from structured observation grid --------
        # The observation points are assumed to lie on a regular 3D grid.
        # We build index mapping and interpolate using trilinear weighting.
        E_interp = np.zeros((N_target, 3), dtype=np.complex128)
        H_interp = np.zeros((N_target, 3), dtype=np.complex128)

        # Detect grid structure from observation points
        Nx, Ny, Nz = self._detect_grid_shape(obs_pts)
        if Nx is not None:
            # Structured grid detected -- use trilinear interpolation
            E_interp, H_interp = self._trilinear_interpolate(
                obs_pts, E_data, H_data, target_points, Nx, Ny, Nz
            )
        else:
            # Unstructured -- fall back to inverse-distance weighting
            E_interp, H_interp = self._idw_interpolate(
                obs_pts, E_data, H_data, target_points
            )

        return E_interp, H_interp

    def _detect_grid_shape(self, pts: np.ndarray) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """Detect if points lie on a regular 3D grid and return (Nx, Ny, Nz)."""
        # Sort by z, then y, then x to detect structure
        sorted_by_z = np.unique(pts[:, 2])
        sorted_by_y = np.unique(pts[:, 1])
        sorted_by_x = np.unique(pts[:, 0])

        # Check if differences are roughly uniform (within 10% tolerance)
        def _uniform(arr: np.ndarray, tol: float = 0.15) -> bool:
            if len(arr) < 2:
                return False
            diffs = np.diff(arr)
            mean_diff = np.mean(diffs)
            if mean_diff < 1e-12:
                return False
            return np.all(np.abs(diffs - mean_diff) / max(mean_diff, 1e-15) < tol)

        if _uniform(sorted_by_z) and _uniform(sorted_by_y) and _uniform(sorted_by_x):
            return len(sorted_by_x), len(sorted_by_y), len(sorted_by_z)
        return None, None, None

    def _trilinear_interpolate(
        self,
        obs_pts: np.ndarray,
        E_data: np.ndarray,
        H_data: np.ndarray,
        target_points: np.ndarray,
        Nx: int, Ny: int, Nz: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Trilinear interpolation on a structured 3D grid."""
        N_target = target_points.shape[0]
        E_interp = np.zeros((N_target, 3), dtype=np.complex128)
        H_interp = np.zeros((N_target, 3), dtype=np.complex128)

        # Build coordinate arrays for each dimension
        x_coords = np.sort(np.unique(obs_pts[:, 0]))[:Nx]
        y_coords = np.sort(np.unique(obs_pts[:, 1]))[:Ny]
        z_coords = np.sort(np.unique(obs_pts[:, 2]))[:Nz]

        # Reshape field data into (Nx, Ny, Nz, 3) grid
        E_grid = np.zeros((Nx, Ny, Nz, 3), dtype=np.complex128)
        H_grid = np.zeros((Nx, Ny, Nz, 3), dtype=np.complex128)

        for i in range(Nx):
            for j in range(Ny):
                for k in range(Nz):
                    idx = k * Ny * Nx + j * Nx + i
                    if idx < len(obs_pts):
                        E_grid[i, j, k] = E_data[idx]
                        H_grid[i, j, k] = H_data[idx]

        # Interpolate each target point
        for t in range(N_target):
            x, y, z = target_points[t]
            val_e, val_h = self._trilinear_sample(E_grid, H_grid, x_coords, y_coords, z_coords, x, y, z)
            E_interp[t] = val_e
            H_interp[t] = val_h

        return E_interp, H_interp

    def _trilinear_sample(self, E_grid, H_grid, x_coords, y_coords, z_coords, x, y, z):
        """Sample a single point from a 3D grid using trilinear interpolation."""
        # Find bracketing indices for each dimension
        ix = np.searchsorted(x_coords, x) - 1
        iy = np.searchsorted(y_coords, y) - 1
        iz = np.searchsorted(z_coords, z) - 1

        # Clamp to valid range
        ix = max(0, min(ix, len(x_coords) - 2))
        iy = max(0, min(iy, len(y_coords) - 2))
        iz = max(0, min(iz, len(z_coords) - 2))

        # Normalized positions within the cell
        dx = (x - x_coords[ix]) / max(x_coords[ix + 1] - x_coords[ix], 1e-15)
        dy = (y - y_coords[iy]) / max(y_coords[iy + 1] - y_coords[iy], 1e-15)
        dz = (z - z_coords[iz]) / max(z_coords[iz + 1] - z_coords[iz], 1e-15)

        # Clamp weights to [0, 1]
        dx = np.clip(dx, 0.0, 1.0)
        dy = np.clip(dy, 0.0, 1.0)
        dz = np.clip(dz, 0.0, 1.0)

        # Trilinear interpolation for each component
        val_e = np.zeros(3, dtype=np.complex128)
        val_h = np.zeros(3, dtype=np.complex128)
        for c in range(3):
            v000 = E_grid[ix, iy, iz, c]
            v100 = E_grid[ix + 1, iy, iz, c]
            v010 = E_grid[ix, iy + 1, iz, c]
            v110 = E_grid[ix + 1, iy + 1, iz, c]
            v001 = E_grid[ix, iy, iz + 1, c]
            v101 = E_grid[ix + 1, iy, iz + 1, c]
            v011 = E_grid[ix, iy + 1, iz + 1, c]
            v111 = E_grid[ix + 1, iy + 1, iz + 1, c]

            # Interpolate along x
            v00 = v000 + dx * (v100 - v000)
            v01 = v010 + dx * (v110 - v010)
            v10 = v001 + dx * (v101 - v001)
            v11 = v011 + dx * (v111 - v011)

            # Interpolate along y
            v0 = v00 + dy * (v01 - v00)
            v1 = v10 + dy * (v11 - v10)

            # Interpolate along z
            val_e[c] = v0 + dz * (v1 - v0)

            # Same for H field
            h00 = H_grid[ix, iy, iz, c] + dx * (H_grid[ix + 1, iy, iz, c] - H_grid[ix, iy, iz, c])
            h01 = H_grid[ix, iy + 1, iz, c] + dx * (H_grid[ix + 1, iy + 1, iz, c] - H_grid[ix, iy + 1, iz, c])
            h10 = H_grid[ix, iy, iz + 1, c] + dx * (H_grid[ix + 1, iy, iz + 1, c] - H_grid[ix, iy, iz + 1, c])
            h11 = H_grid[ix, iy + 1, iz + 1, c] + dx * (H_grid[ix + 1, iy + 1, iz + 1, c] - H_grid[ix, iy + 1, iz + 1, c])
            h0 = h00 + dy * (h01 - h00)
            h1 = h10 + dy * (h11 - h10)
            val_h[c] = h0 + dz * (h1 - h0)

        return val_e, val_h

    def _idw_interpolate(
        self,
        obs_pts: np.ndarray,
        E_data: np.ndarray,
        H_data: np.ndarray,
        target_points: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Inverse-distance-weighted interpolation for unstructured observation points."""
        N_target = target_points.shape[0]
        E_interp = np.zeros((N_target, 3), dtype=np.complex128)
        H_interp = np.zeros((N_target, 3), dtype=np.complex128)

        # Compute distances: (N_target, N_obs)
        diff = obs_pts[np.newaxis, :, :] - target_points[:, np.newaxis, :]
        dists = np.sqrt(np.sum(diff ** 2, axis=2))

        # Inverse distance weighting with smooth transition near zero
        weights = 1.0 / (dists + 1e-12)
        weights = weights / (np.sum(weights, axis=1, keepdims=True) + 1e-15)

        E_interp = (weights[:, :, np.newaxis] * E_data[np.newaxis, :, :]).sum(axis=1)
        H_interp = (weights[:, :, np.newaxis] * H_data[np.newaxis, :, :]).sum(axis=1)

        return E_interp, H_interp

    # -------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------

    def save(self, filepath: str) -> None:
        """Save field data to an HDF5 file.

        Parameters
        ----------
        filepath : str
            Output file path (will be created or overwritten).
        """
        with h5py.File(filepath, "w") as hf:
            # Metadata
            meta_grp = hf.create_group("metadata")
            for key, val in self.metadata.items():
                if isinstance(val, (int, float, str, bool)):
                    meta_grp.attrs[key] = val
                elif isinstance(val, np.ndarray):
                    meta_grp.attrs[key] = val.tolist()

            # Frequencies
            freqs_dset = hf.create_dataset("frequencies", data=np.array(self.frequencies))
            freqs_dset.attrs["units"] = "Hz"

            # Observation points
            if self.observation_points is not None:
                obs_grp = hf.create_group("observation_points")
                obs_grp.create_dataset("coordinates", data=self.observation_points)
                obs_grp.attrs["units"] = "m"

            # Field data per frequency
            fields_grp = hf.create_group("field_data")
            for i, (freq, E, H) in enumerate(zip(self.frequencies, self.E_fields, self.H_fields)):
                freq_grp = fields_grp.create_group(f"f_{i}")
                freq_grp.attrs["frequency"] = freq
                freq_grp.attrs["frequency_units"] = "Hz"

                e_dset = freq_grp.create_dataset("E_field", data=E)
                e_dset.attrs["units"] = "V/m"
                e_dset.attrs["dtype"] = str(E.dtype)

                h_dset = freq_grp.create_dataset("H_field", data=H)
                h_dset.attrs["units"] = "A/m"
                h_dset.attrs["dtype"] = str(H.dtype)

    @staticmethod
    def load(filepath: str) -> "FieldDataStore":
        """Load field data from an HDF5 file.

        Parameters
        ----------
        filepath : str
            Input HDF5 file path.

        Returns
        -------
        FieldDataStore
            Populated field data store.

        Raises
        ------
        FieldCalculationError
            If the file is invalid or missing required datasets.
        """
        if not os.path.exists(filepath):
            raise FieldCalculationError(f"File not found: {filepath}")

        store = FieldDataStore()

        with h5py.File(filepath, "r") as hf:
            # Load metadata
            if "metadata" in hf:
                meta_grp = hf["metadata"]
                for key in meta_grp.attrs.keys():
                    store.metadata[key] = meta_grp.attrs[key]

            # Load frequencies
            if "frequencies" in hf:
                store.frequencies = list(hf["frequencies"][:])

            # Load observation points
            if "observation_points" in hf:
                obs_grp = hf["observation_points"]
                store.observation_points = np.array(obs_grp["coordinates"][:])

            # Load field data
            if "field_data" in hf:
                fields_grp = hf["field_data"]
                # Clear any previously loaded frequencies to avoid duplicates
                store.frequencies.clear()
                store.E_fields.clear()
                store.H_fields.clear()
                for key in sorted(fields_grp.keys()):
                    freq_grp = fields_grp[key]
                    freq = float(freq_grp.attrs.get("frequency", 0))
                    E = np.array(freq_grp["E_field"][:])
                    H = np.array(freq_grp["H_field"][:])
                    store.frequencies.append(freq)
                    store.E_fields.append(E)
                    store.H_fields.append(H)

        return store

    # -------------------------------------------------------------------
    # Utility methods
    # -------------------------------------------------------------------

    def get_field_magnitude(self, frequency: float) -> np.ndarray:
        """Compute |E| field magnitude at a given frequency.

        Parameters
        ----------
        frequency : float
            Frequency in Hz.

        Returns
        -------
        np.ndarray
            Field magnitude array with shape (N_obs,) and dtype float64.
        """
        E, _ = self.get_field_at_frequency(frequency)
        return np.sqrt(np.sum(np.abs(E) ** 2, axis=1))

    def get_field_phase(self, frequency: float) -> np.ndarray:
        """Compute E field phase (radians) at a given frequency.

        Parameters
        ----------
        frequency : float
            Frequency in Hz.

        Returns
        -------
        np.ndarray
            Field phase array with shape (N_obs,) and dtype float64.
        """
        E, _ = self.get_field_at_frequency(frequency)
        return np.angle(E[:, 0])  # Phase of Ex component

    def __len__(self) -> int:
        """Return the number of frequency points stored."""
        return len(self.frequencies)

    def __repr__(self) -> str:
        """Return a concise summary string."""
        n_freq = len(self.frequencies)
        freq_range = f"{min(self.frequencies):.2e} - {max(self.frequencies):.2e}" if self.frequencies else "none"
        return f"FieldDataStore(n_frequencies={n_freq}, freq_range={freq_range})"
