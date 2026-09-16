from contextlib import contextmanager
from unittest.mock import patch
from uuid import uuid4
import unittest

from identity import service
from identity.validation import ValidationError
from main import app


class ConversationServiceTests(unittest.TestCase):
    def setUp(self):
        self.creator = uuid4()
        self.participant = uuid4()
        self.public_participant = {
            "id": self.participant, "ouivocal_id": "second_user",
            "full_name": "Second User", "avatar_url": None,
            "identity_verified_at": None,
        }

    def repository(self, participant=None):
        class Repository:
            def user(_, user_id): return {"id": user_id}
            def public_active_user(_, user_id): return participant
            def direct_with_preferences(_, creator, other, source, target):
                _.call = (creator, other, source, target)
                return uuid4(), True
        return Repository()

    def test_creates_authenticated_direct_conversation_with_languages(self):
        repo = self.repository(self.public_participant)
        result = service.create_direct_conversation(repo, self.creator, {
            "participant_id": str(self.participant), "my_language": "en", "their_language": "fr",
        })
        self.assertEqual(repo.call, (self.creator, self.participant, "en", "fr"))
        self.assertTrue(result["created"])
        self.assertEqual(result["participant"]["oui_vocal_id"], "second_user")
        self.assertNotIn("email", result["participant"])

    def test_rejects_self_invalid_language_and_missing_participant(self):
        repo = self.repository(None)
        for payload in (
            {"participant_id": str(self.creator), "my_language": "en", "their_language": "fr"},
            {"participant_id": str(self.participant), "my_language": "pt", "their_language": "fr"},
            {"participant_id": "not-a-uuid", "my_language": "en", "their_language": "fr"},
        ):
            with self.assertRaises(ValidationError): service.create_direct_conversation(repo, self.creator, payload)
        with self.assertRaises(LookupError):
            service.create_direct_conversation(repo, self.creator, {"participant_id": str(self.participant), "my_language": "en", "their_language": "fr"})

    def test_duplicate_returns_existing_conversation(self):
        existing = uuid4()
        repo = self.repository(self.public_participant)
        repo.direct_with_preferences = lambda *_: (existing, False)
        result = service.create_direct_conversation(repo, self.creator, {"participant_id": str(self.participant), "my_language": "en", "their_language": "fr"})
        self.assertEqual(result["conversation_id"], str(existing))
        self.assertFalse(result["created"])


class ConversationRouteTests(unittest.TestCase):
    def setUp(self): self.client = app.test_client()

    def test_unauthenticated_request_is_rejected(self):
        self.assertEqual(self.client.post("/identity/conversations", json={}).status_code, 401)

    def test_authenticated_request_delegates_to_service(self):
        @contextmanager
        def fake_connection(): yield object()
        with (
            patch("routes.identity.connection", fake_connection),
            patch("routes.identity.decode_access_token", return_value=str(uuid4())),
            patch("routes.identity.identity_service.create_direct_conversation", return_value={"conversation_id": str(uuid4()), "created": True, "participant": {}}) as create,
        ):
            response = self.client.post("/identity/conversations", headers={"Authorization": "Bearer test"}, json={"participant_id": str(uuid4()), "my_language": "en", "their_language": "fr"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(create.call_count, 1)


if __name__ == "__main__": unittest.main()
