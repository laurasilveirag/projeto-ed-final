# Como Rodar

## Pré-requisitos

- Docker Desktop com WSL2
- Git
- Python 3.12 + [uv](https://docs.astral.sh/uv/)

## Passo a Passo

### 1. Clonar o repositório

```bash
git clone https://github.com/laurasilveirag/projeto-ed-final.git
cd projeto-ed-final
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

### 3. Subir a infraestrutura

```bash
docker compose up -d --build
```

!!! info "Primeira execução"
    O build baixa os JARs do Delta Lake (~5 min). As execuções seguintes são instantâneas.

### 4. Verificar os containers

```bash
docker ps
```

Aguarde o `streaming_airflow_webserver` ficar `(healthy)`.

### 5. Executar o pipeline

Acesse `http://localhost:8080` (admin / admin), encontre o DAG `pipeline_streaming` e clique em **Trigger DAG**.

O pipeline completo leva entre **10 e 20 minutos**.

### 6. Verificar os dados

```bash
docker exec streaming_postgres psql -U streaming -d streaming -c "
SELECT 'fato_reproducao' AS tabela, count(*) FROM gold.fato_reproducao
UNION ALL
SELECT 'fato_pagamento',  count(*) FROM gold.fato_pagamento
UNION ALL
SELECT 'dim_usuario',     count(*) FROM gold.dim_usuario;"
```

### 7. Acessar o Metabase

Abra `http://localhost:3000` — o dashboard **"Streaming — One Page View"** está disponível.

## Rodar os testes

```bash
uv sync
uv run pytest tests/ -v
```

## Rodar os notebooks manualmente

```bash
uv run jupyter lab
```

Execute em ordem: `01_landing_dimensoes` → `02_landing_fatos` → `03_bronze_fatos` → `04_bronze_dimensoes` → `05_silver_fatos` → `06_silver_dimensoes` → `07_gold_dimensoes` → `08_gold_fatos` → `09_gold_para_postgres`.

## Problemas comuns

| Sintoma | Solução |
|---|---|
| Airflow não abre em `localhost:8080` | Usar `http://<ip-wsl>:8080` — descobrir IP: `hostname -I` |
| DAG aparece como "Broken" | Aguardar 30s e recarregar |
| Task falha com erro de rede | Acionar novo Trigger DAG |
| Porta 9000 ocupada pelo Spark | `sudo fuser -k 9000/tcp` antes de rodar notebooks Silver |
