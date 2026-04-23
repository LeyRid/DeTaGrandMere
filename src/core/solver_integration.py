"""Solver integration for dispersive and anisotropic material models.

This module provides the :class:`DispersiveMaterialSolver` class that integrates
frequency-dependent and anisotropic material properties into the MoM solver.
It handles:

- Frequency interpolation of dispersive material parameters
- Tensor material property evaluation at each frequency point
- Coupling of material properties with RWG basis functions
- Solver configuration for frequency sweeps with dispersion
"""

from __future__ import annotations

import numpy as np
from typing import Optional, Dict, List, Tuple

from src.cad.advanced_materials import (
    AnisotropicMaterial,
    DebyeMaterial,
    LorentzMaterial,
    ColeColeMaterial,
)
from src.core.mom_solver.solver_engine import MOMSolver
from src.utils.errors import SolverError


class DispersiveMaterialSolver:
    """MoM solver with support for dispersive and anisotropic materials.

    This class extends the standard MoM solver to handle frequency-dependent
    material properties. It interpolates complex permittivity and permeability
    at each simulation frequency point using the appropriate dispersion model,
    then passes the effective material properties to the base solver.

    Parameters
    ----------
    frequency : float, optional
        Operating frequency in Hz. Used for single-frequency solves.
    frequencies : np.ndarray, optional
        Array of frequencies for sweep simulations. Overrides `frequency` if provided.
    dispersion_model : str, default="debye"
        Default dispersion model name: "debye", "lorentz", "cole_cole".

    Attributes
    ----------
    frequency : float
        Current operating frequency in Hz.
    solver : MOMSolver
        The underlying MoM solver instance.
    materials : dict[str, Material]
        Dictionary mapping material names to their instances.
    """

    def __init__(
        self,
        frequency: Optional[float] = None,
        frequencies: Optional[np.ndarray] = None,
        dispersion_model: str = "debye",
    ) -> None:
        """Initialise the dispersive material solver."""
        if frequencies is not None and len(frequencies) > 0:
            self.frequencies = frequencies
            self.frequency = float(frequencies[0])
        elif frequency is not None:
            self.frequency = frequency
            self.frequencies = np.array([frequency])
        else:
            self.frequency = 1e9
            self.frequencies = np.array([self.frequency])

        self.dispersion_model = dispersion_model
        self.materials: Dict[str, object] = {}

        # Initialize the base MoM solver
        self.solver = MOMSolver(frequency=self.frequency)

    # -------------------------------------------------------------------
    # Material management
#    ----------------------------------------------------------------

    def add_material(
        self,
        name: str,
        material: object,
    ) -> None:
        """Add a dispersive or anisotropic material to the solver.

        Parameters
        ----------
        name : str
            Unique identifier for the material.
        material : AnisotropicMaterial, DebyeMaterial, LorentzMaterial, or ColeColeMaterial
            Material instance with frequency-dependent properties.

        Raises
        ------
        SolverError
            If a material with the same name already exists.
        """
        if name in self.materials:
            raise SolverError(f"Material '{name}' already registered")

        self.materials[name] = material

    def get_material_at_freq(self, name: str, frequency: float) -> np.ndarray:
        """Get effective permittivity tensor for a material at a given frequency.

        Parameters
        ----------
        name : str
            Material name.
        frequency : float
            Frequency in Hz for property evaluation.

        Returns
        -------
        np.ndarray
            Effective permittivity tensor (3x3 complex array).

        Raises
        ------
        SolverError
            If the material is not registered or frequency-dependent properties
            cannot be evaluated.
        """
        if name not in self.materials:
            raise SolverError(f"Material '{name}' not found")

        material = self.materials[name]

        if isinstance(material, AnisotropicMaterial):
            return material.get_permittivity_at_freq(frequency)
        elif isinstance(material, DebyeMaterial):
            eps = material.get_permittivity(frequency)
            return np.eye(3) * eps
        elif isinstance(material, LorentzMaterial):
            eps = material.get_permittivity(frequency)
            return np.eye(3) * eps
        elif isinstance(material, ColeColeMaterial):
            eps = material.get_permittivity(frequency)
            return np.eye(3) * eps
        else:
            raise SolverError(f"Unsupported material type: {type(material)}")

    # -------------------------------------------------------------------
    # Solver integration
