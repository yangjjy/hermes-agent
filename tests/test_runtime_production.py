import tempfile
import unittest
from pathlib import Path

from hermes_cli.runtime_production import ProductionRuntimeConfig


class ProductionRuntimeConfigTests(unittest.TestCase):
    def test_loads_non_secret_endpoint_and_allowlist(self):
        config = ProductionRuntimeConfig.from_yaml(Path(__file__).parents[1] / "configs" / "runtime-production.yaml")
        self.assertEqual("http://127.0.0.1:8643", config.runtime_base_url)
        self.assertEqual(("asset.profile",), config.allowed_capabilities)
        self.assertEqual(0, config.max_transport_retries)

    def test_rejects_broad_allowlist(self):
        with self.assertRaises(ValueError):
            ProductionRuntimeConfig.from_mapping({"runtime_base_url": "http://127.0.0.1:8643", "credential_reference": "env:X", "allowed_capabilities": ["*"]})
