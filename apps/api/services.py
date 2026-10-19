from db import db, new_id, now_iso, clean

# Membership states that grant access
ACTIVE_MEMBERSHIP = {"TRIAL", "ACTIVE"}


async def get_setting(key: str, default=None):
    doc = await db.settings.find_one({"key": key})
    return doc["value"] if doc else default


async def set_setting(key: str, value):
    await db.settings.update_one({"key": key}, {"$set": {"key": key, "value": value}}, upsert=True)


LICENSE_REASON_MESSAGES = {
    "account_suspended": "Your KAOS account is suspended.",
    "account_banned": "Your KAOS account is banned.",
    "access_revoked": "Extension access was revoked for this account.",
    "device_revoked": "This device was revoked. Manage devices in your KAOS dashboard.",
}


async def compute_license(user: dict, device: dict = None, broker: str = "pocket_option") -> dict:
    """Server-authoritative license decision for a user (+ optional device) on a broker.

    Referral enrollment is optional. License access never depends on referral status.
    """
    reasons = []
    authorized = True
    status = user.get("account_status", "active")
    membership = user.get("membership_status", "EXPIRED")
    affiliate = user.get("affiliate_status", "NOT_STARTED")

    if status in ("suspended", "banned"):
        authorized = False
        reasons.append(f"account_{status}")
    if user.get("extension_access_revoked"):
        authorized = False
        reasons.append("access_revoked")
    # Free tier: no paid membership needed for the bot; AI and paid features are gated by entitlements.
    tier = "paid" if membership in ACTIVE_MEMBERSHIP else "free"
    if device is not None and device.get("revoked"):
        authorized = False
        reasons.append("device_revoked")

    features = []
    if authorized:
        features = ["strategy_cloud", "community", "sync", "backtests", "indicators"]

    return {
        "authorized": authorized,
        "membershipStatus": membership,
        "tier": tier,
        "affiliateStatus": affiliate,
        "userId": user.get("id"),
        "licenseId": user.get("license_id"),
        "serverTime": now_iso(),
        "expiresAt": user.get("membership_expires_at"),
        "features": features,
        "reasons": reasons,
        "reasonMessages": [LICENSE_REASON_MESSAGES.get(r, r) for r in reasons],
        "broker": broker,
        "brokerEligibility": {
            "pocket_option": {
                "eligible": True,
                "status": affiliate,
                "referralRequired": False,
            },
        },
    }


async def audit_log(actor: dict, action: str, target_type: str = None,
                    target_id: str = None, meta: dict = None):
    await db.admin_audit_logs.insert_one({
        "id": new_id("audit"),
        "actorId": actor.get("id") if actor else None,
        "actorEmail": actor.get("email") if actor else None,
        "action": action,
        "targetType": target_type,
        "targetId": target_id,
        "meta": meta or {},
        "createdAt": now_iso(),
    })


async def notify(user_id: str, ntype: str, message: str, link: str = None, actor: dict = None):
    await db.notifications.insert_one({
        "id": new_id("ntf"),
        "userId": user_id,
        "type": ntype,
        "message": message,
        "link": link,
        "actorId": actor.get("id") if actor else None,
        "actorName": actor.get("username") or actor.get("name") if actor else None,
        "read": False,
        "createdAt": now_iso(),
    })


def public_user(user: dict) -> dict:
    """Safe public projection of a user/profile."""
    if not user:
        return None
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "name": user.get("name"),
        "displayName": user.get("name") or user.get("username"),
        "avatar": user.get("avatar"),
        "bio": user.get("bio"),
        "joinDate": user.get("created_at"),
    }
