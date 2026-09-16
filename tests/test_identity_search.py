from contextlib import contextmanager
from datetime import datetime, UTC
from unittest.mock import patch
import unittest

from identity import service
from identity.validation import ValidationError
from main import app


class UserSearchServiceTests(unittest.TestCase):
    def test_query_validation_trims_and_requires_two_characters(self):
        self.assertEqual(service.normalize_user_search_query("  Al  "), "Al")
        for query in (None, "", " ", "a"):
            with self.assertRaises(ValidationError):
                service.normalize_user_search_query(query)

    def test_search_serializes_only_safe_public_fields(self):
        class Repository:
            def search_public_users(self, query, current_user_id, limit):
                self.args = (query, current_user_id, limit)
                return [{
                    "id": "target-id", "ouivocal_id": "Alpha_User",
                    "full_name": "Alpha User", "avatar_url": "https://example.test/a.png",
                    "identity_verified_at": datetime.now(UTC),
                    "email": "private@example.test", "password_hash": "private",
                }]

        repo = Repository()
        result = service.search_users(repo, "caller-id", "  ALp  ")
        self.assertEqual(repo.args, ("ALp", "caller-id", service.USER_SEARCH_LIMIT))
        user = result["results"][0]
        self.assertEqual(user["display_name"], "Alpha User")
        self.assertTrue(user["is_verified"])
        self.assertEqual(user["languages"], [])
        self.assertEqual(set(user), {"id", "oui_vocal_id", "username", "display_name", "profile_photo_url", "is_verified", "languages"})
        self.assertNotIn("email", user)
        self.assertNotIn("password_hash", user)


class UserSearchRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get("/identity/users/search?q=al")
        self.assertEqual(response.status_code, 401)

    def test_authenticated_request_delegates_with_query(self):
        @contextmanager
        def fake_connection():
            yield object()

        with (
            patch("routes.identity.connection", fake_connection),
            patch("routes.identity.decode_access_token", return_value="caller-id"),
            patch("routes.identity.identity_service.search_users", return_value={"results": []}) as search,
        ):
            response = self.client.get(
                "/identity/users/search?q=%20Al%20",
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"results": []})
        self.assertEqual(search.call_args.args[1:], ("caller-id", " Al "))


class UserSearchRepositoryTests(unittest.TestCase):
    def test_query_is_parameterized_limited_and_excludes_requester(self):
        class Cursor:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def execute(self, sql, args): self.sql, self.args = sql, args
            def fetchall(self): return []
        class Connection:
            def __init__(self): self.cursor_instance = Cursor()
            def cursor(self): return self.cursor_instance

        from identity.repository import Repository
        connection = Connection()
        Repository(connection).search_public_users("ALp", "caller-id", 20)
        cursor = connection.cursor_instance
        self.assertIn("id <> %s", cursor.sql)
        self.assertIn("ILIKE %s", cursor.sql)
        self.assertIn("ORDER BY lower(ouivocal_id), id", cursor.sql)
        self.assertIn("LIMIT %s", cursor.sql)
        self.assertEqual(cursor.args, ("caller-id", "%ALp%", "%ALp%", 20))


if __name__ == "__main__":
    unittest.main()
