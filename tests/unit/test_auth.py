"""Tests for authentication and TLS configuration."""

from pathlib import Path

import pytest

from gvx.auth.config import (
    AuthConfig,
    AuthConfigParser,
    RegistryAuth,
    RegistryConfig,
    TLSCertificate,
    parse_auth_config,
)


class TestRegistryAuth:
    """Test RegistryAuth class."""

    def test_basic(self) -> None:
        auth = RegistryAuth(url="https://pypi.org/simple")
        assert auth.url == "https://pypi.org/simple"
        assert not auth.has_credentials

    def test_with_username_password(self) -> None:
        auth = RegistryAuth(
            url="https://pypi.org/simple",
            username="user",
            password="pass",
        )
        assert auth.has_credentials
        assert auth.username == "user"
        assert auth.password == "pass"

    def test_with_token(self) -> None:
        auth = RegistryAuth(
            url="https://pypi.org/simple",
            token="my-token",
        )
        assert auth.has_credentials
        assert auth.token == "my-token"

    def test_with_keyring(self) -> None:
        auth = RegistryAuth(
            url="https://pypi.org/simple",
            keyring_provider="secret",
        )
        assert auth.has_credentials
        assert auth.keyring_provider == "secret"

    def test_to_dict(self) -> None:
        auth = RegistryAuth(
            url="https://pypi.org/simple",
            username="user",
            token="secret",
        )
        result = auth.to_dict()
        assert result["url"] == "https://pypi.org/simple"
        assert result["username"] == "user"
        assert result["token"] == "***"


class TestTLSCertificate:
    """Test TLSCertificate class."""

    def test_ca_cert(self) -> None:
        cert = TLSCertificate(path="/etc/ssl/certs/ca.pem")
        assert cert.is_ca
        assert not cert.is_client_cert

    def test_client_cert(self) -> None:
        cert = TLSCertificate(path="/etc/ssl/certs/client.pem", type="client-cert")
        assert not cert.is_ca
        assert cert.is_client_cert


class TestRegistryConfig:
    """Test RegistryConfig class."""

    def test_basic(self) -> None:
        registry = RegistryConfig(name="pypi", url="https://pypi.org/simple")
        assert registry.name == "pypi"
        assert not registry.has_auth
        assert not registry.has_tls

    def test_default_registry(self) -> None:
        registry = RegistryConfig(
            name="pypi",
            url="https://pypi.org/simple",
            default=True,
        )
        assert registry.default

    def test_with_auth(self) -> None:
        auth = RegistryAuth(url="https://private.example.com/simple", username="user")
        registry = RegistryConfig(
            name="private",
            url="https://private.example.com/simple",
            auth=auth,
        )
        assert registry.has_auth
        assert not registry.has_tls

    def test_with_tls(self) -> None:
        cert = TLSCertificate(path="/etc/ssl/certs/ca.pem")
        registry = RegistryConfig(
            name="private",
            url="https://private.example.com/simple",
            tls_certificates=[cert],
        )
        assert not registry.has_auth
        assert registry.has_tls

    def test_to_dict(self) -> None:
        registry = RegistryConfig(
            name="pypi",
            url="https://pypi.org/simple",
            default=True,
        )
        result = registry.to_dict()
        assert result["name"] == "pypi"
        assert result["url"] == "https://pypi.org/simple"
        assert result["default"] is True


