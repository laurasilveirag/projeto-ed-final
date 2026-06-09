import random
from datetime import datetime, timedelta, date
from faker import Faker

fake = Faker("pt_BR")
random.seed(42)
Faker.seed(42)

_NOW = datetime.now()
_THREE_YEARS_AGO = _NOW - timedelta(days=3 * 365)


def _rand_ts() -> datetime:
    delta = _NOW - _THREE_YEARS_AGO
    return _THREE_YEARS_AGO + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def _rand_date() -> date:
    return _rand_ts().date()


GENEROS_NOMES = [
    "Pop", "Rock", "Sertanejo", "Funk", "Forró", "MPB", "Samba", "Pagode",
    "Eletrônica", "Hip-Hop", "R&B", "Reggae", "Gospel", "Metal", "Blues",
    "Jazz", "Clássica", "Indie", "Bossa Nova", "Axé", "Baião", "Reggaeton",
    "K-Pop", "Country", "Soul", "Punk", "Disco", "Techno", "Trap", "Lo-Fi",
]


def gen_generos() -> list[tuple]:
    ts = _NOW
    return [(nome, ts) for nome in GENEROS_NOMES]


PLANOS_DATA = [
    ("Grátis",  0.00),
    ("Premium", 19.90),
    ("Família", 29.90),
]


def gen_planos() -> list[tuple]:
    ts = _NOW
    return [(nome, preco, ts) for nome, preco in PLANOS_DATA]


PAISES = [
    "Brasil", "EUA", "Reino Unido", "Canadá", "Austrália", "Argentina",
    "México", "Portugal", "Espanha", "França", "Alemanha", "Japão", "Coreia do Sul",
]


def gen_artistas(n: int = 500) -> list[tuple]:
    rows = []
    for _ in range(n):
        ts = _rand_ts()
        rows.append((fake.name(), random.choice(PAISES), ts))
    return rows


def gen_albuns(artista_ids: list[int], n: int = 2000) -> list[tuple]:
    rows = []
    for _ in range(n):
        ts = _rand_ts()
        ano = random.randint(1990, 2024)
        rows.append((random.choice(artista_ids), fake.catch_phrase(), ano, ts))
    return rows


def gen_musicas(
    album_ids: list[int],
    artista_ids: list[int],
    genero_ids: list[int],
    n: int = 10000,
) -> list[tuple]:
    rows = []
    for _ in range(n):
        ts = _rand_ts()
        duracao_ms = random.randint(90_000, 360_000)
        rows.append((
            random.choice(album_ids),
            random.choice(artista_ids),
            random.choice(genero_ids),
            fake.catch_phrase(),
            duracao_ms,
            ts,
        ))
    return rows


def gen_usuarios(n: int = 3000) -> list[tuple]:
    rows = []
    for _ in range(n):
        ts = _rand_ts()
        rows.append((fake.name(), fake.unique.email(), ts.date(), random.choice(PAISES), ts))
    return rows


TIPOS_DISPOSITIVO = ["mobile", "web", "desktop"]
SISTEMAS = {
    "mobile":  ["Android", "iOS"],
    "web":     ["Chrome/Windows", "Firefox/Linux", "Safari/macOS"],
    "desktop": ["Windows 11", "macOS Ventura", "Ubuntu 22.04"],
}


def gen_dispositivos(usuario_ids: list[int], n: int = 5000) -> list[tuple]:
    rows = []
    for _ in range(n):
        ts = _rand_ts()
        tipo = random.choice(TIPOS_DISPOSITIVO)
        so = random.choice(SISTEMAS[tipo])
        rows.append((random.choice(usuario_ids), tipo, so, ts))
    return rows


def gen_assinaturas(
    usuario_ids: list[int],
    plano_ids: list[int],
    n: int = 3500,
) -> list[tuple]:
    rows = []
    for _ in range(n):
        ts = _rand_ts()
        data_inicio = ts.date()
        cancelada = random.random() < 0.15
        if cancelada:
            data_fim = data_inicio + timedelta(days=random.randint(30, 365))
            if data_fim > date.today():
                data_fim = date.today()
            status = "cancelada"
        else:
            data_fim = None
            status = "ativa"
        rows.append((
            random.choice(usuario_ids),
            random.choice(plano_ids),
            data_inicio,
            data_fim,
            status,
            ts,
        ))
    return rows


def gen_pagamentos(
    assinatura_ids: list[int],
    assinatura_valores: dict[int, float],
    n: int = 10500,
) -> list[tuple]:
    rows = []
    for _ in range(n):
        ts = _rand_ts()
        assinatura_id = random.choice(assinatura_ids)
        valor = assinatura_valores.get(assinatura_id, 19.90)
        status = "pago" if random.random() < 0.92 else "falhou"
        rows.append((assinatura_id, valor, ts.date(), status, ts))
    return rows


def gen_playlists(usuario_ids: list[int], n: int = 2000) -> list[tuple]:
    rows = []
    for _ in range(n):
        ts = _rand_ts()
        rows.append((random.choice(usuario_ids), fake.catch_phrase(), ts))
    return rows


def gen_playlist_musicas(
    playlist_ids: list[int],
    musica_ids: list[int],
    n: int = 20000,
) -> list[tuple]:
    rows = []
    seen: set[tuple] = set()
    attempts = 0
    while len(rows) < n and attempts < n * 3:
        attempts += 1
        pl = random.choice(playlist_ids)
        ms = random.choice(musica_ids)
        if (pl, ms) in seen:
            continue
        seen.add((pl, ms))
        ts = _rand_ts()
        ordem = random.randint(1, 100)
        rows.append((pl, ms, ordem, ts))
    if len(rows) < n:
        raise RuntimeError(
            f"gen_playlist_musicas: only {len(rows)}/{n} unique pairs possible "
            f"with {len(playlist_ids)} playlists × {len(musica_ids)} músicas"
        )
    return rows


def gen_reproducoes(
    usuario_ids: list[int],
    musica_ids: list[int],
    dispositivo_ids: list[int],
    duracoes: dict[int, int],
    n: int = 70000,
) -> list[tuple]:
    rows = []
    for _ in range(n):
        ts = _rand_ts()
        musica_id = random.choice(musica_ids)
        duracao = duracoes.get(musica_id, 200_000)
        if random.random() < 0.20:
            ms_tocados = random.randint(0, 29_999)
        else:
            ms_tocados = random.randint(30_000, duracao)
        completou = ms_tocados >= int(duracao * 0.9)
        rows.append((
            random.choice(usuario_ids),
            musica_id,
            random.choice(dispositivo_ids),
            ts,
            ms_tocados,
            completou,
            ts,
        ))
    return rows
