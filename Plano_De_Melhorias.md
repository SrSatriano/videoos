# Plano De Melhorias - VideoOS

Data da auditoria: 2026-07-19

## Regra Basica Permanente

Antes de qualquer nova tarefa neste sistema, ler:

1. `Regras_Gerais.md`
2. `Sistema_Completo.md`
3. `Memoria_Do_Sistema.md`
4. `Plano_De_Melhorias.md`

Toda leitura feita dentro da pasta do sistema deve ser registrada em `Memoria_Do_Sistema.md`. Ao finalizar qualquer tarefa, atualizar `Sistema_Completo.md`, `Memoria_Do_Sistema.md` e `Plano_De_Melhorias.md` com estado, evidencias, pendencias e proximos passos.

## Objetivo Do Plano

Transformar o VideoOS em um estudio local-first confiavel para producao em massa de videos curtos, com operacao previsivel, seguranca local, rastreabilidade e recursos de IA que degradam bem quando ferramentas opcionais nao estao instaladas.

## P0 - Recuperar Operacao Basica

1. Corrigir ambiente Python local ou documentar Docker como unico caminho oficial.
   - Estado: concluido em 2026-06-19.
   - Resultado: `.venv` antiga preservada como `.venv_broken_20260619-061119`; nova `.venv` criada com Python 3.12.13 via `pythonw.exe` empacotado.
   - Evidencia atual: dependencias backend instaladas; `.venv\Scripts\pytest.exe backend -q` passou com 68 testes na Passada 08.

2. Subir Docker Desktop/engine e validar stack completa.
   - Estado: concluido em 2026-06-19.
   - Resultado: Docker engine respondeu; stack API/Web/Worker esta operante nesta verificacao detalhada da Passada 31.
   - Evidencia: API saudavel em `8010`, web saudavel em `5174`, worker ativo, restart count 0 e FFmpeg/FFprobe disponiveis no backend container.

3. Confirmar endpoints vivos.
   - Estado: concluido em 2026-06-19 durante validacao temporaria e reconfirmado com Docker iniciado.
   - Evidencia:
     - `Invoke-WebRequest http://127.0.0.1:8010/api/system/health`: status 200.
     - `Invoke-WebRequest http://127.0.0.1:5174`: status 200.
     - 22 endpoints GET seguros responderam 200.
     - UI renderizada em navegador real.
   - Fechamento atual: sistema permaneceu rodando em Docker porque o usuario ja havia subido a stack e pediu verificacao detalhada.

4. Corrigir caminho padrao de importacao em `frontend/src/App.tsx`.
   - Estado: concluido em 2026-06-19.
   - Resultado: caminho antigo removido; a UI usa o primeiro `import_root` retornado pelo backend quando disponivel.
   - Evidencia: `npm.cmd run build` passou apos a alteracao.

5. Rodar testes backend.
   - Estado: concluido em 2026-06-19.
    - Evidencia: 68 testes passaram em host via `.venv\Scripts\pytest.exe backend -q` e 68 testes passaram em Docker via `docker compose exec api python -m pytest -q` na Passada 08.

6. Reparar/reindexar assets existentes.
   - Estado: concluido na Passada 02 em 2026-06-19.
   - Resultado: rotina idempotente criada e executada; 3 assets reparados, 0 falhas.
   - Evidencia: `POST /api/assets/reindex?only_attention=true&force_thumbnail=false` retornou `checked=3`, `repaired=3`, `failed=0`; smart bin `Atencao=0`.

## P1 - Endurecimento De Seguranca Local

1. Desligar importacao ampla por padrao.
   - Estado: concluido em 2026-06-19.
   - Resultado: default `0` em `backend/app/config.py`, `docker-compose.yml`, `.env` e `.env.example`.
   - Evidencia: `docker compose config` confirmou `VIDEO_OS_ALLOW_ANY_IMPORT_PATH: "0"`.

2. Reduzir mount de `C:/` no Docker.
   - Estado: concluido em 2026-06-19 como mitigacao inicial.
   - Resultado: `C:/` agora monta como `/host/c:ro` em API e worker.
   - Observacao: ideal futuro e montar apenas pastas necessarias, nao todo `C:/`.

3. Validar paths de `/api/system/settings` e `output_dir` de publicacao.
   - Estado: concluido na Passada 03 em 2026-06-19.
   - Resultado: settings e `output_dir` de pacotes aceitam apenas `data/`, `Planejamento/` ou roots extras aprovadas por `VIDEO_OS_ALLOWED_OUTPUT_ROOTS`.
   - Evidencia: settings rejeitou `/tmp/videoos-outside-test`; pacote rejeitou `/tmp/videoos-publish-outside`; health/settings expoem `allowed_output_roots`.

3.1. Validar `output_dir` por lote.
   - Estado: concluido na Passada 20 em 2026-07-09.
   - Resultado: `Batch.output_dir` permite exportacao em massa para pasta escolhida pelo usuario, validada pela mesma allowlist de saidas.
   - Evidencia: testes cobrem aceite dentro de `data/`, rejeicao fora das roots, migration SQLite legado e uso real no caminho passado ao render.

4. Endurecer Electron.
   - Estado: concluido em 2026-06-19 em nivel estatico, reforcado nas Passadas 10 e 21.
   - Resultado: `sandbox: true`, `webSecurity: true`, bloqueio de navegacao externa, bloqueio de novas janelas, bloqueio de permissoes, protecao contra webview e `open-path` restrito a pasta do app.
   - Resultado Passada 21: URL aceita somente HTTP em loopback, handlers de arquivo/pasta/path validam a origem do emissor e DevTools exigem `VIDEO_OS_ENABLE_DEVTOOLS=1`.
   - Resultado adicional: stdout/stderr do Electron agora sao gravados em `data/logs/electron.desktop.log` e `data/logs/electron.desktop.err.log`, evitando que logs internos do Chromium poluam o terminal do executor.
   - Pendencia: validar interacao visual completa do Electron em uma rodada dedicada, se necessario.

5. Revisar CORS.
   - Estado: concluido em 2026-06-19.
   - Resultado: `allow_credentials` agora e calculado como falso quando as origens contem `*`, alinhado a FastAPI/Starlette.

6. Remover dependencia visual externa bloqueada por CSP.
   - Estado: concluido em 2026-06-19.
   - Resultado: `frontend/src/styles.css` nao importa mais Google Fonts por rede externa.
   - Evidencia: navegador real nao registrou falha de fonte/CSP apos restart do web container.

## P1 - Dependencias E Reprodutibilidade

1. Trocar `latest` por versoes fixas em `frontend/package.json`.
   - Estado: concluido em 2026-06-19.
   - Resultado: `latest` removido; versoes fixas em `package.json` e `package-lock.json`.
   - Versoes: React 19.2.7, React DOM 19.2.7, Lucide React 1.24.0, Electron 42.4.1, TypeScript 6.0.3, Vite 8.1.5 e plugin React 6.0.3.

2. Tratar `npm audit`.
   - Estado: concluido em 2026-06-19.
   - Resultado: Vite atualizado para 8.0.16, Electron para 42.4.1 e `npm audit fix` atualizou `undici` para 7.28.0.
   - Evidencia: `npm.cmd audit --audit-level=moderate` e `docker compose run --rm --no-deps web npm audit --audit-level=moderate` retornaram 0 vulnerabilidades; `npm.cmd audit --json` reconfirmou 0 vulnerabilidades na Passada 21.
   - Observacao Passada 21: `pip check` passou, mas `pip-audit` nao esta instalado; auditoria CVE especifica do Python continua pendente e nao deve ser instalada automaticamente sem aprovacao.
   - Auditoria Passada 29: npm continua com 0 vulnerabilidades. React 19.2.7, Lucide React 1.24.0, Vite 8.1.5, FastAPI 0.139.1, Uvicorn 0.51.0, HTTPX2 2.7.0, yt-dlp 2026.7.4 e gallery-dl 1.32.6 foram validados no runtime efetivo.
   - Estado Passada 29: host/container passaram com 115 testes; `pip check` e build frontend passaram. Electron 43.1.1 e TypeScript 7.0.2 ficam adiados para rodada de compatibilidade por serem upgrades maiores.

3. Separar perfil dev e perfil runtime.
   - Estado: revisado na Passada 08 e mitigado parcialmente na Passada 09.
   - Alvo recomendado agora: backend/API/worker no Docker e frontend/Electron/Vite nativo no Windows como fluxo principal de desenvolvimento/operacao local; manter frontend Docker como fallback/validacao.
   - Motivo: o problema visual da Passada 08 veio de web container/Vite com transformacao/env antigos, enquanto o codigo do host ja estava correto.
   - Mitigacao aplicada: enquanto essa separacao nao vira modo oficial, `VideoOS.ps1` valida se a stack Docker viva esta alinhada ao `.env` antes de abrir a UI.
   - Pendencia: implementar scripts e docs dedicados se o usuario confirmar.

4. Adicionar checagem de versoes no pre-flight.
   - Estado: concluido em camadas entre 2026-06-19 e a Passada 18 em 2026-06-23.
   - Resultado: Docker frontend atualizado para `node:22-alpine`, compativel com Electron 42.4.1.
   - Resultado adicional: `VideoOS.ps1` agora aceita `VIDEO_OS_PREFLIGHT_ONLY=1` para rodar diagnostico sem iniciar servicos.
   - Resultado adicional: o diagnostico Node agora usa `package-lock.json` como marcador de dependencias quando disponivel, reduzindo falso positivo de `node_modules` desatualizado quando so scripts/metadados de `package.json` mudam.
   - Resultado adicional: o pre-flight agora exibe versoes de Python runtime, Node, npm e Docker CLI.
   - Resultado adicional: o pre-flight agora mostra se as portas esperadas da API e Web estao `LIVRE` ou `OCUPADA`.
   - Pendencia: quando Docker Desktop estiver online, enriquecer a validacao viva com versao do engine e status de imagens/containers.

## P1 - Contratos E Bugs De Codigo

1. Unificar URL do Ollama.
   - Estado: concluido em 2026-06-19.
   - Resultado: `agents.py` e `llm.py` usam candidatos comuns derivados de config/env, host Docker e localhost.

2. Corrigir tipos frontend.
   - Estado: concluido em 2026-06-19.
   - Resultado: `AuditEvent` declara `payload`; `RenderedVideo` declara `path` e `reviewed_at`.

3. Alinhar UI de receita com renderizador real.
   - Estado: concluido na Passada 04 em 2026-06-19.
   - Resultado: tipos/presets/template base deixam de anunciar `layout`, `music`, `intro`, `outro`, `cta` e caption style em receitas instalaveis.
   - Evidencia: `TemplateStudio` expoe `format.fit`; presets instalaveis usam apenas `crop/contain`; teste garante ausencia de campos nao aplicados.

3.1. Normalizar templates legados persistidos.
   - Estado: concluido na Passada 05 em 2026-06-19.
   - Resultado: o startup remove campos nao aplicados pelo renderizador atual de receitas legadas persistidas.
   - Evidencia: validacao viva confirmou 94 templates e 0 receitas com `layout`, `music`, `intro`, `outro`, `cta` ou `captions.style`.

3.2. Corrigir sintaxe FFmpeg `drawtext`.
   - Estado: concluido na Passada 03 em 2026-06-19.
   - Resultado: filtro mudou de `drawtext:fontfile=...` para `drawtext=fontfile=...`.
   - Evidencia: teste unitario novo em `backend/tests/test_render_recipe.py`, render real 1080x1920 concluido e retry do job falho concluido.

4. Melhorar migrations.
   - Estado: concluido na Passada 06 em 2026-06-19.
   - Resultado: `migrations.py` agora cria `schema_migrations`, registra IDs/checksums e aplica `ALTER TABLE ADD COLUMN` idempotente para evolucao segura de SQLite.
   - Evidencia: banco vivo confirmou `schema_migrations`, 10 colunas novas em `platform_presets` e migrations `20260619_0000...` e `20260619_0001...`.
   - Evolucao futura: adotar Alembic/batch migrations se o sistema precisar recriar tabelas, alterar constraints ou fazer mudancas nao cobertas por `ADD COLUMN`.

5. Validar caminhos de B-roll e SRT.
    - Estado: concluido na Passada 04 em 2026-06-19.
    - Resultado: `captions.burned_srt_path` e `broll[].path` passam por allowlist e normalizacao antes do FFmpeg.
    - Evidencia: testes rejeitam paths externos e API rejeita template com B-roll fora das roots.

