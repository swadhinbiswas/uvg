# Release Plan

**Date:** 2026-06-04
**Status:** APPROVED

---

## Versioning Strategy

GVX follows [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH
```

- **MAJOR**: Breaking changes to public API or store format
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

---

## Release Cadence

| Phase | Cadence | Duration |
|-------|---------|----------|
| Pre-alpha | Weekly | Months 1-6 |
| Alpha | Bi-weekly | Months 7-12 |
| Beta | Monthly | Months 13-18 |
| GA | Quarterly | After Month 18 |

---

## Release Channels

| Channel | Purpose | Stability |
|---------|---------|-----------|
| `main` | Development | Unstable |
| `alpha` | Early testing | Low |
| `beta` | Pre-release testing | Medium |
| `stable` | Production | High |
| `lts` | Long-term support | Highest |

---

## Release Process

### 1. Pre-Release Checklist

- [ ] All tests pass
- [ ] All benchmarks meet targets
- [ ] Documentation updated
- [ ] Changelog generated
- [ ] Migration guide written (if breaking)
- [ ] Security review completed
- [ ] Performance review completed
- [ ] Code review completed
- [ ] No critical/open bugs

### 2. Release Branch

```bash
git checkout -b release/v0.1.0
```

### 3. Version Bump

```bash
# Update version in pyproject.toml
# Update version in __init__.py
# Update version in documentation
```

### 4. Changelog Generation

```bash
gvx changelog generate --from v0.0.1 --to v0.1.0 > CHANGELOG.md
```

### 5. Release Tag

```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

### 6. Build and Publish

```bash
uv build
uv publish
```

### 7. GitHub Release

```bash
gh release create v0.1.0 \
  --title "GVX v0.1.0" \
  --notes-file CHANGELOG.md \
  --draft
```

### 8. Post-Release

- [ ] Monitor issues
- [ ] Monitor performance
- [ ] Collect feedback
- [ ] Plan next release

---

## Changelog Format

```markdown
# Changelog

## [v0.1.0] - 2026-09-04

### Added
- Content-addressable store
- Runtime construction
- `gvx sync` command
- `gvx run` command
- Fingerprint caching

### Changed
- None

### Deprecated
- None

### Removed
- None

### Fixed
- None

### Security
- Hash verification on all store objects
```

---

## Breaking Change Policy

### Store Format Changes

If the store format changes:

1. **Minor change**: Automatic migration on next access
2. **Major change**: New store version, migration tool provided
3. **Incompatible change**: New store path, dual-store support during transition

### API Changes

If the public API changes:

1. **Deprecation**: Old API marked deprecated, warning issued
2. **Transition**: Both APIs supported for one minor version
3. **Removal**: Old API removed in next major version

### CLI Changes

If the CLI changes:

1. **Deprecation**: Old command marked deprecated, warning issued
2. **Transition**: Both commands supported for one minor version
3. **Removal**: Old command removed in next major version

---

## LTS Policy

### LTS Releases

LTS releases are supported for 24 months after GA.

| Release | LTS Start | LTS End |
|---------|-----------|---------|
| v1.0.0 | 2027-06-04 | 2029-06-04 |
| v2.0.0 | 2028-06-04 | 2030-06-04 |

### LTS Guarantees

- Security fixes
- Critical bug fixes
- No breaking changes
- No new features

---

## Release Artifacts

### PyPI

- Source distribution (sdist)
- Wheel distribution (bdist_wheel)

### GitHub Releases

- Source tarball
- Release notes
- Changelog
- Migration guide (if applicable)

### Documentation

- User guide
- API reference
- Migration guide
- Examples

---

## Rollback Plan

### If Release Has Critical Bug

1. **Yank release from PyPI**:
   ```bash
   uv publish --yank v0.1.0
   ```

2. **Mark GitHub release as pre-release**:
   ```bash
   gh release edit v0.1.0 --prerelease
   ```

3. **Issue advisory**:
   - GitHub Security Advisory
   - PyPI advisory
   - Community notification

4. **Release patch version**:
   - Fix bug
   - Release v0.1.1
   - Unyank v0.1.0 (if appropriate)

---

## Release Communication

### Channels

| Channel | Purpose |
|---------|---------|
| GitHub Releases | Official release notes |
| CHANGELOG.md | Detailed changelog |
| Discord/Slack | Community notification |
| Twitter/X | Announcement |
| Blog post | Detailed release notes |
| Newsletter | Monthly release summary |

### Announcement Template

```
GVX v{version} is now available!

What's new:
- {feature 1}
- {feature 2}
- {feature 3}

Install: pip install gvx=={version}
Docs: https://gvx.opencodehub.space/docs
Changelog: https://github.com/gvx/gvx/releases/tag/v{version}
```

---

## Release Metrics

### Track Per Release

| Metric | Target |
|--------|--------|
| Download count (24h) | 1,000+ |
| Download count (7d) | 10,000+ |
| GitHub stars (30d) | 100+ |
| Issues opened (7d) | <20 |
| Issues resolved (7d) | >15 |
| PRs merged (7d) | >5 |
| Community feedback | Positive |

---

## Release Calendar

| Version | Target Date | Status |
|---------|-------------|--------|
| v0.0.1 | 2026-06-04 | NOT STARTED |
| v0.0.2 | 2026-06-11 | NOT STARTED |
| v0.0.3 | 2026-06-18 | NOT STARTED |
| v0.0.4 | 2026-06-25 | NOT STARTED |
| v0.0.5 | 2026-07-02 | NOT STARTED |
| v0.0.6 | 2026-07-09 | NOT STARTED |
| v0.0.7 | 2026-07-16 | NOT STARTED |
| v0.0.8 | 2026-07-23 | NOT STARTED |
| v0.1.0-alpha.1 | 2026-09-04 | NOT STARTED |
| v0.1.0-beta.1 | 2027-03-04 | NOT STARTED |
| v1.0.0 | 2027-06-04 | NOT STARTED |
