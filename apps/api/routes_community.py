from fastapi import APIRouter, HTTPException, Depends
from db import db, new_id, now_iso, clean
from auth import get_current_user, get_optional_user
from services import public_user, notify
from models import CommentReq, ReportReq
from pymongo.errors import DuplicateKeyError
from hashlib import sha256

router = APIRouter(prefix="/api/community", tags=["community"])
social = APIRouter(prefix="/api", tags=["social"])


async def _enrich(s, user_id=None):
    s = clean(dict(s))
    owner = await db.users.find_one({"id": s["ownerUserId"]})
    s["owner"] = public_user(owner)
    if user_id:
        s["liked"] = bool(await db.strategy_likes.find_one({"strategyId": s["id"], "userId": user_id}))
        s["saved"] = bool(await db.strategy_saves.find_one({"strategyId": s["id"], "userId": user_id}))
    return s


@router.get("/strategies")
async def community_list(sort: str = "popular", user: dict = Depends(get_optional_user)):
    q = {"published": True, "visibility": "PUBLIC"}
    sort_map = {"newest": [("publishedAt", -1)], "popular": [("likesCount", -1)],
                "saved": [("savesCount", -1)], "updated": [("updatedAt", -1)]}
    docs = await db.strategies.find(q, {"_id": 0}).sort(sort_map.get(sort, [("likesCount", -1)])).to_list(200)
    uid = user["id"] if user else None
    return [await _enrich(d, uid) for d in docs]


@router.get("/strategies/{sid}")
async def community_detail(sid: str, user: dict = Depends(get_optional_user)):
    s = await db.strategies.find_one({"id": sid})
    if not s or not s.get("published") or s.get("visibility")!="PUBLIC":
        raise HTTPException(status_code=404, detail="Not found")
    out = await _enrich(s, user["id"] if user else None)
    out["versions"] = await db.strategy_versions.find({"strategyId": sid}, {"_id": 0}).sort("version", -1).to_list(100)
    comments = await db.comments.find({"targetType": "strategy", "targetId": sid, "hidden": {"$ne": True}}, {"_id": 0}).sort("createdAt", 1).to_list(500)
    for c in comments:
        au = await db.users.find_one({"id": c["authorId"]})
        c["author"] = public_user(au)
    out["comments"] = comments
    return out


@router.post("/strategies/{sid}/like")
async def like(sid: str, user: dict = Depends(get_current_user)):
    s = await db.strategies.find_one({"id": sid})
    if not s or not s.get("published") or s.get("visibility")!="PUBLIC":
        raise HTTPException(status_code=404, detail="Not found")
    if await db.strategy_likes.find_one({"strategyId": sid, "userId": user["id"]}):
        return {"liked": True}
    await db.strategy_likes.insert_one({"id": new_id("like"), "strategyId": sid, "userId": user["id"], "createdAt": now_iso()})
    await db.strategies.update_one({"id": sid}, {"$inc": {"likesCount": 1}})
    if s["ownerUserId"] != user["id"]:
        await notify(s["ownerUserId"], "strategy_liked", f"{user.get('username')} liked {s['name']}", f"/community/{sid}", user)
    return {"liked": True}


@router.delete("/strategies/{sid}/like")
async def unlike(sid: str, user: dict = Depends(get_current_user)):
    res = await db.strategy_likes.delete_one({"strategyId": sid, "userId": user["id"]})
    if res.deleted_count:
        await db.strategies.update_one({"id": sid}, {"$inc": {"likesCount": -1}})
    return {"liked": False}


@router.post("/strategies/{sid}/save")
async def save(sid: str, user: dict = Depends(get_current_user)):
    s = await db.strategies.find_one({"id": sid})
    if not s or not s.get("published") or s.get("visibility")!="PUBLIC":
        raise HTTPException(status_code=404, detail="Not found")
    if not await db.strategy_saves.find_one({"strategyId": sid, "userId": user["id"]}):
        await db.strategy_saves.insert_one({"id": new_id("save"), "strategyId": sid, "userId": user["id"], "createdAt": now_iso()})
        await db.strategies.update_one({"id": sid}, {"$inc": {"savesCount": 1}})
    # Add to library = installation association pinned to a version
    if not await db.strategy_installations.find_one({"strategyId": sid, "userId": user["id"]}):
        await db.strategy_installations.insert_one({"id": new_id("inst"), "strategyId": sid, "userId": user["id"],
                                                    "installedVersion": s["version"], "createdAt": now_iso()})
    return {"saved": True}


