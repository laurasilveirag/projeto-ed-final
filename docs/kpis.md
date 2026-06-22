# KPIs e Dashboard

## Dashboard — One Page View

Disponível em `http://localhost:3000` após executar o pipeline.
Todas as visualizações ficam em uma única tela sem scroll.

## KPIs

### KPI 1 — Receita mensal por plano

- **Fonte:** `gold.fato_pagamento` + `gold.dim_plano`
- **Regra:** Soma de `valor` onde `pago = true`, agrupado por plano e `ano_mes`
- **SQL:** `sql/kpis/01_kpi_receita_mensal_por_plano.sql`

### KPI 2 — Taxa de churn mensal

- **Fonte:** `gold.fato_pagamento`
- **Regra:** Usuários que pagaram no mês M-1 mas não no mês M
- **SQL:** `sql/kpis/02_kpi_taxa_churn_mensal.sql`

### KPI 3 — Usuários Ativos (MAU)

- **Fonte:** `gold.fato_reproducao`
- **Regra:** Usuários distintos com ≥ 1 play válido no mês
- **SQL:** `sql/kpis/03_kpi_usuarios_ativos_mau.sql`

### KPI 4 — Top 10 artistas por reproduções

- **Fonte:** `gold.fato_reproducao` + `gold.dim_artista`
- **Regra:** Contagem de plays válidos por artista, top 10
- **SQL:** `sql/kpis/04_kpi_top10_artistas.sql`

## Métricas

### Total de horas ouvidas
Soma de `ms_tocados / 3.600.000` (só plays válidos).

### Ticket médio
Receita paga / número de assinantes pagantes no mês.

**SQL:** `sql/kpis/05_metricas_horas_ticket_medio.sql`

## Play válido

> `ms_tocados >= 30.000 ms` (30 segundos). Plays abaixo desse limiar são descartados na Silver.