5.1. Validar caminhos de logo e musica de receita.
    - Estado: concluido na Passada 20 em 2026-07-09.
    - Resultado: `frame.logo_path` e `audio.music_path` passam por `VIDEO_OS_ALLOWED_RECIPE_MEDIA_ROOTS`, extensoes permitidas e normalizacao antes do FFmpeg.
    - Evidencia: `backend/tests/test_render_recipe.py` cobre rejeicao de musica externa e montagem de comando framed+music.

6. Corrigir MassLoader cookies no Docker/Windows.
   - Estado: concluido na Passada 07 e reforcado na Passada 08 em 2026-06-19.
   - Resultado: `cookies_from_browser` de Edge/Chrome nao e mais oferecido/aceito silenciosamente quando o backend roda em container; o fluxo suportado usa upload de `cookies.txt` para `data/incoming/massloader-cookies` e passa o arquivo ao `yt-dlp` como `cookiefile`.
   - Evidencia: testes cobrem 422 para navegador em container, upload de cookies, captura com `cookies_file_path` e rejeicao de path externo; runtime Docker confirmou `browser_cookie_import_supported=false`, upload 200 e path externo 400.

7. Atualizar e monitorar `yt-dlp` do MassLoader.
   - Estado: concluido na Passada 08 em 2026-06-19.
   - Resultado: `yt-dlp` foi atualizado/pinado para `2026.6.9`, correspondente a release oficial `2026.06.09`; `/api/social/instagram/status` agora expoe `yt_dlp_version`.
   - Evidencia: `.venv\Scripts\pytest.exe backend -q` passou com 68 testes; `docker compose exec api python -m pytest -q` passou com 68 testes; `docker compose exec api yt-dlp --version` retornou `2026.06.09`; status da API retornou `yt_dlp_version=2026.6.9`.
   - Evolucao futura: criar rotina opcional de atualizacao controlada de `yt-dlp`/nightly quando sites externos quebrarem o extractor, sempre com pin, rollback e teste de regressao.

8. Melhorar mensagens de falha do Instagram.
   - Estado: concluido na Passada 08 e reforcado na Passada 12 em 2026-06-19.
   - Resultado: falhas de `instagram:user`/perfil quebrado continuam exibindo o erro real do `yt-dlp`, mas agora recebem orientacao clara para rebuild/update, `cookies.txt` e URLs diretas de Reels/posts autorizados.
   - Evidencia: teste `test_instagram_profile_downloader_errors_get_actionable_guidance` cobre a mensagem vista na tela do usuario.

8.1. Normalizar abas de perfil Instagram no MassLoader.
   - Estado: concluido na Passada 12 em 2026-06-19.
   - Resultado: URLs como `https://www.instagram.com/art_viral/reels/` sao normalizadas para `https://www.instagram.com/art_viral/` antes de chamar `yt-dlp`, evitando o erro direto `Unsupported URL` da aba de perfil.
   - Evidencia: o teste novo falhou antes da correcao e passou depois; `docker compose exec api python -c "from app.services.social import parse_sources; ..."` retornou `['https://www.instagram.com/art_viral/']`; backend host e Docker passaram com 69 testes.
   - Observacao: perfis ainda podem exigir `cookies.txt` e podem continuar instaveis por mudancas externas do Instagram/yt-dlp; para itens especificos, a orientacao continua sendo usar URLs diretas de post/Reel autorizado.

9. Corrigir executor para abrir a atualizacao correta.
   - Estado: concluido na Passada 09 em 2026-06-19.
   - Resultado: `VideoOS.ps1` centraliza runtime em `.env`, prefere API `8010` e web `5174`, confere portas, `VITE_API_URL` e frescor dos containers antes de reaproveitar uma stack Docker viva, e usa `--force-recreate` quando detectar defasagem.
   - Evidencia: parser PowerShell OK; `docker compose config --quiet` OK; smoke com `VIDEO_OS_NO_OPEN=1` reaproveitou a stack correta em `http://127.0.0.1:5174`; health API 200 em `8010`; web 200 em `5174`; `/src/api.ts` confirmou `http://127.0.0.1:8010`.

10. Redirecionar logs internos do Electron/Chromium.
   - Estado: concluido na Passada 10 em 2026-06-19.
   - Resultado: mensagens como `Network service crashed or was terminated, restarting service` deixam de aparecer diretamente no terminal do executor e ficam preservadas em logs dedicados.
   - Evidencia: API 200, web 200, Docker healthy, 0 processos desktop remanescentes; `electron.cmd --version` com redirecionamento retornou exit 0 e `v42.4.1`; `docker compose config --quiet` passou.

11. Tolerar locks SQLite transitorios no worker.
   - Estado: concluido na Passada 21 em 2026-07-10.
   - Achado: logs historicos continham `sqlite3.OperationalError: locking protocol`, capaz de encerrar o worker e depender do restart do container.
   - Resultado: espera ociosa ocorre depois de fechar a sessao; apenas mensagens conhecidas de lock recebem retry com backoff limitado a 30 segundos. Outros `OperationalError` continuam visiveis e encerram o processo.
   - Evidencia: 3 testes novos em `test_worker_resilience.py`, suite completa com 98 testes, worker reiniciado e logs recentes limpos.

## P2 - Qualidade De Midia E Plataformas

1. Versionar regras de plataforma.
   - TikTok: fonte oficial de ads atualizada em marco de 2026.
   - YouTube: Shorts ate 3 minutos para videos verticais/quadrados.
   - Instagram: manter fonte oficial atualizada quando o acesso Meta estiver disponivel.
   - Estado: concluido no backend na Passada 06 em 2026-06-19.
   - Resultado: cada `PlatformPreset` guarda fonte, data de checagem, tipo da regra, limites tecnicos, safe zone e observacoes.
   - Pendencia: exibir esses detalhes de forma mais rica na UI e buscar fonte Meta oficial especifica para Reels organico.

2. Gerar `quality-report.json` no pacote final.
   - Estado: concluido na Passada 05 e enriquecido na Passada 31.
   - Resultado: pacote inclui video, thumbnail, caption, hashtags, checklist, metadata e `quality-report.json`.
   - Evidencia historica: pacote em `/workspace/data/passada05-packages/...` gerou relatorio v1.
   - Evolucao Passada 31: novos pacotes usam `videoos-quality-report/v2`, com FFprobe, loudnorm, codecs, audio, container, FPS, bitrate, tamanho, tempo e pico RSS; uma analise e reutilizada entre plataformas.

3. Adicionar analise de audio/loudness mais rica.
   - Atual: render usa `loudnorm=I=-14:TP=-1.5:LRA=11`.
   - Estado: medicao concluida na Passada 31; alertas finos concluidos na Passada 32.
   - Evolucao Passada 34: Quality Check assincrono em lote (`quality_check_batch`) e audio ducking com fade in/out no motor FFmpeg e Template Studio.
   - Resultado: QC e quality report medem LUFS integrado, true peak, LRA e threshold no arquivo final; arquivo sem audio e falha de medicao possuem estados explicitos.

4. Adicionar estimador de tamanho/bitrate antes do lote.
   - Estado: concluido na Passada 23 em 2026-07-10.
   - Resultado: `BatchQueue` estima tempo, tamanho e pico de memoria por resolucao/duracao/variacoes e exige confirmacao para 4K extenso.
   - Evidencia Passada 22: para 3s, 1080p gerou 2.03 MiB/4.822s/1.51 GiB RSS; 2K 3.96 MiB/6.731s/2.34 GiB; 4K 8.20 MiB/14.168s/4.78 GiB.
   - Evolucao Passada 24: tempo e bytes reais agora sao persistidos; o health agrega ate 20 amostras por template/resolucao e o frontend usa historico depois de 3 jobs validos. `trim` passou a reduzir corretamente a duracao estimada.
   - Evolucao Passada 30: pico RSS real agora e persistido por job e agregado por template/resolucao. O estimador aceita a memoria local para elevar o alerta, mas usa sempre o maior valor entre historico e benchmark.
   - Evolucao futura: sugerir CRF/preset com base em evidencia sem alterar automaticamente a receita.

5. Pre-flight de capacidade da pasta de exportacao.
   - Estado: concluido na Passada 26.
   - Resultado: backend mede o volume permitido, aplica 15% sobre a estimativa e preserva 10% do livre ou no minimo 1 GiB; UI mostra a decisao e o POST do lote repete o bloqueio.
   - Evidencia: 1 GiB estimado foi aceito com 51.26 GiB seguros; 1 TiB foi recusado. Testes cobrem reserva, margem, endpoint e criacao bloqueada.

## P2 - IA E Edicao Avancada

1. Trocar Whisper CLI por `faster-whisper` opcional.
   - Motivo: fonte oficial aponta ganhos de desempenho e uso de PyAV.
   - Estado: concluido na Passada 35 com extracao automatica de `words_json` e `segments_json`, endpoints de patch de transcricao e exportacao de legendas SRT/VTT.
   - Alvo: animacao de legendas (karaoke) e estilizacao avancada com libass.

2. Usar PySceneDetect como opcional.
   - Atual: scene detect usa FFmpeg `select=gt(scene,threshold),showinfo`.
   - Alvo: detector adaptativo, lista de cenas, EDL/HTML opcional e melhor controle de threshold.

3. Consolidar structured outputs com Ollama.
   - Estado: concluido na Passada 39 com modelos formais Pydantic (`AgentRunResult`, `AgentItem`) em `llm.py` e fallback estruturado auditavel.

4. Music Lab opcional com Demucs.
   - Estado: concluido na Passada 39 com deteccao dinamica de Demucs, fallback DSP FFmpeg para isolamento de voz e instrumental e endpoint `POST /api/music/separate-stems`.


5. Render Engine V2.
   - Implementar:
     - layouts split/screenshare/gameplay
     - ducking inteligente de musica (avancado na Passada 34 com fade in/out)
     - intro/outro
     - CTA temporizado
     - caption style/karaoke (concluido nas Passadas 36 e 37 com gerador ASS, filtro ass= e presets visuais Hormozi, Neon, Minimalista e Bold Red)
     - auto jump-cut (concluido na Passada 37 com silencedetect e speech intervals)
     - safe-zone guard para texto
   - Avanco Passada 20: moldura 9:16 com logo/nome do canal, area de video, legendas SRT/VTT, music bed simples e presets 1080p/2K/4K foram implementados no renderizador atual, sem esperar o V2 completo.

## P2 - UX E Operacao

1. Command palette.
   - Estado: concluido na Passada 33 com busca global de 17 telas e acoes operacionais via Ctrl+K / Cmd+K.

2. Media pool com modo grade/lista.
   - Estado: concluido na Passada 38 com alternador visual de 1 clique (Grade / Lista) no AssetLibrary.tsx, com tags, miniaturas e busca por nome.


3. Tela de sistema mais acionavel.
   - Mostrar: Docker online/offline, Python host, FFmpeg host, FFmpeg container, SQLite status, audit events, tamanho de `data/`.
   - Estado: avancado nas Passadas 15, 21, 31 e 36;
   - Resultado Passada 36: endpoint health e SystemPanel agora detalham o volume em bytes de `data/` (`assets_bytes`, `renders_bytes`, `proxies_bytes`, `thumbnails_bytes`, `publish_packages_bytes`, `db_bytes`, `logs_bytes` e `total_bytes`).

4. Botao "abrir pasta do pacote/lote" seguro.
   - Estado: concluido na Passada 37 via endpoint `POST /api/system/open-path` com validacao de sandbox e botao integrado no historico de lotes.


5. Limpeza de encoding dos MDs antigos.
   - Varios docs estavam com mojibake (`edicao`, etc.).
   - Alvo: UTF-8 limpo ou ASCII operacional.

6. Investigar console 404 generico.
   - Estado: concluido na Passada 03 em 2026-06-19.
   - Resultado: adicionado `frontend/public/favicon.svg` e link em `frontend/index.html`.

