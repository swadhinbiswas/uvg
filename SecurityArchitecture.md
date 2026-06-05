# Security Architecture

**Date:** 2026-06-04
**Status:** APPROVED

---

## Overview

Security is a core feature of GVX, not an afterthought. Every layer of the system includes security controls: hash verification, integrity validation, supply chain checks, offline mode, and enterprise registry support.

---

## Threat Model

### Threats Addressed

| Threat | Impact | Mitigation |
|--------|--------|------------|
| Package tampering | Malicious code execution | Hash verification at every layer |
| Supply chain attack | Compromised dependencies | Supply chain validation, hash pinning |
| Dependency confusion | Wrong package installed | Strict registry configuration |
| Cache poisoning | Corrupted store objects | Hash verification on read |
| Man-in-the-middle | Intercepted downloads | HTTPS-only, certificate pinning |
| Privilege escalation | Unauthorized access | File permissions, sandboxing |
| Denial of service | Store corruption | Atomic operations, backups |
| Information leakage | Sensitive data exposure | Registry credential isolation |

---

## Hash Verification

### Wheel Hash Verification

Every wheel is verified against its hash before extraction:

```python
def verify_wheel_hash(wheel_path: Path, expected_hash: str) -> bool:
    actual_hash = compute_sha256(wheel_path)
    return actual_hash == expected_hash.removeprefix("sha256:")

def compute_sha256(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
```

### Store Object Verification

Every store object is verified on read:

```python
def verify_store_object(object_path: Path) -> VerificationResult:
    metadata = load_metadata(object_path)

    # Verify metadata hash
    if metadata.wheel_hash != compute_object_hash(object_path):
        return VerificationResult.FAIL("Object hash mismatch")

    # Verify file integrity
    for file in object_path.rglob("*"):
        if file.is_file():
            if not verify_file_integrity(file):
                return VerificationResult.FAIL(f"File integrity failure: {file}")

    return VerificationResult.PASS
```

### Runtime Verification

Every runtime is verified before use:

```python
def verify_runtime(runtime_dir: Path) -> VerificationReport:
    manifest = load_manifest(runtime_dir)
    report = VerificationReport()

    # Verify manifest hash
    if not verify_manifest_hash(manifest):
        report.add_critical("Manifest hash mismatch - possible tampering")

    # Verify all store objects
    for pkg in manifest.packages.values():
        result = verify_store_object(Path(pkg.store_path))
        if not result.is_pass:
            report.add_critical(f"Store object verification failed: {pkg.name}")

    # Verify symlinks
    for symlink in runtime_dir.glob("site-packages/*"):
        if symlink.is_symlink():
            target = symlink.resolve()
            if not target.exists():
                report.add_error(f"Broken symlink: {symlink.name}")

    return report
```

---

## Runtime Integrity Validation

### Pre-Execution Verification

```python
def verify_before_execution(runtime_dir: Path) -> SecurityCheck:
    checks = []

    # Check 1: Manifest integrity
    manifest = load_manifest(runtime_dir)
    checks.append(SecurityCheck(
        name="manifest_integrity",
        passed=verify_manifest_hash(manifest),
        message="Manifest hash verified" if verify_manifest_hash(manifest) else "Manifest hash mismatch"
    ))

    # Check 2: Store object integrity
    all_verified = True
    for pkg in manifest.packages.values():
        if not verify_store_object(Path(pkg.store_path)):
            all_verified = False
            break
    checks.append(SecurityCheck(
        name="store_integrity",
        passed=all_verified,
        message="All store objects verified" if all_verified else "Store object verification failed"
    ))

    # Check 3: Symlink integrity
    broken = list(runtime_dir.glob("site-packages/*"))
    broken = [s for s in broken if s.is_symlink() and not s.exists()]
    checks.append(SecurityCheck(
        name="symlink_integrity",
        passed=len(broken) == 0,
        message=f"{len(broken)} broken symlinks found" if broken else "All symlinks valid"
    ))

    # Check 4: No unauthorized packages
    expected = set(manifest.packages.keys())
    actual = set(s.name for s in runtime_dir.glob("site-packages/*") if not s.name.startswith("_"))
    unauthorized = actual - expected
    checks.append(SecurityCheck(
        name="no_unauthorized_packages",
        passed=len(unauthorized) == 0,
        message=f"Unauthorized packages: {unauthorized}" if unauthorized else "No unauthorized packages"
    ))

    return SecurityCheck(run=checks)
```

