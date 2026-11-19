"""Owner-managed public social links. URLs are stored, never fetched by the server."""

from uuid import uuid4
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, ConfigDict
from db import db, now_iso
from auth import require_role
from pymongo.errors import DuplicateKeyError

router = APIRouter(tags=["Follow Us"])
KEY = "follow_us"
owner = require_role("super_admin")


class SocialLink(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=1, max_length=60)
    url: str = Field(min_length=1, max_length=1000)
    enabled: bool = True


class FollowSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: str = Field(max_length=128)
    title: str = Field(default="Follow KAOS", min_length=1, max_length=100)
    description: str = Field(
        default="Keep up with KAOS updates, education and community news.",
        max_length=500,
    )
    links: list[SocialLink] = Field(default_factory=list, max_length=20)


async def settings():
    row = await db.settings.find_one({"key": KEY})
    return (
        row.get("value")
        if row
        else {
            "revision": "default",
            "title": "Follow KAOS",
            "description": "Keep up with KAOS updates, education and community news.",
            "links": [],
        }
    )


@router.get("/api/site/follow-us")
async def public(response: Response):
    value = await settings()
    response.headers["Cache-Control"] = "no-store"
    return {
        "title": value["title"],
        "description": value["description"],
        "links": [
            {"label": r["label"], "url": r["url"]}
            for r in value.get("links", [])
            if r.get("enabled")
        ],
    }


@router.get("/api/admin/follow-us")
async def admin_settings(response: Response, user=Depends(owner)):
    response.headers["Cache-Control"] = "private, no-store"
    return await settings()


@router.put("/api/admin/follow-us")
async def save(req: FollowSettings, user=Depends(owner)):
    links = []
    for link in req.links:
        try:
            url = urlsplit(link.url)
        except ValueError:
            raise HTTPException(422, "Provide a valid HTTPS link") from None
        if url.scheme != "https" or not url.hostname or url.username or url.password:
            raise HTTPException(
                422, "Social links must use HTTPS without embedded credentials"
            )
        if any(c in link.url for c in ("\r", "\n", "\t")):
            raise HTTPException(422, "Invalid URL")
        if not link.label.strip():
            raise HTTPException(422, "Provide a label for each link")
        links.append(
            {"label": link.label.strip(), "url": link.url, "enabled": link.enabled}
        )
    previous = await settings()
    if req.revision != previous["revision"]:
        raise HTTPException(409, "Follow Us settings changed; reload before saving")
    value = {
        "revision": uuid4().hex,
        "title": req.title.strip(),
        "description": req.description.strip(),
        "links": links,
        "updatedAt": now_iso(),
        "updatedBy": user["id"],
    }
    row = await db.settings.find_one({"key": KEY})
    if row:
        result = await db.settings.update_one(
            {"_id": row["_id"], "value.revision": req.revision},
            {"$set": {"value": value}},
        )
        if result.modified_count != 1:
            raise HTTPException(409, "Follow Us settings changed; reload before saving")
    else:
        try:
            await db.settings.insert_one({"_id": KEY, "key": KEY, "value": value})
        except DuplicateKeyError:
            raise HTTPException(
                409, "Follow Us settings changed; reload before saving"
            ) from None
    return value