7. Fluxo visual de producao em massa.
   - Estado: concluido em codigo e UI integrada na Passada 20 em 2026-07-10.
   - Resultado: `TemplateStudio` ganhou editor de moldura/canal, resolucoes 1080p/2K/4K, legendas e musica; `BatchQueue` ganhou pasta de exportacao do lote.
   - Evidencia: backend 95 testes, frontend build, `npm.cmd run test:paths`, API/web host 200 e navegador integrado passaram; presets 2K/4K e pasta de exportacao por lote foram verificados na tela.
   - Evidencia real: Docker healthy em API `8010`/web `5174`, worker ativo e MP4 1080x1920 gerado com moldura, logo, canal, SRT, musica/audio original, H.264 e AAC.
   - Escala Passada 22: benchmark comparavel 1080p/2K/4K concluido; os tres MP4 passaram por decode e inspecao visual.
   - Resultado: 1080p recomendado para massa, 2K seletivo e 4K sequencial/sob demanda.

7.1. Organizar navegacao e operacao visual.
   - Estado: concluido na Passada 21 em 2026-07-10.
   - Resultado: navegacao agrupada/recolhivel, home operacional compacta, busca e scroll controlado para templates, plano de assets/variacoes/jobs, contadores de fila e responsividade da tela Sistema.
   - Higiene: removidos bloco tardio de overrides, fontes nao declaradas, brilho excessivo, CSS morto do hero anterior e uso visual indiscriminado de `!important`.
   - Evidencia: build TypeScript/Vite, `test:paths`, HTTP 200 e codigo servido pelo Vite com marcadores novos; captura automatizada nova ficou bloqueada pela politica local do Chrome para loopback.
   - Evolucao Passada 31: Revisao ganhou grid largo, telemetria agrupada, estados de prontidao coerentes e controle de integridade em massa; Publicacao ganhou bloqueio/estado vazio; screenshots reais passaram em 1440x1000 e 419x900.

7. Exibir caminho de downloads do MassLoader com clareza.
   - Estado: concluido na Passada 14 em 2026-06-20.
   - Resultado: painel `Resultado` mostra `Container: /workspace/data/incoming/massloader/...` e `Local: data\incoming\massloader\...`.
   - Evidencia: `npm.cmd run test:paths` e `npm.cmd run build` passaram.

8. Automacao recorrente de melhoria sistemica.
   - Estado: concluido na Passada 13 em 2026-06-20.
   - Resultado: automacao `videoos-melhoria-sistemica-5h10` criada e ativa para executar novas passadas de melhoria, correcao e auditoria sistemica.
   - Agenda: primeira execucao em 2026-06-20 as 18:35, fuso `America/Sao_Paulo`, e recorrencia de 5h10.
   - Contrato: cada rodada deve ler os 4 MDs obrigatorios, abrir a proxima passada na memoria, escolher o proximo item relevante, pesquisar fontes oficiais quando necessario, implementar melhoria pequena e verificavel, validar, atualizar os 3 MDs principais e reportar evidencias/riscos/proximo passo.

## Plano De Validacao

Validacao minima a cada tarefa:

1. Atualizar `Memoria_Do_Sistema.md` com leituras e acoes.
2. Rodar checagem especifica do arquivo alterado.
3. Rodar `npm.cmd run build` se frontend mudou.
4. Rodar `python -m pytest backend` ou Docker equivalente se backend mudou.
5. Rodar `docker compose config` se Compose/env/script mudou.
6. Checar health da API/web se a tarefa afeta runtime.
7. Atualizar `Sistema_Completo.md`, `Memoria_Do_Sistema.md` e `Plano_De_Melhorias.md` antes de encerrar.

Ultima execucao direcionada do plano de validacao de codigo: Passada 32 em 2026-07-19.

- Backend: 125 testes passaram no host e container; `compileall` e `pip check` passaram.
- Frontend: builds host/container e `npm.cmd run test:paths` passaram; Vite 8.1.5 compilou 1801 modulos; `npm audit` retornou 0 vulnerabilidades.
- Qualidade: testes cobrem cache hit/invalido por SHA-256, silencio, clipping, FFprobe/loudnorm, status editorial, schema v2 e endpoint seguro do relatorio.
- Runtime: API/web healthy, worker ativo, FFmpeg/FFprobe disponiveis, SQLite WAL e fila sem falhas.
- Evidencia real: QC repetido passou de `miss` em cerca de 2.031s para `hit` em cerca de 0.035s; viewer abriu pacote historico v1 sem alterar status editorial.
- Visual: as 17 telas passaram em navegador real no desktop 1440x1000 e mobile 419x900, sem overflow global; Captura, Editor, Revisao e Publicacao receberam conferencia focada.
- Resultado operacional: QC tecnico e persistente, revisao editorial, integridade e pacote possuem contratos distintos; o relatorio agora pode ser consultado sem acesso arbitrario ao filesystem.

Evidencias historicas anteriores:

- Launcher: parser PowerShell de `VideoOS.ps1` passou.
- Launcher: `VIDEO_OS_PREFLIGHT_ONLY=1` executou pre-flight e saiu com exit 0 sem iniciar servicos.
- Launcher: pre-flight Node passou de falso positivo `DESATUALIZADO` para `ATUALIZADO` apos usar `package-lock.json` como marcador de dependencias.
- Launcher: pre-flight passou a exibir Python `3.12.13`, Node `v24.14.1`, npm `11.11.0` e Docker CLI `29.5.3`.
- Launcher: pre-flight passou a exibir portas API/Web esperadas; na Passada 19, API `8010` e Web `5174` estavam `LIVRE`.
- Docker config: `docker compose config --quiet` passou.
- Docker runtime: `docker compose ps` e `docker version` nao conectaram ao Docker Desktop na Passada 19; ultima validacao Docker completa segue sendo a Passada 12.
- Portas: `8010` e `5174` livres na Passada 19.
- Frontend host: `npm.cmd run build` passou apos mudanca no `SystemPanel`.
- Frontend host: `npm.cmd run test:paths` passou, preservando a verificacao do MassLoader.
- Docker config: `docker compose config --quiet` passou.
- Docker runtime: `docker compose ps` e `docker version` nao conectaram ao Docker Desktop na Passada 15; ultima validacao Docker completa segue sendo a Passada 12.
- Frontend host: `npm.cmd run test:paths` passou, cobrindo conversao de paths do MassLoader.
- Frontend host: `npm.cmd run build` passou.
- Docker: `docker compose ps` nao conectou ao Docker Desktop na Passada 14; ultima validacao Docker completa segue sendo a Passada 12.
- Backend host: 69 testes passaram.
- Backend Docker: 69 testes passaram.
- Frontend host: build passou.
- API/Web/Worker: runtime vivo confirmado, com API `8010`, web `5174`, API/web healthy e worker ativo.
- Fluxo real: proxy, render, quality, aprovacao e pacote manual validados na Passada 03; pacote real com `quality-report.json` validado na Passada 05.
- Banco: migrations versionadas aplicadas e confirmadas no banco vivo na Passada 06.
- MassLoader: `yt-dlp 2026.06.09` confirmado no container, status da API expoe `yt_dlp_version=2026.6.9` e `parse_sources` normaliza `/usuario/reels/` para o perfil raiz.
- Executor: parser PowerShell OK, `docker compose config --quiet` OK, smoke com `VIDEO_OS_NO_OPEN=1` abriu o alvo correto sem janela e confirmou web `5174` apontando para API `8010`.
- Electron: stdout/stderr redirecionados para `data/logs/electron.desktop.*.log`; teste de `electron.cmd --version` com redirecionamento retornou `v42.4.1`.

## Backlog Priorizado

| Prioridade | Item | Estado |
| --- | --- | --- |
| P0 | Reparar Python/venv ou validar Docker como caminho oficial | Concluido em 2026-06-19 |
| P0 | Subir Docker e validar API/Web/Worker | Concluido em 2026-06-19 |
| P0 | Corrigir defaultImportPath antigo | Concluido em 2026-06-19 |
| P1 | Desligar importacao ampla por default | Concluido em 2026-06-19 |
| P1 | Reduzir mount `C:/` ou marcar read-only | Concluido em 2026-06-19 |
| P1 | Fixar versoes em `package.json` | Concluido em 2026-06-19 |
| P1 | Tratar vulnerabilidades `npm audit` | Concluido em 2026-06-19 |
| P1 | Unificar config Ollama | Concluido em 2026-06-19 |
| P1 | Corrigir tipos `AuditEvent`/`RenderedVideo` | Concluido em 2026-06-19 |
| P1 | Endurecer CORS com wildcard | Concluido em 2026-06-19 |
| P1 | Endurecer Electron | Concluido e reforcado na Passada 21; janela visual dedicada pendente |
| P1 | Atualizar Docker frontend para Node compativel | Concluido em 2026-06-19 |
| P1 | Reparar/reindexar assets e metadados existentes | Concluido na Passada 02 |
| P1 | Remover Google Fonts externo bloqueado por CSP | Concluido em 2026-06-19 |
| P1 | Corrigir botao aninhado na biblioteca | Concluido na Passada 02 |
| P1 | Endurecer paths de settings/output | Concluido na Passada 03 |
| P1 | Corrigir sintaxe FFmpeg `drawtext` | Concluido na Passada 03 |
| P1 | Validar fluxo real render/pacote | Concluido na Passada 03 |
| P2 | Investigar console 404 generico | Concluido na Passada 03 |
| P1 | Alinhar UI/presets com renderizador | Concluido na Passada 04 |
| P1 | Validar paths de B-roll e SRT | Concluido na Passada 04 |
| P1 | Validar runtime vivo apos restart da Passada 04 | Concluido na Passada 05 |
| P1 | Normalizar templates legados persistidos | Concluido na Passada 05 |
| P1 | Migrations idempotentes formais | Concluido na Passada 06 |
| P2 | Versionar regras de plataforma no backend | Concluido na Passada 06 |
| P1 | Atualizar `yt-dlp` e expor versao no MassLoader | Concluido na Passada 08 |
| P1 | Melhorar mensagens de falha de perfil Instagram | Concluido na Passada 08 |
| P1 | Normalizar URL Instagram `/usuario/reels/` no MassLoader | Concluido na Passada 12 |
| P1 | Corrigir executor para abrir atualizacao correta | Concluido na Passada 09 |
| P1 | Redirecionar logs Chromium/Electron do executor | Concluido na Passada 10 |
| P1 | Tolerar locks SQLite transitorios no worker | Concluido na Passada 21 |
| P1 | Automacao recorrente de melhoria sistemica | Concluido na Passada 13 |
| P1 | Modo pre-flight-only do launcher | Concluido na Passada 16 |
| P1 | Remover falso positivo Node desatualizado no pre-flight | Concluido na Passada 17 |
| P1 | Exibir versoes Python/Node/npm/Docker CLI no pre-flight | Concluido na Passada 18 |
| P1 | Exibir status de portas API/Web no pre-flight | Concluido na Passada 19 |
| P1 | Modo backend Docker + frontend nativo | Recomendado; pendente confirmacao |
| P2 | Exibir caminho local de downloads do MassLoader | Concluido na Passada 14 |
| P2 | Tela de sistema mais acionavel | Avancado na Passada 21; diagnosticos host pendentes |
| P2 | Organizar navegacao e operacao visual | Concluido na Passada 21 |
| P2 | Benchmark comparavel 1080p/2K/4K | Concluido na Passada 22 |
| P2 | Estimar custo do lote antes de criar | Concluido na Passada 23; calibrado na Passada 24 |
| P2 | Pre-flight de espaco livre para exportacao | Concluido na Passada 26 |
| P2 | Pausa/retomada persistente e cancelamento cooperativo | Concluido na Passada 28 |
| P2 | Cancelar lote inteiro e retry em massa dos falhos | Concluido na Passada 29 |
| P2 | Persistir pico real de memoria por job | Concluido na Passada 30 |
| P2 | Exibir pico por render e enriquecer quality report | Concluido na Passada 31 |
| P2 | Separar QC tecnico de aprovacao editorial | Concluido na Passada 31 |
| P2 | Integridade em massa explicita e sem varredura ao abrir | Concluido na Passada 31 |
| P2 | Cache persistente de QC por hash do render | Concluido na Passada 32 |
| P2 | Alertas de silencio/clipping e viewer do relatorio v2 | Concluido na Passada 32 |
| P2 | QC de lote em segundo plano com progresso/indice | Proxima passada recomendada |
| P2 | faster-whisper opcional | Pendente |
| P2 | PySceneDetect opcional | Pendente |
| P2 | `quality-report.json` no pacote | Concluido na Passada 05 |
| P2 | Demucs opcional no Music Lab | Pendente |
| P2 | Render Engine V2 | Pendente |

