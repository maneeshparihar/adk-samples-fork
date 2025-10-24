# Deployed Agent Demo

This folder contains tools for interacting with your **deployed agent on Vertex AI Agent Engine**.

## 📁 Files

- **`test-deployed-agent.py`** - CLI script to test the deployed agent
- **`web_backend.py`** - Backend server to connect web UI to deployed agent
- **`web_ui_deployed.html`** - Beautiful web UI for chatting with deployed agent
- **`run_web_deployed.py`** - Script to launch ADK web UI (if supported)

## 🚀 Quick Start

### Option 1: Command Line Test

Test the deployed agent from the terminal:

```bash
cd deployed-agent-demo
uv run python test-deployed-agent.py
```

Expected output:
```
🔗 Connecting to deployed agent...
✅ Connected to deployed agent!

👤 User: Hi, I need help with my garden
🤖 Agent: Hello Alex! I'm Project Pro...
```

### Option 2: Web UI

Launch a beautiful web interface to chat with your deployed agent:

**Terminal 1 - Start backend:**
```bash
cd deployed-agent-demo
uv run python web_backend.py
# Backend runs on http://localhost:8001
```

**Terminal 2 - Serve web UI:**
```bash
cd deployed-agent-demo
python3 -m http.server 9001
```

**Browser:**
1. Open http://localhost:9001/web_ui_deployed.html
2. Enter backend URL: `http://localhost:8001`
3. Type a message and start chatting!

**Features:**
- ✅ Dynamic backend URL configuration
- ✅ "New" button to start fresh session and change URL
- ✅ Real-time streaming responses
- ✅ Session management across messages

## 🔧 Configuration

The agent resource ID is currently set to:
```
projects/project1-193817/locations/us-central1/reasoningEngines/2404275688178712576
```

To update it, edit the `REASONING_ENGINE_ID` in each file.

You can also set it via environment variable:
```bash
export AGENT_RESOURCE_ID="your-new-id"
uv run python test-deployed-agent.py
```

## 🌐 For SSH Tunneling (Remote VM)

If running on a remote VM, use SSH tunneling:

```bash
# On your laptop
ssh -L 8001:localhost:8001 -L 9001:localhost:9001 maneesh@192.168.10.248

# Then access in browser
http://localhost:9001/web_ui_deployed.html

# Backend URL in the UI
http://localhost:8001
```

**Or access directly via VM IP:**
```
http://192.168.10.248:9001/web_ui_deployed.html

# Backend URL in the UI
http://192.168.10.248:8001
```

## 🆚 Deployed vs Voice Agent

| Feature | Deployed Agent (This Folder) | Voice Agent (`server.py` + `client.html`) |
|---------|------------------------------|-------------------------------------------|
| **Model** | `gemini-2.5-flash` | `gemini-live-2.5-flash-preview-native-audio` |
| **Mode** | Text-based API | Real-time voice streaming |
| **Hosting** | Vertex AI Agent Engine | Local InMemoryRunner |
| **Access** | HTTP/REST API | WebSocket |
| **Best For** | Production API access | Voice demos, live interaction |

## 📝 Notes

- The deployed agent uses the **standard Gemini model** (not live model)
- All queries go through **Vertex AI Agent Engine**
- Session management is handled automatically
- Perfect for **API-based integrations** and **production deployments**

