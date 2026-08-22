import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


class ConfigAuthenticationTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_config_rejects_missing_token(self):
        with patch.dict(os.environ, {"API_SECRET_TOKEN": "correct-token"}, clear=False):
            response = self.client.get("/api/config")

        self.assertEqual(response.status_code, 401)

    def test_config_rejects_wrong_token(self):
        with patch.dict(os.environ, {"API_SECRET_TOKEN": "correct-token"}, clear=False):
            response = self.client.get(
                "/api/config",
                headers={"X-Api-Token": "wrong-token"},
            )

        self.assertEqual(response.status_code, 401)

    def test_config_accepts_correct_token_without_exposing_gas_url(self):
        with patch.dict(
            os.environ,
            {
                "API_SECRET_TOKEN": "correct-token",
                "GAS_WEB_APP_URL": "https://example.invalid/internal-endpoint",
            },
            clear=False,
        ):
            response = self.client.get(
                "/api/config",
                headers={"X-Api-Token": "correct-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "app_name": "Workspace Next",
                "icon": "🚀",
                "version": "2.0.0",
                "auth_mode": "token",
            },
        )


if __name__ == "__main__":
    unittest.main()