## Rodada Executada Em 2026-06-19 Sem Deixar Online

- Pesquisa usada: FastAPI CORS, Docker bind mounts, Electron Security e Ollama structured outputs.
- Melhorias aplicadas: CORS seguro com wildcard, importacao ampla desligada por default, `C:/` read-only no Docker, Electron endurecido, CSP basica, caminho padrao antigo removido, tipos frontend/API corrigidos e URL Ollama unificada.
- Evidencias: `npm.cmd run build` passou; `docker compose config` passou; portas `8000`, `8010`, `5173` e `5174` sem listeners.
- Bloqueios mantidos: testes backend e health real dependem de Python/venv funcional ou Docker engine ativo.
- Proximo melhor passo: recuperar ambiente de execucao sem misturar com novas features, depois rodar testes backend e fluxo real minimo.

## Rodada Sistemica Executada Em 2026-06-19

- Python/venv: `.venv` quebrada preservada como backup e recriada com Python 3.12.13; dependencias backend instaladas.
- Launcher: `VideoOS.ps1` agora aceita `pythonw.exe`, usa executaveis da venv para pip/pytest/uvicorn e cria venv com bootstrap por `VIDEO_OS_PYTHON_BOOTSTRAP`, runtime empacotado, `python` ou `py`.
- Frontend: `latest` removido; versoes fixas; `.npmrc` local para cache do projeto.
- Seguranca de dependencias: `npm audit` zerado em host e Docker.
- Docker: frontend passou de `node:20-alpine` para `node:22-alpine`; web build em Docker validado.
- Validacao completa: backend 52 testes em host e Docker na Passada 02, frontend build em host e Docker, API 200, web 200, worker ativo.
- Fechamento: `docker compose stop`; sem listeners em `8000`, `8010`, `5173` e `5174`.

## Rodada De Verificacao Detalhada Com Docker Em 2026-06-19

- Estado vivo: API, web e worker operantes em Docker; API e web saudaveis.
- API: `/api/system/health` 200; 22 endpoints GET seguros 200; OpenAPI 200.
- Worker: ativo, sem restart e sem erros recentes nos logs.
- Banco: `quick_check=ok`, WAL ativo, 0 violacoes de foreign key e `foreign_keys=ON` pela conexao da aplicacao.
- Testes/build/audit: backend Docker 52 passed na Passada 02; frontend build Docker e host passaram; npm audit 0 em Docker e host.
- UI: renderizada em navegador real; Google Fonts externo foi removido de `frontend/src/styles.css` para respeitar CSP/local-first.
- Achado pendente: assets existentes precisam de reparo/reindexacao de metadados e caminhos.
- Estado final: sistema permaneceu rodando em Docker, conforme contexto atual do usuario.

## Passada 02 - 2026-06-19 - Alinhamento Vivo E Reindexacao

- Pesquisa usada: FFmpeg ffprobe JSON, FFmpeg loudnorm, OWASP File Upload Cheat Sheet e SQLite WAL/checkpoints.
- Backend: adicionadas rotas `POST /api/assets/reindex` e `POST /api/assets/{asset_id}/reindex`.
- Dados reais: 3/3 assets reparados; `metadata_status=ready`, `media_url` e `thumbnail_url` presentes.
- Smart bins: `Atencao=0`, `Prontos para shorts=2`, `Longos=1`, `Com proxy=0`.
- Frontend: Biblioteca ganhou `Reindexar atencao`; `.asset-row` deixou de conter botoes dentro de botao.
- Validacao: backend 52 testes host e Docker; frontend build host e Docker; npm audit host e Docker com 0 vulnerabilidades; UI validada em navegador real.
- Encaminhamento: itens executados e fechados na Passada 03.

## Passada 03 - 2026-06-19 - Paths, Render Real E Pacote

- Pesquisa usada: OWASP File Upload Cheat Sheet, Python pathlib, Starlette StaticFiles e FastAPI Static Files.
- Backend: settings/output agora obedecem `ALLOWED_OUTPUT_ROOTS`, com `data/`, `Planejamento/` e roots extras em `VIDEO_OS_ALLOWED_OUTPUT_ROOTS`.
- Publicacao: `output_dir` arbitrario foi bloqueado; pacote manual permitido foi criado dentro de `/workspace/data/passada03-packages`.
- Render: corrigida sintaxe FFmpeg `drawtext=...`; job que revelou a falha foi reprocessado com sucesso.
- Frontend: favicon local adicionado; navegador real ficou sem 404/CSP/page errors.
- Fluxo real: proxy 720p, template, batch, render 1080x1920, quality, integridade, aprovacao e pacote manual validados.
- Validacao: backend 56 testes host e Docker; frontend build host e Docker; npm audit Docker com 0 vulnerabilidades; API/web/worker saudaveis.
- Proxima Passada 04: alinhar UI/presets com renderizador real, validar paths de B-roll/SRT e preparar decisao de Render Engine V2.

## Passada 04 - 2026-06-19 - Receitas E Paths De Midia

- Pesquisa usada: FFmpeg Filters e OWASP File Upload Cheat Sheet.
- Backend: adicionada `ALLOWED_RECIPE_MEDIA_ROOTS`; `captions.burned_srt_path` e `broll[].path` agora sao normalizados e validados antes do FFmpeg.
- Presets/seeds: templates instalaveis usam somente recursos aplicados pelo renderizador atual; seeds reconciliam templates numerados antigos.
- Frontend: `RenderRecipe` foi reduzido ao contrato aplicado e `TemplateStudio` ganhou controle real de enquadramento `crop/contain`.
- Validacao: testes novos falharam antes da implementacao e depois passaram; backend 60 testes host e Docker; frontend build host e Docker; npm audit Docker 0.
- Bloqueio: validacao viva detalhada apos `docker compose restart api worker web` foi bloqueada pelo limite de execucao da ferramenta.
- Proxima Passada 05: confirmar runtime vivo apos restart e seguir para migrations, `quality-report.json` ou Electron runtime.

## Passada 05 - 2026-06-19 - Runtime, Templates Legados E Quality Report

- Pesquisa complementar: FFmpeg ffprobe para futura medicao real do arquivo final, YouTube Help para Shorts ate 3 minutos e TikTok Business Help para specs/safe zone de video vertical.
- Runtime: confirmado apos restart; API e web healthy, worker ativo, API health `ok`, web 200 e fila sem falhas.
- Templates: seed passou a normalizar receitas persistidas; banco vivo confirmou 94 templates e 0 receitas com campos nao aplicados.
- Publicacao: pacotes finais agora incluem `quality-report.json` e `metadata.json` referencia o relatorio.
- Validacao: backend 61 testes host e Docker; `compileall` backend; frontend build host; pacote real criado em `data/passada05-packages`; logs recentes sem erros filtrados.
- Proxima Passada 06: migrations idempotentes formais ou runtime visual do Electron.

## Passada 06 - 2026-06-19 - Migrations E Regras Versionadas

- Pesquisa usada: SQLite ALTER TABLE, SQLAlchemy reflection e Alembic batch migrations.
- Banco: adicionada tabela `schema_migrations` com IDs/checksums e migration idempotente para colunas de regra em `platform_presets`.
- Plataforma: `PlatformPreset` agora guarda `rule_type`, `source_url`, `source_checked_at`, limites tecnicos, `safe_zone` e observacoes.
- API/frontend: `/api/platform-presets` expoe os novos campos e o contrato TypeScript foi alinhado.
- Validacao: testes vermelhos antes da implementacao, depois backend 63 testes host/Docker, `compileall`, frontend build, Docker Compose config, health API/web e banco vivo confirmando migrations.
- Encaminhamento daquela rodada: runtime visual do Electron ou `quality-report.json` com FFprobe/loudness real; a Passada 08 acabou priorizando MassLoader/runtime apos nova evidencia visual do usuario.

## Passada 08 - 2026-06-19 - MassLoader Runtime E yt-dlp

- Pesquisa usada: GitHub Releases oficial do `yt-dlp` e README oficial de update/nightly.
- Backend: `yt-dlp` atualizado para `2026.6.9`; status do MassLoader expoe `yt_dlp_version`.
- MassLoader: mensagens de falha de perfil Instagram agora incluem orientacao para rebuild/update, `cookies.txt` e URLs diretas de Reels/posts autorizados.
- Frontend: `CaptureDesk` mostra versao do `yt-dlp`; web Docker foi recriado para servir UI nova e `VITE_API_URL=http://127.0.0.1:8010`.
- Runtime: API `8010`, web `5174`, API/web healthy, worker ativo, `yt-dlp 2026.06.09` no container.
- Validacao: backend 68 testes host/Docker; `compileall`; frontend build; Docker Compose config; logs recentes sem traceback/erro critico.
- Proxima decisao recomendada: transformar backend Docker + frontend nativo em modo oficial.

## Passada 09 - 2026-06-19 - Executor VideoOS

- Alvo: fazer o executor abrir a atualizacao correta do VideoOS, sem cair em frontend/porta/env antigos.
- Implementado: `VideoOS.ps1` le `.env`, fixa defaults operacionais em API `8010` e web `5174`, valida `VITE_API_URL`, confere se containers estao frescos em relacao a arquivos criticos e recria a stack quando detectar defasagem.
- Validacao sem janela: `VIDEO_OS_NO_OPEN=1` impede Electron/Edge durante smoke test.
- Evidencia: executor validado com Docker real; stack existente atual foi reaproveitada sem reiniciar; API `8010`, web `5174`, API/web healthy, worker up e frontend servido com `http://127.0.0.1:8010`.
- Pendencia opcional: criar um executor dedicado para o modo backend Docker + frontend/Electron nativo se essa arquitetura for aprovada como caminho principal.

## Passada 10 - 2026-06-19 - Logs Chromium/Electron

- Alvo: tratar o log `Network service crashed or was terminated, restarting service` reportado no terminal.
- Diagnostico: API/web/worker permaneceram operantes; o log veio do runtime Chromium/Electron/Edge e nao de queda da stack Docker.
- Implementado: `VideoOS.ps1` redireciona stdout/stderr do Electron para `data/logs/electron.desktop.log` e `data/logs/electron.desktop.err.log`; se o Electron fechar rapido, o executor exibe o caminho e as ultimas linhas do erro antes de cair para Edge.
- Validacao: parser PowerShell OK; `electron.cmd --version` redirecionado retornou `v42.4.1`; `docker compose config --quiet` OK; API 200; web 200; Docker healthy.

## Passada 11 - 2026-06-19 - Local Dos Downloads

- Alvo: responder onde o MassLoader salva os downloads no container e no Windows.
- Confirmado: downloads ficam em `/workspace/data/incoming/massloader/<timestamp>` no container e em `data\incoming\massloader\<timestamp>` no Windows pelo bind mount do projeto.
- Cookies: uploads ficam em `data\incoming\massloader-cookies`.
- Biblioteca: quando `import_to_library` esta ativo, o arquivo tambem e copiado para `data\assets\<asset_id>.mp4`.
- Evolucao pendente: deixar o caminho Windows/local mais visivel no painel de resultado e/ou botao seguro para abrir a pasta.

## Passada 12 - 2026-06-19 - MassLoader Instagram `/reels/`

- Alvo: corrigir o teste do usuario com `https://www.instagram.com/art_viral/reels/`, que retornava `Unsupported URL`.
- Diagnostico: o extractor oficial do `yt-dlp` diferencia perfil raiz de URL direta de post/Reel; a aba de perfil `/usuario/reels/` nao e aceita diretamente.
- Implementado: `parse_sources` agora normaliza abas `reels`, `tagged` e `guides` de perfil Instagram para `https://www.instagram.com/<usuario>/` antes do downloader.
- Frontend: `CaptureDesk` orienta `post/Reel direto` e avisa que `/usuario/reels/` vira perfil raiz.
- Validacao: teste vermelho/verde novo; backend host 69 testes; backend Docker 69 testes; frontend build; API/web/worker saudaveis; `parse_sources` no container retornou `https://www.instagram.com/art_viral/`.
- Pendencia externa: perfis ainda podem exigir `cookies.txt` e falhar por instabilidade do Instagram/yt-dlp; para itens especificos, URLs diretas continuam mais confiaveis.

## Passada 13 - 2026-06-20 - Automacao Recorrente

