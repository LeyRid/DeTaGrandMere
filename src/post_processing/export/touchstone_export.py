"""Touchstone file format exporter and importer for S-parameter data.

Implements the Touchstone v2.0 format (per IEC 61746-3) for exporting and
importing S-parameter data files (.s1p, .s2p, ..., .sNp).

Supported features:
- Single-port (.s1p) through four-port (.s4p) formats
- Optional multi-port extension (up to 8 ports)
- Frequency data in GHz, MHz, kHz, Hz, or seconds
- Magnitude/phase and real/imaginary representations
- Comment headers with date, description, and simulation metadata

Example usage::

    from src.post_processing.export.touchstone_export import TouchstoneExporter

    exporter = TouchstoneExporter(n_ports=2)
    exporter.write_sparams(
        frequencies_hz=freqs,
        s_params=s_matrix,  # shape (N_freq, N_ports, N_ports)
        output_file="results.s2p",
    )
"""

from __future__ import annotations

import os
import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class TouchstoneExporter:
    """Export S-parameter data to Touchstone format files.

    Parameters
    ----------
    n_ports : int, optional
        Number of ports (1-4 supported, up to 8 with extension). Default is 2.
    frequency_unit : str, optional
        Frequency unit string: 'GHz', 'MHz', 'kHz', 'Hz', or 's'. Default is 'GHz'.
    data_format : str, optional
        Data representation: 'MA' (magnitude/phase) or 'RI' (real/imaginary). Default is 'MA'.
    """

    SUPPORTED_UNITS = {"GHz", "MHz", "kHz", "Hz", "s"}
    SUPPORTED_FORMATS = {"MA", "RI"}

    def __init__(
        self,
        n_ports: int = 2,
        frequency_unit: str = "GHz",
        data_format: str = "MA",
    ) -> None:
        """Initialise the Touchstone exporter.

        Parameters
        ----------
        n_ports : int, optional
            Number of ports (1-4 supported). Default is 2.
        frequency_unit : str, optional
            Frequency unit. Default is 'GHz'.
        data_format : str, optional
            Data format: 'MA' or 'RI'. Default is 'MA'.
        """
        if not (1 <= n_ports <= 8):
            raise ValueError(f"n_ports must be 1-8, got {n_ports}")
        if frequency_unit not in self.SUPPORTED_UNITS:
            raise ValueError(
                f"frequency_unit must be one of {self.SUPPORTED_UNITS}, got {frequency_unit}"
            )
        if data_format not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"data_format must be one of {self.SUPPORTED_FORMATS}, got {data_format}"
            )

        self.n_ports = n_ports
        self.frequency_unit = frequency_unit
        self.data_format = data_format
        self._metadata: dict[str, str] = {}

    def set_metadata(self, **kwargs: str) -> None:
        """Set arbitrary metadata key-value pairs for the file header.

        Parameters
        ----------
        **kwargs : str
            Key-value pairs to include in the Touchstone comment header.
        """
        self._metadata.update(kwargs)

    def _get_file_extension(self) -> str:
        """Return the Touchstone file extension (e.g., '.s2p')."""
        return f".s{self.n_ports}p"

    def write_sparams(
        self,
        frequencies_hz: np.ndarray,
        s_params: np.ndarray,
        output_file: str,
        description: str = "",
    ) -> str:
        """Write S-parameter data to a Touchstone file.

        Parameters
        ----------
        frequencies_hz : np.ndarray
            Frequency array in Hz with shape ``(N_freq,)``.
        s_params : np.ndarray
            S-parameter matrix with shape ``(N_freq, N_ports, N_ports)``.
        output_file : str
            Path for the output file (e.g., 'results.s2p').
        description : str, optional
            Optional description string to include in comments.

        Returns
        -------
        str
            Full path of the written file.
        """
        frequencies_hz = np.asarray(frequencies_hz)
        s_params = np.asarray(s_params)

        if self.data_format == "MA":
            mag = np.abs(s_params)
            phase = np.degrees(np.angle(s_params))
        else:  # RI
            mag = None
            phase = None

        lines = []
        # Touchstone v2.0 header
        lines.append(f"# Touchstone {self.data_format} {self.frequency_unit} "
                     f"n={self.n_ports} date=\"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\"")

        if description:
            lines.append(f"! {description}")

        for key, val in self._metadata.items():
            lines.append(f"! {key}={val}")

        # Data rows
        for i, freq_hz in enumerate(frequencies_hz):
            freq_val = self._format_frequency(freq_hz)
            s_row = s_params[i]

            if self.data_format == "MA":
                # Magnitude/phase: each S-parameter is mag phase
                parts = [freq_val]
                for p in range(self.n_ports):
                    for q in range(self.n_ports):
                        val = s_row[p, q]
                        m = abs(val) if np.abs(val) > 1e-15 else 0.0
                        ph = float(np.angle(val)) * 180.0 / np.pi if np.abs(val) > 1e-15 else 0.0
                        parts.append(f"{m:.12e} {ph:.6f}")
                lines.append(" ".join(parts))
            else:
                # Real/imaginary: each S-parameter is real imag
                parts = [freq_val]
                for p in range(self.n_ports):
                    for q in range(self.n_ports):
                        val = s_row[p, q]
                        parts.append(f"{val.real:.12e} {val.imag:.12e}")
                lines.append(" ".join(parts))

        content = "\n".join(lines) + "\n"

        # Write to file
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
        with open(output_file, "w") as f:
            f.write(content)

        logger.info("Wrote Touchstone file: %s (%d data points)", output_file, len(frequencies_hz))
        return output_file

    def _format_frequency(self, freq_hz: float) -> str:
        """Format frequency value according to the chosen unit."""
        if self.frequency_unit == "GHz":
            return f"{freq_hz / 1e9:.12f}"
        elif self.frequency_unit == "MHz":
            return f"{freq_hz / 1e6:.12f}"
        elif self.frequency_unit == "kHz":
            return f"{freq_hz / 1e3:.12f}"
        elif self.frequency_unit == "Hz":
            return f"{freq_hz:.12f}"
        else:  # seconds
            return f"{1.0 / freq_hz:.12e}" if freq_hz > 0 else "0"


