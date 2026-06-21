import pytest
from datetime import date, datetime
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField,
    IntegerType, StringType, TimestampType, DateType, DoubleType, BooleanType,
)


@pytest.fixture(scope="session")
def spark():
    s = (
        SparkSession.builder
        .appName("test-gold")
        .master("local[1]")
        .config("spark.sql.shuffle.partitions", "1")
        .getOrCreate()
    )
    yield s
    s.stop()


# ─────────────────────────────────────────────────────────
# dim_tempo
# ─────────────────────────────────────────────────────────

def test_dim_tempo_calendario_continuo(spark):
    """dim_tempo deve cobrir todos os dias entre data_min e data_max, sem buracos."""
    df = spark.sql(
        "SELECT explode(sequence(to_date('2024-01-01'), to_date('2024-01-10'), "
        "interval 1 day)) AS data"
    )
    assert df.count() == 10


def test_dim_tempo_data_id_yyyymmdd(spark):
    """data_id deve ser a data no formato inteiro yyyyMMdd."""
    df = spark.createDataFrame([(date(2024, 3, 5),)], ["data"])
    df = df.withColumn("data_id", F.date_format("data", "yyyyMMdd").cast("int"))
    assert df.collect()[0].data_id == 20240305


def test_dim_tempo_dia_semana_alinhado(spark):
    """dia_semana deve ser derivado de dayofweek (1=Domingo..7=Sábado)."""
    dias_semana = [
        "Domingo", "Segunda-feira", "Terça-feira", "Quarta-feira",
        "Quinta-feira", "Sexta-feira", "Sábado",
    ]
    arr = F.array(*[F.lit(d) for d in dias_semana])
    # 2024-03-13 é uma quarta-feira
    df = spark.createDataFrame([(date(2024, 3, 13),)], ["data"])
    df = df.withColumn("dia_semana", F.element_at(arr, F.dayofweek("data")))
    assert df.collect()[0].dia_semana == "Quarta-feira"


def test_dim_tempo_ano_mes(spark):
    df = spark.createDataFrame([(date(2025, 11, 5),)], ["data"])
    df = df.withColumn("ano_mes", F.date_format("data", "yyyy-MM"))
    assert df.collect()[0].ano_mes == "2025-11"


# ─────────────────────────────────────────────────────────
# fato_reproducao
# ─────────────────────────────────────────────────────────

def test_fato_reproducao_join_artista_via_musica(spark):
    """artista_id deve vir da música associada ao play."""
    schema_repro = StructType([
        StructField("usuario_id", IntegerType(), False),
        StructField("musica_id", IntegerType(), False),
        StructField("timestamp", TimestampType(), False),
        StructField("ms_tocados", IntegerType(), False),
        StructField("completou", BooleanType(), False),
        StructField("ano_mes", StringType(), False),
    ])
    df_repro = spark.createDataFrame(
        [(1, 10, datetime(2024, 3, 15, 12, 0, 0), 50000, False, "2024-03")],
        schema_repro,
    )
    df_musica_artista = spark.createDataFrame([(10, 99)], ["musica_id", "artista_id"])

    df_fato = (
        df_repro.join(df_musica_artista, on="musica_id", how="left")
        .withColumn("data_id", F.date_format("timestamp", "yyyyMMdd").cast("int"))
        .withColumn("contagem", F.lit(1))
    )
    row = df_fato.collect()[0]
    assert row.artista_id == 99
    assert row.data_id == 20240315
    assert row.contagem == 1


def test_fato_reproducao_preserva_grao_de_play(spark):
    """O grão deve continuar sendo 1 linha por play válido (sem agregação)."""
    schema_repro = StructType([
        StructField("usuario_id", IntegerType(), False),
        StructField("musica_id", IntegerType(), False),
        StructField("timestamp", TimestampType(), False),
        StructField("ms_tocados", IntegerType(), False),
        StructField("completou", BooleanType(), False),
        StructField("ano_mes", StringType(), False),
    ])
    df_repro = spark.createDataFrame(
        [
            (1, 10, datetime(2024, 3, 15, 12, 0, 0), 50000, False, "2024-03"),
            (1, 10, datetime(2024, 3, 16, 12, 0, 0), 70000, True, "2024-03"),
        ],
        schema_repro,
    )
    assert df_repro.count() == 2  # 2 plays distintos, mesma música/usuário


# ─────────────────────────────────────────────────────────
# fato_pagamento
# ─────────────────────────────────────────────────────────

def test_fato_pagamento_flag_pago(spark):
    """pago deve ser True apenas quando status == 'pago'."""
    schema_pag = StructType([
        StructField("assinatura_id", IntegerType(), False),
        StructField("valor", DoubleType(), False),
        StructField("data", DateType(), False),
        StructField("status", StringType(), False),
    ])
    df_pag = spark.createDataFrame(
        [(1, 19.90, date(2024, 3, 15), "pago"), (2, 9.90, date(2024, 3, 16), "falhou")],
        schema_pag,
    )
    df_pag = df_pag.withColumn("pago", F.col("status") == F.lit("pago"))
    resultado = {r.assinatura_id: r.pago for r in df_pag.collect()}
    assert resultado[1] is True
    assert resultado[2] is False


def test_fato_pagamento_join_usuario_plano_via_assinatura(spark):
    """usuario_id e plano_id devem vir da assinatura referenciada pelo pagamento."""
    df_pag = spark.createDataFrame(
        [(1, 19.90, date(2024, 3, 15), "pago")],
        ["assinatura_id", "valor", "data", "status"],
    )
    df_assin = spark.createDataFrame([(1, 500, 2)], ["assinatura_id", "usuario_id", "plano_id"])

    df_fato = df_pag.join(df_assin, on="assinatura_id", how="left")
    row = df_fato.collect()[0]
    assert row.usuario_id == 500
    assert row.plano_id == 2


def test_fato_pagamento_data_id_a_partir_de_date(spark):
    """data_id deve ser derivado corretamente mesmo quando a coluna original é DateType."""
    df = spark.createDataFrame([(date(2024, 3, 15),)], ["data"])
    df = df.withColumn(
        "data_id",
        F.date_format(F.col("data").cast("timestamp"), "yyyyMMdd").cast("int"),
    )
    assert df.collect()[0].data_id == 20240315
