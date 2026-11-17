# VideoOS — edição de vídeos curtos em massa

[![CI](https://github.com/SrSatriano/videoos/actions/workflows/ci.yml/badge.svg)](https://github.com/SrSatriano/videoos/actions/workflows/ci.yml)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React_19-Vite-61DAFB?logo=react&logoColor=black)
![FFmpeg](https://img.shields.io/badge/FFmpeg-render-007808?logo=ffmpeg)
![testes](https://img.shields.io/badge/backend-173_testes-22c55e)

Sistema local-first para importar videos curtos verticais, aplicar templates de edicao em lote, revisar renders e gerar pacotes de publicacao manual para Instagram Reels, TikTok e YouTube Shorts.

## Stack

- Backend: FastAPI, SQLite WAL, SQLAlchemy, Pydantic.
- Worker: Python + FFmpeg/FFprobe.
- Frontend: React, Vite, TypeScript.
- Desktop opcional: Electron.
- Execucao recomendada: Docker Compose no Windows.

## Estado Validado

Validado em 2026-08-19 (Passada 33):

- Backend host: 126 testes passaram via `pytest` com 100% de sucesso.
- Frontend host e Docker: `npm run build` (`tsc && vite build`) e `npm run test:paths` passaram.
- Frontend audit: `npm audit` retornou 0 vulnerabilidades.
- Segurança: Endpoint `/media` protegido com `SafeStaticFiles` contra vazamento de banco/cookies/logs; mount irrestrito `C:/` removido do Docker Compose.
- Produtividade: Command Palette global disponível em todas as 17 telas via `Ctrl+K` / `Cmd+K`.
- Stack Docker: API (`8010`), web (`5174`) e worker ativos e healthy; SQLite em modo WAL; FFmpeg/FFprobe operantes.

## Como Rodar

Opcao recomendada:

```powershell
.\VideoOS.cmd
```

Ou manualmente:

```powershell
docker compose up -d --remove-orphans
```

Com o `.env` atual:

- Frontend: http://127.0.0.1:5174
- API docs: http://127.0.0.1:8010/docs
- Health: http://127.0.0.1:8010/api/system/health

Para parar:

```powershell
docker compose stop
```

## Ambiente Local

Backend com Python 3.12 em uma `.venv` na raiz do projeto.

Backend:

```powershell
.\.venv\Scripts\pytest.exe
```

Frontend:

```powershell
cd frontend
npm install
npm run build
```

O frontend usa cache npm local em `../.npm-cache`, configurado em `frontend/.npmrc`.

## Pastas De Dados

- `data/incoming`: arquivos recebidos/importados.
- `data/assets`: copias controladas dos videos originais.
- `data/thumbnails`: thumbnails de assets e renders.
- `data/renders`: videos renderizados.
- `data/publish-packages`: pacotes prontos para postagem manual (v1 e v2).
- `data/db`: banco SQLite (WAL) e backups protegidos.
- `data/logs`: logs de execução e auditoria.

## Fluxo Principal

1. Importar videos da pasta `Planejamento` ou de outra pasta permitida.
2. Criar ou ajustar um template vertical 9:16 com preview dinâmico.
3. Criar um lote com um ou mais assets, variacoes e verificação prévia de espaço em disco.
4. Worker renderiza os jobs usando FFmpeg com amostragem de pico RSS.
5. Revisar, rodar Quality Check técnico com Safe Zones e aprovar ou reprovar os renders.
6. Gerar pacote de publicacao manual com video, thumbnail, legenda, hashtags, checklist e metadata (`quality-report.json`).

## Seguranca Operacional

O sistema nao automatiza login nem postagem em redes sociais. Ele prepara arquivos e checklist para publicacao manual, evitando automacoes frageis de browser e reduzindo risco de bloqueio de conta.

Por padrao, a importacao ampla esta desligada (`VIDEO_OS_ALLOW_ANY_IMPORT_PATH=0`), a API atende apenas em loopback (`127.0.0.1`), arquivos sensíveis de banco/cookies são bloqueados no `/media` e o contêiner opera restrito ao workspace do projeto.



## Autor

Matheus Rodrigues Satriano — [github.com/SrSatriano](https://github.com/SrSatriano)
