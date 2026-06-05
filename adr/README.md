# Architecture Decision Records

**Date:** 2026-06-04
**Status:** APPROVED

---

## ADR-001: Content-Addressable Storage

**Status:** ACCEPTED
**Date:** 2026-06-04

### Context

GVX needs a storage system that eliminates duplication while maintaining isolation between projects. Traditional virtual environments duplicate packages across projects.

### Decision

Use content-addressable storage (CAS) where objects are stored by their SHA-256 hash. Each object is immutable and identified by a 7-tuple: (package_name, package_version, python_version, abi_tag, platform_tag, architecture, wheel_hash).

### Consequences

**Positive:**
- Eliminates duplication (80-90% savings)
- Enables verification (hash matches content)
- Supports multiple versions simultaneously
- Enables caching and reuse

**Negative:**
- More complex than name-based storage
- Requires hash computation on download
- Store structure is less intuitive for users

**Risks:**
- Hash collisions (mitigated by SHA-256)
- Store corruption (mitigated by verification)

---

## ADR-002: Symlink-Based Runtime Construction

**Status:** ACCEPTED
**Date:** 2026-06-04

### Context

GVX needs to construct isolated import paths for each project. Options include symlinks, `.pth` files, `PYTHONPATH` injection, and import hooks.

### Decision

Use symlinks as the primary method for runtime construction. Each project's `site-packages/` directory contains symlinks to store objects.

### Consequences

**Positive:**
- Native Python support
- IDE compatibility
- Tool compatibility
- Fast construction (O(1) per package)

**Negative:**
- Some tools may not follow symlinks
- Symlink count scales with dependency count

**Risks:**
- Windows symlink support (mitigated by junction points)
- Network filesystem symlink issues (mitigated by fallback to `.pth` files)

---

## ADR-003: SQLite for Indexing

**Status:** ACCEPTED
**Date:** 2026-06-04

### Context

GVX needs a persistent index for store objects, relationships, and fingerprints. Options include SQLite, embedded key-value stores, and in-memory databases.

### Decision

Use SQLite with WAL mode for all indexing. Three database files: `metadata.db`, `relationships.db`, `fingerprints.db`.

### Consequences

**Positive:**
- Zero configuration
- ACID guarantees
- Concurrent access (WAL mode)
- Single file, easy backup
- Well-tested and stable

**Negative:**
- Write serialization (mitigated by WAL mode)
- Limited concurrency for writes

**Risks:**
- Database corruption (mitigated by backups)
- Lock contention (mitigated by busy timeout)

---

## ADR-004: Delegate to UV for Resolution

**Status:** ACCEPTED
**Date:** 2026-06-04

### Context

GVX needs dependency resolution. UV already provides excellent resolution. Options include implementing a custom resolver, delegating to UV, or delegating to pip.

### Decision

Delegate to UV for all dependency resolution, wheel download, and lock file generation. GVX focuses on storage, runtime construction, and intelligence.

### Consequences

**Positive:**
- No resolver implementation needed
- UV's resolver is excellent
- UV's wheel download is fast
- UV's lock file is well-designed

**Negative:**
- Dependency on UV
- Limited control over resolution behavior
- UV version compatibility required

**Risks:**
- UV API changes (mitigated by version pinning)
- UV availability (mitigated by fallback to pip)

---

## ADR-005: Runtime Fingerprinting

**Status:** ACCEPTED
**Date:** 2026-06-04

### Context

GVX needs a way to identify equivalent runtimes across projects for reuse. Options include fingerprinting, manifest comparison, and hash comparison.

### Decision

Compute a deterministic SHA-256 fingerprint from the runtime inputs: Python version, dependency graph, wheel hashes, ABI, platform, architecture. Fingerprints enable runtime reuse and caching.

### Consequences

**Positive:**
- Enables runtime reuse
- Enables cache hits
- Enables verification
- Enables analytics

**Negative:**
- Fingerprint computation adds latency
- Fingerprint cache management required

**Risks:**
- Fingerprint collisions (mitigated by SHA-256)
- Fingerprint invalidation complexity (mitigated by deterministic algorithm)

---

## ADR-006: TOML for Lockfile Format

**Status:** ACCEPTED
**Date:** 2026-06-04

### Context

GVX needs a lockfile format that extends UV's lock file with runtime fingerprints and additional metadata. Options include TOML, JSON, and YAML.

### Decision

Use TOML for `gvx.lock`. TOML is human-readable, widely supported, and consistent with `pyproject.toml`.

### Consequences

**Positive:**
- Human-readable
- Consistent with pyproject.toml
- Widely supported in Python ecosystem
- Easy to parse and generate

**Negative:**
- Less compact than JSON
- Less expressive than YAML

**Risks:**
- TOML parsing errors (mitigated by validation)
- Format evolution (mitigated by version field)

---

## ADR-007: Python for Implementation Language

**Status:** ACCEPTED
**Date:** 2026-06-04

### Context

GVX needs an implementation language. Options include Python, Rust, and Go.

### Decision

Use Python for the initial implementation. Python provides native access to the Python import system, wheel format, and packaging ecosystem.

### Consequences

**Positive:**
- Native Python ecosystem access
- Easy to contribute for Python developers
- Direct access to import system internals
- Fast development iteration

**Negative:**
- Slower than Rust/Go
- Larger memory footprint
- Distribution complexity

**Risks:**
- Performance bottlenecks (mitigated by profiling and optimization)
- Distribution size (mitigated by wheel distribution)

**Future:**
- Performance-critical paths may be rewritten in Rust
- FFI bindings for hot paths

---

## ADR-008: Hybrid Import Path Construction

**Status:** ACCEPTED
**Date:** 2026-06-04

### Context

GVX needs to construct import paths that work with all tools and environments. No single method works universally.

### Decision

Use a hybrid approach: symlinks as primary, `.pth` files as fallback, `PYTHONPATH` injection via `gvx run` wrapper for guaranteed correctness.

### Consequences

**Positive:**
- Maximum compatibility
- Graceful degradation
- Guaranteed correctness via wrapper

**Negative:**
- More complex implementation
- Three code paths to maintain

**Risks:**
- Method selection logic complexity (mitigated by clear priority)
- Edge cases in fallback (mitigated by comprehensive testing)

---

## ADR-009: Strict Dependency Isolation

**Status:** ACCEPTED
**Date:** 2026-06-04

### Context

GVX needs to decide whether projects can see dependencies they didn't declare. Options include strict isolation (like pnpm) and permissive access (like pip).

### Decision

Enforce strict dependency isolation. Projects see only their declared dependencies and their transitive dependencies. No access to undeclared packages.

### Consequences

**Positive:**
- Prevents dependency leakage
- Catches missing dependencies early
- Matches production behavior
- Improves reliability

**Negative:**
- May break projects that rely on implicit dependencies
- Requires import analysis to detect issues

**Risks:**
- Breaking existing projects (mitigated by `gvx scan` to detect issues)
- Developer friction (mitigated by clear error messages)

---

## ADR-010: Immutable Store Objects

**Status:** ACCEPTED
**Date:** 2026-06-04

### Context

GVX needs to decide whether store objects can be modified after creation. Options include mutable objects (update in place) and immutable objects (replace entirely).

### Decision

Store objects are immutable. Once created, they are never modified. Updates create new objects with new hashes.

### Consequences

**Positive:**
- Eliminates race conditions
- Enables caching
- Enables verification
- Simplifies concurrency

**Negative:**
- More disk usage during updates
- Garbage collection required

**Risks:**
- Disk space growth (mitigated by garbage collection)
- Orphaned objects (mitigated by reference counting)
