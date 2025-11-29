# 🚀 Home Assistant Diagnostics Agent - Quick Start

## 📋 Prerequisites

1. **Python 3.11+** installed
2. **Gemini API Key** - Get from [Google AI Studio](https://aistudio.google.com/apikey)
3. **(Optional)** Home Assistant instance for LIVE mode

---

## 🎯 Option 1: Demo Mode (Fastest)

Perfect for testing and HuggingFace Spaces deployment.

```bash
# 1. Navigate to app directory
cd Home-Assistant-Diagnostics-Agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Gemini API key
export GEMINI_API_KEY="your_gemini_api_key_here"

# 4. Run in demo mode
export DEMO_MODE=true
python app.py
```

**That's it!** Open http://localhost:7861

The app will use pre-generated demo data (no Home Assistant required).

Try it online: [Hugging Face Space](https://huggingface.co/spaces/MCP-1st-Birthday/Home-Assistant-Diagnostics-Agent)

---

## 🏠 Option 2: Live Mode (Full Features)

Connect to your real Home Assistant instance.

### Step 1: Get Home Assistant Token

1. Open your Home Assistant
2. Go to: **Profile → Security**
3. Scroll to **Long-Lived Access Tokens**
4. Click **Create Token**
5. Name it: "MCP Diagnostics"
6. Copy the token (you won't see it again!)

### Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your favorite editor
nano .env  # or vi, code, etc.
```

**Set these values in `.env`:**

```bash
# Switch to LIVE mode (for demo, leave DEMO_MODE=true and HA_* blank)
DEMO_MODE=false
GEMINI_API_KEY=your_gemini_key_here
HA_URL=        # set when using LIVE mode
HA_TOKEN=      # set when using LIVE mode
```

### Step 3: Install MCP Server

```bash
# Navigate to MCP server directory
cd Home-Assistant-Diagnostics-MCP-Server

# Install MCP server in development mode
pip install -e .

# Test MCP server
python -m app.run
# Should connect to your HA and show available tools
# Press Ctrl+C to stop

# Return to gradio app
cd ..
```

### Step 4: Run App

```bash
# Load environment variables
source .env  # on macOS/Linux
# or
set -a; source .env; set +a  # if above doesn't work

# Run app
python app.py
```

**Open http://localhost:7861**

You're now connected to your **real Home Assistant**! 🎉

---

## 🧪 Testing the App

### 1. Health Dashboard Tab

Click **"Run Full Diagnostics"**

You should see:
- ✅ Overall health score
- ✅ Zigbee mesh status
- ✅ Battery health
- ✅ Energy consumption
- ✅ Quick stats

### 2. AI Chat Tab

Try these example queries:

```
"Run a complete system health check"
"Analyze my Zigbee mesh network"
"Which batteries are low?"
"Show energy consumption"
```

You should see:
- ✅ Natural language responses
- ✅ Tools timeline showing which MCP tools were used
- ✅ Markdown-formatted results

### 3. Investigation Lab Tab

**Entity Investigation:**
- Enter an entity ID (e.g., `light.kitchen`)
- Click "Investigate"
- See detailed diagnostic report

**Cleanup Center:**
- Click "Scan for Orphan Entities"
- See entities not used in any automation/script

---

## ❓ Troubleshooting

### "Import 'gradio' could not be resolved"

```bash
pip install gradio>=5.0.0
```

### "Import 'google.genai' could not be resolved"

```bash
pip install google-genai>=0.3.0
```

### "Gemini API not available"

Check your API key:

```bash
echo $GEMINI_API_KEY
```

If empty, set it:

```bash
export GEMINI_API_KEY="your_key_here"
```

### "MCP client not available"

Only needed for LIVE mode:

```bash
pip install mcp>=1.0.0
```

### Can't connect to Home Assistant (LIVE mode)

1. **Check URL:**
   ```bash
   curl -k https://your-ha-instance.duckdns.org:8123/api/
   # Should return {"message": "API running."}
   ```

2. **Test token:**
   ```bash
   curl -k -H "Authorization: Bearer YOUR_TOKEN" \
     https://your-ha-instance.duckdns.org:8123/api/
   # Should return {"message": "API running."}
   ```

3. **Check .env file:**
   ```bash
   cat .env | grep HA_URL
   cat .env | grep HA_TOKEN
   ```

### App shows "DEMO MODE" but I set DEMO_MODE=false

Make sure environment variables are loaded:

```bash
# Load .env manually
export $(cat .env | grep -v '#' | xargs)

# Or use python-dotenv
pip install python-dotenv
```

---

## 🎨 Customization

### Change App Port

```bash
# Edit app.py, line ~545
demo.launch(
    server_port=8080,  # Change from 7860
    ...
)
```

### Add Custom Tools

See [Development section in README.md](README.md#development)

### Modify UI Theme

```bash
# Edit app.py, line ~15
THEME = gr.themes.Soft(
    primary_hue="green",  # Change from "blue"
    ...
)
```

---

## 🚢 Deploying to HuggingFace Spaces

### 1. Create Space

1. Go to [HuggingFace Spaces](https://huggingface.co/spaces)
2. Click **"Create new Space"**
3. Choose **Gradio** SDK
4. Name it: `ha-doctor`

### 2. Upload Files

Upload these files:
- `app.py`
- `agent.py`
- `mcp_bridge.py`
- `requirements.txt`
- `demo_data/` (entire folder)
- `.env.example` → rename to `.env`

### 3. Configure Space

In Space settings, add **Secret**:
- Name: `GEMINI_API_KEY`
- Value: Your Gemini API key

Set `.env`:
```bash
DEMO_MODE=true
GEMINI_API_KEY=  # Will be loaded from Space secret
```

### 4. Deploy

Space will automatically build and deploy!

---

## 📚 Next Steps

1. ✅ Read [full README.md](README.md) for architecture details
2. ✅ Check [MCP server README](../home-assistant-diagnostics-mcp/README.md) for tool documentation
3. ✅ Try example queries in AI Chat
4. ✅ Run full diagnostics on your HA
5. ✅ Explore Investigation Lab features

---

## 💬 Need Help?

Check the [main README](README.md) or open an issue!

---

**Happy Diagnosing! 🏥**
