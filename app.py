"""
Home Assistant Diagnostics Agent - Gradio UI for Home Assistant MCP Diagnostics

Built for Hugging Face MCP Hackathon 2025
Track: MCP in Action - Consumer
"""

import os
import gradio as gr
import asyncio
import re
import json
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional

# Load custom CSS once
CUSTOM_CSS: str = ""
try:
    CUSTOM_CSS = (Path(__file__).parent / "custom.css").read_text(encoding="utf-8")
except Exception:
    CUSTOM_CSS = ""
# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import bridge (agent will be loaded lazily)
from mcp_bridge import get_bridge, reset_bridge

# Agent will be initialized on first use
agent = None

def get_or_init_agent():
    """Lazy initialization of agent"""
    global agent
    # Recreate agent if bridge changed (e.g., switched demo/live)
    from agent import get_agent, _agent_instance  # type: ignore
    if agent is None or agent.bridge is not get_bridge():
        # Reset singleton inside agent module
        try:
            import agent as agent_module  # type: ignore
            agent_module._agent_instance = None
        except Exception:
            pass
        agent = get_agent()
    return agent

# Theme
THEME = gr.themes.Soft(
    primary_hue="blue",
    secondary_hue="cyan",
    neutral_hue="slate",
)

def render_mode_badge() -> str:
    """Render the mode badge based on current bridge state."""
    bridge = get_bridge()
    if not bridge.demo_mode and bridge.connected:
        mode_text = "🟢 LIVE MODE"
        mode_color = "#10b981"
        subtitle = "Connected to live Home Assistant"
    elif not bridge.demo_mode and not bridge.connected:
        mode_text = "⚠️ LIVE MODE (Not connected)"
        mode_color = "#f59e0b"
        subtitle = f"Error: {bridge.init_error or 'Bridge not connected'}"
    else:
        mode_text = "🔴 DEMO MODE"
        mode_color = "#f59e0b"
        subtitle = "Default DEMO mode for non-Home Assistant users. For HA users, configure credentials in Settings to switch to LIVE."

    return f"""
    <div style="text-align: center; padding: 10px; background: #1A1A1C; border-radius: 10px; margin-bottom: 20px; border: 1px solid {mode_color};">
        <span style="font-weight: bold; color: {mode_color};">{mode_text}</span>
        <span style="margin-left: 15px; color: #E8E8E8; font-size: 0.9em;">{subtitle}</span>
    </div>
    """

# ============================================================================
# TAB 1: HOME HEALTH DASHBOARD
# ============================================================================

def format_health_card(title: str, score: float, status: str, details: str = "") -> str:
    """Format a health card with color coding"""
    if score >= 90:
        color = "#10b981"  # green
        emoji = "🟢"
    elif score >= 70:
        color = "#f59e0b"  # yellow  
        emoji = "🟡"
    elif score >= 50:
        color = "#ef4444"  # orange
        emoji = "🟠"
    else:
        color = "#dc2626"  # red
        emoji = "🔴"
    
    bg_color = "#1A1A1C"
    
    return f"""
<div style="border: 3px solid {color}; border-radius: 12px; padding: 20px; margin: 10px 0; background: {bg_color}; color:#E8E8E8;">
    <h3 style="margin: 0 0 10px 0; color: {color};">{emoji} {title}</h3>
    <div style="font-size: 2.5em; font-weight: bold; color: {color}; margin: 10px 0;">{score:.1f}/100</div>
    <div style="color: #E8E8E8; font-weight: 600; font-size: 1.1em; margin-top: 5px;">{status}</div>
    {f'<div style="margin-top: 10px; font-size: 0.95em; color: #B0B0B0;">{details}</div>' if details else ''}
</div>
"""

