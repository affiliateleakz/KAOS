"""Real MongoDB integration against isolated fixture databases; no member records."""
import asyncio
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock
import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI,HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
import community_network as network
import routes_community as legacy
import routes_admin as admin
from models import SettingsReq

ALICE={'id':'alice','username':'alice','name':'Alice','email':'private-alice@example.com','password_hash':'private-hash','role':'user'}
BOB={'id':'bob','username':'bob','name':'Bob','role':'user'}
CHARLIE={'id':'charlie','username':'charlie','name':'Charlie','role':'user'}
MOD={'id':'moderator','username':'mod','role':'moderator'}


def run(monkeypatch,callback):
    async def scenario():
        client=AsyncIOMotorClient('mongodb://127.0.0.1:27017',serverSelectionTimeoutMS=2000)
        database=client['kaos_community_fixture_'+uuid4().hex]
        monkeypatch.setattr(network,'db',database);monkeypatch.setattr(network,'_ready',False)
        monkeypatch.setattr(legacy,'db',database);monkeypatch.setattr(admin,'db',database)
        monkeypatch.setattr(network,'notify',AsyncMock());monkeypatch.setattr(legacy,'notify',AsyncMock());monkeypatch.setattr(admin,'audit_log',AsyncMock())
        try:
            await client.admin.command('ping')
            await database.users.insert_many([dict(ALICE),dict(BOB),dict(CHARLIE)])
            await callback(database)
        finally:
            await client.drop_database(database.name);client.close()
    asyncio.run(scenario())


async def feed(user=ALICE,**options):
    return await network.feed(**{'mode':'all','kind':'all','author':None,'cursor':None,'limit':20,**options},user=user)


@pytest.mark.parametrize('payload',[{'body':'   '},{'body':'ok','kind':'script'}, {'body':'ok','authorId':'forged'},
    {'body':'ok','link':'javascript:alert(1)'},{'body':'ok','code':'print(1)'},{'body':'ok','link':'https://user:secret@example.com'}])
def test_post_contract_rejects_empty_forged_and_unsafe_fields(payload):
    with pytest.raises(ValidationError):network.PostInput(**payload)


def test_anonymous_members_cannot_read_or_write_member_social_content():
    app=FastAPI();app.include_router(network.router,prefix='/api/community')
    with TestClient(app) as client:
        assert client.get('/api/community/posts').status_code==401
        assert client.get('/api/community/members').status_code==401
        assert client.post('/api/community/posts',json={'body':'test'}).status_code==401


def test_script_storage_is_non_executing_and_feed_uses_public_projections(monkeypatch):
    async def scenario(db):
        source='  # preserve the exact shared whitespace\nraise RuntimeError("this is shared text, never executed")\n'
        post=await network.create(network.PostInput(kind='script',body='Review this script',code=source,language='python'),ALICE)
        assert post['code']==source and post['authorId']=='alice'
        assert post['createdAt']==post['updatedAt']
        assert 'email' not in post['author'] and 'password_hash' not in post['author']
        listing=await feed()
        assert 'code' not in listing['items'][0]
        assert (await network.detail(post['id'],BOB))['code']==source
        await network.edit(post['id'],network.PostInput(kind='script',body='New explanation',code=source,language='python'),ALICE)
        assert (await network.detail(post['id'],BOB))['body']=='New explanation'
        with pytest.raises(HTTPException) as exc:await network.edit(post['id'],network.PostInput(body='hijacked'),BOB)
        assert exc.value.status_code==403
    run(monkeypatch,scenario)


def test_following_feed_and_rosters_share_existing_follow_relationships(monkeypatch):
    async def scenario(db):
        await network.create(network.PostInput(body='Bob discusses forex'),BOB)
        await network.create(network.PostInput(body='Charlie discusses crypto'),CHARLIE)
        assert (await feed(mode='following'))['items']==[]
        await legacy.follow('bob',ALICE);await legacy.follow('bob',ALICE)
        assert await db.follows.count_documents({'followerId':'alice','followingId':'bob'})==1
        assert legacy.notify.await_count==1
        items=(await feed(mode='following'))['items'];assert [p['authorId'] for p in items]==['bob']
        assert items[0]['isFollowing']
        roster=await network.members(q='',connection='following',username='alice',page=0,user=ALICE)
        assert [p['username'] for p in roster['items']]==['bob']
        assert 'email' not in roster['items'][0]
        await legacy.unfollow('bob',ALICE)
        assert (await feed(mode='following'))['items']==[]
    run(monkeypatch,scenario)


