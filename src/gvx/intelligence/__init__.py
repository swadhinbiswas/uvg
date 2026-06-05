"""Dependency intelligence layer for GVX.

Provides import analysis, unused/missing dependency detection,
and dependency conflict detection.
"""

from gvx.intelligence.analyzer import DependencyReport, ImportAnalyzer
from gvx.intelligence.scanner import ProjectScanner

__all__ = [
    "DependencyReport",
    "ImportAnalyzer",
    "ProjectScanner",
]
