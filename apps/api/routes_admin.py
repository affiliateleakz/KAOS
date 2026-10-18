from fastapi import APIRouter, HTTPException, Depends, Request
from db import db, new_id, now, now_iso, clean
from auth import require_role, get_current_user, ROLE_RANK
from services import audit_log, set_setting, get_setting, notify
from models import RoleReq, PlanReq, SettingsReq
from datetime import timedelta

router = APIRouter(prefix="/api/admin", tags=["admin"])
admin_dep = require_role("admin")
mod_dep = require_role("moderator")


@router.get("/export/source.zip")
async def export_source(admin: dict = Depends(admin_dep)):
    """Stream a .zip of the full project source (backend + frontend + extension + docs).
    Secrets (.env*) and heavy/generated dirs are excluded."""
    import io
    import os as _os
    import zipfile
    from fastapi.responses import StreamingResponse
    base = "/app"
    roots = ["backend", "frontend/src", "frontend/public", "extension", "memory", "scripts"]
    single = ["frontend/package.json", "frontend/tailwind.config.js", "frontend/craco.config.js",
              "frontend/postcss.config.js", "frontend/jsconfig.json", "frontend/yarn.lock"]
    excl_dirs = {"node_modules", "__pycache__", ".git", "build", "dist", ".venv", "venv",
                 ".pytest_cache", ".emergent", "test_reports"}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for root in roots:
            abs_root = _os.path.join(base, root)
            if not _os.path.isdir(abs_root):
                continue
            for dp, dns, fns in _os.walk(abs_root):
                dns[:] = [d for d in dns if d not in excl_dirs]
                for fn in fns:
                    if fn.startswith(".env") or fn.endswith((".pyc", ".map")):
                        continue
                    fp = _os.path.join(dp, fn)
                    z.write(fp, arcname=_os.path.join("kaos-trading", _os.path.relpath(fp, base)))
        for f in single:
            fp = _os.path.join(base, f)
            if _os.path.isfile(fp):
                z.write(fp, arcname=_os.path.join("kaos-trading", f))
        for fn in _os.listdir(base):
            if fn.endswith(".md"):
                z.write(_os.path.join(base, fn), arcname=_os.path.join("kaos-trading", fn))
    buf.seek(0)
    await audit_log(admin, "export_source", "system", "source.zip")
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": "attachment; filename=kaos-trading-source.zip"})


