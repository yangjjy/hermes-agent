"""Small HTTP client for the AIOS Runtime public API.

The client deliberately knows only the public Host contract.  It does not
import Runtime code, inspect Runtime State, or resolve repository paths.
"""

from dataclasses import dataclass
import json
import socket
from typing import Any, Callable, Dict, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class RuntimeClientError(Exception):
    """Base class for deterministic Runtime client failures."""


class RuntimeTransportError(RuntimeClientError):
    """Transport failed; ``ambiguous`` marks a possible transmitted request."""

    def __init__(self, message: str, *, ambiguous: bool = False) -> None:
        super().__init__(message)
        self.ambiguous = ambiguous


class RuntimeHTTPError(RuntimeClientError):
    """Runtime returned a non-success HTTP status."""

    def __init__(self, status_code: int, code: str) -> None:
        super().__init__(f"Runtime HTTP {status_code}: {code}")
        self.status_code = status_code
        self.code = code


class RuntimeResponseError(RuntimeClientError):
    """Runtime returned malformed or incomplete JSON."""


@dataclass(frozen=True)
class RuntimeClientConfig:
    runtime_base_url: str
    credential_ref: str
    timeout_seconds: float = 10.0
    max_transport_retries: int = 0

    def __post_init__(self) -> None:
        if not self.runtime_base_url.startswith(("http://", "https://")):
            raise ValueError("runtime_base_url must use http:// or https://")
        if not self.runtime_base_url.rstrip("/"):
            raise ValueError("runtime_base_url is required")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_transport_retries < 0 or self.max_transport_retries > 2:
            raise ValueError("max_transport_retries must be between 0 and 2")


@dataclass(frozen=True)
class RuntimeResponse:
    request_id: str
    correlation_id: str
    status: str
    code: str
    execution_id: Optional[str]
    audit_correlation_id: Optional[str]
    result: Any
    error: Optional[Mapping[str, Any]]
    raw: Mapping[str, Any]

    @classmethod
    def from_json(cls, payload: Any) -> "RuntimeResponse":
        if not isinstance(payload, dict):
            raise RuntimeResponseError("Runtime response must be a JSON object")
        required = ("request_id", "correlation_id", "status", "code")
        missing = [key for key in required if not isinstance(payload.get(key), str)]
        if missing:
            raise RuntimeResponseError("Runtime response missing fields: " + ", ".join(missing))
        execution_id = payload.get("execution_id")
        if execution_id is not None and not isinstance(execution_id, str):
            raise RuntimeResponseError("Runtime execution_id must be a string")
        if payload["status"] == "COMPLETED" and not execution_id:
            raise RuntimeResponseError("Completed Runtime response missing execution_id")
        audit_id = payload.get("audit_correlation_id")
        if audit_id is not None and not isinstance(audit_id, str):
            raise RuntimeResponseError("Runtime audit_correlation_id must be a string")
        error = payload.get("error")
        if error is not None and not isinstance(error, dict):
            raise RuntimeResponseError("Runtime error must be an object")
        return cls(
            request_id=payload["request_id"],
            correlation_id=payload["correlation_id"],
            status=payload["status"],
            code=payload["code"],
            execution_id=execution_id,
            audit_correlation_id=audit_id,
            result=payload.get("result"),
            error=error,
            raw=payload,
        )


class RuntimeClient:
    """Generic client for the four public Runtime Host endpoints."""

    def __init__(
        self,
        config: RuntimeClientConfig,
        *,
        credential_provider: Callable[[], str],
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self.config = config
        self._credential_provider = credential_provider
        self._opener = opener

    def health_live(self) -> Mapping[str, Any]:
        payload = self._request("GET", "/v1/health/live", authenticated=False)
        if payload.get("status") != "alive":
            raise RuntimeResponseError("Runtime live response is not alive")
        return payload

    def health_ready(self) -> Mapping[str, Any]:
        payload = self._request("GET", "/v1/health/ready")
        if payload.get("state") != "READY" or payload.get("status") != "ready":
            raise RuntimeResponseError("Runtime ready response is malformed")
        return payload

    def capabilities(self) -> Mapping[str, Any]:
        payload = self._request("GET", "/v1/capabilities")
        if not isinstance(payload.get("capabilities"), list):
            raise RuntimeResponseError("Runtime capabilities response is malformed")
        return payload

    def invoke(self, request: Mapping[str, Any]) -> RuntimeResponse:
        if not isinstance(request, Mapping):
            raise ValueError("Runtime request must be a mapping")
        payload = self._request("POST", "/v1/invoke", payload=dict(request))
        return RuntimeResponse.from_json(payload)

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, Any]] = None,
        authenticated: bool = True,
    ) -> Dict[str, Any]:
        headers = {"Accept": "application/json"}
        if authenticated:
            token = self._credential_provider()
            if not isinstance(token, str) or not token.strip():
                raise RuntimeClientError("Runtime credential provider returned no token")
            headers["Authorization"] = "Bearer " + token.strip()
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        request = Request(
            self.config.runtime_base_url.rstrip("/") + path,
            data=data,
            headers=headers,
            method=method,
        )
        attempts = 0
        while True:
            try:
                with self._opener(request, timeout=self.config.timeout_seconds) as response:
                    raw = response.read()
                try:
                    decoded = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise RuntimeResponseError("Runtime response is not valid JSON") from exc
                if not isinstance(decoded, dict):
                    raise RuntimeResponseError("Runtime response must be a JSON object")
                return decoded
            except HTTPError as exc:
                code = "HTTP_ERROR"
                try:
                    body = json.loads(exc.read().decode("utf-8"))
                    if isinstance(body, dict):
                        code = str(body.get("code") or body.get("error", {}).get("code") or code)
                except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                    pass
                raise RuntimeHTTPError(exc.code, code) from exc
            except (TimeoutError, socket.timeout) as exc:
                raise RuntimeTransportError("Runtime request timed out", ambiguous=True) from exc
            except URLError as exc:
                if attempts < self.config.max_transport_retries and self._is_pre_transmit(exc):
                    attempts += 1
                    continue
                raise RuntimeTransportError(
                    "Runtime transport failed",
                    ambiguous=not self._is_pre_transmit(exc),
                ) from exc

    @staticmethod
    def _is_pre_transmit(error: URLError) -> bool:
        reason = error.reason
        return isinstance(reason, (ConnectionRefusedError, socket.gaierror))
