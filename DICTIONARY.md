# DICTIONARY.md — Glossário de Tabelas e Colunas

Glossário completo de todas as tabelas e colunas do projeto, da origem (Postgres) à Gold (star schema).

---

## Tabelas de Origem (PostgreSQL — schema public)

### usuarios
| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL PK | Identificador único do usuário |
| `nome` | VARCHAR(200) | Nome completo |
| `email` | VARCHAR(300) | E-mail único |
| `data_cadastro` | DATE | Data de criação da conta |
| `pais` | VARCHAR(100) | País de origem |
| `created_at` | TIMESTAMP | Timestamp de inserção (watermark) |

### planos
| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL PK | Identificador do plano |
| `nome` | VARCHAR(50) | Nome: Grátis, Premium ou Família |
| `preco_mensal` | DECIMAL(8,2) | Valor mensal em R$ |
| `created_at` | TIMESTAMP | Timestamp de inserção |

### assinaturas
| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL PK | Identificador da assinatura |
| `usuario_id` | INT FK | Referência a `usuarios.id` |
| `plano_id` | INT FK | Referência a `planos.id` |
| `data_inicio` | DATE | Início da assinatura |
| `data_fim` | DATE (nullable) | Fim da assinatura — `NULL` = ativa |
| `status` | VARCHAR(20) | `ativa` ou `cancelada` |
| `created_at` | TIMESTAMP | Timestamp de inserção |

### pagamentos
| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL PK | Identificador do pagamento |
| `assinatura_id` | INT FK | Referência a `assinaturas.id` |
| `valor` | DECIMAL(8,2) | Valor cobrado em R$ |
| `data` | DATE | Data do pagamento |
| `status` | VARCHAR(20) | `pago` ou `falhou` |
| `created_at` | TIMESTAMP | Timestamp de inserção |

### artistas
| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL PK | Identificador do artista |
| `nome` | VARCHAR(200) | Nome artístico |
| `pais` | VARCHAR(100) | País de origem |
| `created_at` | TIMESTAMP | Timestamp de inserção |

### albuns
| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL PK | Identificador do álbum |
| `artista_id` | INT FK | Referência a `artistas.id` |
| `titulo` | VARCHAR(300) | Título do álbum |
| `ano_lancamento` | SMALLINT | Ano de lançamento |
| `created_at` | TIMESTAMP | Timestamp de inserção |

### musicas
| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL PK | Identificador da música |
| `album_id` | INT FK | Referência a `albuns.id` |
| `artista_id` | INT FK | Referência a `artistas.id` |
| `genero_id` | INT FK | Referência a `generos.id` |
| `titulo` | VARCHAR(300) | Título da música |
| `duracao_ms` | INT | Duração em milissegundos |
| `created_at` | TIMESTAMP | Timestamp de inserção |

### generos
| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL PK | Identificador do gênero |
| `nome` | VARCHAR(100) | Nome: Pop, Rock, MPB, etc. |
| `created_at` | TIMESTAMP | Timestamp de inserção |

### playlists
| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL PK | Identificador da playlist |
| `usuario_id` | INT FK | Referência a `usuarios.id` |
| `nome` | VARCHAR(300) | Nome da playlist |
| `created_at` | TIMESTAMP | Timestamp de inserção |

### playlist_musicas
| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL PK | Identificador |
| `playlist_id` | INT FK | Referência a `playlists.id` |
| `musica_id` | INT FK | Referência a `musicas.id` |
| `ordem` | SMALLINT | Posição da música na playlist |
| `created_at` | TIMESTAMP | Timestamp de inserção |

### reproducoes ⭐ (fato principal)
| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL PK | Identificador do play |
| `usuario_id` | INT FK | Referência a `usuarios.id` |
| `musica_id` | INT FK | Referência a `musicas.id` |
| `dispositivo_id` | INT FK | Referência a `dispositivos.id` |
| `timestamp` | TIMESTAMP | Momento do play |
| `ms_tocados` | INT | Milissegundos efetivamente ouvidos |
| `completou` | BOOLEAN | Se o usuário ouviu a música até o fim |
| `created_at` | TIMESTAMP | Timestamp de inserção (watermark) |

