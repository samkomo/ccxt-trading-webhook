import unittest
import json
from app import create_app
from datetime import datetime
import hmac
import hashlib
import os

class WebhookTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app().test_client()
        self.secret = os.getenv("WEBHOOK_SECRET", "test_secret")

    def _sign_payload(self, payload):
        data = json.dumps(payload).encode()
        signature = hmac.new(
            key=self.secret.encode(),
            msg=data,
            digestmod=hashlib.sha256
        ).hexdigest()
        return signature, data

    def test_health_check(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn("status", response.json)

    def test_invalid_signature(self):
        payload = {"test": "data"}
        headers = {
            "Content-Type": "application/json",
            "X-Signature": "invalid",
            "X-Timestamp": datetime.utcnow().isoformat() + "Z"
        }
        response = self.app.post('/webhook', data=json.dumps(payload), headers=headers)
        self.assertEqual(response.status_code, 403)

    def test_missing_timestamp(self):
        payload = {"test": "data"}
        sig, data = self._sign_payload(payload)
        headers = {
            "Content-Type": "application/json",
            "X-Signature": sig
        }
        response = self.app.post('/webhook', data=data, headers=headers)
        self.assertEqual(response.status_code, 403)

# Run tests
if __name__ == '__main__':
    unittest.main()
