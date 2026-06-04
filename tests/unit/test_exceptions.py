"""Tests for exception hierarchy."""

from __future__ import annotations

from uvg.core.exceptions import (
    CLIError,
    ConfigurationError,
    CredentialNotFoundError,
    FingerprintMismatchError,
    HashMismatchError,
    IndexCorruptionError,
    ObjectExistsError,
    ObjectNotFoundError,
    OfflineResolutionError,
    RuntimeNotFoundError,
    RuntimeOperationError,
    SecurityError,
    StoreCorruptionError,
    StoreError,
    UVGError,
    VerificationFailedError,
)


class TestExceptionHierarchy:
    def test_uvg_error_base(self) -> None:
        err = UVGError("test")
        assert isinstance(err, Exception)

    def test_store_error_inheritance(self) -> None:
        err = StoreError("test")
        assert isinstance(err, UVGError)

    def test_object_not_found(self) -> None:
        err = ObjectNotFoundError("abc123")
        assert isinstance(err, StoreError)
        assert "abc123" in str(err)
        assert err.object_hash == "abc123"

    def test_object_exists(self) -> None:
        err = ObjectExistsError("abc123")
        assert isinstance(err, StoreError)
        assert "abc123" in str(err)
        assert err.object_hash == "abc123"

    def test_hash_mismatch(self) -> None:
        err = HashMismatchError(expected="sha256:abc", actual="sha256:def", context="test")
        assert isinstance(err, StoreError)
        assert "sha256:abc" in str(err)
        assert "sha256:def" in str(err)
        assert err.expected == "sha256:abc"
        assert err.actual == "sha256:def"

    def test_store_corruption(self) -> None:
        err = StoreCorruptionError("corrupt data")
        assert isinstance(err, StoreError)
        assert "corrupt data" in str(err)

    def test_runtime_error_inheritance(self) -> None:
        err = RuntimeOperationError("test")
        assert isinstance(err, UVGError)

    def test_runtime_not_found(self) -> None:
        err = RuntimeNotFoundError("/path/to/project")
        assert isinstance(err, RuntimeError)
        assert "/path/to/project" in str(err)
        assert err.project_path == "/path/to/project"

    def test_fingerprint_mismatch(self) -> None:
        err = FingerprintMismatchError(expected="fp1", actual="fp2")
        assert isinstance(err, RuntimeError)
        assert "fp1" in str(err)
        assert "fp2" in str(err)

    def test_index_corruption(self) -> None:
        err = IndexCorruptionError("corrupt index")
        assert isinstance(err, UVGError)
        assert "corrupt index" in str(err)

    def test_security_error_inheritance(self) -> None:
        err = SecurityError("test")
        assert isinstance(err, UVGError)

    def test_verification_failed(self) -> None:
        err = VerificationFailedError("verification failed")
        assert isinstance(err, SecurityError)
        assert "verification failed" in str(err)

    def test_offline_resolution(self) -> None:
        err = OfflineResolutionError("numpy", "2.3.0")
        assert isinstance(err, UVGError)
        assert "numpy" in str(err)
        assert "2.3.0" in str(err)
        assert err.package_name == "numpy"
        assert err.package_version == "2.3.0"

    def test_credential_not_found(self) -> None:
        err = CredentialNotFoundError("https://registry.example.com")
        assert isinstance(err, SecurityError)
        assert "https://registry.example.com" in str(err)
        assert err.registry == "https://registry.example.com"

    def test_cli_error(self) -> None:
        err = CLIError("cli error")
        assert isinstance(err, UVGError)

    def test_configuration_error(self) -> None:
        err = ConfigurationError("bad config")
        assert isinstance(err, UVGError)
        assert "bad config" in str(err)
