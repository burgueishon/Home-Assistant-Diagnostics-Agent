"""
Gemini AI Agent with MCP Tool Calling

Uses Gemini 2.0 Flash with function calling to orchestrate MCP diagnostics.
Adds OpenAI fallback for natural-language explanation when Gemini fails.
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

FEATURE_LLAMAINDEX = os.getenv("FEATURE_LLAMAINDEX", "true").lower() == "true"
FEATURE_BLAXEL = os.getenv("FEATURE_BLAXEL", "false").lower() == "true"

# Don't import Gemini at module level - only when needed
GEMINI_AVAILABLE = False

from mcp_bridge import get_bridge

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class DiagnosticAgent:
    """AI Agent powered by Gemini with MCP tool access"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Diagnostic Agent
        
        Args:
            api_key: Gemini API key (or set GEMINI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.bridge = get_bridge()
        self.conversation_history = []
        self.tools_used = []
        self.model = None
        self.chat = None
        self.openai_client = None
        self.llama_index_engine = None
        
        # Don't initialize Gemini in __init__ - do it on first use
        if not self.api_key:
            print("⚠️ No GEMINI_API_KEY found. Agent will run in demo mode.")
        # Initialize OpenAI client lazily if key present
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and OpenAI is not None:
            try:
                self.openai_client = OpenAI(api_key=openai_key)
            except Exception as e:
                print(f"⚠️ Failed to initialize OpenAI client: {e}")
        elif openai_key:
            print("⚠️ OpenAI package not installed; fallback disabled.")
    
    def _setup_function_declarations(self):
        """Setup MCP diagnostic tools for Gemini function calling"""
        try:
            from google.generativeai import types
        except ImportError:
            return []

        tools: List[types.FunctionDeclaration] = []

        # Core known tools with schemas
        tools.extend([
            types.FunctionDeclaration(
                name="diagnose_system",
                description="Run complete Home Assistant system diagnostic check. Returns overall health score, detected issues by severity, and actionable recommendations.",
                parameters={
                    "type": "object",
                    "properties": {
                        "include_entities": {
                            "type": "boolean",
                            "description": "Include detailed entity analysis (default: true)"
                        }
                    }
                }
            ),
            types.FunctionDeclaration(
                name="diagnose_issue",
                description="Deep-diagnose a specific entity by entity_id. Returns summary, severity, root causes, and recommended fixes.",
                parameters={
                    "type": "object",
                    "properties": {
                        "entity_id": {"type": "string", "description": "Home Assistant entity_id to diagnose"}
                    },
                    "required": ["entity_id"]
                }
            ),
            types.FunctionDeclaration(
                name="audit_zigbee_mesh",
                description="Analyze Zigbee mesh network health. Returns mesh health score (0-100), weak links with LQI/RSSI values, orphan devices, and router placement recommendations.",
                parameters={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of devices to analyze (default: 100)"
                        }
                    }
                }
            ),
            types.FunctionDeclaration(
                name="find_orphan_entities",
                description="Find entities not used in any automations, scripts, or scenes. Returns total orphan count, percentage, and breakdown by domain. Useful for cleanup.",
                parameters={
                    "type": "object",
                    "properties": {}
                }
            ),
            types.FunctionDeclaration(
                name="detect_automation_conflicts",
                description="Detect race conditions, infinite loops, and conflicting automations. Returns total conflicts, race conditions (multiple automations on same entity), and circular dependencies.",
                parameters={
                    "type": "object",
                    "properties": {}
                }
            ),
            types.FunctionDeclaration(
                name="battery_report",
                description="Get battery health report for all battery-powered devices. Returns low battery count, critical batteries, and device-level battery percentages.",
                parameters={
                    "type": "object",
                    "properties": {}
                }
            ),
            types.FunctionDeclaration(
                name="energy_consumption_report",
                description="Generate energy consumption report with cost estimates. Returns total consumption, top consumers, cost estimate, and energy-saving recommendations.",
                parameters={
                    "type": "object",
                    "properties": {
                        "period_hours": {
                            "type": "integer",
                            "description": "Time period in hours for the report (default: 24)"
                        }
                    }
                }
            ),
            types.FunctionDeclaration(
                name="identify_device",
                description="Physically identify a device (flash/beep/toggle) by entity_id or device_id.",
                parameters={
                    "type": "object",
                    "properties": {
                        "device_id_or_entity_id": {"type": "string", "description": "Device ID or entity_id"},
                        "pattern": {"type": "string", "description": "auto, flash, toggle, color, beep"},
                        "duration": {"type": "integer", "description": "Duration in seconds"}
                    },
                    "required": ["device_id_or_entity_id"]
                }
            ),
            types.FunctionDeclaration(
                name="list_entities",
                description="List entities (optionally by domain). Useful to confirm available entity_ids.",
                parameters={
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string", "description": "Optional domain filter"},
                        "limit": {"type": "integer", "description": "Max entities to return (default 100)"}
                    }
                }
            ),
            types.FunctionDeclaration(
                name="list_automations",
                description="List automations with entity_id and alias.",
                parameters={"type": "object", "properties": {}}
            ),
            types.FunctionDeclaration(
                name="find_unavailable_entities",
                description="Find entities that are currently unavailable.",
                parameters={"type": "object", "properties": {}}
            ),
            types.FunctionDeclaration(
                name="find_stale_entities",
                description="Find entities not updating within a timeframe.",
                parameters={
                    "type": "object",
                    "properties": {
                        "hours": {"type": "integer", "description": "Threshold in hours (default 2)"}
                    }
                }
            ),
            types.FunctionDeclaration(
                name="get_repair_items",
                description="Return Home Assistant repair panel items.",
                parameters={"type": "object", "properties": {}}
            ),
            types.FunctionDeclaration(
                name="get_update_status",
                description="Return available updates for core/addons/devices.",
                parameters={"type": "object", "properties": {}}
            ),
            types.FunctionDeclaration(
                name="get_error_log",
                description="Return Home Assistant error log summary.",
                parameters={"type": "object", "properties": {}}
            ),
        ])

        # Optional LlamaIndex tool
        if FEATURE_LLAMAINDEX:
            tools.append(
                types.FunctionDeclaration(
                    name="query_diagnostics_knowledge",
                    description="Query the diagnostics knowledge base built from demo data and markdown resources.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "Question to ask the knowledge base"
                            }
                        },
                        "required": ["question"]
                    }
                )
            )
        # Optional Blaxel history tool
        if FEATURE_BLAXEL:
            tools.append(
                types.FunctionDeclaration(
                    name="query_diagnostic_history",
                    description="Retrieve saved diagnostic snapshots from Blaxel history.",
                    parameters={"type": "object", "properties": {}}
                )
            )

        # Generic declarations for any other MCP functions the bridge exposes
        for name in self.bridge.available_tools():
            if any(t.name == name for t in tools):
                continue
            tools.append(
                types.FunctionDeclaration(
                    name=name,
                    description=f"Invoke MCP tool '{name}' (auto-generated).",
                    parameters={"type": "object", "properties": {}}
                )
            )

        return tools

    def _ensure_model_loaded(self):
        """Lazy load Gemini model on first use"""
        if self.model is not None or not self.api_key:
            return

        try:
            import google.generativeai as genai

            # Configure Gemini
            genai.configure(api_key=self.api_key)

            # Get function declarations
            tools = self._setup_function_declarations()

            # Initialize model with function calling support
            self.model = genai.GenerativeModel(
                model_name='gemini-2.0-flash-exp',  # Best for function calling
                tools=tools if tools else None,
                system_instruction="""You are an expert Home Assistant diagnostic AI assistant.

You have access to the Home Assistant Diagnostics MCP server with ~39 tools and markdown resources.

When users ask about their Home Assistant system:
- Call the available MCP tools to gather accurate data before answering
- Combine multiple tools when needed for coverage (e.g., diagnose_system + audit_zigbee_mesh + battery_report)
- Explain issues and fixes in clear, user-friendly language
- Be concise but thorough

Core tools (always available):
- diagnose_system: Complete system health check
- audit_zigbee_mesh: Zigbee mesh analysis with health scoring
- find_orphan_entities: Find unused entities for cleanup
- detect_automation_conflicts: Find race conditions and loops
- battery_report: Battery health monitoring
- energy_consumption_report: Energy usage and cost analysis
- find_unavailable_entities / find_stale_entities: Availability and freshness checks
- list_entities / list_automations: Discovery helpers
- identify_device: Physical identify (flash/beep/toggle)
- get_repair_items / get_update_status / get_error_log / get_entity_statistics: Maintenance and diagnostics

You may also see additional MCP tools exposed dynamically—feel free to call any that are declared.
When appropriate, use multiple tools to provide comprehensive diagnostics."""
            )

            # Start chat
            self.chat = self.model.start_chat(history=[])
            print("✅ Gemini model loaded successfully with function calling")

        except Exception as e:
            print(f"⚠️ Failed to load Gemini: {e}")
            self.model = None
            self.chat = None

    def _extract_text(self, response) -> str:
        """Safely extract text from a Gemini response."""
        if not response:
            return "✅ Analysis complete."
        try:
            return response.text
        except Exception:
            texts = []
            for cand in getattr(response, "candidates", []) or []:
                if not getattr(cand, "content", None):
                    continue
                for part in getattr(cand.content, "parts", []) or []:
                    if getattr(part, "text", None):
                        texts.append(part.text)
            return "\n".join(texts) if texts else "✅ Analysis complete."
    
    async def chat_async(self, user_message: str) -> Tuple[str, List[Dict], bool]:
        """
        Send message to agent and get response with function calling support

        Flow:
        1. Send user message to Gemini
        2. While Gemini requests function calls:
           a. Execute the requested tool
           b. Send result back to Gemini
        3. Return final text + list of tools used

        Returns:
            (response_text, tools_used_list, fallback_used)
            where tools_used_list is: [{"name": str, "args": dict, "result": dict}, ...]
            fallback_used indicates whether OpenAI fallback produced the response
        """
        # Ensure model is loaded
        self._ensure_model_loaded()

        if not self.model:
            # No Gemini available; try OpenAI fallback if configured
            if self.openai_client:
                explanation = await self._openai_explanation(
                    user_message,
                    [],
                    reason="GEMINI_API_KEY not configured or Gemini unavailable"
                )
                return (explanation, [], True)
            return ("⚠️ Gemini API not configured. Please set GEMINI_API_KEY.", [], False)

        tools_used_this_turn = []

        try:
            # Import genai for function response
            import google.generativeai as genai

            # Send initial message
            response = self.chat.send_message(user_message)

            # Multi-turn function calling loop
            max_iterations = 10  # Prevent infinite loops
            iteration = 0

            while iteration < max_iterations:
                # Check if response has parts
                if not response.candidates:
                    break

                candidate = response.candidates[0]
                if not candidate.content or not candidate.content.parts:
                    break

                # Collect all function calls in this turn
                call_parts = []
                for part in candidate.content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        call_parts.append(part.function_call)

                if not call_parts:
                    break  # no function calls, final response

                response_parts = []
                for function_call in call_parts:
                    tool_name = function_call.name
                    tool_args = dict(function_call.args) if function_call.args else {}

                    print(f"🔧 Gemini requested tool: {tool_name} with args: {tool_args}")

                    # Safety check for dangerous operations
                    if self._is_dangerous_tool(tool_name):
                        return (
                            f"⚠️ **Safety Confirmation Required**\n\nThe tool `{tool_name}` requires explicit user confirmation as it can affect physical devices or system state.\n\nPlease confirm if you want to proceed with this action.",
                            tools_used_this_turn
                        )

                    # Execute the tool via MCP bridge
                    tool_result = await self._execute_tool(tool_name, tool_args)

                    # Track tool usage
                    tools_used_this_turn.append({
                        "name": tool_name,
                        "args": tool_args,
                        "result": tool_result
                    })

                    response_parts.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=tool_name,
                                response={"result": tool_result}
                            )
                        )
                    )

                # Send all function responses together
                response = self.chat.send_message(response_parts)

                iteration += 1

            # Check for loop timeout
            if iteration >= max_iterations:
                return (
                    "⚠️ Maximum function call iterations reached. Response may be incomplete.",
                    tools_used_this_turn,
                    False
                )

            # Extract final text response
            final_text = self._extract_text(response)

            return (final_text, tools_used_this_turn, False)

        except Exception as e:
            is_quota = "ResourceExhausted" in str(type(e)) or "quota" in str(e).lower()

            # Quota handling: try OpenAI fallback first if configured
            if is_quota:
                if self.openai_client:
                    try:
                        explanation = await self._openai_explanation(
                            user_message,
                            tools_used_this_turn,
                            reason="Gemini quota exceeded"
                        )
                        return (explanation, tools_used_this_turn, True)
                    except Exception as oe:
                        print(f"❌ OpenAI fallback failed after Gemini quota error: {oe}")
                return ("⚠️ Gemini quota exceeded. Please wait or upgrade your plan.", tools_used_this_turn, False)

            # Other errors
            import traceback
            error_detail = traceback.format_exc()
            print(f"❌ Error in chat_async: {error_detail}")
            # Fallback to OpenAI explanation if available
            try:
                explanation = await self._openai_explanation(
                    user_message,
                    tools_used_this_turn,
                    reason=str(e)
                )
                return (explanation, tools_used_this_turn, True)
            except Exception as oe:
                print(f"❌ OpenAI fallback failed: {oe}")
                return (f"❌ Error: {str(e)}", tools_used_this_turn, False)
    
    def chat_sync(self, user_message: str) -> Tuple[str, List[str]]:
        """Synchronous wrapper for Gradio"""
        return asyncio.run(self.chat_async(user_message))
    
    def clear_history(self):
        """Clear conversation history and start fresh"""
        self.conversation_history = []
        self.tools_used = []
        if self.model and self.chat:
            self.chat = self.model.start_chat(history=[])

    def reset_conversation(self):
        """Alias for clear_history (for UI compatibility)"""
        self.clear_history()

    async def _openai_explanation(self, message: str, tools_used: List[Dict], reason: str = "") -> str:
        """
        Generate a natural-language explanation using OpenAI when Gemini fails.
        Does NOT perform function calling; only summarizes existing tool results.
        """
        if not self.openai_client:
            return "⚠️ OpenAI fallback not configured. Please set OPENAI_API_KEY."

        tools_json = json.dumps(tools_used, indent=2)
        reason_text = f"Gemini unavailable or failed. Reason: {reason}" if reason else "Gemini unavailable or failed."

        completion = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert Home Assistant diagnostic system. "
                        "Your only job is to convert tool outputs into clear, helpful explanations for a user. "
                        "Do NOT invent values. Use ONLY the JSON results provided. "
                        "If there are no tool results because Gemini was unavailable, clearly state that and advise setting GEMINI_API_KEY for full diagnostics."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"User message:\n{message}\n\n"
                        f"{reason_text}\n\n"
                        f"Tool results (JSON):\n{tools_json}"
                    ),
                },
            ],
        )

        return completion.choices[0].message.content

    async def _ensure_llamaindex(self):
        """Lazy-init LlamaIndex engine if feature flag is enabled."""
        if not FEATURE_LLAMAINDEX:
            return None
        if self.llama_index_engine is not None:
            return self.llama_index_engine

        try:
            from llama_index.core import KeywordTableIndex, Document, SimpleDirectoryReader
            import glob
        except Exception as e:
            print(f"⚠️ LlamaIndex not available: {e}")
            return None

        docs: List[Document] = []

        # Load demo_data JSON as text
        for path in glob.glob(os.path.join("demo_data", "*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                docs.append(Document(text=json.dumps(data, indent=2), metadata={"source": path}))
            except Exception as e:
                print(f"⚠️ Failed to load {path}: {e}")

        # Load markdown resources if present
        resources_path = os.path.join("resources")
        if os.path.isdir(resources_path):
            try:
                reader = SimpleDirectoryReader(resources_path, required_exts=[".md"], recursive=True)
                docs.extend(reader.load_data())
            except Exception as e:
                print(f"⚠️ Failed to load resources markdown: {e}")

        if not docs:
            print("⚠️ No documents loaded for LlamaIndex.")
            return None

        try:
            index = KeywordTableIndex.from_documents(docs)
            self.llama_index_engine = index.as_query_engine()
            return self.llama_index_engine
        except Exception as e:
            print(f"⚠️ Failed to build LlamaIndex: {e}")
            return None

    async def query_diagnostics_knowledge(self, question: str) -> Dict[str, Any]:
        """Query local diagnostics knowledge base."""
        if not FEATURE_LLAMAINDEX:
            return {"error": "LlamaIndex feature is disabled."}

        engine = await self._ensure_llamaindex()
        if engine is None:
            return {"error": "LlamaIndex not available or failed to load documents."}

        try:
            resp = engine.query(question)
            return {"answer": str(resp)}
        except Exception as e:
            return {"error": f"LlamaIndex query failed: {e}"}

    async def query_diagnostic_history(self) -> Dict[str, Any]:
        """Return stored diagnostic snapshots."""
        if not FEATURE_BLAXEL:
            return {"error": "Blaxel feature is disabled."}
        try:
            from blaxel_backend import get_snapshots
            return get_snapshots()
        except Exception as e:
            return {"error": f"Blaxel history lookup failed: {e}"}


    def _is_dangerous_tool(self, tool_name: str) -> bool:
        """
        Check if tool requires explicit user confirmation

        Dangerous tools are those that:
        - Affect physical devices (identify_device)
        - Restart services (restart_home_assistant)
        - Modify entity states (entity_action, turn_on, turn_off)

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if tool requires confirmation, False otherwise
        """
        dangerous_tools = [
            'identify_device',
            'restart_home_assistant',
            'entity_action',
            'turn_on',
            'turn_off',
            'reload_core_config',
        ]
        return tool_name in dangerous_tools

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute MCP diagnostic tool via bridge

        Maps tool names to bridge methods and handles execution.

        Args:
            tool_name: Name of the MCP tool to execute
            args: Arguments for the tool (as dict)

        Returns:
            Tool result as dict (includes success status, data, errors)
        """
        # Map tool names to bridge methods
        tool_map = {
            'diagnose_system': self.bridge.diagnose_system,
            'audit_zigbee_mesh': self.bridge.audit_zigbee_mesh,
            'find_orphan_entities': self.bridge.find_orphan_entities,
            'detect_automation_conflicts': self.bridge.detect_automation_conflicts,
            'battery_report': self.bridge.battery_report,
            'energy_consumption_report': self.bridge.energy_consumption_report,
            'diagnose_issue': self.bridge.diagnose_issue,
            'identify_device': self.bridge.identify_device,
            'list_entities': self.bridge.list_entities,
            'get_entities': self.bridge.list_entities,
            'list_automations': self.bridge.list_automations,
            'get_automations': self.bridge.list_automations,
            'find_unavailable_entities': self.bridge.find_unavailable_entities,
            'find_stale_entities': self.bridge.find_stale_entities,
            'get_repair_items': self.bridge.get_repair_items,
            'get_update_status': self.bridge.get_update_status,
            'get_error_log': self.bridge.get_error_log,
        }

        # Optional LlamaIndex tool
        if FEATURE_LLAMAINDEX:
            tool_map['query_diagnostics_knowledge'] = self.query_diagnostics_knowledge
        # Optional Blaxel history
        if FEATURE_BLAXEL:
            tool_map['query_diagnostic_history'] = self.query_diagnostic_history

        if tool_name not in tool_map:
            try:
                return await self.bridge.call_tool(tool_name, **args)
            except Exception as e:
                return {
                    "error": f"Unknown tool: {tool_name}. {str(e)}",
                    "available_tools": list(tool_map.keys())
                }

        try:
            # Get the bridge method
            bridge_method = tool_map[tool_name]

            # Execute the tool with provided arguments
            result = await bridge_method(**args)

            # Ensure result is JSON-serializable
            if not isinstance(result, dict):
                result = {"data": str(result)}

            # Save snapshot to Blaxel (local stub) if enabled
            if FEATURE_BLAXEL and tool_name != "query_diagnostic_history":
                try:
                    from blaxel_backend import save_snapshot
                    save_snapshot(tool_name, args, result)
                except Exception as e:
                    print(f"⚠️ Failed to save Blaxel snapshot: {e}")

            return result

        except TypeError as e:
            # Handle parameter mismatch
            return {
                "error": f"Invalid arguments for {tool_name}: {str(e)}",
                "provided_args": args
            }
        except Exception as e:
            # Handle execution errors
            import traceback
            return {
                "error": f"Tool execution failed: {str(e)}",
                "tool_name": tool_name,
                "traceback": traceback.format_exc()
            }


# Singleton instance
_agent_instance = None

def get_agent() -> DiagnosticAgent:
    """Get singleton agent instance"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = DiagnosticAgent()
    return _agent_instance
