# Roadmap

**Date:** 2026-06-04
**Status:** APPROVED

---

## Phase 0: Foundation (Months 1-2)

### Goals
- Project structure and tooling
- Core store layer
- Basic CLI
- Test infrastructure

### Deliverables
- [ ] Project initialization (pyproject.toml, CI, linting, typing)
- [ ] Content-addressable store implementation
- [ ] Package identity model (7-tuple)
- [ ] Wheel extraction and storage
- [ ] SQLite index (metadata.db)
- [ ] Basic CLI (`gvx init`, `gvx store info`)
- [ ] Test framework (pytest, coverage)
- [ ] Benchmark framework

### Success Criteria
- Store can accept and retrieve package objects
- CLI shows store status
- All tests pass
- Benchmarks establish baseline

---

## Phase 1: Runtime Construction (Months 3-4)

### Goals
- Runtime directory creation
- Symlink-based import paths
- Entry point script generation
- Fingerprint computation

### Deliverables
- [ ] Runtime manifest generation
- [ ] Symlink construction
- [ ] Entry point script generation
- [ ] Fingerprint algorithm
- [ ] Fingerprint cache
- [ ] `gvx sync` command
- [ ] `gvx run` command
- [ ] Runtime verification

### Success Criteria
- `gvx sync` creates working runtime
- `gvx run python -c "import numpy"` works
- Fingerprint reuse demonstrated
- All tests pass

---

## Phase 2: UV Integration (Months 5-6)

### Goals
- UV delegation for resolution
- Lockfile parsing
- Wheel download via UV
- `gvx.lock` format

### Deliverables
- [ ] UV integration layer
- [ ] Lockfile parser (uv.lock + gvx.lock)
- [ ] `gvx.lock` format specification
- [ ] Wheel download delegation
- [ ] Resolution caching
- [ ] `gvx add` / `gvx remove` commands
- [ ] Native extension validation

### Success Criteria
- `gvx add numpy` resolves via UV and stores in GVX
- Lockfile round-trips correctly
- Native extensions validated before storage
- All tests pass

---

## Phase 3: Dependency Intelligence (Months 7-8)

### Goals
- Import analysis
- Unused dependency detection
- Missing dependency detection
- Doctor command

### Deliverables
- [ ] Import statement parser
- [ ] Import graph builder
- [ ] Unused dependency detection
- [ ] Missing dependency detection
- [ ] `gvx doctor` command
- [ ] `gvx scan` command
- [ ] `gvx stats` command
- [ ] Report generation

### Success Criteria
- `gvx scan` correctly identifies unused deps
- `gvx doctor` diagnoses common issues
- `gvx stats` shows storage analytics
- All tests pass

---

## Phase 4: Workspace Mode (Months 9-10)

### Goals
- Monorepo support
- Workspace synchronization
- Workspace analytics
- Dependency graph visualization

### Deliverables
- [ ] Workspace discovery
- [ ] Workspace manifest format
- [ ] `gvx workspace sync`
- [ ] `gvx workspace doctor`
- [ ] `gvx workspace graph`
- [ ] `gvx workspace stats`
- [ ] Cross-project dependency analysis
- [ ] Workspace visualization

### Success Criteria
- Workspace sync creates runtimes for all projects
- Workspace graph shows dependency relationships
- Workspace stats show cross-project analytics
- All tests pass

---

## Phase 5: Security & Enterprise (Months 11-12)

### Goals
- Hash verification
- Supply chain validation
- Offline mode
- Private registry support

### Deliverables
- [ ] Hash verification (all layers)
- [ ] Runtime integrity validation
- [ ] Lockfile verification
- [ ] Supply chain validation
- [ ] Offline mode
- [ ] Private registry support
- [ ] Enterprise registry adapters
- [ ] Credential management
- [ ] `gvx verify` command

### Success Criteria
- All objects verified on read
- Offline mode works in air-gapped environments
- Private registries supported
- `gvx verify` passes all checks
- All tests pass

---

## Phase 6: Performance & Polish (Months 13-14)

### Goals
- Performance optimization
- Benchmark suite
- Documentation
- Examples

### Deliverables
- [ ] Performance optimization (cold/warm runtime)
- [ ] Benchmark suite
- [ ] Performance reports
- [ ] User documentation
- [ ] API documentation
- [ ] Examples and tutorials
- [ ] Migration guides
- [ ] IDE integration guides

### Success Criteria
- Cold runtime <2s
- Warm runtime <200ms
- Storage duplication <5%
- Documentation complete
- All tests pass

---

## Phase 7: Beta Release (Month 15)

### Goals
- Beta release
- Community feedback
- Bug fixes
- Stability improvements

### Deliverables
- [ ] Beta release (v0.1.0)
- [ ] Community feedback collection
- [ ] Bug fixes
- [ ] Stability improvements
- [ ] Performance tuning
- [ ] Documentation updates

### Success Criteria
- 100+ beta users
- All critical bugs fixed
- Positive feedback
- Stable on Linux, macOS

---

## Phase 8: GA Release (Month 18)

### Goals
- General availability
- Windows support
- Full test coverage
- Production readiness

### Deliverables
- [ ] GA release (v1.0.0)
- [ ] Windows support
- [ ] Full test coverage (>95%)
- [ ] Production readiness review
- [ ] Security audit
- [ ] Performance audit
- [ ] Complete documentation

### Success Criteria
- 1,000+ GitHub stars
- 50+ organizations using
- All tests pass
- Security audit passed
- Performance targets met
