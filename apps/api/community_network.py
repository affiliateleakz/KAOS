"""Member social feed. Shared text/code is data and is never executed."""
import asyncio
import base64
import json
import re
from datetime import datetime,timezone,timedelta
from typing import Literal,Annotated
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,ConfigDict,Field,HttpUrl,model_validator,StringConstraints
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from db import db,new_id,now_iso
from auth import get_current_user,ROLE_RANK
from services import public_user,notify

router=APIRouter()
_ready=False


async def indexes():
    global _ready
    if _ready:return
    await db.community_posts.create_index('id',unique=True)
    await db.community_comments.create_index('id',unique=True)
    await db.community_posts.create_index([('hidden',1),('createdAt',-1),('id',-1)])
    await db.community_posts.create_index([('authorId',1),('hidden',1),('createdAt',-1)])
    await db.community_comments.create_index([('postId',1),('hidden',1),('createdAt',-1)])
    await db.community_reactions.create_index('postId')
    await db.community_write_limits.create_index('expiresAt',expireAfterSeconds=0)
    _ready=True


async def member(user=Depends(get_current_user)):
    from routes_billing import get_entitlements
    if not (await get_entitlements(user)).get('community'):raise HTTPException(403,'Community access is not included in your membership')
    return user


async def rate(user,action,limit):
    await indexes()
    now=datetime.now(timezone.utc)
    query={'_id':f'{user["id"]}:{action}:{int(now.timestamp())//60}'}
    update={'$inc':{'count':1},'$setOnInsert':{'expiresAt':now+timedelta(minutes=2)}}
    try:row=await db.community_write_limits.find_one_and_update(query,update,upsert=True,return_document=ReturnDocument.AFTER)
    except DuplicateKeyError:row=await db.community_write_limits.find_one_and_update(query,update,return_document=ReturnDocument.AFTER)
    if row['count']>limit:raise HTTPException(429,'Please wait a moment before posting again')


