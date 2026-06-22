# Diagrama do Modelo Gold — Star Schema

## Closes #22

## Visão geral

A camada Gold implementa um star schema dimensional (ADR-0002) com 2 tabelas fato
e 5 dimensões, otimizado para os KPIs do dashboard Metabase.

---

## Tabelas Fato

### fato_reproducao
Grão: 1 linha por play válido (ms_tocados ≥ 30.000 ms)

| Coluna | Tipo | Descrição |
|---|---|---|
| data_id | INT | FK → dim_tempo.data_id |
| usuario_id | INT | FK → dim_usuario.usuario_id |
| musica_id | INT | FK → dim_musica.musica_id |
| artista_id | INT | FK → dim_artista.artista_id |
| ms_tocados | INT | Milissegundos tocados |
| completou | BOOLEAN | ms_tocados ≥ 90% da duracao_ms |
| contagem | INT | Sempre 1 (facilita SUM) |
| ano_mes | STRING | Partição (ex: '2026-06') |

### fato_pagamento
Grão: 1 linha por transação de pagamento

| Coluna | Tipo | Descrição |
|---|---|---|
| data_id | INT | FK → dim_tempo.data_id |
| usuario_id | INT | FK → dim_usuario.usuario_id |
| plano_id | INT | FK → dim_plano.plano_id |
| valor | DECIMAL(8,2) | Valor cobrado |
| pago | BOOLEAN | true = pago / false = falhou |
| ano_mes | STRING | Partição (ex: '2026-06') |

---

## Dimensões

### dim_tempo
| Coluna | Tipo |
|---|---|
| data_id | INT (PK, formato yyyyMMdd) |
| data | DATE |
| ano | INT |
| mes | INT |
| dia | INT |
| dia_semana | STRING |
| ano_mes | STRING |

### dim_usuario
| Coluna | Tipo |
|---|---|
| usuario_id | INT (PK) |
| nome | STRING |
| pais | STRING |
| data_cadastro | DATE |

### dim_plano
| Coluna | Tipo |
|---|---|
| plano_id | INT (PK) |
| nome | STRING |
| preco_mensal | DECIMAL(8,2) |

### dim_artista
| Coluna | Tipo |
|---|---|
| artista_id | INT (PK) |
| nome | STRING |
| pais | STRING |

### dim_musica
| Coluna | Tipo |
|---|---|
| musica_id | INT (PK) |
| titulo | STRING |
| genero | STRING |
| album | STRING |
| artista_id | INT |
| duracao_ms | INT |

---

## Relações

```
dim_tempo ──── fato_reproducao ──── dim_usuario
                     │ ├──────────── dim_musica
                     │ └──────────── dim_artista

dim_tempo ──── fato_pagamento ───── dim_usuario
                     └──────────── dim_plano
```

---

## Validação dos KPIs

| KPI | Tabelas usadas | Resultado esperado |
|---|---|---|
| Receita mensal | fato_pagamento + dim_plano | ~R$2.500–3.500/mês por plano Família |
| Churn mensal | fato_pagamento | ~0% (dados sintéticos com renovação automática) |
| MAU | fato_reproducao | ~1.200 usuários ativos/mês |
| Top 10 artistas | fato_reproducao + dim_artista | Top artista com ~198 plays |
| Horas ouvidas | fato_reproducao | ~55 horas/mês |
| Ticket médio | fato_pagamento | ~R$17–19/assinante/mês |
