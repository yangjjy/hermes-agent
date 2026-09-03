"""Manual Hermes business operations over the Runtime public API."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Optional
import uuid

from .runtime_client import RuntimeClient, RuntimeClientError, RuntimeHTTPError, RuntimeTransportError
from .runtime_production import ProductionRuntimeConfig


@dataclass(frozen=True)
class BusinessOperationResult:
    operation_id: str
    workflow_id: str
    asset_id: str
    business_status: str
    result: Mapping[str, Any]
    operation_timestamp: str
    request_id: str
    correlation_id: str
    execution_id: Optional[str]
    audit_correlation_id: Optional[str]

    def business_view(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "workflow_id": self.workflow_id,
            "asset_id": self.asset_id,
            "business_status": self.business_status,
            "result": dict(self.result),
            "operation_timestamp": self.operation_timestamp,
        }


def run_asset_profile_query(
    config: ProductionRuntimeConfig,
    credential_provider: Callable[[], str],
    asset_id: str,
    *,
    operation_id: Optional[str] = None,
    audit_path: Optional[Path] = None,
    client: Optional[RuntimeClient] = None,
) -> BusinessOperationResult:
    """Run one manual, single-asset read-only operation through Runtime."""
    if not isinstance(asset_id, str) or not asset_id.strip():
        raise ValueError("asset_id is required")
    if "asset.profile" not in config.allowed_capabilities:
        raise RuntimeClientError("CAPABILITY_NOT_AUTHORIZED")
    runtime = client or config.client(credential_provider)
    ready = runtime._request("GET", "/v1/health/ready")
    if ready.get("status") != "ready":
        raise RuntimeClientError("RUNTIME_NOT_READY")
    capabilities = runtime.capabilities().get("capabilities", [])
    binding = next((item for item in capabilities if item.get("capability_id") == "asset.profile"), None)
    if not binding or binding.get("state") != "AVAILABLE" or binding.get("code") != "OK":
        raise RuntimeClientError("CAPABILITY_NOT_AVAILABLE")
    operation = operation_id or "hermes-op-" + uuid.uuid4().hex
    timestamp = datetime.now(timezone.utc).isoformat()
    request_id = "hermes-request-" + uuid.uuid4().hex
    correlation_id = "hermes-correlation-" + uuid.uuid4().hex
    response = runtime.invoke({
        "contract_version": "aios.runtime.host.v1",
        "request_id": request_id,
        "instance_id": "production-runtime",
        "capability_id": "asset.profile",
        "intent": "READ",
        "payload": {"asset_id": asset_id.strip()},
        "business_date": timestamp[:10],
        "data_as_of": timestamp,
        "timezone": "UTC",
        "approval_context": {"approval_id": None, "status": "NOT_REQUIRED"},
        "correlation_id": correlation_id,
    })
    if response.status != "COMPLETED" or response.code != "OK" or not isinstance(response.result, dict):
        raise RuntimeClientError(response.code or "RUNTIME_OPERATION_FAILED")
    result = BusinessOperationResult(operation, "asset-profile-query-v1", asset_id.strip(), "SUCCESS", response.result, timestamp, response.request_id, response.correlation_id, response.execution_id, response.audit_correlation_id)
    _write_audit(audit_path, result)
    return result


def _write_audit(path: Optional[Path], result: BusinessOperationResult) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "operation_id": result.operation_id,
        "workflow_id": result.workflow_id,
        "business_timestamp": result.operation_timestamp,
        "capability": "asset.profile",
        "asset_id": result.asset_id,
        "request_id": result.request_id,
        "correlation_id": result.correlation_id,
        "execution_id": result.execution_id,
        "audit_correlation_id": result.audit_correlation_id,
        "terminal_runtime_status": "COMPLETED",
        "terminal_business_status": result.business_status,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
