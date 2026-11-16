import importlib.util
from pathlib import Path
from zipfile import ZipFile
import json
import pytest

spec=importlib.util.spec_from_file_location('extension_package',Path(__file__).resolve().parents[1]/'build_extension_package.py')
package=importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


def test_review_package_targets_existing_item_and_contains_runtime_only(tmp_path):
    source=tmp_path/'extension';source.mkdir()
    (source/'manifest.json').write_text(json.dumps({'version':'1.7.26','homepage_url':'https://chromewebstore.google.com/detail/'+package.STORE_ID,'background':{'service_worker':'background.js'}}))
    for filename in ('popup.html','background.js','kaos-cloud.js','test_auth.cjs','README.md','.env'):(source/filename).write_text('fixture')
    output=tmp_path/'review.zip'
    report=package.build(source,output)
    assert report['store_item_id']==package.STORE_ID and report['state']=='review_candidate_not_live_verified'
    with ZipFile(output) as archive:
        assert set(archive.namelist())=={'manifest.json','popup.html','background.js','kaos-cloud.js'}
    manifest=json.loads((source/'manifest.json').read_text());manifest['homepage_url']='https://chromewebstore.google.com/detail/other'
    (source/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='existing KAOS'):package.build(source,output)
