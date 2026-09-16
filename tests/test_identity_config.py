"""Dependency-free tests for identity secret configuration."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from identity.config import IdentityConfigurationError, jwt_secret


class JwtSecretConfigurationTests(unittest.TestCase):
    def test_reads_valid_secret_from_file_and_strips_trailing_whitespace(self):
        secret = "s" * 32
        with TemporaryDirectory() as directory:
            secret_file = Path(directory) / "jwt.secret"
            secret_file.write_text(f"{secret}\n\n", encoding="utf-8")
            with patch.dict(
                os.environ,
                {"OUIVOCAL_JWT_SECRET_FILE": str(secret_file)},
                clear=True,
            ):
                self.assertEqual(jwt_secret(), secret)

    def test_missing_secret_file_is_a_configuration_error(self):
        with patch.dict(
            os.environ,
            {"OUIVOCAL_JWT_SECRET_FILE": "/missing/ouivocal-jwt.secret"},
            clear=True,
        ):
            with self.assertRaisesRegex(IdentityConfigurationError, "file"):
                jwt_secret()

    def test_empty_secret_file_is_rejected(self):
        with TemporaryDirectory() as directory:
            secret_file = Path(directory) / "jwt.secret"
            secret_file.write_text("\n", encoding="utf-8")
            with patch.dict(
                os.environ,
                {"OUIVOCAL_JWT_SECRET_FILE": str(secret_file)},
                clear=True,
            ):
                with self.assertRaises(IdentityConfigurationError):
                    jwt_secret()

    def test_file_secret_must_meet_minimum_length(self):
        with TemporaryDirectory() as directory:
            secret_file = Path(directory) / "jwt.secret"
            secret_file.write_text("too-short\n", encoding="utf-8")
            with patch.dict(
                os.environ,
                {"OUIVOCAL_JWT_SECRET_FILE": str(secret_file)},
                clear=True,
            ):
                with self.assertRaises(IdentityConfigurationError):
                    jwt_secret()

    def test_file_secret_takes_precedence_over_direct_environment_value(self):
        file_secret = "f" * 32
        with TemporaryDirectory() as directory:
            secret_file = Path(directory) / "jwt.secret"
            secret_file.write_text(file_secret, encoding="utf-8")
            with patch.dict(
                os.environ,
                {
                    "OUIVOCAL_JWT_SECRET_FILE": str(secret_file),
                    "OUIVOCAL_JWT_SECRET": "e" * 32,
                },
                clear=True,
            ):
                self.assertEqual(jwt_secret(), file_secret)

    def test_direct_environment_secret_remains_supported(self):
        secret = "e" * 32
        with patch.dict(
            os.environ,
            {"OUIVOCAL_JWT_SECRET": secret},
            clear=True,
        ):
            self.assertEqual(jwt_secret(), secret)


if __name__ == "__main__":
    unittest.main()
