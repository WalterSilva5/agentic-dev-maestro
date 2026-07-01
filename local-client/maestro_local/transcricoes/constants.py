"""Constantes do módulo de Transcrições (gravação + transcrição)."""

SAMPLE_RATE = 16000  # ótimo para Whisper
CHANNELS = 1

WHISPER_DEFAULT_MODEL = "small"
WHISPER_DEFAULT_LANGUAGE = "pt"
WHISPER_SUPPORTED_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
WHISPER_COMPUTE_TYPE = "int8"

# --- Modo ao vivo (assistente de reunião em tempo real) ---
# Modelo menor por padrão no ao vivo (latência); o resumo final usa o modelo
# configurado em Configurações (mais preciso).
LIVE_DEFAULT_MODEL = "base"
LIVE_WINDOW_SECONDS = 10   # tamanho da janela transcrita a cada ciclo
LIVE_MIN_SECONDS = 4       # só transcreve quando há ao menos este tanto de áudio novo
# Extração de IA ao vivo: dispara quando acumular tempo OU palavras novas.
LIVE_AI_MIN_SECONDS = 15
LIVE_AI_MIN_WORDS = 40

HOTKEY_TOGGLE_RECORDING = "<ctrl>+<shift>+r"

DEFAULT_TAGS = [
    "frontend", "backend", "devops", "design", "planning",
    "standup", "1on1", "learning", "review", "debug",
]