def test_reactions_are_idempotent_and_cross_post_replies_are_rejected(monkeypatch):
    async def scenario(db):
        first=await network.create(network.PostInput(body='First post'),ALICE)
        second=await network.create(network.PostInput(body='Second post'),BOB)
        await network.like(first['id'],BOB);await network.like(first['id'],BOB)
        assert (await network.detail(first['id'],ALICE))['likesCount']==1
        comment=await network.comment(first['id'],network.CommentInput(body='Useful idea'),BOB)
        assert (await network.detail(first['id'],ALICE))['commentsCount']==1
        with pytest.raises(HTTPException) as exc:await network.comment(second['id'],network.CommentInput(body='Wrong thread',parentId=comment['id']),ALICE)
        assert exc.value.status_code==422
        await network.unlike(first['id'],BOB);await network.unlike(first['id'],BOB)
        assert (await network.detail(first['id'],ALICE))['likesCount']==0
        with pytest.raises(HTTPException):await network.remove_comment(first['id'],comment['id'],ALICE)
        await network.remove_comment(first['id'],comment['id'],MOD)
        assert (await network.comments(first['id'],None,ALICE))['items']==[]
    run(monkeypatch,scenario)


def test_only_public_strategies_can_be_shared_and_revocation_hides_the_attachment(monkeypatch):
    async def scenario(db):
        await db.strategies.insert_many([{'id':'private','ownerUserId':'bob','published':False,'visibility':'PRIVATE','rules':{'secret':True}},
            {'id':'public','ownerUserId':'bob','published':True,'visibility':'PUBLIC','name':'Test strategy','version':1}])
        with pytest.raises(HTTPException):await network.create(network.PostInput(kind='strategy',body='Private leak',strategyId='private'),ALICE)
        shared=await network.create(network.PostInput(kind='strategy',body='Public discussion',strategyId='public'),ALICE)
        assert shared['strategy']['name']=='Test strategy'
        await db.strategies.update_one({'id':'public'},{'$set':{'visibility':'PRIVATE'}})
        assert (await network.detail(shared['id'],ALICE))['strategy'] is None
        with pytest.raises(HTTPException):await legacy.community_detail('private',ALICE)
        with pytest.raises(HTTPException):await legacy.fork('private',ALICE)
    run(monkeypatch,scenario)


def test_feed_pagination_has_no_duplicates_at_equal_timestamps(monkeypatch):
    async def scenario(db):
        for i in range(5):await network.create(network.PostInput(body=f'Fixture {i}'),ALICE)
        await db.community_posts.update_many({},{'$set':{'createdAt':'2026-11-16T00:00:00+00:00'}})
        found=[];cursor=None
        for _ in range(3):
            result=await feed(limit=2,cursor=cursor);found.extend(p['id'] for p in result['items']);cursor=result['nextCursor']
        assert len(found)==len(set(found))==5 and cursor is None
        with pytest.raises(HTTPException):await feed(cursor='not-a-valid-cursor')
    run(monkeypatch,scenario)


def test_author_deletion_and_moderation_hide_posts_without_exposing_nested_content(monkeypatch):
    async def scenario(db):
        item=await network.create(network.PostInput(body='Reported content'),ALICE)
        with pytest.raises(HTTPException):await network.remove(item['id'],BOB)
        await network.report_post(item['id'],network.ReportInput(reason='Spam'),BOB)
        report=await db.reports.find_one({'targetId':item['id']})
        await admin.report_action(report['id'],SettingsReq(key='report',value={'action':'hide'}),MOD)
        assert (await feed())['items']==[]
        for fn in (lambda:network.detail(item['id'],ALICE),lambda:network.comments(item['id'],None,ALICE),lambda:network.like(item['id'],ALICE)):
            with pytest.raises(HTTPException) as exc:await fn()
            assert exc.value.status_code==404
    run(monkeypatch,scenario)


def test_post_rate_limits_are_real_and_member_search_is_literal(monkeypatch):
    async def scenario(db):
        for i in range(10):await network.create(network.PostInput(body=f'Test {i}'),ALICE)
        with pytest.raises(HTTPException) as exc:await network.create(network.PostInput(body='Too fast'),ALICE)
        assert exc.value.status_code==429
        assert (await network.members(q='.*',connection='all',username=None,page=0,user=ALICE))['items']==[]
    run(monkeypatch,scenario)


def test_account_deletion_removes_social_visibility_and_follow_relationships(monkeypatch):
    import routes_auth
    from fastapi import Response
    async def scenario(db):
        monkeypatch.setattr(routes_auth,'db',db)
        item=await network.create(network.PostInput(body='My post'),ALICE)
        await network.comment(item['id'],network.CommentInput(body='My comment'),ALICE)
        await legacy.follow('bob',ALICE)
        await routes_auth.delete_account(Response(),ALICE)
        assert (await feed(user=BOB))['items']==[]
        assert await db.follows.count_documents({'followerId':'alice'})==0
        assert await db.community_comments.count_documents({'authorId':'alice','hidden':False})==0
    run(monkeypatch,scenario)


def test_concurrent_follows_do_not_duplicate_edges_or_notifications(monkeypatch):
    async def scenario(db):
        await asyncio.gather(*(legacy.follow('bob',ALICE) for _ in range(8)))
        assert await db.follows.count_documents({'followerId':'alice','followingId':'bob'})==1
        assert legacy.notify.await_count==1
    run(monkeypatch,scenario)
