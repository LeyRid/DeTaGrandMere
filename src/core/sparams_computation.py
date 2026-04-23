"""Multi-port excitation and mutual coupling analysis for antenna arrays.

This module provides the :class:`MultiPortExcitation` class for managing
multiple port excitations with independent power distribution, along with
the :class:`SParameterCalculator` class for computing full N-port S-parameter
matrices and mutual coupling coefficients.

Key features:
- Multi-port excitation with independent amplitude/phase control
- Full N×N S-parameter matrix computation across frequency sweeps
- Mutual coupling coefficient calculation between all port pairs
- Array factor analysis for antenna array performance
"""

from __future__ import annotations

import numpy as np
from typing import Optional, List, Tuple, Dict

from src.utils.errors import SolverError


class MultiPortExcitation:
    """Manage multi-port excitation with independent power distribution.

    This class provides methods for setting up and controlling multiple
    port excitations in a simulation. Each port can have independent
    amplitude and phase settings.

    Parameters
    ----------
    n_ports : int, default=1
        Number of ports in the system.
    reference_impedance : float, default=50.0
        Reference impedance in ohms for all ports.
    """

    def __init__(
        self,
        n_ports: int = 1,
        reference_impedance: float = 50.0,
    ) -> None:
        """Initialise the multi-port excitation manager."""
        self.n_ports = n_ports
        self.reference_impedance = reference_impedance

        # Port excitation settings
        self.port_amplitudes = np.ones(n_ports)
        self.port_phases = np.zeros(n_ports)  # in radians

        # Excitation state (active/inactive)
        self.active_ports = [True] * n_ports

    def set_excitation(
        self,
        port_index: int,
        amplitude: Optional[float] = None,
        phase: Optional[float] = None,
    ) -> None:
        """Set excitation parameters for a specific port.

        Parameters
        ----------
        port_index : int
            Port index (0-based).
        amplitude : float, optional
            Excitation amplitude. If None, keeps current value.
        phase : float, optional
            Excitation phase in radians. If None, keeps current value.

        Raises
        ------
        SolverError
            If the port index is out of range.
        """
        if not 0 <= port_index < self.n_ports:
            raise SolverError(
                f"Port index {port_index} out of range (0-{self.n_ports - 1})"
            )

        if amplitude is not None:
            self.port_amplitudes[port_index] = amplitude
        if phase is not None:
            self.port_phases[port_index] = phase

    def set_all_excitations(
        self,
        amplitudes: np.ndarray,
        phases: Optional[np.ndarray] = None,
    ) -> None:
        """Set excitation parameters for all ports.

        Parameters
        ----------
        amplitudes : np.ndarray
            Array of amplitudes with shape (n_ports,).
        phases : np.ndarray, optional
            Array of phases in radians with shape (n_ports,). Defaults to zero.

        Raises
        ------
        SolverError
            If arrays have incorrect length.
        """
        if len(amplitudes) != self.n_ports:
            raise SolverError(
                f"Amplitude array length {len(amplitudes)} doesn't match "
                f"port count {self.n_ports}"
            )

        self.port_amplitudes = np.array(amplitudes)

        if phases is not None:
            if len(phases) != self.n_ports:
                raise SolverError(
                    f"Phase array length {len(phases)} doesn't match "
                    f"port count {self.n_ports}"
                )
            self.port_phases = np.array(phases)

    def get_excitation_vector(self, frequency: float) -> np.ndarray:
        """Get the complex excitation vector for all ports.

        Parameters
        ----------
        frequency : float
            Operating frequency in Hz (used for phase calculations).

        Returns
        -------
        np.ndarray
            Complex excitation vector with shape (n_ports,) and dtype
            complex128. Each element is amplitude * exp(j*phase).
        """
        return self.port_amplitudes * np.exp(1j * self.port_phases)

    def activate_port(self, port_index: int) -> None:
        """Activate a specific port for excitation.

        Parameters
        ----------
        port_index : int
            Port index (0-based).

        Raises
        ------
        SolverError
            If the port index is out of range.
        """
        if not 0 <= port_index < self.n_ports:
            raise SolverError(f"Port index {port_index} out of range")

        self.active_ports[port_index] = True

    def deactivate_port(self, port_index: int) -> None:
        """Deactivate a specific port (no excitation).

        Parameters
        ----------
        port_index : int
            Port index (0-based).

        Raises
        ------
        SolverError
            If the port index is out of range.
        """
        if not 0 <= port_index < self.n_ports:
            raise SolverError(f"Port index {port_index} out of range")

        self.active_ports[port_index] = False


