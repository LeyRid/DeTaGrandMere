"""Port definition module for electromagnetic simulation excitation ports.

This module defines types and managers for creating and managing simulation
ports (lumped and waveguide), including placement validation against a mesh
and frequency-dependent sizing checks.

Example usage::

    from port_definition import PortManager, PortType

    mgr = PortManager()
    pid = mgr.create_lumped_port(
        "port1", location=[0, 0, 0], surface_ids=[0], size=0.01
    )
    mgr.create_waveguide_port("wg1", location=[0.5, 0, 0], surface_ids=[1], size=0.02)
    result = mgr.validate_placement(mesh, frequency=1e9)
    print(result["warnings"])
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import numpy as np

from .errors import CADError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & Data classes
# ---------------------------------------------------------------------------


class PortType(Enum):
    """Types of simulation excitation ports.

    Members
    -------
    LUMPED
        Lumped port -- applies a voltage/current source over a defined region.
    WAVEGUIDE
        Waveguide port -- launches/absorbs guided modes at a cross-section.
    """

    LUMPED = "LUMPED"
    WAVEGUIDE = "WAVEGUIDE"


@dataclass
class Port:
    """Describes an excitation port on the simulation geometry.

    Attributes
    ----------
    name : str
        Human-readable identifier for the port.
    port_type : PortType
        The physical type of the port (lumped or waveguide).
    location : np.ndarray
        3-D spatial position of the port centre, shape ``(3,)``.
    surface_ids : list[int]
            Mesh surface identifiers defining where the port is applied.
    size : float
        Characteristic transverse dimension in metres.
    impedance : float
        Reference impedance in ohms (default 50.0).
    orientation : np.ndarray
        Normal direction vector of the port face, shape ``(3,)``.
        Defaults to ``[1, 0, 0]``.
    excitation_phase : float
        Excitation phase offset in radians (default 0.0).
    excitation_amplitude : float
        Excitation amplitude scaling factor (default 1.0).
    """

    name: str
    port_type: PortType
    location: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    surface_ids: List[int] = field(default_factory=list)
    size: float = 0.01
    impedance: float = 50.0
    orientation: np.ndarray = field(
        default_factory=lambda: np.array([1.0, 0.0, 0.0], dtype=np.float64)
    )
    excitation_phase: float = 0.0
    excitation_amplitude: float = 1.0

    def __post_init__(self) -> None:
        self.location = np.asarray(self.location, dtype=np.float64)
        self.orientation = np.asarray(self.orientation, dtype=np.float64)
        if self.location.shape != (3,):
            raise CADError(f"Port '{self.name}': location must have shape (3,), got {self.location.shape}")
        if self.orientation.shape != (3,):
            raise CADError(f"Port '{self.name}': orientation must have shape (3,), got {self.orientation.shape}")
        norm = np.linalg.norm(self.orientation)
        if norm < 1e-12:
            raise CADError(f"Port '{self.name}': orientation vector is near-zero.")

    def to_dict(self) -> dict:
        """Return a serialisable dictionary.

        Returns
        -------
        dict
            Port fields with numpy arrays converted to lists.
        """
        return {
            "name": self.name,
            "port_type": self.port_type.value,
            "location": list(self.location),
            "surface_ids": list(self.surface_ids),
            "size": float(self.size),
            "impedance": float(self.impedance),
            "orientation": list(self.orientation),
            "excitation_phase": float(self.excitation_phase),
            "excitation_amplitude": float(self.excitation_amplitude),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Port":
        """Reconstruct a Port from a serialisable dictionary.

        Parameters
        ----------
        data : dict
            Dictionary produced by :meth:`to_dict`.

        Returns
        -------
        Port
            Restored port instance.
        """
        return cls(
            name=data["name"],
            port_type=PortType(data["port_type"]),
            location=np.array(data["location"], dtype=np.float64),
            surface_ids=data["surface_ids"],
            size=data["size"],
            impedance=data["impedance"],
            orientation=np.array(data["orientation"], dtype=np.float64),
            excitation_phase=data.get("excitation_phase", 0.0),
            excitation_amplitude=data.get("excitation_amplitude", 1.0),
        )


# ---------------------------------------------------------------------------
# PortManager
# ---------------------------------------------------------------------------


class PortManager:
    """Manages simulation excitation ports.

    Provides factory methods for creating lumped and waveguide ports, along
    with placement validation utilities.

    Example usage::

        mgr = PortManager()
        pid = mgr.create_lumped_port(
            "feed", location=[0, 0, 0], surface_ids=[0], size=0.005
        )
        mgr.remove_port(pid)
        for p in mgr.list_ports():
            print(p.name)
    """

    def __init__(self) -> None:
        self._ports: Dict[str, Port] = {}

    # ------------------------------------------------------------------ factory methods ---------------------------------

    def create_lumped_port(
        self,
        name: str,
        location: np.ndarray,
        surface_ids: List[int],
        size: float,
        impedance: float = 50.0,
        orientation: Optional[np.ndarray] = None,
        phase: float = 0.0,
        amplitude: float = 1.0,
    ) -> str:
        """Create a lumped excitation port.

        A lumped port applies a voltage/current source over the defined
        surface region and is commonly used for coaxial feeds or discrete
        component connections.

        Parameters
        ----------
        name : str
            Port identifier.
        location : np.ndarray
            3-D position of the port centre, shape ``(3,)``.
        surface_ids : list[int]
            Mesh surface identifiers.
        size : float
            Transverse dimension in metres.
        impedance : float
            Reference impedance in ohms (default 50.0).
        orientation : np.ndarray or None
            Normal direction; defaults to ``[1, 0, 0]``.
        phase : float
            Excitation phase offset in radians (default 0.0).
        amplitude : float
            Excitation amplitude scaling factor (default 1.0).

        Returns
        -------
        str
            Unique port identifier.
        """
        if orientation is None:
            orientation = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        loc = np.asarray(location, dtype=np.float64)

        port_id = f"port_{uuid.uuid4().hex[:8]}"
        self._ports[port_id] = Port(
            name=name,
            port_type=PortType.LUMPED,
            location=loc,
            surface_ids=list(surface_ids),
            size=float(size),
            impedance=float(impedance),
            orientation=orientation,
            excitation_phase=float(phase),
            excitation_amplitude=float(amplitude),
        )
        logger.info("Created lumped port %s ('%s')", port_id, name)
        return port_id

    def create_waveguide_port(
        self,
        name: str,
        location: np.ndarray,
        surface_ids: List[int],
        size: float,
        impedance: float = 50.0,
        orientation: Optional[np.ndarray] = None,
        mode_number: int = 1,
    ) -> str:
        """Create a waveguide excitation port.

        A waveguide port launches or absorbs guided modes at a cross-section
        and is typically used for rectangular/circular waveguides and
        microstrip transitions.

        Parameters
        ----------
        name : str
            Port identifier.
        location : np.ndarray
            3-D position of the port centre, shape ``(3,)``.
        surface_ids : list[int]
            Mesh surface identifiers.
        size : float
            Transverse dimension in metres.
        impedance : float
            Reference impedance in ohms (default 50.0).
        orientation : np.ndarray or None
            Normal direction; defaults to ``[1, 0, 0]``.
        mode_number : int
            Mode number to excite (default 1).

        Returns
        -------
        str
            Unique port identifier.
        """
        if orientation is None:
            orientation = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        loc = np.asarray(location, dtype=np.float64)

        port_id = f"port_{uuid.uuid4().hex[:8]}"
        self._ports[port_id] = Port(
            name=name,
            port_type=PortType.WAVEGUIDE,
            location=loc,
            surface_ids=list(surface_ids),
            size=float(size),
            impedance=float(impedance),
            orientation=orientation,
            excitation_phase=0.0,
            excitation_amplitude=1.0,
        )
        # Store mode_number as an extra attribute on the port dict entry
        self._ports[port_id].mode_number = mode_number  # type: ignore[attr-defined]
        logger.info("Created waveguide port %s ('%s')", port_id, name)
        return port_id

    # ------------------------------------------------------------------ CRUD -------------------------------

    def remove_port(self, port_id: str) -> None:
        """Remove a port by its identifier.

        Parameters
        ----------
        port_id : str
            Port identifier.

        Raises
        ------
        CADError
            If *port_id* is not registered.
        """
        if port_id not in self._ports:
            raise CADError(f"Port '{port_id}' not found.")
        del self._ports[port_id]
        logger.debug("Removed port %s", port_id)

    def get_port(self, port_id: str) -> Optional[Port]:
        """Retrieve a port by its identifier.

        Parameters
        ----------
        port_id : str
            Port identifier.

        Returns
        -------
        Port or None
            The requested port, or ``None`` if not found.
        """
        return self._ports.get(port_id)

    def list_ports(self) -> List[str]:
        """Return a sorted list of all port names.

        Returns
        -------
        list[str]
            Port name identifiers.
        """
        return sorted(p.name for p in self._ports.values())

    # ------------------------------------------------------------------ validation ---------------------------------

    def validate_placement(
        self, mesh, frequency: float
    ) -> dict:
        """Validate all port placements against a mesh at a given frequency.

        Checks that surface IDs referenced by ports exist within the mesh
        and that each port's transverse size is sufficiently large relative
        to the wavelength (minimum ``lambda/10``).

        Parameters
        ----------
        mesh
            A mesh-like object supporting ``get_surface_count()``.
        frequency : float
            Operating frequency in Hz used for wavelength calculations.

        Returns
        -------
        dict
            Keys ``warnings`` and ``errors``, each a list of human-readable
            strings.
        """
        warnings: List[str] = []
        errors: List[str] = []

        # Mesh surface count check
        try:
            max_surface = mesh.get_surface_count()
        except AttributeError:
            warnings.append(
                "Mesh object does not expose get_surface_count(); "
                "surface existence checks skipped."
            )
            max_surface = None

        if max_surface is not None:
            for pid, port in self._ports.items():
                for sid in port.surface_ids:
                    if sid >= max_surface:
                        errors.append(
                            f"Port '{port.name}' references surface {sid}, "
                            f"which exceeds mesh limit ({max_surface} surfaces)."
                        )

        # Wavelength-based size check (size >= lambda / 10)
        c = 299792458.0  # speed of light in m/s
        wavelength = c / frequency if frequency > 0 else float("inf")
        min_size = wavelength / 10.0

        for pid, port in self._ports.items():
            if port.size < min_size:
                warnings.append(
                    f"Port '{port.name}' has size {port.size:.4f} m which is "
                    f"< lambda/10 ({min_size:.4f} m) at {frequency / 1e6:.1f} MHz. "
                    f"Consider increasing port size."
                )

        # Check for ports with no surface assignment
        for pid, port in self._ports.items():
            if not port.surface_ids:
                warnings.append(f"Port '{port.name}' has no surface assigned.")

        return {"warnings": warnings, "errors": errors}

    def clear(self) -> None:
        """Remove all ports."""
        self._ports.clear()
        logger.info("Cleared all ports")


# ---------------------------------------------------------------------------
# Module-level example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mgr = PortManager()

    # Create a lumped port
    pid1 = mgr.create_lumped_port(
        "coax_feed",
        location=np.array([0.0, 0.0, 0.0]),
        surface_ids=[0],
        size=0.005,
        impedance=50.0,
        phase=0.0,
        amplitude=1.0,
    )
    print(f"Lumped port: {pid1}")

    # Create a waveguide port
    pid2 = mgr.create_waveguide_port(
        "waveguide_in",
        location=np.array([0.05, 0.0, 0.0]),
        surface_ids=[1],
        size=0.02286,
        mode_number=1,
    )
    print(f"Waveguide port: {pid2}")

    # List and retrieve
    for name in mgr.list_ports():
        print(f"Port: {name}")

    # Validate at 1 GHz
    class MockMesh:
        def get_surface_count(self):
            return 10

    result = mgr.validate_placement(MockMesh(), frequency=1e9)
    print("Validation warnings:", result["warnings"])
    print("Validation errors:", result["errors"])
