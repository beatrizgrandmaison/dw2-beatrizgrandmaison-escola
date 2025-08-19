# REPORT

Projeto: Gestão Escolar — Turmas e Matrículas

## Arquitetura
- FastAPI backend (SQLite via SQLAlchemy)
- Frontend estático (HTML/CSS/JS) comunicando via fetch

Fluxo: Browser -> fetch -> FastAPI endpoints -> SQLAlchemy ORM -> SQLite DB -> resposta JSON

## Peculiaridades implementadas
- Validações custom front+back (faixa etária >=5 anos) — item 2
- Seed com dados plausíveis (20 nomes) — item 7
- Export não implementado ainda; poderia ser adicionado — (planejado)

## Como rodar
1. Backend
- criar venv: python -m venv .venv; .\.venv\Scripts\Activate.ps1
- instalar: pip install -r backend\requirements.txt
- rodar seed: python backend\seed.py
- iniciar: uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000

2. Frontend
- abrir `frontend/index.html` no navegador ou servir com `npx http-server frontend`

