"""CAD package exception re-exports."""

from src.utils.errors import MeshError

__all__: list[str] = ["MeshError"]
