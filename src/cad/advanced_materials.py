"""Advanced electromagnetic material models with frequency dispersion.

This module provides classes for dispersive and anisotropic electromagnetic
materials used in computational electromagnetics simulations. It includes:

- AnisotropicMaterial: Materials with direction-dependent permittivity/permeability
  tensors and Drude dispersive behavior.
- DebyeMaterial: Single-relaxation-time dielectric dispersion model.
- LorentzMaterial: Resonant dispersion model for materials with natural frequencies.
- ColeColeMaterial: Generalized Debye model with distributed relaxation times.

All material classes support frequency-dependent complex permittivity evaluation
and optional conductivity contributions.

Example usage::

    from advanced_materials import (
        AnisotropicMaterial,
        DebyeMaterial,
        LorentzMaterial,
        ColeColeMaterial,
    )
    import numpy as np

    # Debye water model at room temperature
    water = DebyeMaterial(
        name="water_25C",
        eps_inf=4.5,
        eps_s=80.0,
        tau=8.1e-12,  # 8.1 ps relaxation time
        sigma=0.0,
    )
    eps_at_1GHz = water.get_permittivity(1e9)

    # Anisotropic uniaxial crystal
    eps_tensor = np.diag([5.0, 5.0, 12.0])
    aniso = AnisotropicMaterial("quartz", eps_tensor=eps_tensor)
"""

from __future__ import annotations

import numpy as np
from typing import Optional


class Material:
    """Base class for electromagnetic material properties."""

    pass


class AnisotropicMaterial(Material):
    """Material with direction-dependent permittivity and permeability tensors.

    Models dispersive anisotropic materials using the Drude model for frequency-
    dependent complex permittivity. Permittivity and permeability are represented
    as 3x3 tensors, allowing full characterization of birefringent and gyrotropic
    media.

    The Drude dispersion model accounts for free-carrier contributions:
        eps(omega) = eps_inf - omega_p^2 / (omega^2 + j*gamma_d*omega)
    where omega_p is the plasma frequency, gamma_d is the damping coefficient,
    and eps_inf represents bound-electron polarization.

    Parameters
    ----------
    name : str
        Descriptive name for the material.
    eps_tensor : np.ndarray
        3x3 complex permittivity tensor at high frequency (relative units).
        Diagonal elements represent principal permittivities; off-diagonal
        elements capture anisotropic coupling.
    mu_tensor : np.ndarray, optional
        3x3 complex permeability tensor (relative units). If None, defaults
        to the identity matrix (mu_r = 1 in all directions).
    sigma : float, default=0.0
        Electrical conductivity in S/m. Adds a loss term j*sigma/(eps_0*omega)
        to the complex permittivity.

    Attributes
    ----------
    name : str
    eps_tensor : np.ndarray (3x3)
    mu_tensor : np.ndarray (3x3)
    sigma : float
    omega_p : np.ndarray (3,) - Plasma frequency vector for each principal axis.
    gamma_d : np.ndarray (3,) - Drude damping coefficients per axis.

    Examples
    --------
    >>> import numpy as np
    >>> eps = np.diag([2.0, 3.0, 4.0])
    >>> mat = AnisotropicMaterial("example", eps_tensor=eps)
    >>> eps_at_10GHz = mat.get_permittivity_at_freq(1e10)
    """

    def __init__(
        self,
        name: str,
        eps_tensor: np.ndarray,
        mu_tensor: Optional[np.ndarray] = None,
        sigma: float = 0.0,
    ) -> None:
        self.name = name
        self.eps_tensor = np.asarray(eps_tensor, dtype=np.complex128)
        if mu_tensor is not None:
            self.mu_tensor = np.asarray(mu_tensor, dtype=np.complex128)
        else:
            self.mu_tensor = np.eye(3, dtype=np.float64)
        self.sigma = sigma

        # Drude model parameters per principal axis (diagonal of eps_tensor)
        self.omega_p = np.zeros(3, dtype=np.float64)  # plasma frequencies
        self.gamma_d = np.zeros(3, dtype=np.float64)  # damping coefficients

    def get_permittivity_at_freq(self, frequency: float) -> np.ndarray:
        """Return the complex permittivity tensor at a given frequency.

        Uses the Drude model to compute frequency-dependent complex permittivity.
        The result combines high-frequency bound-electron contribution (eps_tensor),
        free-carrier Drude dispersion, and conductivity loss.

        Parameters
        ----------
        frequency : float
            Frequency in Hz at which to evaluate the permittivity tensor.

    Returns
    -------
    np.ndarray
        3x3 complex permittivity tensor (relative units). Each element is
        eps_r - j*sigma/(2*pi*f*eps_0), where eps_r comes from Drude model.

    Raises
    ------
    ValueError
        If frequency is negative or the tensor shape is invalid.

    Notes
    -----
    The Drude model expression used:
        eps_drude(omega) = diag(eps_tensor) - omega_p^2 / (omega^2 + j*gamma_d*omega)
    Conductivity contribution:
        eps_loss = sigma / (2*pi*f*eps_0)
    """
        if frequency < 0:
            raise ValueError("Frequency must be non-negative.")

        omega = 2.0 * np.pi * frequency
        eps_0 = 8.854187817e-12  # vacuum permittivity in F/m

        # Drude dispersion for each principal axis (diagonal elements)
        drude_correction = np.zeros_like(self.eps_tensor, dtype=np.complex128)
        if omega > 1e-10:
            for i in range(3):
                denom = omega ** 2 + 1j * self.gamma_d[i] * omega
                if abs(denom) > 1e-30:
                    drude_correction[i, i] -= (self.omega_p[i] ** 2) / denom

        # Conductivity contribution to imaginary part
        conductivity_loss = self.sigma / (max(omega, 1e-10) * eps_0)

        return self.eps_tensor + drude_correction - 1j * conductivity_loss


