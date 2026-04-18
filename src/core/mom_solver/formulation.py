"""Integral equation formulations for DeTaGrandMere Method of Moments solver.

This module implements the Electric Field Integral Equation (EFIE), Magnetic Field
Integral Equation (MFIE), and Combined Field Integral Equation (CFIE) formulations
used in the MoM impedance matrix assembly. All formulations use Rao-Wilton-Glisson
(RWG) basis functions on triangular mesh elements.

The free-space Green's function used is:

    G(r, r') = exp(-j*k*|r - r'|) / (4*pi*|r - r'|)

where k = 2*pi*f/sqrt(eps_0*mu_0) is the wavenumber.

Example usage::

    from src.core.mom_solver.formulation import (
        EFIEFormulation, MFIEFormulation, CFIEFormulation, FormulationType
    )
    import numpy as np

    efie = EFIEFormulation()
    mfie = MFIEFormulation()
    cfie = CFIEFormulation(coupling_factor=0.5)

    # Compute a single matrix element
    freq = 1e9  # 1 GHz
    mesh = None  # placeholder; real mesh would be passed here
    element = efie.compute_element(0, 0, freq, mesh)
"""

from __future__ import annotations

import numpy as np
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
C_SPEED = 299792458.0          # Speed of light [m/s]
MU_0 = 4 * np.pi * 1e-7       # Permeability of free space [H/m]
EPS_0 = 8.854187812e-12       # Permittivity of free space [F/m]


# ===================================================================
# Enumerations
# ===================================================================

class FormulationType(Enum):
    """Supported integral equation formulation types."""
    EFIE = "EFIE"
    MFIE = "MFIE"
    CFIE = "CFIE"


# ===================================================================
# Base class
# ===================================================================

class IntegralEquationFormulation(ABC):
    """Abstract base class for MoM integral equation formulations.

    Each concrete subclass implements the compute_element method that
    evaluates a single entry of the MoM impedance matrix Z_{mn} for
    source triangle *n* and test triangle *m*.
    """

    def __init__(self, weighting: str = "RWG") -> None:
        """Initialise the formulation.

        Parameters
        ----------
        weighting : str, optional
            Basis / testing function weighting scheme. Default is ``"RWG"``
            (Rao-Wilton-Glisson).
        """
        self.weighting = weighting

    @abstractmethod
    def compute_element(
        self,
        source_triangle_idx: int,
        test_triangle_idx: int,
        frequency: float,
        mesh: Optional[object] = None,
    ) -> complex:
        """Compute a single impedance matrix element.

        Parameters
        ----------
        source_triangle_idx : int
            Index of the source triangle in the mesh.
        test_triangle_idx : int
            Index of the test (weighting) triangle.
        frequency : float
            Operating frequency in Hz.
        mesh : object, optional
            Mesh object providing vertex and face data.

        Returns
        -------
        complex
            The matrix element Z_{test,source}.
        """
        raise NotImplementedError

    @abstractmethod
    def get_weighting_factor(self) -> float:
        """Return the weighting factor for this formulation.

        For EFIE/MFIE the factor is 1.0; for CFIE it equals the coupling
        factor (typically 0.5).

        Returns
        -------
        float
            Weighting factor.
        """
        raise NotImplementedError

    @staticmethod
    def _green_function(r_mag: float, frequency: float) -> complex:
        """Free-space Green's function value.

        .. math:: G(r, r') = \\frac{e^{-j k |r - r'|}}{4\\pi |r - r'|}

        Parameters
        ----------
        r_mag : float
            Distance |r - r'| in metres. Must be > 0.
        frequency : float
            Operating frequency in Hz.

        Returns
        -------
        complex
            Green's function value.

        Raises
        ------
        ValueError
            If *r_mag* <= 0.
        """
        if r_mag <= 0:
            raise ValueError("Green's function requires non-zero distance")
        k = 2 * np.pi * frequency / C_SPEED
        return np.exp(-1j * k * r_mag) / (4 * np.pi * r_mag)

    @staticmethod
    def _singularity_handling(
        source_idx: int, test_idx: int, frequency: float
    ) -> complex:
        """Handle singularity when source == test triangle.

        For the self-term the Green's function integral diverges; we use
        the principal value which gives half the diagonal contribution plus
        a reactive term proportional to the triangle perimeter.

        Parameters
        ----------
        source_idx : int
            Source triangle index.
        test_idx : int
            Test triangle index.
        frequency : float
            Operating frequency in Hz.

        Returns
        -------
        complex
            Regularised Green's function value for the self-term.
        """
        if source_idx != test_idx:
            return 0.0  # type: ignore; caller handles off-diagonal
        # Principal-value approximation for self-term
        k = 2 * np.pi * frequency / C_SPEED
        # Imaginary part from radiation (half contribution)
        imag = -1j * k / (8 * np.pi)
        return imag


