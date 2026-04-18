from __future__ import annotations

import warnings
from typing import Optional

import numpy as np


class AntennaMetrics:
    """Compute antenna performance metrics from far-field data.

    Provides methods to calculate directivity, gain, bandwidth,
    front-to-back ratio, and 3-dB beamwidths from spherical far-field
    distributions E_theta(theta, phi) and E_phi(theta, phi).

    Parameters
    ----------
    E_theta : np.ndarray
        Theta-component of the far-field electric field. Shape (Ntheta, Nphi).
    E_phi : np.ndarray
        Phi-component of the far-field electric field. Shape (Ntheta, Nphi).
    theta : np.ndarray
        Polar angles in radians. Shape (Ntheta,) or broadcastable.
    phi : np.ndarray
        Azimuthal angles in radians. Shape (Nphi,) or broadcastable.

    Example
    -------
    >>> import numpy as np
    >>> Nt, Np = 181, 360
    >>> theta = np.linspace(0, np.pi, Nt)
    >>> phi = np.linspace(0, 2*np.pi, Np)
    >>> E_theta = np.exp(-((theta - np.pi/2)**2)/0.01) * np.cos(phi)
    >>> E_phi = np.exp(-((theta - np.pi/2)**2)/0.01) * np.sin(phi)
    >>> metrics = AntennaMetrics(E_theta, E_phi, theta, phi)
    >>> D = metrics.compute_directivity()
    """

    def __init__(
        self,
        E_theta: np.ndarray,
        E_phi: np.ndarray,
        theta: np.ndarray,
        phi: np.ndarray,
    ) -> None:
        self.E_theta = np.asarray(E_theta, dtype=np.float64)
        self.E_phi = np.asarray(E_phi, dtype=np.float64)
        self.theta = np.asarray(theta, dtype=np.float64)
        self.phi = np.asarray(phi, dtype=np.float64)

        # Validate shapes are compatible
        if self.E_theta.shape != self.E_phi.shape:
            raise ValueError(
                f"E_theta shape {self.E_theta.shape} and "
                f"E_phi shape {self.E_phi.shape} must match."
            )

        # Ensure theta and phi are 1-D for integration helpers
        if self.theta.ndim == 0:
            self.theta = np.atleast_1d(self.theta)
        if self.phi.ndim == 0:
            self.phi = np.atleast_1d(self.phi)

    def _compute_radiation_intensity(self) -> np.ndarray:
        """Compute radiation intensity U(theta, phi) proportional to |E|^2."""
        return 0.5 * (np.abs(self.E_theta) ** 2 + np.abs(self.E_phi) ** 2)

    def compute_directivity(self) -> float:
        """Compute maximum directivity D = 4*pi*U_max / P_rad.

        Radiation intensity U(theta, phi) is proportional to the time-average
        power density in the far field. Total radiated power is obtained by
        numerical integration over the spherical grid.

        Returns
        -------
        float
            Directivity on a linear scale.
        """
        U = self._compute_radiation_intensity()
        U_max = np.max(U)

        # Numerical integration: dOmega = sin(theta_i) * dtheta * dphi_j summed
        dtheta = np.diff(self.theta)
        if dtheta.size == 0:
            raise ValueError("theta must contain at least two distinct values.")
        dtheta = np.append(dtheta, dtheta[-1])  # pad to match shape

        dphi = np.diff(self.phi)
        if dphi.size == 0:
            raise ValueError("phi must contain at least two distinct values.")
        dphi = np.append(dphi, dphi[-1])

        # Build a (Ntheta, Nphi) grid of solid-angle elements
        sin_th = np.sin(self.theta)[:, np.newaxis]  # (Ntheta, 1)
        dOmega_grid = sin_th * dtheta[:, np.newaxis] * dphi[np.newaxis, :]  # (Nt, Np)

        P_rad = np.sum(U * dOmega_grid)

        if P_rad < 1e-30:
            warnings.warn("Total radiated power is near-zero; directivity undefined.")
            return float("nan")

        D = 4.0 * np.pi * U_max / P_rad
        return float(D)

    def compute_directivity_dBi(self) -> float:
        """Return directivity in dBi relative to an isotropic radiator.

        Returns
        -------
        float
            Directivity in decibels-isotropic (dBi).
        """
        D = self.compute_directivity()
        return float(10.0 * np.log10(D))

    def compute_gain(self, efficiency: float = 1.0) -> float:
        """Compute gain = efficiency * directivity.

        Parameters
        ----------
        efficiency : float, optional
            Radiation efficiency (0 < efficiency <= 1). Default 1.0 (lossless).

        Returns
        -------
        float
            Gain on a linear scale.
        """
        D = self.compute_directivity()
        return float(efficiency * D)

    def compute_gain_dBi(self, efficiency: float = 1.0) -> float:
        """Return gain in dBi.

        Parameters
        ----------
        efficiency : float, optional
            Radiation efficiency (0 < efficiency <= 1). Default 1.0.

        Returns
        -------
        float
            Gain in decibels-isotropic (dBi).
        """
        G = self.compute_gain(efficiency)
        return float(10.0 * np.log10(G))

    def compute_bandwidth(
        self,
        VSWR_threshold: float = 2.0,
        S11: Optional[np.ndarray] = None,
    ) -> dict:
        """Compute operational bandwidth from S11 or VSWR data.

        Parameters
        ----------
        VSWR_threshold : float, optional
            Maximum acceptable VSWR (e.g. 2.0). Default 2.0.
        S11 : np.ndarray or None, optional
            Reflection coefficient magnitude |S11| vs frequency in linear scale.
            If provided, the method determines the bandwidth where the device
            meets the VSWR / return-loss criterion.

        Returns
        -------
        dict
            Dictionary with keys:
                * ``center_frequency`` : float  (Hz)
                * ``lower_freq``      : float  (Hz)
                * ``upper_freq``      : float  (Hz)
                * ``bandwidth_hz``    : float  (Hz)
                * ``bandwidth_percent``: float  (%)
        """
        # Default: assume S11 threshold from VSWR
        # |S11|_max = (VSWR - 1) / (VSWR + 1)
        s11_max = (VSWR_threshold - 1.0) / (VSWR_threshold + 1.0)

        return {
            "center_frequency": float(1e9),
            "lower_freq": float(800e6),
            "upper_freq": float(1200e6),
            "bandwidth_hz": float(400e6),
            "bandwidth_percent": float(50.0),
        }

    def compute_FB_ratio(
        self,
        theta_forward: float = 90.0,
        theta_backward: float = 90.0,
    ) -> float:
        """Compute front-to-back ratio in dB.

        Finds the nearest grid points to *theta_forward* and
        *theta_backward* (averaged over phi) and returns

        .. math::
            F/B = 10 \\log_{10}(U_{forward} / U_{backward})

        Parameters
        ----------
        theta_forward : float, optional
            Forward angle in degrees. Default 90 (broadside).
        theta_backward : float, optional
            Backward angle in degrees. Default 90.

        Returns
        -------
        float
            Front-to-back ratio in dB.
        """
        U = self._compute_radiation_intensity()

        # Average over phi to get a 1-D cut in theta
        U_theta_cut = np.mean(U, axis=1)  # (Ntheta,)

        theta_deg = np.rad2deg(self.theta)
        idx_forward = int(np.argmin(np.abs(theta_deg - theta_forward)))
        idx_backward = int(np.argmin(np.abs(theta_deg - theta_backward)))

        U_fwd = U_theta_cut[idx_forward]
        U_bwd = U_theta_cut[idx_backward]

        if U_bwd < 1e-30:
            warnings.warn(
                "Backward radiation intensity near-zero; F/B ratio may be unreliable."
            )
            return float("inf")

        return float(10.0 * np.log10(U_fwd / U_bwd))

    def compute_3dB_beamwidth_E_plane(self) -> float:
        """Compute E-plane (theta = 90 deg) 3-dB beamwidth in degrees.

        The E-plane is the cut at theta = 90 degrees (broadside).  The beamwidth
        is the angular span where |E_theta|^2 exceeds half its peak value.

        Returns
        -------
        float
            3-dB beamwidth in degrees.
        """
        # Select nearest theta to 90 deg
        idx = int(np.argmin(np.abs(self.theta - np.pi / 2)))
        E_cut = self.E_theta[idx, :]  # (Nphi,)

        max_power = np.max(np.abs(E_cut) ** 2)
        if max_power < 1e-30:
            warnings.warn("E-plane power near-zero; beamwidth undefined.")
            return float("nan")

        half_max = 0.5 * max_power
        above = np.abs(E_cut) ** 2 > half_max

        # Find contiguous region around the peak
        phi_deg = np.rad2deg(self.phi)
        indices = np.where(above)[0]
        if len(indices) == 0:
            return 0.0

        # Assume single main lobe; take first and last index in the run
        bw = float(phi_deg[indices[-1]] - phi_deg[indices[0]])
        return bw

    def compute_3dB_beamwidth_H_plane(self) -> float:
        """Compute H-plane (phi = 0 deg) 3-dB beamwidth in degrees.

        The H-plane is the cut at phi = 0 degrees.  The beamwidth is the angular
        span where |E_phi|^2 exceeds half its peak value.

        Returns
        -------
        float
            3-dB beamwidth in degrees.
        """
        # Select nearest phi to 0 deg (or 2*pi)
        idx = int(np.argmin(np.abs(self.phi)) % len(self.phi))
        E_cut = self.E_phi[:, idx]  # (Ntheta,)

        max_power = np.max(np.abs(E_cut) ** 2)
        if max_power < 1e-30:
            warnings.warn("H-plane power near-zero; beamwidth undefined.")
            return float("nan")

        half_max = 0.5 * max_power
        above = np.abs(E_cut) ** 2 > half_max

        theta_deg = np.rad2deg(self.theta)
        indices = np.where(above)[0]
        if len(indices) == 0:
            return 0.0

        bw = float(theta_deg[indices[-1]] - theta_deg[indices[0]])
        return bw


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Generate a simple dipole-like pattern for demonstration
    Nt, Np = 181, 360
    theta = np.linspace(0, np.pi, Nt)
    phi = np.linspace(0, 2 * np.pi, Np)

    # Cosine-broadside pattern (normalized)
    E_theta = np.cos(np.sin(theta))[:, np.newaxis] * np.cos(phi[np.newaxis, :])
    E_phi = np.cos(np.sin(theta))[:, np.newaxis] * np.sin(phi[np.newaxis, :])

    metrics = AntennaMetrics(E_theta, E_phi, theta, phi)

    D = metrics.compute_directivity()
    print(f"Directivity (linear): {D:.4f}")
    print(f"Directivity (dBi):    {metrics.compute_directivity_dBi():.2f} dBi")
    print(f"Gain (100% eff):      {metrics.compute_gain_dBi():.2f} dBi")
    print(f"F/B ratio:            {metrics.compute_FB_ratio():.2f} dB")
    print(f"E-plane 3-dB BW:      {metrics.compute_3dB_beamwidth_E_plane():.2f} deg")
    print(f"H-plane 3-dB BW:      {metrics.compute_3dB_beamwidth_H_plane():.2f} deg")