class TouchstoneImporter:
    """Import S-parameter data from Touchstone files.

    Parameters
    ----------
    validate : bool, default=True
        Whether to validate the imported data (port count, frequency consistency).
    """

    def __init__(self, validate: bool = True) -> None:
        """Initialise the Touchstone importer.

        Parameters
        ----------
        validate : bool, default=True
            Validate port count and frequency consistency after import.
        """
        self.validate = validate
        self._header_info: dict[str, str] = {}

    def read_sparams(self, input_file: str) -> dict:
        """Read S-parameter data from a Touchstone file.

        Parameters
        ----------
        input_file : str
            Path to the .sNp Touchstone file.

        Returns
        -------
        dict
            Dictionary with keys:
            - 'frequencies_hz': np.ndarray of frequencies in Hz
            - 's_params': np.ndarray of shape (N_freq, N_ports, N_ports)
            - 'data_format': str ('MA' or 'RI')
            - 'frequency_unit': str
            - 'n_ports': int
            - 'metadata': dict of comment header info

        Raises
        ------
        FileNotFoundError
            If the input file does not exist.
        ValueError
            If the file format is invalid or corrupted.
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Touchstone file not found: {input_file}")

        with open(input_file, "r") as f:
            lines = f.readlines()

        # Parse header
        n_ports = 2
        data_format = "MA"
        frequency_unit = "GHz"
        metadata: dict[str, str] = {}
        data_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                # Parse Touchstone header
                parts = stripped.split()
                if len(parts) >= 2 and parts[1] == "Touchstone":
                    if len(parts) >= 3:
                        data_format = parts[2]
                    if len(parts) >= 4:
                        frequency_unit = parts[3]
                    # Parse n= value
                    for part in parts:
                        if part.startswith("n="):
                            n_ports = int(part.split("=")[1])
                elif stripped.startswith("!"):
                    comment = stripped[1:].strip()
                    if "=" in comment:
                        key, val = comment.split("=", 1)
                        metadata[key.strip()] = val.strip()
                    else:
                        metadata["description"] = comment
            else:
                data_lines.append(stripped)

        self._header_info = {
            "data_format": data_format,
            "frequency_unit": frequency_unit,
            "n_ports": n_ports,
            "metadata": metadata,
        }

        # Parse data lines
        n_data_points = len(data_lines)
        s_params = np.zeros((n_data_points, n_ports, n_ports), dtype=complex)
        frequencies = np.zeros(n_data_points)

        for i, line in enumerate(data_lines):
            parts = line.split()
            freq_val = float(parts[0])

            # Convert frequency to Hz based on unit
            if frequency_unit == "GHz":
                frequencies[i] = freq_val * 1e9
            elif frequency_unit == "MHz":
                frequencies[i] = freq_val * 1e6
            elif frequency_unit == "kHz":
                frequencies[i] = freq_val * 1e3
            elif frequency_unit == "Hz":
                frequencies[i] = freq_val
            else:  # seconds
                frequencies[i] = 1.0 / freq_val if freq_val > 0 else 0

            # Parse S-parameter data
            idx = 1
            for p in range(n_ports):
                for q in range(n_ports):
                    if data_format == "MA":
                        mag = float(parts[idx])
                        phase_deg = float(parts[idx + 1])
                        s_params[i, p, q] = mag * np.exp(1j * np.deg2rad(phase_deg))
                        idx += 2
                    else:  # RI
                        real = float(parts[idx])
                        imag = float(parts[idx + 1])
                        s_params[i, p, q] = complex(real, imag)
                        idx += 2

        result = {
            "frequencies_hz": frequencies,
            "s_params": s_params,
            "data_format": data_format,
            "frequency_unit": frequency_unit,
            "n_ports": n_ports,
            "metadata": metadata,
        }

        # Validate if requested
        if self.validate:
            self._validate_result(result)

        logger.info("Read Touchstone file: %s (%d points, %d ports)", input_file, n_data_points, n_ports)
        return result

    def _validate_result(self, result: dict) -> None:
        """Validate imported data for consistency."""
        s_params = result["s_params"]
        n_ports = result["n_ports"]

        # Check port count matches file header
        if s_params.shape[1] != n_ports or s_params.shape[2] != n_ports:
            raise ValueError(
                f"Port count mismatch: expected {n_ports}x{n_ports}, got "
                f"{s_params.shape[1]}x{s_params.shape[2]}"
            )

        # Check for NaN/Inf values
        if np.any(np.isnan(s_params)) or np.any(np.isinf(s_params)):
            raise ValueError("Imported S-parameters contain NaN or Inf values")

        # Check frequency ordering (should be monotonic)
        freqs = result["frequencies_hz"]
        if not np.all(np.diff(freqs) > 0):
            logger.warning("Frequencies are not strictly monotonically increasing")