---

## Lockfile Verification

### Lockfile Hash Pinning

```toml
[metadata]
version = 1
python_version = "3.12"
platform = "linux"
architecture = "x86_64"
fingerprint = "runtime_8fa2d1c3"
lockfile_hash = "sha256:d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5"

[[packages]]
name = "numpy"
version = "2.3.0"
hash = "sha256:a4f8d2e1b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0"
# ...
```

### Verification Process

```python
def verify_lockfile(lockfile_path: Path) -> VerificationResult:
    lockfile = parse_lockfile(lockfile_path)

    # Verify lockfile hash
    content = lockfile_path.read_text()
    content_hash = hashlib.sha256(content.encode()).hexdigest()

    if content_hash != lockfile.metadata.lockfile_hash.removeprefix("sha256:"):
        return VerificationResult.FAIL("Lockfile hash mismatch - file may have been modified")

    # Verify all package hashes are present
    for pkg in lockfile.packages:
        if not pkg.hash:
            return VerificationResult.FAIL(f"Missing hash for package: {pkg.name}")

    return VerificationResult.PASS
```

---

## Supply Chain Validation

### Package Provenance Tracking

```python
@dataclass
class PackageProvenance:
    package_name: str
    package_version: str
    source_registry: str
    download_url: str
    download_time: datetime
    verified_by: str
    hash: str
    signature: Optional[str] = None

def track_provenance(package: Package, registry: str) -> PackageProvenance:
    return PackageProvenance(
        package_name=package.name,
        package_version=package.version,
        source_registry=registry,
        download_url=package.download_url,
        download_time=datetime.now(timezone.utc),
        verified_by="gvx",
        hash=package.wheel_hash,
    )
```

### Dependency Chain Validation

```python
def validate_dependency_chain(manifest: RuntimeManifest) -> ValidationReport:
    report = ValidationReport()

    for pkg in manifest.packages.values():
        # Check if package comes from a trusted registry
        if not is_trusted_registry(pkg.source_registry):
            report.add_warning(f"Package from untrusted registry: {pkg.name}")

        # Check if package hash is pinned
        if not pkg.hash:
            report.add_error(f"Package hash not pinned: {pkg.name}")

        # Check for known vulnerabilities
        vulns = check_vulnerabilities(pkg.name, pkg.version)
        if vulns:
            report.add_error(f"Known vulnerabilities in {pkg.name}=={pkg.version}: {vulns}")

    return report
```

---

## Offline Mode

### Configuration

```toml
[security]
offline_mode = true
allowed_registries = ["https://registry.company.com/simple"]
cached_packages_only = true
```

### Offline Operation

```python
def resolve_offline(lockfile: Lockfile) -> ResolutionResult:
    """Resolve dependencies using only cached packages."""
    result = ResolutionResult()

    for pkg in lockfile.packages:
        # Check if package exists in store
        object_path = store.find_object(pkg.wheel_hash)
        if object_path is None:
            raise OfflineResolutionError(
                f"Package not in store: {pkg.name}=={pkg.version}. "
                "Run in online mode first to download packages."
            )
        result.add_package(pkg, object_path)

    return result
```

### Air-Gapped Deployment

```
1. On internet-connected machine:
   gvx sync --download-only
   gvx export --format bundle > packages.tar.gz

2. Transfer packages.tar.gz to air-gapped machine

3. On air-gapped machine:
   gvx import packages.tar.gz
   gvx sync --offline
```

---

## Private Registries

### Configuration

```toml
[registries]
default = "https://pypi.org/simple"
private = [
    "https://registry.company.com/simple"
]

[registries.auth]
"https://registry.company.com/simple" = { type = "basic", username = "${COMPANY_REGISTRY_USER}", password = "${COMPANY_REGISTRY_PASS}" }

[registries.tls]
"https://registry.company.com/simple" = { ca_bundle = "/etc/ssl/company-ca.pem" }
```

### Registry Priority