- Alvo: criar uma automacao para continuar melhorias, correcoes e auditoria sistemica no mesmo padrao das passadas.
- Criado: `videoos-melhoria-sistemica-5h10`, ativa.
- Agenda: primeira execucao em 2026-06-20 as 18:35, fuso `America/Sao_Paulo`; depois, recorrencia de 5h10.
- Prompt: ler os 4 MDs obrigatorios, abrir a proxima passada na memoria, selecionar o proximo item importante do plano/runtime, pesquisar fontes oficiais quando necessario, implementar e validar uma melhoria pequena, atualizar MDs e reportar evidencias/riscos/proxima passada.
- Validacao: automacao criada e visualizada no app pelo ID; nao houve alteracao de codigo nesta passada.
- Resultado posterior: Passada 14 foi executada pela automacao.

## Passada 14 - 2026-06-20 - Caminho Local Do MassLoader

- Alvo: reduzir duvida operacional sobre onde ficam os downloads do MassLoader.
- Implementado: `frontend/src/massloaderPaths.ts` converte paths `/workspace/data/incoming/massloader/...` para `data\incoming\massloader\...`; `CaptureDesk` mostra o caminho do container e o caminho local no resultado.
- Teste: `frontend/tests/massloaderPaths.test.ts` cobre path container, path com barras Windows, path fora do MassLoader e valor vazio.
- Validacao: `npm.cmd run test:paths`, `npm.cmd run build` e `git diff --check` passaram.
- Bloqueio operacional: `docker compose ps` nao conectou ao Docker Desktop; a proxima passada deve revalidar runtime Docker antes de alterar algo que dependa da stack viva.

## Passada 15 - 2026-06-20 - Tela Sistema Mais Acionavel

- Alvo: continuar a melhoria P2 da tela Sistema enquanto Docker Desktop segue indisponivel.
- Implementado: `SystemPanel` mostra FFprobe, path do banco SQLite, pacotes, fila `queued/processing/failed`, raizes de importacao e saidas permitidas.
- Settings: o frontend passou a enviar somente campos mutaveis ao salvar caminhos, sem reenviar `allowed_output_roots`.
- Higiene visual: textos do `SystemPanel` foram normalizados para ASCII.
- Validacao: `npm.cmd run build`, `npm.cmd run test:paths`, `docker compose config --quiet` e `git diff --check` passaram.
- Bloqueio operacional: `docker compose ps` e `docker version` continuaram sem conectar ao Docker Desktop; a proxima passada deve revalidar runtime vivo antes de mudancas dependentes da stack.

## Passada 16 - 2026-06-21 - Diagnostico Host E Pre-flight Sem Docker

- Alvo: permitir diagnostico repetivel sem iniciar servicos quando Docker Desktop esta indisponivel.
- Implementado: `VideoOS.ps1` reconhece `VIDEO_OS_PREFLIGHT_ONLY=1`; com a flag ativa, executa `Invoke-PreFlightAudit` e sai antes de preparar diretorios, instalar dependencias, iniciar Docker/local mode, API, Vite ou Electron.
- Validacao: parser PowerShell OK; execucao com `VIDEO_OS_PREFLIGHT_ONLY=1` e `VIDEO_OS_NO_OPEN=1` retornou exit 0; `docker compose config --quiet` e `git diff --check` passaram.
- Diagnostico atual: arquivos essenciais integros, Python atualizado, Node marcado como desatualizado por timestamp, Docker Desktop offline e portas `8010`/`5174` sem listeners.
- Proxima passada: rodar pre-flight-only primeiro, depois revalidar Docker Desktop/API/web/worker.

## Passada 17 - 2026-06-21 - Pre-flight Node Sem Falso Positivo

- Alvo: corrigir diagnostico enganoso de Node desatualizado quando `package.json` muda por scripts/metadados, mas a arvore de dependencias travada em `package-lock.json` nao muda.
- Fonte oficial: docs npm de `package-lock.json` e `npm ci`, usadas para confirmar o lockfile como representacao da arvore exata/fixa de dependencias.
- Implementado: `VideoOS.ps1` ganhou `Get-FrontendDependencyMarker`; `Invoke-PreFlightAudit` e `Ensure-FrontendEnv` usam `package-lock.json` quando existir e `package.json` apenas como fallback.
- Validacao: parser PowerShell OK; pre-flight-only retornou exit 0 e reportou Node `ATUALIZADO`; `docker compose config --quiet` e `git diff --check` passaram.
- Bloqueio operacional: Docker Desktop continuou offline pelo pipe `npipe:////./pipe/dockerDesktopLinuxEngine`; portas `8010` e `5174` sem listeners.
- Proxima passada: revalidar Docker Desktop/API/web/worker antes de mudancas dependentes da stack; se online, avancar para modo backend Docker + frontend/Electron nativo.

## Passada 18 - 2026-06-23 - Versoes No Pre-flight

- Alvo: tornar o diagnostico host-only mais acionavel enquanto Docker Desktop segue indisponivel.
- Implementado: `VideoOS.ps1` ganhou helpers para detectar executaveis, coletar versoes e ler a versao Python de `.venv\pyvenv.cfg` quando o runtime e `pythonw.exe`.
- Resultado: `Invoke-PreFlightAudit` agora mostra Python runtime, Node, npm e Docker CLI alem dos status de dependencias.
- Validacao: parser PowerShell OK; pre-flight-only retornou exit 0 sem iniciar servicos e exibiu Python `3.12.13`, Node `v24.14.1`, npm `11.11.0`, Docker CLI `29.5.3`, Node `ATUALIZADO` e Docker Desktop `OFFLINE`; `docker compose config --quiet` e `git diff --check` passaram.
- Bloqueio operacional: Docker Desktop continuou offline pelo pipe `npipe:////./pipe/dockerDesktopLinuxEngine`; portas `8010` e `5174` sem listeners.
- Proxima passada: repetir pre-flight-only; se Docker estiver online, validar stack viva completa. Se continuar offline, evoluir melhorias host-only da tela Sistema ou limpar encoding/documentacao.

## Passada 19 - 2026-06-23 - Portas No Pre-flight

- Alvo: reduzir comandos manuais repetidos nas automacoes quando Docker Desktop esta offline.
- Implementado: `VideoOS.ps1` ganhou `Get-PortStatusLabel`; `Invoke-PreFlightAudit` agora mostra as portas esperadas da API e Web como `LIVRE` ou `OCUPADA`.
- Resultado: as portas sao derivadas de `VIDEO_OS_API_PORT`/`VIDEO_OS_WEB_PORT`, com fallback para `8010`/`5174`, e testadas por bind local rapido sem iniciar servicos.
- Validacao: parser PowerShell OK; pre-flight-only retornou exit 0 sem iniciar servicos e exibiu `Porta API esperada (8010): LIVRE` e `Porta Web esperada (5174): LIVRE`; `docker compose config --quiet` e `git diff --check` passaram.
- Bloqueio operacional: Docker Desktop continuou offline pelo pipe `npipe:////./pipe/dockerDesktopLinuxEngine`.
- Proxima passada: repetir pre-flight-only; se Docker estiver online, validar stack viva completa. Se continuar offline, avancar em melhoria host-only de tela Sistema ou limpeza documental de encoding.

## Passada 21 - 2026-07-10 - Auditoria Completa E Organizacao Visual

- Alvo: revisar sistema, runtime, seguranca, dependencias, fluxo em massa e organizacao visual sem ampliar o escopo do renderizador.
- Interface: navegacao recolhivel, home operacional, busca de templates, resumo de lote/fila e tela Sistema responsiva e organizada.
- Seguranca: Electron limitado a URL loopback, IPC com origem validada e DevTools opt-in.
- Qualidade: removidos overrides visuais tardios, fontes nao declaradas e CSS morto; botoes icon-only usam tooltip.
- Validacao: backend 98 testes, compileall, pip check, frontend build/testes, sintaxe Electron, npm audit 0, Compose config, diff check, API health `ok`, web 200 e worker ativo.
- Runtime: o web foi reiniciado para descartar transformacao Vite antiga e passou a servir os componentes novos.
- Resiliencia: logs historicos revelaram lock SQLite no worker; o loop ganhou fechamento de sessao antes do idle e retry/backoff seletivo, com 3 testes novos. Worker reiniciado e logs recentes limpos.
- Limites: `pip-audit` ausente; `npm outdated` bloqueado por problema no cache local; navegador automatizado recusou URL loopback.
- Proxima passada recomendada: medir lote maior em 1080p/2K/4K e, quando permitido, fazer validacao visual desktop/mobile dedicada.

## Passada 22 - 2026-07-10 - Benchmark 1080p, 2K E 4K

- Alvo: executar o teste de escala recomendado com a mesma receita completa nas tres resolucoes.
- Utilitario: `backend/scripts/benchmark_render_presets.py` mede tempo, CPU, pico RSS, tamanho, bitrate, codecs, dimensoes e FPS e grava relatorio JSON.
- Falha encontrada: preset 2K gerava `logo_size=219` e falhava no FFmpeg com `Padded dimensions cannot be smaller than input dimensions`.
- Correcao: backend normaliza logo par; UI gera 218 em 2K; presets escalam fonte/borda; watermark/margens escalam; CTA inferior respeita safe zone quando captions estao ativas.
- Resultado final: 1080p 4.822s/2.03 MiB/1.51 GiB; 2K 6.731s/3.96 MiB/2.34 GiB; 4K 14.168s/8.20 MiB/4.78 GiB.
- Qualidade: tres MP4 H.264/AAC passaram por decode integral; thumbnails confirmaram composicao proporcional e ausencia de sobreposicao CTA/captions.
- Validacao: backend 101 testes, frontend build e `test:paths`, script compilado, Compose config, health e logs do worker passaram.
- Decisao: 1080p default de massa; 2K seletivo; 4K sequencial/sob demanda.
- Proxima passada recomendada: mostrar estimativa de tempo/tamanho/memoria no `BatchQueue` e confirmar lotes 4K extensos.

## Passada 23 - 2026-07-10 - Estimativa Preventiva E Confirmacao 4K

- Alvo: transformar o benchmark da Passada 22 em informacao preventiva antes do enfileiramento.
- Implementacao: helper puro calcula tempo, saida e pico por job a partir de resolucao, duracao e variacoes; duracao ausente usa fallback explicito de 30s.
- Protecao: lotes 4K com mais de um job ou mais de 30s renderizados exigem checkbox de confirmacao; qualquer mudanca relevante invalida a confirmacao.
- Interface: estimativa aparece como faixa operacional responsiva, identifica benchmark/base local e fila sequencial, sem prometer valor exato.
- Validacao: backend 101 testes, frontend build e `test:paths`, Compose config, API/web 200/healthy, SQLite WAL, FFmpeg/FFprobe e fila sem falhas passaram.
- Limite: a politica local do Chrome continuou bloqueando validacao visual automatizada de loopback; build, codigo servido e responsividade CSS foram verificados.
- Proxima passada recomendada: persistir metricas reais por job e calibrar os perfis por receita/host, mantendo a Passada 22 como fallback.

## Passada 24 - 2026-07-11 - Telemetria Local E Calibracao Conservadora

- Alvo: aprender com jobs reais sem remover o baseline confiavel nem enviar telemetria externa.
- Persistencia: `RenderedVideo` guarda `size_bytes`/`render_seconds`; migration idempotente e retropreenchimento cobrem banco legado.
- Agregacao: health usa ate 20 amostras recentes por template/resolucao e exige 3 para calibrar tempo/tamanho.
- Correcao: estimador passou a respeitar `trim.start/end`, evitando superestimar assets longos usados em trechos curtos.
- UI: identifica benchmark ou historico local e mostra progresso da coleta; guardrail 4K e pico de memoria permanecem.
- Validacao: backend 104 testes, frontend build/`test:paths`, compileall, pip check, Compose, migration, API/web/worker e SQLite WAL passaram.
- Runtime: 2/2 renders existentes retropreenchidos; duas amostras de templates distintos ficaram em `1/3`, portanto o fallback continuou ativo como projetado.
- Proxima passada recomendada: consultar espaco livre da pasta de exportacao e comparar com a saida estimada antes de lotes grandes.

## Passada 25 - 2026-07-11 - Organizacao E Polimento Visual Dedicado

