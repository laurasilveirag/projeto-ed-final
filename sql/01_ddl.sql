-- sql/01_ddl.sql
CREATE SCHEMA IF NOT EXISTS public;

CREATE TABLE IF NOT EXISTS generos (
    id          SERIAL PRIMARY KEY,
    nome        VARCHAR(100) NOT NULL UNIQUE,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS planos (
    id             SERIAL PRIMARY KEY,
    nome           VARCHAR(50)  NOT NULL UNIQUE,
    preco_mensal   NUMERIC(8,2) NOT NULL,
    created_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS artistas (
    id          SERIAL PRIMARY KEY,
    nome        VARCHAR(200) NOT NULL,
    pais        VARCHAR(100) NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS albuns (
    id               SERIAL PRIMARY KEY,
    artista_id       INT NOT NULL REFERENCES artistas(id),
    titulo           VARCHAR(300) NOT NULL,
    ano_lancamento   SMALLINT NOT NULL,
    created_at       TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS musicas (
    id           SERIAL PRIMARY KEY,
    album_id     INT NOT NULL REFERENCES albuns(id),
    artista_id   INT NOT NULL REFERENCES artistas(id),
    genero_id    INT NOT NULL REFERENCES generos(id),
    titulo       VARCHAR(300) NOT NULL,
    duracao_ms   INT NOT NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS usuarios (
    id              SERIAL PRIMARY KEY,
    nome            VARCHAR(200) NOT NULL,
    email           VARCHAR(200) NOT NULL UNIQUE,
    data_cadastro   DATE NOT NULL,
    pais            VARCHAR(100) NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dispositivos (
    id          SERIAL PRIMARY KEY,
    usuario_id  INT NOT NULL REFERENCES usuarios(id),
    tipo        VARCHAR(20)  NOT NULL CHECK (tipo IN ('mobile','web','desktop')),
    so          VARCHAR(50)  NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS assinaturas (
    id           SERIAL PRIMARY KEY,
    usuario_id   INT NOT NULL REFERENCES usuarios(id),
    plano_id     INT NOT NULL REFERENCES planos(id),
    data_inicio  DATE NOT NULL,
    data_fim     DATE,
    status       VARCHAR(20) NOT NULL CHECK (status IN ('ativa','cancelada')),
    created_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pagamentos (
    id              SERIAL PRIMARY KEY,
    assinatura_id   INT NOT NULL REFERENCES assinaturas(id),
    valor           NUMERIC(8,2) NOT NULL,
    data            DATE NOT NULL,
    status          VARCHAR(20) NOT NULL CHECK (status IN ('pago','falhou')),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS playlists (
    id          SERIAL PRIMARY KEY,
    usuario_id  INT NOT NULL REFERENCES usuarios(id),
    nome        VARCHAR(300) NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS playlist_musicas (
    id           SERIAL PRIMARY KEY,
    playlist_id  INT NOT NULL REFERENCES playlists(id),
    musica_id    INT NOT NULL REFERENCES musicas(id),
    ordem        SMALLINT NOT NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reproducoes (
    id             SERIAL PRIMARY KEY,
    usuario_id     INT NOT NULL REFERENCES usuarios(id),
    musica_id      INT NOT NULL REFERENCES musicas(id),
    dispositivo_id INT NOT NULL REFERENCES dispositivos(id),
    timestamp      TIMESTAMP NOT NULL,
    ms_tocados     INT NOT NULL,
    completou      BOOLEAN NOT NULL,
    created_at     TIMESTAMP NOT NULL DEFAULT NOW()
);