async def run_full_diagnostics_async():
    """Run complete diagnostic suite"""
    try:
        bridge = get_bridge()
        print(f"🔍 DEBUG: Bridge mode = {bridge.demo_mode}")
        result = await bridge.run_full_diagnostics()

        # Surface bridge errors
        if isinstance(result, dict) and result.get("error"):
            raise Exception(result.get("error"))
        
        # Extract data
        overall_score = result.get("overall_health_score", 0)
        diagnostics = result.get("diagnostics", {})
        
        # System Health
        system = diagnostics.get("system", {})
        system_score = system.get("global_health_score", 0)
        system_issues = system.get("total_issues", 0)
        severity = system.get("severity_breakdown", {})
        issues_by_category = system.get("issues_by_category", {})
        
        # Zigbee Mesh
        zigbee = diagnostics.get("zigbee_mesh", {})
        mesh_score = zigbee.get("mesh_health_score", 0)
        mesh_devices = zigbee.get("total_devices", 0)
        weak_links = len(zigbee.get("weak_links", []))
        
        # Batteries
        battery = diagnostics.get("battery", {})
        low_batteries = battery.get("low_battery_count", 0)
        critical_batteries = battery.get("critical_count", 0)
        
        # Orphans
        orphans = diagnostics.get("orphan_entities", {})
        total_orphans = orphans.get("total_orphans", 0)
        orphan_pct = orphans.get("orphan_percentage", 0)
        
        # Conflicts
        conflicts = diagnostics.get("automation_conflicts", {})
        total_conflicts = conflicts.get("total_conflicts", 0)
        
        # Energy
        energy = diagnostics.get("energy", {})
        energy_consumption = energy.get("total_consumption", 0)
        energy_cost = energy.get("cost_estimate", {}).get("period_cost", 0)
        
        # Updates & Repairs
        updates = diagnostics.get("updates", {})
        total_updates = updates.get("total_updates_available", 0)
        
        repairs = diagnostics.get("repairs", {})
        total_repairs = repairs.get("total_issues", 0)
        
        # Build dashboard HTML
        dashboard_html = f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #161617; padding: 20px; border-radius: 16px; border: 1px solid #2A2A2C; color:#E8E8E8;">
    <h1 style="text-align: center; color: #E8E8E8; margin-bottom: 30px;">🏥 System Health Dashboard</h1>
    
    {format_health_card(
        "Overall System Health", 
        overall_score, 
        "EXCELLENT" if overall_score >= 90 else "GOOD" if overall_score >= 70 else "FAIR" if overall_score >= 50 else "CRITICAL",
        f"{system_issues} total issues found • {severity.get('critical', 0)} critical • {severity.get('high', 0)} high priority"
    )}
    
    <!-- ISSUES BREAKDOWN TABLE -->
    <div style="margin: 30px 0; padding: 25px; background: #161617; border-radius: 12px; border: 1px solid #2A2A2C; box-shadow: none;">
        <h2 style="color: #E8E8E8; margin-top: 0; border-bottom: 3px solid #FF7A00; padding-bottom: 10px;">📋 Detected Issues ({system_issues} total)</h2>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px; color:#E8E8E8;">
            <thead>
                <tr style="background: #1A1A1C;">
                    <th style="padding: 12px; text-align: left; border-bottom: 2px solid #2A2A2C; color: #E8E8E8; font-weight: 600;">Severity</th>
                    <th style="padding: 12px; text-align: left; border-bottom: 2px solid #2A2A2C; color: #E8E8E8; font-weight: 600;">Category</th>
                    <th style="padding: 12px; text-align: left; border-bottom: 2px solid #2A2A2C; color: #E8E8E8; font-weight: 600;">Description</th>
                    <th style="padding: 12px; text-align: center; border-bottom: 2px solid #2A2A2C; color: #E8E8E8; font-weight: 600;">Count</th>
                </tr>
            </thead>
            <tbody>
