"""Constantes do módulo de Transcrições (gravação + transcrição)."""

SAMPLE_RATE = 16000  # ótimo para Whisper
CHANNELS = 1

WHISPER_DEFAULT_MODEL = "small"
WHISPER_DEFAULT_LANGUAGE = "pt"
WHISPER_SUPPORTED_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
WHISPER_COMPUTE_TYPE = "int8"

HOTKEY_TOGGLE_RECORDING = "<ctrl>+<shift>+r"

DEFAULT_TAGS = [
    "frontend", "backend", "devops", "design", "planning",
    "standup", "1on1", "learning", "review", "debug",
]
