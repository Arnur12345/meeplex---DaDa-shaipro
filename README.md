# RavenAI: API for **Real-Time Meeting Transcription**

RavenAI is an API for **real-time meeting transcription** leveraging **meeting bots** and direct **streaming from web/mobile apps**. It's designed to extract knowledge from various platforms, currently including:

  * **Google Meet**
  * **Zoom** (coming soon)
  * **Microsoft Teams** (coming soon)

This project serves as a **privacy-first, open-source** alternative, focusing on delivering **clean, private, real-time transcription under your control**, allowing you to safely build on top of its capabilities.

  * **MCP server for agents (new microservice):** Full RavenAI API access from any MCP-capable agent (Claude Desktop, Cursor, etc.). See `services/mcp`. Built with [https://github.com/tadata-org/fastpi\_mcp](https://github.com/tadata-org/fastpi_mcp)
  * **Hallucination filtering:** Greatly reduced hallucinations in selected languages. Contributions welcome — add phrases to `services/WhisperLive/hallucinations/` for your language.
  * **Google Meet UI updates:** Bot adjusted to the latest Google Meet UI changes for reliable joining and capture.

## Build on Top. In Hours, Not Months

**Build powerful meeting assistants (like Otter.ai, Fireflies.ai, Fathom) for your startup, internal use, or custom integrations.**

The RavenAI API provides powerful abstractions and a clear separation of concerns, enabling rapid development of sophisticated applications. For instance, the RavenAI Example Client was built in just 3 hours of live coding with Cursor, demonstrating the speed of development possible with RavenAI.

Additionally, with our **n8n integration**, you can create complex workflows with no code, utilizing real-time transcription from Google Meet (with support for other platforms coming soon).

  * [api-gateway](https://www.google.com/search?q=./services/api-gateway): Routes API requests to appropriate services
  * [mcp](https://www.google.com/search?q=./services/mcp): Provides MCP-capable agents with RavenAI as a toolkit
  * [bot-manager](https://www.google.com/search?q=./services/bot-manager): Handles bot lifecycle management
  * [ravenai-bot](https://www.google.com/search?q=./services/vexa-bot): The bot that joins meetings and captures audio
  * [WhisperLive](https://www.google.com/search?q=./services/WhisperLive): Real-time audio transcription service
  * [transcription-collector](https://www.google.com/search?q=./services/transcription-collector): Processes and stores transcription segments
  * [llm-processor](https://www.google.com/search?q=./services/llm-processor): Processes transcripts using **Mistral-7B** for enhanced readability and features.
  * [tts-processor](https://www.google.com/search?q=./services/tts-processor): Converts text to speech using **gTTS** (Google Text-to-Speech).
  * [Database models](https://www.google.com/search?q=./libs/shared-models/shared_models/models.py): Data structures for storing meeting information

## Public Hosted API

🔑 Get your API key at [www.vexa.ai](https://www.vexa.ai/?utm_source=github&utm_medium=readme&utm_campaign=vexa_repo) to try RavenAI instantly.

🚀 Read [DEPLOYMENT.md](https://www.google.com/search?q=DEPLOYMENT.md) for self-hosting and local run with single `make all` on CPU even on laptop or on your GPU server.

### Key features in this release:

  * **Google Meet Bot Integration**: Programmatically send bots to join and transcribe meetings
  * **Real-Time Transcription**: Access meeting transcripts as they happen through the API
  * **Real-Time Translation**: Change the language of transcription for instant translations across 99 languages

## API Capabilities

## Simple API Integration

**Set up and running in under 5 minutes**

Get your API key in 3 clicks and start using the API immediately.

### Create a meeting bot

```bash
# POST /bots
curl -X POST http://74.161.160.54:18056)/bots \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "native_meeting_id": "xxx-xxxx-xxx",
    "platform": "google_meet"
  }'
```

### Retrieve meeting transcript

```bash
# GET /transcripts/{platform}/{native_meeting_id}
# Example assumes native_meeting_id is derived from the meeting URL
curl -H "X-API-Key: YOUR_CLIENT_API_KEY" \
  http://74.161.160.54:18056/transcripts/google_meet/xxx-xxxx-xxx
```

```json
{
  "data": {
    "meeting_id": "meet_abc123",
    "transcripts": [
      {
        "time": "00:01:15",
        "speaker": "John Smith",
        "text": "Let's discuss the quarterly results."
      },
      {
        "time": "00:01:23",
        "speaker": "Sarah Johnson",
        "text": "The Q3 revenue exceeded our projections by 15%."
      },
      {
        "time": "00:01:42",
        "speaker": "Michael Chen",
        "text": "Customer acquisition costs decreased by 12% from last quarter."
      }
    ]
  }
}
```


### Features:

  * **Real-time multilingual transcription** supporting **99 languages** with **Whisper**
  * **Real-time translation** across all 99 supported languages
  * **LLM Processing:** Utilizing **Mistral-7B** for enhancing transcript readability and other advanced features.
  * **TTS Processing:** Converting text to speech using **gTTS**.

## Current Status

  * **Public API**: Fully available with self-service API keys at [www.vexa.ai](https://raven-ai-client.vercel.app)
  * **Google Meet Bot:** Fully operational bot for joining Google Meet calls
  * **Real-time Transcription:** Low-latency, multilingual transcription service is live
  * **Real-time Translation:** Instant translation between 99 supported languages
  * **LLM Processing:** Integrated with **Mistral-7B** for advanced text processing.
  * **TTS Processing:** Integrated with **gTTS** for text-to-speech functionality.
  * **Pending:** Speaker identification is under development

## Coming Next

  * **Microsoft Teams Bot:** Integration for automated meeting attendance (June 2025)
  * **Zoom Bot:** Integration for automated meeting attendance (July 2025)
  * **Direct Streaming:** Ability to stream audio directly from web/mobile apps
  * **Meeting Knowledge Extraction (RAG):** Post-meeting analysis and Q\&A

## Self-Deployment

For **security-minded companies**, RavenAI offers complete **self-deployment** options.

To run RavenAI locally on your own infrastructure, the primary command you'll use after cloning the repository is `make all`. This command sets up the environment (CPU by default, or GPU if specified), builds all necessary Docker images, and starts the services.

Detailed instructions: [Local Deployment and Testing Guide](https://www.google.com/search?q=DEPLOYMENT.md).

[](https://opensource.org/licenses/Apache-2.0)

RavenAI is licensed under the **Apache License, Version 2.0**. See [LICENSE](https://www.google.com/search?q=LICENSE) for the full license text.

The RavenAI name and logo are trademarks of **RavenAI Inc**.
