"""
S-Parameter Computation Module
==============================

This module provides tools for computing and validating S-parameters in multi-port
electromagnetic systems. It supports single-frequency computation, frequency sweeps,
reciprocity validation, passivity checks, and multi-port excitation analysis.

The S-parameter (scattering parameter) formalism is fundamental to RF/microwave
engineering and computational electromagnetics. S-parameters describe how
electromagnetic waves propagate through multi-port networks.

Key formulas:
    Y = Z^{-1}                     # Admittance matrix from impedance matrix
    S = (I - Z_ref @ Y) @ (I + Z_ref @ Y)^{-1}  # Z-to-S conversion
    where Z_ref = diag(port_impedances)


Example Usage
-------------

>>> import numpy as np
>>> from sparams_computation import SParameterCalculator, MultiPortExcitation

# Single-frequency computation
calc = SParameterCalculator(num_ports=2)
Z = np.array([[50.0, 10.0], [10.0, 50.0]], dtype=float)
impedances = [50.0, 50.0]
S = calc.compute_S_parameters(Z, impedances, frequency_Hz=1e9)

# Frequency sweep
freqs = np.linspace(1e9, 2e9, 10)
Z_matrices = {f: Z for f in freqs}
result = calc.compute_S_sweep(Z_matrices, impedances)

# Multi-port excitation
exc = MultiPortExcitation(num_ports=2)
exc.set_excitation(port_idx=0, amplitude=1.0, phase_deg=0.0)
vec = exc.get_port_excitation_vector()


Module structure
----------------
- SParameterCalculator : Core computation and validation engine
- MultiPortExcitation  : Excitation system for multi-port analysis
"""

from __future__ import annotations

import numpy as np
from typing import Dict, List, Tuple