@router.get("/dashboard")
async def admin_dashboard(admin: dict = Depends(admin_dep)):
    from routes_billing import get_plans
    total = await db.users.count_documents({})
    active = await db.users.count_documents({"membership_status": "ACTIVE"})
    trial = await db.users.count_documents({"membership_status": "TRIAL"})
    canceled = await db.users.count_documents({"membership_status": "CANCELED"})
    past_due = await db.users.count_documents({"membership_status": "PAST_DUE"})
    suspended = await db.users.count_documents({"account_status": "suspended"})
    aff_pending = await db.users.count_documents({"affiliate_status": "PENDING"})
    aff_verified = await db.users.count_documents({"affiliate_status": "VERIFIED"})
    published = await db.strategies.count_documents({"published": True})
    open_reports = await db.reports.count_documents({"status": "open"})
    week_ago = (now() - timedelta(days=7)).isoformat()
    new_members = await db.users.count_documents({"created_at": {"$gt": week_ago}})
    # ---- Revenue (MRR) normalized to a monthly figure from real membership state ----
    # Prefer Stripe subscription records when present; otherwise derive from active/trial members
    # and their plan's monthly-equivalent price (yearly amortized /12).
    plans = await get_plans()
    plan_by_id = {p["id"]: p for p in plans}
    plan_by_lookup = {p.get("lookup_key"): p for p in plans}

    def _monthly(amount_cents, interval):
        m = (amount_cents or 0) / 100.0
        return m / 12.0 if interval == "year" else m

    default_month = next((p for p in plans if p.get("interval") == "month"),
                         (plans[0] if plans else {"id": "monthly", "name": "Monthly", "amount": 2900, "interval": "month"}))
    member_plan_counts = {}
    async for u in db.users.find({"membership_status": {"$in": ["ACTIVE", "TRIAL"]}}, {"membership_plan": 1}):
        pid = u.get("membership_plan") or default_month["id"]
        member_plan_counts[pid] = member_plan_counts.get(pid, 0) + 1
    plan_mix = []
    for pid, cnt in member_plan_counts.items():
        p = plan_by_id.get(pid) or default_month
        plan_mix.append({"planId": pid, "name": p.get("name", pid), "count": cnt,
                         "monthlyRevenue": round(_monthly(p.get("amount"), p.get("interval")) * cnt, 2)})
    plan_mix.sort(key=lambda x: -x["monthlyRevenue"])

    subs = await db.subscriptions.find({"state": "active"}).to_list(2000)
    if subs:
        mrr = sum(_monthly(s.get("amount"),
                           (plan_by_lookup.get(s.get("lookup_key")) or plan_by_id.get(s.get("planId")) or {}).get("interval", "month"))
                  for s in subs)
    else:
        mrr = sum(pm["monthlyRevenue"] for pm in plan_mix)
    mrr = round(mrr, 2)
    # ---- Affiliate commissions payable + confirmed trades (real business signal) ----
    payable_agg = await db.commissions.aggregate([
        {"$match": {"status": {"$in": ["APPROVED", "PAYABLE"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}]).to_list(1)
    commissions_payable = round((payable_agg[0]["total"] if payable_agg else 0) or 0, 2)
    confirmed_trades = await db.trades.count_documents(
        {"state": {"$in": ["BROKER_CONFIRMED", "TRADE_OPEN", "TRADE_RESULT"]}})
    # extension version distribution
    devices = await db.devices.find({"revoked": False}).to_list(2000)
    versions = {}
    for d in devices:
        v = d.get("extensionVersion") or "unknown"
        versions[v] = versions.get(v, 0) + 1
    return {"totalUsers": total, "activeMembers": active, "trial": trial, "canceled": canceled,
            "pastDue": past_due, "suspended": suspended, "affiliatePending": aff_pending,
            "affiliateVerified": aff_verified, "publishedStrategies": published,
            "openReports": open_reports, "newMembers": new_members, "revenueMRR": mrr,
            "commissionsPayable": commissions_payable, "confirmedTrades": confirmed_trades,
            "planMix": plan_mix, "extensionVersions": versions}


@router.get("/users")
async def admin_users(q: str = "", status: str = "", admin: dict = Depends(admin_dep)):
    query = {}
    if q:
        query["$or"] = [{"email": {"$regex": q, "$options": "i"}}, {"username": {"$regex": q, "$options": "i"}}, {"name": {"$regex": q, "$options": "i"}}]
    if status:
        query["membership_status"] = status
    docs = await db.users.find(query, {"_id": 0, "password_hash": 0, "verify_token": 0}).sort("created_at", -1).to_list(500)
    return docs


@router.get("/users/{uid}")
async def admin_user_detail(uid: str, admin: dict = Depends(admin_dep)):
    u = await db.users.find_one({"id": uid}, {"_id": 0, "password_hash": 0, "verify_token": 0})
    if not u:
        raise HTTPException(status_code=404, detail="Not found")
    u["devices"] = await db.devices.find({"userId": uid}, {"_id": 0}).to_list(100)
    u["strategies"] = await db.strategies.count_documents({"ownerUserId": uid})
    u["subscriptions"] = await db.subscriptions.find({"userId": uid}, {"_id": 0}).to_list(50)
    return u


async def _set_user(uid, updates, admin, action, meta=None):
    updates["updated_at"] = now_iso()
    res = await db.users.update_one({"id": uid}, {"$set": updates})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Not found")
    await audit_log(admin, action, "user", uid, meta or updates)
    return await db.users.find_one({"id": uid}, {"_id": 0, "password_hash": 0, "verify_token": 0})


@router.post("/users/{uid}/suspend")
async def suspend(uid: str, admin: dict = Depends(admin_dep)):
    return await _set_user(uid, {"account_status": "suspended"}, admin, "suspend_user")


@router.post("/users/{uid}/unsuspend")
async def unsuspend(uid: str, admin: dict = Depends(admin_dep)):
    return await _set_user(uid, {"account_status": "active"}, admin, "unsuspend_user")


@router.post("/users/{uid}/revoke-access")
async def revoke_access(uid: str, admin: dict = Depends(admin_dep)):
    return await _set_user(uid, {"extension_access_revoked": True}, admin, "revoke_extension_access")


@router.post("/users/{uid}/restore-access")
async def restore_access(uid: str, admin: dict = Depends(admin_dep)):
    return await _set_user(uid, {"extension_access_revoked": False}, admin, "restore_extension_access")


@router.post("/users/{uid}/force-logout")
async def force_logout(uid: str, admin: dict = Depends(admin_dep)):
    await db.users.update_one({"id": uid}, {"$inc": {"token_version": 1}})
    await db.sessions.delete_many({"user_id": uid})
    await audit_log(admin, "force_logout", "user", uid)
    return {"ok": True}


@router.post("/users/{uid}/role")
async def change_role(uid: str, req: RoleReq, admin: dict = Depends(require_role("super_admin"))):
    if req.role not in ROLE_RANK:
        raise HTTPException(status_code=400, detail="Invalid role")
    return await _set_user(uid, {"role": req.role}, admin, "change_role", {"role": req.role})


@router.post("/users/{uid}/set-membership")
async def set_membership(uid: str, req: SettingsReq, admin: dict = Depends(admin_dep)):
    val = req.value
    updates = {"membership_status": val.get("status", "ACTIVE")}
    if val.get("status") == "ACTIVE":
        updates["membership_expires_at"] = (now() + timedelta(days=30)).isoformat()
        updates["membership_plan"] = val.get("plan", "monthly")
    return await _set_user(uid, updates, admin, "set_membership", val)


@router.post("/devices/{did}/revoke")
async def admin_revoke_device(did: str, admin: dict = Depends(admin_dep)):
    await db.devices.update_one({"id": did}, {"$set": {"revoked": True}})
    await audit_log(admin, "revoke_device", "device", did)
    return {"revoked": True}


@router.post("/users/{uid}/revoke-all-devices")
async def revoke_all_devices(uid: str, admin: dict = Depends(admin_dep)):
    await db.devices.update_many({"userId": uid}, {"$set": {"revoked": True}})
    await audit_log(admin, "revoke_all_devices", "user", uid)
    return {"ok": True}


@router.get("/devices")
async def admin_devices(admin: dict = Depends(admin_dep)):
    docs = await db.devices.find({}, {"_id": 0}).sort("lastActive", -1).to_list(1000)
    for d in docs:
        u = await db.users.find_one({"id": d["userId"]}, {"_id": 0, "username": 1, "email": 1})
        d["user"] = u
    return docs


# ---------- Affiliate queue ----------
@router.get("/affiliate")
async def admin_affiliate(admin: dict = Depends(admin_dep)):
    refs = await db.affiliate_referrals.find({}, {"_id": 0}).sort("createdAt", -1).to_list(500)
    for r in refs:
        u = await db.users.find_one({"id": r["userId"]}, {"_id": 0, "username": 1, "email": 1, "affiliate_status": 1})
        r["user"] = u
    return refs


@router.post("/affiliate/{uid}/approve")
async def approve_affiliate(uid: str, admin: dict = Depends(admin_dep)):
    await db.affiliate_referrals.update_one({"userId": uid}, {"$set": {"status": "VERIFIED", "updatedAt": now_iso()}})
    await db.users.update_one({"id": uid}, {"$set": {"affiliate_status": "VERIFIED", "onboarding_step": 5, "updated_at": now_iso()}})
    await notify(uid, "affiliate", "Your Pocket Option affiliate was verified. You can now proceed.", "/dashboard")
    await audit_log(admin, "affiliate_approve", "user", uid)
    return {"affiliateStatus": "VERIFIED"}


@router.post("/affiliate/{uid}/reject")
async def reject_affiliate(uid: str, admin: dict = Depends(admin_dep)):
    await db.affiliate_referrals.update_one({"userId": uid}, {"$set": {"status": "REJECTED", "updatedAt": now_iso()}})
    await db.users.update_one({"id": uid}, {"$set": {"affiliate_status": "REJECTED", "updated_at": now_iso()}})
    await notify(uid, "affiliate", "Your Pocket Option affiliate submission was rejected. Please resubmit.", "/dashboard")
    await audit_log(admin, "affiliate_reject", "user", uid)
    return {"affiliateStatus": "REJECTED"}


# ---------- Moderation ----------
@router.get("/reports")
async def admin_reports(mod: dict = Depends(mod_dep)):
    docs = await db.reports.find({}, {"_id": 0}).sort("createdAt", -1).to_list(500)
    return docs


@router.post("/reports/{rid}/action")
async def report_action(rid: str, req: SettingsReq, mod: dict = Depends(mod_dep)):
    action = req.value.get("action", "dismiss")
    report = await db.reports.find_one({"id": rid})
    if not report:
        raise HTTPException(status_code=404, detail="Not found")
    await db.reports.update_one({"id": rid}, {"$set": {"status": "resolved", "resolution": action, "updatedAt": now_iso()}})
    if action in ("hide", "remove") and report["targetType"] == "strategy":
        await db.strategies.update_one({"id": report["targetId"]}, {"$set": {"published": False, "visibility": "PRIVATE"}})
    if action in ("hide", "remove") and report["targetType"] == "comment":
        await db.comments.update_one({"id": report["targetId"]}, {"$set": {"hidden": True}})
    await db.moderation_actions.insert_one({"id": new_id("mod"), "reportId": rid, "moderatorId": mod["id"],
                                            "action": action, "createdAt": now_iso()})
    await audit_log(mod, f"moderation_{action}", report["targetType"], report["targetId"])
    return {"status": "resolved", "action": action}


# ---------- Strategies / catalog admin ----------
@router.get("/strategies")
async def admin_strategies(admin: dict = Depends(admin_dep)):
    return await db.strategies.find({}, {"_id": 0}).sort("updatedAt", -1).to_list(1000)


# ---------- Extension releases ----------
@router.get("/extension/releases")
async def list_releases(admin: dict = Depends(admin_dep)):
    return await db.extension_releases.find({}, {"_id": 0}).sort("createdAt", -1).to_list(100)


@router.post("/extension/releases")
async def create_release(req: SettingsReq, admin: dict = Depends(admin_dep)):
    v = req.value
    doc = {"id": new_id("rel"), "version": v.get("version"), "releaseNotes": v.get("releaseNotes", ""),
           "minSupportedVersion": v.get("minSupportedVersion", ""), "recommendedVersion": v.get("recommendedVersion", ""),
           "downloadUrl": v.get("downloadUrl", ""), "mandatory": v.get("mandatory", False),
           "published": v.get("published", True), "createdAt": now_iso()}
    await db.extension_releases.insert_one(dict(doc))
    await audit_log(admin, "create_release", "release", doc["id"], {"version": doc["version"]})
    return clean(doc)


# ---------- Settings (plans, affiliate, branding) ----------
@router.get("/settings")
async def get_settings(admin: dict = Depends(admin_dep)):
    plans = await get_setting("plans")
    affiliate = await get_setting("affiliate", {})
    branding = await get_setting("branding", {"productName": "Trading Platform"})
    from routes_billing import DEFAULT_PLANS
    return {"plans": plans or DEFAULT_PLANS, "affiliate": affiliate, "branding": branding}


@router.post("/settings")
async def update_settings(req: SettingsReq, admin: dict = Depends(admin_dep)):
    if req.key not in ("plans", "affiliate", "branding"):
        raise HTTPException(status_code=400, detail="Unknown setting")
    value = req.value.get("value", req.value)
    await set_setting(req.key, value)
    await audit_log(admin, "update_settings", "settings", req.key)
    return {"ok": True, "key": req.key}


# ---------- Audit ----------
@router.get("/audit")
async def audit(admin: dict = Depends(admin_dep)):
    return await db.admin_audit_logs.find({}, {"_id": 0}).sort("createdAt", -1).to_list(500)