"""
        
        # Helpers to keep details/counts clean for mixed data structures
        def _clean_details(value: Any) -> str:
            if value is None or value == "":
                return ""
            if isinstance(value, dict):
                parts = []
                for k, v in value.items():
                    if v is None:
                        continue
                    if isinstance(v, (list, tuple, set)):
                        vals = list(v)
                        snippet = ", ".join(map(str, vals[:5]))
                        if len(vals) > 5:
                            snippet += " ..."
                        parts.append(f"{k.replace('_', ' ').title()}: {snippet}")
                    elif isinstance(v, dict):
                        nested = ", ".join(f"{subk}: {subv}" for subk, subv in v.items())
                        parts.append(f"{k.replace('_', ' ').title()}: {nested}")
                    else:
                        parts.append(f"{k.replace('_', ' ').title()}: {v}")
                return " • ".join(parts)
            if isinstance(value, (list, tuple, set)):
                vals = list(value)
                snippet = ", ".join(map(str, vals[:5]))
                if len(vals) > 5:
                    snippet += " ..."
                return snippet
            return str(value)

        def _extract_count(issue: Dict[str, Any], main_issue: str) -> Optional[int]:
            numeric_fields = (
                "entity_count", "count", "error_count", "warning_count",
                "update_count", "device_count", "total", "orphan_count"
            )
            for field in numeric_fields:
                val = issue.get(field)
                if isinstance(val, (int, float)):
                    return int(val)

            for list_field in ("devices", "entities", "items"):
                val = issue.get(list_field)
                if isinstance(val, (list, tuple, set)):
                    return len(val)

            if isinstance(main_issue, str):
                match = re.search(r"(\d+)", main_issue)
                if match:
                    return int(match.group(1))
            return None

        # Add all issues from categories
        issue_rows = []
        for category, issues_list in issues_by_category.items():
            for issue in issues_list:
                severity_level = issue.get("severity", "low")
                main_issue = issue.get("issue") or issue.get("description") or "N/A"

                details_text = _clean_details(issue.get("details"))
                description = (
                    main_issue if not details_text
                    else f"{main_issue}<br><small style='color: #6b7280;'>{details_text}</small>"
                )

                count = _extract_count(issue, main_issue)

                # Severity badge
                if severity_level == "critical":
                    badge = "<span style='background: #2b1616; color: #fca5a5; padding: 4px 10px; border-radius: 10px; font-weight: 700; font-size: 0.85em; border: 1px solid #ef4444;'>🔴 CRITICAL</span>"
                elif severity_level == "high":
                    badge = "<span style='background: #2a1c0f; color: #fdba74; padding: 4px 10px; border-radius: 10px; font-weight: 700; font-size: 0.85em; border: 1px solid #f97316;'>🟠 HIGH</span>"
                elif severity_level == "medium":
                    badge = "<span style='background: #29200e; color: #fcd34d; padding: 4px 10px; border-radius: 10px; font-weight: 700; font-size: 0.85em; border: 1px solid #f59e0b;'>🟡 MEDIUM</span>"
                else:
                    badge = "<span style='background: #14271c; color: #a7f3d0; padding: 4px 10px; border-radius: 10px; font-weight: 700; font-size: 0.85em; border: 1px solid #10b981;'>🟢 LOW</span>"

                # Device details (for old format compatibility)
                devices_detail = ""
                if isinstance(issue.get("devices"), list) and issue["devices"]:
                    devices_detail = f"<br><small style='color: #6b7280;'>Devices: {', '.join(issue['devices'][:3])}{' ...' if len(issue['devices']) > 3 else ''}</small>"

                issue_rows.append(f"""
                <tr style="border-bottom: 1px solid #2A2A2C;">
                    <td style="padding: 12px;">{badge}</td>
                    <td style="padding: 12px; color: #E8E8E8; font-weight: 500;">{category.replace('_', ' ').title()}</td>
                    <td style="padding: 12px; color: #E8E8E8;">{description}{devices_detail}</td>
                    <td style="padding: 12px; text-align: center; color: #E8E8E8; font-weight: 600;">{count if count is not None else '—'}</td>
                </tr>
                """)
        
        # Sort by severity (critical first)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        dashboard_html += "".join(issue_rows)
        
        dashboard_html += f"""
            </tbody>
        </table>
    </div>
    
    <div style="margin-top: 30px; padding: 20px; background: #161617; border-radius: 12px; border: 1px solid #2A2A2C; box-shadow: none;">
        <h3 style="margin-top: 0; color: #E8E8E8;">📊 Quick Stats</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
            <div style="padding: 15px; background: #1A1A1C; border-radius: 10px; border: 1px solid #2A2A2C;">
                <div style="font-size: 0.9em; color: #B0B0B0; margin-bottom: 6px;">Energy (24h)</div>
                <div style="font-size: 1.6em; font-weight: 800; color: #E8E8E8;">{energy_consumption:.1f} kWh</div>
                <div style="font-size: 0.9em; color: #E8E8E8; margin-top: 5px;">${energy_cost:.2f}</div>
            </div>
            <div style="padding: 15px; background: #1A1A1C; border-radius: 10px; border: 1px solid #2A2A2C;">
                <div style="font-size: 0.9em; color: #B0B0B0; margin-bottom: 6px;">Updates Available</div>
                <div style="font-size: 1.6em; font-weight: 800; color: {'#FFC940' if total_updates > 0 else '#E8E8E8'};">{total_updates}</div>
            </div>
            <div style="padding: 15px; background: #1A1A1C; border-radius: 10px; border: 1px solid #2A2A2C;">
                <div style="font-size: 0.9em; color: #B0B0B0; margin-bottom: 6px;">Repairs Needed</div>
                <div style="font-size: 1.6em; font-weight: 800; color: {'#FF4A4A' if total_repairs > 0 else '#E8E8E8'};">{total_repairs}</div>
            </div>
            <div style="padding: 15px; background: #1A1A1C; border-radius: 10px; border: 1px solid #2A2A2C;">
                <div style="font-size: 0.9em; color: #B0B0B0; margin-bottom: 6px;">Zigbee Devices</div>
                <div style="font-size: 1.6em; font-weight: 800; color: #E8E8E8;">{mesh_devices}</div>
                <div style="font-size: 0.9em; color: {'#FF4A4A' if weak_links > 0 else '#E8E8E8'}; margin-top: 5px;">{weak_links} weak links</div>
            </div>
        </div>
    </div>
    
    <div style="text-align: center; margin-top: 20px; font-size: 0.85em; color: #E8E8E8;">
        Last updated: {result.get('timestamp', 'N/A')}
    </div>
</div>
"""

        # Get AI analysis - Create compact summary for AI to avoid truncation
        agent = get_or_init_agent()

        # Extract key info instead of full JSON
        summary_for_ai = {
            "overall_health": result.get("overall_health", {}),
            "issues_by_category": {
                cat: [
                    {
                        "severity": issue.get("severity"),
                        "issue": issue.get("issue") or issue.get("description"),
                        "count": issue.get("count") or len(issue.get("devices", []))
                    }
                    for issue in issues[:3]  # Limit to 3 per category
                ]
                for cat, issues in issues_by_category.items()
            },
            "stats": {
                "energy_24h": energy_consumption,
                "energy_cost": energy_cost,
                "total_updates": total_updates,
                "total_repairs": total_repairs,
                "zigbee_devices": mesh_devices,
                "weak_links": weak_links
            }
        }

        ai_prompt = f"""Analyze this Home Assistant system diagnostic summary and provide actionable insights.

System Diagnostic Data:
{json.dumps(summary_for_ai, indent=2)}

Based on the data above, provide:
1. Priority assessment - Which issues need immediate attention?
2. Root cause analysis - Are any issues related or symptoms of a larger problem?
3. Action plan - Step-by-step recommendations in priority order
4. Impact summary - How do these issues affect daily operation?"""

        ai_analysis, _, fallback_used = await agent.chat_async(ai_prompt)
        ai_prefix = "🟦 OpenAI Analysis" if fallback_used else "🟨 Gemini Analysis"

        # Clear chat history to avoid contaminating future chatbot interactions
        agent.clear_history()

        # Add AI analysis section
        ai_section = f"""