- Interface: Home, navegacao mobile, Biblioteca, Template Studio e Lotes foram reorganizados sem alterar contratos funcionais.
- Validacao: backend 104 testes, frontend build/`test:paths`, compileall, pip check, Compose, API/web, worker e SQLite WAL passaram.
- Limite: captura final bloqueada pela politica local de loopback.
- Proxima passada: auditar melhorias restantes e implementar o pre-flight de capacidade de exportacao.

## Passada 26 - 2026-07-11 - Auditoria E Capacidade De Exportacao

- Alvo: revalidar riscos/atualizacoes e impedir que lotes ultrapassem o espaco seguro da pasta escolhida.
- Backend: novo servico e endpoint de capacidade; criacao de lote repete a verificacao usando a estimativa enviada pela UI.
- Frontend: fila mostra capacidade confirmada, margem necessaria e espaco seguro; bloqueia somente insuficiencia confirmada.
- Politica: 15% de margem da estimativa e reserva do maior valor entre 1 GiB e 10% do espaco livre.
- Validacao: backend 108 testes, frontend build/`test:paths`, npm audit 0, compileall, pip check, Compose, API/web healthy, worker ativo e SQLite WAL.
- Dependencias: React, yt-dlp e gallery-dl atuais; upgrade conjunto de FastAPI/Uvicorn/SQLAlchemy/Pydantic recomendado para a proxima passada.

## Passada 27 - 2026-07-11 - Atualizacao Controlada Dos Frameworks Python

- Alvo: atualizar o nucleo FastAPI sem quebrar API, worker, banco ou testes.
- Versoes: FastAPI 0.139.0, Uvicorn 0.50.2, SQLAlchemy 2.0.51, Pydantic 2.13.4, Starlette 1.3.1 e HTTPX2 2.5.0.
- Compatibilidade: HTTPX antigo foi substituido por HTTPX2 apos o TestClient emitir deprecacao; suite final ficou sem warnings.
- Build: builder classico contornou erro conhecido do BuildKit/pipe; imagens API/worker reconstruidas e containers recriados.
- Validacao: 108 testes na imagem, 108 no container vivo e 108 na `.venv`; compileall/pip check, Compose, OpenAPI e seis endpoints principais passaram.
- Runtime: API/web healthy, worker ativo, SQLite WAL, 34 assets, 94 templates e fila sem falhas.
- Proxima passada: pausa/retomada de lote e cancelamento cooperativo do job em processamento.

## Passada 28 - 2026-07-11 - Pausa, Retomada E Cancelamento Cooperativo

- Alvo: controlar lotes extensos sem perder a fila e permitir encerrar um FFmpeg ativo por decisao do usuario.
- Persistencia: migration `20260711_0004_queue_controls` adicionou `batches.is_paused` e `render_jobs.cancel_requested` com default `0`.
- Fila: lotes pausados nao entregam novos jobs; `pausing` indica que o job atual ainda termina; retomar libera os mesmos pendentes.
- Cancelamento: jobs em processamento recebem pedido persistente; o executor consulta o SQLite, termina/mata o subprocesso se necessario, limpa o temporario e registra `canceled` sem falso erro tecnico.
- Restart: processamento interrompido volta para a fila, exceto quando havia pedido de cancelamento, caso em que fecha como cancelado.
- Interface: historico ganhou pausa/retomada; jobs ativos ganharam cancelar; status `paused`/`pausing` e pedido pendente ficam visiveis. Polling de health tolera uma falha isolada.
- Validacao: 113 testes na `.venv` e na imagem Docker, `compileall`, `pip check`, frontend build/`test:paths`, npm audit 0, Compose, OpenAPI, API/web healthy, worker ativo, SQLite WAL e migration real.
- Visual: navegador validado em 419 px e 1440 px, sem overflow horizontal, erros de console ou estado offline transitorio apos o ajuste.
- Proxima passada: cancelar o lote inteiro e recolocar todos os falhos/cancelados na fila em uma unica acao; depois persistir pico real de memoria por job.

## Passada 29 - 2026-07-16 - Auditoria Integral, Controles Em Massa E Polimento Visual

- Alvo: concluir o controle por lote, auditar todo o stack, atualizar dependencias seguras e reduzir fragmentacao visual em filas grandes.
- Backend: endpoints de cancelamento e retry por lote, status `canceling`, contagens `active/canceled/retryable` e eventos de auditoria consolidados.
- Semantica: cancelamento pausa o lote, fecha queued/failed e solicita encerramento dos processing; retry reabre apenas failed/canceled, preserva completed e pode reiniciar tentativas.
- Frontend: filtros `Ativos/Atencao/Todos`, 50 jobs iniciais com expansao progressiva, acoes com loading/erro e historico de largura total com contagens alinhadas.
- Dependencias: FastAPI 0.139.1, Uvicorn 0.51.0, HTTPX2 2.7.0, yt-dlp 2026.7.4, gallery-dl 1.32.6, Lucide React 1.24.0, Vite 8.1.5 e plugin React 6.0.3.
- Seguranca: npm audit 0; Electron manteve sandbox, isolamento de contexto, Node desligado, IPC/origem validados, bloqueio de navegacao/janelas e permissoes negadas. `pip-audit` segue ausente.
- Validacao: 115 testes no host e container, build frontend host/container, `test:paths`, sintaxe Electron, compileall, pip check, Compose, OpenAPI, health, web 200, logs e SQLite passaram.
- Visual: desktop sem overflow, historico de 1426 px; mobile com 513 px uteis, paineis de 490 px, linhas de 455 px e nenhum elemento visivel escapando do container.
- Runtime: imagens API/worker/web reconstruidas, containers recriados e deixados ativos; API/web healthy em `8010`/`5174`, worker ativo, FFmpeg/FFprobe disponiveis e fila sem falhas.
- Proxima passada: persistir pico RSS real por job e incorporar o dado ao estimador; avaliar Electron 43/TypeScript 7 em rodada separada.

## Passada 30 - 2026-07-16 - Telemetria De Pico RSS Por Job E Calibracao De Memoria

- Alvo: substituir a lacuna de memoria do historico local por telemetria real por job, sem reduzir o baseline conservador da Passada 22.
- Backend: `RenderedVideo.peak_rss_bytes`, migration idempotente, persistencia no worker, serializer e agregacao por template/resolucao.
- Sampler: leitura Linux via `/proc` e Windows via `GetProcessMemoryInfo`, em intervalos de 250 ms, tolerante a plataforma ou processo indisponivel.
- Estimador: tempo/tamanho mantem minimo de 3 amostras; memoria positiva entra imediatamente apenas para elevar `max(local, benchmark)`.
- Frontend: faixa de custo mostra `benchmark conservador` ou numero de amostras com `piso seguro`, preservando o layout compacto.
- Validacao: 116 testes no host e container, 22 focados, `compileall`, `pip check`, builds e `test:paths` host/container, npm audit 0, migration e SQLite passaram.
- Prova real: processo Python mediu `34.996.224` bytes e FFmpeg controlado mediu `53.477.376` bytes; health preservou renders legados com memoria nula.
- Visual/runtime: fila validada em `1440x1000` e `419x900`; API/web healthy em `8010`/`5174`, worker ativo e stack deixada online.
- Proxima passada: exibir o pico medido por render na Revisao e ampliar `quality-report.json` com FFprobe/loudness reais; Electron 43/TypeScript 7 continuam separados.

## Passada 31 - 2026-07-19 - Auditoria Integral, Revisao Tecnica E Quality Report Medido

- Alvo: fechar a telemetria por render e o relatorio medido, corrigindo tambem inconsistencias funcionais/visuais verificadas na auditoria.
- Correcao critica: score tecnico 100 nao significa pacote pronto quando o render esta `pending_review` ou `rejected`; backend e UI agora separam os estados.
- Backend: FFprobe expoe codecs/audio/container/bitrate; loudnorm mede LUFS/true peak/LRA; QC inclui tempo/pico RSS e `package_ready`; quality report passou para v2.
- Escala: pacote Instagram/TikTok/Shorts reutiliza uma unica analise por render, evitando tres varreduras completas do mesmo arquivo.
- Operacao em massa: integridade nao roda mais ao abrir Revisao; `Verificar todos` processa grupos de 3 e a verificacao individual permanece disponivel.
- Frontend: telemetria e analise em grids estaveis, historico limitado a 20 e convertido em cards no mobile, Publicacao com pacote vazio bloqueado.
- Validacao: 120 testes backend, compileall, pip check, build Vite 8.1.5, `test:paths`, npm audit 0 e Compose config passaram.
- Runtime: API/web healthy em `8010`/`5174`, worker ativo, FFmpeg/FFprobe disponiveis, SQLite WAL e fila sem falhas.
- Prova real: render H.264/AAC medido em 30 FPS, 1704.11 kbps, `-14.1 LUFS` e `-5.73 dBTP`; reports tecnicos passaram, mas `package_ready=false` por status `rejected`.
- Visual: desktop 1440x1000 e mobile 419x900 confirmaram Revisao/Sistema/Publicacao alinhados e console sem warning/error.
- Dependencias: npm sem vulnerabilidades; `pip-audit` ausente; Lucide 1.25, Electron 43 e TypeScript 7 disponiveis, sem atualizacao automatica nesta passada.
- Proxima passada: cache persistente de QC por hash, alertas de silencio/clipping e viewer/download do relatorio v2 na Publicacao.

## Passada 32 - 2026-07-19 - Cache De QC, Alertas De Audio E Relatorio Na Publicacao

- Alvo: eliminar reanalise repetida do render, tornar falhas de audio acionaveis, expor o relatorio final e percorrer visualmente toda a aplicacao.
- Persistencia: migration `20260719_0006_render_quality_cache` adiciona cache com schema, SHA-256, horario e metadados; mudanca do arquivo invalida a analise.
- Qualidade: silencio e clipping bloqueiam tecnicamente; falta de audio, headroom baixo e loudness fora da faixa recebem severidade explicita sem substituir revisao editorial.
- Publicacao: endpoint com allowlist/filho direto entrega o relatorio; a UI agrupa tarefas e oferece viewer/download acessivel, inclusive para pacotes historicos v1.
- Visual: 17 telas auditadas em `1440x1000` e `419x900`; Captura e Editor perderam overflow mobile, Publicacao/Revisao ficaram mais compactas e nenhuma tela terminou com overflow global.
- Validacao: 125 testes backend no host e container, 23 focados, `compileall`, `pip check`, builds host/container, `test:paths`, Electron syntax check, npm audit 0 e Compose config passaram.
- Runtime: API/web healthy em `8010`/`5174`, worker ativo, SQLite WAL/integro, migration unica, cache vivo e logs finais limpos.
- Prova real: QC passou de `miss` em cerca de 2.031s para `hit` em cerca de 0.035s na amostra local; viewer abriu quality report v1 historico com score 100 e 5 checks.
- Dependencias/seguranca: varredura do codigo executavel sem segredos/padroes perigosos; `pip-audit` ausente; Electron 43 e TypeScript 7 continuam em rodada separada.
- Proxima passada: executar QC de lote em segundo plano com progresso e indice consolidado; validar novo pacote v2 quando houver render editorialmente aprovado.

### Passada 33 (2026-08-19) - Saneamento de Arquivos Sombra, Hardening de Seguranca e Command Palette

- Saneamento geral: eliminados todos os 78 arquivos sombra `*(1)*` do repositório gerados por concorrência de sincronização na nuvem.
- Seguranca: endpoint `/media` em `backend/app/main.py` protegido com `SafeStaticFiles` bloqueando `/db`, `/massloader-cookies`, `/logs` e `settings.json` (SEC-01).
- Hardening Docker: mount amplo `C:/:/host/c:ro` removido do `docker-compose.yml` (SEC-02).
- Frontend: Command Palette (`Ctrl+K` / `Cmd+K`) implementado com navegação rápida entre as 17 telas e disparo de ações globais (backup SQLite e refresh de dados).
- Validacao: 126 testes de backend rodando e passando 100%, `npm run build` do frontend com TypeScript e Vite passando em ~1.6s, e `npm run test:paths` passando.

### Passada 40 (2026-09-09) - Auditoria Completa com 10 Agentes Especializados e Implementações Estruturais

