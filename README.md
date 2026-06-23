# Pipeline de Dados — Streaming de Música

Pipeline de dados completo implementando a **Arquitetura Medalhão** sobre um dataset sintético de streaming de música, desenvolvido como projeto final da disciplina de Engenharia de Dados — SATC 2026/1.

## Arquitetura

```
PostgreSQL (12 tabelas) → Landing (CSV) → Bronze (Delta) → Silver (Delta) → Gold (Delta) → Metabase
```

| Camada | Formato | Partição | O que contém |
|---|---|---|---|
| Landing | CSV | — | Dados brutos do Postgres |
| Bronze | Delta Lake | `ingestao_date` | Cópia fiel da Landing com tipagem |
| Silver | Delta Lake | `ano_mes` | Dados limpos + regras de negócio |
| Gold | Delta Lake + Postgres | `ano_mes` | Star schema para análise |

## Stack

| Tecnologia | Versão | Papel |
|---|---|---|
| PostgreSQL | 16 | Banco de dados de origem |
| MinIO | latest | Object Storage (Data Lake) |
| Apache Spark / PySpark | 3.5.1 | Engine de transformação |
| Delta Lake | 3.2.0 | Formato de armazenamento |
| Apache Airflow | 2.9.2 | Orquestração do pipeline |
| Metabase | v0.50.15 | Dashboard / BI |
| Docker Compose | — | Infraestrutura local |
| Python | 3.12 | Scripts e notebooks |

## Como Rodar

```bash
# 1. Clonar
git clone https://github.com/laurasilveirag/projeto-ed-final.git
cd projeto-ed-final

# 2. Configurar ambiente
cp .env.example .env

# 3. Subir infraestrutura
docker compose up -d --build

# 4. Executar pipeline (Airflow)
# Acesse http://localhost:8080 (admin/admin) → Trigger DAG pipeline_streaming

# 5. Ver dashboard
# Acesse http://localhost:3000
```

Documentação completa em: **https://laurasilveirag.github.io/projeto-ed-final/**

## Modelo de Dados — Gold (Star Schema)

```
          dim_tempo
              │
dim_usuario ──┼── fato_reproducao ── dim_musica
              │         │
          dim_artista   └── fato_pagamento ── dim_plano
```

## KPIs do Dashboard

| KPI | Fonte | Resultado esperado |
|---|---|---|
| Receita mensal por plano | `fato_pagamento` + `dim_plano` | ~R$2.500–3.500/mês (Família) |
| Taxa de churn mensal | `fato_pagamento` | ~0% (dados sintéticos) |
| Usuários Ativos (MAU) | `fato_reproducao` | ~1.200/mês |
| Top 10 artistas | `fato_reproducao` + `dim_artista` | Top ~198 plays |
| Horas ouvidas | `fato_reproducao.ms_tocados` | ~55h/mês |
| Ticket médio | `fato_pagamento` | ~R$17–19/mês |

## Testes

```bash
uv run pytest tests/ -v
# 18+ testes cobrindo seed, Silver e Gold
```

## Estrutura do Repositório

```
projeto-ed-final/
├── dags/                    # DAGs do Airflow
├── docker/                  # Dockerfiles customizados
├── docs/                    # Documentação MkDocs
│   ├── adr/                 # Architectural Decision Records
│   └── ...
├── sql/
│   ├── 01_ddl.sql           # DDL das 12 tabelas de origem
│   └── kpis/               # Queries SQL dos KPIs
├── src/
│   ├── notebooks/           # Notebooks PySpark (01-09)
│   └── seed/               # Script de geração de dados (Faker)
├── tests/                   # Testes pytest
├── docker-compose.yml
├── mkdocs.yml
├── DICTIONARY.md
└── pyproject.toml
```

## Carga Incremental

O pipeline suporta carga incremental via **watermark de `created_at`** (ADR-0001).
Na segunda execução em diante, o Airflow processa apenas os registros inseridos após o último run.

```bash
# Para demonstrar: inserir novos dados e acionar o DAG novamente
# O watermark_created_at fica salvo nas Airflow Variables
```

## Tecnologias

![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql&logoColor=white)
![MinIO](https://img.shields.io/badge/MinIO-latest-C72E49?style=flat&logo=minio&logoColor=white)
![Apache Spark](https://img.shields.io/badge/Apache%20Spark-3.5.1-E25A1C?style=flat&logo=apachespark&logoColor=white)
![PySpark](https://img.shields.io/badge/PySpark-3.5.1-E25A1C?style=flat&logo=apachespark&logoColor=white)
![Delta Lake](https://img.shields.io/badge/Delta%20Lake-3.2.0-00A3E0?style=flat&logo=delta&logoColor=white)
![Apache Airflow](https://img.shields.io/badge/Apache%20Airflow-2.9.2-017CEE?style=flat&logo=apacheairflow&logoColor=white)
![Metabase](https://img.shields.io/badge/Metabase-v0.50.15-509EE3?style=flat&logo=metabase&logoColor=white)
![Docker Compose](https://img.shields.io/badge/Docker%20Compose-local-2496ED?style=flat&logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)

## Documentação

A documentação completa está disponível em:  
**https://laurasilveirag.github.io/projeto-ed-final/**
