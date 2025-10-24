# Voice-Enabled Customer Service Agent Setup

This guide explains how to run the customer service agent with Gemini Live voice support.

## Problem

The default `adk web` command doesn't properly configure voice output for Gemini Live models. While it can receive audio input, it won't generate audio responses, leading to the agent only speaking once or not at all.

## Solution

We've created a custom FastAPI server (`server.py`) that properly configures the `RunConfig` with:
- `response_modalities = ["AUDIO"]` - Enables audio output
- `speech_config` - Configures voice and language
- Proper bidirectional streaming setup

## Setup Instructions

### 1. Install Dependencies

```bash
cd python/agents/customer-service
uv sync
```

This will install the additional dependencies (FastAPI, uvicorn, python-dotenv) that were added to `pyproject.toml`.

### 2. Configure Environment Variables

Create a `.env` file in the `customer-service` directory:

```bash
cp .env.example .env
```

Then edit `.env` with your settings:

```bash
# Required: Google Cloud Configuration
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-actual-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# Required: Voice Configuration
AGENT_VOICE=Puck
AGENT_LANGUAGE=en-US

# Required: Application Name
APP_NAME=customer_service_app
```

### 3. Available Voice Options

Choose from these voice personalities:

- **Puck**: Conversational, friendly tone (recommended for customer service)
- **Charon**: Deep, authoritative voice
- **Kore**: Warm, empathetic voice
- **Fenrir**: Energetic, dynamic voice
- **Aoede**: Calm, soothing voice

### 4. Run the Custom Server

Instead of `adk web`, run:

```bash
cd python/agents/customer-service
uv run python server.py
```

Or using uvicorn directly:

```bash
uv run uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

The server will start at `http://0.0.0.0:8000`

### 5. Connect Your Client

The WebSocket endpoint is available at:

```
ws://localhost:8000/ws/{user_id}
```

Replace `{user_id}` with a unique identifier for the user session.

## WebSocket Message Format

### Client to Server (Input)

```json
{
  "mime_type": "text/plain",
  "data": "Hello, I need help with my garden"
}
```

```json
{
  "mime_type": "audio/pcm",
  "data": "<base64-encoded-audio>"
}
```

```json
{
  "mime_type": "image/jpeg",
  "data": "<base64-encoded-image>"
}
```

### Server to Client (Output)

```json
{
  "type": "text",
  "data": "Hello! How can I help you today?"
}
```

```json
{
  "type": "audio",
  "mime_type": "audio/pcm",
  "data": "<base64-encoded-audio>"
}
```

```json
{
  "type": "tool_call",
  "data": {
    "name": "access_cart_information",
    "args": {...}
  }
}
```

## Testing

### Using curl for WebSocket

```bash
# Check health endpoint
curl http://localhost:8000/health

# For WebSocket testing, use a WebSocket client or the browser
```

### Using Python Client

```python
import asyncio
import websockets
import json

async def test_agent():
    uri = "ws://localhost:8000/ws/test_user_123"
    async with websockets.connect(uri) as websocket:
        # Send a message
        message = {
            "mime_type": "text/plain",
            "data": "Hi, I need help with my garden"
        }
        await websocket.send(json.dumps(message))
        
        # Receive responses
        async for message in websocket:
            response = json.loads(message)
            print(f"Received: {response['type']}")
            if response['type'] == 'text':
                print(f"Text: {response['data']}")
            elif response['type'] == 'audio':
                print(f"Audio received: {len(response['data'])} bytes")
            elif response['type'] == 'end':
                break

asyncio.run(test_agent())
```

## Troubleshooting

### No Audio Output

1. Check that `AGENT_VOICE` and `AGENT_LANGUAGE` are set in `.env`
2. Verify the model is `gemini-live-2.5-flash-preview-native-audio-09-2025`
3. Check server logs for errors related to speech configuration

### Connection Issues

1. Ensure the server is running: `curl http://localhost:8000/health`
2. Check firewall settings allow port 8000
3. Verify WebSocket URL format: `ws://localhost:8000/ws/user_id`

### Logging Issues Fixed

The logging has been configured to prevent sensitive information leakage:
- Root logger set to `WARNING` level
- Only `customer_service` module logs at `DEBUG` level
- ADK's internal library logs (like `google_llm.py`) won't print sensitive agent configurations

## Additional Configuration

You can modify the `RunConfig` in `server.py` to adjust:

- **Speech sensitivity**: `start_of_speech_sensitivity` and `end_of_speech_sensitivity`
- **Audio detection timing**: `prefix_padding_ms` and `silence_duration_ms`
- **Session resumption**: Enable/disable transparent session resumption
- **Streaming mode**: Currently set to `"bidi"` for bidirectional streaming

## References

- [Gemini Live API Documentation](https://cloud.google.com/vertex-ai/docs/generative-ai/multimodal/live-api)
- [ADK RunConfig Documentation](https://github.com/google/adk-python)
- [Realtime Conversational Agent Example](/python/agents/realtime-conversational-agent/)

