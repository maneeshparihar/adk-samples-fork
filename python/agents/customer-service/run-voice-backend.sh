#!/bin/bash
export GOOGLE_CLOUD_PROJECT=project1-193817
export GOOGLE_CLOUD_LOCATION=us-central1 
/home/maneeshparihar/.local/bin/uv run uvicorn server:app --reload --host 0.0.0.0 --port 8002