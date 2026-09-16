"""Dependency-free checks for inactive identity-layer safeguards."""

from datetime import UTC, datetime, timedelta
import importlib
from pathlib import Path
import sys
import types
import unittest


class MigrationInvariantTests(unittest.TestCase):
    def test_direct_conversation_constraint_triggers_are_deferred_and_complete(self):
        migration = Path("migrations/001_identity_foundation.sql").read_text()
        self.assertIn("direct_lower_user_id IS NOT NULL", migration)
        self.assertIn("direct_higher_user_id IS NOT NULL", migration)
        self.assertIn("CREATE CONSTRAINT TRIGGER conversation_members_direct_invariants", migration)
        self.assertIn("CREATE CONSTRAINT TRIGGER conversations_direct_invariants", migration)
        self.assertIn("DEFERRABLE INITIALLY DEFERRED", migration)
        self.assertIn("member_count <> 2", migration)
        self.assertIn("participant_count <> 2", migration)
        self.assertIn("NOT creator_is_direct_participant", migration)
        self.assertIn("NOT creator_is_owner", migration)

    def test_non_returning_mutations_use_execute(self):
        repository = Path("identity/repository.py").read_text()
        service = Path("identity/service.py").read_text()
        self.assertNotIn("self.one('UPDATE", repository)
        self.assertNotIn("self.one('INSERT INTO conversations", repository)
        self.assertNotIn("repo.one('UPDATE", service)
        self.assertNotIn("repo.one('INSERT INTO refresh_tokens", service)


class RefreshExpirationTests(unittest.TestCase):
    def load_service(self):
        security = types.ModuleType("identity.security")
        security.token_digest = lambda token: token
        security.issue_access_token = lambda user_id: f"access:{user_id}"
        security.issue_refresh_token = lambda user_id, family_id=None: (
            "refresh",
            "digest",
            datetime.now(UTC) + timedelta(days=30),
            "new-token-id",
            family_id or "new-family-id",
        )
        security.hash_password = lambda password: password
        security.password_matches = lambda expected, actual: expected == actual

        validation = types.ModuleType("identity.validation")
        validation.normalize_email = lambda value: value
        validation.normalize_ouivocal_id = lambda value: value
        validation.require_password = lambda value: value
        validation.optional_text = lambda value, _field, _maximum: value

        original_security = sys.modules.get("identity.security")
        original_validation = sys.modules.get("identity.validation")
        original_service = sys.modules.pop("identity.service", None)
        sys.modules["identity.security"] = security
        sys.modules["identity.validation"] = validation
        try:
            return importlib.import_module("identity.service")
        finally:
            sys.modules.pop("identity.service", None)
            if original_security is None:
                sys.modules.pop("identity.security", None)
            else:
                sys.modules["identity.security"] = original_security
            if original_validation is None:
                sys.modules.pop("identity.validation", None)
            else:
                sys.modules["identity.validation"] = original_validation
            if original_service is not None:
                sys.modules["identity.service"] = original_service

    def test_expired_refresh_token_is_rejected_without_rotation(self):
        service = self.load_service()

        class Repository:
            def __init__(self):
                self.executed = []
                self.revoked_families = []

            def token(self, digest):
                if digest != "expired-token":
                    raise AssertionError("unexpected token digest")
                return {
                    "id": "token-id",
                    "user_id": "user-id",
                    "token_family_id": "family-id",
                    "revoked_at": None,
                    "expires_at": datetime.now(UTC) - timedelta(seconds=1),
                }

            def execute(self, sql, args):
                self.executed.append((sql, args))

            def revoke_family(self, family_id):
                self.revoked_families.append(family_id)

        repo = Repository()
        with self.assertRaisesRegex(PermissionError, "expired"):
            service.refresh(repo, "expired-token")
        self.assertEqual(repo.executed, [])
        self.assertEqual(repo.revoked_families, [])


if __name__ == "__main__":
    unittest.main()
