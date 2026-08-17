"""One-off script: synthesizes the fixed opening greeting to a WAV file via
Gemini TTS, so agent.py can play it back instantly on session start instead
of asking the live model to generate it fresh every time (see agent.py's
_speak_greeting_with_retry comment for why the live-generated greeting was
unreliable - the fix here is to stop depending on it for this one fixed
sentence). Re-run manually if GREETING_TEXT or the voice changes.

    cd services/realtime_agent
    .venv/bin/python scripts/generate_greeting_audio.py
"""

import os
import wave

from google import genai
from google.genai import types

GREETING_TEXT = "Xin chào, tôi là COSA, tôi có thể giúp gì cho bạn?"
VOICE_NAME = "Puck"  # matches google_realtime.RealtimeModel(voice="Puck") in agent.py
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "greeting_vi.wav")
MODEL = "gemini-2.5-flash-preview-tts"
SAMPLE_RATE = 24000  # Gemini TTS returns 16-bit mono PCM at 24kHz


def main() -> None:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=MODEL,
        contents=GREETING_TEXT,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE_NAME)
                )
            ),
        ),
    )
    pcm_data = response.candidates[0].content.parts[0].inline_data.data

    with wave.open(OUTPUT_PATH, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_data)

    print(f"Wrote {len(pcm_data)} bytes of PCM to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
