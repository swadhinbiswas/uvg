"""Dependency intelligence layer for UVG.

Provides import analysis, unused/missing dependency detection,
and dependency conflict detection.
"""

from uvg.intelligence.analyzer import DependencyReport, ImportAnalyzer
from uvg.intelligence.scanner import ProjectScanner

__all__ = [
    "DependencyReport",
    "ImportAnalyzer",
    "ProjectScanner",
]
