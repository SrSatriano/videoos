# Histórico de Atualizações do Sistema (VideoOS)

Este documento registra a evolução cronológica do **VideoOS**, desde sua concepção como um MVP de edição local-first até o desenvolvimento do estúdio de verificação de qualidade de publicação recente.

> [!IMPORTANT]
> **REGRA DE ATUALIZAÇÃO**: De acordo com a Seção 5 de [Regras_Gerais.md](file:///e:/Projetos/Privado/Sistema%20de%20edição/Regras_Gerais.md), toda e qualquer modificação, adição de funcionalidade ou correção feita no código-fonte do sistema **DEVE** ser gravada e documentada neste histórico logo após sua finalização.

---

## [Fase 1] Fundação do Core e MVP (Meados de Maio de 2026)
* **Arquitetura Base**: Implementação da estrutura de microsserviços locais unificando o Backend (FastAPI), Banco de Dados (SQLite) e Frontend (React + Vite + TypeScript) orquestrados localmente via Docker Compose.
* **Pipeline de Renderização**: Criação do Worker assíncrono em Python que lê jobs da fila, executa comandos FFmpeg e gera renders verticais 9:16 aplicando templates de vídeo em lote.
* **Estrutura Soberana de Pastas**: Organização física de diretórios locais sob `data/`:
  - `data/incoming`: Ingestão temporária de arquivos brutos.
  - `data/assets`: Cópia local protegida dos vídeos importados.
  - `data/thumbnails`: Miniaturas rápidas extraídas de assets e renders.
  - `data/renders`: Pasta final de exportação de vídeos processados.
  - `data/publish-packages`: Pacotes prontos (vídeo + capa + checklist + legenda) prontos para postagem.
  - `data/db`: Banco SQLite local.
* **Frontend Primitivo**: Telas iniciais de biblioteca de assets, fila de renderização (Batch Queue) e editor de receitas visuais (Templates).

---

## [Fase 2] Estabilidade Local e Scripts de Suporte (Final de Maio de 2026)
* **Modo SQLite WAL (Write-Ahead Logging)**: Configuração do banco de dados relacional para rodar no modo WAL, permitindo leituras simultâneas e gravação de alta concorrência entre as chamadas da API do FastAPI e o Worker de renderização assíncrona.
* **Segurança e Validação de Ingestão**: Implementação de verificação de integridade e duplicidade de arquivos de mídia baseado em Hashing SHA-256 no backend, evitando importar duas vezes o mesmo arquivo.
* **Tratamento de Paths no Windows**: Correção de bugs de parsing de caminhos e manipulação de arquivos de vídeo que continham caracteres especiais ou acentuação em português (ex.: caminhos com "edição", "gravação", etc.).
* **Script Administrativo do Windows**: Criação do script `VideoOS.ps1` (e atalho `VideoOS.cmd`) para automatizar a manutenção de ambiente no Windows:
  - Resolução dinâmica de portas ocupadas no host (fallback automático de portas).
  - Parada forçada de instâncias fantasmas de Node/Python executando no diretório.
  - Inicialização do Docker Desktop e WSL2 caso estejam desligados no Windows do usuário.
* **Cobertura de Testes**: Implementação de suíte de testes com `pytest` cobrindo receitas FFmpeg, validação de limites de corte e filtros drawtext.

---

## [Fase 3] Quality Check, Safe Zone Studio e Biblioteca Inteligente (Atualização Recente - Junho de 2026)
* **Serviço de Quality Check (QC) de Renders**:
  - Endpoint `POST /api/quality/renders/{id}` e serviço `quality.py` para auditar a conformidade de arquivos renderizados.
  - Regras de qualidade específicas e avisos customizados para as plataformas **Instagram Reels**, **TikTok** e **YouTube Shorts** baseados em resolução, proporção (aspect ratio), duração, taxa de quadros (FPS) e tamanho de arquivo (MB).
* **Safe Zone Overlay Studio**:
  - Implementação na tela de revisão (`ReviewDesk.tsx`) de camadas visuais de overlay transparentes para as 3 redes e uma guia universal conservadora.
  - Permite ao editor visualizar exatamente quais partes da imagem serão cortadas ou cobertas pela interface de botões (curtidas, comentários, áudio) e avatar das plataformas sociais.
* **Smart Bins na Biblioteca**:
  - Classificação inteligente automática de vídeos na barra lateral da biblioteca (`AssetLibrary.tsx`):
    - *Todos*: Lista geral de mídias.
    - *Verticais*: Mídias com orientação 9:16 ou verticais similares.
    - *Prontos para Shorts*: Vídeos verticais de curta duração.
    - *Até 60s*: Vídeos ideais para Reels/Shorts tradicionais.
    - *Longos*: Vídeos que excedem o limite de corte rápido.
    - *Com Proxy*: Vídeos que já possuem versão de visualização rápida 720p gerada.
    - *Atenção*: Vídeos horizontais ou com metadados corrompidos/incompletos.
  - Seleção ágil em lote com base no Bin ativo para criação instantânea de fila de renderização.
* **Ingestão Otimizada de Proxies**:
  - Geração automática de proxies em 720p para vídeos muito pesados em 4K/1080p, acelerando a resposta de preview no navegador sem engasgos de processamento.
* **Detecção Automática de Cenas**:
  - Integração inicial com PySceneDetect para detecção de cortes secos e marcação automática de frames (Scene Markers) no banco de dados.
* **Aceleração por Hardware e Fallback Inteligente (FFmpeg)**:
  - Implementação de checagem dinâmica de codecs de vídeo disponíveis (`available_video_encoders()`) via `ffmpeg -encoders` no backend (`media.py`).
  - Fallback automático e transparente de codecs no `render.py`: se o usuário configurar aceleração NVENC (Nvidia) mas o computador local não possuir o hardware compatível, o sistema reverte automaticamente para o processamento em CPU (`libx264`), evitando falhas na renderização.
  - Correção de parâmetros específicos de codificação de GPU (traduzindo `-crf` para `-cq:v` e mapeando presets de velocidade da CPU para GPU), permitindo o uso seguro de aceleração por hardware no Windows.
* **Aviso Informativo de FPS no Quality Check**:
  - Ajuste de sensibilidade no `quality.py`: quando o FPS de um render não é diretamente detectado nos metadados (devido à taxa de quadros variável típica de celulares), o Reels agora retorna um aviso informativo (`info`) útil em vez de passar silenciosamente ou forçar um erro.
* **Painel de Auditoria no Frontend (SystemPanel.tsx)**:
  - Implementação da busca dinâmica dos logs de auditoria (`AuditEvent`) da API no frontend (`api.ts` e `App.tsx`).
  - Criação de uma tabela visual organizada no painel de integridade (`SystemPanel.tsx`) para exibir logs operacionais do sistema com data e hora local, tipo do evento, tipo da entidade, hash da ID da entidade e a mensagem do log, proporcionando observabilidade total e local-first do VideoOS.

---

## [Fase 4] Auditoria de Integridade Física e Decodificabilidade (Junho de 2026)
* **Verificação de Integridade de Mídias (Backend)**:
  - Criação da rotina `verify_media_integrity()` em `backend/app/services/quality.py`.
  - Valida presença física dos arquivos no disco rígido local.
  - Verifica legibilidade do contêiner e dos metadados através do `ffprobe`.
  - Executa uma decodificação rápida de teste (5 primeiros frames de vídeo) via `ffmpeg` para garantir que o arquivo não está corrompido.
  - Gravação automática de eventos de auditoria (`AuditEvent`) no banco de dados SQLite para monitoramento contínuo.
* **Endpoints de API de Integridade**:
  - Exposição de `POST /api/quality/assets/{asset_id}/integrity` e `POST /api/quality/renders/{rendered_id}/integrity` em `backend/app/routes/quality.py`.
* **Integração no Frontend**:
  - Atualização de `frontend/src/api.ts` e `frontend/src/types.ts` com o tipo `IntegrityCheckResult` e novos endpoints.
  - Biblioteca de Mídias (`AssetLibrary.tsx`): Adicionado botão "Auditar" e indicador visual de integridade para cada vídeo bruto. Se exatamente um vídeo for selecionado, o painel do inspetor lateral exibe os detalhes completos da auditoria técnica.
  - Revisão de Vídeos Renders (`ReviewDesk.tsx`): Integração da rotina de auditoria que roda em segundo plano ao abrir a tela, marcando renders validados como "✓ Decodificável" ou apontando caminhos ausentes/corrupções de codificação.
* **Testes de Cobertura e Robustez**:
  - Criação de suíte de testes unitários `backend/tests/test_integrity.py` cobrindo cenários de arquivo ausente, metadados corrompidos, decodificação bem-sucedida e decodificação falha (FFmpeg).

---

## [Fase 5] Renovação Visual Premium e Otimização de UX (Junho de 2026)
* **Tipografia e Fontes Premium**:
  - Integração do Google Fonts importando as fontes **Plus Jakarta Sans** (para textos e formulários) e **Outfit** (para números de métricas, contadores e títulos principais), trazendo um acabamento altamente refinado e legível de cockpit profissional.
* **Estética Glassmorphism**:
  - Aplicação de `backdrop-filter: blur(20px)` e gradientes lineares translúcidos nos painéis principais (`.panel`) e cartões de métricas (`.metric`), com bordas finas semi-transparentes e sombras internas (`inset box-shadow`) para simulação realista de relevo físico e vidro fosco.
* **Micro-Animações e Efeitos Hover**:
  - Animação de elevação física e brilho sutil com scale 3D ao passar o cursor sobre linhas de mídias (`.asset-row`), templates (`.template-row`), abas e cards rápidos (`.quick-card`).
  - Efeito de deslocamento lateral (`translateX(5px)`) ao passar o cursor nos itens de navegação da barra lateral (`.nav-item`).
  - Anéis de foco e transições de cor suaves com sombra em todos os campos de texto, buscas, textareas e seletores.
* **StatusPills & Botões Inteligentes**:
  - Modernização das pílulas de status (`status-pill`) com bordas reforçadas e sombras brilhantes coloridas em HSL de acordo com a gravidade do status (sucesso, aviso, erro).
  - Implementação do suporte a `loading` no componente `Button.tsx`, integrando um spinner circular SVG animado e desabilitando cliques extras de forma automática para garantir resiliência e estabilidade nas ações de renderização e importação.
  - **Unificação de Controles e Loader nas Telas**: Substituímos todos os botões `<button>` HTML nativos pelo componente unificado `<Button>` nas telas **MassLoader** (`CaptureDesk.tsx`), **Brand Kit** (`BrandKitStudio.tsx`), **AI Clips** (`AiClipsDesk.tsx`), **Caption Lab** (`TranscriptionDesk.tsx`), **Fila de Lote** (`BatchQueue.tsx`), **Template Studio** (`TemplateStudio.tsx`), **Music Lab** (`MusicLab.tsx`) e **Calendário** (`CalendarDesk.tsx`), mapeando estados de carregamento independentes para operações de transcrição, download em massa, geração de SRT/VTT, salvamento manual, detecção de vícios, geração de briefs de áudio e criação de cronogramas semanais, bem como suporte a botões apenas com ícone (icon-only).
  - **Identidade Premium para Stems**: Estilização da classe `.stem-card` no `styles.css` utilizando desfoque glassmorphic, cores de bordas alinhadas e micro-escala com elevação de cursor de acordo com as diretrizes do cockpit premium.

---

## [Fase 6] Auditoria e Robustez no MassLoader (Junho de 2026)
* **Extração Ativa de Logs de Erro do Downloader**:
  - Implementação da classe `MyLogger` para capturar warnings e erros do subprocesso do `yt-dlp` em tempo real, resolvendo o problema das falhas de download silenciosas devido à flag `"ignoreerrors": True`.
  - Exibição de relatórios detalhados com lista de erros estruturada na barra de resultados do frontend.
* **Mecanismo de Importação de Cookies de Navegador**:
  - Adicionada a opção de passar `cookies_from_browser` para que o downloader importe os cookies ativos de sessões de navegadores instalados no host (Chrome, Edge, Firefox, Brave).
  - Auxilia o desvio de bloqueios HTTP 401/403 e a restrição de download de perfis ou Reels do Instagram.
  - Implementado fallback automático com aviso caso a extração de cookies do navegador falhe por travamento ou criptografia.
* **Resiliência Inteligente de Formatos (Verificação de FFmpeg)**:
  - Verificação dinâmica da presença de `ffmpeg` no PATH local.
  - **FFmpeg ausente (Host Local)**: O downloader chaveia automaticamente o formato para `"best[ext=mp4]/best"`, garantindo o download de streams com áudio e vídeo pré-mesclados (evitando que o vídeo fique sem som pela falta de fusão de faixas independentes).
  - **FFmpeg presente (Container/WSL)**: Mantido `"format": "bv*+ba/best"` para priorizar a qualidade máxima dos streams e mesclá-los localmente.
* **Ajuste de Padrões e Entrada Tolerante**:
  - Correção do nome dos arquivos gerados (`outtmpl`) de `uploader|canal` para a sintaxe correta `uploader,channel,uploader_id|unknown` usando vírgula para fallbacks e pipe para valor padrão.
  - Correção e tolerância a erros no parseador de URLs, permitindo o auto-ajuste de caminhos colados com prefixo `www.` para `https://www.`.

---

* **Passada 07 - Cookies.txt seguro para Docker/Windows**:
  - A importacao direta de cookies de Chrome/Edge via `cookies_from_browser` deixou de ser tratada como caminho padrao quando o backend roda em container Linux, evitando a busca incorreta por perfis como `/root/.config/microsoft-edge`.
  - Criado `POST /api/social/cookies` para upload controlado de `cookies.txt`/`.cookies` em `data/incoming/massloader-cookies`.
  - `CaptureDesk.tsx` passou a oferecer seletor de `cookies.txt` e ocultar navegador local quando a API retorna `browser_cookie_import_supported=false`.
  - O MassLoader agora retorna erro 422 claro orientando `cookies.txt`, em vez de tentar continuar sem cookies e produzir falha confusa.

* **Passada 08 - yt-dlp atualizado e runtime MassLoader alinhado**:
  - `backend/requirements.txt` atualizou o pin do `yt-dlp` para `2026.6.9`, correspondente a release oficial `2026.06.09`.
  - `/api/social/instagram/status` passou a expor `yt_dlp_version`, permitindo diagnosticar rapidamente quando o extractor esta defasado.
  - Falhas de perfil Instagram (`instagram:user`, `Unable to extract data` ou extractor marcado como quebrado) agora mantem o erro real e adicionam orientacao para rebuild/update, `cookies.txt` e URLs diretas de Reels/posts autorizados.
  - `CaptureDesk.tsx` passou a exibir a versao do `yt-dlp` no bloco de regras.
  - Runtime Docker foi realinhado: API e worker recriados com `yt-dlp 2026.06.09`; web recriado para sair de env/porta antigos e servir `VITE_API_URL=http://127.0.0.1:8010`.
  - Validacao: 68 testes backend em host e Docker, `compileall`, build frontend, API `8010` healthy, web `5174` healthy e worker ativo.

---

## [Fase 7] Auditoria de Pré-inicialização (Pre-Flight Audit) no Launcher (Junho de 2026)
* **Pre-Flight Audit Visual**:
  - Implementação do painel `Pre-Flight Audit` que executa automaticamente no início do script `VideoOS.ps1`.
  - Verifica se os arquivos essenciais (`docker-compose.yml`, `backend/requirements.txt`, `backend/app/main.py`, `frontend/package.json`, `frontend/src/App.tsx`) estão presentes e com tamanho válido (maior que 0 bytes).
  - Compara dinamicamente timestamps de dependências Python (`backend/requirements.txt` vs `.venv/pyvenv.cfg`) e Node (`frontend/package.json` / `frontend/package-lock.json` vs `frontend/node_modules`) para determinar se precisam de atualização.
  - Testa se os pacotes `fastapi` (no Python) e `react` e `vite` (no Node) estão fisicamente instalados para garantir integridade do ambiente antes de abrir o sistema.
* **Centralização da Preparação do Host**:
  - Refatorado o fluxo de inicialização para que `Ensure-PythonEnv` e `Ensure-FrontendEnv` executem logo após o Pre-Flight Audit na etapa `[1/7]`. Isso garante que as dependências do host (incluindo o Electron local) estejam sempre atualizadas tanto no modo Docker quanto no modo Local.
* **Monitoramento de Crash do Electron e Fallback para Navegador**:
  - Adicionado monitoramento de processo por 2 segundos ao abrir o aplicativo local via Electron.
  - Caso o Electron termine inesperadamente (sinalizando falhas silenciosas de dependências locais do SO), o launcher detecta e aciona automaticamente o fallback para abrir o sistema em modo aplicativo usando o Microsoft Edge, garantindo que o usuário consiga acessar a interface sem travamentos.
* **Monitoramento e Detecção de Estado do Docker**:
  - Inspeciona via `docker inspect` as datas de criação das imagens Docker (`sistemadeedio-api`, `sistemadeedio-web`, `sistemadeedio-worker`) e compara com a data dos arquivos fontes para rotulá-las como `NOVA`, `DESATUALIZADA` ou `ATUALIZADA`.
  - Refatorado o `Run-DockerMode` para validar o estado das imagens **antes** de pular a inicialização no caso de uma stack já existente estar ativa. Caso qualquer imagem esteja desatualizada, o script força o build e a reinicialização dos contêineres obsoletos, garantindo que o usuário visualize sempre a versão mais recente do código e dos componentes visuais.

* **Passada 09 - Executor alinhado a atualizacao correta**:
  - `VideoOS.ps1` passou a inicializar o runtime a partir do `.env`, com defaults oficiais para API `8010`, web `5174`, `VITE_API_URL=http://127.0.0.1:8010` e CORS coerente.
  - Antes de reaproveitar uma stack Docker viva, o executor agora valida portas, `VITE_API_URL` servido/inspecionado no container web e frescor dos containers em relacao aos arquivos criticos.
  - Stack defasada passa a ser recriada com `docker compose up -d --remove-orphans --force-recreate`, evitando abrir UI antiga.
  - Adicionado `VIDEO_OS_NO_OPEN=1` para smoke test sem abrir Electron/Edge.
  - Validacao: parser PowerShell OK, `docker compose config --quiet` OK, executor reaproveitou a stack correta em `http://127.0.0.1:5174`, API 200 em `8010`, web 200 em `5174` e `/src/api.ts` confirmou `http://127.0.0.1:8010`.
* **Passada 10 - Logs Chromium/Electron em arquivo**:
  - Diagnosticado o log `Network service crashed or was terminated, restarting service` como mensagem interna do runtime Chromium/Electron/Edge, sem queda da stack Docker.
  - `VideoOS.ps1` passou a redirecionar stdout/stderr do Electron para `data/logs/electron.desktop.log` e `data/logs/electron.desktop.err.log`.
  - Se o Electron fechar rapidamente, o executor mostra o caminho do log e as ultimas linhas do erro antes de usar fallback para Edge.
  - Validacao: parser PowerShell OK, `electron.cmd --version` com redirecionamento retornou `v42.4.1`, `docker compose config --quiet` OK, API/web 200 e Docker healthy.

---

## [Fase 8] Controle Dinâmico de Caminhos e Destinos de Mídia (Junho de 2026)
* **Customização de Pastas no Host**:
  - Implementada a leitura de um arquivo local de configurações (`data/settings.json`) no `backend/app/config.py` para reatribuir dinamicamente os caminhos principais em tempo de execução:
    - **Downloads (MassLoader)**: `INCOMING_DIR`
    - **Biblioteca**: `ASSETS_DIR`
    - **Vídeos Renderizados**: `RENDERS_DIR`
    - **Pacotes de Publicação**: `PUBLISH_PACKAGES_DIR`
  - Criada rotina para garantir a criação física dos diretórios no host (`ensure_data_dirs()`) assim que forem alterados.
* **Endpoints de API de Configuração**:
  - Adicionados os endpoints `GET /api/system/settings` e `POST /api/system/settings` no backend (`backend/app/routes/system.py`) para ler e gravar as preferências de pastas no arquivo `data/settings.json` em tempo de execução.
* **Painel Gráfico de Configuração no Cockpit**:
  - Criação da seção **"Caminhos e Destinos"** na tela de integridade (`SystemPanel.tsx`).
  - Permite visualizar, digitar caminhos arbitrários ou selecionar pastas do sistema local graficamente clicando em um botão nativo de seleção de pasta (`FolderOpen` usando as caixas de diálogo do Electron no Windows).

---

## [Fase 9] Saneamento Sistêmico, Hardening de Segurança e Command Palette (Agosto de 2026 - Passada 33)
* **Saneamento de Arquivos Sombra**:
  - Remoção completa de 78 arquivos sombra/órfãos (`*(1)*`) gerados por conflitos de sincronização na nuvem nos diretórios do backend, frontend e documentação.
  - Correção de conflitos que quebravam compilações do TypeScript (`tsc`) e testes do `pytest`.
* **Hardening de Segurança do Endpoint de Mídias (SEC-01)**:
  - Substituição da montagem padrão de arquivos estáticos por `SafeStaticFiles` em `backend/app/main.py`.
  - Bloqueio explícito com HTTP 403 Forbidden para requisições a arquivos de banco de dados (`/db/*`), cookies de sessão (`/massloader-cookies/*`), logs internos (`/logs/*`) e configurações (`settings.json`).
* **Hardening da Infraestrutura Docker (SEC-02)**:
  - Remoção da montagem irrestrita da unidade C: do host (`- "C:/:/host/c:ro"`) nos serviços `api` e `worker` do `docker-compose.yml`.
* **Command Palette Global (`Ctrl+K` / `Cmd+K`)**:
  - Implementação do componente `CommandPalette.tsx` no frontend.
  - Disponibilização de busca rápida com teclado para as 17 telas do sistema e atalhos diretos para operações frequentes (backup do SQLite, recarga de dados, etc.).
* **Validação de Qualidade e Integridade**:
  - 126 testes de backend executados e aprovados com 100% de sucesso no `pytest`.
  - Build do frontend aprovado (`npm run build`) com TypeScript e Vite.
  - Testes de caminhos do frontend validados (`npm run test:paths`).

---

## [Fase 10 / Passada 34] - 2026-08-19

### Adicionado / Melhorado
* **Quality Check em Segundo Plano para Lotes**:
  - Endpoint `POST /api/quality/batches/{batch_id}` e `GET /api/quality/batches/{batch_id}` para processamento de conformidade técnica agregada de todo o lote.
  - Integração no `BatchQueue.tsx` com botão de execução rápida (`ShieldCheck`), contagem de aprovações/erros e badge dinâmico de conformidade técnica.
* **Audio Ducking com Fades Parametrizados**:
  - Suporte a `fade_in` e `fade_out` no construtor de filtros FFmpeg (`build_music_audio_filter_complex`).
  - Controles de Fade In e Fade Out (em segundos) adicionados no bloco de áudio do `TemplateStudio.tsx`.
* **Validação Integral**:
  - 128 testes de backend executados e aprovados no `pytest` (100% sucesso).
  - Build do frontend `npm run build` (`tsc && vite build`) concluído com 0 erros em 1.20s.
  - Testes de caminhos `npm run test:paths` validados com sucesso.

---

## [Fase 11 / Passada 35] - 2026-08-19

### Adicionado / Melhorado
* **Transcrição com Word Timestamps e Segmentos**:
  - Suporte a detecção in-process de `faster-whisper` e extração de `words_json` (`start`, `end`, `word`, `probability`) e `segments_json`.
  - Novos endpoints: `PATCH /api/transcriptions/{transcript_id}` para edição e `GET /api/transcriptions/{transcript_id}/subtitles` para download direto de legendas SRT/VTT.
* **Timeline no Caption Lab (`TranscriptionDesk.tsx`)**:
  - Exibição de blocos temporais com timestamps (`[start -> end]`) e contagem de palavras sincronizadas.
* **Gestão e Expurgo de Logs (`data/logs/`)**:
  - Endpoints `GET /api/system/logs` e `POST /api/system/logs/purge` para consulta e limpeza periódica de disco.
* **Validação Integral**:
  - 131 testes de backend executados e aprovados no `pytest` (100% sucesso).
  - Build do frontend aprovado (`tsc && vite build`) em 1.66s.
  - Testes de caminhos validados com sucesso (`npm run test:paths`).

---

## [Fase 12 / Passada 36] - 2026-08-19

### Adicionado / Melhorado
* **Legendas Animadas estilo Karaokê (ASS)**:
  - Implementação de `build_ass_karaoke` com tags de duração centesimal `{\k<cs>}` por palavra.
  - Suporte ao filtro `ass=` no motor FFmpeg em `backend/app/services/render.py` quando o arquivo de legenda possui extensão `.ass`.
  - Endpoint `GET /api/transcriptions/{transcript_id}/subtitles?format=ass` para exportação direta em formato Advanced SubStation Alpha.
* **Storage Analytics Detalhado**:
  - Endpoint `GET /api/system/health` enriquecido com detalhamento de volume de bytes por pasta em `data/` (`assets/`, `renders/`, `proxies/`, `thumbnails/`, `publish-packages/`, `db/`, `logs/` e `total_bytes`).
  - Exibição de estatísticas de armazenamento no `SystemPanel.tsx`.
* **Validação Integral**:
  - 131 testes de backend executados e aprovados no `pytest` (100% sucesso).
  - Build do frontend `npm run build` aprovado em 1.79s.
  - Testes de caminhos `npm run test:paths` validados com sucesso.

---

## [Fase 13 / Passada 37] - 2026-08-19

### Adicionado / Melhorado
* **Presets de Karaokê (ASS)**:
  - Dicionário de estilos pré-configurados: Hormozi (amarelo), Neon Cyber (ciano), Minimalista (branco) e Bold Red (vermelho).
  - Seletor de estilo no `TemplateStudio.tsx` com preview integrado.
* **Silence Remover / Auto Jump-Cut**:
  - Detecção automática de pausas com FFmpeg `silencedetect` em `silence.py`.
  - Endpoint `POST /api/editor/assets/{id}/detect-silence` e toggle no `TemplateStudio.tsx`.
* **Ação Segura "Abrir no Explorer"**:
  - Endpoint `POST /api/system/open-path` com sandbox de diretórios permitidos e botão `FolderOpen` no histórico de lotes em `BatchQueue.tsx`.
* **Layouts de Produção**:
  - Suporte a layouts `single`, `split_vertical` e `pip` no `RenderRecipe` e no formulário do template.
* **Validação Integral**:
  - 135 testes de backend executados e aprovados no `pytest` (100% sucesso).
  - Build do frontend `npm run build` aprovado em 1.08s.
  - Testes de caminhos `npm run test:paths` validados com sucesso.

---

## [Fase 14 / Passada 38] - 2026-08-19

### Adicionado / Melhorado
* **Aceleração por Hardware GPU com Auto-Fallback**:
  - Funções `available_hardware_encoders` e `resolve_render_codec` com suporte nativo a NVENC, QSV e AMF e fallback transparente para `libx264`.
* **Auto B-Roll Matcher por Transcrição**:
  - Algoritmo de matching semântico e por tags em `broll.py` e novo endpoint `POST /api/broll/auto-match`.
* **Media Pool Alternável (Grade / Lista)**:
  - Alternador visual em `AssetLibrary.tsx` com visualização em grade responsiva e tabela compacta.
* **Validação Integral**:
  - 139 testes de backend executados e aprovados no `pytest` (100% sucesso).
  - Build do frontend `npm run build` aprovado em 1.62s.
  - Testes de caminhos `npm run test:paths` validados com sucesso.

---

## [Fase 15 / Passada 39] - 2026-08-19

### Adicionado / Melhorado
* **Music Lab com Separação de Stems (Vocais / Instrumental)**:
  - Funções `demucs_status` e `separate_audio_stems` em `audio_lab.py` com detecção de Demucs CLI e fallback DSP FFmpeg.
  - Novo endpoint `POST /api/music/separate-stems` e método integrado no frontend.
* **Structured Outputs com Pydantic para IA Local**:
  - Modelos formais `AgentRunResult` e `AgentItem` em `llm.py` garantindo validação estrita e esquema robusto para Ollama.
* **Validação Integral**:
  - 144 testes de backend executados e aprovados no `pytest` (100% sucesso).
  - Build do frontend `npm run build` aprovado em 1.31s.
  - Testes de caminhos `npm run test:paths` validados com sucesso.