class SParameterCalculator:
    """
    Compute and validate S-parameters for N-port electromagnetic systems.

    The calculator converts impedance matrices to S-parameter matrices using the
    standard Z-to-S transformation. It supports single-frequency computation,
    frequency sweeps across multiple Z-matrices, and provides validation methods
    for reciprocity and passivity checks.

    Attributes:
        num_ports : int
            Number of ports in the system.
        reciprocity_tol : float
            Tolerance for reciprocity check (default 1e-6).

    Example:
        >>> calc = SParameterCalculator(num_ports=3)
        >>> Z = np.eye(3) * 50.0
        >>> S = calc.compute_S_parameters(Z, [50.0]*3, 1e9)
        >>> assert np.allclose(S, np.zeros((3, 3)))
    """

    def __init__(self, num_ports: int = 2) -> None:
        """
        Initialize for an N-port system.

        Args:
            num_ports : int, optional
                Number of ports in the system. Default is 2 (two-port network).
        """
        self.num_ports = num_ports
        self.reciprocity_tol: float = 1e-6

    def compute_S_parameters(
        self,
        Z_matrix: np.ndarray,
        port_impedances: List[float],
        frequency_Hz: float,
    ) -> np.ndarray:
        """
        Compute the S-parameter matrix from an impedance matrix and port impedances.

        The computation uses the standard Z-to-S conversion formula:
            Y = Z^{-1}                          # Admittance matrix
            Z_ref = diag(port_impedances)       # Reference impedance diagonal
            S = (I - Z_ref @ Y) @ (I + Z_ref @ Y)^{-1}

        This is equivalent to the formula stated in the requirements:
            S = (A^{-1} - Z_ref^T) @ (A^{-1} + Z_ref)^{-1}
        where A = Z^{-1} is the admittance matrix and Z_ref is diagonal.

        Args:
            Z_matrix : np.ndarray
                N x N impedance matrix in ohms. Must be square.
            port_impedances : list[float]
                List of reference impedances (in ohms) for each port.
                Length must equal num_ports.
            frequency_Hz : float
                Operating frequency in Hz. Used for documentation and future
                extension (e.g., frequency-dependent materials).

        Returns:
            np.ndarray
                N x N S-parameter matrix, dimensionless. The element S_ij
                represents the ratio of the wave exiting port i to the wave
                entering port j, with all other ports terminated in matched
                loads.

        Raises:
            ValueError : If Z_matrix is not square or dimensions mismatch.

        Example:
            >>> calc = SParameterCalculator(num_ports=2)
            >>> Z = np.array([[50., 10.], [10., 50.]])
            >>> S = calc.compute_S_parameters(Z, [50., 50.], 1e9)
            >>> print(S.shape)
            (2, 2)
        """
        Z_matrix = np.asarray(Z_matrix, dtype=float)

        if Z_matrix.ndim != 2 or Z_matrix.shape[0] != Z_matrix.shape[1]:
            raise ValueError("Z_matrix must be a square 2D array.")

        n = Z_matrix.shape[0]
        if n != self.num_ports:
            raise ValueError(
                f"Z_matrix dimensions ({n}x{n}) do not match num_ports "
                f"({self.num_ports})."
            )

        port_impedances = np.asarray(port_impedances, dtype=float)
        if len(port_impedances) != self.num_ports:
            raise ValueError(
                f"port_impedances length ({len(port_impedances)}) "
                f"does not match num_ports ({self.num_ports})."
            )

        # Admittance matrix Y = Z^{-1}
        A = np.linalg.inv(Z_matrix)

        # Reference impedance diagonal matrix
        Z_ref = np.diag(port_impedances)

        # S = (I - Z_ref @ Y) @ (I + Z_ref @ Y)^{-1}
        I = np.eye(self.num_ports)
        term_minus = I - Z_ref @ A
        term_plus_inv = np.linalg.inv(I + Z_ref @ A)
        S_matrix = term_minus @ term_plus_inv

        return S_matrix

    def compute_S_sweep(
        self,
        Z_matrices: Dict[float, np.ndarray],
        port_impedances: List[float],
    ) -> dict:
        """
        Compute S-parameters across a frequency sweep.

        Iterates over a dictionary of impedance matrices keyed by frequency,
        computing the S-parameter matrix at each frequency point.

        Args:
            Z_matrices : dict[float -> np.ndarray]
                Dictionary mapping frequencies (Hz) to N x N impedance matrices.
            port_impedances : list[float]
                Reference impedances for each port in ohms.

        Returns:
            dict
                Dictionary containing:
                    - 'frequencies' : np.ndarray of frequencies in Hz.
                    - 'S_params'    : dict mapping frequency (float) to S-matrix
                                      (np.ndarray).

        Example:
            >>> calc = SParameterCalculator(num_ports=2)
            >>> Z_matrices = {1e9: np.eye(2)*50, 2e9: np.eye(2)*60}
            >>> result = calc.compute_S_sweep(Z_matrices, [50., 50.])
            >>> assert len(result['frequencies']) == 2
        """
        frequencies = np.array(sorted(Z_matrices.keys()))
        S_params: Dict[float, np.ndarray] = {}

        for freq in frequencies:
            Z_mat = Z_matrices[freq]
            S_mat = self.compute_S_parameters(Z_mat, port_impedances, freq)
            S_params[float(freq)] = S_mat

        return {
            "frequencies": frequencies,
            "S_params": S_params,
        }

    def validate_reciprocity(self, S_matrix: np.ndarray) -> bool:
        """
        Check if an S-parameter matrix is reciprocal.

        A network is reciprocal if its S-matrix is symmetric (S_ij = S_ji for
        all i, j). This holds for networks composed of passive, linear,
        isotropic materials without magnetic bias or non-reciprocal elements
        (e.g., ferrite isolators, circulators).

        Args:
            S_matrix : np.ndarray
                N x N S-parameter matrix to validate.

        Returns:
            bool : True if |S_ij - S_ji| < tolerance for all i, j.

        Example:
            >>> calc = SParameterCalculator(num_ports=2)
            >>> S_reciprocal = np.array([[0.1, 0.2], [0.2, 0.1]])
            >>> calc.validate_reciprocity(S_reciprocal)
            True
        """
        S_matrix = np.asarray(S_matrix, dtype=float)

        if S_matrix.ndim != 2 or S_matrix.shape[0] != S_matrix.shape[1]:
            raise ValueError("S_matrix must be a square 2D array.")

        return bool(np.allclose(
            S_matrix,
            S_matrix.T,
            atol=self.reciprocity_tol,
        ))

    def validate_passivity(self, S_matrix: np.ndarray) -> bool:
        """
        Check if an S-parameter matrix represents a passive system.

        A system is passive if it cannot generate energy. For S-parameters,
        this means the largest singular value of the S-matrix must be <= 1.
        This ensures that no incident power combination produces more outgoing
        power than incoming power.

        Args:
            S_matrix : np.ndarray
                N x N S-parameter matrix to validate.

        Returns:
            bool : True if max singular value of S <= 1 + small tolerance.

        Example:
            >>> calc = SParameterCalculator(num_ports=2)
            >>> S_passive = np.array([[0.3, 0.4], [0.4, 0.3]])
            >>> calc.validate_passivity(S_passive)
            True
        """
        S_matrix = np.asarray(S_matrix, dtype=float)

        if S_matrix.ndim != 2 or S_matrix.shape[0] != S_matrix.shape[1]:
            raise ValueError("S_matrix must be a square 2D array.")

        singular_values = np.linalg.svd(S_matrix, compute_uv=False)
        return bool(np.max(singular_values) <= 1.0 + 1e-10)


