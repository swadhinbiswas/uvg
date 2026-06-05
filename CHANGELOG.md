# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.1] - 2026-06-04

### Added
- Content-addressable store with SHA-256 hash addressing
- Runtime construction with symlink-based import paths
- Deterministic runtime fingerprinting (SHA-256)
- Dependency intelligence (AST import analysis, unused/missing detection)
- Workspace mode (monorepo discovery, shared dependency tracking)
- Security verification engine (hash verification, runtime integrity, lockfile validation)
- UV integration (delegation for resolution, downloads, lockfile parsing)
- CLI with 12 commands: init, add, remove, sync, run, doctor, scan, verify, stats, info, store, workspace
- SQLite index with WAL mode for concurrent access
- Package identity 7-tuple model (name, version, python_version, abi_tag, platform_tag, architecture, wheel_hash)
- Comprehensive test suite (142 tests)
- CI/CD pipeline with test matrix, lint, type check, benchmarks
- Documentation site (Astro + Starlight)