<div style="margin: 30px 0; padding: 25px; background: #161617; color: #eaeaea; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.35); border: 1px solid #2a2a2c;">
    <h2 style="margin-top: 0; color: #f8fafc; border-bottom: 2px solid #3b82f6; padding-bottom: 10px;">{ai_prefix}</h2>
    <div style="line-height: 1.6; white-space: pre-wrap; color: #eaeaea;">{ai_analysis}</div>
</div>
"""

        return dashboard_html + ai_section
        
    except Exception as e:
        return f"""
<div style="padding: 20px; background: #2b1616; color: #fca5a5; border-radius: 8px; border: 2px solid #f88;">
    <h3 style="color: #c00; margin-top: 0;">❌ Diagnostic Error</h3>
    <p>{str(e)}</p>
</div>
"""

def run_full_diagnostics():
    """Sync wrapper for Gradio"""
    return asyncio.run(run_full_diagnostics_async())


# ============================================================================
# TAB 2: AI DIAGNOSTIC CHAT
# ============================================================================

def _normalize_history(history: Any) -> List[Dict[str, str]]:
    """Normalize history to list of {'role','content'} dicts (user/assistant)."""
    if not history:
        return []
    normalized = []
    for msg in history:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            normalized.append({"role": msg["role"], "content": msg["content"]})
        elif isinstance(msg, (list, tuple)) and len(msg) == 2:
            user_msg, assistant_msg = msg
            normalized.append({"role": "user", "content": user_msg})
            if assistant_msg:
                normalized.append({"role": "assistant", "content": assistant_msg})
    return normalized


def chat_with_agent(message: str, history: Any) -> Tuple[List[Dict[str, str]], str]:
    """
    Chat with diagnostic agent
    
    Returns:
        (updated_history, tools_used_html)
    """
    try:
        history = _normalize_history(history)

        # Guard against empty input to avoid Gemini errors
        if not message or not str(message).strip():
            history.append({"role": "assistant", "content": "⚠️ Please enter a question to start the diagnostic."})
            return history, "<div style='padding: 10px; color: #9ca3af; font-style: italic;'>No tools used yet</div>"

        # Get or initialize agent (lazy loading)
        agent = get_or_init_agent()
        
        # Get response from agent
        response, tools_used, fallback_used = agent.chat_sync(message)

        prefix = "🟦 OpenAI Fallback Active\n\n" if fallback_used else "🟨 Gemini Response\n\n"
        response_text = f"{prefix}{response}"
        
        # Update history
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response_text})
        
        # Format tools timeline
        if tools_used:
            tools_html = "<div style='padding: 12px; background: #121214; color: #eaeaea; border-radius: 12px; margin-top: 10px; border: 1px solid #2a2a2c; box-shadow: 0 1px 4px rgba(0,0,0,0.25);'>"
            tools_html += "<h4 style='margin-top: 0; color: #eaeaea;'>🔧 Tools Used:</h4>"
            tools_html += "<div style='font-size: 0.95em; color: #dcdce2;'>"
            
            for i, tool in enumerate(tools_used, 1):
                tool_name = tool.get("name", "unknown")
                tool_args = tool.get("args", {})
                success = "error" not in tool.get("result", {})
                
                icon = "✅" if success else "❌"
                tools_html += f"""
<div style='margin: 8px 0; padding: 10px; background: #161617; color: #eaeaea; border-radius: 8px; border: 1px solid #2a2a2c; border-left: 3px solid {"#10b981" if success else "#ef4444"}; box-shadow: 0 1px 3px rgba(0,0,0,0.25);'>
    {icon} <strong style='color:#eaeaea;'>{tool_name}</strong>
    {f"<div style='font-size: 0.85em; color: #cbd5e1; margin-top: 4px;'>{tool_args}</div>" if tool_args else ""}
</div>
"""
            
            tools_html += "</div></div>"
        else:
            tools_html = "<div style='padding: 10px; color: #9ca3af; font-style: italic;'>No tools used yet</div>"
        
        return history, tools_html
        
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        history = _normalize_history(history)
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": error_msg})
        return history, "<div style='color: #c00;'>Error executing agent</div>"


# ============================================================================
# TAB 3: INVESTIGATION LAB
# ============================================================================

async def investigate_entity_async(entity_id: str) -> str:
    """Investigate specific entity with AI-powered analysis"""
    if not entity_id:
        return "⚠️ Please enter an entity ID"

    try:
        # Run diagnosis to get raw data
        result = await get_bridge().diagnose_issue(entity_id)

        if not result.get("success"):
            # Fallback: try to see if entity exists via list_entities
            try:
                entities = await get_bridge().list_entities(limit=5000)
                found = False
                if isinstance(entities, dict):
                    for ent in entities.get("entities", []):
                        if ent.get("entity_id") == entity_id:
                            found = True
                            break
                if found:
                    return f"⚠️ Unable to run full diagnosis, but entity exists: {entity_id}\nDetails: {result.get('error', 'Unknown error')}"
            except Exception:
                pass
            return f"❌ Error: {result.get('error', 'Unknown error')}"

        # Get AI analysis - Create compact summary for AI to avoid truncation
        agent = get_or_init_agent()

        # Extract key info instead of full JSON
        summary_for_ai = {
            "entity_id": entity_id,
            "summary": result.get("summary", {}),
            "recommendations": result.get("recommendations", [])[:5],  # Limit to 5
            "related_issues": result.get("related_issues", [])[:3]     # Limit to 3
        }

        ai_prompt = f"""Analyze this Home Assistant entity diagnostic data and provide a clear, helpful explanation.

