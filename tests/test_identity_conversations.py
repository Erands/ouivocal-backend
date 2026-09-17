from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
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
            def accepted_contact_exists(_, creator, other): return True
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
        repo.direct_with_preferences = lambda *_: (existing, False, {
            "created_by_user_id": self.creator,
            "default_source_language": "en", "default_target_language": "fr",
        })
        result = service.create_direct_conversation(repo, self.creator, {"participant_id": str(self.participant), "my_language": "en", "their_language": "fr"})
        self.assertEqual(result["conversation_id"], str(existing))
        self.assertFalse(result["created"])

    def test_other_participant_sees_the_inverse_canonical_language_pair(self):
        conversation = {
            "created_by_user_id": self.creator,
            "default_source_language": "en", "default_target_language": "fr",
        }
        self.assertEqual(service.conversation_languages_for_user(conversation, self.creator), ("en", "fr"))
        self.assertEqual(service.conversation_languages_for_user(conversation, self.participant), ("fr", "en"))

    def test_inverse_pair_is_derived_for_each_supported_direction(self):
        conversation = {
            "created_by_user_id": self.creator,
            "default_source_language": "fr", "default_target_language": "en",
        }
        self.assertEqual(service.conversation_languages_for_user(conversation, self.participant), ("en", "fr"))

    def test_duplicate_conversation_keeps_its_existing_canonical_pair(self):
        existing = uuid4()
        repo = self.repository({
            "id": self.creator, "ouivocal_id": "first_user", "full_name": "First User",
            "avatar_url": None, "identity_verified_at": None,
        })
        repo.direct_with_preferences = lambda *_: (existing, False, {
            "created_by_user_id": self.creator,
            "default_source_language": "en", "default_target_language": "fr",
        })
        result = service.create_direct_conversation(repo, self.participant, {
            "participant_id": str(self.creator), "my_language": "fr", "their_language": "en",
        })
        self.assertEqual(result["conversation_id"], str(existing))
        self.assertFalse(result["created"])
        self.assertEqual((result["source_language"], result["target_language"]), ("fr", "en"))

    def test_rejects_non_contacts_before_creating_a_conversation(self):
        repo = self.repository(self.public_participant)
        repo.accepted_contact_exists = lambda *_: False
        with self.assertRaises(service.AuthorizationError):
            service.create_direct_conversation(repo, self.creator, {"participant_id": str(self.participant), "my_language": "en", "their_language": "fr"})

    def test_rejects_pending_and_rejected_contact_relationships(self):
        for relationship_status in ("pending", "rejected"):
            repo = self.repository(self.public_participant)
            repo.accepted_contact_exists = lambda *_: False
            with self.subTest(relationship_status=relationship_status), self.assertRaises(service.AuthorizationError):
                service.create_direct_conversation(repo, self.creator, {"participant_id": str(self.participant), "my_language": "en", "their_language": "fr"})

    def test_authenticated_user_can_list_only_their_direct_conversations(self):
        repo = self.repository(self.public_participant)
        conversation_id = uuid4()
        repo.direct_conversations_for = lambda user_id: [{
            "conversation_id": conversation_id, "created_by_user_id": self.creator,
            "default_source_language": "en", "default_target_language": "fr",
            **self.public_participant,
        }]
        result = service.list_direct_conversations(repo, self.creator)
        self.assertEqual(result["conversations"][0]["conversation_id"], str(conversation_id))
        self.assertEqual(result["conversations"][0]["participant"]["oui_vocal_id"], "second_user")
        self.assertNotIn("email", result["conversations"][0]["participant"])

    def test_message_history_is_chronological_and_only_for_members(self):
        conversation_id = uuid4()
        first = datetime.now(UTC)
        second = first + timedelta(seconds=1)
        repo = self.repository(self.public_participant)
        repo.conversation_for_member = lambda conversation, user: {
            "id": conversation, "created_by_user_id": self.creator,
            "default_source_language": "en", "default_target_language": "fr",
        } if user == self.creator else None
        repo.conversation_messages_for_member = lambda *_: [
            {"id": uuid4(), "sender_user_id": self.creator, "original_text": "First", "translated_text": "Premier", "source_language": "en", "target_language": "fr", "created_at": first},
            {"id": uuid4(), "sender_user_id": self.participant, "original_text": "Second", "translated_text": "Deuxième", "source_language": "fr", "target_language": "en", "created_at": second},
        ]
        result = service.conversation_messages(repo, self.creator, conversation_id)
        self.assertEqual([message["original"] for message in result["messages"]], ["First", "Second"])
        self.assertTrue(result["messages"][0]["is_mine"])
        self.assertFalse(result["messages"][1]["is_mine"])
        with self.assertRaises(service.AuthorizationError):
            service.conversation_messages(repo, self.participant, conversation_id)

    def test_message_creation_rejects_unsupported_or_wrong_direction(self):
        conversation_id = uuid4()
        repo = self.repository(self.public_participant)
        repo.conversation_for_member = lambda *_: {
            "created_by_user_id": self.creator, "default_source_language": "en", "default_target_language": "fr",
        }
        with self.assertRaises(service.AuthorizationError):
            service.create_conversation_message(repo, self.creator, conversation_id, {
                "original": "Hello", "translated": "Bonjour", "source_language": "fr", "target_language": "en",
            })

    def test_inactive_authenticated_user_cannot_create_a_message(self):
        repo = self.repository(self.public_participant)
        repo.user = lambda *_: None
        with self.assertRaises(PermissionError):
            service.create_conversation_message(repo, self.creator, uuid4(), {
                "original": "Hello", "translated": "Bonjour", "source_language": "en", "target_language": "fr",
            })


class ConversationRouteTests(unittest.TestCase):
    def setUp(self): self.client = app.test_client()

    def test_unauthenticated_request_is_rejected(self):
        self.assertEqual(self.client.post("/identity/conversations", json={}).status_code, 401)
        self.assertEqual(self.client.get("/identity/conversations").status_code, 401)
        self.assertEqual(self.client.get(f"/identity/conversations/{uuid4()}/messages").status_code, 401)
        self.assertEqual(self.client.post(f"/identity/conversations/{uuid4()}/messages", json={}).status_code, 401)

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

    def test_authenticated_conversation_list_delegates_to_service(self):
        @contextmanager
        def fake_connection(): yield object()
        with (
            patch("routes.identity.connection", fake_connection),
            patch("routes.identity.decode_access_token", return_value=str(uuid4())),
            patch("routes.identity.identity_service.list_direct_conversations", return_value={"conversations": []}) as listed,
        ):
            response = self.client.get("/identity/conversations", headers={"Authorization": "Bearer test"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"conversations": []})
        self.assertEqual(listed.call_count, 1)


if __name__ == "__main__": unittest.main()
