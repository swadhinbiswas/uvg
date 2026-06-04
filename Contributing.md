# Contributing to UVG

**Date:** 2026-06-04
**Status:** APPROVED

---

## Code of Conduct

UVG follows the [Contributor Covenant](https://www.contributor-covenant.org/).

Be respectful. Be inclusive. Be helpful.

---

## Getting Started

### 1. Fork and Clone

```bash
git clone https://github.com/your-username/uvg.git
cd uvg
```

### 2. Set Up Development Environment

```bash
uv sync --dev
```

### 3. Run Tests

```bash
uv run pytest
```

### 4. Run Linting

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
```

---

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming:
- `feature/...` for new features
- `fix/...` for bug fixes
- `docs/...` for documentation
- `refactor/...` for code refactoring
- `perf/...` for performance improvements
- `test/...` for test additions

### 2. Make Changes

Follow the engineering standards defined in `skill.md`:
- Type all code
- Test all code
- Document all code
- Benchmark performance-critical code

### 3. Run Checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy .
```

### 4. Commit

Follow the commit standards defined in `gitagent.md`:
- Conventional commits
- Atomic commits
- Descriptive messages

```bash
git commit -m "feat(store): add content-addressable object storage"
```

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Create a PR on GitHub with:
- Clear description
- Linked issues
- Test results
- Benchmark results (if applicable)

---

## Pull Request Requirements

### All PRs Must

- [ ] Pass all tests
- [ ] Pass linting
- [ ] Pass type checking
- [ ] Include tests for new code
- [ ] Include documentation for new features
- [ ] Follow conventional commits
- [ ] Have a clear description

### Feature PRs Must Also

- [ ] Include benchmark results
- [ ] Include usage examples
- [ ] Update relevant documentation
- [ ] Include migration guide (if breaking)

### Bug Fix PRs Must Also

- [ ] Include regression test
- [ ] Describe the bug being fixed
- [ ] Describe the root cause

---

## Testing Standards

### Unit Tests

- Test every public function
- Test edge cases
- Test error conditions
- Mock external dependencies

### Integration Tests

- Test end-to-end workflows
- Test with real UV
- Test with real packages
- Test native extensions

### Performance Tests

- Benchmark critical paths
- Compare against baseline
- Report regression

### Test Coverage

- Target: >95% line coverage
- Target: >90% branch coverage

---

## Code Style

### Formatting

- Use `ruff format` (Black-compatible)
- Line length: 120 characters
- UTF-8 encoding

### Typing

- Strict mode (`mypy --strict`)
- No `Any` without justification
- No `# type: ignore` without comment
- All public APIs typed

### Naming

- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_leading_underscore`

### Imports

- Standard library first
- Third-party second
- Local third
- Sorted within groups
- No wildcard imports

---

## Documentation Standards

### Code Documentation

- Docstrings for all public APIs
- Google style docstrings
- Type hints in signatures
- Examples in docstrings

### User Documentation

- Clear and concise
- Examples for every feature
- Error messages explained
- Troubleshooting guides

### Architecture Documentation

- ADRs for decisions
- Diagrams for complex flows
- Rationale for tradeoffs
- Alternatives considered

---

## Review Process

### Reviewer Checklist

- [ ] Code follows style guide
- [ ] Tests are comprehensive
- [ ] Documentation is complete
- [ ] Performance is acceptable
- [ ] Security is considered
- [ ] Error handling is robust

### Author Responsibilities

- Respond to review comments
- Make requested changes
- Update PR description
- Re-run checks

### Merge Requirements

- [ ] All checks pass
- [ ] At least 1 approval
- [ ] No unresolved comments
- [ ] Branch is up to date

---

## Reporting Issues

### Bug Reports

Include:
- UVG version
- Python version
- OS
- Steps to reproduce
- Expected behavior
- Actual behavior
- Logs/output

### Feature Requests

Include:
- Use case
- Proposed solution
- Alternatives considered
- Priority justification

### Security Reports

Report security issues privately:
- Email: security@uvg.dev
- Do not create public issues

---

## Community

### Channels

- GitHub Discussions
- Discord
- Twitter/X

### Events

- Monthly community call
- Quarterly release planning
- Annual contributor summit

---

## Recognition

### Contributors

All contributors are listed in `CONTRIBUTORS.md`.

### Hall of Fame

Top contributors are recognized in the README.

### Sponsorship

Organizations that sponsor UVG are listed in the README.
