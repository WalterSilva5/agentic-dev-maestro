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
- **Ganhos anteriores** (sessões passadas): `snapshot_since` no áudio ao vivo
  (janela de custo constante, antes copiava o buffer inteiro a cada 10s);
  `cpu_threads` do Whisper limitado à metade dos núcleos (antes saturava a CPU);
  coach sem N+1 de consultas por minuto.

## 3. A fazer (por esforço)

### Baixo risco
- **E1 — Import tardio no boot** (~1 HD): adiar imports pesados (uvicorn, libs de
  view raramente usadas) para reduzir tempo de partida e footprint parado. Medir
  antes/depois com `tracemalloc`/RSS.
- **E2 — Instanciar telas sob demanda** (~2–3 HD): criar cada view no primeiro
  acesso (lazy) em vez de todas no boot; manter a navegação e o estado. Reduz RAM
  de partida — telas pesadas (board, reuniões) só custam quando abertas.
- **E3 — Guia de tamanho de modelo** (~0,5 HD): documentar/expor o trade-off
  qualidade×RAM (`tiny`/`base`/`small`) nas Configurações; default consciente.

### Médio (estrutural)
- **E4 — Daemon headless (rota web)** (~2–3 HD): rodar captura + Whisper + API sem
  a GUI Qt carregada. É o maior ganho estrutural de memória e coincide com o
  **W3** do [Plano 11](migracao-toolkit-ui.ptbr.md): a UI leve (web/shell) separada
  do daemon pesado. Elimina o custo do Qt quando só o back é necessário.
- **E5 — Descarregar recursos por ociosidade** (~1–2 HD): estender o padrão do
  Whisper a outros caches caros (ex.: modelos/embeddings da base de conhecimento),
  liberando-os quando não usados.

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