class DebyeMaterial(Material):
    """Dielectric material modeled with the single-relaxation-time Debye model.

    The Debye model describes frequency-dependent complex permittivity for
    polar dielectrics (e.g., water, polymers). It captures the relaxation of
    dipole orientations in response to an oscillating electric field.

    The complex permittivity is given by:
        eps(f) = eps_inf + (eps_s - eps_inf) / (1 + j*2*pi*f*tau) + j*sigma/(2*pi*f*eps_0)

    where:
        eps_inf  : high-frequency permittivity (electronic polarization only)
        eps_s    : static/low-frequency permittivity (all polarization mechanisms)
        tau      : relaxation time in seconds
        sigma    : DC conductivity in S/m

    Parameters
    ----------
    name : str
        Descriptive name for the material.
    eps_inf : float
        High-frequency relative permittivity (limit as f -> infinity).
    eps_s : float
        Static/low-frequency relative permittivity (limit as f -> 0).
    tau : float
        Relaxation time in seconds. Controls the transition frequency
        f_c = 1/(2*pi*tau) at which dispersion is strongest.
    sigma : float, default=0.0
        Electrical conductivity in S/m.

    Attributes
    ----------
    name : str
    eps_inf : float
    eps_s : float
    tau : float
    sigma : float

    Examples
    --------
    >>> water = DebyeMaterial("water", eps_inf=4.5, eps_s=80.0, tau=8.1e-12)
    >>> eps = water.get_permittivity(1e9)  # ~ 67 - 15j at 1 GHz
    """

    def __init__(
        self,
        name: str,
        eps_inf: float,
        eps_s: float,
        tau: float,
        sigma: float = 0.0,
    ) -> None:
        self.name = name
        self.eps_inf = float(eps_inf)
        self.eps_s = float(eps_s)
        self.tau = float(tau)
        self.sigma = float(sigma)

    def get_permittivity(self, frequency: float) -> np.ndarray:
        """Evaluate the complex relative permittivity at a given frequency.

        Parameters
        ----------
        frequency : float
            Frequency in Hz.

    Returns
    -------
    np.ndarray
        1D array of shape (3, 3) representing isotropic complex permittivity.
        All diagonal elements are equal; off-diagonal elements are zero.

    Notes
    -----
    The Debye formula:
        eps(f) = eps_inf + (eps_s - eps_inf) / (1 + j*2*pi*f*tau)
    """
        omega = 2.0 * np.pi * frequency
        denom = 1.0 + 1j * omega * self.tau
        eps_complex = self.eps_inf + (self.eps_s - self.eps_inf) / denom

        # Add conductivity loss if sigma > 0
        if self.sigma > 0.0 and omega > 1e-10:
            eps_0 = 8.854187817e-12
            eps_complex -= 1j * self.sigma / (omega * eps_0)

        return np.full((3, 3), eps_complex, dtype=np.complex128)


