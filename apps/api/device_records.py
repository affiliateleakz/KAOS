"""Stable selectors for legacy device rows without a KAOS id; no GET-time writes."""
import base64
from bson import ObjectId
from fastapi import HTTPException


def device_public(record):
    result = dict(record)
    mongo_id = result.pop('_id', None)
    if not isinstance(result.get('id'), str) or not result['id'].strip():
        if isinstance(mongo_id, ObjectId):
            result['id'] = 'legacy-oid-' + str(mongo_id)
        elif isinstance(mongo_id, str) and mongo_id:
            result['id'] = 'legacy-str-' + base64.urlsafe_b64encode(mongo_id.encode()).decode().rstrip('=')
        else:
            raise HTTPException(status_code=409, detail='Device record has no usable identifier')
    return result


def device_query(identifier, user_id=None):
    if not isinstance(identifier, str) or not identifier.strip() or identifier in ('undefined', 'null'):
        raise HTTPException(status_code=400, detail='A valid device identifier is required')
    if identifier.startswith('legacy-oid-'):
        try:
            mongo_id = ObjectId(identifier[len('legacy-oid-'):])
        except Exception:
            raise HTTPException(status_code=400, detail='Invalid legacy device identifier')
    elif identifier.startswith('legacy-str-'):
        encoded = identifier[len('legacy-str-'):]
        try:
            mongo_id = base64.b64decode(encoded + '=' * (-len(encoded) % 4), altchars=b'-_', validate=True).decode()
            if not mongo_id:
                raise ValueError('Empty identifier')
        except (ValueError, UnicodeError):
            raise HTTPException(status_code=400, detail='Invalid legacy device identifier')
    else:
        query = {'id': identifier}
        if user_id is not None:
            query['userId'] = user_id
        return query
    # A selector for a legacy row must not target a current device with an id.
    query = {'_id': mongo_id, '$or': [{'id': {'$exists': False}}, {'id': None}, {'id': ''}]}
    if user_id is not None:
        query['userId'] = user_id
    return query


def device_record_query(record, user_id):
    return device_query(device_public(record)['id'], user_id)
