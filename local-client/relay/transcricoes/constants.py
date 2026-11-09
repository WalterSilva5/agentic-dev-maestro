"""Constantes do módulo de Transcrições (gravação + transcrição)."""

SAMPLE_RATE = 16000  # ótimo para Whisper
CHANNELS = 1

WHISPER_DEFAULT_MODEL = "small"
WHISPER_DEFAULT_LANGUAGE = "pt"
WHISPER_SUPPORTED_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
WHISPER_COMPUTE_TYPE = "int8"
# RAM aproximada residente por modelo (compute_type=int8, CPU) — para orientar a
# escolha em Configurações. Valores de referência do faster-whisper/ctranslate2;
# variam um pouco por SO/plataforma, mas dão a ordem de grandeza certa.
WHISPER_MODEL_RAM_MB = {
    "tiny": 75,
    "base": 145,
    "small": 500,
    "medium": 1500,
    "large-v3": 3000,
}
# Núcleos usados pelo Whisper. O ctranslate2 usa TODOS por padrão, o que satura
# a CPU e trava a máquina durante a reunião. Deixa folga para o resto do sistema.
WHISPER_CPU_THREADS = 0  # 0 = automático (metade dos núcleos, mínimo 1)

# --- Modo ao vivo (assistente de reunião em tempo real) ---
# Modelo menor por padrão no ao vivo (latência); o resumo final usa o modelo
# configurado em Configurações (mais preciso).
LIVE_DEFAULT_MODEL = "base"
LIVE_WINDOW_SECONDS = 10   # tamanho da janela transcrita a cada ciclo
LIVE_MIN_SECONDS = 4       # só transcreve quando há ao menos este tanto de áudio novo
# Extração de IA ao vivo: dispara quando acumular tempo OU palavras novas.
LIVE_AI_MIN_SECONDS = 15
LIVE_AI_MIN_WORDS = 40
# Verificação periódica: um timer próprio garante a cadência mesmo quando a
# fala é curta/esparsa (antes dependia só do tique da gravação).
LIVE_AI_INTERVAL_MS = 5000
# Timeout curto no ao vivo: o padrão do provedor é 120s com retries, e uma
# extração que demora tanto já não serve — a reunião andou. Falhar rápido
# deixa o ciclo seguinte tentar de novo com o texto preservado.
LIVE_AI_TIMEOUT = 45

HOTKEY_TOGGLE_RECORDING = "<ctrl>+<shift>+r"

DEFAULT_TAGS = [
    "frontend", "backend", "devops", "design", "planning",
    "standup", "1on1", "learning", "review", "debug",
]
