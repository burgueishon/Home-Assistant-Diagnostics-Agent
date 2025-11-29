---
title: Home Assistant Diagnostics Agent
emoji: 🏠🔍
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 6.0.0
app_file: app.py
pinned: false
license: mit
tags:
  - mcp
  - home-assistant
  - diagnostics
  - gemini
  - openai
  - llamaindex
  - blaxel
  - mcp-in-action-track-consumer
  - smart-home
  - ai-agent
---

# 🏠🔍 Home Assistant Diagnostics Agent

**Built for Hugging Face MCP's 1st Birthday Hackathon**

---

## 🎯 What is the Home Assistant Diagnostics Agent?

An AI-powered diagnostic assistant for Home Assistant smart homes, combining:

- **39 MCP Tools** for deep system analysis
- **13 MCP Resources** with beautiful markdown reports
- **Gemini 2.0 Flash** AI agent with function calling
- **Gradio 6** modern UI with 3 specialized interfaces

It's like having a **smart home doctor** that can:
- 🔍 Diagnose issues automatically
- 📡 Analyze Zigbee mesh networks
- ⚡ Track energy consumption & costs
- 🧹 Find orphan entities for cleanup
- 🔧 Detect automation conflicts & loops
- 🤖 Chat naturally about your smart home

<p align="center">
  <a href="https://youtu.be/chPXuaOtSJ4">
    <img src="https://img.youtube.com/vi/chPXuaOtSJ4/maxresdefault.jpg" alt="Demo Video" width="80%">
    <br>
    <img src="https://img.shields.io/badge/▶%20Watch%20Demo-YouTube-red?style=for-the-badge&logo=youtube">
  </a>
</p>

## 🚀 Hugging Face Space

