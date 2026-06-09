# Pipeline de Dados — Streaming de Música (Arquitetura Medalhão)

**Disciplina:** Engenharia de Dados · **Time:** 7 pessoas · **Entrega:** 23/06 às 18:59

Pipeline de dados completo para uma plataforma de streaming de música, implementando a arquitetura medalhão (Landing → Bronze → Silver → Gold) com geração de dados sintéticos, orquestração via Airflow e dashboard no Metabase.

---

## Arquitetura

```
PostgreSQL (origem)
      │
      ▼ extração (PySpark)
   Landing (CSV no MinIO)
      │
      ▼ promoção (PySpark)
   Bronze (Delta Lake — particionado por ingestao_date)
      │
      ▼ limpeza + regras (PySpark)
   Silver (Delta Lake — particionado por ano_mes)
      │
      ▼ star schema (PySpark)
    Gold (Delta Lake no MinIO)
      │
      ▼ espelho (DAG Airflow)
 Postgres schema gold
      │
      ▼
  Metabase (dashboard)
```

**Stack:** PostgreSQL 16 · MinIO · Apache Airflow · Apache Spark / PySpark · Delta Lake · Metabase · Python 3.12 · UV · Docker Compose

---

## Como Rodar

### Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e rodando
- [UV](https://docs.astral.sh/uv/getting-started/installation/) instalado

### 1. Clonar e configurar variáveis de ambiente

```bash
git clone <url-do-repo>
cd projeto-final-eng
cp .env.example .env
```

> Edite `.env` se quiser mudar senhas ou portas.

### 2. Subir toda a stack (infra + seed automático)

```bash
docker compose up --build
```

O serviço `seed` popula o Postgres automaticamente após o banco estar saudável.
Aguarde a mensagem `Seed concluído!` nos logs.

### 3. Verificar os dados

```bash
docker compose exec postgres psql -U streaming -d streaming -c \
  "SELECT tablename, n_live_tup FROM pg_stat_user_tables ORDER BY tablename;"
```

### 4. Acessar os serviços

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| MinIO Console | http://localhost:9001 | `minioadmin` / `minioadmin` |
| Airflow | http://localhost:8080 | `airflow` / `airflow` |
| Metabase | http://localhost:3000 | configurar no primeiro acesso |
| Postgres | `localhost:5432` | `streaming` / `streaming123` |

### 5. Parar

```bash
docker compose down          # para os containers
docker compose down -v       # para e apaga os volumes (reset completo)
```

---

## Seed de Dados

O script de seed gera **~126 500 linhas** distribuídas nas 12 tabelas da origem:

| Tabela | Linhas | Tipo |
|--------|--------|------|
| `generos` | 30 | dimensão |
| `planos` | 3 | dimensão |
| `artistas` | 500 | dimensão |
| `albuns` | 2 000 | dimensão |
| `musicas` | 10 000 | dimensão |
| `usuarios` | 3 000 | dimensão |
| `dispositivos` | 5 000 | dimensão |
| `assinaturas` | 3 500 | fato/transação |
| `pagamentos` | 10 500 | fato/transação |
| `playlists` | 2 000 | dimensão |
| `playlist_musicas` | 20 000 | associativa |
| `reproducoes` | **70 000** | **fato principal** |

**Regras aplicadas pelo seed:**
- `created_at` em todas as tabelas (necessário para carga incremental)
- ~15% das assinaturas com `data_fim` preenchida (churn real)
- ~20% das reproduções com `ms_tocados < 30s` (plays inválidos — filtrados na Silver)
- `completou` derivado: `ms_tocados ≥ 90%` da duração da música
- Dados espalhados nos **últimos 3 anos**

### Rodar o seed manualmente

```bash
# Com Postgres já rodando:
docker compose up postgres -d

uv run python -m src.seed.main            # inserir dados
uv run python -m src.seed.main --truncate # limpar e reinserir
```

---

## Estrutura do Repositório

```
projeto-final-eng/
├── docker-compose.yml          # orquestra todos os serviços
├── docker/
│   ├── airflow/Dockerfile      # Airflow + PySpark + Java (delta-spark)
│   └── seed/Dockerfile         # imagem Python p/ seed
├── sql/
│   └── 01_ddl.sql              # DDL das 12 tabelas da origem
├── src/
│   └── seed/
│       ├── config.py           # lê variáveis de ambiente
│       ├── db.py               # conexão + bulk insert
│       ├── generators.py       # geradores Faker por tabela
│       └── main.py             # CLI entry-point
├── dags/                       # DAGs Airflow (P6)
├── notebooks/                  # notebooks exploratórios
├── tests/
│   └── test_generators.py      # testes dos geradores (10 testes)
├── docs/                       # MkDocs
├── pyproject.toml              # projeto UV + dependências
└── .env.example                # template de variáveis de ambiente
```

---

## KPIs e Métricas

| # | Indicador | Fonte | Regra |
|---|-----------|-------|-------|
| KPI 1 | Receita mensal por plano | `pagamentos` | só `status='pago'`, agrupado por `ano_mes` |
| KPI 2 | Taxa de churn | `assinaturas` | cancelados no mês / ativos no início |
| KPI 3 | Usuários ativos (MAU) | `reproducoes` | distintos com ≥1 play válido no mês |
| KPI 4 | Top 10 artistas | `reproducoes` | só plays válidos (`ms_tocados ≥ 30s`) |
| M 1 | Total horas ouvidas | `reproducoes.ms_tocados` | só plays válidos |
| M 2 | Ticket médio | `pagamentos` | receita paga / nº assinantes pagantes |

---

## Modelo Gold (Star Schema)

**Fatos:** `fato_reproducao` · `fato_pagamento`

**Dimensões:** `dim_tempo` (grão dia) · `dim_usuario` · `dim_musica` · `dim_artista` · `dim_plano`

---

## Divisão de Responsabilidades

| # | Responsável | Frente |
|---|-------------|--------|
| P1 | — | Arquitetura + geração de dados (seed) |
| P2 | — | Infra (docker-compose) + ingestão dimensões → Landing |
| P3 | — | Ingestão fatos → Landing → Bronze |
| P4 | — | Transformação Silver (limpeza, dedup, regras) |
| P5 | — | Modelagem Gold (star schema) |
| P6 | — | Orquestração Airflow (DAGs + carga incremental) |
| P7 | — | Metabase + KPIs + MkDocs |

> Detalhes completos em [PROJETO.md](PROJETO.md).

---

## Testes

```bash
uv run pytest tests/ -v
```

10 testes cobrindo: leitura de config, geração de dados por tabela, unicidade de emails, proporção de cancelamentos (~15%) e volume total (≥120k linhas).

---

## Padrão de Commits

```
feat(ingestao): extrai tabelas de dimensão para a Landing
fix(silver): descarta plays com ms_tocados < 30s
docs(readme): adiciona instruções de como subir o ambiente
```

**Tipos:** `feat` · `fix` · `docs` · `refactor` · `test` · `chore`  
**Escopos:** `ingestao` · `bronze` · `silver` · `gold` · `dag` · `infra` · `bi` · `dados` · `docs`