@router.delete("/strategies/{sid}/save")
async def unsave(sid: str, user: dict = Depends(get_current_user)):
    res = await db.strategy_saves.delete_one({"strategyId": sid, "userId": user["id"]})
    if res.deleted_count:
        await db.strategies.update_one({"id": sid}, {"$inc": {"savesCount": -1}})
    await db.strategy_installations.delete_one({"strategyId": sid, "userId": user["id"]})
    return {"saved": False}


@router.post("/strategies/{sid}/fork")
async def fork(sid: str, user: dict = Depends(get_current_user)):
    s = await db.strategies.find_one({"id": sid})
    if not s or not s.get("published") or s.get("visibility")!="PUBLIC":
        raise HTTPException(status_code=404, detail="Not found")
    fork_doc = {
        "id": new_id("strat"), "ownerUserId": user["id"], "ownerUsername": user.get("username"),
        "name": f"{s['name']} (fork)", "description": s.get("description"), "version": 1,
        "type": "CUSTOM", "editable": True, "locked": False, "visibility": "PRIVATE",
        "engineType": s.get("engineType"), "signalTimeframe": s.get("signalTimeframe"), "expiry": s.get("expiry"),
        "indicators": s.get("indicators"), "indicatorSettings": s.get("indicatorSettings"),
        "rules": s.get("rules"), "parameters": s.get("parameters"), "tags": s.get("tags"), "category": s.get("category"),
        "published": False, "publishedAt": None,
        "forkedFromStrategyId": s["id"], "forkedFromVersion": s["version"],
        "likesCount": 0, "savesCount": 0, "forksCount": 0, "commentsCount": 0,
        "createdAt": now_iso(), "updatedAt": now_iso(),
    }
    await db.strategies.insert_one(dict(fork_doc))
    await db.strategy_versions.insert_one({"id": new_id("sv"), "strategyId": fork_doc["id"], "version": 1,
                                           "name": fork_doc["name"], "changelog": f"Forked from {s['name']} v{s['version']}",
                                           "indicators": s.get("indicators"), "rules": s.get("rules"),
                                           "parameters": s.get("parameters"), "createdAt": now_iso()})
    await db.strategies.update_one({"id": sid}, {"$inc": {"forksCount": 1}})
    if s["ownerUserId"] != user["id"]:
        await notify(s["ownerUserId"], "strategy_forked", f"{user.get('username')} forked {s['name']}", f"/community/{sid}", user)
    return clean(fork_doc)


@router.post("/strategies/{sid}/comment")
async def comment(sid: str, req: CommentReq, user: dict = Depends(get_current_user)):
    s = await db.strategies.find_one({"id": sid})
    if not s or not s.get("published") or s.get("visibility")!="PUBLIC":
        raise HTTPException(status_code=404, detail="Not found")
    doc = {"id": new_id("cmt"), "targetType": "strategy", "targetId": sid, "authorId": user["id"],
           "body": req.body, "parentId": req.parentId, "hidden": False, "createdAt": now_iso()}
    await db.comments.insert_one(dict(doc))
    await db.strategies.update_one({"id": sid}, {"$inc": {"commentsCount": 1}})
    if s["ownerUserId"] != user["id"]:
        await notify(s["ownerUserId"], "strategy_commented", f"{user.get('username')} commented on {s['name']}", f"/community/{sid}", user)
    if req.parentId:
        parent = await db.comments.find_one({"id": req.parentId})
        if parent and parent["authorId"] != user["id"]:
            await notify(parent["authorId"], "reply", f"{user.get('username')} replied to your comment", f"/community/{sid}", user)
    out = clean(doc)
    out["author"] = public_user(user)
    return out


