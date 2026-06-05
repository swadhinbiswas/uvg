"""Workspace mode for GVX.

Provides monorepo support with workspace discovery, synchronization,
dependency graph visualization, and cross-project analytics.
"""

from gvx.workspace.discovery import WorkspaceDiscovery, WorkspaceManifest, WorkspaceProject
from gvx.workspace.manager import WorkspaceManager

__all__ = [
    "WorkspaceDiscovery",
    "WorkspaceManager",
    "WorkspaceManifest",
    "WorkspaceProject",
]
