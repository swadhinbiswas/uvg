# UVG

**One Package Store. Zero Duplicate Environments.**

UVG is the runtime layer that Python never had.

UVG is not a package manager.
UVG is not a dependency resolver.
UVG is not a replacement for UV.

UVG is a runtime, storage, caching, diagnostics, and dependency intelligence layer built on top of UV.

---

## Quick Start

```bash
# Install UVG
pip install uvg

# Initialize UVG in a project
uvg init

# Sync dependencies
uvg sync

# Run with correct runtime
uvg run python script.py

# Diagnose dependency issues
uvg doctor

# Scan for unused/missing dependencies
uvg scan

# Show storage and dependency stats
uvg stats
```

---

## Features

- **Global Content-Addressable Store**: Packages stored once, by content hash
- **Runtime Construction**: Isolated import paths from shared store
- **Runtime Fingerprinting**: Deterministic fingerprints enable runtime reuse
- **Dependency Intelligence**: Unused deps, missing deps, conflict detection
- **Workspace Mode**: First-class monorepo support
- **Security**: Hash verification, integrity validation, supply chain checks
- **Performance**: Cold runtime <2s, warm runtime <200ms

---

## Documentation

- [Vision](Vision.md)
- [Architecture](Architecture.md)
- [Runtime Architecture](RuntimeArchitecture.md)
- [Store Architecture](StoreArchitecture.md)
- [Database Architecture](DatabaseArchitecture.md)
- [Security Architecture](SecurityArchitecture.md)
- [Roadmap](Roadmap.md)
- [Milestones](Milestones.md)
- [Release Plan](ReleasePlan.md)
- [Contributing](Contributing.md)
- [Governance](Governance.md)
- [Architecture Decision Records](adr/README.md)

---

## License

MIT
