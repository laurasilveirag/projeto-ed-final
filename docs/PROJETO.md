# Plano de Projeto — Pipeline de Dados (Arquitetura Medalhão)

**Disciplina:** Engenharia de Dados
**Time:** 7 pessoas
**Prazo de entrega:** 23/06 às 18:59 (AVA: URL GitHub + URL MkDocs)
**Referência:** https://github.com/jlsilva01/projeto-ed-satc

---

## 1. Definição do Tema

**Tema definido: Música (streaming).** ✅

Escolhido por ter relacionamentos ricos (artista, álbum, usuário, plano), fato de
reprodução com grão fino, e KPIs claros (receita por plano, churn, MAU, top artistas).
Fácil modelar 10+ tabelas e gerar massa com `faker`.

### Modelo de origem — Postgres (mínimo 10 tabelas, 10k+ linhas no fato, 3 anos)

**12 tabelas. `created_at` em TODAS** (necessário pro watermark / carga incremental — ADR-0001).

| Tabela | Tipo | Colunas principais |
|--------|------|--------------------|
| `usuarios` | dimensão | `id`, `nome`, `email`, `data_cadastro`, `pais`, `created_at` |
| `planos` | dimensão | `id`, `nome` (Grátis/Premium/Família), `preco_mensal`, `created_at` |
| `assinaturas` | fato/transação | `id`, `usuario_id`, `plano_id`, `data_inicio`, `data_fim` (nulo=ativa), `status` (ativa/cancelada), `created_at` |
| `pagamentos` | fato/transação | `id`, `assinatura_id`, `valor`, `data`, `status` (pago/falhou), `created_at` |
| `artistas` | dimensão | `id`, `nome`, `pais`, `created_at` |
| `albuns` | dimensão | `id`, `artista_id`, `titulo`, `ano_lancamento`, `created_at` |
| `musicas` | dimensão | `id`, `album_id`, `artista_id`, `genero_id`, `titulo`, `duracao_ms`, `created_at` |
| `generos` | dimensão | `id`, `nome`, `created_at` |
| `playlists` | dimensão | `id`, `usuario_id`, `nome`, `created_at` |
| `playlist_musicas` | associativa | `id`, `playlist_id`, `musica_id`, `ordem`, `created_at` |
| `reproducoes` | **FATO principal (10k+)** | `id`, `usuario_id`, `musica_id`, `dispositivo_id`, `timestamp`, `ms_tocados`, `completou`, `created_at` |
| `dispositivos` | dimensão | `id`, `usuario_id`, `tipo` (mobile/web/desktop), `so`, `created_at` |

### Modelo Gold — star schema dimensional (Delta no MinIO + espelho no Postgres p/ Metabase)

**Fatos:**

| Fato | Grão | Medidas | Liga em |
|------|------|---------|---------|
| `fato_reproducao` | 1 play válido (`ms_tocados>=30s`) | `ms_tocados`, `completou`, contagem | `dim_tempo`, `dim_usuario`, `dim_musica`, `dim_artista` |
| `fato_pagamento` | 1 pagamento | `valor`, flag `pago` | `dim_tempo`, `dim_usuario`, `dim_plano` |

**Dimensões:**

| Dimensão | Grão | Atributos |
|----------|------|-----------|
| `dim_tempo` | **dia** | `data_id`, `data`, `ano`, `mes`, `dia`, `dia_semana`, `ano_mes` |
| `dim_usuario` | usuário | `usuario_id`, `nome`, `pais`, `data_cadastro` |
| `dim_plano` | plano | `plano_id`, `nome`, `preco_mensal` |
| `dim_artista` | artista | `artista_id`, `nome`, `pais` |
| `dim_musica` | música | `musica_id`, `titulo`, `genero`, `album`, `artista_id`, `duracao_ms` |

> Churn e MAU saem de agregações sobre `fato_reproducao`/`assinaturas` por `ano_mes`
> (ver regras na seção 8). Mês = agregação da `dim_tempo` (grão dia) via `ano_mes`.

---

## 2. Stack Técnica (sugestão padrão, ajustável)