### dispositivos
| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL PK | Identificador do dispositivo |
| `usuario_id` | INT FK | Referência a `usuarios.id` |
| `tipo` | VARCHAR(20) | `mobile`, `web` ou `desktop` |
| `so` | VARCHAR(50) | Sistema operacional |
| `created_at` | TIMESTAMP | Timestamp de inserção |

---

## Tabelas Gold (PostgreSQL — schema gold / Delta Lake)

### fato_reproducao
| Coluna | Tipo | Descrição |
|---|---|---|
| `data_id` | INT | FK → `dim_tempo.data_id` (formato yyyyMMdd) |
| `usuario_id` | INT | FK → `dim_usuario.usuario_id` |
| `musica_id` | INT | FK → `dim_musica.musica_id` |
| `artista_id` | INT | FK → `dim_artista.artista_id` |
| `ms_tocados` | INT | Milissegundos ouvidos |
| `completou` | BOOLEAN | `ms_tocados >= 90%` da `duracao_ms` |
| `contagem` | INT | Sempre 1 — facilita `SUM` sem `COUNT` |
| `ano_mes` | STRING | Partição — ex: `2026-06` |

### fato_pagamento
| Coluna | Tipo | Descrição |
|---|---|---|
| `data_id` | INT | FK → `dim_tempo.data_id` |
| `usuario_id` | INT | FK → `dim_usuario.usuario_id` |
| `plano_id` | INT | FK → `dim_plano.plano_id` |
| `valor` | DECIMAL(8,2) | Valor cobrado em R$ |
| `pago` | BOOLEAN | `true` = pago / `false` = falhou |
| `ano_mes` | STRING | Partição — ex: `2026-06` |

### dim_tempo
| Coluna | Tipo | Descrição |
|---|---|---|
| `data_id` | INT PK | Formato yyyyMMdd — ex: `20260615` |
| `data` | DATE | Data completa |
| `ano` | INT | Ano |
| `mes` | INT | Mês (1–12) |
| `dia` | INT | Dia do mês |
| `dia_semana` | STRING | Ex: `Segunda-feira` |
| `ano_mes` | STRING | Ex: `2026-06` |

### dim_usuario
| Coluna | Tipo | Descrição |
|---|---|---|
| `usuario_id` | INT PK | Chave natural de `usuarios.id` |
| `nome` | STRING | Nome do usuário |
| `pais` | STRING | País |
| `data_cadastro` | DATE | Data de criação da conta |

### dim_plano
| Coluna | Tipo | Descrição |
|---|---|---|
| `plano_id` | INT PK | Chave natural de `planos.id` |
| `nome` | STRING | Grátis, Premium ou Família |
| `preco_mensal` | DECIMAL(8,2) | Valor mensal em R$ |

### dim_artista
| Coluna | Tipo | Descrição |
|---|---|---|
| `artista_id` | INT PK | Chave natural de `artistas.id` |
| `nome` | STRING | Nome artístico |
| `pais` | STRING | País de origem |

### dim_musica
| Coluna | Tipo | Descrição |
|---|---|---|
| `musica_id` | INT PK | Chave natural de `musicas.id` |
| `titulo` | STRING | Título da música |
| `genero` | STRING | Gênero musical (desnormalizado) |
| `album` | STRING | Título do álbum (desnormalizado) |
| `artista_id` | INT | FK → `dim_artista` |
| `duracao_ms` | INT | Duração em milissegundos |

---

## Regras de Negócio

| Termo | Definição |
|---|---|
| **Play válido** | `ms_tocados >= 30.000 ms` (30 segundos) |
| **completou** | `ms_tocados >= 90% * duracao_ms` da música |
| **Watermark** | Maior `created_at` já processado — base da carga incremental |
| **ingestao_date** | Data em que o dado entrou na Bronze |
| **ano_mes** | String no formato `yyyy-MM` — partição de Silver e Gold |
