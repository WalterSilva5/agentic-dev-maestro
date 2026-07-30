# 12 — Plano de eficiência de recursos

> Objetivo: reduzir o consumo de memória e CPU do `local-client`. Este documento
> separa **causa real** de **percepção** ("Python pesa"), lista o que já foi
> aplicado e o que falta, com esforço em **homem-dia (HD)**. Alocação e
> cronograma são decisão de liderança.

## 1. Diagnóstico (medido no código)

A percepção de "Python para tudo" aponta para o lugar errado. O peso não vem da
linguagem de cola, e sim de **o quê** roda e **como**:

1. **Modelo Whisper residente para sempre** — `transcriber._cached_model` fica em
   memória após o primeiro uso e nunca era liberado. O default `small` int8 são
   centenas de MB parados quando não se está transcrevendo. **Maior vilão de RAM.**
   O motor é C++ (ctranslate2), não Python — trocar a linguagem da UI não muda isso.
2. **Um processo gordo só** — o app Qt sobe **Qt + FastAPI + modelo ML + threads
   + listener de atalho global** no mesmo processo. É **arquitetura, não
   linguagem**: qualquer front (Flutter/Java/web) somaria seu runtime a esse
   núcleo, que continuaria em Python por causa da captura de áudio + Whisper.
3. **Timer ocioso de 1s** — o main_window espelhava o estado de gravação na
   sidebar via um QTimer de 1s **sempre ativo**, acordando a CPU mesmo parado.
4. **Instanciação ansiosa das telas** — o main_window cria **todas** as views no
   boot, mesmo as não abertas. Custo de memória/tempo de partida.

## 2. Aplicado (concluído)

- **Liberar o Whisper quando ocioso** (`transcriber.release_model`): após ~4 min
  sem gravar/transcrever, o modelo é liberado e a RAM volta ao sistema (recarrega
  sozinho no próximo uso). Guardas `agent_service.is_busy()` / `view.is_busy()`
  garantem que nunca é liberado durante uso.
- **Widget de gravação por evento**: removido o poll de 1s; a view emite
  `recording_state_changed` ao iniciar/parar e a cada segundo gravando. Zero
  timer ocioso para isso.
- **E1 + E2 — Import tardio + telas sob demanda**: as 9 telas do hub
  "Ferramentas" pouco acessadas (vault, library, apitester, kb, memory, english,
  translate, skills, guide) viraram **fábricas** (`MainWindow._lazy_factory`) em
  vez de instâncias — só são importadas/construídas no primeiro `_open_key`.
  Nenhuma tinha referência externa a `main_window.py`, então adiar foi seguro
  (confirmado por grep e por teste offscreen: stack tem 9 widgets no boot,
  cresce 1 a cada tela nova aberta, sem duplicar ao reabrir). **Medido**: RSS de
  boot caiu de ~174,2 MB para ~160,2 MB (**~14 MB, ~8%**), estável em 3
  execuções — método em `medir_rss()` abaixo.
- **E3 — Guia de tamanho de modelo**: Configurações mostra a RAM aproximada do
  modelo Whisper selecionado (`WHISPER_MODEL_RAM_MB`), atualizando ao trocar —
  de ~75 MB (tiny) a ~3 GB (large-v3). Ajuda a escolher conscientemente.
- **E4 — Achado**: a rota `webmain` (API + web UI, sem GUI) **já não carrega
  Qt** — confirmado (`grep PySide6` vazio em `api/`, `webmain.py`). O daemon
  headless para o resto do app já existe; falta só **Reuniões**, cujos workers
  usam `QThread` (`transcricoes/agent_service.py`, `live_assistant.py`,
  `transcriber.py`) — depende do WebSocket ao vivo (E2/E3 do
  [Plano 11](migracao-toolkit-ui.ptbr.md)), não resolvido aqui.
- **E5 — Achado**: nenhum outro cache de modelo local pesado além do Whisper.
  Os embeddings da base de conhecimento (`memory.py`) vão por API HTTP
  (OpenAI-compat), não há modelo local residente a liberar.

## 3. A fazer (por esforço)

- **E4 (restante) — Reuniões sem QThread** (~2–3 HD, dentro do W1/W2 do Plano
  11): mover a captura/transcrição/estado ao vivo para rodar sem depender do
  loop de eventos Qt, permitindo Reuniões no daemon `webmain` headless.

## 4. Onde a eficiência NÃO está

- **Trocar a linguagem da UI** (Flutter/Java): não reduz o núcleo pesado
  (Whisper/áudio segue em Python nativo) e **soma** o runtime do novo toolkit.
  A eficiência vem de **arquitetura** (separar daemon/UI, liberar recursos
  ociosos, gatear timers), não de reescrever a interface.
- **Micro-otimizar Python de cola**: o tempo/memória está no ML e no Qt, não nos
  laços de aplicação.

## 5. Métrica de acompanhamento

Antes de cada item, registrar **RSS ocioso** (app aberto, sem gravar) e **RSS de
pico** (durante transcrição), além do **tempo de boot**. Comparar após a mudança.
Sem medida, não há ganho comprovado.

Método usado para E1+E2 (repetível): construir `MainWindow` offscreen
(`QT_QPA_PLATFORM=offscreen`) num processo novo, com banco temporário isolado, e
ler `resource.getrusage(RUSAGE_SELF).ru_maxrss` logo após `processEvents()`.
Rodar 3× para checar estabilidade.

> **Cuidado de isolamento**: `SettingsView`/`_save_settings` grava em
> `~/.maestro-local/config.json` — um arquivo **real do usuário**, fora do banco
> SQLite temporário. Um script de verificação manual durante o desenvolvimento
> deste plano interagiu com o combo do modelo Whisper e **sobrescreveu essa
> configuração de verdade** (detectado pelo mtime do arquivo, corrigido de volta
> ao default `small`). A fixture `temp_db` em `tests/conftest.py` agora isola
> `config.json` também (`monkeypatch` em `config._CONFIG_FILE`); scripts de
> verificação manual (fora do pytest) devem fazer o mesmo antes de simular
> interação de UI que salve configurações.