Entity: {entity_id}
Diagnostic Data:
{json.dumps(summary_for_ai, indent=2)}

Based on the data above, provide:
1) What this entity is
2) Current status/issues
3) Specific actionable recommendations"""

        ai_analysis, _, fallback_used = await agent.chat_async(ai_prompt)
        ai_prefix = "🟦 OpenAI Analysis" if fallback_used else "🟨 Gemini Analysis"

        # Clear chat history to avoid contaminating future chatbot interactions
        agent.clear_history()

        # Format results
        summary = result.get("entity_summary", {})
        severity = result.get("severity", "unknown")

        # Build HTML with AI analysis
        html = f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #eaeaea;">
    <h2>🔍 Entity Investigation: <code>{entity_id}</code></h2>

    <div style="padding: 15px; background: #121214; color: #eaeaea; border-radius: 12px; margin: 15px 0; border: 1px solid #2a2a2c; box-shadow: 0 4px 10px rgba(0,0,0,0.25);">
        <h3 style="margin-top: 0; color: #eaeaea;">Summary</h3>
        <div style="margin-top: 8px; color: #eaeaea;"><strong style="color:#eaeaea;">State:</strong> <span style="color: #eaeaea;">{summary.get('state', 'N/A')}</span></div>
        <div style="margin-top: 8px; color: #eaeaea;"><strong style="color:#eaeaea;">Severity:</strong> <span style="color: {'#ef4444' if severity in ['critical', 'high'] else '#f59e0b' if severity == 'medium' else '#22c55e'};">{severity.upper()}</span></div>
        <div style="margin-top: 8px; color: #eaeaea;"><strong style="color:#eaeaea;">Last Updated:</strong> <span style="color: #eaeaea;">{summary.get('last_updated', 'N/A')}</span></div>
    </div>

    <div style="padding: 15px; background: #161617; color: #eaeaea; border-radius: 12px; margin: 15px 0; border: 1px solid #2a2a2c; box-shadow: 0 4px 10px rgba(0,0,0,0.25);">
        <h3 style="margin-top: 0; color: #f8fafc;">{ai_prefix}</h3>
        <div style="color: #eaeaea; line-height: 1.6; white-space: pre-wrap;">{ai_analysis}</div>
    </div>
</div>
"""

        return html

    except Exception as e:
        return f"❌ Error: {str(e)}"

def investigate_entity(entity_id: str) -> str:
    """Sync wrapper"""
    return asyncio.run(investigate_entity_async(entity_id))


async def identify_device_async(entity_id: str) -> str:
    """Identify device physically"""
    if not entity_id:
        return "⚠️ Please enter an entity ID"
    
    try:
        result = await get_bridge().identify_device(entity_id)
        
        if result.get("success"):
            actions = result.get("actions_executed") or result.get("actions", [])
            actions_text = "\n".join([f"- {a}" for a in actions]) if actions else "N/A"
            return "\n".join([
                "✅ Device identified successfully!",
                "",
                f"Actions: {actions_text}",
                f"Duration: {result.get('duration_seconds', result.get('duration', 0))}s",
                f"Entities: {', '.join(result.get('entities_found', [])[:5])}"
            ])
        else:
            return f"❌ Failed to identify device:\n{result.get('error', 'Unknown error')}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def identify_device(entity_id: str) -> str:
    """Sync wrapper"""
    return asyncio.run(identify_device_async(entity_id))


async def load_automations_async() -> List[str]:
    """Load automation list"""
    try:
        automations = await get_bridge().list_automations()
        return [f"{a.get('entity_id', 'unknown')} - {a.get('alias', 'No name')}" for a in automations]
    except:
        return ["automation.example_1", "automation.example_2"]

def load_automations() -> gr.Dropdown:
    """Sync wrapper"""
    choices = asyncio.run(load_automations_async())
    return gr.Dropdown(choices=choices, value=choices[0] if choices else None)


async def scan_orphans_async() -> str:
    """Scan for orphan entities"""
    try:
        result = await get_bridge().find_orphan_entities()

        if not result.get("success", True) and result.get("error"):
            return f"❌ Error: {result.get('error')}"
        
        total = result.get("total_orphans", 0)
        pct = result.get("orphan_percentage", 0)
        by_domain = result.get("orphans_by_domain", {})
        orphan_entities = result.get("orphan_entities", [])
        
        html = f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <h2>🧹 Orphan Entity Report</h2>
    
    <div style="padding: 20px; background: #121214; border-radius: 12px; border: 2px solid #f59e0b; margin: 15px 0; color: #eaeaea;">
        <div style="font-size: 2em; font-weight: bold; color: #f59e0b;">{total} Orphans</div>
        <div style="color: #d6cbb8; margin-top: 5px;">{pct:.1f}% of total entities</div>
    </div>
    
    <h3>By Domain:</h3>
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px;">
"""
        
        for domain, count in sorted(by_domain.items(), key=lambda x: x[1], reverse=True):
            html += f"""
