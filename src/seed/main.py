import sys
import time
import click
from src.seed.db import get_connection, bulk_insert, truncate_all
from src.seed.generators import (
    gen_generos, gen_planos, gen_artistas, gen_albuns,
    gen_musicas, gen_usuarios, gen_dispositivos, gen_assinaturas,
    gen_pagamentos, gen_playlists, gen_playlist_musicas, gen_reproducoes,
)


def _ids(conn, table: str) -> list[int]:
    with conn.cursor() as cur:
        cur.execute(f"SELECT id FROM {table} ORDER BY id")
        return [r[0] for r in cur.fetchall()]


def _col(conn, table: str, col: str) -> dict:
    with conn.cursor() as cur:
        cur.execute(f"SELECT id, {col} FROM {table}")
        return {r[0]: r[1] for r in cur.fetchall()}


@click.command()
@click.option("--truncate/--no-truncate", default=False, help="Limpa as tabelas antes de inserir")
def main(truncate: bool) -> None:
    click.echo("Conectando ao banco...")
    conn = None
    for attempt in range(30):
        try:
            conn = get_connection()
            break
        except Exception as e:
            if attempt == 29:
                click.echo(f"Falha ao conectar: {e}", err=True)
                sys.exit(1)
            click.echo(f"Aguardando banco... tentativa {attempt + 1}/30")
            time.sleep(2)

    if truncate:
        click.echo("Truncando tabelas...")
        truncate_all(conn)

    click.echo("Inserindo gêneros (30)...")
    bulk_insert(conn, "generos", ["nome", "created_at"], gen_generos())

    click.echo("Inserindo planos (3)...")
    bulk_insert(conn, "planos", ["nome", "preco_mensal", "created_at"], gen_planos())

    click.echo("Inserindo artistas (500)...")
    bulk_insert(conn, "artistas", ["nome", "pais", "created_at"], gen_artistas(500))

    artista_ids = _ids(conn, "artistas")

    click.echo("Inserindo álbuns (2000)...")
    bulk_insert(
        conn, "albuns",
        ["artista_id", "titulo", "ano_lancamento", "created_at"],
        gen_albuns(artista_ids, n=2000),
    )

    album_ids  = _ids(conn, "albuns")
    genero_ids = _ids(conn, "generos")

    click.echo("Inserindo músicas (10000)...")
    bulk_insert(
        conn, "musicas",
        ["album_id", "artista_id", "genero_id", "titulo", "duracao_ms", "created_at"],
        gen_musicas(album_ids, artista_ids, genero_ids, n=10000),
    )

    click.echo("Inserindo usuários (3000)...")
    bulk_insert(
        conn, "usuarios",
        ["nome", "email", "data_cadastro", "pais", "created_at"],
        gen_usuarios(3000),
    )

    usuario_ids = _ids(conn, "usuarios")

    click.echo("Inserindo dispositivos (5000)...")
    bulk_insert(
        conn, "dispositivos",
        ["usuario_id", "tipo", "so", "created_at"],
        gen_dispositivos(usuario_ids, n=5000),
    )

    plano_ids = _ids(conn, "planos")

    click.echo("Inserindo assinaturas (3500)...")
    bulk_insert(
        conn, "assinaturas",
        ["usuario_id", "plano_id", "data_inicio", "data_fim", "status", "created_at"],
        gen_assinaturas(usuario_ids, plano_ids, n=3500),
    )

    assinatura_ids  = _ids(conn, "assinaturas")
    preco_por_plano = _col(conn, "planos", "preco_mensal")

    with conn.cursor() as cur:
        cur.execute("SELECT id, plano_id FROM assinaturas")
        assin_plano = {r[0]: r[1] for r in cur.fetchall()}
    assin_valor = {sid: float(preco_por_plano[plano_id])
                   for sid, plano_id in assin_plano.items()}

    click.echo("Inserindo pagamentos (10500)...")
    bulk_insert(
        conn, "pagamentos",
        ["assinatura_id", "valor", "data", "status", "created_at"],
        gen_pagamentos(assinatura_ids, assin_valor, n=10500),
    )

    click.echo("Inserindo playlists (2000)...")
    bulk_insert(
        conn, "playlists",
        ["usuario_id", "nome", "created_at"],
        gen_playlists(usuario_ids, n=2000),
    )

    musica_ids   = _ids(conn, "musicas")
    playlist_ids = _ids(conn, "playlists")

    click.echo("Inserindo playlist_musicas (20000)...")
    bulk_insert(
        conn, "playlist_musicas",
        ["playlist_id", "musica_id", "ordem", "created_at"],
        gen_playlist_musicas(playlist_ids, musica_ids, n=20000),
    )

    dispositivo_ids = _ids(conn, "dispositivos")
    duracoes        = _col(conn, "musicas", "duracao_ms")

    click.echo("Inserindo reproduções (70000)...")
    bulk_insert(
        conn, "reproducoes",
        ["usuario_id", "musica_id", "dispositivo_id", "timestamp",
         "ms_tocados", "completou", "created_at"],
        gen_reproducoes(usuario_ids, musica_ids, dispositivo_ids, duracoes, n=70000),
    )

    click.echo("\nSeed concluído! Contagem final:")
    with conn.cursor() as cur:
        for table in [
            "generos", "planos", "artistas", "albuns", "musicas", "usuarios",
            "dispositivos", "assinaturas", "pagamentos", "playlists",
            "playlist_musicas", "reproducoes",
        ]:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            click.echo(f"  {table:25s}: {count:>8,}")

    conn.close()


if __name__ == "__main__":
    main()
