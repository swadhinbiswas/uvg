"""Authentication and TLS configuration.

Handles registry authentication, TLS certificates, and enterprise
registry configuration for GVX.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RegistryAuth:
    """Authentication configuration for a registry."""

    url: str
    username: str | None = None
    password: str | None = None
    token: str | None = None
    keyring_provider: str | None = None

    @property
    def has_credentials(self) -> bool:
        """Check if credentials are configured."""
        return bool(self.username or self.password or self.token or self.keyring_provider)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (without sensitive data)."""
        result: dict[str, Any] = {"url": self.url}
        if self.username:
            result["username"] = self.username
        if self.token:
            result["token"] = "***"
        if self.keyring_provider:
            result["keyring_provider"] = self.keyring_provider
        return result


@dataclass
class TLSCertificate:
    """TLS certificate configuration."""

    path: str
    type: str = "ca"  # ca, client-cert, client-key

    @property
    def is_ca(self) -> bool:
        """Check if this is a CA certificate."""
        return self.type == "ca"

    @property
    def is_client_cert(self) -> bool:
        """Check if this is a client certificate."""
        return self.type == "client-cert"


@dataclass
class RegistryConfig:
    """Configuration for a package registry."""

    name: str
    url: str
    default: bool = False
    explicit: bool = False
    auth: RegistryAuth | None = None
    tls_certificates: list[TLSCertificate] = field(default_factory=list)
    exclude_newer: str | None = None
    publish_url: str | None = None

    @property
    def has_auth(self) -> bool:
        """Check if registry has authentication configured."""
        return self.auth is not None and self.auth.has_credentials

    @property
    def has_tls(self) -> bool:
        """Check if registry has TLS certificates configured."""
        return len(self.tls_certificates) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "name": self.name,
            "url": self.url,
            "default": self.default,
            "explicit": self.explicit,
        }
        if self.auth:
            result["auth"] = self.auth.to_dict()
        if self.tls_certificates:
            result["tls_certificates"] = [{"path": c.path, "type": c.type} for c in self.tls_certificates]
        if self.exclude_newer:
            result["exclude_newer"] = self.exclude_newer
        if self.publish_url:
            result["publish_url"] = self.publish_url
        return result


@dataclass
class AuthConfig:
    """Complete authentication and TLS configuration."""

    registries: list[RegistryConfig] = field(default_factory=list)
    tls_ca_certificates: list[str] = field(default_factory=list)
    tls_client_cert: str | None = None
    tls_client_key: str | None = None
    tls_no_verify: bool = False
    keyring_provider: str | None = None

    @property
    def has_registries(self) -> bool:
        """Check if custom registries are configured."""
        return len(self.registries) > 0

    @property
    def has_tls_config(self) -> bool:
        """Check if TLS configuration is present."""
        return bool(self.tls_ca_certificates or self.tls_client_cert or self.tls_client_key or self.tls_no_verify)

    def get_default_registry(self) -> RegistryConfig | None:
        """Get the default registry."""
        for registry in self.registries:
            if registry.default:
                return registry
        return None

    def get_registry_by_name(self, name: str) -> RegistryConfig | None:
        """Get a registry by name."""
        for registry in self.registries:
            if registry.name == name:
                return registry
        return None

    def get_registry_by_url(self, url: str) -> RegistryConfig | None:
        """Get a registry by URL."""
        for registry in self.registries:
            if registry.url == url:
                return registry
        return None


class AuthConfigParser:
    """Parses authentication and TLS configuration from pyproject.toml."""

    def parse(self, content: str) -> AuthConfig:
        """Parse auth configuration from pyproject.toml content.

        Args:
            content: pyproject.toml file content.

        Returns:
            AuthConfig instance.
        """
        config = AuthConfig()
        lines = content.splitlines()
        current_section: str | None = None
        current_registry: dict[str, Any] = {}

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("[["):
                if current_registry:
                    config.registries.append(self._build_registry(current_registry))
                    current_registry = {}
                current_section = stripped.split("]]")[0].strip("[")
                continue

            if stripped.startswith("["):
                if current_registry:
                    config.registries.append(self._build_registry(current_registry))
                    current_registry = {}
                current_section = stripped.strip("[]").strip()
                continue

            if "=" in stripped and current_section:
                key, value = stripped.split("=", 1)
                key = key.strip()
                value = value.strip()

                if current_section.startswith("tool.uv.index"):
                    current_registry[key] = self._parse_value(value)
                elif current_section == "tool.uv":
                    self._parse_global_auth(config, key, self._parse_value(value))

        if current_registry:
            config.registries.append(self._build_registry(current_registry))

        return config

    def _parse_value(self, value: str) -> Any:
        """Parse a TOML value."""
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            return self._parse_array(value)
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        if value.startswith("'") and value.endswith("'"):
            return value[1:-1]
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        return value

    def _parse_array(self, value: str) -> list[str]:
        """Parse a TOML array."""
        value = value.strip("[]").strip()
        if not value:
            return []
        items = []
        for item in value.split(","):
            item = item.strip().strip('"').strip("'")
            if item:
                items.append(item)
        return items

    def _parse_global_auth(self, config: AuthConfig, key: str, value: Any) -> None:
        """Parse global authentication configuration."""
        if key == "tls-ca-certificates":
            if isinstance(value, list):
                config.tls_ca_certificates = value
            elif isinstance(value, str):
                config.tls_ca_certificates = [value]
        elif key == "tls-client-cert":
            config.tls_client_cert = str(value)
        elif key == "tls-client-key":
            config.tls_client_key = str(value)
        elif key == "tls-no-verify":
            config.tls_no_verify = bool(value)
        elif key == "keyring-provider":
            config.keyring_provider = str(value)

    def _build_registry(self, data: dict[str, Any]) -> RegistryConfig:
        """Build a RegistryConfig from parsed data."""
        auth = None
        if data.get("username") or data.get("password") or data.get("token"):
            auth = RegistryAuth(
                url=str(data.get("url", "")),
                username=data.get("username"),
                password=data.get("password"),
                token=data.get("token"),
                keyring_provider=data.get("keyring-provider"),
            )

        return RegistryConfig(
            name=str(data.get("name", "")),
            url=str(data.get("url", "")),
            default=bool(data.get("default", False)),
            explicit=bool(data.get("explicit", False)),
            auth=auth,
            exclude_newer=data.get("exclude-newer"),
            publish_url=data.get("publish-url"),
        )


def parse_auth_config(pyproject_path: Path) -> AuthConfig:
    """Parse authentication configuration from a pyproject.toml file.

    Args:
        pyproject_path: Path to pyproject.toml.

    Returns:
        AuthConfig instance.

    Raises:
        FileNotFoundError: If pyproject.toml does not exist.
    """
    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found: {pyproject_path}")

    content = pyproject_path.read_text(encoding="utf-8")
    parser = AuthConfigParser()
    return parser.parse(content)
