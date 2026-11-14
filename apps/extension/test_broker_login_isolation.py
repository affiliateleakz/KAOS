"""Static release guard: Pocket Option is untouched until KAOS authorizes connection."""
import json
from pathlib import Path

ROOT = Path(__file__).parent

def test_no_automatic_pocket_option_injection():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    assert not manifest.get("content_scripts"), (
        "Do not inject the KAOS WebSocket wrapper into signed-out Pocket Option pages"
    )

def test_explicit_authentication_gate_for_broker_scripts():
    script = (ROOT / "background.js").read_text()
    assert "async function kaosPermitBrokerIntegration()" in script
    assert "state.step !== 'DASHBOARD'" in script
    assert "!state.license?.authorized" in script
    assert "chrome.scripting.registerContentScripts" in script
    assert "persistAcrossSessions:false" in script
    assert "if(!kaosAuthorizedPo) return {ok:false,reason:'KAOS_AUTH_REQUIRED'};" in script
    assert "case 'KAOS_LOGOUT': await kaosStopBrokerIntegration();" in script
    assert "chrome.scripting.unregisterContentScripts" in script
