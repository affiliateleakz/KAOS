"""KAOS Affiliate system: accounts, attribution, commissions (admin-configurable), payouts, marketing."""
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends, Request
from db import db, new_id, now, now_iso, clean
from auth import get_current_user, require_role
from services import get_setting, set_setting, audit_log
from datetime import timedelta

aff = APIRouter(prefix="/api/affiliate", tags=["affiliate"])
aff_admin = APIRouter(prefix="/api/admin", tags=["affiliate-admin"])
public = APIRouter(prefix="/api/aff", tags=["affiliate-public"])
admin_dep = require_role("admin")

DEFAULT_PROGRAM = {
    "enabled": True, "defaultRatePct": 30, "commissionType": "percentage", "recurring": True,
    "attributionWindowDays": 30, "holdDays": 30, "minPayout": 50,
    "perPlan": {},  # {planId: {ratePct, type, recurring}}
}


async def get_program():
    return await get_setting("affiliate_program", DEFAULT_PROGRAM)


def _code(user):
    return (user.get("username") or user.get("id"))[:16].upper()


@aff.post("/activate")
async def activate(user: dict = Depends(get_current_user)):
    acc = await db.affiliate_accounts.find_one({"userId": user["id"]})
    if acc:
        return clean(acc)
    doc = {"id": new_id("affacc"), "userId": user["id"], "code": _code(user),
           "status": "active", "createdAt": now_iso()}
    await db.affiliate_accounts.insert_one(dict(doc))
    return clean(doc)


@aff.get("/overview")
async def overview(request: Request, user: dict = Depends(get_current_user)):
    acc = await db.affiliate_accounts.find_one({"userId": user["id"]}, {"_id": 0})
    if not acc:
        return {"active": False}
    code = acc["code"]
    origin = request.headers.get("origin") or "https://TradeWithKAOS.com"
    comms = await db.commissions.find({"affiliateUserId": user["id"]}, {"_id": 0}).sort("createdAt", -1).to_list(200)

    def sum_status(s):
        return round(sum(c["amount"] for c in comms if c["status"] == s), 2)
    refs = await db.affiliate_customer_referrals.find({"affiliateUserId": user["id"]}, {"_id": 0}).sort("createdAt", -1).to_list(100)
    clicks = await db.affiliate_clicks.count_documents({"code": code})
    share_clicks = await db.affiliate_clicks.count_documents({"code": code, "campaign": "signal_share"})
    shares_created = await db.signal_shares.count_documents({"userId": user["id"]})
    signups = len(refs)
    paying = len([r for r in refs if r.get("converted")])
    return {
        "active": True, "code": code, "referralLink": f"{origin}/?ref={code}",
        "clicks": clicks, "signups": signups, "payingReferrals": paying,
        "conversionRate": round((paying / clicks) * 100, 2) if clicks else 0,
        "shareFunnel": {"shares": shares_created, "clicks": share_clicks, "signups": signups,
                        "paying": paying,
                        "clickToSignup": round((signups / share_clicks) * 100, 1) if share_clicks else 0,
                        "signupToPaying": round((paying / signups) * 100, 1) if signups else 0},
        "pending": sum_status("PENDING"), "approved": sum_status("APPROVED"),
        "payable": sum_status("PAYABLE"), "paid": sum_status("PAID"),
        "lifetime": round(sum(c["amount"] for c in comms if c["status"] != "REVERSED"), 2),
        "recentReferrals": refs[:20], "recentCommissions": comms[:20],
    }


@aff.get("/my-rank")
async def my_rank(user: dict = Depends(get_current_user)):
    """Lightweight leaderboard position for the current user (for a dashboard-home badge)."""
    mine = await db.affiliate_customer_referrals.count_documents({"affiliateUserId": user["id"], "converted": True})
    if mine == 0:
        return {"ranked": False, "paying": 0}
    rows = await db.affiliate_customer_referrals.aggregate([
        {"$match": {"converted": True}},
        {"$group": {"_id": "$affiliateUserId", "paying": {"$sum": 1}}}]).to_list(1000)
    ahead = sum(1 for r in rows if r["paying"] > mine)
    return {"ranked": True, "rank": ahead + 1, "paying": mine, "totalAffiliates": len(rows)}


@aff.get("/marketing")
async def member_marketing(user: dict = Depends(get_current_user)):
    return await db.marketing_assets.find({"published": True}, {"_id": 0}).sort("createdAt", -1).to_list(100)


@aff.get("/leaderboard")
async def leaderboard(user: dict = Depends(get_current_user)):
    """Top affiliates ranked by paying (converted) referrals — friendly competition for sharers."""
    rows = await db.affiliate_customer_referrals.aggregate([
        {"$match": {"converted": True}},
        {"$group": {"_id": "$affiliateUserId", "paying": {"$sum": 1}}},
        {"$sort": {"paying": -1}}, {"$limit": 10}]).to_list(10)
    out = []
    for i, r in enumerate(rows):
        uid = r["_id"]
        u = await db.users.find_one({"id": uid}, {"_id": 0, "username": 1, "name": 1})
        signups = await db.affiliate_customer_referrals.count_documents({"affiliateUserId": uid})
        comms = await db.commissions.find({"affiliateUserId": uid, "status": {"$ne": "REVERSED"}},
                                          {"_id": 0, "amount": 1}).to_list(1000)
        earned = round(sum(c["amount"] for c in comms), 2)
        name = (u or {}).get("username") or (u or {}).get("name") or f"Trader-{str(uid)[-4:]}"
        out.append({"rank": i + 1, "name": name, "paying": r["paying"], "signups": signups,
                    "earned": earned, "isYou": uid == user["id"]})
    return out