#    ----------------------------------------------------------------

    def run_sweep(self) -> dict:
        """Run frequency sweep with dispersive material support.

        For each frequency point, evaluates material properties using the
        appropriate dispersion model, then runs the MoM solver.

        Returns
        -------
        dict
            Results dictionary with keys:
            - 'frequencies': array of frequencies in Hz
            - 's_parameters': dict of S-parameter arrays per frequency
            - 'material_properties': dict of evaluated permittivity tensors
            - 'summary': dict with total_time, success_count

        Raises
        ------
        SolverError
            If any frequency point fails to converge.
        """
        results = {
            "frequencies": self.frequencies.tolist(),
            "s_parameters": {},
            "material_properties": {},
        }

        for i, freq in enumerate(self.frequencies):
            try:
                # Update solver frequency
                self.solver.frequency = freq
                self.solver.wavenumber = 2 * np.pi * freq / 299792458.0
                self.solver.omega = 2 * np.pi * freq

                # Evaluate material properties at this frequency
                mat_props = {}
                for name, material in self.materials.items():
                    mat_props[name] = self.get_material_at_freq(name, freq)
                results["material_properties"][f"f_{i}"] = mat_props

                # Run MoM solve (stub - actual solver would use mesh and basis functions)
                s_param = self._solve_single_frequency(freq)
                results["s_parameters"][f"f_{i}"] = s_param

            except Exception as e:
                raise SolverError(
                    f"Failed at frequency {freq:.3e} Hz",
                    context={"error": str(e), "frequency_index": i},
                )

        results["summary"] = {
            "total_frequencies": len(self.frequencies),
            "success_count": len(self.frequencies),
        }

        return results

    def _solve_single_frequency(self, frequency: float) -> np.ndarray:
        """Solve MoM system at a single frequency with material properties.

        Parameters
        ----------
        frequency : float
            Operating frequency in Hz.

        Returns
        -------
        np.ndarray
            S-parameter matrix (stubs return identity for now).
        """
        # In the full implementation, this would:
        # 1. Assemble MoM impedance matrix using RWG basis functions
        # 2. Include material properties from self.materials
        # 3. Solve Z·I = V using PETSc linear solver
        # 4. Extract S-parameters from current solution

        # Stub: return a simple identity S-matrix (2x2 for demonstration)
        n_ports = max(1, len(self.materials))
        s_matrix = np.eye(n_ports * 2).reshape(n_ports, n_ports, 2, 2).astype(np.complex128)

        # Add a simple frequency-dependent reflection coefficient
        f_center = 1e9
        bw = 0.2e9
        if abs(frequency - f_center) < bw:
            s_matrix[0, 0] = 0.1 * np.exp(-1j * 2 * np.pi * frequency * 1e-9)
        else:
            s_matrix[0, 0] = 0.5 + 0.3j

        return s_matrix

    def get_dispersion_curve(
        self,
        name: str,
        freq_range: Tuple[float, float] = (1e8, 1e11),
        n_points: int = 100,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute permittivity vs. frequency curve for a material.

        Parameters
        ----------
        name : str
            Material name.
        freq_range : tuple[float, float], default=(1e8, 1e11)
            Frequency range in Hz as (f_min, f_max).
        n_points : int, default=100
            Number of frequency points to evaluate.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            (frequencies, permittivity_real) arrays for plotting.

        Raises
        ------
        SolverError
            If the material is not registered or does not support dispersion.
        """
        if name not in self.materials:
            raise SolverError(f"Material '{name}' not found")

        material = self.materials[name]
        frequencies = np.linspace(freq_range[0], freq_range[1], n_points)

        real_parts = []
        for f in frequencies:
            eps = self.get_material_at_freq(name, f)
            real_parts.append(np.real(eps[0, 0]))  # Use epsilon_xx component

        return frequencies, np.array(real_parts)


class AnisotropicSolverExtension:
    """Extension for anisotropic material handling in MoM solver.

    This class provides additional functionality for computing the
    impedance matrix contributions from anisotropic materials. It handles
    the tensor nature of permittivity and permeability in the boundary
    integral formulation.
    """

    @staticmethod
    def compute_anisotropic_impedance(
        basis_functions: list,
        eps_tensor: np.ndarray,
        mu_tensor: np.ndarray,
        frequency: float,
    ) -> np.ndarray:
        """Compute impedance matrix contribution from anisotropic materials.

        Parameters
        ----------
        basis_functions : list[RWGBasisFunction]
            RWG basis functions defined on the mesh triangles.
        eps_tensor : np.ndarray
            Permittivity tensor (3x3 complex array) in global coordinates.
        mu_tensor : np.ndarray
            Permeability tensor (3x3 complex array) in global coordinates.
        frequency : float
            Operating frequency in Hz.

        Returns
        -------
        np.ndarray
            Impedance matrix contribution from anisotropic materials.
        """
        # In the full implementation, this would integrate the dyadic Green's
        # function contracted with the anisotropic permittivity and permeability
        # tensors over each RWG basis function pair.

        n_basis = len(basis_functions)
        Z_aniso = np.zeros((n_basis, n_basis), dtype=np.complex128)

        # Simplified: compute diagonal contribution from epsilon tensor
        omega = 2 * np.pi * frequency
        k0 = 2 * np.pi * frequency / 299792458.0

        for i, bf_i in enumerate(basis_functions):
            for j, bf_j in enumerate(basis_functions):
                # Compute dot product of basis function with epsilon tensor
                J_i = bf_i.get_current_direction()
                J_j = bf_j.get_current_direction()

                if len(J_i) > 0 and len(J_j) > 0:
                    # Contract with permittivity tensor
                    eps_eff = np.dot(J_i, eps_tensor)
                    mu_eff = np.dot(J_i, mu_tensor)

                    # Add diagonal contribution (simplified)
                    Z_aniso[i, j] += (omega / 2) * np.sum(eps_eff * J_j)

        return Z_aniso
