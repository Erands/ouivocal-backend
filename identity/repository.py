"""Inactive psycopg 3 repository; callers provide an already-open transaction."""

from identity.models import canonical_pair, new_id


class Repository:
    def __init__(self, conn):
        self.conn = conn

    def one(self, sql, args=()):
        with self.conn.cursor() as cursor:
            cursor.execute(sql, args)
            return cursor.fetchone()

    def execute(self, sql, args=()):
        with self.conn.cursor() as cursor:
            cursor.execute(sql, args)
            return cursor.rowcount

    def user(self, user_id):
        return self.one(
            "SELECT * FROM users WHERE id=%s AND account_status='active'", (user_id,)
        )

    def by_email(self, email):
        return self.one("SELECT * FROM users WHERE email_normalized=%s", (email,))

    def by_oui(self, oui):
        return self.one("SELECT * FROM users WHERE ouivocal_id_normalized=%s", (oui,))

    def search_public_users(self, query, current_user_id, limit):
        """Search only public directory fields; never select private identity data."""
        pattern = f"%{query}%"
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, ouivocal_id, full_name, avatar_url, identity_verified_at "
                "FROM users "
                "WHERE account_status='active' AND id <> %s "
                "AND (ouivocal_id ILIKE %s OR full_name ILIKE %s) "
                "ORDER BY lower(ouivocal_id), id "
                "LIMIT %s",
                (current_user_id, pattern, pattern, limit),
            )
            return cursor.fetchall()

    def public_active_user(self, user_id):
        return self.one(
            "SELECT id, ouivocal_id, full_name, avatar_url, identity_verified_at "
            "FROM users WHERE id=%s AND account_status='active'",
            (user_id,),
        )

    def direct_with_preferences(self, creator, other, source_language, target_language):
        """Return the canonical direct conversation, creating it atomically if absent."""
        low, high = canonical_pair(creator, other)
        conversation_id = new_id()
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO conversations("
                "id,created_by_user_id,direct_lower_user_id,direct_higher_user_id,"
                "default_source_language,default_target_language"
                ") VALUES(%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT(direct_lower_user_id,direct_higher_user_id) DO NOTHING "
                "RETURNING id",
                (conversation_id, creator, low, high, source_language, target_language),
            )
            created = cursor.fetchone()
            if created:
                cursor.execute(
                    "INSERT INTO conversation_members(id,conversation_id,user_id,member_role) "
                    "VALUES(%s,%s,%s,'owner'),(%s,%s,%s,'member')",
                    (new_id(), conversation_id, creator, new_id(), conversation_id, other),
                )
                return created["id"], True

            cursor.execute(
                "SELECT id FROM conversations "
                "WHERE direct_lower_user_id=%s AND direct_higher_user_id=%s",
                (low, high),
            )
            existing = cursor.fetchone()
            if not existing:
                raise RuntimeError("Direct conversation was not created")
            return existing["id"], False

    def create_user(self, values):
        user_id = new_id()
        self.one(
            "INSERT INTO users(id,ouivocal_id,ouivocal_id_normalized,email,email_normalized,password_hash,full_name) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (
                user_id,
                values["ouivocal_id"],
                values["oui"],
                values["email"],
                values["email_norm"],
                values["password_hash"],
                values["full_name"],
            ),
        )
        return user_id

    def direct(self, creator, other):
        low, high = canonical_pair(creator, other)
        old = self.one(
            "SELECT id FROM conversations WHERE direct_lower_user_id=%s AND direct_higher_user_id=%s",
            (low, high),
        )
        if old:
            return old["id"]

        conversation_id = new_id()
        self.execute(
            "INSERT INTO conversations(id,created_by_user_id,direct_lower_user_id,direct_higher_user_id) "
            "VALUES(%s,%s,%s,%s)",
            (conversation_id, creator, low, high),
        )
        self.execute(
            "INSERT INTO conversation_members(id,conversation_id,user_id,member_role) "
            "VALUES(%s,%s,%s,'owner'),(%s,%s,%s,'member')",
            (new_id(), conversation_id, creator, new_id(), conversation_id, other),
        )
        return conversation_id

    def token(self, digest):
        return self.one("SELECT * FROM refresh_tokens WHERE token_digest=%s", (digest,))

    def revoke_family(self, family):
        return self.execute(
            "UPDATE refresh_tokens SET revoked_at=NOW(),reuse_detected_at=NOW() "
            "WHERE token_family_id=%s AND revoked_at IS NULL",
            (family,),
        )
