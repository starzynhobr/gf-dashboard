# GF Dashboard Controller

MVP desktop local para controle de farm em Grand Fantasia.

## Arquitetura inicial

- Python para domínio, aplicação e persistência local;
- PySide6/QWebEngine como shell Windows;
- React + TypeScript + Vite + Tailwind como única interface;
- Qt WebChannel por um contrato `AppGateway`;
- SQLite como fonte de verdade local, com migrations SQL, checksum e backups verificados.

Supabase, autenticação, API HTTP e distribuição no navegador não fazem parte do MVP atual.

## Regras e planejamento

Antes de implementar, leia `AGENTS.md`. O diretório `vault/` é o vault do Obsidian que mantém fonte da verdade, ADRs, modelo de dados, roadmap, backlog, kanban e plano mestre; mudanças relevantes no código devem manter esses documentos alinhados.

## Desenvolvimento

```powershell
uv sync --dev
npm --prefix frontend install
npm --prefix frontend run build
uv run gf-dashboard
```

Para trabalhar com hot reload:

```powershell
npm --prefix frontend run dev
$env:GF_DASHBOARD_DEV_URL = "http://127.0.0.1:5173"
uv run gf-dashboard
```

## Qualidade

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv lock --check
npm --prefix frontend run test
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

## Dados locais

Na inicialização, o aplicativo prepara o banco SQLite em `QStandardPaths.AppLocalDataLocation`, dentro de `data/gf-dashboard.sqlite3`. Esse caminho é separado da instalação e do repositório; migrations pendentes criam um backup verificado antes de alterar um banco existente.
