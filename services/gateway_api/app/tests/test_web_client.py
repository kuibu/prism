from fastapi.testclient import TestClient

from app.main import app


def test_web_root_redirects() -> None:
    with TestClient(app) as client:
        response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/web/"


def test_web_client_is_served() -> None:
    with TestClient(app) as client:
        response = client.get("/web/")

    assert response.status_code == 200
    assert "Prism Web Console" in response.text


def test_web_client_contains_chat_controls() -> None:
    with TestClient(app) as client:
        response = client.get("/web/")

    assert response.status_code == 200
    assert '@click="sendMessage"' in response.text
    assert '@click="uploadFile"' in response.text
    assert '@click="downloadMessageFile(msg)"' in response.text
    assert '@click="acceptInviteFromInbox"' in response.text
    assert 'name="bridge"' in response.text
    assert '@click="runBridgeInboundRelay"' in response.text
    assert '@click="runBridgeOutboundPreview"' in response.text
    assert '@click="runTelegramRealPoll"' in response.text
    assert '@click="runTelegramRealSend"' in response.text
    assert '@change="onBridgePlatformChanged"' in response.text
    assert "bridgeInboundButtonLabel" in response.text
    assert "bridgeOutboundButtonLabel" in response.text
    assert ":title=\"tt('err_no_session')\"\n                  ></el-alert>" in response.text
    assert ":title=\"tt('err_no_session')\"\n                  />" not in response.text


def test_web_client_persists_session_and_history() -> None:
    with TestClient(app) as client:
        response = client.get("/web/app.js")

    assert response.status_code == 200
    js_source = response.text
    assert "window.sessionStorage.setItem(SESSION_KEY" in js_source
    assert "window.sessionStorage.getItem(SESSION_KEY" in js_source
    assert "HISTORY_KEY_PREFIX" in js_source
    assert "saveHistoryCache" in js_source
    assert "restoreHistoryCache" in js_source
    assert "loadBridgeConnectors" in js_source
    assert "createBridgeLink" in js_source
    assert "BRIDGE_PLATFORM_UI_PRESETS" in js_source
    assert "bridgeCanInbound" in js_source
    assert "bridgeCanOutbound" in js_source
    assert "runTelegramRealPoll" in js_source
    assert "runTelegramRealSend" in js_source
