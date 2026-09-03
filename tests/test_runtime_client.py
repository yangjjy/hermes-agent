import json
import socket
import unittest
from io import BytesIO
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.error import HTTPError, URLError

from hermes_cli.runtime_client import (
    RuntimeClient,
    RuntimeClientConfig,
    RuntimeHTTPError,
    RuntimeResponseError,
    RuntimeTransportError,
)


class _RuntimeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        payloads = {
            "/v1/health/live": {"status": "alive"},
            "/v1/health/ready": {"state": "READY", "status": "ready"},
            "/v1/capabilities": {"capabilities": [{"capability_id": "asset.profile"}]},
        }
        payload = payloads.get(self.path, {"error": {"code": "NOT_FOUND"}})
        self.send_response(200 if self.path in payloads else 404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def do_POST(self):
        if self.headers["Authorization"] != "Bearer test-token":
            self.send_response(401)
            self.end_headers()
            return
        self.assert_json_content_type()
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        payload = {
            "request_id": body["request_id"],
            "correlation_id": body["correlation_id"],
            "audit_correlation_id": body["correlation_id"],
            "execution_id": "exec:synthetic-001",
            "status": "COMPLETED",
            "code": "OK",
            "result": {"asset_id": body["payload"]["asset_id"]},
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def assert_json_content_type(self):
        if self.headers["Content-Type"] != "application/json":
            self.send_response(415)
            self.end_headers()
            raise AssertionError("unexpected content type")

    def log_message(self, *_args):
        return


class _MalformedReadyHandler(_RuntimeHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"alive"}')


class RuntimeClientTests(unittest.TestCase):
    def setUp(self):
        self.server = HTTPServer(("127.0.0.1", 0), _RuntimeHandler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = RuntimeClient(
            RuntimeClientConfig(
                runtime_base_url=f"http://127.0.0.1:{self.server.server_port}",
                credential_ref="synthetic-token-ref",
                timeout_seconds=2,
            ),
            credential_provider=lambda: "test-token",
        )

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def test_public_http_contract_and_runtime_ids(self):
        self.assertEqual(self.client.health_live()["status"], "alive")
        self.assertEqual(self.client.health_ready()["state"], "READY")
        self.assertEqual(self.client.capabilities()["capabilities"][0]["capability_id"], "asset.profile")
        response = self.client.invoke(
            {
                "contract_version": "aios.runtime.host.v1",
                "request_id": "request-001",
                "instance_id": "synthetic-runtime-v1",
                "capability_id": "asset.profile",
                "intent": "READ",
                "payload": {"asset_id": "UNIT-001"},
                "business_date": "2026-09-03",
                "data_as_of": "2026-09-03T00:00:00Z",
                "timezone": "Asia/Shanghai",
                "approval_context": {"status": "NOT_REQUIRED"},
                "correlation_id": "corr-001",
            }
        )
        self.assertEqual(response.status, "COMPLETED")
        self.assertEqual(response.execution_id, "exec:synthetic-001")
        self.assertEqual(response.audit_correlation_id, "corr-001")
        self.assertEqual(response.result["asset_id"], "UNIT-001")

    def test_malformed_runtime_response_is_not_silent_success(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()
        self.server = HTTPServer(("127.0.0.1", 0), _MalformedReadyHandler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = RuntimeClient(
            RuntimeClientConfig(
                runtime_base_url=f"http://127.0.0.1:{self.server.server_port}",
                credential_ref="synthetic-token-ref",
            ),
            credential_provider=lambda: "test-token",
        )
        with self.assertRaises(RuntimeResponseError):
            self.client.health_ready()

    def test_completed_response_requires_execution_id(self):
        class MissingExecutionHandler(_RuntimeHandler):
            def do_POST(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "request_id": "request-001",
                    "correlation_id": "corr-001",
                    "status": "COMPLETED",
                    "code": "OK",
                    "result": {},
                }).encode())

        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()
        self.server = HTTPServer(("127.0.0.1", 0), MissingExecutionHandler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = RuntimeClient(
            RuntimeClientConfig(
                runtime_base_url=f"http://127.0.0.1:{self.server.server_port}",
                credential_ref="synthetic-token-ref",
            ),
            credential_provider=lambda: "test-token",
        )
        with self.assertRaises(RuntimeResponseError):
            self.client.invoke({"request_id": "request-001"})

    def test_http_failures_are_explicit_and_not_success(self):
        failures = ((401, "UNAUTHENTICATED"), (403, "CAPABILITY_NOT_AUTHORIZED"),
                    (404, "ASSET_NOT_FOUND"), (503, "PROVIDER_SOURCE_UNAVAILABLE"))
        for status, code in failures:
            def opener(_request, *, _status=status, _code=code, **_kwargs):
                raise HTTPError(
                    "http://runtime.invalid/v1/invoke", _status, "failure", {},
                    BytesIO(json.dumps({"code": _code}).encode()),
                )

            client = RuntimeClient(
                RuntimeClientConfig("http://runtime.invalid", "credential-ref"),
                credential_provider=lambda: "test-token",
                opener=opener,
            )
            with self.assertRaises(RuntimeHTTPError) as raised:
                client.health_ready()
            self.assertEqual(raised.exception.status_code, status)
            self.assertEqual(raised.exception.code, code)

    def test_not_ready_fails_closed(self):
        def opener(_request, **_kwargs):
            class Response:
                def __enter__(self):
                    return self

                def __exit__(self, *_args):
                    return False

                def read(self):
                    return b'{"state":"STARTING","status":"starting"}'

            return Response()

        client = RuntimeClient(
            RuntimeClientConfig("http://runtime.invalid", "credential-ref"),
            credential_provider=lambda: "test-token",
            opener=opener,
        )
        with self.assertRaises(RuntimeResponseError):
            client.health_ready()

    def test_timeout_is_ambiguous_and_only_pretransmit_refusal_is_retried(self):
        def timeout_opener(_request, **_kwargs):
            raise socket.timeout("synthetic timeout")

        timeout_client = RuntimeClient(
            RuntimeClientConfig("http://runtime.invalid", "credential-ref", max_transport_retries=2),
            credential_provider=lambda: "test-token",
            opener=timeout_opener,
        )
        with self.assertRaises(RuntimeTransportError) as raised:
            timeout_client.health_live()
        self.assertTrue(raised.exception.ambiguous)

        calls = []

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"status":"alive"}'

        def retry_opener(_request, **_kwargs):
            calls.append(1)
            if len(calls) < 3:
                raise URLError(ConnectionRefusedError("not listening yet"))
            return Response()

        retry_client = RuntimeClient(
            RuntimeClientConfig("http://runtime.invalid", "credential-ref", max_transport_retries=2),
            credential_provider=lambda: "test-token",
            opener=retry_opener,
        )
        self.assertEqual(retry_client.health_live()["status"], "alive")
        self.assertEqual(len(calls), 3)


if __name__ == "__main__":
    unittest.main()
