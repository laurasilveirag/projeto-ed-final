# Setup Metabase e Dashboard — Streaming Gold

## Closes #30 | #36

## Pré-requisitos

- Docker Compose rodando (`docker compose up -d`)
- DAG `pipeline_streaming` executada com sucesso no Airflow
- Schema `gold` populado no Postgres com as 7 tabelas

---

## 1. Acessar o Metabase

Abra `http://localhost:3000` no navegador.

No primeiro acesso, o Metabase pede para criar o usuário administrador.
Use as credenciais definidas por você durante o onboarding (não há usuário/senha fixos versionados no repositório).
---

## 2. Conexão com o Postgres (schema gold)

Configuração em **Admin → Databases → streaming-gold**:

| Campo | Valor |
|---|---|
| Tipo | PostgreSQL |
| Nome amigável | streaming-gold |
| Servidor | `postgres` |
| Porta | `5432` |
| Banco de dados | `streaming` |
| Usuário | `${POSTGRES_USER}` |
| Senha | `${POSTGRES_PASSWORD}` |
| Schemas | `gold` |
| SSL | Desligado |

---

## 3. Tabelas disponíveis no schema gold

| Tabela | Tipo | Descrição |
|---|---|---|
| `fato_reproducao` | Fato | Plays válidos (≥30s) com musica_id, artista_id, ms_tocados |
| `fato_pagamento` | Fato | Pagamentos com flag pago/falhou, plano_id, usuario_id |
| `dim_tempo` | Dimensão | Calendário completo com data_id, ano, mes, dia_semana |
| `dim_usuario` | Dimensão | Usuários com nome e país |
| `dim_plano` | Dimensão | Planos com nome e preco_mensal |
| `dim_artista` | Dimensão | Artistas com nome e país |
| `dim_musica` | Dimensão | Músicas com título, gênero, álbum e duração |

---

## 4. KPIs configurados no Metabase

Os arquivos SQL estão em `sql/kpis/`. Para recriar cada pergunta:
**+ Novo → SQL nativo → streaming-gold → cola o SQL → salva em Nossas análises**

| Arquivo SQL | Nome no Metabase | Visualização |
|---|---|---|
| `01_kpi_receita_mensal_por_plano.sql` | KPI 1 — Receita mensal por plano | Tabela |
| `02_kpi_taxa_churn_mensal.sql` | KPI 2 — Taxa de churn mensal | Linha |
| `03_kpi_usuarios_ativos_mau.sql` | KPI 3 — Usuários Ativos (MAU) | Linha |
| `04_kpi_top10_artistas.sql` | KPI 4 — Top 10 artistas | Tabela |
| `05_metricas_horas_ticket_medio.sql` | Métricas — Horas ouvidas e Ticket médio | Linha |

---

## 5. Dashboard — One Page View

**Nome:** Dashboard Streaming — One Page View
**Coleção:** Nossas análises
**URL:** `http://localhost:3000/dashboard/2-dashboard-streaming-one-page-view`

Layout em grade 3x2 — todos os KPIs visíveis em uma única página sem scroll.