class LorentzMaterial(Material):
    """Dielectric material modeled with the Lorentz oscillator dispersion model.

    The Lorentz model describes resonant polarization in materials with natural
    oscillation frequencies (e.g., infrared-active phonons, electronic transitions).
    It is particularly useful for modeling materials near resonance frequencies.

    The complex permittivity is given by:
        eps(f) = eps_inf + (eps_s - eps_inf) * omega_0^2 /
                 / (omega_0^2 - omega^2 - j*gamma*omega)
                 + j*sigma/(2*pi*f*eps_0)

    where:
        omega_0 : resonant angular frequency (rad/s)
        gamma     : damping (broadening) coefficient (rad/s)
        eps_s     : static permittivity (related to oscillator strength)

    Parameters
    ----------
    name : str
        Descriptive name for the material.
    eps_inf : float
        High-frequency relative permittivity outside the resonance band.
    eps_s : float
        Static/low-frequency relative permittivity. Determines the oscillator
        strength as (eps_s - eps_inf).
    omega_0 : float
        Resonant angular frequency in rad/s. Set omega_0 = 2*pi*f_res where
        f_res is the resonance frequency in Hz.
    gamma : float
        Damping coefficient (broadening) in rad/s. Controls the width of the
        resonance feature. Larger gamma gives broader, more lossy response.
    sigma : float, default=0.0
        Electrical conductivity in S/m.

    Attributes
    ----------
    name : str
    eps_inf : float
    eps_s : float
    omega_0 : float
    gamma : float
    sigma : float

    Examples
    --------
    >>> # Infrared resonance at 10 THz (typical for Si-O stretching)
    >>> si_o2 = LorentzMaterial(
    ...     "SiO2_IR", eps_inf=2.1, eps_s=3.9, omega_0=2*np.pi*10e12, gamma=1e11
    ... )
    >>> eps = si_o2.get_permittivity(5e12)  # below resonance
    """

    def __init__(
        self,
        name: str,
        eps_inf: float,
        eps_s: float,
        omega_0: float,
        gamma: float,
        sigma: float = 0.0,
    ) -> None:
        self.name = name
        self.eps_inf = float(eps_inf)
        self.eps_s = float(eps_s)
        self.omega_0 = float(omega_0)
        self.gamma = float(gamma)
        self.sigma = float(sigma)

    def get_permittivity(self, frequency: float) -> np.ndarray:
        """Evaluate the complex relative permittivity at a given frequency.

        Parameters
        ----------
        frequency : float
            Frequency in Hz.

    Returns
    -------
    np.ndarray
        1D array of shape (3, 3) representing isotropic complex permittivity.

    Notes
    -----
    Lorentz formula:
        eps(omega) = eps_inf + (eps_s - eps_inf)*omega_0^2 /
                     / (omega_0^2 - omega^2 - j*gamma*omega)
    """
        omega = 2.0 * np.pi * frequency

        numerator = (self.eps_s - self.eps_inf) * self.omega_0 ** 2
        denominator = (self.omega_0 ** 2 - omega ** 2) - 1j * self.gamma * omega

        if abs(denominator) > 1e-30:
            eps_complex = self.eps_inf + numerator / denominator
        else:
            # Near resonance singularity: use limiting value
            eps_complex = self.eps_inf

        # Add conductivity loss
        if self.sigma > 0.0 and omega > 1e-10:
            eps_0 = 8.854187817e-12
            eps_complex -= 1j * self.sigma / (omega * eps_0)

        return np.full((3, 3), eps_complex, dtype=np.complex128)


