"""
MCP Bridge - Abstraction layer for Home Assistant diagnostics

Supports two modes:
- LIVE: Direct imports from MCP server functions
- DEMO: Use pre-generated JSON data (for HuggingFace Spaces)
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime

# Add MCP server to path for direct imports (parent of app package)
MCP_SERVER_PATH = Path(__file__).parent.parent / "Home-Assistant-Diagnostics-MCP-Server"
if str(MCP_SERVER_PATH) not in sys.path:
    sys.path.insert(0, str(MCP_SERVER_PATH))


class MCPBridge:
    """Bridge between Gradio app and Home Assistant diagnostics"""

    def __init__(self, demo_mode: bool = None):
        """
        Initialize MCP Bridge

        Args:
            demo_mode: True for demo data, False for live HA.
                      None = auto-detect from env
        """
        print(f"🔧 MCPBridge.__init__ called with demo_mode={demo_mode}")
        if demo_mode is None:
            demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
            print(f"   → Auto-detected from env: demo_mode={demo_mode}")
        else:
            print(f"   → Using provided value: demo_mode={demo_mode}")

        self.demo_mode = demo_mode
        ha_url_env = os.getenv("HA_URL")
        self.ha_url = ha_url_env.rstrip("/") if ha_url_env else None
        self.ha_token = os.getenv("HA_TOKEN")
        self.init_error: Optional[str] = None
        print(f"   → Final self.demo_mode={self.demo_mode}")
        self.demo_data_dir = Path(__file__).parent / "demo_data"
        self.connected = False

        # Import live functions only if in LIVE mode
        if not self.demo_mode:
            try:
                print("   → Importing MCP server functions...")
                self._import_live_functions()
                self.connected = True
                print("   ✅ Live functions imported successfully")
            except Exception as e:
                self.connected = False
                self.init_error = str(e)
                print(f"   ❌ Failed to import live functions: {e}")
                print(f"   ⚠️  Staying in LIVE mode but bridge is not connected")

        print(f"🔧 MCP Bridge initialized in {'DEMO' if self.demo_mode else 'LIVE'} mode")

    def available_tools(self) -> List[str]:
        """List available tool names in LIVE mode."""
        if not self.demo_mode and hasattr(self, "_live_functions"):
            return list(self._live_functions.keys())
        return []

    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Generic tool caller for LIVE mode."""
        if self.demo_mode:
            return {"success": False, "error": "Tool not available in demo mode", "tool": tool_name}
        if tool_name not in self._live_functions:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        return await self._live_functions[tool_name](**kwargs)

    def _import_live_functions(self):
        """Import functions from MCP server for LIVE mode"""
        import inspect
        import app.ha as ha

        self._live_functions = {}
        for name, func in inspect.getmembers(ha, inspect.iscoroutinefunction):
            if name.startswith("_"):
                continue
            self._live_functions[name] = func

        # Common aliases
        if "get_entities" in self._live_functions:
            self._live_functions["list_entities"] = self._live_functions["get_entities"]
        if "get_automations" in self._live_functions:
            self._live_functions["list_automations"] = self._live_functions["get_automations"]
        if "get_ha_error_log" in self._live_functions:
            self._live_functions["get_error_log"] = self._live_functions["get_ha_error_log"]

    def _load_demo_data(self, filename: str) -> Dict[str, Any]:
        """Load demo data from JSON file"""
        filepath = self.demo_data_dir / filename
        if not filepath.exists():
            return {
                "error": f"Demo data not found: {filename}",
                "demo_mode": True,
                "timestamp": datetime.now().isoformat()
            }

        with open(filepath, 'r') as f:
            data = json.load(f)
            data["demo_mode"] = True
            return data

    # ========================================================================
    # DIAGNOSTIC TOOLS
    # ========================================================================

    async def diagnose_system(self, include_entities: bool = True) -> Dict[str, Any]:
        """Run complete system diagnostic"""
        print(f"🔍 diagnose_system called (demo_mode={self.demo_mode})")
        if self.demo_mode:
            return self._load_demo_data("diagnose_system.json")
        if not self.connected:
            return {"success": False, "error": self.init_error or "MCP bridge not connected"}
        return await self._live_functions['diagnose_system'](include_entities=include_entities)

    async def diagnose_issue(self, entity_id: str) -> Dict[str, Any]:
        """Diagnose specific entity issue"""
        print(f"🔍 diagnose_issue called for {entity_id} (demo_mode={self.demo_mode})")
        if self.demo_mode:
            return self._load_demo_data("diagnose_issue_example.json")
        if not self.connected:
            return {"success": False, "error": self.init_error or "MCP bridge not connected"}
        return await self._live_functions['diagnose_issue'](entity_id=entity_id)

    async def diagnose_automation(self, automation_id: str) -> Dict[str, Any]:
        """Diagnose automation issues"""
        print(f"🔍 diagnose_automation called for {automation_id} (demo_mode={self.demo_mode})")
        if self.demo_mode:
            return self._load_demo_data("diagnose_automation.json")
        if not self.connected:
            return {"success": False, "error": self.init_error or "MCP bridge not connected"}
        return await self._live_functions['diagnose_automation'](automation_id=automation_id)

    # ========================================================================
    # SIGNATURE TOOLS (NEW)
    # ========================================================================

    async def audit_zigbee_mesh(self, limit: int = 100) -> Dict[str, Any]:
        """Audit Zigbee mesh network health"""
        print(f"🔍 audit_zigbee_mesh called (demo_mode={self.demo_mode})")
        if self.demo_mode:
            return self._load_demo_data("audit_zigbee_mesh.json")
        if not self.connected:
            return {"success": False, "error": self.init_error or "MCP bridge not connected"}
        return await self._live_functions['audit_zigbee_mesh'](limit=limit)

    async def find_orphan_entities(self) -> Dict[str, Any]:
        """Find entities not used in automations/scripts/scenes"""
        print(f"🔍 find_orphan_entities called (demo_mode={self.demo_mode})")
        if self.demo_mode:
            return self._load_demo_data("find_orphan_entities.json")
        if not self.connected:
            return {"success": False, "error": self.init_error or "MCP bridge not connected"}
        return await self._live_functions['find_orphan_entities']()

    async def detect_automation_conflicts(self) -> Dict[str, Any]:
        """Detect race conditions and loops in automations"""
        print(f"🔍 detect_automation_conflicts called (demo_mode={self.demo_mode})")
        if self.demo_mode:
            return self._load_demo_data("detect_automation_conflicts.json")
        if not self.connected:
            return {"success": False, "error": self.init_error or "MCP bridge not connected"}
        return await self._live_functions['detect_automation_conflicts']()

    async def energy_consumption_report(self, period_hours: int = 24) -> Dict[str, Any]:
        """Generate energy consumption report"""
        print(f"🔍 energy_consumption_report called (demo_mode={self.demo_mode})")
        if self.demo_mode:
            return self._load_demo_data("energy_consumption_report.json")
        if not self.connected:
            return {"success": False, "error": self.init_error or "MCP bridge not connected"}
        return await self._live_functions['energy_consumption_report'](period_hours=period_hours)

    async def entity_dependency_graph(self, entity_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate entity dependency graph"""
        print(f"🔍 entity_dependency_graph called (demo_mode={self.demo_mode})")
        if self.demo_mode:
            return self._load_demo_data("entity_dependency_graph.json")
        if not self.connected:
            return {"success": False, "error": self.init_error or "MCP bridge not connected"}
        # Note: This function might not exist in ha.py, using demo for now
        return self._load_demo_data("entity_dependency_graph.json")

    # ========================================================================
    # MONITORING TOOLS
    # ========================================================================

    async def battery_report(self) -> Dict[str, Any]:
        """Get battery status report"""
        print(f"🔍 battery_report called (demo_mode={self.demo_mode})")
        if self.demo_mode:
            return self._load_demo_data("battery_report.json")
        if not self.connected:
            return {"success": False, "error": self.init_error or "MCP bridge not connected"}
        return await self._live_functions['battery_report']()

    async def find_unavailable_entities(self) -> Dict[str, Any]:
        """Find unavailable entities"""
        print(f"🔍 find_unavailable_entities called (demo_mode={self.demo_mode})")
        if self.demo_mode:
            return self._load_demo_data("find_unavailable_entities.json")
        if not self.connected:
            return {"success": False, "error": self.init_error or "MCP bridge not connected"}
        return await self._live_functions['find_unavailable_entities']()

    async def find_stale_entities(self, hours: int = 2) -> Dict[str, Any]:
        """Find stale entities (not updated recently)"""
        print(f"🔍 find_stale_entities called (demo_mode={self.demo_mode})")
        if self.demo_mode:
            return self._load_demo_data("find_stale_entities.json")
        if not self.connected:
            return {"success": False, "error": self.init_error or "MCP bridge not connected"}
        return await self._live_functions['find_stale_entities'](hours=hours)

    async def get_repair_items(self) -> Dict[str, Any]:
        """Get Home Assistant repair items"""
        print(f"🔍 get_repair_items called (demo_mode={self.demo_mode})")
        if self.demo_mode:
            return self._load_demo_data("get_repair_items.json")
        if not self.connected:
            return {"success": False, "error": self.init_error or "MCP bridge not connected"}
        return await self._live_functions['get_repair_items']()

    async def get_update_status(self) -> Dict[str, Any]:
        """Get available updates"""
        print(f"🔍 get_update_status called (demo_mode={self.demo_mode})")
        if self.demo_mode:
            return self._load_demo_data("get_update_status.json")
        if not self.connected:
            return {"success": False, "error": self.init_error or "MCP bridge not connected"}
        return await self._live_functions['get_update_status']()

    async def get_error_log(self) -> Dict[str, Any]:
        """Get error log"""
        print(f"🔍 get_error_log called (demo_mode={self.demo_mode})")
        if self.demo_mode:
            return self._load_demo_data("get_error_log.json")
        if not self.connected:
            return {"success": False, "error": self.init_error or "MCP bridge not connected"}
        result = await self._live_functions['get_error_log']()
        # Wrap result if it's a list
        if isinstance(result, list):
            return {"errors": result, "count": len(result)}
        return result

    # ========================================================================
    # ENTITY MANAGEMENT
    # ========================================================================

    async def list_entities(self, domain: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """List entities"""
        print(f"🔍 list_entities called (demo_mode={self.demo_mode})")
        if self.demo_mode and not self.connected:
            return self._load_demo_data("list_entities.json")
        if not self.connected:
            return {"success": False, "error": self.init_error or "MCP bridge not connected"}

        live_fn = self._live_functions.get('list_entities') or self._live_functions.get('get_entities')
        if not live_fn:
            return {"success": False, "error": "list_entities not available"}

        entities = await live_fn(domain=domain, limit=int(limit) if limit else 100)

        # Ensure proper format
        if isinstance(entities, list):
            return {
                "success": True,
                "entities": entities,
                "total_count": len(entities),
                "demo_mode": False
            }
        if isinstance(entities, dict) and "entities" in entities:
            entities["success"] = True
        return entities

    async def list_automations(self) -> List[Dict[str, Any]]:
        """List all automations"""
        print(f"🔍 list_automations called (demo_mode={self.demo_mode})")
        if self.demo_mode and not self.connected:
            data = self._load_demo_data("list_automations.json")
            return data.get("automations", [])
        if not self.connected:
            return {"success": False, "error": self.init_error or "MCP bridge not connected"}
        live_fn = self._live_functions.get('list_automations') or self._live_functions.get('get_automations')
        return await live_fn()

    async def get_entity_statistics(self, entity_id: str, period_hours: int = 24) -> Dict[str, Any]:
        """Get entity statistics"""
        print(f"🔍 get_entity_statistics called for {entity_id} (demo_mode={self.demo_mode})")
        if self.demo_mode:
            return self._load_demo_data("get_entity_statistics.json")
        if not self.connected:
            return {"success": False, "error": self.init_error or "MCP bridge not connected"}
        return await self._live_functions['get_entity_statistics'](
            entity_id=entity_id,
            period_hours=period_hours
        )

    async def identify_device(self, device_id_or_entity_id: str, pattern: str = "auto", duration: int = 3) -> Dict[str, Any]:
        """Identify device physically (flash/beep)"""
        print(f"🔍 identify_device called for {device_id_or_entity_id} (demo_mode={self.demo_mode})")
        if self.demo_mode:
            return {
                "success": True,
                "message": f"[DEMO] Would identify device: {device_id_or_entity_id}",
                "pattern": pattern,
                "duration": duration,
                "demo_mode": True
            }
        if not self.connected:
            return {"success": False, "error": self.init_error or "MCP bridge not connected"}
        return await self._live_functions['identify_device'](
            device_id_or_entity_id=device_id_or_entity_id,
            pattern=pattern,
            duration=duration
        )

    # ========================================================================
    # RESOURCES (Markdown reports)
    # ========================================================================

    async def get_resource(self, uri: str) -> str:
        """Get MCP resource (markdown report)"""
        print(f"🔍 get_resource called for {uri} (demo_mode={self.demo_mode})")
        if self.demo_mode:
            # Map URIs to demo files
            uri_map = {
                "ha://diagnostics/zigbee-mesh": "resource_zigbee_mesh.md",
                "ha://diagnostics/system-health": "resource_system_health.md",
                "ha://diagnostics/system": "resource_system.md",
            }
            filename = uri_map.get(uri, "resource_not_found.md")
            filepath = self.demo_data_dir / filename

            if filepath.exists():
                with open(filepath, 'r') as f:
                    return f.read()
            return f"# Resource Not Found\n\nURI: {uri}\n\n(Demo data not available)"

        # For LIVE mode, resources aren't implemented via direct imports
        return f"# Resource Not Available\n\nResources are only available in DEMO mode.\n\nURI: {uri}"

    # ========================================================================
    # ORCHESTRATION (Combined operations)
    # ========================================================================

    async def run_full_diagnostics(self) -> Dict[str, Any]:
        """
        Run complete diagnostic suite (diagnose_everything)

        Combines:
        - diagnose_system
        - audit_zigbee_mesh
        - find_orphan_entities
        - detect_automation_conflicts
        - energy_consumption_report
        - battery_report
        """
        print(f"🔍 run_full_diagnostics called (demo_mode={self.demo_mode})")
        results = {}

        if not self.demo_mode and not self.connected:
            return {
                "error": self.init_error or "MCP bridge not connected",
                "success": False,
                "demo_mode": False
            }

        # Run all diagnostics in parallel
        tasks = {
            "system": self.diagnose_system(include_entities=True),
            "zigbee_mesh": self.audit_zigbee_mesh(),
            "orphan_entities": self.find_orphan_entities(),
            "automation_conflicts": self.detect_automation_conflicts(),
            "energy": self.energy_consumption_report(),
            "battery": self.battery_report(),
            "repairs": self.get_repair_items() if hasattr(self, 'get_repair_items') else None,
            "updates": self.get_update_status() if hasattr(self, 'get_update_status') else None,
        }

        # Execute all tasks
        task_coros = [t for t in tasks.values() if t is not None]
        task_results = await asyncio.gather(*task_coros, return_exceptions=True)

        # Combine results
        idx = 0
        for key, coro in tasks.items():
            if coro is None:
                continue
            result = task_results[idx]
            idx += 1
            if isinstance(result, Exception):
                results[key] = {"error": str(result), "success": False}
            else:
                results[key] = result

        # Calculate overall health score
        system_score = results.get("system", {}).get("global_health_score", 0)
        zigbee_score = results.get("zigbee_mesh", {}).get("mesh_health_score", 100)

        overall_score = (system_score * 0.7 + zigbee_score * 0.3)

        return {
            "overall_health_score": round(overall_score, 1),
            "timestamp": datetime.now().isoformat(),
            "diagnostics": results,
            "demo_mode": self.demo_mode
        }


# Global bridge instance
_bridge: Optional[MCPBridge] = None

def get_bridge() -> MCPBridge:
    """Get or create global MCP bridge instance"""
    global _bridge
    if _bridge is None:
        _bridge = MCPBridge()
    return _bridge

def reset_bridge(demo_mode: bool = None) -> MCPBridge:
    """
    Reset and recreate the global bridge instance.
    Useful when switching between DEMO and LIVE modes.

    Args:
        demo_mode: True for DEMO, False for LIVE, None to auto-detect from env

    Returns:
        New MCPBridge instance
    """
    global _bridge
    print(f"🔄 reset_bridge called with demo_mode={demo_mode}")

    # Force reimport of app.config to pick up new env vars
    if not demo_mode and demo_mode is not None:
        # Reload the config module to pick up new environment variables
        import importlib
        try:
            import app.config
            importlib.reload(app.config)
            print("   ✅ Reloaded app.config with new env vars")
        except:
            pass

    _bridge = None  # Destroy existing instance
    _bridge = MCPBridge(demo_mode=demo_mode)
    return _bridge