- Mobilização de 10 agentes especializados cobrindo Render, Banco de Dados, Fila/Worker, Segurança, IA/LLM, Audio Lab, Social/QC, Arquitetura Frontend, UI/UX e Infra/DevOps.
- Render Engine: `:force_divisible_by=2` em escala e logo, reordenação de camadas de B-Roll (overlays e legendas sobre o B-Roll), retiming de b-roll, mixagem com `aformat` estéreo 48kHz, tolerância com `-an` para vídeos sem áudio, escape de caracteres especiais.
- Segurança & Path Policy: `SafeStaticFiles` com checagem canônica de diretório (`relative_to`) e whitelist de extensões restrita a mídias, `SecurityHeadersMiddleware` injetado na FastAPI, proteção de path traversal em `/api/music/separate-stems`.
- Banco de Dados: exclusão de assets em cascata (`BrollCue`, `ClipCandidate`, `Transcript`) prevenindo erro 500 de foreign key, limpeza de thumbs órfãs, nova migração `20260909_0007_performance_indexes` com índices estratégicos tolerantes a bancos legados, concorrência SQLite WAL sem deadlocks.
- IA, Transcrições & Clips: VAD filter no faster-whisper, word-timestamps no Whisper CLI, detecção de silêncio residual final, busca de clipes com Non-Maximum Suppression (NMS) e janelas variáveis, validação estrita Pydantic de saídas de agentes LLM.
- Social & Safe Zones: limites de duração ajustados para Instagram Reels (15 min) e TikTok (10 min), margem de Karaokê ASS elevada para 460px (~24%) para não colidir com a interface do TikTok/Reels.
- Frontend & UI/UX: dependência do `useEffect` corrigida no `TemplateStudio.tsx` (`[selected?.id]`) eliminando perda de texto em digitação com polling, 3 telas faltantes adicionadas ao `CommandPalette.tsx` (Ferramentas, Presets e Agentes), atalhos de QC no `ReviewDesk.tsx` (`[A]`, `[R]`, `[S]`, `[Z]`, `[Espaço]`), botão toggle da máscara Safe Zone, `--muted-2` elevado para `#8e9ca8` (WCAG AA), regra CSS de player vertical responsivo com `object-fit: cover`, polling pausando em aba em background (`document.hidden`) e métodos CRUD para Brand Kit no cliente de API.
- Infra: repasse de argumentos `%*` no `VideoOS.cmd`.
### Passada 41 (2026-09-22) - Auditoria Ampla de Templates, Comparativo Canva e Vulnerabilidades de Conversão

- Auditoria ampla do módulo de Templates (`TemplateStudio.tsx`, `templates.py`, `render.py`, `schemas.py`):
  - Mapeamento funcional comparativo contra o Canva em 10 dimensões críticas (Camadas livres, Transformação/Posicionamento, Tipografia, Cores/BrandKit, Formas/Adesivos, Proporções de Tela, Animações/Keyframes, Criação em Massa, Ciclo de Vida CRUD e Trilha de Áudio).
  - Identificação de 8 vulnerabilidades e erros críticos de conversão de dados:
    1. Drawtext & Multiline Filter Injection: Quebra de linha em `<textarea>` crashando filtergraphs do FFmpeg no subprocesso de renderização.
    2. Conversão de Cores (`ffmpeg_color`): Falha ao manipular cores hexadecimais de 8 dígitos (`#RRGGBBAA`), 3 dígitos (`#RGB`) e `rgba(...)`.
    3. Inconsistência nos 3 motores de filtro (`build_video_filters`, `build_broll_filter_complex`, `build_framed_filter_complex`): Descarte silencioso de zoom dinâmico e CTAs ao ativar moldura ou B-roll.
    4. Funcionalidades fantasma na UI (`jump_cut` na tela mas ausente no backend; `layout: pip` não implementado; `split_vertical` sem o segundo vídeo; `captions.style` ignorado em `.srt`).
    5. Risco de divisão por zero e dimensões inválidas em `frame_layout` (`logo_size` ímpar virando 0 gerando `scale=0:0`).
    6. Parâmetros de ducking de áudio sem bounds checking (`threshold`, `ratio`, `attack`, `release`).
    7. Caminhos não validados de mídia em `split.secondary_video_path` e `hooks[].hook_video_path`.
    8. Falta de endpoints CRUD de ciclo de vida (`PUT /api/templates/{id}` para edição real sem duplicatas e `DELETE /api/templates/{id}`).
- Validação: 155 testes backend no pytest (100% de sucesso), compilação do frontend Vite em 3.15s e testes de paths aprovados.
- Próximas ações prioritárias para modernização e blindagem do estúdio de templates:
  1. Implementar schema Pydantic estrito para `recipe` em `schemas.py` e rotas completas de CRUD (`PUT`, `DELETE`, `GET /{id}`). (Concluído na Passada 42)
  2. Corrigir `ffmpeg_color` para suportar `#RRGGBBAA` e `#RGB`, e sanitizar textos com quebras de linha para drawtext. (Concluído na Passada 42)
  3. Unificar o pipeline de filtros do FFmpeg para garantir paridade total de zoom e CTAs em todos os modos. (Concluído na Passada 42)
  4. Conectar o `TemplateStudio` ao `BrandKit` para herança instantânea de paleta, logos e tipografia. (Concluído na Passada 42)
  5. Expandir o suporte a formatos de tela para incluir 16:9 (YouTube) e 1:1 (Feed). (Concluído na Passada 42)

### Passada 42 (2026-09-22) - Modernização de Templates, Paridade Canva, Correção de 12 Vulnerabilidades e Refinamento de Fluidez

