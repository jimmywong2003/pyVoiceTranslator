# API Documentation

## VoiceTranslate Pro - RESTful API Reference

This document provides comprehensive documentation for the VoiceTranslate Pro RESTful API, enabling integration with third-party applications and services.

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Base URL](#base-url)
4. [Rate Limits](#rate-limits)
5. [Endpoints](#endpoints)
6. [Error Handling](#error-handling)
7. [WebSocket API](#websocket-api)
8. [SDKs and Libraries](#sdks-and-libraries)
9. [Changelog](#changelog)

---

## Overview

The VoiceTranslate Pro API provides programmatic access to all core translation features:

- **Text Translation**: Translate text between 50+ languages
- **Audio Translation**: Translate speech from audio files
- **Real-time Translation**: Stream audio for live translation
- **Language Management**: List supported languages and configurations
- **Session Management**: Manage translation sessions

### API Features

| Feature | Description |
|---------|-------------|
| RESTful Design | Standard HTTP methods and status codes |
| JSON Format | All requests and responses in JSON |
| WebSocket Support | Real-time streaming capabilities |
| Authentication | API key-based authentication |
| Rate Limiting | Fair usage policies |
| Webhooks | Event notifications |

---

## Authentication

All API requests require authentication using an API key.

### Obtaining an API Key

1. Sign up at [VoiceTranslate Pro Dashboard](https://dashboard.voicetranslate.pro)
2. Navigate to API Keys section
3. Generate a new API key
4. Copy and securely store your key

### Using API Keys

Include your API key in the `Authorization` header:

```http
Authorization: Bearer YOUR_API_KEY
```

### Example

```bash
curl -X GET "https://api.voicetranslate.pro/v1/languages" \
  -H "Authorization: Bearer sk_live_1234567890abcdef"
```

### Python Example

```python
import requests

headers = {
    "Authorization": "Bearer sk_live_1234567890abcdef",
    "Content-Type": "application/json"
}

response = requests.get(
    "https://api.voicetranslate.pro/v1/languages",
    headers=headers
)
```

---

## Base URL

### Production

```
https://api.voicetranslate.pro/v1
```

### Sandbox (Testing)

```
https://api.sandbox.voicetranslate.pro/v1
```

### Local Development

```
http://localhost:8000/api/v1
```

---

## Rate Limits

Rate limits are applied per API key to ensure fair usage.

### Limits by Plan

| Plan | Requests/Minute | Requests/Hour | Concurrent Streams |
|------|-----------------|---------------|-------------------|
| Free | 60 | 1,000 | 1 |
| Pro | 300 | 10,000 | 5 |
| Enterprise | 1,000 | 100,000 | 20 |
| Custom | Custom | Custom | Custom |

### Rate Limit Headers

Each response includes rate limit information:

```http
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 299
X-RateLimit-Reset: 1640995200
```

### Exceeding Limits

When rate limits are exceeded, the API returns:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
```

---

## Endpoints

### Health Check

Check API availability and status.

```http
GET /health
```

#### Response

```json
{
  "status": "healthy",
  "version": "2.1.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "translation": "operational",
    "asr": "operational",
    "tts": "operational"
  }
}
```

---

### List Languages

Get a list of supported languages.

```http
GET /languages
```

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `type` | string | No | Filter by type: `source`, `target`, or `all` |
| `capability` | string | No | Filter by capability: `asr`, `translation`, `tts` |

#### Response

```json
{
  "languages": [
    {
      "code": "en",
      "name": "English",
      "native_name": "English",
      "capabilities": ["asr", "translation", "tts"],
      "supported_pairs": ["zh", "ja", "fr", "de", "es"]
    },
    {
      "code": "zh",
      "name": "Chinese (Simplified)",
      "native_name": "简体中文",
      "capabilities": ["asr", "translation", "tts"],
      "supported_pairs": ["en", "ja", "ko"]
    }
  ],
  "total": 50
}
```

#### Example

```bash
curl -X GET "https://api.voicetranslate.pro/v1/languages?type=source" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### Translate Text

Translate text from one language to another.

```http
POST /translate/text
```

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Text to translate (max 5000 characters) |
| `source_lang` | string | Yes | Source language code or `auto` |
| `target_lang` | string | Yes | Target language code |
| `context` | string | No | Additional context for better translation |
| `formality` | string | No | Formality level: `formal`, `informal`, `default` |

#### Request Example

```json
{
  "text": "Hello, how are you today?",
  "source_lang": "en",
  "target_lang": "zh",
  "context": "casual greeting",
  "formality": "informal"
}
```

#### Response

```json
{
  "translation": "你好，你今天怎么样？",
  "source_lang": "en",
  "target_lang": "zh",
  "detected_source": "en",
  "confidence": 0.98,
  "alternatives": [
    "你好，今天过得怎么样？",
    "嗨，你今天好吗？"
  ],
  "characters_used": 25,
  "processing_time": 0.234
}
```

#### Example

```bash
curl -X POST "https://api.voicetranslate.pro/v1/translate/text" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, how are you today?",
    "source_lang": "en",
    "target_lang": "zh"
  }'
```

#### Python Example

```python
import requests

response = requests.post(
    "https://api.voicetranslate.pro/v1/translate/text",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={
        "text": "Hello, how are you today?",
        "source_lang": "en",
        "target_lang": "zh"
    }
)

result = response.json()
print(result["translation"])
```

---

### Translate Audio

Translate speech from an audio file.

```http
POST /translate/audio
```

#### Request

**Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `audio` | file | Yes | Audio file (MP3, WAV, M4A, OGG) |
| `source_lang` | string | Yes | Source language code or `auto` |
| `target_lang` | string | Yes | Target language code |
| `output_format` | string | No | Output format: `text`, `audio`, `both` |
| `voice` | string | No | TTS voice ID for audio output |

#### Supported Audio Formats

| Format | Extension | Max Size |
|--------|-----------|----------|
| MP3 | .mp3 | 50 MB |
| WAV | .wav | 100 MB |
| M4A | .m4a | 50 MB |
| OGG | .ogg | 50 MB |
| FLAC | .flac | 100 MB |

#### Response (text output)

```json
{
  "transcription": "Hello, how are you today?",
  "translation": "你好，你今天怎么样？",
  "source_lang": "en",
  "target_lang": "zh",
  "detected_source": "en",
  "confidence": 0.95,
  "duration": 3.5,
  "processing_time": 2.1
}
```

#### Response (audio output)

```json
{
  "transcription": "Hello, how are you today?",
  "translation": "你好，你今天怎么样？",
  "audio_url": "https://cdn.voicetranslate.pro/audio/abc123.mp3",
  "audio_format": "mp3",
  "duration": 3.2,
  "expires_at": "2024-01-15T11:30:00Z"
}
```

#### Example

```bash
curl -X POST "https://api.voicetranslate.pro/v1/translate/audio" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "audio=@recording.wav" \
  -F "source_lang=en" \
  -F "target_lang=zh" \
  -F "output_format=both"
```

#### Python Example

```python
import requests

with open("recording.wav", "rb") as f:
    response = requests.post(
        "https://api.voicetranslate.pro/v1/translate/audio",
        headers={"Authorization": "Bearer YOUR_API_KEY"},
        files={"audio": f},
        data={
            "source_lang": "en",
            "target_lang": "zh",
            "output_format": "both"
        }
    )

result = response.json()
print(result["translation"])
```

---

### Batch Translation

Translate multiple texts or audio files in a single request.

```http
POST /translate/batch
```

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `items` | array | Yes | Array of translation requests |
| `source_lang` | string | Yes | Source language for all items |
| `target_lang` | string | Yes | Target language for all items |

#### Request Example

```json
{
  "items": [
    {"text": "Hello"},
    {"text": "How are you?"},
    {"text": "Thank you"}
  ],
  "source_lang": "en",
  "target_lang": "zh"
}
```

#### Response

```json
{
  "results": [
    {
      "original": "Hello",
      "translation": "你好",
      "confidence": 0.99
    },
    {
      "original": "How are you?",
      "translation": "你好吗？",
      "confidence": 0.98
    },
    {
      "original": "Thank you",
      "translation": "谢谢",
      "confidence": 0.99
    }
  ],
  "total_items": 3,
  "successful": 3,
  "failed": 0,
  "processing_time": 0.567
}
```

---

### Text-to-Speech

Convert text to speech in the target language.

```http
POST /tts
```

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Text to synthesize |
| `language` | string | Yes | Language code |
| `voice` | string | No | Voice ID (default: auto-selected) |
| `speed` | float | No | Speech speed: 0.5 to 2.0 (default: 1.0) |
| `pitch` | float | No | Voice pitch: -10 to 10 (default: 0) |
| `format` | string | No | Audio format: `mp3`, `wav`, `ogg` |

#### Response

```json
{
  "audio_url": "https://cdn.voicetranslate.pro/tts/xyz789.mp3",
  "format": "mp3",
  "duration": 2.5,
  "voice": "zh-female-1",
  "expires_at": "2024-01-15T11:30:00Z"
}
```

#### Example

```bash
curl -X POST "https://api.voicetranslate.pro/v1/tts" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你好，世界",
    "language": "zh",
    "speed": 1.0,
    "format": "mp3"
  }'
```

---

### List Voices

Get available TTS voices for a language.

```http
GET /voices
```

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `language` | string | Yes | Language code |
| `gender` | string | No | Filter by gender: `male`, `female`, `neutral` |

#### Response

```json
{
  "voices": [
    {
      "id": "zh-female-1",
      "name": "Xiaomei",
      "gender": "female",
      "language": "zh",
      "preview_url": "https://cdn.voicetranslate.pro/voices/zh-female-1.mp3",
      "styles": ["neutral", "friendly", "professional"]
    },
    {
      "id": "zh-male-1",
      "name": "Xiaoming",
      "gender": "male",
      "language": "zh",
      "preview_url": "https://cdn.voicetranslate.pro/voices/zh-male-1.mp3",
      "styles": ["neutral", "authoritative"]
    }
  ]
}
```

---

### Session Management

#### Create Session

Create a new translation session.

```http
POST /sessions
```

#### Request Body

```json
{
  "source_lang": "en",
  "target_lang": "zh",
  "settings": {
    "auto_detect": true,
    "save_history": true,
    "output_audio": true
  }
}
```

#### Response

```json
{
  "session_id": "sess_1234567890",
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-01-15T11:30:00Z",
  "ws_url": "wss://api.voicetranslate.pro/v1/ws/sess_1234567890"
}
```

#### Get Session

```http
GET /sessions/{session_id}
```

#### Response

```json
{
  "session_id": "sess_1234567890",
  "status": "active",
  "source_lang": "en",
  "target_lang": "zh",
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-01-15T11:30:00Z",
  "translations_count": 15
}
```

#### Delete Session

```http
DELETE /sessions/{session_id}
```

---

## Error Handling

The API uses standard HTTP status codes and returns detailed error information.

### Error Response Format

```json
{
  "error": {
    "code": "invalid_language",
    "message": "The specified language code is not supported",
    "details": {
      "provided": "xx",
      "supported": ["en", "zh", "ja", "fr", "de", "es"]
    },
    "request_id": "req_abc123def456"
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `invalid_request` | 400 | Malformed request |
| `invalid_language` | 400 | Unsupported language code |
| `invalid_audio` | 400 | Invalid audio file |
| `unauthorized` | 401 | Invalid or missing API key |
| `forbidden` | 403 | Insufficient permissions |
| `not_found` | 404 | Resource not found |
| `rate_limited` | 429 | Rate limit exceeded |
| `server_error` | 500 | Internal server error |
| `service_unavailable` | 503 | Service temporarily unavailable |

### Handling Errors

```python
import requests

response = requests.post(
    "https://api.voicetranslate.pro/v1/translate/text",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={"text": "Hello", "source_lang": "en", "target_lang": "xx"}
)

if response.status_code != 200:
    error = response.json()["error"]
    print(f"Error {error['code']}: {error['message']}")
    # Handle error appropriately
```

---

## WebSocket API

For real-time translation, use the WebSocket API.

### Connection

```javascript
const ws = new WebSocket(
  'wss://api.voicetranslate.pro/v1/ws',
  [],
  {
    headers: {
      'Authorization': 'Bearer YOUR_API_KEY'
    }
  }
);
```

### Message Format

#### Client to Server

```json
{
  "type": "audio_chunk",
  "session_id": "sess_123456",
  "data": "base64_encoded_audio_data",
  "timestamp": 1640995200000
}
```

#### Server to Client

```json
{
  "type": "translation",
  "transcription": "Hello world",
  "translation": "你好，世界",
  "confidence": 0.95,
  "is_final": false,
  "timestamp": 1640995200100
}
```

### Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `audio_chunk` | Client → Server | Send audio data |
| `translation` | Server → Client | Receive translation |
| `config` | Client → Server | Configure session |
| `error` | Server → Client | Error notification |
| `ping`/`pong` | Both | Keep connection alive |

### Example WebSocket Client

```python
import websocket
import json
import base64

def on_message(ws, message):
    data = json.loads(message)
    if data["type"] == "translation":
        print(f"Transcription: {data['transcription']}")
        print(f"Translation: {data['translation']}")

def on_open(ws):
    # Configure session
    ws.send(json.dumps({
        "type": "config",
        "source_lang": "en",
        "target_lang": "zh"
    }))
    
    # Send audio data
    with open("audio_chunk.wav", "rb") as f:
        audio_data = base64.b64encode(f.read()).decode()
    
    ws.send(json.dumps({
        "type": "audio_chunk",
        "data": audio_data
    }))

ws = websocket.WebSocketApp(
    "wss://api.voicetranslate.pro/v1/ws",
    header={"Authorization": "Bearer YOUR_API_KEY"},
    on_message=on_message,
    on_open=on_open
)

ws.run_forever()
```

---

## SDKs and Libraries

### Official SDKs

| Language | Package | Installation |
|----------|---------|--------------|
| Python | `voicetranslate-pro` | `pip install voicetranslate-pro` |
| JavaScript | `@voicetranslate/pro` | `npm install @voicetranslate/pro` |
| Java | `voicetranslate-pro` | Maven/Gradle |
| Go | `github.com/voicetranslate/pro-go` | `go get` |

### Python SDK Example

```python
from voicetranslate_pro import VoiceTranslateClient

# Initialize client
client = VoiceTranslateClient(api_key="YOUR_API_KEY")

# Translate text
result = client.translate.text(
    text="Hello world",
    source_lang="en",
    target_lang="zh"
)
print(result.translation)

# Translate audio
result = client.translate.audio(
    audio_file="recording.wav",
    source_lang="en",
    target_lang="zh"
)
print(result.translation)

# Real-time translation
with client.translate.stream(source_lang="en", target_lang="zh") as stream:
    for audio_chunk in audio_generator():
        result = stream.send(audio_chunk)
        print(result.translation)
```

### JavaScript SDK Example

```javascript
import { VoiceTranslateClient } from '@voicetranslate/pro';

const client = new VoiceTranslateClient({ apiKey: 'YOUR_API_KEY' });

// Translate text
const result = await client.translate.text({
  text: 'Hello world',
  sourceLang: 'en',
  targetLang: 'zh'
});
console.log(result.translation);

// Real-time translation
const stream = client.translate.stream({
  sourceLang: 'en',
  targetLang: 'zh'
});

stream.on('translation', (data) => {
  console.log(data.translation);
});

// Send audio from microphone
navigator.mediaDevices.getUserMedia({ audio: true })
  .then(stream => {
    // Process audio and send to API
  });
```

---

## Changelog

### v2.1.0 (2024-01-15)

- Added batch translation endpoint
- Improved WebSocket stability
- Added voice customization options
- Enhanced error messages

### v2.0.0 (2023-12-01)

- New RESTful API design
- Added real-time streaming support
- Expanded language support to 50+ languages
- Improved translation accuracy

### v1.0.0 (2023-09-01)

- Initial API release
- Basic text and audio translation
- Support for 20 languages

---

## Support

- **Documentation**: [https://docs.voicetranslate.pro](https://docs.voicetranslate.pro)
- **Support Email**: api-support@voicetranslate.pro
- **Status Page**: [https://status.voicetranslate.pro](https://status.voicetranslate.pro)
- **Community Forum**: [https://community.voicetranslate.pro](https://community.voicetranslate.pro)
