# SimuCESPE - Painel de Simulados INSS

Projeto de ingestao e simulados CEBRASPE para provas do INSS.

## Ambiente local

Use Python 3.12, conforme `.python-version`. Crie e ative o ambiente virtual:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Se `py` nao estiver disponivel, use o Python instalado na maquina:

```powershell
python -m venv .venv
```

## Validacao

Rodar testes:

```powershell
python -m unittest discover -s tests
```

Validar um par prova/gabarito:

```powershell
python scripts\validate_pair.py --pair-key cespe-cebraspe-2026-inss-tecnico-do-seguro-social-curso-de-formacao-4-turma --summary-only
```

Ou, apos instalar o pacote:

```powershell
simucespe-validate-pair --pair-key cespe-cebraspe-2026-inss-tecnico-do-seguro-social-curso-de-formacao-4-turma --summary-only
```

Ingerir todos os pares descobertos e gerar JSONs em `data/parsed/`:

```powershell
simucespe-ingest-all
```

Subir a API local:

```powershell
cd C:\Users\kant-sdev\Desktop\Analu\simucespe
.\.venv\Scripts\Activate.ps1
simucespe-api --reload
```

Depois acesse:

```text
http://127.0.0.1:8000/docs
```

Para encerrar o servidor, volte ao terminal em que ele esta rodando e pressione
`Ctrl+C`.

## Docker

Build da imagem:

```powershell
docker build -t simucespe-api .
```

Rodar localmente em container:

```powershell
docker run --rm -p 8000:8000 `
  -e PORT=8000 `
  -e BACKEND_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173 `
  simucespe-api
```

Ou com Compose:

```powershell
docker compose up --build
```

API local:

```text
http://127.0.0.1:8000/docs
```

Endpoints principais:

```text
GET  /health
GET  /provas
GET  /provas/{source_id}
POST /simulados
GET  /simulados/{simulado_id}
POST /simulados/{simulado_id}/respostas
GET  /historico
```

## Producao

Para instalacao de runtime, sem ferramentas de desenvolvimento:

```powershell
python -m pip install .
```

Dependencias de producao ficam em `pyproject.toml` e sao espelhadas em
`requirements.txt` para ambientes que preferem instalacao por arquivo.

## Deploy no Render

Opcao 1: crie um Web Service apontando para este repositorio e selecione Docker
como runtime.

Opcao 2: use o Blueprint `render.yaml` no repositorio.

O container ja usa `PORT`, com default `10000`, e escuta em `0.0.0.0`, como o
Render espera.

Variaveis de ambiente recomendadas:

```text
PORT=10000
BACKEND_CORS_ORIGINS=https://seu-front.netlify.app
```

Health check path:

```text
/health
```

Observacao: o historico atual e persistido em `data/runtime/history.json`. Em
producao no Render, configure um Persistent Disk montado em `/app/data/runtime`
ou troque essa camada por banco quando evoluir o produto.
