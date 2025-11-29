import types

import asyncio

from mcp_bridge import MCPBridge


def test_list_entities_uses_live_when_connected(monkeypatch):
    """list_entities should not fall back to demo when connected=True even if demo_mode=True."""
    bridge = MCPBridge(demo_mode=True)

    # Simulate live availability
    bridge.connected = True
    bridge._live_functions = {
        "list_entities": (lambda domain=None, limit=100: asyncio.sleep(0, [{"entity_id": "light.test"}]))
    }

    result = asyncio.run(bridge.list_entities(domain="light", limit=5))
    assert result.get("success") is True
    assert result.get("total_count") == 1
    assert result.get("entities")[0]["entity_id"] == "light.test"