<div style="padding: 12px; background: #161617; border-radius: 10px; border-left: 4px solid #3b82f6; color: #eaeaea; box-shadow: none; border: 1px solid #2a2a2c;">
    <div style="font-size: 0.95em; color: #dcdce2;">{domain}</div>
    <div style="font-size: 1.6em; font-weight: 800; color: #eaeaea;">{count}</div>
</div>
"""
        
        html += "</div>"

        if orphan_entities:
            html += "<h3 style='margin-top:20px;'>Sample Orphan Entities (first 50)</h3><ul>"
            for orphan in orphan_entities:
                eid = orphan.get("entity_id", "unknown")
                friendly = orphan.get("friendly_name", eid)
                state = orphan.get("state", "unknown")
                html += f"<li><code>{eid}</code> — {friendly} (state: {state})</li>"
            html += "</ul>"

        html += "</div>"

        # Get AI analysis - Create compact summary for AI to avoid truncation
        agent = get_or_init_agent()

        # Extract key info instead of full JSON (limit entities to first 20)
        orphan_entities = result.get("orphan_entities", [])
        summary_for_ai = {
            "total_orphans": result.get("total_orphans", 0),
            "orphans_by_domain": result.get("orphans_by_domain", {}),
            "sample_entities": [
                {
                    "entity_id": orphan.get("entity_id"),
                    "friendly_name": orphan.get("friendly_name"),
                    "state": orphan.get("state")
                }
                for orphan in orphan_entities[:20]  # Limit to first 20
            ]
        }

        ai_prompt = f"""Analyze these orphan entities in Home Assistant and provide cleanup guidance.

Orphan Entities Data:
{json.dumps(summary_for_ai, indent=2)}

Based on the data above, provide:
1. Safety assessment - Which orphans are safe to delete vs need investigation?
2. Pattern detection - Do you see groups of orphans from specific integrations or patterns?
3. Usage check - Could any of these still be used in automations despite being orphaned?
4. Cleanup priority - Recommend an order for cleanup (start with safest)
5. Potential issues - Any orphans that might indicate integration problems?"""

        ai_analysis, _, fallback_used = await agent.chat_async(ai_prompt)
        ai_prefix = "🟦 OpenAI Analysis" if fallback_used else "🟨 Gemini Analysis"

        # Clear chat history to avoid contaminating future chatbot interactions
        agent.clear_history()

        # Add AI analysis section
        ai_section = f"""
<div style="margin: 30px 0; padding: 25px; background: #161617; color: #eaeaea; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.35); border: 1px solid #2a2a2c;">
    <h2 style="margin-top: 0; color: #f8fafc; border-bottom: 2px solid #3b82f6; padding-bottom: 10px;">{ai_prefix}</h2>
    <div style="line-height: 1.6; white-space: pre-wrap; color: #eaeaea;">{ai_analysis}</div>
</div>
"""

        return html + ai_section
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

def scan_orphans() -> str:
    """Sync wrapper"""
    return asyncio.run(scan_orphans_async())

async def get_entity_examples_async() -> str:
    """Get entity examples based on current mode"""
    bridge = get_bridge()

    if bridge.demo_mode:
        return """
