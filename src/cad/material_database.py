"""Material database module for electromagnetic simulation materials.

This module provides a comprehensive material management system including:
- A Material dataclass representing electromagnetic material properties
- A MaterialDatabase class for managing collections of materials with persistence
- Dispersive model classes (Debye, Lorentz, Drude) for frequency-dependent behavior
- Frequency interpolation utilities for complex permittivity evaluation

Example usage::

    from material_database import MaterialDatabase, DebyeModel

    db = MaterialDatabase()

    # Query a built-in material
    copper = db.get_material("copper")
    print(f"Copper conductivity: {copper.conductivity:.2e} S/m")

    # Add a custom dispersive material
    model = DebyeModel(eps_inf=3.0, eps_0=1.5, tau=1e-12)
    frequencies = np.logspace(8, 12, 100)
    eps_complex = model.get_permittivity(frequencies)

    # Save and reload material database
    db.save_to_file("materials.json")
    db.load_from_file("materials.json")
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict, fields
from typing import Dict, List, Optional, Union

import numpy as np

from .errors import MaterialError, CADError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Material:
    """Represents an electromagnetic material with its constitutive properties.

    Attributes
    ----------
    name : str
        Human-readable identifier for the material.
    permittivity : float
        Absolute permittivity in F/m (vacuum default 8.854e-12).
    permeability : float
        Absolute permeability in H/m (vacuum default 1.257e-6).
    conductivity : float
        Electrical conductivity in S/m (default 0.0).
    loss_tangent : float
        Dielectric loss tangent, dimensionless (default 0.0).
    frequency_points : np.ndarray or None
        Array of reference frequencies (Hz) where material data is defined.
    permittivity_at_freq : np.ndarray or None
        Complex permittivity values corresponding to *frequency_points*.
    """

    name: str = "unnamed"
    permittivity: float = 8.854e-12
    permeability: float = 1.257e-6
    conductivity: float = 0.0
    loss_tangent: float = 0.0
    frequency_points: Optional[np.ndarray] = None
    permittivity_at_freq: Optional[np.ndarray] = None

    def __post_init__(self) -> None:
        if self.frequency_points is not None and self.permittivity_at_freq is not None:
            freqs = np.asarray(self.frequency_points, dtype=np.float64)
            eps = np.asarray(self.permittivity_at_freq, dtype=np.complex128)
            if len(freqs) != len(eps):
                raise MaterialError(
                    f"Mismatch between frequency_points ({len(freqs)}) "
                    f"and permittivity_at_freq ({len(eps)}) for '{self.name}'."
                )

    # ------------------------------------------------------------------ serialization helpers -------------------------------

    def to_dict(self) -> dict:
        """Return a serialisable dictionary representation.

        Returns
        -------
        dict
            Material fields with numpy arrays converted to lists.
        """
        d = asdict(self)
        if self.frequency_points is not None:
            d["frequency_points"] = list(self.frequency_points)
        if self.permittivity_at_freq is not None:
            d["permittivity_at_freq"] = [
                [eps.real, eps.imag] for eps in self.permittivity_at_freq
            ]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Material":
        """Reconstruct a Material from a serialisable dictionary.

        Parameters
        ----------
        data : dict
            Dictionary produced by :meth:`to_dict`.

        Returns
        -------
        Material
            Restored material instance.
        """
        freq = data.get("frequency_points")
        eps = data.get("permittivity_at_freq")
        if freq is not None:
            freq = np.array(freq, dtype=np.float64)
        if eps is not None:
            eps = np.array([[r, i] for r, i in eps], dtype=np.complex128)
        return cls(
            name=data["name"],
            permittivity=data["permittivity"],
            permeability=data["permeability"],
            conductivity=data["conductivity"],
            loss_tangent=data["loss_tangent"],
            frequency_points=freq,
            permittivity_at_freq=eps,
        )


# ---------------------------------------------------------------------------
# Dispersive models
# ---------------------------------------------------------------------------


class DebyeModel:
    """Debye frequency-dependent dielectric model.

    The complex relative permittivity follows the classic Debye relation::

        eps_r(f) = eps_inf + (eps_0 - eps_inf) / (1 + j * 2*pi*f*tau)

    Parameters
    ----------
    eps_inf : float
        High-frequency relative permittivity (limit as f -> infinity).
    eps_0 : float
        Static (zero-frequency) relative permittivity.
    tau : float
        Relaxation time in seconds.
    """

    def __init__(self, eps_inf: float = 1.0, eps_0: float = 2.5, tau: float = 1e-12) -> None:
        self.eps_inf = float(eps_inf)
        self.eps_0 = float(eps_0)
        self.tau = float(tau)

    def get_permittivity(self, frequency: np.ndarray) -> np.ndarray:
        """Evaluate complex relative permittivity at the given frequencies.

        Parameters
        ----------
        frequency : np.ndarray
            Frequency values in Hz.

        Returns
        -------
        np.ndarray
            Complex relative permittivity array with the same shape as *frequency*.
        """
        freq = np.asarray(frequency, dtype=np.float64)
        omega = 2.0 * np.pi * freq
        return self.eps_inf + (self.eps_0 - self.eps_inf) / (1.0 + 1j * omega * self.tau)


class LorentzModel:
    """Lorentz oscillator frequency-dependent dielectric model.

    The complex relative permittivity follows the Lorentz resonance::

        eps_r(f) = eps_inf + (eps_0 - eps_inf) / (1 - (f/f0)^2 + j*gamma*f)

    Parameters
    ----------
    eps_inf : float
        High-frequency relative permittivity.
    eps_0 : float
        Static relative permittivity.
    f0 : float
        Resonance frequency in Hz.
    gamma : float
        Damping coefficient (Hz^-1).
    """

    def __init__(
        self,
        eps_inf: float = 1.0,
        eps_0: float = 3.0,
        f0: float = 1e9,
        gamma: float = 1e7,
    ) -> None:
        self.eps_inf = float(eps_inf)
        self.eps_0 = float(eps_0)
        self.f0 = float(f0)
        self.gamma = float(gamma)

    def get_permittivity(self, frequency: np.ndarray) -> np.ndarray:
        """Evaluate complex relative permittivity at the given frequencies.

        Parameters
        ----------
        frequency : np.ndarray
            Frequency values in Hz.

        Returns
        -------
        np.ndarray
            Complex relative permittivity array.
        """
        freq = np.asarray(frequency, dtype=np.float64)
        f2 = freq ** 2
        denom = 1.0 - (f2 / self.f0 ** 2) + 1j * self.gamma * freq / self.f0
        return self.eps_inf + (self.eps_0 - self.eps_inf) / denom


class DrudeModel:
    """Drude free-electron frequency-dependent dielectric model.

    The complex relative permittivity follows the Drude relation::

        eps_r(f) = 1 - omega_p^2 / (f^2 + j*gamma*f)

    Parameters
    ----------
    omega_p : float
        Plasma angular frequency in rad/s.
    gamma : float
        Collision damping rate in rad/s.
    """

    def __init__(self, omega_p: float = 1.4e16, gamma: float = 1.0e13) -> None:
        self.omega_p = float(omega_p)
        self.gamma = float(gamma)

    def get_permittivity(self, frequency: np.ndarray) -> np.ndarray:
        """Evaluate complex relative permittivity at the given frequencies.

        Parameters
        ----------
        frequency : np.ndarray
            Frequency values in Hz.  (Internally converted to angular frequency.)

        Returns
        -------
        np.ndarray
            Complex relative permittivity array.
        """
        freq = np.asarray(frequency, dtype=np.float64)
        omega = 2.0 * np.pi * freq
        denom = omega ** 2 + 1j * self.gamma * omega
        return 1.0 - (self.omega_p ** 2) / denom


# ---------------------------------------------------------------------------
# Material Database
# ---------------------------------------------------------------------------


def _make_material(
    name: str, eps_r: float = 1.0, mu_r: float = 1.0, sigma: float = 0.0, loss_tangent: float = 0.0
) -> Material:
    """Helper to create a :class:`Material` from relative constants."""
    return Material(
        name=name,
        permittivity=float(eps_r) * 8.854e-12,
        permeability=float(mu_r) * 1.257e-6,
        conductivity=float(sigma),
        loss_tangent=float(loss_tangent),
    )


class MaterialDatabase:
    """Manages a collection of :class:`Material` instances with persistence support.

    The database ships with a small built-in library (copper, aluminium, FR4,
    air, gold) that is populated on construction.  Custom materials can be
    added and the full collection persisted to / restored from JSON.

    Example usage::

        db = MaterialDatabase()
        db.add_material("my_dielectric", Material(name="my_dielectric", eps_r=4.5))
        for name in db.list_materials():
            print(name)
        db.save_to_file("custom_materials.json")
    """

    def __init__(self) -> None:
        self._materials: Dict[str, Material] = {}

        # Populate built-in library
        self._materials["copper"] = _make_material(
            "copper", eps_r=1.0, mu_r=1.0, sigma=5.8e7, loss_tangent=0.0
        )
        self._materials["aluminum"] = _make_material(
            "aluminum", eps_r=1.0, mu_r=1.0, sigma=3.77e7, loss_tangent=0.0
        )
        self._materials["FR4"] = _make_material(
            "FR4", eps_r=4.5, mu_r=1.0, sigma=0.001, loss_tangent=0.02
        )
        self._materials["air"] = _make_material(
            "air", eps_r=1.0, mu_r=1.0, sigma=0.0, loss_tangent=0.0
        )
        self._materials["gold"] = _make_material(
            "gold", eps_r=1.0, mu_r=1.0, sigma=4.1e7, loss_tangent=0.0
        )

    # ------------------------------------------------------------------ public API -------------------------------

    def add_material(self, name: str, material: Material) -> None:
        """Add a material to the database.

        Parameters
        ----------
        name : str
            Unique material identifier.
        material : Material
            The material object to store.

        Raises
        ------
        MaterialError
            If *name* already exists in the database.
        """
        if name in self._materials:
            raise MaterialError(f"Material '{name}' already exists.")
        self._materials[name] = material

    def get_material(self, name: str) -> Optional[Material]:
        """Retrieve a material by name.

        Parameters
        ----------
        name : str
            Material identifier.

        Returns
        -------
        Material or None
            The requested material, or ``None`` if not found.
        """
        return self._materials.get(name)

    def remove_material(self, name: str) -> None:
        """Remove a material from the database.

        Parameters
        ----------
        name : str
            Material identifier.

        Raises
        ------
        MaterialError
            If *name* is not present.
        """
        if name not in self._materials:
            raise MaterialError(f"Material '{name}' not found.")
        del self._materials[name]

    def list_materials(self) -> List[str]:
        """Return a sorted list of all material names.

        Returns
        -------
        list[str]
            Sorted material identifiers.
        """
        return sorted(self._materials.keys())

    # ---------------------------------------------------------------- persistence ---------------------------------

    def save_to_file(self, path: str) -> None:
        """Persist the entire database to a JSON file.

        Parameters
        ----------
        path : str
            Destination file path.
        """
        data = {name: mat.to_dict() for name, mat in self._materials.items()}
        with open(path, "w") as fh:
            json.dump(data, fh, indent=2)
        logger.info("Saved %d materials to %s", len(data), path)

    def load_from_file(self, path: str) -> None:
        """Load a database from a previously saved JSON file.

        Existing materials are replaced by the loaded set.

        Parameters
        ----------
        path : str
            Source JSON file path.

        Raises
        ------
        CADError
            If the file does not exist or contains invalid data.
        """
        try:
            with open(path, "r") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            raise CADError(f"File not found: {path}")
        except json.JSONDecodeError as exc:
            raise CADError(f"Invalid JSON in {path}: {exc}")

        self._materials.clear()
        for name, mat_dict in data.items():
            self._materials[name] = Material.from_dict(mat_dict)
        logger.info("Loaded %d materials from %s", len(data), path)


# ---------------------------------------------------------------------------
# Interpolation helper
# ---------------------------------------------------------------------------


def interpolate_material_properties(
    material: Material, frequencies: np.ndarray
) -> np.ndarray:
    """Interpolate complex permittivity for a material at arbitrary frequencies.

    If the material already carries frequency-dependent data
    (*frequency_points* / *permittivity_at_freq*), linear interpolation is
    performed on both real and imaginary parts.  Otherwise a constant value
    equal to ``material.permittivity`` is returned (real part only).

    Parameters
    ----------
    material : Material
        The material whose properties are being interpolated.
    frequencies : np.ndarray
            Frequency values in Hz where permittivity is desired.

    Returns
    -------
    np.ndarray
        Complex permittivity array with the same shape as *frequencies*.
    """
    freqs = np.asarray(frequencies, dtype=np.float64)
    if material.frequency_points is not None and material.permittivity_at_freq is not None:
        # Interpolate real and imaginary parts independently
        freq_arr = material.frequency_points
        eps_real = [eps.real for eps in material.permittivity_at_freq]
        eps_imag = [eps.imag for eps in material.permittivity_at_freq]

        interp_real = np.interp(freqs, freq_arr, eps_real)
        interp_imag = np.interp(freqs, freq_arr, eps_imag)
        return interp_real + 1j * interp_imag
    else:
        # Static permittivity -- return as complex (imaginary part from loss tangent)
        real_part = material.permittivity
        imag_part = material.permittivity * material.loss_tangent
        return np.full_like(freqs, real_part + 1j * imag_part, dtype=np.complex128)


# ---------------------------------------------------------------------------
# Module-level example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    # Demonstrate built-in materials
    db = MaterialDatabase()
    print("Built-in materials:", db.list_materials())

    copper = db.get_material("copper")
    print(f"Copper: eps={copper.permittivity:.3e}, sigma={copper.conductivity:.2e}")

    # Demonstrate dispersion models
    freqs = np.logspace(8, 12, 50)
    debye = DebyeModel(eps_inf=2.5, eps_0=4.0, tau=1e-12)
    print(f"Debye permittivity at 1 GHz: {debye.get_permittivity(np.array([1e9]))[0]:.4f}")

    lorentz = LorentzModel(eps_inf=1.5, eps_0=3.0, f0=1e9, gamma=1e7)
    print(f"Lorentz permittivity at resonance: {lorentz.get_permittivity(np.array([1e9]))[0]:.4f}")

    drude = DrudeModel(omega_p=1.4e16, gamma=1e13)
    print(f"Drude permittivity at 1 THz: {drude.get_permittivity(np.array([1e12]))[0]:.4f}")

    # Demonstrate interpolation
    mat = Material(
        name="test",
        frequency_points=np.array([1e8, 1e9, 1e10]),
        permittivity_at_freq=np.array([3.0 + 0.1j, 2.5 + 0.05j, 2.0 + 0.02j]),
    )
    interp_eps = interpolate_material_properties(mat, np.array([5e8]))
    print(f"Interpolated permittivity at 500 MHz: {interp_eps[0]:.4f}")

    # Demonstrate persistence
    db.save_to_file("/tmp/test_materials.json")
    db2 = MaterialDatabase()
    db2.load_from_file("/tmp/test_materials.json")
    print("Loaded materials:", db2.list_materials())
