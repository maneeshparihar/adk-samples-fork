# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Custom server for customer service agent with Gemini Live voice support."""

import json
import asyncio
import base64
import os
import logging

from dotenv import load_dotenv

from google.genai.types import (
    Part,
    Content,
    Blob,
)

from google.adk.runners import InMemoryRunner
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig
from google.genai import types

from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect

from customer_service.agent import root_agent
from customer_service.config import Config

load_dotenv()

configs = Config()

# Override agent model to use Gemini Live for voice capabilities
# (The default config uses standard Gemini for Agent Engine deployment)
root_agent.model = "gemini-live-2.5-flash-preview-native-audio"

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def start_agent_session(user_id: str):
    """Starts an agent session with voice configuration."""

    # Create a Runner
    runner = InMemoryRunner(
        app_name=configs.app_name,
        agent=root_agent
    )

    # Create a Session
    session = await runner.session_service.create_session(
        app_name=configs.app_name,
        user_id=user_id,
    )

    # Create a LiveRequestQueue for this session
    live_request_queue = LiveRequestQueue()

    # Setup RunConfig with voice configuration
    run_config = RunConfig(
        streaming_mode="bidi",
        session_resumption=types.SessionResumptionConfig(transparent=True),
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,
                end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                prefix_padding_ms=300,  # 300ms of audio before speech detection
                silence_duration_ms=1500,  # Wait 1.5s of silence before ending turn
            )
        ),
        response_modalities=["AUDIO"],  # Enable audio output
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=os.getenv("AGENT_VOICE", "Puck")
                )
            ),
            language_code=os.getenv("AGENT_LANGUAGE", "en-US")
        ),
        output_audio_transcription={},
        input_audio_transcription={},
    )

    # Start agent session - use session.id attribute
    live_events = runner.run_live(
        user_id=user_id,
        session_id=session.id,
        live_request_queue=live_request_queue,
        run_config=run_config
    )

    return live_events, live_request_queue


async def agent_to_client_messaging(websocket: WebSocket, live_events):
    """Agent to client communication - sends responses including audio."""
    try:
        async for event in live_events:
            # Event is a Pydantic object, access attributes directly
            if not event.content:
                # Handle turn completion or interruption
                if event.turn_complete or event.interrupted:
                    message = {
                        "type": "turn_complete",
                        "interrupted": event.interrupted or False
                    }
                    await websocket.send_text(json.dumps(message))
                continue

            # Process content based on role
            if hasattr(event.content, "role") and event.content.role == "model":
                # Collect text from all parts
                text_parts = [part.text for part in event.content.parts if part.text]
                if text_parts:
                    full_text = "".join(text_parts)
                    message = {
                        "type": "text",
                        "data": full_text,
                        "is_partial": event.partial or False
                    }
                    await websocket.send_text(json.dumps(message))
                    logger.info(f"Sent text: {full_text[:100]}...")

                # Process each part for audio and tool calls
                for part in event.content.parts:
                    # Handle audio parts (voice output)
                    if part.inline_data and part.inline_data.mime_type.startswith("audio/"):
                        encoded_audio = base64.b64encode(part.inline_data.data).decode('utf-8')
                        message = {
                            "type": "audio",
                            "mime_type": part.inline_data.mime_type,
                            "data": encoded_audio
                        }
                        await websocket.send_text(json.dumps(message))
                        logger.info(f"Sent audio chunk: {len(part.inline_data.data)} bytes")

                    # Handle tool/function calls
                    elif part.function_call:
                        message = {
                            "type": "tool_call",
                            "data": {
                                "name": part.function_call.name,
                                "args": part.function_call.args or {}
                            }
                        }
                        await websocket.send_text(json.dumps(message))
                        logger.info(f"Tool call: {part.function_call.name}")

                    # Handle tool/function responses
                    elif part.function_response:
                        message = {
                            "type": "tool_response",
                            "data": {
                                "name": part.function_response.name,
                                "response": part.function_response.response or {}
                            }
                        }
                        await websocket.send_text(json.dumps(message))
                        logger.info(f"Tool response: {part.function_response.name}")

    except Exception as e:
        logger.error(f"Error in agent_to_client_messaging: {e}", exc_info=True)
        raise


async def client_to_agent_messaging(websocket: WebSocket, live_request_queue: LiveRequestQueue):
    """Client to agent communication - receives user input including audio."""
    while True:
        try:
            message_json = await websocket.receive_text()
            message = json.loads(message_json)
            mime_type = message["mime_type"]

            if mime_type == "text/plain":
                data = message["data"]
                content = Content(role="user", parts=[Part.from_text(text=data)])
                live_request_queue.send_content(content=content)
                logger.info(f"Received text: {data[:100]}...")

            elif mime_type == "audio/pcm":
                data = message["data"]
                decoded_data = base64.b64decode(data)
                live_request_queue.send_realtime(Blob(data=decoded_data, mime_type=mime_type))
                logger.debug(f"Received audio chunk: {len(decoded_data)} bytes")

            elif mime_type == "image/jpeg":
                data = message["data"]
                decoded_data = base64.b64decode(data)
                live_request_queue.send_realtime(Blob(data=decoded_data, mime_type=mime_type))
                logger.info(f"Received image: {len(decoded_data)} bytes")

            else:
                logger.warning(f"Unsupported mime type: {mime_type}")

        except WebSocketDisconnect:
            logger.info("Client disconnected (WebSocketDisconnect).")
            break

        except Exception as e:
            logger.error(f"Error in client_to_agent_messaging: {e}", exc_info=True)
            break


app = FastAPI(title="Customer Service Agent Server")


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for bidirectional communication."""
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for user: {user_id}")

    try:
        # Start agent session with voice configuration
        live_events, live_request_queue = await start_agent_session(user_id)

        # Run both messaging tasks concurrently
        await asyncio.gather(
            agent_to_client_messaging(websocket, live_events),
            client_to_agent_messaging(websocket, live_request_queue)
        )

    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}", exc_info=True)

    finally:
        logger.info(f"WebSocket connection closed for user: {user_id}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agent": configs.agent_settings.name}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