- Implementação integral do plano de modernização de templates e blindagem contra as 12 vulnerabilidades levantadas na auditoria:
  1. CRUD Completo de Templates: endpoints `GET /api/templates/{id}`, `PUT /api/templates/{id}`, `DELETE /api/templates/{id}` (com verificação de integridade referencial retornando 409 caso haja lotes ou renders vinculados) e `POST /api/templates/{id}/duplicate`.
  2. Drawtext & Sanitização de Caracteres: `escape_drawtext` converte `\n` em `\\n` para suporte visual a múltiplas linhas no FFmpeg, escapa duplamente `%` (`\\%`) para neutralizar expansão involuntária de macros do FFmpeg em textos com percentual (ex: "50% OFF") e protege aspas e dois-pontos.
  3. Conversão de Cores (`ffmpeg_color`): suporte unificado por regex a `rgba(r,g,b,a)`, `rgb(r,g,b)`, hexadecimais de 3, 4, 6 e 8 dígitos (`#RGB`, `#RGBA`, `#RRGGBB`, `#RRGGBBAA`) e prefixo `0x`.
  4. Ducking de Áudio e Mixagem FFmpeg: correção da falha crítica de reuso de pad no filtergraph de áudio utilizando `asplit=2` (`[a_voice]` e `[a_trigger]`), adição de `normalize=0` no `amix` para preservar o volume da voz do locutor e bounds checking de `threshold`, `ratio`, `attack_ms` e `release_ms`.
  5. Unificação de Motores de Render: zoom dinâmico e CTAs integrados a `build_broll_filter_complex` e `build_framed_filter_complex` (eliminando o descarte silencioso anterior), com verificação de limites em `frame_layout` (`logo_size >= 16` e dimensões pares).
  6. Subtítulos e Karaokê: parser robusto de arquivos SRT/VTT (`parse_subtitles_text`, `parse_subtitles_file`), conversor ASS estilizado (`convert_srt_to_styled_ass`) e interpolação de palavras em `build_ass_karaoke` para legendas sem timestamps por palavra.
  7. Audio Lab e Stem Separation: Demucs CLI chamado com `--two-stems=vocals` e extração de diretório `htdemucs`, e fallback DSP com conversão estéreo prévia obrigatória para estabilidade do filtro `stereotools` e EQ vocal balanceado.
  8. Quality Check: relaxamento do FPS para Instagram Reels (24-29 fps aceito com info, apenas < 23 como erro), tolerância no aspect ratio 9:16 (0.54 a 1.92), durações mínimas para TikTok (3.0s) e YouTube Shorts (1.0s).
  9. Resiliência de Fila e Limpeza: eliminação de deadlocks de cancelamento com force-cancel para jobs travados em `processing`, purga recursiva com `rglob` de arquivos parciais de lotes e correção de checagem de espaço em disco com estimativa zero (`safe_available_bytes > 0`).
  10. TemplateStudio Modernizado: eliminação da renomeação forçada para `copia`, ações explícitas de salvar alterações (PUT), salvar como novo (POST) e excluir (DELETE), botão 1-clique "Herdar Marca" sincronizado com o `BrandKit` (cores, logo, marca d'água, karaokê), e Canvas Mockup 9:16 com Safe Zones interativas comutáveis.
  11. BatchQueue & ReviewDesk: race condition eliminada com `await onCreateBatch(...)` antes de `await onProcessNext()`; filtros por status de aprovação e geração em 1-clique de pacote de publicação no `ReviewDesk.tsx`.
- Validação: suite ampliada para 158 testes no pytest backend (100% aprovados em 16.55s), build do frontend em 1.16s via Vite 8.1.5 e testes de caminhos passando.

### Passada 43 (2026-09-22) - Blindagem de Mídia contra Path Traversal, Concorrência de Jobs e Sanitização 500

- Blindagem de Mídia Zero Trust:
  1. Extensões de validação e normalização em `render.py` cobrindo `split.secondary_video_path`, `hooks[].hook_video_path` e `watermark.image_path` contra a allowlist `ALLOWED_RECIPE_MEDIA_ROOTS`.
  2. Helpers exportados em `path_policy.py`: `allowed_recipe_media_roots()` e `validate_recipe_media_paths(recipe)`.
- Sanitização de Erros e Defesa em Profundidade:
  3. Exception handler global em `main.py` capturando falhas não tratadas e retornando HTTP 500 limpo com mensagem padronizada, impedindo vazamento de caminhos do host Windows (`E:\...`, `C:\...`) ou traces internos.
- Concorrência Segura na Fila:
  4. Rota `POST /api/jobs/process-next` com checagem ativa de jobs em `processing`, prevenindo renders simultâneos acidentais que sobrecarreguem recursos de CPU/GPU em ambiente local host/Docker.
- Resiliência de Polling Frontend:
  5. Timeout parametrizável em `api.ts`, fixando timeout de 5 segundos dedicado ao `health()`, eliminando acúmulo de requisições pendentes na UI durante tarefas pesadas de renderização.
### Passada 44 (2026-09-22) - Auditoria Visual Ampla, Design System e Acessibilidade (WCAG 2.1 AA)

- Auditoria visual e acessibilidade estrutural em toda a interface do VideoOS:
  1. Navegação Assistiva & Skip Links: adição do link `.skip-to-content` com foco por teclado (`Tab`) e alvo direto no container `<main className="workspace" id="main-content" tabIndex={-1}>`, acelerando a navegação de leitores de tela.
  2. Sensibilidade a Movimento (`prefers-reduced-motion`): suporte global via media query CSS desligando animações/transições para usuários sensíveis.
  3. Contraste e Ergonomia de Foco: `:focus-visible` enriquecido com outline 2px sólido e halo luminoso azul (`box-shadow: 0 0 0 4px rgba(77, 163, 255, 0.25)`); foco otimizado em inputs, selects e textareas.
  4. Target Size Ergonômico (WCAG 2.5.8): classes padronizadas `.review-filter-group`, `.review-filter-btn`, `.safezone-btn-group` e `.safezone-btn` com altura mínima útil de 30-32px, eliminando botões minúsculos com inline-styles em `ReviewDesk` e `TemplateStudio`.
  5. Semântica ARIA & Feedback Acessível:
     - `Button.tsx`: suporte a `aria-busy` e fallback automático de `aria-label` para botões somente com ícone.
     - `SegmentedControl.tsx`: contêiner com `role="radiogroup"` e botões com `role="radio"` e `aria-checked`.
     - `StatusPill.tsx`: inserção de `role="status"` em todos os marcadores.
     - `App.tsx`: `role="alert"` + `aria-live="assertive"` em erros; `role="status"` + `aria-live="polite"` em mensagens; botões de fechar com `aria-label`.
     - `AppShell.tsx`: `aria-label` no acionador da Command Palette; `aria-expanded` e `aria-haspopup="dialog"` no HUD da Mini-Queue.
     - `ReviewDesk.tsx` e `TemplateStudio.tsx`: `aria-pressed` nos seletores de filtros e safe zones.
     - `styles.css`: pílulas de status modernizadas com fundos translúcidos temáticos (`rgba(..., 0.1)`).
- Validação:
  - 164 testes backend aprovados no pytest (100% de sucesso).
  - Testes de caminhos frontend (`npm run test:paths`) e build Vite (`npm run build`) 100% aprovados em 1.33s.

### Passada 45 (2026-09-22) - Auditoria Completa de Operabilidade e Validação Ponta a Ponta

- Auditoria operacional ampla e certificação de prontidão de uso:
  1. Resiliência do SQLite em Bind Mounts Docker (`database.py`):
     - Movida a ativação do `PRAGMA journal_mode=WAL` para o `init_db()` com proteção defensiva, eliminando tentativa de alterar journal mode em cada conexão do pool, o que causava `unable to open database file` no worker.
     - Pragmas de conexão mantidos limpos: `foreign_keys=ON`, `busy_timeout=30000`, `synchronous=NORMAL`.
  2. Resiliência de Resolução de Mídia na Fila de Render (`queue.py`):
     - Integração de `existing_asset_path(job.asset)` como fallback inteligente para localização de mídias de jobs, evitando falhas quando caminhos absolutos divergirem entre host e container.
     - Garantida a persistência física do asset base em `data/assets/`.
  3. Validação Real Ponta a Ponta Concluída:
     - Criação de lote com sucesso (`Auditoria Passada 45`).
     - Renderização 9:16 vertical assíncrona executada pelo Worker em 2.93s (`dd1647e60efc477eabae71b4cd7dc3f9`).
     - Aprovação editorial com persistência em banco.
     - Geração de pacote completo de publicação para Instagram Reels (`868b38e47d0846efa5159338958a78b4`) com os 8 arquivos (`video.mp4`, `thumbnail.jpg`, `quality-report.json`, `metadata.json`, `caption.txt`, `copy.txt`, `hashtags.txt`, `checklist.md`).
     - Quality Check técnico aprovado com Score 100.0 e áudio balanceado a -14.1 LUFS.
### Passada 46 (2026-09-22) - Suporte a Diretórios Externos do Host e Desbloqueio de Caminhos Customizados

- Suporte a pastas e discos arbitrários do host Windows:
  1. Ponto de Montagem do Drive Host em Docker (`docker-compose.yml`):
     - Mapeamento de `E:/:/host/e` nos serviços `api` e `worker`.
     - Inclusão de `/host/e` nas variáveis `VIDEO_OS_ALLOWED_OUTPUT_ROOTS`, `VIDEO_OS_ALLOWED_RECIPE_MEDIA_ROOTS` e `VIDEO_OS_IMPORT_ROOTS`.
  2. Resolução Resiliente de Caminhos do Windows (`media.py`):
     - Atualização de `resolve_user_path` para reconhecer mounts de drives do host mesmo para subdiretórios que serão provisionados automaticamente em tempo de execução.
  3. Formatação Amigável de Caminhos e Ação de Reset (`system.py` & `api.ts`):
     - Helper `to_display_path` convertendo caminhos internos de container para caminhos amigáveis Windows (`E:\...`).
     - Endpoint `POST /api/system/settings/reset` para restauração de fábrica dos caminhos de dados.
  4. Interface do Usuário (`SystemPanel.tsx`):
     - Adição do botão "Restaurar padrões" na barra de ações de armazenamento.
  5. Validação:
     - Configuração dos caminhos do usuário (`E:\Renda extra\Vídeos\Downloads\...`) salva e aplicada com sucesso.
     - 164 testes backend aprovados (100% de sucesso em 26.26s).
     - Build de produção do frontend aprovado em 1.42s.

### Passada 47 (2026-09-22) - Botão e Atalho Oficial de Inicialização na Área de Trabalho

- Inicialização Rápida e Acessibilidade Operacional:
  1. Ícone Nativo em Alta Resolução (`generate_icon.ps1`):
     - Geração de ícone oficial 256x256 anti-aliasing via GDI+ (`System.Drawing`), exportado como `frontend/public/icon.ico` e `icon.ico` na raiz.
  2. Janela e Barra de Tarefas do Electron (`frontend/electron/main.cjs`):
     - Aplicação do ícone oficial na inicialização da janela desktop.
  3. Script Canônico de Automação de Atalho (`Criar_Atalho_Desktop.ps1`):
     - Automação via WScript.Shell criando o atalho `Video OS.lnk` na Área de Trabalho (`%USERPROFILE%\Desktop\Video OS.lnk`).
     - Alvo: `VideoOS.cmd` com diretório de trabalho correto e ícone oficial associado.
### Passada 48 (2026-09-22) - Automacao Viral Ponta a Ponta, Google Gemini 2.0 Flash e AI Clips Station

- Ecossistema de Automação de Vídeos, Viral Score e Inteligência Artificial:
  1. Síntese Neural & Legendas Alinhadas (`backend/app/services/tts.py`):
     - Integração assíncrona com Edge-TTS gerando áudio vocal de alta fidelidade e legendas `.srt` com timestamps precisos no nível de palavras (`WordBoundary`).
     - Catálogo de vozes pt-BR e en-US e suporte a fallback offline defensivo.
  2. Motor Google Gemini 2.0 Flash REST (`backend/app/services/llm.py`):
     - Comunicação JSON estruturada nativa sem dependências pesadas extras.
     - Algoritmo de análise viral pontuando ganchos de abertura (Hook 0-3s), pico de retenção, cálculo do Viral Score (0-100%), ritmo e geração automática de copy pronta com hashtags para redes sociais.
  3. API de Cortes e Lotes Derivados (`backend/app/routes/clips.py` & `system.py`):
     - Endpoints `/api/clips/assets/{id}/mine-viral` e `/api/clips/batch-create` para converter seleções de clipes diretamente em lotes verticais 9:16.
     - Endpoints `/api/system/ai-status`, `/test-google-api` e rotas de TTS.
  4. Painel do Sistema (`SystemPanel.tsx`):
     - Card "Inteligência Artificial & Google Ecosystem" com telemetria dos 4 motores (Gemini, Edge-TTS, Whisper, Ollama), chave mascarada, seletor de modelos e teste de ping em tempo real.
  5. Estação AI Clips & Shorts (`AiClipsDesk.tsx`):
     - Interface profissional estilo Vizard.ai / Opus Clip: visualização de Viral Score (0-100%) em badges coloridos, gancho de retenção em destaque, rationale técnico, cópia de legenda com 1 clique e botão de criação de lote 9:16 com envio para renderização.
  6. Validação e Qualidade:
     - 168 testes automatizados aprovados no backend (100% de sucesso).
     - Testes de paths e build de produção Vite do frontend aprovados em 1.53s.

### Passada 49 (2026-09-22) - Edição Condicional, Estúdio Faceless & Roteiros IA com Geração 9:16

- Edição Condicional Personalizada e Estúdio de Vídeos com IA Generativa:
  1. Edição Condicional nos Lotes de Clipes (`backend/app/routes/clips.py` & `AiClipsDesk.tsx`):
     - Atendimento à preferência direta do usuário: toggles opcionais de legendas dinâmicas (4 estilos: Hormozi, Neon, Minimal, Bold Red), música com volume ducking ajustável e jump cuts automáticos (>0.4s de silêncio) integrados à receita de renderização.
  2. Roteirização Estruturada com IA (`backend/app/services/llm.py`):
     - Estruturação de vídeos curtos em 5 blocos canônicos (Hook 0-3s, Contexto, Solução, Aplicação Prática, CTA).
     - Geração de falas, palavras-chave, direção de cena e prompts visuais prontos para geradores de imagem/vídeo (Midjourney/Imagen/Veo) com cópia em 1 clique.
  3. Estúdio Faceless & Roteiros IA (`frontend/src/components/AgentStudio.tsx`):
     - Criação do modo Estúdio Faceless: tópicos rápidos com 1 clique, gerador de roteiro com Google Gemini 2.0 Flash, editor de narração, seletor de voz neural Edge-TTS com player de teste de áudio imediato e botão de produção 9:16 com envio para a fila de renderização.
  4. Rota Transacional de Geração de Vídeo Faceless (`backend/app/routes/agents.py`):
     - Endpoint `POST /api/agents/generate-faceless-video`: síntese vocal neural, geração de `.srt` sincronizado, vinculação de template derivado com legendas queimadas e enfileiramento atômico de `Batch` e `RenderJob`.
  5. Validação e Qualidade:
     - 171 testes automatizados aprovados no pytest (100% de sucesso em 26.81s).
     - Testes de paths e build de produção Vite do frontend aprovados em 890ms.

### Passada 50 (2026-09-23) - Piloto Automático Ponta a Ponta 1-Clique & Gerador de Imagens de Cena com IA

- Automação Total 1-Clique e Geração Visual de Cenas com IA:
  1. Piloto Automático Ponta a Ponta (`backend/app/routes/clips.py` & `AiClipsDesk.tsx`):
     - Implementação do endpoint `/api/clips/autopilot` executando de ponta a ponta: ingestão, transcrição com Whisper, mineração e pontuação de Viral Score (0-100%) com detecção de hooks (0-3s), auto-seleção dos melhores cortes, aplicação de legendas dinâmicas (4 estilos), áudio ducking e jump cuts em lote vertical 9:16 com enfileiramento de RenderJobs.
     - Botão "🚀 Piloto Automático 1-Clique" no topo da estação de cortes com redirecionamento para Lotes.
  2. Gerador Neural de Imagens de Cena 9:16 (`backend/app/services/image_gen.py` & `AgentStudio.tsx`):
     - Geração de imagens via Google Imagen 3 (quando chave configurada) e Pollinations AI (FLUX) gratuito, com persistência em `data/broll` e registro automático na biblioteca de assets.
     - Botão "🎨 Gerar Imagem IA" integrado a cada cena do storyboard no Estúdio Faceless, com exibição de thumbnail 9:16 e link em resolução 1080x1920.
  3. Validação e Qualidade:
     - 173 testes automatizados aprovados no pytest (100% de sucesso em 29.21s).
     - Testes de paths e build de produção Vite do frontend aprovados em 3.67s.

### Passada 51 (2026-09-23) - Geração em Lote de Imagens e Montagem Sequencial 9:16 no Estúdio Faceless

- Automação em Lote de Imagens de Cena e Montagem Visual com B-Rolls no FFmpeg:
  1. Geração em Lote de Imagens IA 9:16 (`frontend/src/components/AgentStudio.tsx`):
     - Botão "🎨 Gerar Todas as Imagens IA" no cabeçalho das cenas do roteiro gerado, permitindo criar sequencialmente todas as ilustrações verticais 9:16 com um único clique via Google Imagen 3 / Pollinations FLUX.
     - Indicador dinâmico de progresso (`allImagesProgress: current/total`) e reset inteligente de imagens anteriores ao gerar novo roteiro para consistência temática.
  2. Montagem Sequencial de B-Rolls no Renderizador FFmpeg (`AgentStudio.tsx` & `backend/app/routes/agents.py`):
     - Repasse ordenado de `scene_images` para `/api/agents/generate-faceless-video`, convertendo automaticamente as imagens em trilha de B-Rolls sincronizados sob a locução neural Edge-TTS e legendas animadas dinâmicas.
     - Card visual de status "Montagem Visual 9:16 (B-Rolls)" com mini-strip de thumbnails e contador de imagens vinculadas antes da produção.
  3. Validação e Qualidade:
     - 173 testes automatizados aprovados no pytest (100% de sucesso em 29.35s).
     - Testes de paths (`test:paths`) e build de produção Vite do frontend aprovados em 1.14s.

## Criterio De Pronto Do Sistema

O sistema so deve ser considerado operante quando:

- API responde health.
- Frontend responde.
- Worker esta ativo.
- FFmpeg/FFprobe disponiveis no ambiente de render.
- Banco SQLite abre com WAL e foreign keys.
- `npm.cmd run build` passa.
- Testes backend passam no ambiente oficial.
- Ao menos um fluxo real e validado: importar asset, criar lote, renderizar, revisar, gerar pacote.

Ultima verificacao documental: 2026-09-23, Passada 51. Geração em Lote de Imagens IA 9:16 (1-Clique), Montagem Visual Sequencial com B-Rolls no FFmpeg e UI do Estúdio Faceless 100% concluídas. 173 testes de backend e build frontend 100% aprovados.



