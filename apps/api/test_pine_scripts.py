"""Offline regressions for Pine content and publication/ownership boundaries."""
import base64
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from PIL import Image
import pine_scripts as pine


def test_thumbnail_strips_metadata_and_rejects_active_content():
    output=BytesIO()
    Image.new('RGB',(800,400),'gold').save(output,format='PNG')
    image=pine.thumbnail('data:image/png;base64,'+base64.b64encode(output.getvalue()).decode())
    assert image.startswith('data:image/jpeg;base64,')
    with Image.open(BytesIO(base64.b64decode(image.split(',',1)[1]))) as decoded:
        assert decoded.width<=640 and decoded.height<=360
    with pytest.raises(HTTPException):pine.thumbnail('data:image/svg+xml;base64,PHN2Zz4=')


def test_nonpublished_content_only_visible_to_owner_or_admin():
    row={'author_id':'alice','status':'pending'}
    assert pine.visible(row,{'id':'alice','role':'user'})
    assert pine.visible(row,{'id':'owner','role':'super_admin'})
    assert not pine.visible(row,{'id':'bob','role':'user'})
    assert not pine.visible(row,{'id':'mod','role':'moderator'})
    assert pine.visible({**row,'status':'published'},{'id':'bob','role':'user'})


def test_source_is_bounded_and_pine_version_required():
    from pydantic import ValidationError
    valid={'title':'Example','description':'Example','source':'//@version=6\nindicator("Example")\nplot(close)'}
    assert pine.Submission(**valid).source.startswith('//@version=6')
    for source in ('plain text','//@version=6\n\x00','//@version=6\n'+'x'*pine.MAX_SOURCE):
        with pytest.raises(ValidationError):pine.Submission(**{**valid,'source':source})


@pytest.mark.asyncio
async def test_member_cannot_publish_or_edit_another_author(monkeypatch):
    request=object()
    data=pine.Submission(title='Example',description='Example',source='//@version=6\nplot(close)',status='published',rights_confirmed=True)
    monkeypatch.setattr(pine,'payload',AsyncMock(return_value=data))
    collection=SimpleNamespace(find_one=AsyncMock(return_value=None))
    monkeypatch.setattr(pine,'db',SimpleNamespace(pine_scripts=collection))
    with pytest.raises(HTTPException) as error:await pine.save(request,{'id':'alice'})
    assert error.value.status_code==403
    collection.find_one.return_value={'author_id':'bob','revision':'a'}
    with pytest.raises(HTTPException) as error:await pine.save(request,{'id':'alice'},sid='private')
    assert error.value.status_code==404


@pytest.mark.asyncio
async def test_admin_edit_conflict_cannot_overwrite_newer_revision(monkeypatch):
    data=pine.Submission(title='Example',description='Example',source='//@version=6\nplot(close)',revision='stale',rights_confirmed=True)
    monkeypatch.setattr(pine,'payload',AsyncMock(return_value=data))
    collection=SimpleNamespace(find_one=AsyncMock(return_value={'author_id':'bob','revision':'current'}),update_one=AsyncMock())
    monkeypatch.setattr(pine,'db',SimpleNamespace(pine_scripts=collection))
    with pytest.raises(HTTPException) as error:await pine.save(object(),{'id':'owner'},sid='script',admin=True)
    assert error.value.status_code==409
    collection.update_one.assert_not_awaited()
