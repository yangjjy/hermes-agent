import unittest
from unittest.mock import Mock

from hermes_cli.runtime_business import run_asset_profile_query
from hermes_cli.runtime_production import ProductionRuntimeConfig
from hermes_cli.runtime_client import RuntimeResponse


class BusinessOperationTests(unittest.TestCase):
    def setUp(self):
        self.config = ProductionRuntimeConfig("http://127.0.0.1:8643", "env:TOKEN")
        self.client = Mock()
        self.client._request.return_value = {"status": "ready", "state": "PARTIAL_READY"}
        self.client.capabilities.return_value = {"capabilities": [{"capability_id": "asset.profile", "state": "AVAILABLE", "code": "OK"}]}
        self.client.invoke.return_value = RuntimeResponse("r", "c", "COMPLETED", "OK", "exec:1", "audit:1", {"asset_id": "A"}, None, {})

    def test_business_response_is_traceable_and_sends_one_runtime_request(self):
        result = run_asset_profile_query(self.config, lambda: "secret", "A", operation_id="hermes-op-1", client=self.client)
        self.assertEqual("SUCCESS", result.business_status)
        self.assertEqual("hermes-op-1", result.operation_id)
        self.assertEqual("exec:1", result.execution_id)
        self.client.invoke.assert_called_once()

    def test_missing_asset_id_fails_before_runtime(self):
        with self.assertRaises(ValueError):
            run_asset_profile_query(self.config, lambda: "secret", "", client=self.client)
        self.client.invoke.assert_not_called()
