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
        async for event in remote_app.async_stream_query(
            user_id=user_id,
            session_id=session_id,
            message=message,
        ):
            # Extract text from events
            if isinstance(event, dict):
                response_data = {}
                
                # Check for session_id
                if 'id' in event:
                    response_data['session_id'] = event['id']
                
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
                
                if response_data:
                    yield f"data: {json.dumps(response_data)}\n\n"
                    
            elif hasattr(event, 'content') and event.content:
                response_data = {}
                
                # Get session_id if available
                if hasattr(event, 'id'):
                    response_data['session_id'] = event.id
                
                content = event.content
                if hasattr(content, 'parts'):
                    text_parts = []
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                    
                    if text_parts:
                        response_data['text'] = ''.join(text_parts)
                
                if response_data:
                    yield f"data: {json.dumps(response_data)}\n\n"
    
    except Exception as e:
        error_data = {'error': str(e)}
        yield f"data: {json.dumps(error_data)}\n\n"


@app.post("/query")
async def query_agent(request: QueryRequest):
    """Query the deployed agent and stream the response"""
    return StreamingResponse(
        stream_response(request.user_id, request.session_id, request.message),
        media_type="text/event-stream"
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