- **Origem:** PostgreSQL (relacional) — gerado via Python `faker` *(escolhemos só relacional; o slide pede relacional **ou** não relacional)*
- **Orquestração:** Apache Airflow (Docker) — *não usar Task Scheduler/cron*
- **Object Storage:** MinIO (Docker) — Data Lake S3-compatible
- **Camadas medalhão:** Landing (CSV bruto) → Bronze → Silver → Gold (Delta Lake)
- **Engine de transformação:** Apache Spark / PySpark
- **Modelo Gold:** **Dimensional / star schema** (fatos + dimensões) — ADR-0002
- **Ferramenta de BI / Dashboard (One Page View):** **Metabase** (open-source, Docker), conectada no schema `gold` do Postgres (espelho da Gold — ADR-0003). Owner: **P7**.
- **Docs:** MkDocs + README caprichado
- **Versionamento:** GitHub com branch `main` protegida (PR obrigatório + aprovação), Issues para todas as tarefas

---

## 3. Divisão de Responsabilidades (7 pessoas)

> ⚠️ **REGRA DE OURO: TODOS desenvolvem.** O professor vai avaliar os **commits individuais**. Ninguém pode ser "só docs" ou "só infra". Cada pessoa tem uma **frente principal de código** + responde por uma fatia das tarefas transversais (infra, docs, testes). Tudo via PR com o nome do autor.

| # | Frente principal (código) | O que desenvolve (commits do autor) | Tarefa transversal |
|---|---------------------------|--------------------------------------|--------------------|
| **P1** | **Arquitetura + Geração de dados** | Scripts Python `faker` (10k linhas, 3 anos), modelagem das 12 tabelas, seed Postgres | Coordena revisão de PRs |
| **P2** | **Infra como código + Ingestão (parte 1)** | `docker-compose.yml`, **e** desenvolve a extração do Postgres → Landing (CSV) das tabelas de dimensão (PySpark) | Setup/README de ambiente |
| **P3** | **Ingestão (parte 2) → Bronze** | Extração das tabelas fato Postgres → Landing (CSV) → Bronze Delta (PySpark) | Qualidade de dados Bronze |
| **P4** | **Transformação Silver** | Limpeza, padronização, dedup, tipagem em PySpark | Testes (`pytest`) das transformações |
| **P5** | **Modelagem Gold (Dimensional)** | Fatos e dimensões em Delta (PySpark) + diagrama do modelo | Validação dos KPIs vs. dados |
| **P6** | **Orquestração (Airflow)** | DAGs em Python orquestrando ingestão→Silver→Gold + carga incremental | CI/CD básico no GitHub Actions |
| **P7** | **Ferramenta de BI + KPIs (código)** | **Responsável pelo Metabase**: subir/configurar, conectar no schema `gold` do Postgres, modelar queries/medidas dos 4 KPIs + 2 métricas, montar o One Page View | MkDocs + slides (com apoio de todos) |

### Detalhamento por integrante

Explicação de cada frente em linguagem clara, pra quem nunca mexeu com a stack.
Detalhe técnico das regras: ver `DICTIONARY.md` e `docs/adr/`.

#### P1 — Arquitetura + Geração de dados
- Define o **DDL** (os `CREATE TABLE`) das 12 tabelas da origem no Postgres, seguindo o `DICTIONARY.md`.
- Escreve um script Python com a lib **`faker`** que inventa dados realistas: 10k+ reproduções, usuários, músicas, assinaturas, pagamentos — tudo espalhado nos **últimos 3 anos**.
- Pontos de atenção (regras já decididas): `created_at` em toda tabela; ~15% das assinaturas com `data_fim` preenchida (senão o churn dá zero); `ms_tocados` variado (uns plays < 30s pra Silver limpar).
- Roda o script e popula o Postgres (o "seed").

#### P2 — Infra como código + Ingestão parte 1 (dimensões)
- Escreve o **`docker-compose.yml`** que sobe tudo junto: Postgres, MinIO, Airflow, Metabase. É o "liga o ambiente" do time inteiro.
- Garante a imagem Docker com Airflow + PySpark + delta-spark + Java (ADR-0004).
- Desenvolve a **extração das tabelas de dimensão** (usuarios, planos, artistas, etc.) do Postgres pra camada **Landing** (arquivos **CSV** brutos no MinIO), usando PySpark.

#### P3 — Ingestão parte 2 (fatos) → Bronze
- Faz a extração das **tabelas fato** (`reproducoes`, `pagamentos`, `assinaturas`) do Postgres → Landing (CSV).
- Promove Landing → **Bronze** (Delta Lake), particionando por **`ingestao_date`** (data em que o dado entrou — ADR-0001).
- Bronze é cópia fiel do bruto, só convertida pra Delta. Sem limpeza ainda.