```python
def resolve_registry(package_name: str) -> Registry:
    """Resolve package from registries in priority order."""
    for registry in config.private_registries:
        if registry.has_package(package_name):
            return registry
    return config.default_registry
```

---

## Enterprise Registry Support

### Supported Registry Protocols

| Protocol | Support | Notes |
|----------|---------|-------|
| PyPI Simple API | Full | Standard |
| PEP 503 | Full | Standard |
| Artifactory | Full | JFrog |
| Nexus | Full | Sonatype |
| DevPi | Full | DevPi server |
| Cloud Registry | Full | AWS CodeArtifact, GCP Artifact Registry |

### Authentication Methods

| Method | Support | Notes |
|--------|---------|-------|
| Basic Auth | Full | Username/password |
| Token Auth | Full | Bearer token |
| API Key | Full | API key header |
| Certificate Auth | Full | mTLS |
| Environment Variables | Full | Credential injection |
| Keyring | Full | System keyring |

---

## File Permissions

### Store Permissions

```
~/.gvx/store/
  objects/    drwx------  (700)  # Owner only
  index/      drwx------  (700)  # Owner only
  cache/      drwx------  (700)  # Owner only
  tmp/        drwx------  (700)  # Owner only
```

### Object Permissions

```
~/.gvx/store/objects/sha256/<hash>/
  dr-x------  (500)  # Read + execute only (immutable)
  files: -r--r----- (440)  # Read only
```

### Runtime Permissions

```
project/.gvx/runtime/
  drwx------  (700)  # Owner only
  site-packages/  drwx------  (700)  # Owner only
  symlinks: lrwxrwxrwx  (777)  # Symlinks are world-readable by design
```

---

## Credential Management

### Credential Storage

```python
class CredentialStore:
    """Secure credential storage using system keyring."""

    def __init__(self):
        self.keyring = keyring.get_keyring()

    def store(self, registry: str, username: str, password: str):
        self.keyring.set_password(f"gvx:{registry}", username, password)

    def retrieve(self, registry: str, username: str) -> Optional[str]:
        return self.keyring.get_password(f"gvx:{registry}", username)

    def delete(self, registry: str, username: str):
        self.keyring.delete_password(f"gvx:{registry}", username)
```

### Environment Variable Injection

```python
def get_registry_credentials(registry: str) -> Credentials:
    """Get credentials from environment variables or keyring."""
    # Check environment variables first
    username = os.environ.get(f"GVX_REGISTRY_{registry.upper()}_USER")
    password = os.environ.get(f"GVX_REGISTRY_{registry.upper()}_PASS")

    if username and password:
        return Credentials(username, password)

    # Fall back to keyring
    cred_store = CredentialStore()
    password = cred_store.retrieve(registry, username)
    if password:
        return Credentials(username, password)

    raise CredentialNotFoundError(f"No credentials found for registry: {registry}")
```

---

## Security Commands

### `gvx verify`

```
Verifying runtime integrity...

  Manifest integrity:    PASS
  Store object integrity: PASS
  Symlink integrity:     PASS
  No unauthorized packages: PASS
  Hash verification:     PASS

All checks passed. Runtime is secure.
```

### `gvx scan --security`

```
Scanning for security issues...

  CRITICAL: requests==2.31.0 has known vulnerability CVE-2023-32681
  WARNING: Package from untrusted registry: internal-pkg==1.0.0
  INFO: All package hashes verified

Found 1 critical, 1 warning, 1 info
```

### `gvx doctor --security`

```
Security diagnostics:

  Store integrity:       PASS (1,234 objects verified)
  Lockfile integrity:    PASS (hash verified)
  Registry config:       PASS (HTTPS only)
  Credential storage:    PASS (keyring)
  File permissions:      PASS (700/440)
  Offline mode:          DISABLED
  Supply chain validation: ENABLED
```

---

## Security Architecture Invariants

1. **Hash verification is mandatory**: Every object is verified on read
2. **HTTPS is required**: No HTTP registry connections
3. **Credentials are isolated**: System keyring, not plaintext
4. **Permissions are restrictive**: Owner-only access to store
5. **Offline mode is supported**: Air-gapped environments
6. **Supply chain is tracked**: Provenance for every package
7. **Integrity is verified**: Before every execution
