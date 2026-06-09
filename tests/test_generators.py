import os
import pytest


def test_config_reads_env(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "myhost")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    monkeypatch.setenv("POSTGRES_DB", "mydb")
    monkeypatch.setenv("POSTGRES_USER", "myuser")
    monkeypatch.setenv("POSTGRES_PASSWORD", "mypass")

    import importlib
    import src.seed.config as cfg
    importlib.reload(cfg)

    assert cfg.DB_HOST == "myhost"
    assert cfg.DB_PORT == 5433
    assert cfg.DB_NAME == "mydb"


from src.seed.generators import (
    gen_generos, gen_planos, gen_artistas,
    gen_albuns, gen_musicas, gen_usuarios,
    gen_dispositivos, gen_assinaturas, gen_pagamentos,
    gen_playlists, gen_playlist_musicas, gen_reproducoes,
)


def test_gen_generos_count():
    rows = gen_generos()
    assert len(rows) == 30


def test_gen_planos_count():
    rows = gen_planos()
    assert len(rows) == 3


def test_gen_artistas_count():
    rows = gen_artistas(500)
    assert len(rows) == 500


def test_gen_albuns_uses_artista_ids():
    artista_ids = list(range(1, 11))
    rows = gen_albuns(artista_ids, n=50)
    assert len(rows) == 50
    for row in rows:
        assert row[0] in artista_ids  # artista_id is first field


def test_gen_musicas_count():
    artista_ids = list(range(1, 6))
    album_ids   = list(range(1, 11))
    genero_ids  = list(range(1, 4))
    rows = gen_musicas(album_ids, artista_ids, genero_ids, n=100)
    assert len(rows) == 100
    for row in rows:
        assert row[4] > 0  # duracao_ms positive


def test_gen_usuarios_emails_unique():
    rows = gen_usuarios(200)
    emails = [r[1] for r in rows]
    assert len(emails) == len(set(emails))


def test_gen_reproducoes_ms_tocados_positive():
    usuario_ids     = list(range(1, 11))
    musica_ids      = list(range(1, 21))
    dispositivo_ids = list(range(1, 11))
    duracoes        = {i: 180_000 for i in range(1, 21)}
    rows = gen_reproducoes(usuario_ids, musica_ids, dispositivo_ids, duracoes, n=100)
    assert len(rows) == 100
    for row in rows:
        assert row[4] >= 0  # ms_tocados non-negative


def test_gen_assinaturas_15pct_canceladas():
    usuario_ids = list(range(1, 101))
    plano_ids   = [1, 2, 3]
    rows = gen_assinaturas(usuario_ids, plano_ids, n=200)
    canceladas = sum(1 for r in rows if r[4] == "cancelada")
    assert 0.05 <= canceladas / len(rows) <= 0.30  # ~15% ±10%
