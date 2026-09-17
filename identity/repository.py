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

    def contact_between(self, first_user_id, second_user_id):
        low, high = canonical_pair(first_user_id, second_user_id)
        return self.one(
            "SELECT id, requester_user_id, addressee_user_id, relationship_status, accepted_at "
            "FROM contacts WHERE lower_user_id=%s AND higher_user_id=%s",
            (low, high),
        )

    def create_contact_request(self, requester_user_id, addressee_user_id):
        low, high = canonical_pair(requester_user_id, addressee_user_id)
        contact_id = new_id()
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO contacts("
                "id,lower_user_id,higher_user_id,requester_user_id,addressee_user_id,relationship_status"
                ") VALUES(%s,%s,%s,%s,%s,'pending') "
                "ON CONFLICT(lower_user_id,higher_user_id) DO NOTHING "
                "RETURNING id,requester_user_id,addressee_user_id,relationship_status,accepted_at",
                (contact_id, low, high, requester_user_id, addressee_user_id),
            )
            created = cursor.fetchone()
        if created:
            return created, True
        return self.contact_between(requester_user_id, addressee_user_id), False

    def respond_to_contact_request(self, contact_id, addressee_user_id, status):
        return self.one(
            "UPDATE contacts SET relationship_status=%s, "
            "accepted_at=CASE WHEN %s='accepted' THEN NOW() ELSE accepted_at END "
            "WHERE id=%s AND addressee_user_id=%s AND relationship_status='pending' "
            "RETURNING id,requester_user_id,addressee_user_id,relationship_status,accepted_at",
            (status, status, contact_id, addressee_user_id),
        )

    def pending_contact_requests_for(self, addressee_user_id):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT c.id AS contact_id,c.relationship_status,c.created_at,"
                "u.id,u.ouivocal_id,u.full_name,u.avatar_url,u.identity_verified_at "
                "FROM contacts c JOIN users u ON u.id=c.requester_user_id "
                "WHERE c.addressee_user_id=%s AND c.relationship_status='pending' "
                "AND u.account_status='active' ORDER BY c.created_at DESC,c.id",
                (addressee_user_id,),
            )
            return cursor.fetchall()

    def accepted_contact_exists(self, first_user_id, second_user_id):
        low, high = canonical_pair(first_user_id, second_user_id)
        return self.one(
            "SELECT id FROM contacts WHERE lower_user_id=%s AND higher_user_id=%s "
            "AND relationship_status='accepted'",
            (low, high),
        ) is not None

    def direct_conversations_for(self, user_id):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT c.id AS conversation_id,c.created_by_user_id,c.default_source_language,c.default_target_language,"
                "last_message.id AS last_message_id,last_message.original_text AS last_message,"
                "last_message.created_at AS last_message_at,"
                "u.id,u.ouivocal_id,u.full_name,u.avatar_url,u.identity_verified_at "
                "FROM conversation_members m JOIN conversations c ON c.id=m.conversation_id "
                "LEFT JOIN LATERAL (SELECT id,original_text,created_at FROM conversation_messages "
                "WHERE conversation_id=c.id ORDER BY created_at DESC,id DESC LIMIT 1) last_message ON TRUE "
                "JOIN users u ON u.id=CASE WHEN c.direct_lower_user_id=%s "
                "THEN c.direct_higher_user_id ELSE c.direct_lower_user_id END "
                "WHERE m.user_id=%s AND m.left_at IS NULL AND c.conversation_type='direct' "
                "AND u.account_status='active' ORDER BY c.updated_at DESC,c.id",
                (user_id, user_id),
            )
            return cursor.fetchall()

    def conversation_for_member(self, conversation_id, user_id):
        return self.one(
            "SELECT c.id,c.created_by_user_id,c.default_source_language,c.default_target_language "
            "FROM conversations c JOIN conversation_members m ON m.conversation_id=c.id "
            "WHERE c.id=%s AND m.user_id=%s AND m.left_at IS NULL",
            (conversation_id, user_id),
        )

    def conversation_messages_for_member(self, conversation_id, user_id, limit):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT message.id,message.sender_user_id,message.original_text,message.translated_text,"
                "message.source_language,message.target_language,message.created_at "
                "FROM conversation_messages message "
                "JOIN conversation_members member ON member.conversation_id=message.conversation_id "
                "WHERE message.conversation_id=%s AND member.user_id=%s AND member.left_at IS NULL "
                "ORDER BY message.created_at ASC,message.id ASC LIMIT %s",
                (conversation_id, user_id, limit),
            )
            return cursor.fetchall()

    def create_conversation_message(self, conversation_id, sender_user_id, original_text,
                                    translated_text, source_language, target_language):
        return self.one(
            "INSERT INTO conversation_messages("
            "id,conversation_id,sender_user_id,original_text,translated_text,source_language,target_language"
            ") VALUES(%s,%s,%s,%s,%s,%s,%s) "
            "RETURNING id,sender_user_id,original_text,translated_text,source_language,target_language,created_at",
            (new_id(), conversation_id, sender_user_id, original_text, translated_text,
             source_language, target_language),
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
                "SELECT id,created_by_user_id,default_source_language,default_target_language FROM conversations "
                "WHERE direct_lower_user_id=%s AND direct_higher_user_id=%s",
                (low, high),
            )
            existing = cursor.fetchone()
            if not existing:
                raise RuntimeError("Direct conversation was not created")
            return existing["id"], False, existing

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
