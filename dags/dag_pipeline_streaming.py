"""
DAG: pipeline_streaming
Orquestra o pipeline completo: Postgres -> Landing -> Bronze -> Silver -> Gold -> Postgres(gold)
Carga incremental via watermark de created_at nas tabelas fato (ADR-0001).
"""

import os
import shutil
from datetime import datetime, date, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

# ── Constantes de ambiente ────────────────────────────────────────────────────

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB   = os.getenv("POSTGRES_DB",   "streaming")
POSTGRES_USER = os.getenv("POSTGRES_USER", "streaming")
POSTGRES_PASS = os.getenv("POSTGRES_PASSWORD", "streaming123")

MINIO_HOST = "minio:9000"
MINIO_USER = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_PASS = os.getenv("MINIO_SECRET_KEY", "minioadmin")

JDBC_URL  = f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
JDBC_PROPS = {
    "user":     POSTGRES_USER,
    "password": POSTGRES_PASS,
    "driver":   "org.postgresql.Driver",
}
JDBC_JAR = "/opt/spark/jars/postgresql-42.7.3.jar"
TS_FMT   = "yyyy-MM-dd HH:mm:ss"


# ── Helpers ───────────────────────────────────────────────────────────────────

DELTA_JARS = ",".join([
    "/opt/spark/jars/delta-spark_2.12-3.2.0.jar",
    "/opt/spark/jars/delta-storage-3.2.0.jar",
])