@public.get("/track")
async def track_click(ref: str, request: Request, campaign: Optional[str] = None):
    acc = await db.affiliate_accounts.find_one({"code": ref})
    if acc:
        await db.affiliate_clicks.insert_one({"id": new_id("clk"), "code": ref, "campaign": campaign,
                                              "ip": request.client.host if request.client else None, "createdAt": now_iso()})
    return {"ok": True}


# ---- commission engine (called from billing on activation / refund) ----
async def record_commission(customer_user: dict, plan: dict, event: str = "purchase"):
    code = customer_user.get("referredByCode")
    if not code:
        return
    acc = await db.affiliate_accounts.find_one({"code": code})
    if not acc or acc["userId"] == customer_user["id"]:
        return
    prog = await get_program()
    if not prog.get("enabled"):
        return
    per = (prog.get("perPlan") or {}).get(plan["id"], {})
    rate = per.get("ratePct", prog["defaultRatePct"])
    ctype = per.get("type", prog["commissionType"])
    amount = round(plan["amount"] / 100 * rate / 100, 2) if ctype == "percentage" else float(rate)
    hold = prog.get("holdDays", 30)
    await db.commissions.insert_one({
        "id": new_id("comm"), "affiliateUserId": acc["userId"], "customerUserId": customer_user["id"],
        "planId": plan["id"], "amount": amount, "rate": rate, "type": ctype, "event": event,
        "status": "PENDING", "holdReleaseAt": (now() + timedelta(days=hold)).isoformat(),
        "createdAt": now_iso()})
    await db.affiliate_customer_referrals.update_one(
        {"affiliateUserId": acc["userId"], "customerUserId": customer_user["id"]},
        {"$set": {"id": new_id("cref"), "affiliateUserId": acc["userId"], "customerUserId": customer_user["id"],
                  "converted": True, "planId": plan["id"], "createdAt": now_iso()}}, upsert=True)


async def reverse_commission(customer_user_id: str, reason: str = "refund"):
    await db.commissions.update_many(
        {"customerUserId": customer_user_id, "status": {"$in": ["PENDING", "APPROVED", "PAYABLE"]}},
        {"$set": {"status": "REVERSED", "reversalReason": reason, "updatedAt": now_iso()}})


# ---- admin ----
@aff_admin.get("/affiliates")
async def admin_affiliates(admin: dict = Depends(admin_dep)):
    accs = await db.affiliate_accounts.find({}, {"_id": 0}).to_list(500)
    for a in accs:
        u = await db.users.find_one({"id": a["userId"]}, {"_id": 0, "email": 1, "username": 1})
        a["user"] = u
        a["referrals"] = await db.affiliate_customer_referrals.count_documents({"affiliateUserId": a["userId"]})
    return accs


@aff_admin.get("/commissions")
async def admin_commissions(admin: dict = Depends(admin_dep)):
    return await db.commissions.find({}, {"_id": 0}).sort("createdAt", -1).to_list(500)


class CommActionReq(BaseModel):
    status: str


@aff_admin.post("/commissions/{cid}/status")
async def set_commission_status(cid: str, req: CommActionReq, admin: dict = Depends(admin_dep)):
    if req.status not in ("PENDING", "APPROVED", "PAYABLE", "PAID", "REVERSED"):
        raise HTTPException(status_code=400, detail="Invalid status")
    await db.commissions.update_one({"id": cid}, {"$set": {"status": req.status, "updatedAt": now_iso()}})
    await audit_log(admin, "commission_status", "commission", cid, {"status": req.status})
    return {"ok": True}


@aff_admin.get("/affiliate-program")
async def get_program_admin(admin: dict = Depends(admin_dep)):
    return await get_program()


@aff_admin.post("/affiliate-program")
async def set_program_admin(req: dict, admin: dict = Depends(admin_dep)):
    await set_setting("affiliate_program", req)
    await audit_log(admin, "update_affiliate_program", "settings", "affiliate_program")
    return {"ok": True}


class MarketingReq(BaseModel):
    title: str
    type: str = "banner"
    url: Optional[str] = ""
    copy: Optional[str] = ""
    published: bool = True


@aff_admin.get("/marketing-assets")
async def list_marketing(admin: dict = Depends(admin_dep)):
    return await db.marketing_assets.find({}, {"_id": 0}).sort("createdAt", -1).to_list(200)


@aff_admin.post("/marketing-assets")
async def add_marketing(req: MarketingReq, admin: dict = Depends(admin_dep)):
    doc = {"id": new_id("mkt"), **req.model_dump(), "createdAt": now_iso()}
    await db.marketing_assets.insert_one(dict(doc))
    await audit_log(admin, "add_marketing_asset", "marketing", doc["id"])
    return clean(doc)


@aff_admin.get("/payouts")
async def list_payouts(admin: dict = Depends(admin_dep)):
    return await db.payouts.find({}, {"_id": 0}).sort("createdAt", -1).to_list(200)
