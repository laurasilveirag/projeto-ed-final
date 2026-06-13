from pyspark.sql import SparkSession
from minio import Minio
from pathlib import Path

DIMENSOES = [
    "usuarios",
    "planos",
    "artistas",
    "albuns",
    "musicas",
    "generos",
    "playlists",
    "dispositivos",
]


def criar_spark():
    return (
        SparkSession.builder
        .appName("landing-dimensoes")
        .config(
            "spark.jars",
            "/opt/spark/jars/postgresql-42.7.3.jar"
        )
        .getOrCreate()
    )


def criar_cliente_minio():
    return Minio(
        "minio:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False
    )


def main():
    spark = criar_spark()

    cliente_minio = criar_cliente_minio()

    print("Testando conexão com MinIO...")

    buckets = cliente_minio.list_buckets()

    for bucket in buckets:
        print(f"Bucket encontrado: {bucket.name}")

    jdbc_url = "jdbc:postgresql://postgres:5432/streaming"

    propriedades = {
        "user": "streaming",
        "password": "streaming123",
        "driver": "org.postgresql.Driver"
    }

    for tabela in DIMENSOES:

        print(f"\n{'=' * 50}")
        print(f"Processando tabela: {tabela}")
        print(f"{'=' * 50}")

        df = spark.read.jdbc(
            url=jdbc_url,
            table=tabela,
            properties=propriedades
        )

        total = df.count()
        print(f"Total de registros: {total}")

        caminho_local = f"/tmp/landing/{tabela}"

        df.write \
            .mode("overwrite") \
            .option("header", "true") \
            .csv(caminho_local)

        csv_dir = Path(caminho_local)

        arquivo_csv = next(
            arquivo
            for arquivo in csv_dir.iterdir()
            if arquivo.name.endswith(".csv")
        )

        cliente_minio.fput_object(
            "landing",
            f"{tabela}/{tabela}.csv",
            str(arquivo_csv)
        )

        print(f"{tabela}.csv enviado para o MinIO!")

    print("\nIngestão das dimensões concluída com sucesso!")

    spark.stop()


if __name__ == "__main__":
    main()