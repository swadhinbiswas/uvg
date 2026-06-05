"""UV integration layer.

Delegates to UV for dependency resolution, wheel download,
and lock file generation.
"""

from gvx.uv.lockfile import GVXLockfile, UVLockfileParser
from gvx.uv.resolver import ResolutionResult, UVResolver

__all__ = [
    "GVXLockfile",
    "ResolutionResult",
    "UVLockfileParser",
    "UVResolver",
]
