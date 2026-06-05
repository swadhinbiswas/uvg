"""Tests for runtime fingerprinting."""

from __future__ import annotations

import pytest

from gvx.runtime.fingerprint import FingerprintInput, compute_fingerprint


class TestFingerprintInput:
    def test_create_sorted_packages(self) -> None:
        packages = {
            "requests": ("2.31.0", "sha256:ccc"),
            "numpy": ("2.3.0", "sha256:aaa"),
            "pandas": ("2.2.0", "sha256:bbb"),
        }
        fp_input = FingerprintInput.create(
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi="cp312",
            manifest_version=1,
            packages=packages,
        )
        names = [p[0] for p in fp_input.packages]
        assert names == ["numpy", "pandas", "requests"]

    def test_frozen(self) -> None:
        packages = {
            "numpy": ("2.3.0", "sha256:aaa"),
        }
        fp_input = FingerprintInput.create(
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi="cp312",
            manifest_version=1,
            packages=packages,
        )
        with pytest.raises(AttributeError):
            fp_input.python_version = "3.13"


class TestComputeFingerprint:
    def test_deterministic(self) -> None:
        packages = {
            "numpy": ("2.3.0", "sha256:aaa"),
            "pandas": ("2.2.0", "sha256:bbb"),
        }
        fp_input = FingerprintInput.create(
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi="cp312",
            manifest_version=1,
            packages=packages,
        )

        fp1 = compute_fingerprint(fp_input)
        fp2 = compute_fingerprint(fp_input)
        assert fp1 == fp2

    def test_format(self) -> None:
        packages = {
            "numpy": ("2.3.0", "sha256:aaa"),
        }
        fp_input = FingerprintInput.create(
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi="cp312",
            manifest_version=1,
            packages=packages,
        )

        fp = compute_fingerprint(fp_input)
        assert fp.startswith("runtime_")
        assert len(fp) == len("runtime_") + 8

    def test_different_inputs_different_fps(self) -> None:
        packages_a = {
            "numpy": ("2.3.0", "sha256:aaa"),
        }
        packages_b = {
            "numpy": ("2.3.1", "sha256:aaa"),
        }
        fp_input_a = FingerprintInput.create(
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi="cp312",
            manifest_version=1,
            packages=packages_a,
        )
        fp_input_b = FingerprintInput.create(
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi="cp312",
            manifest_version=1,
            packages=packages_b,
        )

        assert compute_fingerprint(fp_input_a) != compute_fingerprint(fp_input_b)

    def test_same_deps_different_order_same_fp(self) -> None:
        packages_a = {
            "numpy": ("2.3.0", "sha256:aaa"),
            "pandas": ("2.2.0", "sha256:bbb"),
        }
        packages_b = {
            "pandas": ("2.2.0", "sha256:bbb"),
            "numpy": ("2.3.0", "sha256:aaa"),
        }
        fp_input_a = FingerprintInput.create(
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi="cp312",
            manifest_version=1,
            packages=packages_a,
        )
        fp_input_b = FingerprintInput.create(
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi="cp312",
            manifest_version=1,
            packages=packages_b,
        )

        assert compute_fingerprint(fp_input_a) == compute_fingerprint(fp_input_b)

    def test_different_python_version_different_fp(self) -> None:
        packages = {
            "numpy": ("2.3.0", "sha256:aaa"),
        }
        fp_input_312 = FingerprintInput.create(
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi="cp312",
            manifest_version=1,
            packages=packages,
        )
        fp_input_313 = FingerprintInput.create(
            python_version="3.13",
            platform="linux",
            architecture="x86_64",
            abi="cp313",
            manifest_version=1,
            packages=packages,
        )

        assert compute_fingerprint(fp_input_312) != compute_fingerprint(fp_input_313)
