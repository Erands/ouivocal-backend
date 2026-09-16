from contextlib import contextmanager
from unittest.mock import patch
from uuid import uuid4
import unittest

from identity import service
from identity.validation import ValidationError
from main import app


class ContactRequestServiceTests(unittest.TestCase):
    def setUp(self):
        self.requester = uuid4()
        self.recipient = uuid4()
        self.request_id = uuid4()
        self.public_recipient = {
            "id": self.recipient, "ouivocal_id": "recipient",
            "full_name": "Recipient", "avatar_url": None,
            "identity_verified_at": None,
        }

    def repository(self, contact=None):
        request_id = self.request_id
        recipient = self.public_recipient

        class Repository:
            def user(_, user_id): return {"id": user_id}
            def public_active_user(_, user_id):
                if user_id == recipient["id"]: return recipient
                if user_id == self.requester:
                    return {"id": self.requester, "ouivocal_id": "requester", "full_name": "Requester", "avatar_url": None, "identity_verified_at": None}
                return None
            def create_contact_request(_, requester, addressee):
                _.created = (requester, addressee)
                return contact or {
                    "id": request_id, "requester_user_id": requester,
                    "addressee_user_id": addressee, "relationship_status": "pending",
                    "accepted_at": None,
                }, contact is None
            def respond_to_contact_request(_, contact_id, addressee, status):
                _.response = (contact_id, addressee, status)
                if contact_id != request_id or addressee != self.recipient:
                    return None
                return {
                    "id": request_id, "requester_user_id": self.requester,
                    "addressee_user_id": self.recipient,
                    "relationship_status": status, "accepted_at": None,
                }
            def pending_contact_requests_for(_ , user_id):
                if user_id != self.recipient: return []
                return [{
                    "contact_id": request_id, "relationship_status": "pending",
                    "id": self.requester, "ouivocal_id": "requester", "full_name": "Requester",
                    "avatar_url": None, "identity_verified_at": None,
                }]
        return Repository()

    def test_authenticated_request_uses_real_target_and_returns_pending(self):
        repo = self.repository()
        result = service.create_contact_request(repo, self.requester, {"user_id": str(self.recipient)})
        self.assertEqual(repo.created, (self.requester, self.recipient))
        self.assertEqual(result, {"id": str(self.request_id), "status": "pending", "direction": "outgoing", "created": True})

    def test_rejects_self_missing_and_inactive_targets(self):
        repo = self.repository()
        with self.assertRaises(ValidationError):
            service.create_contact_request(repo, self.requester, {"user_id": str(self.requester)})
        with self.assertRaises(ValidationError):
            service.create_contact_request(repo, self.requester, {"user_id": "not-a-uuid"})
        with self.assertRaises(LookupError):
            service.create_contact_request(repo, self.requester, {"user_id": str(uuid4())})

    def test_duplicate_and_reverse_pending_requests_preserve_the_single_row(self):
        pending = {
            "id": self.request_id, "requester_user_id": self.requester,
            "addressee_user_id": self.recipient, "relationship_status": "pending", "accepted_at": None,
        }
        duplicate = service.create_contact_request(self.repository(pending), self.requester, {"user_id": str(self.recipient)})
        reverse = service.create_contact_request(self.repository(pending), self.recipient, {"user_id": str(self.requester)})
        self.assertEqual(duplicate["status"], "pending")
        self.assertEqual(duplicate["direction"], "outgoing")
        self.assertFalse(duplicate["created"])
        self.assertEqual(reverse["direction"], "incoming")
        self.assertFalse(reverse["created"])

    def test_only_recipient_can_accept_or_reject_pending_request(self):
        repo = self.repository()
        accepted = service.respond_to_contact_request(repo, self.recipient, str(self.request_id), "accepted")
        self.assertEqual(accepted["status"], "accepted")
        rejected = service.respond_to_contact_request(repo, self.recipient, str(self.request_id), "rejected")
        self.assertEqual(rejected["status"], "rejected")
        with self.assertRaises(LookupError):
            service.respond_to_contact_request(repo, self.requester, str(self.request_id), "accepted")
        with self.assertRaises(LookupError):
            service.respond_to_contact_request(repo, self.requester, str(self.request_id), "rejected")

    def test_incoming_requests_are_safe_in_app_notifications(self):
        result = service.incoming_contact_requests(self.repository(), self.recipient)
        request = result["requests"][0]
        self.assertEqual(request["id"], str(self.request_id))
        self.assertEqual(request["requester"]["oui_vocal_id"], "requester")
        self.assertNotIn("email", request["requester"])


class ContactRequestRouteTests(unittest.TestCase):
    def setUp(self): self.client = app.test_client()

    def test_contact_request_routes_reject_unauthenticated_requests(self):
        request_id = str(uuid4())
        self.assertEqual(self.client.post("/identity/contact-requests", json={}).status_code, 401)
        self.assertEqual(self.client.get("/identity/contact-requests/incoming").status_code, 401)
        self.assertEqual(self.client.post(f"/identity/contact-requests/{request_id}/accept").status_code, 401)
        self.assertEqual(self.client.post(f"/identity/contact-requests/{request_id}/reject").status_code, 401)

    def test_authenticated_request_delegates_to_service(self):
        @contextmanager
        def fake_connection(): yield object()
        with (
            patch("routes.identity.connection", fake_connection),
            patch("routes.identity.decode_access_token", return_value=str(uuid4())),
            patch("routes.identity.identity_service.create_contact_request", return_value={"id": str(uuid4()), "status": "pending", "direction": "outgoing", "created": True}) as create,
        ):
            response = self.client.post("/identity/contact-requests", headers={"Authorization": "Bearer test"}, json={"user_id": str(uuid4())})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(create.call_count, 1)


if __name__ == "__main__": unittest.main()