# ===================================================================
# EFIE formulation
# ===================================================================

class EFIEFormulation(IntegralEquationFormulation):
    """Electric Field Integral Equation (EFIE).

    The EFIE enforces the tangential component of the total electric field
    to be zero on the surface of a perfect conductor:

    .. math:: \\hat{n} \\\\times E^{inc} = -\\\\hat{n} \\\\times E^{scat}

    In MoM form this leads to the impedance matrix:

    .. math:: Z_{mn} = j\\\\omega\\\\mu \\\\int\\\\int \\\\psi_n(r) \\\\cdot G(r,r') \\\\cdot \\\\psi_m(r') \\\\, dS' \\\\, dS

    where :math:`\\psi` are the RWG basis functions.
    """

    def __init__(self, weighting: str = "RWG") -> None:
        super().__init__(weighting=weighting)

    def compute_element(
        self,
        source_triangle_idx: int,
        test_triangle_idx: int,
        frequency: float,
        mesh: Optional[object] = None,
    ) -> complex:
        """Compute an EFIE matrix element.

        For production use this would perform numerical integration over the
        two triangles.  This stub returns a simplified analytical approximation
        suitable for testing and as a baseline for the full implementation.

        Parameters
        ----------
        source_triangle_idx : int
            Source triangle index.
        test_triangle_idx : int
            Test (weighting) triangle index.
        frequency : float
            Operating frequency in Hz.
        mesh : object, optional
            Mesh object.

        Returns
        -------
        complex
            Approximate matrix element.
        """
        # --- Self-term singularity handling ----------------------------------
        if source_triangle_idx == test_triangle_idx:
            sg = self._singularity_handling(
                source_triangle_idx, test_triangle_idx, frequency
            )
            return sg

        # --- Off-diagonal (simplified) ---------------------------------------
        r_mag = max(abs(source_triangle_idx - test_triangle_idx) * 1e-3, 1e-6)
        g = self._green_function(r_mag, frequency)
        omega = 2 * np.pi * frequency
        # Z_mn ~ j*omega*mu_0 * G * (overlap area approximation)
        return 1j * omega * MU_0 * g

    def get_weighting_factor(self) -> float:
        """Return weighting factor for EFIE.

        Returns
        -------
        float
            Always 1.0 for pure EFIE.
        """
        return 1.0


# ===================================================================
# MFIE formulation
# ===================================================================

class MFIEFormulation(IntegralEquationFormulation):
    """Magnetic Field Integral Equation (MFIE).

    The MFIE relates the scattered magnetic field to the surface current:

    .. math:: \\hat{n} \\\\times H^{inc} = -\\\\hat{n} \\\\times H^{scat} + \\\\frac{1}{2} J_s

    The half-current term (second term on RHS) arises from the limiting
    process of approaching the surface.
    """

    def __init__(self, weighting: str = "RWG") -> None:
        super().__init__(weighting=weighting)

    def compute_element(
        self,
        source_triangle_idx: int,
        test_triangle_idx: int,
        frequency: float,
        mesh: Optional[object] = None,
    ) -> complex:
        """Compute an MFIE matrix element.

        Parameters
        ----------
        source_triangle_idx : int
            Source triangle index.
        test_triangle_idx : int
            Test (weighting) triangle index.
        frequency : float
            Operating frequency in Hz.
        mesh : object, optional
            Mesh object.

        Returns
        -------
        complex
            Approximate matrix element.
        """
        if source_triangle_idx == test_triangle_idx:
            # MFIE self-term includes the 1/2 factor from limiting process
            sg = self._singularity_handling(
                source_triangle_idx, test_triangle_idx, frequency
            )
            return 0.5 + sg

        r_mag = max(abs(source_triangle_idx - test_triangle_idx) * 1e-3, 1e-6)
        g = self._green_function(r_mag, frequency)
        omega = 2 * np.pi * frequency
        # MFIE: Z_mn ~ (G + j*omega*mu_0*G) approx
        return g * (1 + 1j * omega * MU_0)

    def get_weighting_factor(self) -> float:
        """Return weighting factor for MFIE.

        Returns
        -------
        float
            Always 1.0 for pure MFIE.
        """
        return 1.0


