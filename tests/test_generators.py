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
