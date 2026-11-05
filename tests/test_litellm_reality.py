"""Receipt validation, independent of the optional LiteLLM dependency."""
import unittest

from scripts.check_litellm_reality import allocation_summary


class ReceiptTests(unittest.TestCase):
    def test_response_cannot_claim_a_different_provider(self):
        row = {"phase": "measured", "error": None, "provider": "B",
               "response_id": "A-1", "endpoint": {"provider": "A", "id": "A-1"},
               "client_seconds": 0.3}
        with self.assertRaisesRegex(ValueError, "PROVIDER_BINDING"):
            allocation_summary([row])
