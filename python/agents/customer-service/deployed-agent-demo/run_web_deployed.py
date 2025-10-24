#!/usr/bin/env python3
"""Run ADK web UI connected to deployed agent"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import vertexai
from customer_service.config import Config

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

print(f"🔗 Connecting to deployed agent...")
print(f"   Resource: {resource_name}")

remote_app = client.agent_engines.get(name=resource_name)

print(f"✅ Connected to deployed agent!")
print(f"\n🌐 Starting ADK web UI...")
print(f"   The web UI will open in your browser at http://localhost:8000")
print(f"   This UI is connected to your PRODUCTION agent on Vertex AI!\n")

# Launch web UI with the remote agent
remote_app.web(port=8000)

