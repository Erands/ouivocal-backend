"""Flask registration and fail-safe tests that do not contact PostgreSQL."""

from contextlib import contextmanager
from unittest.mock import patch
import unittest

from identity.config import IdentityConfigurationError
from main import app


class IdentityBlueprintTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_existing_and_identity_routes_are_registered(self):
        rules = {rule.rule for rule in app.url_map.iter_rules()}
        self.assertTrue({"/", "/translate", "/audio", "/audio-live", "/audio/<path:filename>"} <= rules)
        self.assertTrue({"/identity/register", "/identity/login", "/identity/refresh"} <= rules)

    def test_identity_database_configuration_failure_is_safe(self):
        with patch(
            "routes.identity.connection",
            side_effect=IdentityConfigurationError("not configured"),
        ):
            response = self.client.post(
                "/identity/login",
                json={"email": "person@example.com", "password": "password"},
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json(), {"error": "Identity service is unavailable"})

    def test_login_delegates_to_existing_service(self):
        @contextmanager
        def fake_connection():
            yield object()

        with (
            patch("routes.identity.connection", fake_connection),
            patch(
                "routes.identity.identity_service.login",
                return_value={"access_token": "test-token", "token_type": "Bearer"},
            ) as login,
        ):
            response = self.client.post(
                "/identity/login",
                json={"email": "person@example.com", "password": "password"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["access_token"], "test-token")
        self.assertEqual(login.call_args.args[1:], ("person@example.com", "password"))


if __name__ == "__main__":
    unittest.main()
