"""Production configuration boundary for the generic Runtime client."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from .runtime_client import RuntimeClient, RuntimeClientConfig


@dataclass(frozen=True)
class ProductionRuntimeConfig:
    runtime_base_url: str
    credential_reference: str
    timeout_seconds: float = 10.0
    max_transport_retries: int = 0
    allowed_capabilities: tuple[str, ...] = ("asset.profile",)
    runtime_release: str = "AIOS_RUNTIME_BASELINE_V1_2"
    environment: str = "production"

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ProductionRuntimeConfig":
        required = ("runtime_base_url", "credential_reference")
        if any(not isinstance(value.get(key), str) or not value[key].strip() for key in required):
            raise ValueError("runtime production config requires endpoint and credential reference")
        allowed = value.get("allowed_capabilities", ["asset.profile"])
        if not isinstance(allowed, list) or tuple(allowed) != ("asset.profile",):
            raise ValueError("production allow-list must contain only asset.profile")
        result = cls(
            runtime_base_url=value["runtime_base_url"],
            credential_reference=value["credential_reference"],
            timeout_seconds=float(value.get("timeout_seconds", 10.0)),
            max_transport_retries=int(value.get("max_transport_retries", 0)),
            allowed_capabilities=("asset.profile",),
            runtime_release=str(value.get("runtime_release", "AIOS_RUNTIME_BASELINE_V1_2")),
            environment=str(value.get("environment", "production")),
        )
        # Reuse the public client validation for transport settings.
        RuntimeClientConfig(result.runtime_base_url, result.credential_reference, result.timeout_seconds, result.max_transport_retries)
        return result

    @classmethod
    def from_yaml(cls, path: Path) -> "ProductionRuntimeConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict) or not isinstance(payload.get("runtime"), dict):
            raise ValueError("runtime production config must contain a runtime mapping")
        return cls.from_mapping(payload["runtime"])

    def client(self, credential_provider: Any) -> RuntimeClient:
        return RuntimeClient(
            RuntimeClientConfig(self.runtime_base_url, self.credential_reference, self.timeout_seconds, self.max_transport_retries),
            credential_provider=credential_provider,
        )