#### P4 — Transformação Silver
- Pega o Bronze e **limpa**: remove duplicados, padroniza texto/datas, corrige tipos.
- Aplica as **regras de negócio** de validade: descarta play com `ms_tocados < 30s`; deriva `completou` (≥90% da duração); mantém todos os pagamentos mas marca `pago`/`falhou`.
- Silver = dado confiável, ainda normalizado (não é o modelo final).

#### P5 — Modelagem Gold (dimensional)
- Constrói o **star schema** em Delta: fatos (`fato_reproducao`, `fato_pagamento`) + dimensões (`dim_tempo`, `dim_usuario`, `dim_plano`, `dim_artista`, `dim_musica`) — ver `DICTIONARY.md`.
- `dim_tempo` no grão **dia**, com coluna `ano_mes` (é o que liga os KPIs mensais).
- Faz o **diagrama** do modelo e valida se os números dos KPIs batem com os dados.

#### P6 — Orquestração (Airflow)
- Escreve as **DAGs**: o passo-a-passo automático que roda ingestão → Bronze → Silver → Gold, na ordem certa.
- Implementa a **carga incremental** com watermark (guarda o maior `created_at` já lido, próxima run pega só o mais novo — ADR-0001).
- Adiciona o passo final que **espelha a Gold pro Postgres** (schema `gold`), pro Metabase ler (ADR-0003).
- Monta CI básico no GitHub Actions.

#### P7 — Metabase + KPIs
- Sobe e configura o **Metabase** (no docker-compose) e conecta no schema `gold` do Postgres.
- Escreve as **queries/medidas** dos 4 KPIs + 2 métricas (receita, churn, MAU, top artistas, horas, ticket médio).
- Monta o **dashboard One Page View** — tudo numa tela só.
- Lidera MkDocs + slides (com apoio de todos).

**Como garantir que todos apareçam nos commits:**
- Cada frente vira uma **branch própria** e **PRs frequentes** (não um único PR gigante no fim).
- **Todos** abrem e fecham **Issues** com seu nome e revisam PRs dos colegas (comentários contam como interação).
- Trabalho que é "de uma pessoa só" (ex.: docs, dashboard) deve ser **dividido em tarefas menores** atribuídas a 2-3 pessoas para gerar commits de vários autores.
- Evitar **pair programming sem co-autoria** — se programarem juntos, usar `Co-authored-by:` no commit para registrar os dois.
- Meta sugerida: **todos com commits em pelo menos 3 das 4 semanas** (atividade contínua, não só na reta final).

---

## 4. KPIs e Métricas (4 KPIs + 2 métricas)

**KPIs:** 1) Receita mensal por plano · 2) Taxa de churn · 3) Usuários ativos (MAU) · 4) Top 10 artistas por reproduções
**Métricas:** 1) Total de horas ouvidas · 2) Ticket médio por assinatura

---

## 5. Timeline de fluxo (até 23/06)

O trabalho **flui entre as pessoas** — cada frente monta uma parte, **entrega** (via PR) e a
próxima continua de onde a anterior parou. Quem depende de uma entrega trabalha em paralelo no
que dá, e **destrava** quando o handoff chega. As fases se sobrepõem; não é "uma por semana".

Legenda: 🔨 trabalha · 📦 entrega (handoff) · ⏳ esperando destravar