class SParameterCalculator:
    """Compute N-port S-parameters and mutual coupling coefficients.

    This class provides methods for computing full S-parameter matrices
    for multi-port systems, including frequency sweep support and mutual
    coupling analysis between all port pairs.

    Parameters
    ----------
    n_ports : int, default=2
        Number of ports in the system.
    reference_impedance : float, default=50.0
        Reference impedance in ohms for all ports.
    """

    def __init__(
        self,
        n_ports: int = 2,
        reference_impedance: float = 50.0,
    ) -> None:
        """Initialise the S-parameter calculator."""
        self.n_ports = n_ports
        self.reference_impedance = reference_impedance

    def compute_s_parameters_from_Z(
        self,
        Z_matrix: np.ndarray,
        Z0: Optional[float] = None,
    ) -> np.ndarray:
        """Compute S-parameter matrix from impedance matrix.

        Parameters
        ----------
        Z_matrix : np.ndarray
            Impedance matrix with shape (N, N).
        Z0 : float, optional
            Reference impedance. Uses self.reference_impedance if None.

        Returns
        -------
        np.ndarray
            S-parameter matrix with shape (N, N) and dtype complex128.

        Raises
        ------
        SolverError
            If the Z-matrix is not square or dimensions don't match ports.
        """
        z0 = Z0 or self.reference_impedance

        if Z_matrix.shape[0] != Z_matrix.shape[1]:
            raise SolverError("Z-matrix must be square")

        n = Z_matrix.shape[0]
        if n != self.n_ports:
            # For multi-port systems, pad or truncate as needed
            pass

        # Convert Z to S using: S = (Z - Z0*I) * (Z + Z0*I)^-1
        I = np.eye(n)
        Z0_matrix = z0 * I

        try:
            A = Z_matrix - Z0_matrix
            B = np.linalg.inv(Z_matrix + Z0_matrix)
            S = np.dot(A, B)
        except np.linalg.LinAlgError:
            raise SolverError("Z-matrix is not invertible; cannot compute S-parameters")

        return S.astype(np.complex128)

    def compute_S_parameters(
        self,
        Z_matrix: np.ndarray,
        port_impedances: Optional[list[float]] = None,
        frequency_Hz: Optional[float] = None,
    ) -> np.ndarray:
        """Compute S-parameter matrix from impedance matrix (convenience method).

        This is a convenience wrapper around :meth:`compute_s_parameters_from_Z`
        that accepts per-port reference impedances.

        Parameters
        ----------
        Z_matrix : np.ndarray
            Impedance matrix with shape (N, N).
        port_impedances : list[float], optional
            List of reference impedances for each port. Uses
            ``self.reference_impedance`` for all ports if None.
        frequency_Hz : float, optional
            Frequency in Hz (for logging / future use).

        Returns
        -------
        np.ndarray
            S-parameter matrix with shape (N, N) and dtype complex128.
        """
        n = Z_matrix.shape[0]
        if port_impedances is None:
            z0 = self.reference_impedance
        else:
            # Use first port impedance as reference for simplicity
            z0 = float(port_impedances[0]) if port_impedances else self.reference_impedance
        return self.compute_s_parameters_from_Z(Z_matrix, Z0=z0)

    def validate_reciprocity(self, S_matrix: np.ndarray, tolerance: float = 1e-6) -> bool:
        """Check if an S-matrix is reciprocal (symmetric).

        A reciprocal network has S_ij = S_ji for all i, j.

        Parameters
        ----------
        S_matrix : np.ndarray
            S-parameter matrix with shape (N, N).
        tolerance : float, default=1e-6
            Maximum allowed deviation from symmetry.

        Returns
        -------
        bool
            True if the matrix is reciprocal, False otherwise.
        """
        S = np.asarray(S_matrix)
        return bool(np.allclose(S, S.T, atol=tolerance))

    def validate_passivity(self, S_matrix: np.ndarray, tolerance: float = 1e-10) -> bool:
        """Check if an S-matrix is passive (all singular values <= 1).

        A passive network has all singular values of its S-matrix less than
        or equal to 1. Active (gain) networks have at least one singular
        value greater than 1.

        Parameters
        ----------
        S_matrix : np.ndarray
            S-parameter matrix with shape (N, N).
        tolerance : float, default=1e-10
            Tolerance for the passivity check.

        Returns
        -------
        bool
            True if the matrix is passive, False otherwise.
        """
        S = np.asarray(S_matrix)
        sv = np.linalg.svd(S, compute_uv=False)
        return bool(np.all(sv <= 1.0 + tolerance))

    def compute_S_sweep(
        self,
        Z_matrices: Dict[float, np.ndarray],
        port_impedances: Optional[list[float]] = None,
    ) -> dict:
        """Compute S-parameters across a frequency sweep.

        Parameters
        ----------
        Z_matrices : dict[float, np.ndarray]
            Dictionary mapping frequency (Hz) to Z-matrices.
        port_impedances : list[float], optional
            List of reference impedances for each port.

        Returns
        -------
        dict
            Results dictionary with keys:
            - 'frequencies': sorted list of frequencies in Hz
            - 'S_params': dict of {freq: S_matrix} per frequency

        Raises
        ------
        SolverError
            If Z-matrices are empty or have invalid dimensions.
        """
        if not Z_matrices:
            raise SolverError("Z_matrices cannot be empty")

        # Sort frequencies and compute S-parameters for each
        sorted_freqs = sorted(Z_matrices.keys())
        s_params = {}

        for freq in sorted_freqs:
            z_mat = Z_matrices[freq]
            S = self.compute_S_parameters(z_mat, port_impedances, frequency_Hz=freq)
            s_params[float(freq)] = S

        return {
            "frequencies": sorted_freqs,
            "S_params": s_params,
        }

    def compute_full_s_matrix(
        self,
        frequencies: np.ndarray,
        Z_matrices: Dict[str, np.ndarray],
    ) -> dict:
        """Compute full N-port S-matrix across a frequency sweep.

        Parameters
        ----------
        frequencies : np.ndarray
            Frequency array in Hz with shape (N_freq,).
        Z_matrices : dict
            Dictionary mapping frequency keys to Z-matrices. Keys should
            match the format "f_{i}" where i is the frequency index.

        Returns
        -------
        dict
            Results dictionary with keys:
            - 'frequencies': array of frequencies in Hz
            - 's_parameters': dict of S-parameter matrices per frequency
            - 'mutual_coupling': dict of coupling coefficients between ports

        Raises
        ------
        SolverError
            If Z-matrices are missing or have invalid dimensions.
        """
        results = {
            "frequencies": frequencies.tolist(),
            "s_parameters": {},
            "mutual_coupling": {},
        }

        for i, freq in enumerate(frequencies):
            key = f"f_{i}"
            if key not in Z_matrices:
                raise SolverError(f"Z-matrix not found for frequency {key}")

            try:
                S = self.compute_s_parameters_from_Z(Z_matrices[key])
                results["s_parameters"][key] = S.tolist()

                # Compute mutual coupling coefficients
                coupling = self._compute_mutual_coupling(S)
                results["mutual_coupling"][key] = coupling

            except Exception as e:
                raise SolverError(
                    f"Failed to compute S-parameters at {freq:.3e} Hz",
                    context={"error": str(e)},
                )

        return results

    def _compute_mutual_coupling(
        self,
        S_matrix: np.ndarray,
    ) -> dict:
        """Compute mutual coupling coefficients between all port pairs.

        Parameters
        ----------
        S_matrix : np.ndarray
            S-parameter matrix with shape (N, N).

        Returns
        -------
        dict
            Coupling coefficients dictionary with keys:
            - 'coupling_db': dict of {f"{i}-{j}": value} for each pair
            - 'max_coupling_db': maximum coupling magnitude in dB
            - 'avg_coupling_db': average coupling magnitude (excluding self)
        """
        n = S_matrix.shape[0]
        coupling_db = {}

        max_coupling = 0.0
        total_coupling = 0.0
        count = 0

        for i in range(n):
            for j in range(n):
                if i != j:
                    # |S_ij| in dB (negative value)
                    s_ij_mag = np.abs(S_matrix[i, j])
                    s_ij_db = -20 * np.log10(max(s_ij_mag, 1e-15))

                    key = f"{i}-{j}"
                    coupling_db[key] = float(s_ij_db)

                    max_coupling = max(max_coupling, s_ij_db)
                    total_coupling += s_ij_db
                    count += 1

        return {
            "coupling_db": coupling_db,
            "max_coupling_db": float(max_coupling),
            "avg_coupling_db": float(total_coupling / count) if count > 0 else 0.0,
        }