class ColeColeMaterial(Material):
    """Dielectric material modeled with the Cole-Cole distribution model.

    The Cole-Cole model generalizes the Debye model by introducing a distributed
    relaxation time spectrum through the Cole-Cole exponent alpha (0 < alpha <= 1).
    This captures the broadened relaxation behavior observed in many real materials
    (e.g., biological tissues, polymers, porous media) where multiple relaxation
    processes overlap.

    The complex permittivity is given by:
        eps(f) = eps_inf + (eps_s - eps_inf) / (1 + (j*2*pi*f*tau)^(1-alpha))
                 + j*sigma/(2*pi*f*eps_0)

    When alpha = 1, this reduces exactly to the Debye model. As alpha approaches 0,
    the relaxation peak broadens significantly.

    Parameters
    ----------
    name : str
        Descriptive name for the material.
    eps_inf : float
        High-frequency relative permittivity (electronic polarization only).
    eps_s : float
        Static/low-frequency relative permittivity (all polarization mechanisms).
    tau : float
        Characteristic relaxation time in seconds.
    alpha : float
        Cole-Cole exponent, 0 < alpha <= 1. Controls the width of the
        relaxation peak. Smaller values give broader distributions.
        Must satisfy 0 < alpha <= 1.
    sigma : float, default=0.0
        Electrical conductivity in S/m.

    Attributes
    ----------
    name : str
    eps_inf : float
    eps_s : float
    tau : float
    alpha : float
    sigma : float

    Raises
    ------
    ValueError
        If alpha is not in the range (0, 1].

    Examples
    --------
    >>> # Biological tissue at body temperature
    >>> tissue = ColeColeMaterial(
    ...     "brain_tissue", eps_inf=5.0, eps_s=70.0, tau=1e-9, alpha=0.7
    ... )
    >>> eps = tissue.get_permittivity(1e8)  # ~ 60 - 10j at 100 MHz
    """

    def __init__(
        self,
        name: str,
        eps_inf: float,
        eps_s: float,
        tau: float,
        alpha: float,
        sigma: float = 0.0,
    ) -> None:
        if not (0.0 < alpha <= 1.0):
            raise ValueError(
                f"Cole-Cole exponent alpha must satisfy 0 < alpha <= 1, "
                f"got {alpha}"
            )

        self.name = name
        self.eps_inf = float(eps_inf)
        self.eps_s = float(eps_s)
        self.tau = float(tau)
        self.alpha = float(alpha)
        self.sigma = float(sigma)

    def get_permittivity(self, frequency: float) -> np.ndarray:
        """Evaluate the complex relative permittivity at a given frequency.

        Parameters
        ----------
        frequency : float
            Frequency in Hz.

    Returns
    -------
    np.ndarray
        1D array of shape (3, 3) representing isotropic complex permittivity.

    Notes
    -----
    Cole-Cole formula:
        eps(omega) = eps_inf + (eps_s - eps_inf) /
                     / (1 + (j*omega*tau)^(1-alpha))
    """
        omega = 2.0 * np.pi * frequency

        # Cole-Cole denominator: 1 + (j*omega*tau)^(1-alpha)
        power = 1.0 - self.alpha
        cc_term = complex(1.0, 0.0) + complex(omega * self.tau, 0.0) ** power

        eps_complex = self.eps_inf + (self.eps_s - self.eps_inf) / cc_term

        # Add conductivity loss
        if self.sigma > 0.0 and omega > 1e-10:
            eps_0 = 8.854187817e-12
            eps_complex -= 1j * self.sigma / (omega * eps_0)

        return np.full((3, 3), eps_complex, dtype=np.complex128)


# ---------------------------------------------------------------------------
# Module-level example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import numpy as np

    print("=" * 60)
    print("Advanced Materials Module - Example Usage")
    print("=" * 60)

    # --- Debye Material ---
    water = DebyeMaterial(
        name="water_25C",
        eps_inf=4.5,
        eps_s=80.0,
        tau=8.1e-12,
        sigma=0.0,
    )
    freqs = np.logspace(6, 12, 7)  # 1 MHz to 1 THz
    print("\n[DebyeMaterial] Water permittivity vs frequency:")
    for f in freqs:
        eps = water.get_permittivity(f)[0, 0]
        print(f"  f={f/1e9:.2f} GHz  |eps|={abs(eps):.2f}  "
              f"Re={np.real(eps):.3f}  Im={np.imag(eps):.3f}")

    # --- Lorentz Material ---
    si_o2 = LorentzMaterial(
        name="SiO2_IR",
        eps_inf=2.1,
        eps_s=3.9,
        omega_0=2 * np.pi * 10e12,
        gamma=1e11,
        sigma=0.0,
    )
    print("\n[LorentzMaterial] SiO2 permittivity at IR resonance:")
    for f in [5e12, 8e12, 10e12, 12e12]:
        eps = si_o2.get_permittivity(f)[0, 0]
        print(f"  f={f/1e12:.2f} THz  |eps|={abs(eps):.3f}")

    # --- Cole-Cole Material ---
    tissue = ColeColeMaterial(
        name="brain_tissue",
        eps_inf=5.0,
        eps_s=70.0,
        tau=1e-9,
        alpha=0.7,
        sigma=0.01,  # 10 mS/m conductivity
    )
    print("\n[ColeColeMaterial] Brain tissue permittivity:")
    for f in [1e6, 1e7, 1e8, 1e9]:
        eps = tissue.get_permittivity(f)[0, 0]
        print(f"  f={f/1e6:.2f} MHz  |eps|={abs(eps):.2f}")

    # --- Anisotropic Material ---
    eps_tensor = np.diag([5.0, 5.0, 12.0])
    aniso = AnisotropicMaterial("quartz", eps_tensor=eps_tensor)
    print("\n[AnisotropicMaterial] Quartz permittivity at 1 GHz:")
    eps_at_1ghz = aniso.get_permittivity_at_freq(1e9)
    print(f"  eps_r =\n{np.round(eps_at_1ghz, 4)}")
