# Milestones

**Date:** 2026-06-04
**Status:** APPROVED

---

## M0: Project Foundation

**Target:** Week 4
**Status:** NOT STARTED

### Deliverables
- [ ] Repository structure
- [ ] pyproject.toml with build system
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Linting (ruff)
- [ ] Type checking (mypy)
- [ ] Test framework (pytest)
- [ ] Benchmark framework
- [ ] skill.md, agent.md, gitagent.md
- [ ] Vision.md, Architecture.md
- [ ] FeasibilityReport.md, CompetitiveAnalysis.md

### Acceptance Criteria
- `uv run pytest` passes
- `uv run ruff check .` passes
- `uv run mypy .` passes
- CI pipeline green

---

## M1: Core Store Layer

**Target:** Week 8
**Status:** NOT STARTED

### Deliverables
- [ ] Content-addressable store implementation
- [ ] Package identity model (7-tuple)
- [ ] Wheel extraction
- [ ] Object metadata
- [ ] SQLite index (metadata.db)
- [ ] Store CLI (`gvx store info`, `gvx store list`)
- [ ] Store tests (>90% coverage)
- [ ] Store benchmarks

### Acceptance Criteria
- Store accepts and retrieves objects
- Objects are immutable
- Hash verification works
- All tests pass
- Benchmarks establish baseline

---

## M2: Runtime Construction

**Target:** Week 12
**Status:** NOT STARTED

### Deliverables
- [ ] Runtime manifest generation
- [ ] Symlink construction
- [ ] Entry point script generation
- [ ] Fingerprint algorithm
- [ ] Fingerprint cache
- [ ] `gvx sync` command
- [ ] `gvx run` command
- [ ] Runtime verification
- [ ] Runtime tests (>90% coverage)

### Acceptance Criteria
- `gvx sync` creates working runtime
- `gvx run python -c "import numpy"` works
- Fingerprint reuse demonstrated
- All tests pass

---

## M3: UV Integration

**Target:** Week 16
**Status:** NOT STARTED

### Deliverables
- [ ] UV integration layer
- [ ] Lockfile parser
- [ ] `gvx.lock` format
- [ ] Wheel download delegation
- [ ] Resolution caching
- [ ] `gvx add` / `gvx remove`
- [ ] Native extension validation
- [ ] Integration tests (>90% coverage)

### Acceptance Criteria
- `gvx add numpy` works end-to-end
- Lockfile round-trips correctly
- Native extensions validated
- All tests pass

---

## M4: Dependency Intelligence

**Target:** Week 20
**Status:** NOT STARTED

### Deliverables
- [ ] Import statement parser
- [ ] Import graph builder
- [ ] Unused dependency detection
- [ ] Missing dependency detection
- [ ] `gvx doctor`
- [ ] `gvx scan`
- [ ] `gvx stats`
- [ ] Report generation
- [ ] Intelligence tests (>90% coverage)

### Acceptance Criteria
- `gvx scan` correctly identifies unused deps
- `gvx doctor` diagnoses common issues
- `gvx stats` shows analytics
- All tests pass

---

## M5: Workspace Mode

**Target:** Week 24
**Status:** NOT STARTED

### Deliverables
- [ ] Workspace discovery
- [ ] Workspace manifest
- [ ] `gvx workspace sync`
- [ ] `gvx workspace doctor`
- [ ] `gvx workspace graph`
- [ ] `gvx workspace stats`
- [ ] Cross-project analysis
- [ ] Workspace tests (>90% coverage)

### Acceptance Criteria
- Workspace sync works
- Workspace graph shows relationships
- Workspace stats show analytics
- All tests pass

---

## M6: Security Layer

**Target:** Week 28
**Status:** NOT STARTED

### Deliverables
- [ ] Hash verification (all layers)
- [ ] Runtime integrity validation
- [ ] Lockfile verification
- [ ] Supply chain validation
- [ ] Offline mode
- [ ] Private registry support
- [ ] Credential management
- [ ] `gvx verify`
- [ ] Security tests (>90% coverage)

### Acceptance Criteria
- All objects verified on read
- Offline mode works
- Private registries supported
- `gvx verify` passes
- All tests pass

---

## M7: Beta Release (v0.1.0)

**Target:** Week 32
**Status:** NOT STARTED

### Deliverables
- [ ] Beta release
- [ ] User documentation
- [ ] Examples
- [ ] Migration guide
- [ ] Bug fixes
- [ ] Performance tuning
- [ ] Community feedback

### Acceptance Criteria
- 100+ beta users
- All critical bugs fixed
- Positive feedback
- Stable on Linux, macOS

---

## M8: GA Release (v1.0.0)

**Target:** Week 40
**Status:** NOT STARTED

### Deliverables
- [ ] GA release
- [ ] Windows support
- [ ] Full test coverage (>95%)
- [ ] Security audit
- [ ] Performance audit
- [ ] Complete documentation
- [ ] Production readiness

### Acceptance Criteria
- 1,000+ GitHub stars
- 50+ organizations using
- All tests pass
- Security audit passed
- Performance targets met