Try it on Hugging Face Spaces: [MCP-1st-Birthday/Home-Assistant-Diagnostics-Agent](https://huggingface.co/spaces/MCP-1st-Birthday/Home-Assistant-Diagnostics-Agent)

---

## ✨ Key Features

### 🏠 **Health Dashboard**
Apple Health-style dashboard with real-time system metrics:
- Overall system health score (0-100)
- Zigbee mesh network analysis
- Battery health monitoring
- Energy consumption tracking
- Automation safety status
- One-click full diagnostics
- 📘 Knowledge Indexing — Powered by LlamaIndex (KeywordTableIndex on demo data & markdown)
- 🗂️ Diagnostic History — Optional Blaxel stub storing tool snapshots (feature-flagged)

### 💬 **AI Diagnostic Chat**
Powered by **Gemini 2.0 Flash** with MCP tool calling:
- Natural language diagnostics
- Automatic tool orchestration
- Visual tools timeline
- Follow-up questions
- Actionable recommendations
- Confirmation before device actions
- OpenAI gpt-4o-mini fallback (explanation only if Gemini is unavailable)
- Optional LlamaIndex knowledge base (keyword index)
- Optional Blaxel diagnostic history (in-memory snapshots)

### 🔬 **Investigation Lab**
Deep-dive troubleshooting tools:
- **Entity Investigation** - Diagnose any entity
- **Device Identification** - Physical flash/beep
- **Cleanup Center** - Find orphan entities
- **Automation Analysis** - Detect conflicts

---

## Optional AI Extensions

### 🔷 LlamaIndex Integration (Knowledge Base Tool)
- Enabled by default: `FEATURE_LLAMAINDEX=true` (no API keys needed).
- Uses `llama-index-core`, `llama-index-readers-file`, `llama-index-llms-openai`.
- Builds a local `KeywordTableIndex` from:
  - `demo_data/*.json` (serialized as text)
  - `resources/*.md` (if present)
- Exposes tool: `query_diagnostics_knowledge(question: str)`
- Tool is in Gemini function declarations and auto-invoked when the model detects a KB-style question; appears in the tools timeline when used.
- Does not change DEMO/LIVE or OpenAI fallback.
- Eligible for the LlamaIndex Category Award.

### 🔷 Blaxel Integration (Stub for Diagnostic History)
- Optional flag: `FEATURE_BLAXEL=false` by default.
- No external SDK; works offline. If `BLAXEL_API_KEY` is missing, returns a friendly error without breaking execution.
- Stores up to 100 snapshots in-memory (`blaxel_backend.py`), capturing: tool_name, arguments, result, timestamp.
- Exposes tool: `query_diagnostic_history()` to retrieve stored snapshots; appears in the tools timeline when used.
- Sufficient to qualify for the Blaxel Choice Award.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GRADIO UI (app.py)                       │
│  ┌──────────────┬──────────────┬─────────────────────────┐  │
│  │  Dashboard   │  AI Chat     │  Investigation Lab      │  │
│  └──────────────┴──────────────┴─────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
            ┌────────────────┐
            │  agent.py      │  ◄── Gemini 2.0 Flash
            │  (Function     │      (Tool Calling)
            │   Calling)     │
            └────────┬───────┘
                     │
                     ▼
            ┌────────────────┐
            │ mcp_bridge.py  │  ◄── DEMO_MODE / LIVE_MODE
            └────────┬───────┘
                     │
         ┌───────────┴────────────┐
         │                        │
         ▼                        ▼
    ┌─────────┐            ┌──────────────┐
    │ MCP     │            │  demo_data/  │
    │ Server  │            │  (JSON/MD)   │
    │ (LIVE)  │            │  (DEMO)      │
    └─────────┘            └──────────────┘
         │
         ▼
┌────────────────────┐
│  Home Assistant    │
└────────────────────┘
```

---

## 🚀 Quick Start

### Option 1: Demo Mode (HuggingFace Spaces)

```bash
# Clone repository
git clone https://github.com/burgueishon/Home-Assistant-Diagnostics-Agent.git
cd Home-Assistant-Diagnostics-Agent

# Install dependencies
pip install -r requirements.txt

# Set Gemini API key
export GEMINI_API_KEY="your_key_here"

# Run in demo mode (uses pre-generated data)
export DEMO_MODE=true
python app.py
```

Open browser to `http://localhost:7861`

### Option 2: Live Mode (Connect to Your HA)

```bash
# Copy environment template
cp .env.example .env

# Edit .env and set:
DEMO_MODE=false
GEMINI_API_KEY=your_gemini_key
HA_URL=                # set your HA URL when switching to LIVE
HA_TOKEN=              # set your HA token when switching to LIVE

# Install MCP server dependencies
cd Home-Assistant-Diagnostics-MCP-Server
pip install -e .

# Return to gradio app
cd ..

# Run in live mode
python app.py
```

---

## 🔧 Environment Variables

Required (typical):
- `GEMINI_API_KEY` — Gemini 2.0 Flash
- `DEMO_MODE` — `true` (demo data) or `false` (live with HA_URL/HA_TOKEN)
- `HA_URL`, `HA_TOKEN` — leave blank for demo; set only for LIVE mode

Optional features:
- `FEATURE_LLAMAINDEX=true` (default ON)
- `FEATURE_BLAXEL=false` (default OFF)
- `BLAXEL_API_KEY=` (stub uses it only to suppress a warning; not required for local history)

---

## 🛠️ MCP Tools (39 total)

Powered by the **Home Assistant Diagnostics MCP Server** (39 tools) — [GitHub](https://github.com/burgueishon/Home-Assistant-Diagnostics-MCP-Server).

### Signature Advanced Tools (NEW)
- `audit_zigbee_mesh` - Mesh health analysis with LQI/RSSI
- `find_orphan_entities` - Unused entity detection
- `detect_automation_conflicts` - Race conditions & loops
- `energy_consumption_report` - Energy tracking & cost analysis
- `query_diagnostics_knowledge` (LlamaIndex) - KB lookups (feature-flagged)
- `query_diagnostic_history` (Blaxel) - Snapshot history (feature-flagged)

### System Diagnostics
- `diagnose_system` - Complete system health check
- `diagnose_issue` - Entity-level diagnostics
- `diagnose_automation` - Automation troubleshooting
- `battery_report` - Battery health monitoring
- `find_unavailable_entities` - Offline entity detection
- `find_stale_entities` - Frozen sensor detection

### Device Management
- `identify_device` - Physical device identification (flash/beep)
- `list_entities` - Entity listing with filters
- `get_entity_statistics` - Historical analysis

### Monitoring
- `get_repair_items` - HA repair panel issues
- `get_update_status` - Available updates
- `get_error_log` - Error analysis

[See complete tool list](https://github.com/burgueishon/Home-Assistant-Diagnostics-MCP-Server)

---

## 🤖 Gemini Integration

Uses **Gemini 2.0 Flash** with function calling:

```python
# Agent automatically decides which tools to use
response = agent.chat("Why isn't my kitchen light working?")

# Behind the scenes:
# 1. Gemini analyzes the question
# 2. Decides to call diagnose_issue(entity_id="light.kitchen")
# 3. Executes tool via MCP bridge
# 4. Analyzes results
# 5. Provides natural language response with recommendations
```

**Key Features**:
- Automatic tool selection
- Multi-turn conversations
- Context awareness
- Confirmation before device actions
- Structured responses with markdown

---

## 📊 Demo Mode vs Live Mode

| Feature | Demo Mode | Live Mode |
|---------|-----------|-----------|
| **Data Source** | Pre-generated JSON | Real Home Assistant |
| **Gemini Chat** | ✅ Full functionality | ✅ Full functionality |
| **MCP Tools** | ✅ Simulated responses | ✅ Real API calls |
| **Use Case** | HuggingFace Spaces demo | Personal deployment |
| **Requirements** | Gemini API key only | + HA URL & Token |

---

## 🔧 Environment Variables

```
# Core
DEMO_MODE=true                 # default demo
GEMINI_API_KEY=...             # required for Gemini
OPENAI_API_KEY=...             # optional fallback
HA_URL=                        # set when switching to LIVE mode
HA_TOKEN=                      # set when switching to LIVE mode

# Optional features
FEATURE_LLAMAINDEX=true        # knowledge base (default on)
FEATURE_BLAXEL=false           # diagnostic history snapshots (default off)
BLAXEL_API_KEY=                # optional; friendly error if missing
```

FEATURE_LLAMAINDEX is always on by default (local KeywordTableIndex, no keys required).
FEATURE_BLAXEL must be enabled manually if you want the history tool; leaving it off is safe for HF Spaces.

---

## 🎯 Hackathon Tags

```yaml
track: mcp-in-action-track-consumer
technologies:
  - mcp
  - home-assistant
  - diagnostics
  - gemini
  - openai
  - llamaindex
  - gradio
  - agents
features:
  - 39 MCP tools
  - 13 MCP resources
  - Gemini 2.0 Flash function calling
  - Dual-mode architecture (DEMO/LIVE)
  - Real-time diagnostics
  - Natural language interface
```

---

## 📖 Example Queries

Try these in the AI Chat:

```
🔍 Diagnostics:
- "Run a complete system health check"
- "Why isn't my kitchen light working?"
- "Diagnose automation.morning_routine"
- "Show diagnostic history"

📡 Network Analysis:
- "Analyze my Zigbee mesh network"
- "Which Zigbee devices have weak signal?"
- "Show me mesh health with recommendations"

🧹 Cleanup & Optimization:
- "Find all orphan entities"
- "Which entities can I safely delete?"
- "Detect automation conflicts"

⚡ Energy & Monitoring:
- "Show energy consumption for last 24 hours"
- "Which devices consume the most power?"
- "Estimate my monthly electricity cost"

🔋 Maintenance:
- "Which batteries are low?"
- "Find sensors that haven't updated"
- "Are there any available updates?"
```

---

## 🔧 Development

### Project Structure

```
Home-Assistant-Diagnostics-Agent/
├── app.py                       # Main Gradio UI (3 tabs)
├── agent.py                     # Gemini AI agent with function calling
├── mcp_bridge.py                # MCP abstraction layer (DEMO/LIVE)
├── custom.css                   # Dark theme overrides
├── demo_data/                   # Pre-generated demo data
│   ├── *.json                   # Tool responses
│   └── *.md                     # Resource markdown
├── requirements.txt             # Python dependencies
├── requirements-dev.txt         # Dev/test dependencies
├── .env.example                 # Configuration template
├── tests/                       # Unit tests for the UI/bridge
├── Home-Assistant-Diagnostics-MCP-Server/   # MCP server (live mode)
│   ├── app/                     # MCP tool implementations
│   ├── tests/                   # MCP server tests
│   └── pyproject.toml           # MCP server deps
└── README.md                    # This file
```

---

## 🤝 Contributing

Built for **Hugging Face MCP Hackathon 2025**

Contributions welcome!

---

## 📄 License

MIT License - See [LICENSE](LICENSE)


---

<div align="center">

**Built with ❤️ for the smart home community**

🏷️ `mcp-in-action-track-consumer` `mcp` `home-assistant` `gemini` `openai` `llamaindex` `blaxel` `gradio`

</div>
