# Pipeline de Dados — Streaming de Música

Pipeline completo implementando a **Arquitetura Medalhão** sobre um dataset de streaming de música com 12 tabelas relacionais no PostgreSQL.

## Visão Geral

```
PostgreSQL → Landing (CSV) → Bronze (Delta) → Silver (Delta) → Gold (Delta) → Metabase
```

| Camada | Formato | O que contém |
|---|---|---|
| **Landing** | CSV | Dados brutos extraídos do Postgres |
| **Bronze** | Delta Lake | Cópia fiel da Landing, particionada por `ingestao_date` |
| **Silver** | Delta Lake | Dados limpos, deduplicados e com regras de negócio |
| **Gold** | Delta Lake + Postgres | Star schema dimensional para análise |

## Stack

| Tecnologia | Papel |
|---|---|
| PostgreSQL 16 | Banco de dados de origem |
| MinIO | Object Storage (Data Lake S3-compatible) |
| Apache Spark / PySpark | Engine de transformação |
| Delta Lake | Formato de armazenamento (Bronze → Gold) |
| Apache Airflow | Orquestração do pipeline |
| Metabase | Dashboard / BI |
| Docker Compose | Infraestrutura local |

## Links Rápidos

- [Como Rodar](como-rodar.md)
- [Arquitetura](arquitetura.md)
- [KPIs e Dashboard](kpis.md)
- [DICTIONARY](dictionary.md)
- [Repositório GitHub](https://github.com/laurasilveirag/projeto-ed-final)
