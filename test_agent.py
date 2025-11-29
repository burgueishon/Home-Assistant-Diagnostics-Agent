"""
Quick test script for agent.py function calling

Tests:
1. Agent initialization
2. Function declarations setup
3. Basic chat (with/without API key)
"""

import os
import asyncio
from agent import DiagnosticAgent

def test_initialization():
    """Test agent can be initialized"""
    print("🧪 Test 1: Agent Initialization")

    agent = DiagnosticAgent()
    print(f"   ✅ Agent created")
    print(f"   ✅ Bridge mode: {'DEMO' if agent.bridge.demo_mode else 'LIVE'}")
    print(f"   ✅ API key configured: {bool(agent.api_key)}")
    print()

def test_function_declarations():
    """Test function declarations are set up"""
    print("🧪 Test 2: Function Declarations")

    agent = DiagnosticAgent()
    tools = agent._setup_function_declarations()

    print(f"   ✅ Number of tools: {len(tools)}")

    expected_tools = [
        'diagnose_system',
        'audit_zigbee_mesh',
        'find_orphan_entities',
        'detect_automation_conflicts',
        'battery_report',
        'energy_consumption_report'
    ]

    if tools:
        tool_names = [t.name for t in tools]
        for expected in expected_tools:
            if expected in tool_names:
                print(f"   ✅ Tool '{expected}' registered")
            else:
                print(f"   ❌ Tool '{expected}' MISSING")
    else:
        print("   ⚠️  No tools registered (google.generativeai not installed?)")
    print()

def test_tool_executor():
    """Test tool executor mapping"""
    print("🧪 Test 3: Tool Executor")

    agent = DiagnosticAgent()

    # Test tool mapping exists
    test_tools = ['diagnose_system', 'battery_report', 'find_orphan_entities']

    for tool_name in test_tools:
        # Just check the mapping exists, don't actually execute
        try:
            # This will check if bridge method exists
            if hasattr(agent.bridge, tool_name):
                print(f"   ✅ Tool '{tool_name}' → bridge.{tool_name}()")
            else:
                print(f"   ❌ Tool '{tool_name}' has no bridge method")
        except Exception as e:
            print(f"   ❌ Error checking '{tool_name}': {e}")
    print()

def test_safety_checker():
    """Test dangerous tool detection"""
    print("🧪 Test 4: Safety Checker")

    agent = DiagnosticAgent()

    safe_tools = ['diagnose_system', 'battery_report']
    dangerous_tools = ['identify_device', 'restart_home_assistant']

    for tool in safe_tools:
        is_dangerous = agent._is_dangerous_tool(tool)
        if not is_dangerous:
            print(f"   ✅ '{tool}' correctly marked as SAFE")
        else:
            print(f"   ❌ '{tool}' incorrectly marked as DANGEROUS")

    for tool in dangerous_tools:
        is_dangerous = agent._is_dangerous_tool(tool)
        if is_dangerous:
            print(f"   ✅ '{tool}' correctly marked as DANGEROUS")
        else:
            print(f"   ❌ '{tool}' incorrectly marked as SAFE")
    print()

async def _basic_execution():
    agent = DiagnosticAgent()
    result = await agent._execute_tool('battery_report', {})
    return result


def test_basic_execution():
    """Test basic tool execution (DEMO mode)"""
    print("🧪 Test 5: Basic Tool Execution (DEMO mode)")
    try:
        result = asyncio.run(_basic_execution())
        if 'error' in result:
            print(f"   ⚠️  Tool returned error: {result.get('error')}")
        else:
            print(f"   ✅ battery_report executed successfully")
            print(f"   ✅ Result type: {type(result)}")
            if 'demo_mode' in result:
                print(f"   ✅ Running in DEMO mode (as expected)")
    except Exception as e:
        print(f"   ❌ Execution failed: {e}")
    print()

def main():
    """Run all tests"""
    print("=" * 60)
    print("🏥 Home Assistant Diagnostics Agent - Function Calling Tests")
    print("=" * 60)
    print()

    # Check environment
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
    has_gemini = bool(os.getenv("GEMINI_API_KEY"))

    print(f"Environment:")
    print(f"   DEMO_MODE: {demo_mode}")
    print(f"   GEMINI_API_KEY: {'✅ Set' if has_gemini else '❌ Not set'}")
    print()

    # Run tests
    test_initialization()
    test_function_declarations()
    test_tool_executor()
    test_safety_checker()

    # Async test
    asyncio.run(test_basic_execution())

    print("=" * 60)
    print("✅ All tests completed!")
    print()

    if not has_gemini:
        print("⚠️  NOTE: Set GEMINI_API_KEY to test actual function calling")
    else:
        print("✅ GEMINI_API_KEY configured - ready for full testing")

    print("=" * 60)

if __name__ == "__main__":
    main()