```
FASE 0 — Fundação (Sem. 1)
  P2 🔨 docker-compose (Postgres+MinIO+Airflow+Metabase)
       └─📦 ambiente de pé ──────────────┐
  P1 🔨 DDL das 12 tabelas + script faker │ (pode escrever offline)
  Todos 🔨 repo, branch protegida, Issues  │
                                           ▼
FASE 1 — Origem viva (Sem. 1→2)
  P1 🔨 roda seed no Postgres (precisava do ambiente do P2)
      └─📦 Postgres populado, 10k+ linhas ──────────┐
  P2 🔨 extração dimensões → Landing (CSV)           │
  P3 ⏳ espera o seed → 🔨 extração fatos → Landing   │
                                                     ▼
FASE 2 — Bronze (Sem. 2)
  P3 🔨 Landing → Bronze (Delta, particionado por ingestao_date)
      └─📦 Bronze pronta ───────────────┐
  P6 🔨 começa 1ª DAG amarrando ingestão │ (em paralelo)
                                         ▼
FASE 3 — Silver (Sem. 2→3)
  P4 ⏳ espera Bronze → 🔨 limpeza/dedup/regras (play 30s, completou)
      └─📦 Silver confiável ────────────┐
                                        ▼
FASE 4 — Gold (Sem. 3)
  P5 ⏳ espera Silver → 🔨 star schema (fatos + dimensões) + diagrama
      └─📦 Gold (Delta no MinIO) ───────┬──────────────┐
  P6 🔨 amplia DAG: ingestão→Silver→Gold │              │
      🔨 carga incremental (watermark)   │              │
      🔨 passo espelho Gold → Postgres ──┘              │
          └─📦 schema `gold` no Postgres ───────────────┤
                                                        ▼
FASE 5 — Dashboard (Sem. 3→4)
  P7 ⏳ espera Gold no Postgres → 🔨 Metabase: conexão, queries dos
      6 indicadores, One Page View
      └─📦 dashboard pronto

FASE 6 — Fechamento (Sem. 4 → Final)
  Todos 🔨 MkDocs, README, slides, testes ponta a ponta
  🔨 ensaio + demo de carga incremental (roda DAG 2x, mostra só o novo entrando)
  📦 entrega no AVA (URLs GitHub + MkDocs) até 23/06 18:59
```

**Caminho crítico** (o que não pode atrasar, pois tudo depende em cadeia):
`P2 ambiente → P1 seed → P3 Bronze → P4 Silver → P5 Gold → P6 espelho → P7 dashboard`.

**Trabalho em paralelo enquanto espera** (ninguém fica parado):
- P1 escreve DDL + script `faker` **antes** do ambiente existir (testa local depois).
- P6 prototipa DAGs e estuda watermark enquanto Bronze/Silver não existem.
- P7 instala/explora o Metabase e desenha o layout do One Page View antes da Gold ficar pronta.
- Todos: Issues, revisão de PRs, MkDocs incremental desde o dia 1.

---

## 6. Padrões de Trabalho no GitHub

- Branch `main` protegida — só via **Pull Request** com aprovação.
- Padrão de branch: `feat/ingestao-bronze`, `fix/...`, `docs/...`
- **Todas** as tarefas viram **Issues** (use labels: `ingestao`, `transformacao`, `infra`, `docs`).
- Estrutura do repositório conforme aula de "Python para Engenharia de Dados" (`src/`, `notebooks/`, `dags/`, `docker/`, `docs/`, `tests/`).
- README com: visão geral, arquitetura (diagrama), como rodar, KPIs, prints do dashboard.

### Padrão de commit (Conventional Commits)

Formato: `tipo(escopo): descrição curta no imperativo`

```
feat(ingestao): extrai tabelas de dimensão para a Landing
fix(silver): descarta plays com ms_tocados < 30s
docs(readme): adiciona instruções de como subir o ambiente
```

- **Tipos:** `feat` (nova funcionalidade), `fix` (correção), `docs`, `refactor`, `test`, `chore` (infra/config).
- **Escopo** (opcional, mas use): `ingestao`, `bronze`, `silver`, `gold`, `dag`, `infra`, `bi`, `dados`, `docs`.
- **Descrição:** imperativo, minúscula, sem ponto final, ≤ 50 caracteres. "extrai", não "extraído"/"extraindo".
- **Corpo** (opcional): explica o *porquê* quando não for óbvio. Linha em branco antes.
- **Programou em dupla?** Registre o segundo autor (conta como commit dele):
  ```
  Co-authored-by: Nome <email@exemplo.com>
  ```
- Commits **pequenos e frequentes** — um assunto por commit. Nada de "várias coisas" num commit só.

### Padrão de branch

`tipo/escopo-curto` — ex.: `feat/ingestao-bronze`, `fix/silver-dedup`, `docs/mkdocs-setup`.

### Padrão de Pull Request

- **Título:** mesmo formato do commit — `feat(gold): cria fato_reproducao e dimensões`.
- **PR pequeno e frequente** (não um PR gigante no fim). Liga à Issue com `Closes #12`.
- **Mínimo 1 aprovação** antes do merge na `main`. Quem revisa comenta (a interação conta na nota).
- **Template do corpo:**
  ```markdown
  ## O que faz
  Descrição curta da mudança.

  ## Por quê
  Contexto / qual parte do pipeline avança. Liga em ADR se aplicável (ex.: ADR-0001).

  ## Como testar
  Passos pra rodar e verificar (comando, o que olhar no MinIO/Postgres/dashboard).

  ## Checklist
  - [ ] Segue o `DICTIONARY.md` (nomes de tabela/coluna)
  - [ ] Testado localmente
  - [ ] Issue ligada (Closes #...)

  Closes #
  ```

