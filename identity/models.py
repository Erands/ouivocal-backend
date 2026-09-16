from uuid import UUID, uuid4

def new_id() -> UUID: return uuid4()
def canonical_pair(a: UUID, b: UUID) -> tuple[UUID, UUID]:
    if a == b: raise ValueError('Two distinct users are required')
    return (a, b) if a.int < b.int else (b, a)
def validate_blocked_by(low: UUID, high: UUID, status: str, blocker: UUID | None) -> None:
    if status == 'blocked' and blocker not in (low, high): raise ValueError('Blocker must be a participant')
    if status != 'blocked' and blocker is not None: raise ValueError('Only blocked contacts have a blocker')
def public_search_result(row: dict) -> dict:
    """The deliberately small public directory representation of a user."""
    return {
        "id": str(row["id"]) if row.get("id") is not None else None,
        "oui_vocal_id": row.get("ouivocal_id"),
        # The current schema has no username column. Keep the mobile contract
        # stable without deriving a second identity from private data.
        "username": None,
        "display_name": row.get("full_name"),
        "profile_photo_url": row.get("avatar_url"),
        "is_verified": row.get("identity_verified_at") is not None,
        # Language preferences are private in the current schema.
        "languages": [],
    }
def public_profile(row: dict) -> dict: return public_search_result(row) | {k: row.get(k) for k in ('bio','location','created_at','last_seen_at')}
def current_user_profile(row: dict) -> dict: return public_profile(row) | {k: row.get(k) for k in ('id','email','phone_e164','email_verified_at','phone_verified_at','account_status','updated_at')}
