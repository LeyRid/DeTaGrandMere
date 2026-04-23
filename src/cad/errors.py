"""CAD package exception re-exports."""

from src.utils.errors import MeshError, CADError

__all__: list[str] = ["MeshError", "CADError"]


class MaterialError(CADError):
    """Raised when material database operations fail.

    Covers unknown materials, invalid permittivity values,
    and errors in dispersive model calculations.
    """


class BoundaryConditionError(CADError):
    """Raised when boundary condition operations fail.

    Includes invalid BC types, conflicting conditions,
    and errors applying BCs to mesh surfaces.
    """


class PortDefinitionError(CADError):
    """Raised when port definition operations fail.

    Covers invalid port positions, unsupported port types,
    and errors associating ports with mesh edges/faces.
    """
