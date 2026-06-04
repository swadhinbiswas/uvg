"""Workspace mode for UVG.

Provides monorepo support with workspace discovery, synchronization,
dependency graph visualization, and cross-project analytics.
"""

from uvg.workspace.discovery import WorkspaceDiscovery, WorkspaceManifest, WorkspaceProject
from uvg.workspace.manager import WorkspaceManager

__all__ = [
    "WorkspaceDiscovery",
    "WorkspaceManager",
    "WorkspaceManifest",
    "WorkspaceProject",
]