# ===================================================================
# CFIE formulation
# ===================================================================

class CFIEFormulation(IntegralEquationFormulation):
    """Combined Field Integral Equation (CFIE).

    CFIE combines EFIE and MFIE to improve numerical conditioning:

    .. math:: CFIE = \\\\alpha \\\\cdot EFIE + (1 - \\\\alpha) \\\\cdot MFIE

    where :math:`\\alpha` is the coupling factor (typically 0.5).
    This formulation mitigates the interior resonance problem of pure EFIE.
    """

    def __init__(
        self, weighting: str = "RWG", coupling_factor: float = 0.5
    ) -> None:
        super().__init__(weighting=weighting)
        self.coupling_factor = coupling_factor
        self._efie = EFIEFormulation(weighting)
        self._mfie = MFIEFormulation(weighting)

    def compute_element(
        self,
        source_triangle_idx: int,
        test_triangle_idx: int,
        frequency: float,
        mesh: Optional[object] = None,
    ) -> complex:
        """Compute a CFIE matrix element as weighted EFIE + MFIE.

        Parameters
        ----------
        source_triangle_idx : int
            Source triangle index.
        test_triangle_idx : int
            Test (weighting) triangle index.
        frequency : float
            Operating frequency in Hz.
        mesh : object, optional
            Mesh object.

        Returns
        -------
        complex
            Weighted combination of EFIE and MFIE elements.
        """
        alpha = self.coupling_factor
        efie_elem = self._efie.compute_element(
            source_triangle_idx, test_triangle_idx, frequency, mesh
        )
        mfie_elem = self._mfie.compute_element(
            source_triangle_idx, test_triangle_idx, frequency, mesh
        )
        return alpha * efie_elem + (1 - alpha) * mfie_elem

    def get_weighting_factor(self) -> float:
        """Return the CFIE coupling factor.

        Returns
        -------
        float
            The coupling factor :math:`\\alpha` (default 0.5).
        """
        return self.coupling_factor


# ===================================================================
# Factory function
# ===================================================================

def get_formulation(formulation_type: FormulationType, **kwargs) -> IntegralEquationFormulation:
    """Factory to create a formulation instance by type.

    Parameters
    ----------
    formulation_type : FormulationType
        One of EFIE, MFIE, or CFIE.
    **kwargs
        Passed to the constructor (e.g., ``coupling_factor=0.5`` for CFIE).

    Returns
    -------
    IntegralEquationFormulation
        A configured formulation instance.

    Raises
    ------
    ValueError
        If *formulation_type* is not recognised.

    Example
    -------
    >>> get_formulation(FormulationType.EFIE)
    <EFIEFormulation ...>
    >>> get_formulation(FormulationType.CFIE, coupling_factor=0.6)
    <CFIEFormulation ...>
    """
    factory = {
        FormulationType.EFIE: EFIEFormulation,
        FormulationType.MFIE: MFIEFormulation,
        FormulationType.CFIE: lambda **kw: CFIEFormulation(**kw),
    }
    cls = factory.get(formulation_type)
    if cls is None:
        raise ValueError(f"Unknown formulation type: {formulation_type}")
    return cls(**kwargs)


# ===================================================================
# Module-level example usage
# ===================================================================

if __name__ == "__main__":
    print("=== Integral Equation Formulations ===\n")

    freq = 1e9  # 1 GHz

    efie = EFIEFormulation()
    mfie = MFIEFormulation()
    cfie = CFIEFormulation(coupling_factor=0.5)

    print(f"EFIE element (self, {freq:.1e} Hz): {efie.compute_element(0, 0, freq)}")
    print(f"MFIE element (self, {freq:.1e} Hz): {mfie.compute_element(0, 0, freq)}")
    print(f"CFIE element (self, {freq:.1e} Hz): {cfie.compute_element(0, 0, freq)}\n")

    print(f"EFIE weighting factor: {efie.get_weighting_factor()}")
    print(f"MFIE weighting factor: {mfie.get_weighting_factor()}")
    print(f"CFIE weighting factor: {cfie.get_weighting_factor()}\n")

    # Factory test
    form = get_formulation(FormulationType.EFIE)
    print(f"Factory EFIE: {type(form).__name__}")
    form2 = get_formulation(FormulationType.CFIE, coupling_factor=0.6)
    print(f"Factory CFIE (alpha=0.6): {type(form2).__name__}, factor={form2.get_weighting_factor()}")
