#!/usr/bin/env python3
"""Test the deployed customer service agent"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import vertexai
import asyncio
import os

# Your deployed agent resource ID
# Update this to your agent's ID after deployment
REASONING_ENGINE_ID = os.getenv("AGENT_RESOURCE_ID", "2404275688178712576")
PROJECT_ID = "project1-193817"
LOCATION = "us-central1"
USER_ID = "demo_user_123"

# Initialize Vertex AI Client (new API)
print("🔗 Connecting to deployed agent...")
client = vertexai.Client(
    project=PROJECT_ID,
    location=LOCATION,
)

# Get the agent based on resource id
resource_name = f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{REASONING_ENGINE_ID}"
adk_app = client.agent_engines.get(name=resource_name)

print(f"✅ Connected to deployed agent!\n")

# Test queries
queries = [
    "Hi, I need help with my garden",
    "What's in my cart?",
    "Can you recommend some products for tomatoes?",
]

async def test_agent():
    """Test the deployed agent with streaming queries"""
    session_id = None  # Let it auto-create a session
    
    for query in queries:
        print(f"👤 User: {query}")
        print("🤖 Agent: ", end="", flush=True)
        
        try:
            # Use async_stream_query as per documentation
            async for event in adk_app.async_stream_query(
                user_id=USER_ID,
                session_id=session_id,  # Optional - auto-creates if None
                message=query,
            ):
                # Extract text from events
                if isinstance(event, dict):
                    # Handle dict-style events
                    if 'content' in event:
                        content = event['content']
                        if isinstance(content, dict) and 'parts' in content:
                            for part in content['parts']:
                                if 'text' in part:
                                    print(part['text'], end="", flush=True)
                elif hasattr(event, 'content') and event.content:
                    # Handle object-style events
                    content = event.content
                    if hasattr(content, 'parts'):
                        for part in content.parts:
                            if hasattr(part, 'text') and part.text:
                                print(part.text, end="", flush=True)
                
                # Capture session_id for subsequent queries
                if session_id is None:
                    if isinstance(event, dict) and 'session_id' in event:
                        session_id = event['session_id']
                    elif hasattr(event, 'session_id'):
                        session_id = event.session_id
            
            print()  # New line after response
        except Exception as e:
            print(f"\n⚠️ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print("="*80 + "\n")
    
    print("✅ Demo complete!")

# Run the async test
asyncio.run(test_agent())