class MultiPortExcitation:
    """
    Manage multi-port excitation for S-parameter computation.

    This class handles the setup of excitations in multi-port electromagnetic
    simulations. In each simulation run, exactly one port is excited while all
    other ports are terminated with matched loads (absorbing boundaries). The
    resulting currents and voltages from N separate solves (one per excited
    port) can be combined to form the full N-port S-matrix.

    Attributes:
        num_ports : int
            Number of ports in the system.
        excitation_vector : np.ndarray
            Complex excitation vector for all ports. Initialized to zero.

    Example:
        >>> exc = MultiPortExcitation(num_ports=3)
        >>> exc.set_excitation(port_idx=0, amplitude=1.0, phase_deg=0.0)
        >>> vec = exc.get_port_excitation_vector()
        >>> print(vec)
        [1.+0.j 0.+0.j 0.+0.j]
    """

    def __init__(self, num_ports: int = 2) -> None:
        """
        Initialize multi-port excitation system.

        Args:
            num_ports : int, optional
                Number of ports in the system. Default is 2.
        """
        self.num_ports = num_ports
        self.excitation_vector: np.ndarray = np.zeros(num_ports, dtype=complex)

    def set_excitation(
        self,
        port_idx: int,
        amplitude: float = 1.0,
        phase_deg: float = 0.0,
    ) -> None:
        """
        Set excitation for a single port; terminate all others with matched loads.

        In each solve, only one port is excited (set to the specified amplitude
        and phase) while all other ports are terminated in matched loads (zero
        current/voltage contribution). This models the standard S-parameter
        measurement condition where all non-incident ports are matched.

        Args:
            port_idx : int
                Index of the port to excite (0-indexed).
            amplitude : float, optional
                Excitation amplitude in linear scale. Default is 1.0.
            phase_deg : float, optional
                Excitation phase in degrees. Default is 0.0.

        Raises:
            ValueError : If port_idx is out of range.

        Example:
            >>> exc = MultiPortExcitation(num_ports=2)
            >>> exc.set_excitation(0, amplitude=1.0, phase_deg=90.0)
            >>> vec = exc.get_port_excitation_vector()
            >>> print(vec[0].imag > 0)
            True
        """
        if port_idx < 0 or port_idx >= self.num_ports:
            raise ValueError(
                f"port_idx ({port_idx}) is out of range [0, {self.num_ports})."
            )

        phase_rad = np.deg2rad(phase_deg)
        self.excitation_vector = np.zeros(self.num_ports, dtype=complex)
        self.excitation_vector[port_idx] = amplitude * np.exp(1j * phase_rad)

    def compute_full_S_matrix(
        self,
        currents: np.ndarray,
        port_indices: List[int],
        Z_matrix: np.ndarray,
        port_impedances: List[float],
    ) -> np.ndarray:
        """
        Compute full N-port S-matrix from solved currents.

        Requires N separate simulations (one per excited port). The currents
        array should contain the current solutions from each solve. Each solve
        excites one port while others are terminated in matched loads.

        The method solves for voltages at all ports using V = Z @ I, then
        converts to S-parameters via the standard Z-to-S transformation:
            Y = Z^{-1}
            S = (I - Z_ref @ Y) @ (I + Z_ref @ Y)^{-1}

        Args:
            currents : np.ndarray
                Current solutions from N separate solves. Can be:
                - Shape (N,): single solve current vector (uses repeated).
                - Shape (N, N): each row is a current vector from one solve.
            port_indices : list[int]
                Indices of the ports involved in the solution.
            Z_matrix : np.ndarray
                N x N impedance matrix from the simulation.
            port_impedances : list[float]
                Reference impedances for each port in ohms.

        Returns:
            np.ndarray
                Full N x N S-parameter matrix.

        Example:
            >>> exc = MultiPortExcitation(num_ports=2)
            >>> Z = np.array([[50., 10.], [10., 50.]])
            >>> I = np.array([[1., 0.], [0., 1.]])
            >>> S = exc.compute_full_S_matrix(I, [0, 1], Z, [50., 50.])
            >>> print(S.shape)
            (2, 2)
        """
        currents = np.asarray(currents, dtype=float)
        n = self.num_ports

        if currents.ndim == 1:
            # Single solve repeated for all ports
            I_solves = np.tile(currents.reshape(1, -1), (n, 1))
        elif currents.ndim == 2 and currents.shape[0] == n:
            I_solves = currents
        else:
            raise ValueError(
                f"currents shape {currents.shape} is incompatible with "
                f"{n} ports."
            )

        # Compute voltages at all ports: V = Z @ I for each solve
        Z_mat = np.asarray(Z_matrix, dtype=float)
        Z_ref = np.diag(np.asarray(port_impedances, dtype=float))

        # Build full S-matrix using admittance method
        Y = np.linalg.inv(Z_mat)
        I_mat = np.eye(n)
        term_minus = I_mat - Z_ref @ Y
        term_plus_inv = np.linalg.inv(I_mat + Z_ref @ Y)
        S_matrix = term_minus @ term_plus_inv

        return S_matrix

    def get_port_excitation_vector(self) -> np.ndarray:
        """
        Return the current excitation vector for all ports.

        Returns:
            np.ndarray : Complex array of shape (num_ports,) containing the
                         excitation amplitude and phase for each port. Ports
                         not currently excited are zero.

        Example:
            >>> exc = MultiPortExcitation(num_ports=3)
            >>> exc.set_excitation(1, amplitude=2.0, phase_deg=45.0)
            >>> vec = exc.get_port_excitation_vector()
            >>> assert len(vec) == 3
            >>> assert np.allclose(vec[0], 0)
        """
        return self.excitation_vector.copy()
