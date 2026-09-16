import unittest

from identity.models import canonical_pair, current_user_profile, new_id, validate_blocked_by
from identity.security import issue_refresh_token, token_digest
from identity.validation import ValidationError, normalize_email, normalize_ouivocal_id, require_language, require_password
from uuid import uuid4


class IdentityValidationTests(unittest.TestCase):
    def test_ouivocal_id_is_case_insensitive_for_lookup(self):
        self.assertEqual(normalize_ouivocal_id("Oui_Vocal9"), "oui_vocal9")

    def test_ouivocal_id_rejects_invalid_characters(self):
        with self.assertRaises(ValidationError):
            normalize_ouivocal_id("not allowed")

    def test_only_official_languages_are_accepted(self):
        self.assertEqual(require_language("ru", "spoken_language"), "ru")
        with self.assertRaises(ValidationError):
            require_language("pt", "spoken_language")

    def test_uuid_email_password_and_token_digest(self):
        self.assertNotEqual(new_id(), new_id())
        self.assertEqual(normalize_email(' User@Example.COM '), 'user@example.com')
        with self.assertRaises(ValidationError): require_password('short')
        token, digest, _, token_id, family_id = issue_refresh_token(str(uuid4()))
        self.assertEqual(token_digest(token), digest); self.assertNotEqual(token_id, family_id)

    def test_contact_pair_and_public_privacy(self):
        low, high = canonical_pair(uuid4(), uuid4()); self.assertLess(low.int, high.int)
        with self.assertRaises(ValueError): validate_blocked_by(low, high, 'blocked', uuid4())
        self.assertNotIn('password_hash', current_user_profile({'password_hash':'x','email':'a@b.co'}))


if __name__ == "__main__":
    unittest.main()