# ---------- Social: profiles, follow, feed, notifications ----------
@social.get("/profiles/{username}")
async def profile(username: str, user: dict = Depends(get_optional_user)):
    u = await db.users.find_one({"username": username})
    if not u:
        raise HTTPException(status_code=404, detail="Not found")
    pub = public_user(u)
    pub["publicStrategies"] = await db.strategies.count_documents({"ownerUserId": u["id"], "published": True, "visibility": "PUBLIC"})
    pub["followers"] = await db.follows.count_documents({"followingId": u["id"]})
    pub["following"] = await db.follows.count_documents({"followerId": u["id"]})
    pub["isFollowing"] = bool(user and await db.follows.find_one({"followerId": user["id"], "followingId": u["id"]}))
    pub["strategies"] = await db.strategies.find({"ownerUserId": u["id"], "published": True, "visibility": "PUBLIC"}, {"_id": 0}).to_list(200)
    return pub


@social.post("/users/{username}/follow")
async def follow(username: str, user: dict = Depends(get_current_user)):
    target = await db.users.find_one({"username": username})
    if not target:
        raise HTTPException(status_code=404, detail="Not found")
    if target["id"] == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    if not await db.follows.find_one({"followerId": user["id"], "followingId": target["id"]}):
        from community_network import rate
        await rate(user,"follow",60)
        try:
            await db.follows.insert_one({"_id":sha256((user["id"]+":"+target["id"]).encode()).hexdigest(),"followerId": user["id"], "followingId": target["id"], "createdAt": now_iso()})
        except DuplicateKeyError:
            return {"following":True}
        await notify(target["id"], "new_follower", f"{user.get('username')} followed you", f"/u/{user.get('username')}", user)
    return {"following": True}


@social.delete("/users/{username}/follow")
async def unfollow(username: str, user: dict = Depends(get_current_user)):
    target = await db.users.find_one({"username": username})
    if target:
        await db.follows.delete_many({"followerId": user["id"], "followingId": target["id"]})
    return {"following": False}


@social.get("/following/strategies")
async def following_feed(user: dict = Depends(get_current_user)):
    follows = await db.follows.find({"followerId": user["id"]}).to_list(1000)
    ids = [f["followingId"] for f in follows]
    docs = await db.strategies.find({"ownerUserId": {"$in": ids}, "published": True, "visibility": "PUBLIC"}, {"_id": 0}).sort("publishedAt", -1).to_list(200)
    return [await _enrich(d, user["id"]) for d in docs]


@social.get("/saved/strategies")
async def saved_feed(user: dict = Depends(get_current_user)):
    saves = await db.strategy_saves.find({"userId": user["id"]}).to_list(1000)
    ids = [s["strategyId"] for s in saves]
    docs = await db.strategies.find({"id": {"$in": ids}, "$or":[{"ownerUserId":user["id"]},{"published":True,"visibility":"PUBLIC"}]}, {"_id": 0}).to_list(200)
    return [await _enrich(d, user["id"]) for d in docs]


@social.get("/notifications")
async def notifications(user: dict = Depends(get_current_user)):
    docs = await db.notifications.find({"userId": user["id"]}, {"_id": 0}).sort("createdAt", -1).to_list(100)
    return docs


@social.post("/notifications/read")
async def mark_read(user: dict = Depends(get_current_user)):
    await db.notifications.update_many({"userId": user["id"]}, {"$set": {"read": True}})
    return {"ok": True}


@social.post("/reports")
async def create_report(req: ReportReq, user: dict = Depends(get_current_user)):
    doc = {"id": new_id("rep"), "reporterId": user["id"], "targetType": req.targetType,
           "targetId": req.targetId, "reason": req.reason, "details": req.details,
           "status": "open", "createdAt": now_iso()}
    await db.reports.insert_one(dict(doc))
    return clean(doc)

# Member social posts complement, rather than replace, the public strategy library.
from community_network import router as network_router
router.include_router(network_router)
