# GVX Git Workflow

---

## Commit Message Format

GVX follows [Conventional Commits](https://www.conventionalcommits.org/).

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation change |
| `style` | Code style change (formatting, no logic change) |
| `refactor` | Code refactoring (no feature change, no bug fix) |
| `perf` | Performance improvement |
| `test` | Test addition or modification |
| `build` | Build system change |
| `ci` | CI/CD change |
| `chore` | Maintenance task |
| `revert` | Revert a previous commit |

### Scopes

| Scope | Description |
|-------|-------------|
| `store` | Store layer |
| `runtime` | Runtime layer |
| `cli` | CLI commands |
| `index` | Database/index layer |
| `security` | Security features |
| `intelligence` | Dependency intelligence |
| `workspace` | Workspace mode |
| `config` | Configuration |
| `docs` | Documentation |
| `ci` | CI/CD |
| `build` | Build system |
| `release` | Release process |

### Examples

```
feat(store): add content-addressable object storage

Implement the core store layer with SHA-256 content addressing.
Objects are stored by hash and are immutable after creation.

Closes #123
```

```
fix(runtime): resolve broken symlink on package update

When a package is updated, the old symlink was not being
removed before creating the new one, causing a race condition.

Fixes #456
```

```
perf(runtime): cache fingerprint lookups in memory

Reduces warm runtime construction from 200ms to 50ms by
caching fingerprint lookups in an LRU cache.

Benchmark: runtime_construction warm 200ms -> 50ms (75% improvement)
```

```
docs(architecture): add runtime architecture document

Document the runtime construction pipeline, fingerprint
algorithm, and symlink management.
```

---

## Commit Rules

### Atomic Commits

Each commit must be atomic:
- One logical change per commit
- Commits must be independently testable
- Commits must not break the build

**GOOD:**
```
feat(store): add object creation
feat(store): add object retrieval
feat(store): add object deletion
```

**BAD:**
```
feat(store): add store layer with creation, retrieval, deletion, indexing, and CLI
```

### Commit Size

- Commits should be small enough to review in 15 minutes
- Large changes should be split into multiple commits
- Each commit should compile and pass tests

### No Mixed Changes

Do not mix different types of changes in one commit:

**BAD:**
```
feat(store): add object creation and fix typo in docs
```

**GOOD:**
```
feat(store): add object creation
docs(store): fix typo in store documentation
```

---

## Branch Strategy

### Branches

| Branch | Purpose | Protection |
|--------|---------|------------|
| `main` | Stable development | Require PR, require CI |
| `release/*` | Release preparation | Require PR, require CI |
| `feature/*` | Feature development | None |
| `fix/*` | Bug fix development | None |
| `docs/*` | Documentation development | None |
| `refactor/*` | Refactoring development | None |
| `perf/*` | Performance development | None |

### Branch Naming

```
feature/add-store-layer
fix/broken-symlink-on-update
docs/add-runtime-architecture
refactor/extract-store-index
perf/cache-fingerprint-lookups
```

### Branch Lifecycle

1. Create branch from `main`
2. Make commits
3. Keep branch updated with `main` (rebase)
4. Create PR when ready
5. Merge to `main`
6. Delete branch

---

## Pull Request Rules

### PR Title

Must follow conventional commit format:

```
feat(store): add content-addressable object storage
```

### PR Description

Must include:

```markdown
## Summary

Brief description of the change.

## Changes

- Change 1
- Change 2
- Change 3

## Testing

- Test 1
- Test 2

## Benchmarks

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| runtime_construction | 200ms | 50ms | -75% |

## Documentation

- [ ] Updated relevant documentation
- [ ] Added examples
- [ ] Updated API reference

## Breaking Changes

- None (or describe breaking changes)

## Related Issues

Closes #123
```

### PR Requirements

- [ ] All checks pass (tests, lint, type check)
- [ ] At least 1 approval
- [ ] No unresolved comments
- [ ] Branch is up to date with `main`
- [ ] Conventional commit format
- [ ] Atomic commits
- [ ] No merge commits (rebase only)

---

## Semantic Versioning

GVX follows [Semantic Versioning](https://semver.org/).

### Version Bump Rules

| Change | Bump |
|--------|------|
| Breaking API change | MAJOR |
| Breaking store format change | MAJOR |
| Breaking CLI change | MAJOR |
| New feature (backward compatible) | MINOR |
| New CLI command (backward compatible) | MINOR |
| Bug fix | PATCH |
| Performance improvement | PATCH |
| Documentation | PATCH |

### Version Format

```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
```

Examples:
- `0.1.0` - Pre-alpha
- `0.1.0-alpha.1` - Alpha release 1
- `0.1.0-beta.1` - Beta release 1
- `1.0.0` - GA release

---

## Changelog Generation

### Automatic Generation

Changelog is generated from conventional commits:

```bash
git log --oneline --no-merges v0.0.1..v0.1.0 | \
  grep "^feat" | sed 's/^feat/### Added/'
git log --oneline --no-merges v0.0.1..v0.1.0 | \
  grep "^fix" | sed 's/^fix/### Fixed/'
```

### Changelog Format

```markdown
# Changelog

## [v0.1.0] - 2026-09-04

### Added
- Content-addressable store (feat(store))
- Runtime construction (feat(runtime))
- `gvx sync` command (feat(cli))
- `gvx run` command (feat(cli))
- Fingerprint caching (feat(runtime))

### Fixed
- Broken symlink on package update (fix(runtime))
- Hash mismatch on corrupted objects (fix(store))

### Performance
- Cached fingerprint lookups (perf(runtime))
```

---

## Release Tagging

### Tag Format

```
vMAJOR.MINOR.PATCH
```

### Tag Creation

```bash
git tag -a v0.1.0 -m "Release v0.1.0

## Added
- Content-addressable store
- Runtime construction
- gvx sync command
- gvx run command
- Fingerprint caching

## Fixed
- Broken symlink on package update
- Hash mismatch on corrupted objects

## Performance
- Cached fingerprint lookups
"
git push origin v0.1.0
```

### Tag Requirements

- Tag must point to a commit on `main` or `release/*`
- Tag must have a message
- Tag must reference the changelog
- Tag must be signed (if GPG is configured)

---

## Pre-Commit Checks

### Mandatory Checks Before Commit

Every commit must pass:

1. **Tests**: `uv run pytest`
2. **Linting**: `uv run ruff check .`
3. **Formatting**: `uv run ruff format --check .`
4. **Type checking**: `uv run mypy .`
5. **Benchmark**: `uv run pytest tests/benchmarks/ --benchmark-only` (for performance changes)

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running pre-commit checks..."

echo "Running tests..."
uv run pytest -q
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi

echo "Running linting..."
uv run ruff check .
if [ $? -ne 0 ]; then
    echo "Linting failed. Commit aborted."
    exit 1
fi

echo "Running type checking..."
uv run mypy .
if [ $? -ne 0 ]; then
    echo "Type checking failed. Commit aborted."
    exit 1
fi

echo "All checks passed."
exit 0
```

---

## Merge Strategy

### Rebase Merge (Preferred)

```bash
git checkout main
git pull
git checkout feature/my-feature
git rebase main
git checkout main
git merge --ff-only feature/my-feature
```

### Squash Merge (For Large PRs)

```bash
git checkout main
git merge --squash feature/my-feature
git commit -m "feat(store): add content-addressable object storage"
```

### No Merge Commits

Merge commits are not allowed on `main`. Use rebase or squash.

---

## Git Configuration

### Recommended Settings

```bash
git config --global core.autocrlf input
git config --global core.eol lf
git config --global pull.rebase true
git config --global fetch.prune true
git config --global init.defaultBranch main
git config --global commit.gpgsign true
```

### .gitignore

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/

# GVX
.gvx/runtime/
.gvx/cache/
*.gvx-metadata.json

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/

# Build
*.egg-info/
dist/
build/
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          python-version: ${{ matrix.python-version }}
      - run: uv sync --dev
      - run: uv run pytest --cov=gvx --cov-report=xml
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy .

  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --dev
      - run: uv run pytest tests/benchmarks/ --benchmark-only
```

---

## Git Workflow Invariants

1. **Conventional commits**: All commits follow the format
2. **Atomic commits**: One logical change per commit
3. **Semantic versioning**: Versions follow semver
4. **Automatic changelog**: Generated from commits
5. **Release tagging**: Tags are annotated and signed
6. **Mandatory tests**: No commit without passing tests
7. **Mandatory lint**: No commit without passing lint
8. **Mandatory type checks**: No commit without passing mypy
9. **No merge commits**: Rebase or squash only
10. **Protected main**: Require PR and CI for main