class ArrayFactorAnalyzer:
    """Analyze array factor and beam steering for antenna arrays.

    This class provides methods for computing array factors, beam
    steering angles, and directivity for N-element antenna arrays.

    Parameters
    ----------
    n_elements : int
        Number of array elements.
    element_spacing : float, default=0.5
        Element spacing in wavelengths.
    """

    def __init__(
        self,
        n_elements: int,
        element_spacing: float = 0.5,
    ) -> None:
        """Initialise the array factor analyzer."""
        self.n_elements = n_elements
        self.element_spacing = element_spacing

    def compute_array_factor(
        self,
        theta_angles: np.ndarray,
        excitation_weights: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Compute the array factor magnitude for given angles.

        Parameters
        ----------
        theta_angles : np.ndarray
            Theta angles in radians with shape (N_angles,).
        excitation_weights : np.ndarray, optional
            Complex excitation weights for each element with shape
            (n_elements,). Uses uniform weighting if None.

        Returns
        -------
        np.ndarray
            Array factor magnitude values with shape (N_angles,).
        """
        if excitation_weights is None:
            excitation_weights = np.ones(self.n_elements)

        # Compute array factor: AF = sum(w_n * exp(j*k*d*n*cos(theta)))
        k = 2 * np.pi  # Normalized wavenumber (in wavelengths)
        d = self.element_spacing

        af = np.zeros(len(theta_angles), dtype=np.complex128)

        for n in range(self.n_elements):
            phase = k * d * n * np.cos(theta_angles)
            af += excitation_weights[n] * np.exp(1j * phase)

        # Normalize to maximum value
        af_mag = np.abs(af)
        if np.max(af_mag) > 0:
            af_mag /= np.max(af_mag)

        return af_mag

    def compute_beam_steering_angle(
        self,
        excitation_weights: np.ndarray,
    ) -> float:
        """Compute the beam steering angle from excitation weights.

        Parameters
        ----------
        excitation_weights : np.ndarray
            Complex excitation weights with shape (n_elements,).

        Returns
        -------
        float
            Beam steering angle in degrees.
        """
        # Compute phase difference between adjacent elements
        phases = np.angle(excitation_weights)
        phase_diff = phases[1] - phases[0] if len(phases) > 1 else 0

        # Beam angle: cos(theta_0) = -phase_diff / (k*d)
        k_d = 2 * np.pi * self.element_spacing
        cos_theta = -phase_diff / k_d if k_d != 0 else 0

        # Clamp to valid range
        cos_theta = np.clip(cos_theta, -1.0, 1.0)
        theta_rad = np.arccos(cos_theta)
        theta_deg = np.rad2deg(theta_rad)

        return float(theta_deg)

    def compute_directivity(
        self,
        theta_angles: np.ndarray,
        af_magnitude: np.ndarray,
    ) -> float:
        """Compute array directivity from array factor.

        Parameters
        ----------
        theta_angles : np.ndarray
            Theta angles in radians with shape (N_angles,).
        af_magnitude : np.ndarray
            Normalized array factor magnitude with shape (N_angles,).

        Returns
        -------
        float
            Directivity in dBi.
        """
        # Numerical integration of radiation intensity
        sin_theta = np.sin(theta_angles)
        intensity = af_magnitude ** 2 * sin_theta

        # Integrate over theta (0 to pi)
        du = theta_angles[1] - theta_angles[0] if len(theta_angles) > 1 else np.pi / 180
        total_power = np.sum(intensity) * du

        # Directivity: D = 4*pi*U_max / P_rad
        u_max = np.max(af_magnitude ** 2)
        d_linear = 4 * np.pi * u_max / max(total_power, 1e-15)
        d_dbi = 10 * np.log10(d_linear)

        return float(d_dbi)
