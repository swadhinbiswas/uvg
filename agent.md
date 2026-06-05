# GVX Agent Workflow

---

## Overview

This document defines the workflow for all agents working on GVX. No feature may skip any phase. Every phase has entry and exit criteria.

---

## Planning Workflow

### Phase 1: Problem Definition

**Input:** Feature request, bug report, or architecture need

**Steps:**
1. Define the problem clearly
2. Identify stakeholders
3. Define success criteria
4. Identify constraints
5. Identify risks

**Output:** Problem statement document

**Exit Criteria:**
- Problem is clearly defined
- Success criteria are measurable
- Constraints are documented
- Risks are identified

### Phase 2: Research

**Input:** Problem statement

**Steps:**
1. Research existing solutions
2. Research competitor approaches
3. Research technical feasibility
4. Identify tradeoffs
5. Document findings

**Output:** Research document

**Exit Criteria:**
- Existing solutions analyzed
- Tradeoffs documented
- Feasibility confirmed

---

## Design Workflow

### Phase 3: Architecture Design

**Input:** Research document

**Steps:**
1. Design the solution architecture
2. Define interfaces and boundaries
3. Define data models
4. Define error handling
5. Define security considerations
6. Define performance considerations
7. Create diagrams
8. Write ADR

**Output:** Architecture design document + ADR

**Exit Criteria:**
- Architecture is documented
- Interfaces are defined
- Data models are defined
- ADR is written and approved
- Security review completed
- Performance review completed

### Phase 4: API Design

**Input:** Architecture design

**Steps:**
1. Define public APIs
2. Define CLI commands
3. Define configuration format
4. Define error types
5. Write API documentation

**Output:** API design document

**Exit Criteria:**
- All public APIs defined
- All CLI commands defined
- Configuration format defined
- Error types defined
- API documentation written

---

## Implementation Workflow

### Phase 5: Implementation

**Input:** Architecture design + API design

**Steps:**
1. Create feature branch
2. Implement code
3. Write tests
4. Write documentation
5. Write benchmarks
6. Run linting
7. Run type checking
8. Run tests
9. Run benchmarks

**Output:** Implementation with tests, docs, and benchmarks

**Exit Criteria:**
- All code implemented
- All tests pass
- All linting passes
- All type checking passes
- All benchmarks meet targets
- Documentation complete

### Phase 6: Self-Review

**Input:** Implementation

**Steps:**
1. Review own code against skill.md standards
2. Check for forbidden patterns
3. Check for required inclusions
4. Verify test coverage
5. Verify documentation completeness
6. Run full test suite
7. Run full benchmark suite

**Output:** Self-review checklist

**Exit Criteria:**
- All checklist items pass
- No forbidden patterns found
- All required inclusions present
- Test coverage meets targets
- Benchmark targets met

---

## Testing Workflow

### Phase 7: Testing

**Input:** Implementation + self-review

**Steps:**
1. Run unit tests
2. Run integration tests
3. Run performance tests
4. Run security tests
5. Run edge case tests
6. Run cross-platform tests
7. Run cross-Python-version tests

**Output:** Test report

**Exit Criteria:**
- All unit tests pass
- All integration tests pass
- All performance tests meet targets
- All security tests pass
- All edge cases handled
- Cross-platform compatibility verified
- Cross-Python-version compatibility verified

---

## Review Workflow

### Phase 8: Code Review

**Input:** Implementation + test report

**Steps:**
1. Create PR
2. Request review from committer
3. Address review comments
4. Update PR
5. Re-run checks
6. Get approval

**Output:** Approved PR

**Exit Criteria:**
- All checks pass
- At least 1 approval
- No unresolved comments
- Branch is up to date

### Phase 9: Merge

**Input:** Approved PR

**Steps:**
1. Squash and merge (or rebase merge)
2. Delete feature branch
3. Verify main branch CI
4. Update issue status

**Output:** Merged code

**Exit Criteria:**
- Code merged to main
- CI green on main
- Issue updated

---

## Release Workflow

### Phase 10: Release Preparation

**Input:** Merged features for release

**Steps:**
1. Create release branch
2. Bump version
3. Generate changelog
4. Update documentation
5. Run full test suite
6. Run full benchmark suite
7. Security review
8. Performance review

**Output:** Release candidate

**Exit Criteria:**
- Version bumped
- Changelog generated
- Documentation updated
- All tests pass
- All benchmarks meet targets
- Security review passed
- Performance review passed

### Phase 11: Release

**Input:** Release candidate

**Steps:**
1. Create release tag
2. Build distributions
3. Publish to PyPI
4. Create GitHub release
5. Announce to community
6. Monitor for issues

**Output:** Released version

**Exit Criteria:**
- Tag created
- Distributions published
- GitHub release created
- Community notified
- No critical issues within 24h

---

## Risk Assessment Workflow

### Trigger

- New feature proposal
- Architecture change
- Security concern
- Performance regression
- Breaking change

### Steps

1. Identify the risk
2. Assess likelihood (Low/Medium/High)
3. Assess impact (Low/Medium/High)
4. Define mitigation strategy
5. Define contingency plan
6. Document in risk register
7. Review with maintainers

### Output

Risk assessment document

### Exit Criteria

- Risk documented
- Mitigation defined
- Contingency defined
- Maintainers reviewed

---

## Architecture Review Workflow

### Trigger

- New architecture decision
- Architecture change
- ADR proposal

### Steps

1. Write ADR
2. Present to maintainers
3. Discuss tradeoffs
4. Discuss alternatives
5. Vote on decision
6. Document decision
7. Update architecture docs

### Output

Approved ADR

### Exit Criteria

- ADR written
- Tradeoffs discussed
- Alternatives considered
- Vote passed
- ADR merged
- Architecture docs updated

---

## Phase Gate Summary

| Phase | Input | Output | Gate |
|-------|-------|--------|------|
| 1. Problem Definition | Feature request | Problem statement | Problem is clear |
| 2. Research | Problem statement | Research doc | Feasibility confirmed |
| 3. Architecture Design | Research doc | Architecture + ADR | ADR approved |
| 4. API Design | Architecture | API doc | APIs defined |
| 5. Implementation | Design docs | Code + tests + docs | All checks pass |
| 6. Self-Review | Implementation | Self-review checklist | Checklist passed |
| 7. Testing | Implementation | Test report | All tests pass |
| 8. Code Review | Implementation + tests | Approved PR | PR approved |
| 9. Merge | Approved PR | Merged code | CI green |
| 10. Release Prep | Merged features | Release candidate | All reviews passed |
| 11. Release | Release candidate | Released version | No critical issues |

**No phase may be skipped. No phase may proceed without meeting exit criteria.**