def _get_spark(app_name: str, with_jdbc: bool = False):
    from pyspark.sql import SparkSession

    jars = DELTA_JARS + (f",{JDBC_JAR}" if with_jdbc else "")

    return (
        SparkSession.builder
        .appName(app_name)
        .config("spark.jars", jars)
        .config("spark.sql.extensions",
                "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )


def _get_minio():
    from minio import Minio
    return Minio(MINIO_HOST, access_key=MINIO_USER, secret_key=MINIO_PASS, secure=False)


def _download_delta(bucket: str, prefix: str, local_dir: Path, cliente) -> None:
    if local_dir.exists():
        shutil.rmtree(local_dir)
    local_dir.mkdir(parents=True)
    for obj in cliente.list_objects(bucket, prefix=f"{prefix}/", recursive=True):
        rel = obj.object_name[len(prefix) + 1:]
        dst = local_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        cliente.fget_object(bucket, obj.object_name, str(dst))


def _upload_delta(local_dir: Path, bucket: str, prefix: str, cliente) -> None:
    for arq in sorted(local_dir.rglob("*")):
        if arq.is_file():
            cliente.fput_object(bucket, f"{prefix}/{arq.relative_to(local_dir)}", str(arq))


# ── Tasks ─────────────────────────────────────────────────────────────────────

def criar_buckets():
    cliente = _get_minio()
    existentes = {b.name for b in cliente.list_buckets()}
    for bucket in ["landing", "bronze", "silver", "gold"]:
        if bucket not in existentes:
            cliente.make_bucket(bucket)
            print(f"Bucket criado: {bucket}")
        else:
            print(f"Bucket já existe: {bucket}")


def landing_dimensoes():
    spark = _get_spark("landing-dimensoes", with_jdbc=True)
    cliente = _get_minio()
    DIMENSOES = ["usuarios", "planos", "artistas", "albuns", "musicas",
                 "generos", "playlists", "dispositivos"]
    try:
        for tabela in DIMENSOES:
            df = spark.read.jdbc(url=JDBC_URL, table=tabela, properties=JDBC_PROPS)
            local = Path(f"/tmp/dag_landing/{tabela}")
            if local.exists():
                shutil.rmtree(local)
            (df.write.mode("overwrite")
               .option("header", "true")
               .option("timestampFormat", TS_FMT)
               .csv(str(local)))
            csv_path = next(f for f in local.iterdir() if f.suffix == ".csv")
            cliente.fput_object("landing", f"{tabela}/{tabela}.csv", str(csv_path))
            print(f"landing/{tabela}: {df.count():,} registros")
    finally:
        spark.stop()


def landing_fatos():
    """Carga incremental por watermark de created_at (ADR-0001)."""
    from pyspark.sql import functions as F

    spark = _get_spark("landing-fatos", with_jdbc=True)
    cliente = _get_minio()
    FATOS = ["reproducoes", "pagamentos", "assinaturas"]

    watermark = Variable.get("watermark_created_at", default_var="1970-01-01 00:00:00")
    print(f"Watermark atual: {watermark}")
    novo_watermark = watermark

    try:
        for tabela in FATOS:
            query = f"(SELECT * FROM {tabela} WHERE created_at > '{watermark}') AS t"
            df = spark.read.jdbc(url=JDBC_URL, table=query, properties=JDBC_PROPS)
            total = df.count()
            print(f"landing/{tabela}: {total:,} registros novos")

            local = Path(f"/tmp/dag_landing/{tabela}")
            if local.exists():
                shutil.rmtree(local)
            (df.write.mode("overwrite")
               .option("header", "true")
               .option("timestampFormat", TS_FMT)
               .csv(str(local)))
            csv_path = next(f for f in local.iterdir() if f.suffix == ".csv")
            cliente.fput_object("landing", f"{tabela}/{tabela}.csv", str(csv_path))

            if total > 0:
                max_ts = df.agg(F.max("created_at")).first()[0]
                if max_ts and str(max_ts) > novo_watermark:
                    novo_watermark = str(max_ts)
    finally:
        spark.stop()

    Variable.set("watermark_created_at", novo_watermark)
    print(f"Novo watermark: {novo_watermark}")


def bronze_dimensoes():
    from pyspark.sql import functions as F
    from pyspark.sql.types import (StructType, StructField, IntegerType, ShortType,
                                   StringType, TimestampType, DateType, DecimalType)

    SCHEMAS = {
        "usuarios": StructType([
            StructField("id",            IntegerType(),    False),
            StructField("nome",          StringType(),     False),
            StructField("email",         StringType(),     False),
            StructField("data_cadastro", DateType(),       False),
            StructField("pais",          StringType(),     False),
            StructField("created_at",    TimestampType(),  False),
        ]),
        "planos": StructType([
            StructField("id",           IntegerType(),    False),
            StructField("nome",         StringType(),     False),
            StructField("preco_mensal", DecimalType(8,2), False),
            StructField("created_at",   TimestampType(),  False),
        ]),
        "artistas": StructType([
            StructField("id",         IntegerType(),   False),
            StructField("nome",       StringType(),    False),
            StructField("pais",       StringType(),    False),
            StructField("created_at", TimestampType(), False),
        ]),
        "albuns": StructType([
            StructField("id",             IntegerType(),   False),
            StructField("artista_id",     IntegerType(),   False),
            StructField("titulo",         StringType(),    False),
            StructField("ano_lancamento", ShortType(),     False),
            StructField("created_at",     TimestampType(), False),
        ]),
        "musicas": StructType([
            StructField("id",         IntegerType(),   False),
            StructField("album_id",   IntegerType(),   False),
            StructField("artista_id", IntegerType(),   False),
            StructField("genero_id",  IntegerType(),   False),
            StructField("titulo",     StringType(),    False),
            StructField("duracao_ms", IntegerType(),   False),
            StructField("created_at", TimestampType(), False),
        ]),
        "generos": StructType([
            StructField("id",         IntegerType(),   False),
            StructField("nome",       StringType(),    False),
            StructField("created_at", TimestampType(), False),
        ]),
        "playlists": StructType([
            StructField("id",         IntegerType(),   False),
            StructField("usuario_id", IntegerType(),   False),
            StructField("nome",       StringType(),    False),
            StructField("created_at", TimestampType(), False),
        ]),
        "dispositivos": StructType([
            StructField("id",         IntegerType(),   False),
            StructField("usuario_id", IntegerType(),   False),
            StructField("tipo",       StringType(),    False),
            StructField("so",         StringType(),    False),
            StructField("created_at", TimestampType(), False),
        ]),
    }

    spark    = _get_spark("bronze-dimensoes")
    cliente  = _get_minio()
    ingestao = str(date.today())

    try:
        for tabela, schema in SCHEMAS.items():
            local_csv = Path(f"/tmp/dag_landing/{tabela}")
            local_csv.mkdir(parents=True, exist_ok=True)
            csv_path = local_csv / f"{tabela}.csv"
            cliente.fget_object("landing", f"{tabela}/{tabela}.csv", str(csv_path))

            df = (spark.read
                  .option("header", "true")
                  .option("timestampFormat", TS_FMT)
                  .option("dateFormat", "yyyy-MM-dd")
                  .schema(schema)
                  .csv(str(csv_path))
                  .withColumn("ingestao_date", F.lit(ingestao).cast("date")))

            local_delta = Path(f"/tmp/dag_bronze/{tabela}")
            if local_delta.exists():
                shutil.rmtree(local_delta)
            (df.write.format("delta").mode("overwrite")
               .partitionBy("ingestao_date").save(str(local_delta)))
            _upload_delta(local_delta, "bronze", f"dimensoes/{tabela}", cliente)
            print(f"bronze/dimensoes/{tabela}: {df.count():,} registros")
    finally:
        spark.stop()


def bronze_fatos():
    from pyspark.sql import functions as F
    from pyspark.sql.types import (StructType, StructField, IntegerType, StringType,
                                   TimestampType, DateType, BooleanType, DecimalType)

    SCHEMAS = {
        "reproducoes": StructType([
            StructField("id",             IntegerType(),    False),
            StructField("usuario_id",     IntegerType(),    False),
            StructField("musica_id",      IntegerType(),    False),
            StructField("dispositivo_id", IntegerType(),    False),
            StructField("timestamp",      TimestampType(),  False),
            StructField("ms_tocados",     IntegerType(),    False),
            StructField("completou",      BooleanType(),    False),
            StructField("created_at",     TimestampType(),  False),
        ]),
        "pagamentos": StructType([
            StructField("id",            IntegerType(),    False),
            StructField("assinatura_id", IntegerType(),    False),
            StructField("valor",         DecimalType(8,2), False),
            StructField("data",          DateType(),       False),
            StructField("status",        StringType(),     False),
            StructField("created_at",    TimestampType(),  False),
        ]),
        "assinaturas": StructType([
            StructField("id",          IntegerType(),   False),
            StructField("usuario_id",  IntegerType(),   False),
            StructField("plano_id",    IntegerType(),   False),
            StructField("data_inicio", DateType(),      False),
            StructField("data_fim",    DateType(),      True),
            StructField("status",      StringType(),    False),
            StructField("created_at",  TimestampType(), False),
        ]),
    }

    spark    = _get_spark("bronze-fatos")
    cliente  = _get_minio()
    ingestao = str(date.today())

    try:
        for tabela, schema in SCHEMAS.items():
            local_csv = Path(f"/tmp/dag_landing/{tabela}")
            local_csv.mkdir(parents=True, exist_ok=True)
            csv_path = local_csv / f"{tabela}.csv"
            cliente.fget_object("landing", f"{tabela}/{tabela}.csv", str(csv_path))

            df = (spark.read
                  .option("header", "true")
                  .option("timestampFormat", TS_FMT)
                  .option("dateFormat", "yyyy-MM-dd")
                  .schema(schema)
                  .csv(str(csv_path))
                  .withColumn("ingestao_date", F.lit(ingestao).cast("date")))

            local_delta = Path(f"/tmp/dag_bronze/{tabela}")
            if local_delta.exists():
                shutil.rmtree(local_delta)
            (df.write.format("delta").mode("overwrite")
               .partitionBy("ingestao_date").save(str(local_delta)))
            _upload_delta(local_delta, "bronze", f"fatos/{tabela}", cliente)
            print(f"bronze/fatos/{tabela}: {df.count():,} registros")
    finally:
        spark.stop()


def silver_dimensoes():
    from pyspark.sql import functions as F

    STRING_COLS = {
        "usuarios":     ["nome", "email", "pais"],
        "planos":       ["nome"],
        "artistas":     ["nome", "pais"],
        "albuns":       ["titulo"],
        "musicas":      ["titulo"],
        "generos":      ["nome"],
        "playlists":    ["nome"],
        "dispositivos": ["tipo", "so"],
    }

    spark   = _get_spark("silver-dimensoes")
    cliente = _get_minio()

    try:
        for tabela, cols_str in STRING_COLS.items():
            local_bronze = Path(f"/tmp/dag_bronze/{tabela}")
            _download_delta("bronze", f"dimensoes/{tabela}", local_bronze, cliente)
            df = spark.read.format("delta").load(str(local_bronze))
            df = df.dropDuplicates(["id"])
            for col in cols_str:
                df = df.withColumn(col, F.trim(F.col(col)))
            local_silver = Path(f"/tmp/dag_silver/{tabela}")
            if local_silver.exists():
                shutil.rmtree(local_silver)
            df.write.format("delta").mode("overwrite").save(str(local_silver))
            _upload_delta(local_silver, "silver", f"dimensoes/{tabela}", cliente)
            print(f"silver/dimensoes/{tabela}: {df.count():,} registros")
    finally:
        spark.stop()


def silver_fatos():
    from pyspark.sql import functions as F

    spark   = _get_spark("silver-fatos")
    cliente = _get_minio()

    try:
        # Musicas necessária para calcular completou
        local_musicas = Path("/tmp/dag_bronze/musicas")
        _download_delta("bronze", "dimensoes/musicas", local_musicas, cliente)
        df_musicas = (spark.read.format("delta").load(str(local_musicas))
                      .select(F.col("id").alias("musica_id"), "duracao_ms"))

        # reproducoes
        local_bronze = Path("/tmp/dag_bronze/reproducoes")
        _download_delta("bronze", "fatos/reproducoes", local_bronze, cliente)
        df = spark.read.format("delta").load(str(local_bronze))
        df = (df.dropDuplicates(["id"])
                .filter(F.col("ms_tocados") >= 30000)
                .join(df_musicas, on="musica_id", how="left")
                .withColumn("completou", F.col("ms_tocados") >= (F.col("duracao_ms") * 0.9))
                .drop("duracao_ms")
                .withColumn("ano_mes", F.date_format("timestamp", "yyyy-MM")))
        local_silver = Path("/tmp/dag_silver/reproducoes")
        if local_silver.exists():
            shutil.rmtree(local_silver)
        df.write.format("delta").mode("overwrite").partitionBy("ano_mes").save(str(local_silver))
        _upload_delta(local_silver, "silver", "fatos/reproducoes", cliente)
        print(f"silver/fatos/reproducoes: {df.count():,} plays válidos")

        # pagamentos
        local_bronze = Path("/tmp/dag_bronze/pagamentos")
        _download_delta("bronze", "fatos/pagamentos", local_bronze, cliente)
        df = (spark.read.format("delta").load(str(local_bronze))
              .dropDuplicates(["id"])
              .withColumn("status", F.lower(F.trim(F.col("status"))))
              .withColumn("ano_mes", F.date_format(F.col("data").cast("timestamp"), "yyyy-MM")))
        local_silver = Path("/tmp/dag_silver/pagamentos")
        if local_silver.exists():
            shutil.rmtree(local_silver)
        df.write.format("delta").mode("overwrite").partitionBy("ano_mes").save(str(local_silver))
        _upload_delta(local_silver, "silver", "fatos/pagamentos", cliente)
        print(f"silver/fatos/pagamentos: {df.count():,} registros")

        # assinaturas
        local_bronze = Path("/tmp/dag_bronze/assinaturas")
        _download_delta("bronze", "fatos/assinaturas", local_bronze, cliente)
        df = (spark.read.format("delta").load(str(local_bronze))
              .dropDuplicates(["id"])
              .withColumn("status", F.lower(F.trim(F.col("status"))))
              .withColumn("ano_mes", F.date_format(F.col("data_inicio").cast("timestamp"), "yyyy-MM")))
        local_silver = Path("/tmp/dag_silver/assinaturas")
        if local_silver.exists():
            shutil.rmtree(local_silver)
        df.write.format("delta").mode("overwrite").partitionBy("ano_mes").save(str(local_silver))
        _upload_delta(local_silver, "silver", "fatos/assinaturas", cliente)
        print(f"silver/fatos/assinaturas: {df.count():,} registros")
    finally:
        spark.stop()


def gold_dimensoes():
    from pyspark.sql import functions as F

    spark   = _get_spark("gold-dimensoes")
    cliente = _get_minio()

    DIAS_SEMANA = ["Domingo", "Segunda-feira", "Terça-feira", "Quarta-feira",
                   "Quinta-feira", "Sexta-feira", "Sábado"]
    array_dias = F.array(*[F.lit(d) for d in DIAS_SEMANA])

    try:
        # dim_tempo — calendário gerado a partir do range das datas dos fatos
        local_repro = Path("/tmp/dag_gold_dim/silver/reproducoes")
        _download_delta("silver", "fatos/reproducoes", local_repro, cliente)
        local_pag = Path("/tmp/dag_gold_dim/silver/pagamentos")
        _download_delta("silver", "fatos/pagamentos", local_pag, cliente)

        df_datas = (spark.read.format("delta").load(str(local_repro))
                    .select(F.to_date("timestamp").alias("data"))
                    .union(spark.read.format("delta").load(str(local_pag))
                           .select(F.to_date("data").alias("data"))))
        data_min, data_max = df_datas.agg(F.min("data"), F.max("data")).first()

        df_tempo = (spark.sql(f"SELECT explode(sequence(to_date('{data_min}'), to_date('{data_max}'), interval 1 day)) AS data")
                    .withColumn("data_id",    F.date_format("data", "yyyyMMdd").cast("int"))
                    .withColumn("ano",        F.year("data"))
                    .withColumn("mes",        F.month("data"))
                    .withColumn("dia",        F.dayofmonth("data"))
                    .withColumn("dia_semana", F.element_at(array_dias, F.dayofweek("data")))
                    .withColumn("ano_mes",    F.date_format("data", "yyyy-MM"))
                    .select("data_id", "data", "ano", "mes", "dia", "dia_semana", "ano_mes")
                    .orderBy("data"))
        local_gold = Path("/tmp/dag_gold_dim/gold/dim_tempo")
        if local_gold.exists():
            shutil.rmtree(local_gold)
        df_tempo.write.format("delta").mode("overwrite").save(str(local_gold))
        _upload_delta(local_gold, "gold", "dimensoes/dim_tempo", cliente)
        print(f"gold/dimensoes/dim_tempo: {df_tempo.count():,} dias")

        # dim_usuario
        local_s = Path("/tmp/dag_gold_dim/silver/usuarios")
        _download_delta("silver", "dimensoes/usuarios", local_s, cliente)
        df = (spark.read.format("delta").load(str(local_s))
              .select(F.col("id").alias("usuario_id"), "nome", "pais", "data_cadastro"))
        local_gold = Path("/tmp/dag_gold_dim/gold/dim_usuario")
        if local_gold.exists():
            shutil.rmtree(local_gold)
        df.write.format("delta").mode("overwrite").save(str(local_gold))
        _upload_delta(local_gold, "gold", "dimensoes/dim_usuario", cliente)
        print(f"gold/dimensoes/dim_usuario: {df.count():,} registros")

        # dim_plano
        local_s = Path("/tmp/dag_gold_dim/silver/planos")
        _download_delta("silver", "dimensoes/planos", local_s, cliente)
        df = (spark.read.format("delta").load(str(local_s))
              .select(F.col("id").alias("plano_id"), "nome", "preco_mensal"))
        local_gold = Path("/tmp/dag_gold_dim/gold/dim_plano")
        if local_gold.exists():
            shutil.rmtree(local_gold)
        df.write.format("delta").mode("overwrite").save(str(local_gold))
        _upload_delta(local_gold, "gold", "dimensoes/dim_plano", cliente)
        print(f"gold/dimensoes/dim_plano: {df.count():,} registros")

        # dim_artista
        local_s = Path("/tmp/dag_gold_dim/silver/artistas")
        _download_delta("silver", "dimensoes/artistas", local_s, cliente)
        df = (spark.read.format("delta").load(str(local_s))
              .select(F.col("id").alias("artista_id"), "nome", "pais"))
        local_gold = Path("/tmp/dag_gold_dim/gold/dim_artista")
        if local_gold.exists():
            shutil.rmtree(local_gold)
        df.write.format("delta").mode("overwrite").save(str(local_gold))
        _upload_delta(local_gold, "gold", "dimensoes/dim_artista", cliente)
        print(f"gold/dimensoes/dim_artista: {df.count():,} registros")

        # dim_musica (join com albuns e generos)
        local_mus = Path("/tmp/dag_gold_dim/silver/musicas")
        _download_delta("silver", "dimensoes/musicas", local_mus, cliente)
        local_alb = Path("/tmp/dag_gold_dim/silver/albuns")
        _download_delta("silver", "dimensoes/albuns", local_alb, cliente)
        local_gen = Path("/tmp/dag_gold_dim/silver/generos")
        _download_delta("silver", "dimensoes/generos", local_gen, cliente)

        df_alb = (spark.read.format("delta").load(str(local_alb))
                  .select(F.col("id").alias("album_id"), F.col("titulo").alias("album")))
        df_gen = (spark.read.format("delta").load(str(local_gen))
                  .select(F.col("id").alias("genero_id"), F.col("nome").alias("genero")))
        df = (spark.read.format("delta").load(str(local_mus))
              .join(df_alb, on="album_id", how="left")
              .join(df_gen, on="genero_id", how="left")
              .select(F.col("id").alias("musica_id"), "titulo", "genero", "album", "artista_id", "duracao_ms"))
        local_gold = Path("/tmp/dag_gold_dim/gold/dim_musica")
        if local_gold.exists():
            shutil.rmtree(local_gold)
        df.write.format("delta").mode("overwrite").save(str(local_gold))
        _upload_delta(local_gold, "gold", "dimensoes/dim_musica", cliente)
        print(f"gold/dimensoes/dim_musica: {df.count():,} registros")
    finally:
        spark.stop()


def gold_fatos():
    from pyspark.sql import functions as F

    spark   = _get_spark("gold-fatos")
    cliente = _get_minio()

    try:
        # fato_reproducao
        local_repro = Path("/tmp/dag_gold_fat/silver/reproducoes")
        _download_delta("silver", "fatos/reproducoes", local_repro, cliente)
        local_mus = Path("/tmp/dag_gold_fat/silver/musicas")
        _download_delta("silver", "dimensoes/musicas", local_mus, cliente)
        df_mus_art = (spark.read.format("delta").load(str(local_mus))
                      .select(F.col("id").alias("musica_id"), "artista_id"))
        df = (spark.read.format("delta").load(str(local_repro))
              .join(df_mus_art, on="musica_id", how="left")
              .withColumn("data_id",   F.date_format("timestamp", "yyyyMMdd").cast("int"))
              .withColumn("contagem",  F.lit(1))
              .select("data_id", "usuario_id", "musica_id", "artista_id",
                      "ms_tocados", "completou", "contagem", "ano_mes"))
        local_gold = Path("/tmp/dag_gold_fat/gold/fato_reproducao")
        if local_gold.exists():
            shutil.rmtree(local_gold)
        df.write.format("delta").mode("overwrite").partitionBy("ano_mes").save(str(local_gold))
        _upload_delta(local_gold, "gold", "fatos/fato_reproducao", cliente)
        print(f"gold/fatos/fato_reproducao: {df.count():,} registros")

        # fato_pagamento
        local_pag = Path("/tmp/dag_gold_fat/silver/pagamentos")
        _download_delta("silver", "fatos/pagamentos", local_pag, cliente)
        local_assin = Path("/tmp/dag_gold_fat/silver/assinaturas")
        _download_delta("silver", "fatos/assinaturas", local_assin, cliente)
        df_assin = (spark.read.format("delta").load(str(local_assin))
                    .select(F.col("id").alias("assinatura_id"), "usuario_id", "plano_id"))
        df = (spark.read.format("delta").load(str(local_pag))
              .join(df_assin, on="assinatura_id", how="left")
              .withColumn("data_id", F.date_format(F.col("data").cast("timestamp"), "yyyyMMdd").cast("int"))
              .withColumn("pago",    F.col("status") == F.lit("pago"))
              .select("data_id", "usuario_id", "plano_id", "valor", "pago", "ano_mes"))
        local_gold = Path("/tmp/dag_gold_fat/gold/fato_pagamento")
        if local_gold.exists():
            shutil.rmtree(local_gold)
        df.write.format("delta").mode("overwrite").partitionBy("ano_mes").save(str(local_gold))
        _upload_delta(local_gold, "gold", "fatos/fato_pagamento", cliente)
        print(f"gold/fatos/fato_pagamento: {df.count():,} registros")
    finally:
        spark.stop()


def gold_postgres():
    """Espelha Gold Delta -> schema gold no Postgres (ADR-0003)."""
    import psycopg2

    spark   = _get_spark("gold-postgres", with_jdbc=True)
    cliente = _get_minio()

    try:
        conn = psycopg2.connect(host=POSTGRES_HOST, port=int(POSTGRES_PORT),
                                dbname=POSTGRES_DB, user=POSTGRES_USER, password=POSTGRES_PASS)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS gold;")
        conn.close()

        DIMENSOES = ["dim_tempo", "dim_usuario", "dim_plano", "dim_artista", "dim_musica"]
        for dim in DIMENSOES:
            local = Path(f"/tmp/dag_gold/{dim}")
            _download_delta("gold", f"dimensoes/{dim}", local, cliente)
            df = spark.read.format("delta").load(str(local))
            df.write.jdbc(url=JDBC_URL, table=f"gold.{dim}", mode="overwrite", properties=JDBC_PROPS)
            print(f"gold.{dim}: {df.count():,} registros -> Postgres")

        for fato, prefix in [("fato_reproducao", "fatos/fato_reproducao"),
                              ("fato_pagamento",  "fatos/fato_pagamento")]:
            local = Path(f"/tmp/dag_gold/{fato}")
            _download_delta("gold", prefix, local, cliente)
            df = spark.read.format("delta").load(str(local))
            df.write.jdbc(url=JDBC_URL, table=f"gold.{fato}", mode="overwrite", properties=JDBC_PROPS)
            print(f"gold.{fato}: {df.count():,} registros -> Postgres")
    finally:
        spark.stop()


# ── Definição do DAG ──────────────────────────────────────────────────────────

default_args = {
    "owner":       "airflow",
    "retries":     1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="pipeline_streaming",
    description="Pipeline medalhão completo com carga incremental por watermark",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@hourly",
    catchup=False,
    default_args=default_args,
    tags=["streaming", "pipeline", "medallion"],
) as dag:

    t_buckets     = PythonOperator(task_id="criar_buckets",     python_callable=criar_buckets)
    t_landing_dim = PythonOperator(task_id="landing_dimensoes", python_callable=landing_dimensoes)
    t_landing_fat = PythonOperator(task_id="landing_fatos",     python_callable=landing_fatos)
    t_bronze_dim  = PythonOperator(task_id="bronze_dimensoes",  python_callable=bronze_dimensoes)
    t_bronze_fat  = PythonOperator(task_id="bronze_fatos",      python_callable=bronze_fatos)
    t_silver_dim  = PythonOperator(task_id="silver_dimensoes",  python_callable=silver_dimensoes)
    t_silver_fat  = PythonOperator(task_id="silver_fatos",      python_callable=silver_fatos)
    t_gold_dim    = PythonOperator(task_id="gold_dimensoes",    python_callable=gold_dimensoes)
    t_gold_fat    = PythonOperator(task_id="gold_fatos",        python_callable=gold_fatos)
    t_gold_pg     = PythonOperator(task_id="gold_postgres",     python_callable=gold_postgres)

    # Dependências
    t_buckets >> [t_landing_dim, t_landing_fat]
    t_landing_dim >> t_bronze_dim
    t_landing_fat >> t_bronze_fat
    t_bronze_dim >> [t_silver_dim, t_silver_fat]   # silver_fatos precisa de musicas (bronze_dim)
    t_bronze_fat >> t_silver_fat
    [t_silver_dim, t_silver_fat] >> t_gold_dim
    [t_silver_dim, t_silver_fat] >> t_gold_fat
    [t_gold_dim, t_gold_fat] >> t_gold_pg