**🔴 DEMO Mode**: Try these example entities:
- `light.kitchen_main` - Unavailable Zigbee light
- `sensor.temperature` - Temperature sensor
- `switch.bedroom` - Smart switch
"""
    else:
        # LIVE mode: simple message, no entity fetching
        return "**🟢 LIVE Mode**: Enter any entity ID from your Home Assistant instance"

def get_entity_examples() -> str:
    """Sync wrapper"""
    return asyncio.run(get_entity_examples_async())


# ============================================================================
# BUILD UI
# ============================================================================

# Build UI with fixed dark CSS; disable theme to avoid Gradio defaults
try:
    demo = gr.Blocks(title="Home Assistant Diagnostics Agent", css="custom.css", theme=None)
except TypeError:
    demo = gr.Blocks(title="Home Assistant Diagnostics Agent")

with demo:

    # Inject CSS inline as a safeguard (HF Spaces may ignore css kwarg)
    if CUSTOM_CSS:
        gr.HTML(f"<style>{CUSTOM_CSS}</style>")

    gr.Markdown("""
    # 🏠🔍 Home Assistant Diagnostics Agent

    It uses [Home Assistant Diagnostics MCP Server](https://huggingface.co/spaces/MCP-1st-Birthday/Home-Assistant-Diagnostics-MCP-Server)

    AI-powered smart home troubleshooting backed by 39 MCP tools (Gemini primary, OpenAI fallback, LlamaIndex KB, Blaxel history)
    """)
    
    # Mode indicator (updates when switching demo/live)
    mode_badge = gr.HTML(render_mode_badge())
    
    with gr.Tabs():
        # TAB 1: Dashboard
        with gr.Tab("🏠 Health Dashboard"):
            gr.Markdown("### System-wide health monitoring with real-time diagnostics")
            
            run_btn = gr.Button("🔄 Run Full Diagnostics", variant="primary", size="lg")
            dashboard_output = gr.HTML(value="<div style='text-align: center; padding: 40px; color: #666;'>Click 'Run Full Diagnostics' to start</div>")
            
            run_btn.click(
                fn=run_full_diagnostics,
                outputs=dashboard_output
            )
        
        # TAB 2: AI Chat
        with gr.Tab("💬 Ask Agent"):
            gr.Markdown("### Chat with AI diagnostic agent powered by Gemini + MCP tools")
            gr.HTML(
                value="""
<div style="font-size: 0.9em; color: #eaeaea; padding: 8px 12px; background: #161617; border-radius: 12px; border: 1px solid #2a2a2c; display: inline-block; margin-bottom: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.3);">
    <span style="margin-right: 14px; color: #f8fafc;">🟨 <strong style=\"color:#f8fafc;\">Primary:</strong> Gemini 2.0 Flash (function calling)</span>
    <span style="color: #f8fafc;">🟦 <strong style=\"color:#f8fafc;\">Fallback:</strong> OpenAI gpt-4o-mini (explanation only if Gemini is unavailable)</span>
</div>
"""
            )
            
            with gr.Row():
                with gr.Column(scale=2):
                    chatbot = gr.Chatbot(height=500, label="Diagnostic Agent")
                    msg_input = gr.Textbox(
                        placeholder="Ask about your smart home... (e.g., 'Why isn't my kitchen light working?')",
                        label="Your Question",
                        lines=2
                    )
                    
                    with gr.Row():
                        submit_btn = gr.Button("Send", variant="primary")
                        clear_btn = gr.Button("Clear Chat")
                
                with gr.Column(scale=1):
                    tools_timeline = gr.HTML(
                        value="<div style='padding: 10px; color: #9ca3af; font-style: italic;'>No tools used yet</div>",
                        label="Tools Timeline"
                    )
            
            # Example queries
            gr.Examples(
                examples=[
                    "Run a complete system health check",
                    "Analyze my Zigbee mesh network",
                    "Find all orphan entities",
                    "Show me energy consumption for last 24 hours",
                    "Which batteries are low?",
                    "Detect automation conflicts",
                    "List common causes of stale entities and how to fix them",
                    "Show diagnostic history",
                ],
                inputs=msg_input
            )
            
            submit_btn.click(
                fn=chat_with_agent,
                inputs=[msg_input, chatbot],
                outputs=[chatbot, tools_timeline]
            ).then(
                lambda: "",
                outputs=msg_input
            )
            
            def clear_chat():
                global agent
                if agent:
                    agent.reset_conversation()
                return [], "<div style='padding: 10px; color: #9ca3af; font-style: italic;'>No tools used yet</div>"

            clear_btn.click(
                fn=clear_chat,
                outputs=[chatbot, tools_timeline]
            ).then(
                lambda: "",
                outputs=msg_input
            )
        
        # TAB 3: Investigation Lab
        with gr.Tab("🔬 Investigation Lab"):
            gr.Markdown("### Deep-dive troubleshooting tools")
            
            with gr.Tabs():
                # Entity Investigation
                with gr.Tab("🏷️ Entity Investigation"):
                    gr.Markdown("Diagnose specific entities with deep analysis")

                    # Mode-aware entity examples (will be updated dynamically)
                    entity_examples_md = gr.Markdown(
                        """
                        **🔴 DEMO Mode**: Try these example entities:
                        - `light.kitchen_main` - Unavailable Zigbee light
                        - `sensor.temperature` - Temperature sensor
                        - `switch.bedroom` - Smart switch
                        """ if get_bridge().demo_mode else ""
                    )

                    entity_input = gr.Textbox(
                        label="Entity ID",
                        placeholder="e.g., light.kitchen, sensor.temperature",
                        lines=1
                    )
                    
                    with gr.Row():
                        investigate_btn = gr.Button("🔍 Investigate", variant="primary")
                        identify_btn = gr.Button("💡 Identify Device (Flash/Beep)", variant="secondary")
                    
                    entity_output = gr.HTML()
                    identify_output = gr.Textbox(label="Identification Result", lines=3)
                    
                    investigate_btn.click(
                        fn=investigate_entity,
                        inputs=entity_input,
                        outputs=entity_output
                    )
                    
                    identify_btn.click(
                        fn=identify_device,
                        inputs=entity_input,
                        outputs=identify_output
                    )
                
                # Cleanup Center
                with gr.Tab("🧹 Cleanup Center"):
                    gr.Markdown("Find and manage orphan entities")
                    
                    scan_btn = gr.Button("🔄 Scan for Orphan Entities", variant="primary", size="lg")
                    orphan_output = gr.HTML()
                    
                    scan_btn.click(
                        fn=scan_orphans,
                        outputs=orphan_output
                    )

        # TAB 4: Settings
        with gr.Tab("⚙️ Settings"):
            gr.Markdown("### Configuration Settings")

            gr.Markdown("""
            **Switch between DEMO and LIVE modes**

            - **DEMO Mode**: Uses pre-generated data (works on HuggingFace Spaces)
            - **LIVE Mode**: Connects to your real Home Assistant instance
            """)

            with gr.Row():
                mode_radio = gr.Radio(
                    choices=["DEMO", "LIVE"],
                    value="DEMO" if get_bridge().demo_mode else "LIVE",
                    label="Mode",
                    interactive=True
                )

            with gr.Column(visible=not get_bridge().demo_mode) as live_config:
                gr.Markdown("#### Home Assistant Connection")
                ha_url_input = gr.Textbox(
                    label="Home Assistant URL",
                    placeholder="http://your-ha-instance:8123",
                    value="",
                    lines=1
                )
                ha_token_input = gr.Textbox(
                    label="Long-Lived Access Token",
                    placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    type="password",
                    value="",
                    lines=1
                )

            # Apply button and status (always visible)
            apply_btn = gr.Button("💾 Apply Settings", variant="primary")
            settings_status = gr.Textbox(label="Status", lines=2, interactive=False)

            def apply_settings(mode, ha_url, ha_token):
                global agent
                try:
                    if mode == "DEMO":
                        # Update env vars first
                        import os
                        os.environ["DEMO_MODE"] = "true"

                        # Reset bridge with DEMO mode
                        reset_bridge(demo_mode=True)
                        agent = None  # force re-init agent on next use
                        try:
                            import agent as agent_module  # type: ignore
                            agent_module._agent_instance = None
                        except Exception:
                            pass
                        return (
                            "✅ Switched to DEMO mode. Using pre-generated data.",
                            render_mode_badge(),
                            get_entity_examples()
                        )
                    else:
                        if not ha_url or not ha_token:
                            return "⚠️ Please provide both HA URL and Token for LIVE mode", render_mode_badge(), get_entity_examples()

                        # Update environment variables for MCP bridge
                        import os
                        os.environ["HA_URL"] = ha_url.rstrip("/")
                        os.environ["HA_TOKEN"] = ha_token
                        os.environ["DEMO_MODE"] = "false"

                        # Reset bridge with LIVE mode and new credentials
                        bridge = reset_bridge(demo_mode=False)
                        agent = None  # force re-init agent on next use
                        try:
                            import agent as agent_module  # type: ignore
                            agent_module._agent_instance = None
                        except Exception:
                            pass

                        if not bridge.connected:
                            return (
                                f"⚠️ Tried to switch to LIVE mode but bridge is not connected.\nError: {bridge.init_error or 'unknown'}",
                                render_mode_badge(),
                                get_entity_examples()
                            )

                        return (
                            f"✅ Switched to LIVE mode. Connected to: {ha_url}\n💡 You can now use all features with your real Home Assistant data!",
                            render_mode_badge(),
                            get_entity_examples()
                        )
                except Exception as e:
                    return f"❌ Error: {str(e)}", render_mode_badge(), get_entity_examples()

            def toggle_live_config(mode):
                return gr.update(visible=(mode == "LIVE"))

            mode_radio.change(
                fn=toggle_live_config,
                inputs=mode_radio,
                outputs=live_config
            )

            apply_btn.click(
                fn=apply_settings,
                inputs=[mode_radio, ha_url_input, ha_token_input],
                outputs=[settings_status, mode_badge, entity_examples_md]
            )

            gr.Markdown("""
            ---

            **🔒 Security Note**: Your Home Assistant URL and token are only stored in memory during this session.
            They are never saved to disk or transmitted anywhere except to your Home Assistant instance.

            **📝 How to get a Long-Lived Access Token**:
            1. Log into your Home Assistant
            2. Click on your profile (bottom left)
            3. Select the **Security** tab
            4. Scroll down to "Long-Lived Access Tokens"
            5. Click "Create Token"
            6. Copy and paste the token here
            """)

    # Footer
    gr.Markdown("""
    ---
    
    <div style="text-align: center; color: #666; font-size: 0.9em;">
        <p><strong>Home Assistant Diagnostics Agent</strong> - Built for Hugging Face MCP Hackathon 2025</p>
        <p>Powered by the <strong>Home Assistant Diagnostics MCP Server</strong> with <strong>Gemini 2.0 Flash</strong> (primary), <strong>OpenAI gpt-4o-mini</strong> (fallback), <strong>LlamaIndex</strong> knowledge base, and <strong>Blaxel</strong> diagnostic history.</p>
        <p>🏷️ Tags: <code>mcp-in-action-track-consumer</code> <code>mcp</code> <code>home-assistant</code> <code>gemini</code> <code>openai</code> <code>llamaindex</code> <code>blaxel</code></p>
    </div>
    """)


if __name__ == "__main__":
    print("🚀 Starting Home Assistant Diagnostics Agent...")
    print(f"📍 Mode: {'DEMO' if get_bridge().demo_mode else 'LIVE'}")
    print(f"🔧 MCP Bridge: {'Ready' if get_bridge() else 'Not initialized'}")
    print(f"🤖 Gemini Agent: Will initialize on first use (lazy loading)")

    # Allow overriding port via env (GRADIO_SERVER_PORT or PORT)
    port = int(os.getenv("GRADIO_SERVER_PORT", os.getenv("PORT", "7861")))

    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False
    )
else:
    # When imported (e.g., Spaces), ensure CSS loads
    if CUSTOM_CSS:
        try:
            demo.load_css(CUSTOM_CSS)
        except Exception:
            pass
