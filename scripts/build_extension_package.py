"""Build a review candidate for the existing KAOS Chrome Web Store item."""
import base64
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
STORE_ID='gbobopmnjgeeegniphckfpalhnebapjm'


def build(source,output):
    manifest=json.loads((source/'manifest.json').read_text())
    if manifest.get('homepage_url')!='https://chromewebstore.google.com/detail/'+STORE_ID:
        raise ValueError('Package must target the existing KAOS store item '+STORE_ID)
    if manifest.get('key'):
        digest=hashlib.sha256(base64.b64decode(manifest['key'],validate=True)).digest()[:16].hex()
        extension_id=''.join(chr(ord('a')+int(c,16)) for c in digest)
        if extension_id!=STORE_ID:raise ValueError('Manifest public key belongs to another extension ID')
    files=sorted(p for p in source.rglob('*') if p.is_file() and not p.is_symlink()
        and not any(part.startswith('.') or part in ('__pycache__','node_modules','fixtures') for part in p.relative_to(source).parts)
        and not p.name.startswith('test_') and p.suffix.lower() not in ('.py','.pyc','.cjs','.md','.zip','.crx','.pem','.key','.log'))
    names={p.relative_to(source).as_posix() for p in files}
    required={'manifest.json','popup.html',manifest['background']['service_worker'],*manifest.get('icons',{}).values()}
    if not required<=names:raise ValueError('Package is missing required runtime assets')
    output.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(output,'w',ZIP_DEFLATED) as archive:
        for p in files:archive.write(p,p.relative_to(source).as_posix())
    with ZipFile(output) as archive:
        if archive.testzip() is not None:raise ValueError('Invalid package ZIP')
    return {'version':manifest['version'],'store_item_id':STORE_ID,'files':len(files),'path':str(output),'state':'review_candidate_not_live_verified'}


if __name__=='__main__':print(json.dumps(build(ROOT/'apps/extension',ROOT/'dist/kaos-chrome-extension.zip'),indent=2))
