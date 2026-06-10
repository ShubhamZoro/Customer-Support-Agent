"""
Voice API — Speech-to-Text (Whisper) and Text-to-Speech (OpenAI TTS)
"""
import io
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

from config import settings
from models.schemas import VoiceSynthesizeRequest

router = APIRouter()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


@router.post("/api/voice/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """
    Transcribe audio to text using OpenAI Whisper.
    Accepts audio file (webm, mp3, wav, etc.) and returns transcript.
    """
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured.")

    try:
        audio_bytes = await audio.read()
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = audio.filename or "audio.webm"

        transcription = await client.audio.transcriptions.create(
            model=settings.OPENAI_STT_MODEL,
            file=(audio_file.name, audio_file, audio.content_type or "audio/webm"),
            response_format="verbose_json",
        )

        return {
            "text": transcription.text,
            "language": getattr(transcription, "language", None),
            "duration": getattr(transcription, "duration", None),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post("/api/voice/synthesize")
async def synthesize_speech(request: VoiceSynthesizeRequest):
    """
    Convert text to speech using OpenAI TTS.
    Returns audio as a streaming MP3 response.
    """
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured.")

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    # Trim to 4096 chars (TTS limit)
    text = request.text[:4096]
    voice = request.voice if request.voice in ["alloy", "echo", "fable", "onyx", "nova", "shimmer"] \
        else settings.OPENAI_TTS_VOICE

    try:
        response = await client.audio.speech.create(
            model=settings.OPENAI_TTS_MODEL,
            voice=voice,
            input=text,
            response_format="mp3",
        )

        audio_bytes = response.content

        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {str(e)}")
