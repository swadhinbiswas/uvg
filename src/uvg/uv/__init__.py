"""UV integration layer.

Delegates to UV for dependency resolution, wheel download,
and lock file generation.
"""

from uvg.uv.lockfile import UVGLockfile, UVLockfileParser
from uvg.uv.resolver import ResolutionResult, UVResolver

__all__ = [
    "ResolutionResult",
    "UVGLockfile",
    "UVLockfileParser",
    "UVResolver",
]
