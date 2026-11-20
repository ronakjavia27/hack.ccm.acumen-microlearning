"""Voice: speech-to-text answers, text-to-speech questions, live AI viva.

Three levels, cheapest first:
    1. STT dictation  — student speaks a written answer; audio → text → normal
                        written grading. Can run in-browser (Web Speech API)
                        for free, server STT for accuracy with medical terms.
    2. TTS questions  — read stems aloud (accessibility, "audio mode" on commute).
    3. Live viva      — speech-to-speech examiner: asks, listens, follows up,
                        grades against the question rubric. Needs a persistent
                        websocket/WebRTC session → realtime service, not Vercel.

Providers are pluggable; nothing is wired yet so every call reports
`not_configured`. The interfaces fix the contract the UI codes against.
"""
from __future__ import annotations

from typing import Optional, Protocol

from . import config


class STTProvider(Protocol):
    def transcribe(self, audio: bytes, mime: str, language: str = "en", prompt: str = "") -> str: ...


class TTSProvider(Protocol):
    def synthesize(self, text: str, voice: str = "") -> bytes: ...


_STT: Optional[STTProvider] = None
_TTS: Optional[TTSProvider] = None


def register(stt: Optional[STTProvider] = None, tts: Optional[TTSProvider] = None):
    global _STT, _TTS
    _STT = stt or _STT
    _TTS = tts or _TTS


def capabilities() -> dict:
    return {
        "stt": {"server": _STT is not None, "provider": config.STT_PROVIDER or None, "browser_fallback": True},
        "tts": {"server": _TTS is not None, "provider": config.TTS_PROVIDER or None, "browser_fallback": True},
        "viva": {"realtime_service": config.REALTIME_SERVICE_URL or None,
                 "available": bool(config.REALTIME_SERVICE_URL)},
    }


# Medical vocabulary hint for STT (improves drug/organism recognition).
STT_PROMPT_HINT = ("Clinical medicine, microbiology and critical care terms: norepinephrine, vasopressin, "
                   "Pseudomonas aeruginosa, Klebsiella, carbapenem, ARDS, PEEP, FiO2, lactate, qSOFA.")


def transcribe(audio: bytes, mime: str) -> Optional[str]:
    return _STT.transcribe(audio, mime, prompt=STT_PROMPT_HINT) if _STT else None


def synthesize(text: str) -> Optional[bytes]:
    return _TTS.synthesize(text) if _TTS else None
