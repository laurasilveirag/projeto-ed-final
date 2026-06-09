import psycopg2
from psycopg2.extras import execute_values
from src.seed import config


def get_connection():
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )


def bulk_insert(conn, table: str, columns: list[str], rows: list[tuple]) -> None:
    if not rows:
        return
    col_str = ", ".join(columns)
    sql = f"INSERT INTO {table} ({col_str}) VALUES %s"
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=1000)
    conn.commit()


def truncate_all(conn) -> None:
    tables = [
        "reproducoes", "playlist_musicas", "pagamentos", "assinaturas",
        "dispositivos", "playlists", "musicas", "albuns", "artistas",
        "generos", "usuarios", "planos",
    ]
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE")
    conn.commit()