class TestAuthConfig:
    """Test AuthConfig class."""

    def test_basic(self) -> None:
        config = AuthConfig()
        assert not config.has_registries
        assert not config.has_tls_config

    def test_with_registries(self) -> None:
        registry = RegistryConfig(name="pypi", url="https://pypi.org/simple")
        config = AuthConfig(registries=[registry])
        assert config.has_registries
        assert not config.has_tls_config

    def test_with_tls(self) -> None:
        config = AuthConfig(
            tls_ca_certificates=["/etc/ssl/certs/ca.pem"],
            tls_client_cert="/etc/ssl/certs/client.pem",
            tls_client_key="/etc/ssl/private/client.key",
        )
        assert not config.has_registries
        assert config.has_tls_config

    def test_get_default_registry(self) -> None:
        default = RegistryConfig(name="pypi", url="https://pypi.org/simple", default=True)
        other = RegistryConfig(name="private", url="https://private.example.com/simple")
        config = AuthConfig(registries=[other, default])
        assert config.get_default_registry() == default

    def test_get_registry_by_name(self) -> None:
        registry = RegistryConfig(name="private", url="https://private.example.com/simple")
        config = AuthConfig(registries=[registry])
        assert config.get_registry_by_name("private") == registry
        assert config.get_registry_by_name("unknown") is None

    def test_get_registry_by_url(self) -> None:
        registry = RegistryConfig(name="private", url="https://private.example.com/simple")
        config = AuthConfig(registries=[registry])
        assert config.get_registry_by_url("https://private.example.com/simple") == registry
        assert config.get_registry_by_url("https://unknown.com") is None


class TestAuthConfigParser:
    """Test AuthConfigParser class."""

    def test_parse_empty(self) -> None:
        parser = AuthConfigParser()
        config = parser.parse("")
        assert not config.has_registries
        assert not config.has_tls_config

    def test_parse_tls_ca_certificates(self) -> None:
        content = """
[tool.uv]
tls-ca-certificates = ["/etc/ssl/certs/ca.pem", "/etc/ssl/certs/custom.pem"]
"""
        parser = AuthConfigParser()
        config = parser.parse(content)
        assert config.has_tls_config
        assert len(config.tls_ca_certificates) == 2
        assert "/etc/ssl/certs/ca.pem" in config.tls_ca_certificates

    def test_parse_tls_client_cert(self) -> None:
        content = """
[tool.uv]
tls-client-cert = "/etc/ssl/certs/client.pem"
tls-client-key = "/etc/ssl/private/client.key"
"""
        parser = AuthConfigParser()
        config = parser.parse(content)
        assert config.tls_client_cert == "/etc/ssl/certs/client.pem"
        assert config.tls_client_key == "/etc/ssl/private/client.key"

    def test_parse_tls_no_verify(self) -> None:
        content = """
[tool.uv]
tls-no-verify = true
"""
        parser = AuthConfigParser()
        config = parser.parse(content)
        assert config.tls_no_verify is True

    def test_parse_keyring_provider(self) -> None:
        content = """
[tool.uv]
keyring-provider = "secret"
"""
        parser = AuthConfigParser()
        config = parser.parse(content)
        assert config.keyring_provider == "secret"

    def test_parse_registry(self) -> None:
        content = """
[[tool.uv.index]]
name = "private"
url = "https://private.example.com/simple"
default = true
"""
        parser = AuthConfigParser()
        config = parser.parse(content)
        assert config.has_registries
        assert len(config.registries) == 1
        assert config.registries[0].name == "private"
        assert config.registries[0].url == "https://private.example.com/simple"
        assert config.registries[0].default is True

    def test_parse_multiple_registries(self) -> None:
        content = """
[[tool.uv.index]]
name = "pypi"
url = "https://pypi.org/simple"
default = true

[[tool.uv.index]]
name = "private"
url = "https://private.example.com/simple"
explicit = true
"""
        parser = AuthConfigParser()
        config = parser.parse(content)
        assert len(config.registries) == 2
        assert config.registries[0].name == "pypi"
        assert config.registries[1].name == "private"
        assert config.registries[1].explicit is True


class TestParseAuthConfig:
    """Test parse_auth_config function."""

    def test_parse_from_file(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
version = "0.1.0"

[tool.uv]
tls-ca-certificates = ["/etc/ssl/certs/ca.pem"]
tls-no-verify = false

[[tool.uv.index]]
name = "private"
url = "https://private.example.com/simple"
default = true
""")

        config = parse_auth_config(pyproject)
        assert config.has_registries
        assert config.has_tls_config
        assert len(config.registries) == 1
        assert config.registries[0].name == "private"
        assert "/etc/ssl/certs/ca.pem" in config.tls_ca_certificates

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            parse_auth_config(tmp_path / "nonexistent" / "pyproject.toml")