class PostInput(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    kind:Literal['discussion','strategy','script']='discussion'
    title:str=Field(default='',max_length=160)
    body:str=Field(min_length=1,max_length=5000)
    code:Annotated[str,StringConstraints(strip_whitespace=False)]=Field(default='',max_length=30000)
    language:Literal['text','javascript','python','pine','json']='text'
    strategyId:str|None=Field(default=None,max_length=80)
    link:HttpUrl|None=None

    @model_validator(mode='after')
    def content(self):
        if self.kind=='script' and not self.code.strip():raise ValueError('Add script code before sharing')
        if self.kind!='script' and self.code:raise ValueError('Choose Script to share code')
        if self.kind!='strategy' and self.strategyId:raise ValueError('Choose Strategy to attach a strategy')
        if self.link and (self.link.username or self.link.password):raise ValueError('Links cannot contain credentials')
        if self.link and len(str(self.link))>2048:raise ValueError('Link is too long')
        return self


class CommentInput(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    body:str=Field(min_length=1,max_length=2000)
    parentId:str|None=Field(default=None,max_length=80)


class ReportInput(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    reason:Literal['Spam','Harassment','Misleading content','Unsafe script','Other']='Other'
    details:str=Field(default='',max_length=1000)


def staff(user):
    return ROLE_RANK.get(user.get('role'),0)>=ROLE_RANK['moderator']


def cursor_filter(cursor):
    if not cursor:return {}
    try:
        time,identity=json.loads(base64.urlsafe_b64decode(cursor+'='*(-len(cursor)%4)))
        datetime.fromisoformat(time)
        if not isinstance(identity,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',identity):raise ValueError()
        return {'$or':[{'createdAt':{'$lt':time}},{'createdAt':time,'id':{'$lt':identity}}]}
    except (ValueError,TypeError,KeyError):raise HTTPException(422,'Invalid feed cursor')


def next_cursor(rows,limit):
    if len(rows)<=limit:return None
    row=rows[limit-1]
    return base64.urlsafe_b64encode(json.dumps([row['createdAt'],row['id']]).encode()).decode().rstrip('=')


async def post(identity):
    row=await db.community_posts.find_one({'id':identity,'hidden':False},{'_id':0})
    if not row:raise HTTPException(404,'Post not found')
    return row


async def strategy(identity):
    if not identity:return None
    row=await db.strategies.find_one({'id':identity,'published':True,'visibility':'PUBLIC'},{'_id':0})
    if not row:raise HTTPException(422,'Only a published public strategy can be shared')
    return row


async def enrich(rows,user):
    if not rows:return []
    ids=[r['id'] for r in rows];authors=list({r['authorId'] for r in rows})
    people=await db.users.find({'id':{'$in':authors}},{'_id':0,'id':1,'username':1,'name':1,'avatar':1,'bio':1,'created_at':1}).to_list(len(authors))
    people={r['id']:public_user(r) for r in people}
    liked=await db.community_reactions.find({'postId':{'$in':ids},'userId':user['id']},{'postId':1}).to_list(len(ids))
    follows=await db.follows.find({'followerId':user['id'],'followingId':{'$in':authors}},{'followingId':1}).to_list(len(authors))
    followed={r['followingId'] for r in follows};liked={r['postId'] for r in liked}
    async def counts(collection,query):
        records=await collection.aggregate([{'$match':{'postId':{'$in':ids},**query}},{'$group':{'_id':'$postId','count':{'$sum':1}}}]).to_list(len(ids))
        return {r['_id']:r['count'] for r in records}
    likes,comments=await asyncio.gather(counts(db.community_reactions,{}),counts(db.community_comments,{'hidden':False}))
    strategy_ids=list({r['strategyId'] for r in rows if r.get('strategyId')})
    shared=await db.strategies.find({'id':{'$in':strategy_ids},'published':True,'visibility':'PUBLIC'},
        {'_id':0,'id':1,'name':1,'version':1,'ownerUsername':1}).to_list(len(strategy_ids)) if strategy_ids else []
    shared={r['id']:r for r in shared}
    return [{**r,'author':people.get(r['authorId']),'isFollowing':r['authorId'] in followed,'liked':r['id'] in liked,
        'likesCount':likes.get(r['id'],0),'commentsCount':comments.get(r['id'],0),'canDelete':r['authorId']==user['id'] or staff(user),
        'strategy':shared.get(r.get('strategyId'))} for r in rows]


@router.get('/posts')
async def feed(mode:Literal['all','following']='all',kind:Literal['all','discussion','strategy','script']='all',
    author:str|None=Query(default=None,max_length=80),cursor:str|None=Query(default=None,max_length=256),
    limit:int=Query(default=20,ge=1,le=30),user=Depends(member)):
    await indexes()
    query={'hidden':False,**cursor_filter(cursor)}
    if kind!='all':query['kind']=kind
    if mode=='following':query['authorId']={'$in':await db.follows.distinct('followingId',{'followerId':user['id']})}
    if author:
        owner=await db.users.find_one({'username':author},{'id':1})
        if not owner:return {'items':[],'nextCursor':None}
        if mode=='following' and owner['id'] not in query['authorId']['$in']:return {'items':[],'nextCursor':None}
        query['authorId']=owner['id']
    rows=await db.community_posts.find(query,{'_id':0,'code':0}).sort([('createdAt',-1),('id',-1)]).limit(limit+1).to_list(limit+1)
    return {'items':await enrich(rows[:limit],user),'nextCursor':next_cursor(rows,limit)}


@router.post('/posts')
async def create(request:PostInput,user=Depends(member)):
    await strategy(request.strategyId)
    await rate(user,'post',10)
    stamp=now_iso()
    row={**request.model_dump(mode='json'),'id':new_id('post'),'authorId':user['id'],'hidden':False,'createdAt':stamp,'updatedAt':stamp}
    await db.community_posts.insert_one(dict(row))
    return (await enrich([row],user))[0]


@router.get('/posts/{identity}')
async def detail(identity:str,user=Depends(member)):
    return (await enrich([await post(identity)],user))[0]


@router.patch('/posts/{identity}')
async def edit(identity:str,request:PostInput,user=Depends(member)):
    row=await post(identity)
    if row['authorId']!=user['id']:raise HTTPException(403,'Only the author can edit this post')
    await strategy(request.strategyId);await rate(user,'edit',20)
    await db.community_posts.update_one({'id':identity,'authorId':user['id'],'hidden':False},{'$set':{**request.model_dump(mode='json'),'updatedAt':now_iso()}})
    return await detail(identity,user)


@router.delete('/posts/{identity}')
async def remove(identity:str,user=Depends(member)):
    row=await post(identity)
    if row['authorId']!=user['id'] and not staff(user):raise HTTPException(403,'Only the author or a moderator can remove this post')
    await db.community_posts.update_one({'id':identity},{'$set':{'hidden':True,'removedBy':user['id'],'removedAt':now_iso()}})
    return {'removed':True}


@router.put('/posts/{identity}/like')
async def like(identity:str,user=Depends(member)):
    await post(identity);await rate(user,'reaction',60)
    await db.community_reactions.update_one({'_id':identity+':'+user['id']},{'$setOnInsert':{'postId':identity,'userId':user['id'],'createdAt':now_iso()}},upsert=True)
    return {'liked':True}


@router.delete('/posts/{identity}/like')
async def unlike(identity:str,user=Depends(member)):
    await post(identity)
    await db.community_reactions.delete_one({'_id':identity+':'+user['id']})
    return {'liked':False}


@router.get('/posts/{identity}/comments')
async def comments(identity:str,cursor:str|None=Query(default=None,max_length=256),user=Depends(member)):
    await post(identity)
    rows=await db.community_comments.find({'postId':identity,'hidden':False,**cursor_filter(cursor)},{'_id':0}).sort([('createdAt',-1),('id',-1)]).limit(31).to_list(31)
    ids=list({r['authorId'] for r in rows})
    people=await db.users.find({'id':{'$in':ids}},{'_id':0,'id':1,'username':1,'name':1}).to_list(len(ids)) if ids else []
    people={r['id']:public_user(r) for r in people}
    return {'items':[{**r,'author':people.get(r['authorId']),'canDelete':r['authorId']==user['id'] or staff(user)} for r in rows[:30]],'nextCursor':next_cursor(rows,30)}


@router.post('/posts/{identity}/comments')
async def comment(identity:str,request:CommentInput,user=Depends(member)):
    target=await post(identity)
    parent=await db.community_comments.find_one({'id':request.parentId,'postId':identity,'hidden':False}) if request.parentId else None
    if request.parentId and not parent:raise HTTPException(422,'Reply must refer to a visible comment on this post')
    await rate(user,'comment',30)
    row={**request.model_dump(),'id':new_id('cmt'),'postId':identity,'authorId':user['id'],'hidden':False,'createdAt':now_iso()}
    await db.community_comments.insert_one(dict(row))
    recipients={target['authorId']}|({parent['authorId']} if parent else set())
    for recipient in recipients-{user['id']}:
        await notify(recipient,'community_comment',f"{user.get('username') or 'A member'} commented on a community post",'/dashboard/community?post='+identity,user)
    return {**row,'author':public_user(user),'canDelete':True}


@router.delete('/posts/{identity}/comments/{comment_id}')
async def remove_comment(identity:str,comment_id:str,user=Depends(member)):
    await post(identity)
    row=await db.community_comments.find_one({'id':comment_id,'postId':identity,'hidden':False})
    if not row:raise HTTPException(404,'Comment not found')
    if row['authorId']!=user['id'] and not staff(user):raise HTTPException(403,'Only the author or a moderator can remove this comment')
    await db.community_comments.update_one({'id':comment_id,'postId':identity},{'$set':{'hidden':True}})
    return {'removed':True}


async def report(target_type,target_id,request,user,post_id=None):
    await rate(user,'report',10)
    await db.reports.insert_one({'id':new_id('rep'),'reporterId':user['id'],'targetType':target_type,'targetId':target_id,'postId':post_id or target_id,
        **request.model_dump(),'status':'open','createdAt':now_iso()})
    return {'reported':True}


@router.post('/posts/{identity}/report')
async def report_post(identity:str,request:ReportInput,user=Depends(member)):
    await post(identity)
    return await report('community_post',identity,request,user)


@router.post('/posts/{identity}/comments/{comment_id}/report')
async def report_comment(identity:str,comment_id:str,request:ReportInput,user=Depends(member)):
    await post(identity)
    if not await db.community_comments.find_one({'id':comment_id,'postId':identity,'hidden':False}):raise HTTPException(404,'Comment not found')
    return await report('community_comment',comment_id,request,user,identity)


@router.get('/members')
async def members(q:str=Query(default='',max_length=80),connection:Literal['all','followers','following']='all',
    username:str|None=Query(default=None,max_length=80),page:int=Query(default=0,ge=0,le=1000),user=Depends(member)):
    query={'account_status':{'$nin':['banned','suspended','deleted']},'username':{'$nin':[None,'']}}
    if q.strip():query['$or']=[{'username':{'$regex':re.escape(q.strip()),'$options':'i'}},{'name':{'$regex':re.escape(q.strip()),'$options':'i'}}]
    if connection!='all':
        owner=await db.users.find_one({'username':username},{'id':1}) if username else user
        if not owner:raise HTTPException(404,'Member not found')
        field,other=('followerId','followingId') if connection=='following' else ('followingId','followerId')
        query['id']={'$in':await db.follows.distinct(other,{field:owner['id']})}
    rows=await db.users.find(query,{'_id':0,'id':1,'username':1,'name':1,'avatar':1,'bio':1,'created_at':1}).sort([('username',1),('id',1)]).skip(page*20).limit(21).to_list(21)
    ids=[r['id'] for r in rows[:20]]
    follows=await db.follows.find({'followerId':user['id'],'followingId':{'$in':ids}},{'followingId':1}).to_list(len(ids)) if ids else []
    followed={r['followingId'] for r in follows}
    return {'items':[{**public_user(r),'isFollowing':r['id'] in followed} for r in rows[:20]],'hasMore':len(rows)>20}