---

## 7. Entregáveis Finais (checklist)

- [ ] Origem com 10+ tabelas, 10k linhas, datas dos últimos 3 anos
- [ ] Data Lake em MinIO com camadas Landing/Bronze/Silver/Gold
- [ ] Landing em CSV/JSON; Bronze/Silver/Gold em Delta Lake
- [ ] Transformações em Spark/PySpark
- [ ] Orquestração via Airflow (DAGs agendadas)
- [ ] Gold em modelo dimensional (star schema)
- [ ] Dashboard One Page View com 4 KPIs + 2 métricas
- [ ] Demonstração de carga incremental
- [ ] Documentação em MkDocs + README
- [ ] GitHub com branch protegida, PRs e Issues
- [ ] Apresentação PowerPoint (20 min) + demo prática
- [ ] Entrega no AVA (URLs) até 23/06 18:59

---

## 8. Decisões Travadas (sessão de design — 04/06)

Resumo das decisões tomadas destrinchando o plano. Glossário + schema completo em
`DICTIONARY.md`; justificativas detalhadas em `docs/adr/`.

### Domínio e modelo
- **Tema:** Streaming de música. ✅
- **Origem (Postgres):** 12 tabelas — `usuarios`, `planos`, `assinaturas`, `pagamentos`,
  `artistas`, `albuns`, `musicas`, `generos`, `playlists`, `playlist_musicas`,
  `reproducoes`, `dispositivos`. Cobre o requisito de 10+ tabelas (o mínimo de 10 é na ORIGEM, não na Gold).
- **Fato principal `reproducoes`:** grão = 1 linha por play (evento bruto). Campos-chave:
  `usuario_id`, `musica_id`, `dispositivo_id`, `timestamp`, `ms_tocados`, `completou`, `created_at`.
- **Plano mora na `assinatura`, não no usuário.** Trocar de plano = nova assinatura →
  histórico preservado sem SCD.
- **`created_at` em TODAS as tabelas de origem** (necessário pro incremental).

### Regras de negócio (cada indicador rastreável a uma tabela)
| Indicador | Fonte | Regra |
|-----------|-------|-------|
| Receita mensal por plano | `pagamentos` | só `status='pago'`, agrupado por `ano_mes` |
| Churn | `assinaturas` | cancelados no mês / ativos no início; lê só `data_fim`/`status`, ignora pagamento |
| MAU | `reproducoes` | usuários **distintos** com ≥1 play válido no mês |
| Top 10 artistas | `reproducoes` | só plays válidos |
| Total horas ouvidas | `reproducoes.ms_tocados` | só plays válidos |
| Ticket médio | `pagamentos` | receita paga / nº assinantes pagantes no mês |

- **Play válido = `ms_tocados >= 30s`.** Abaixo (incl. 0/nulo) = descartado na Silver.
- **`completou`** derivado: `ms_tocados >= 90% da duração da música`.
- **Massa:** ~15% das assinaturas com `data_fim` preenchida (espalhadas nos 3 anos), senão churn = 0.

### Arquitetura (ver ADRs)
- **ADR-0001 — Carga incremental por watermark de `created_at`.** DAG guarda o maior
  `created_at` ingerido e lê só o que é mais novo. Particionamento: Bronze por
  `ingestao_date`; Silver/Gold por `ano_mes` do evento; dimensões sem partição.
- **ADR-0002 — Gold em star schema dimensional.** Fatos (`fato_reproducao`, `fato_pagamento`)
  + dimensões (`dim_usuario`, `dim_musica`, `dim_artista`, `dim_tempo` grão dia, `dim_plano`).
- **ADR-0003 — Serving Gold → Postgres.** Gold oficial em Delta no MinIO; passo final da
  DAG espelha pro schema `gold` no Postgres; Metabase conecta no Postgres (não lê Delta direto).
- **ADR-0004 — Spark via PythonOperator.** PySpark in-process no container do Airflow
  (volume pequeno, sem cluster). Imagem única: Airflow + PySpark + delta-spark + Java.

### Ainda em aberto (fora da modelagem)
- Versões exatas das imagens Docker (P2).
- Branch protection + CI no GitHub Actions (P6).
- Conteúdo do MkDocs.
