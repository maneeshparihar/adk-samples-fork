#!/usr/bin/env python3
"""Simple backend server for web UI connected to deployed agent"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import vertexai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from customer_service.config import Config
import json

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

configs = Config()

# Initialize Vertex AI
vertexai.init(
    project=configs.CLOUD_PROJECT,
    location=configs.CLOUD_LOCATION,
)

# Your deployed agent resource ID
REASONING_ENGINE_ID = "2404275688178712576"
resource_name = f"projects/{configs.CLOUD_PROJECT}/locations/{configs.CLOUD_LOCATION}/reasoningEngines/{REASONING_ENGINE_ID}"

# Get the deployed agent
client = vertexai.Client(
    project=configs.CLOUD_PROJECT,
    location=configs.CLOUD_LOCATION,
)

remote_app = client.agent_engines.get(name=resource_name)
print(f"✅ Connected to deployed agent: {resource_name}")


class QueryRequest(BaseModel):
    user_id: str
    session_id: str | None = None
    message: str


async def stream_response(user_id: str, session_id: str | None, message: str):
    """Stream responses from the deployed agent"""
    try:
        print(f"\n{'='*60}")
        print(f"📤 Streaming query")
        print(f"   User ID: {user_id}")
        print(f"   Session ID: {session_id}")
        print(f"   Message: {message[:50]}...")
        print(f"{'='*60}")
        
        event_count = 0
        first_event_id = None
        first_invocation_id = None
        found_session_id = None
        
        # Create the stream
        stream = remote_app.async_stream_query(
            user_id=user_id,
            session_id=session_id,
            message=message,
        )
        print(f"🔄 Stream created: {type(stream)}")
        
        async for event in stream:
            event_count += 1
            print(f"\n📨 Event #{event_count}: {type(event)}")
            
            # Debug: Print full event structure for troubleshooting
            if hasattr(event, '__dict__'):
                print(f"   Event attributes: {list(event.__dict__.keys())}")
            elif isinstance(event, dict):
                print(f"   Event keys: {list(event.keys())}")
                # For the first event, print ALL ID fields to understand the structure
                if event_count == 1:
                    print(f"   🔍 First Event ALL ID fields:")
                    if 'id' in event:
                        first_event_id = event['id']
                        print(f"      id: {event['id']}")
                    if 'invocation_id' in event:
                        first_invocation_id = event['invocation_id']
                        print(f"      invocation_id: {event['invocation_id']}")
                    if 'session_id' in event:
                        print(f"      session_id (CORRECT FIELD): {event['session_id']}")
                
                # Check if invocation_id is consistent across events
                if event_count > 1 and 'invocation_id' in event:
                    if event['invocation_id'] != first_invocation_id:
                        print(f"   ⚠️ Different invocation_id: {event['invocation_id']}")
                    else:
                        print(f"   ✓ Same invocation_id as first event")
            
            # Extract text from events
            if isinstance(event, dict):
                response_data = {}
                
                # Check for session_id (use the actual 'session_id' field, not 'id')
                if 'session_id' in event:
                    response_data['session_id'] = event['session_id']
                    found_session_id = event['session_id']
                    print(f"   ✓ Session ID (from session_id field): {event['session_id']}")
                
                # Extract text content
                if 'content' in event:
                    content = event['content']
                    if isinstance(content, dict) and 'parts' in content:
                        text_parts = []
                        for part in content['parts']:
                            if 'text' in part:
                                text_parts.append(part['text'])
                        
                        if text_parts:
                            response_data['text'] = ''.join(text_parts)
                            print(f"   ✓ Text: {response_data['text'][:100]}...")
                
                if response_data:
                    yield f"data: {json.dumps(response_data)}\n\n"
                else:
                    print(f"   ⚠️ No data extracted from this event")
                    
            elif hasattr(event, 'content') and event.content:
                response_data = {}
                
                # Get session_id if available (use the actual 'session_id' attribute, not 'id')
                if hasattr(event, 'session_id'):
                    response_data['session_id'] = event.session_id
                    found_session_id = event.session_id
                    print(f"   ✓ Session ID (from session_id attr): {event.session_id}")
                
                content = event.content
                if hasattr(content, 'parts'):
                    text_parts = []
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                    
                    if text_parts:
                        response_data['text'] = ''.join(text_parts)
                        print(f"   ✓ Text: {response_data['text'][:100]}...")
                
                if response_data:
                    yield f"data: {json.dumps(response_data)}\n\n"
                else:
                    print(f"   ⚠️ No data extracted from this event")
            else:
                print(f"   ⚠️ Unknown event format, skipping")
        
        print(f"\n✅ Stream completed - Total events: {event_count}")
        if event_count == 0:
            print(f"⚠️ WARNING: No events received from agent!")
            print(f"   This usually means:")
            print(f"   1. Session ID is invalid or expired")
            print(f"   2. Agent returned empty response")
            print(f"   3. Agent encountered an error")
        elif event_count > 0:
            print(f"\n💡 ID Analysis:")
            print(f"   First event 'id': {first_event_id}")
            print(f"   First event 'invocation_id': {first_invocation_id}")
            if found_session_id:
                print(f"   ✅ Found 'session_id' field: {found_session_id}")
                print(f"   This is the correct field to use for follow-up queries!")
            else:
                print(f"   ⚠️ No 'session_id' field found in any event!")
                print(f"   The agent may not support multi-turn conversations")
    
    except Exception as e:
        import traceback
        print(f"\n❌ Error in stream: {e}")
        print(f"   Traceback:")
        traceback.print_exc()
        error_data = {'error': str(e)}
        yield f"data: {json.dumps(error_data)}\n\n"


@app.post("/query")
async def query_agent(request: QueryRequest):
    """Query the deployed agent and stream the response"""
    return StreamingResponse(
        stream_response(request.user_id, request.session_id, request.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx/proxy
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": resource_name,
        "project": configs.CLOUD_PROJECT,
        "location": configs.CLOUD_LOCATION
    }


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting web backend for deployed agent...")
    print(f"   Backend: http://localhost:8001")
    print(f"   Health check: http://localhost:8001/health")
    print(f"\n📝 To use the web UI:")
    print(f"   1. Keep this backend running")
    print(f"   2. In another terminal: cd deployed-agent-demo && python3 -m http.server 9001")
    print(f"   3. Open: http://localhost:9001/web_ui_deployed.html")
    uvicorn.run(app, host="0.0.0.0", port=8001)

