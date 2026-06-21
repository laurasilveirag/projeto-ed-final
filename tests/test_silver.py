import pytest
from datetime import date, datetime
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField,
    IntegerType, StringType, TimestampType, DateType,
)


@pytest.fixture(scope="session")
def spark():
    s = (
        SparkSession.builder
        .appName("test-silver")
        .master("local[1]")
        .config("spark.sql.shuffle.partitions", "1")
        .getOrCreate()
    )
    yield s
    s.stop()


# ─────────────────────────────────────────────────────────
# reproducoes
# ─────────────────────────────────────────────────────────

def test_filtra_plays_invalidos(spark):
    """Plays com ms_tocados < 30000 ms devem ser descartados na Silver."""
    schema = StructType([
        StructField("id", IntegerType(), False),
        StructField("ms_tocados", IntegerType(), False),
    ])
    df = spark.createDataFrame([(1, 29999), (2, 30000), (3, 60000)], schema)
    resultado = df.filter(F.col("ms_tocados") >= 30000)
    ids = [r.id for r in resultado.collect()]
    assert 1 not in ids, "Play com 29999 ms deve ser descartado"
    assert 2 in ids,     "Play com exatamente 30000 ms deve ser mantido"
    assert 3 in ids,     "Play com 60000 ms deve ser mantido"


def test_completou_derivado(spark):
    """completou = True quando ms_tocados >= 90% da duracao_ms."""
    schema = StructType([
        StructField("id", IntegerType(), False),
        StructField("ms_tocados", IntegerType(), False),
        StructField("duracao_ms", IntegerType(), False),
    ])
    dados = [
        (1, 90000, 100000),   # 90 % — True
        (2, 89999, 100000),   # 89.999 % — False
        (3, 100000, 100000),  # 100 % — True
        (4, 0,     100000),   # 0 % — False
    ]
    df = spark.createDataFrame(dados, schema)
    df = df.withColumn(
        "completou",
        F.col("ms_tocados") >= (F.col("duracao_ms") * 0.9)
    )
    resultado = {r.id: r.completou for r in df.collect()}
    assert resultado[1] is True
    assert resultado[2] is False
    assert resultado[3] is True
    assert resultado[4] is False


def test_dedup_por_id(spark):
    """Registros com o mesmo id devem ser deduplicados."""
    schema = StructType([
        StructField("id", IntegerType(), False),
        StructField("ms_tocados", IntegerType(), False),
    ])
    df = spark.createDataFrame([(1, 30000), (1, 30000), (2, 45000)], schema)
    resultado = df.dropDuplicates(["id"])
    assert resultado.count() == 2


# ─────────────────────────────────────────────────────────
# ano_mes
# ─────────────────────────────────────────────────────────

def test_ano_mes_de_timestamp(spark):
    """ano_mes derivado de campo timestamp (reproducoes)."""
    schema = StructType([
        StructField("id", IntegerType(), False),
        StructField("timestamp", TimestampType(), False),
    ])
    df = spark.createDataFrame([(1, datetime(2024, 3, 15, 10, 0, 0))], schema)
    df = df.withColumn("ano_mes", F.date_format(F.col("timestamp"), "yyyy-MM"))
    assert df.collect()[0].ano_mes == "2024-03"


def test_ano_mes_de_date(spark):
    """ano_mes derivado de campo date (pagamentos / assinaturas)."""
    schema = StructType([
        StructField("id", IntegerType(), False),
        StructField("data", DateType(), False),
    ])
    df = spark.createDataFrame([(1, date(2025, 11, 5))], schema)
    df = df.withColumn(
        "ano_mes",
        F.date_format(F.col("data").cast("timestamp"), "yyyy-MM")
    )
    assert df.collect()[0].ano_mes == "2025-11"


# ─────────────────────────────────────────────────────────
# padronização de texto
# ─────────────────────────────────────────────────────────

def test_status_padronizado(spark):
    """Status com espaços ou maiúsculas deve ser normalizado com lower + trim."""
    schema = StructType([
        StructField("id", IntegerType(), False),
        StructField("status", StringType(), False),
    ])
    df = spark.createDataFrame([(1, " Pago "), (2, "FALHOU"), (3, "ativa")], schema)
    df = df.withColumn("status", F.lower(F.trim(F.col("status"))))
    resultado = {r.id: r.status for r in df.collect()}
    assert resultado[1] == "pago"
    assert resultado[2] == "falhou"
    assert resultado[3] == "ativa"


def test_trim_colunas_texto(spark):
    """Colunas de texto das dimensões devem ter espaços removidos nas bordas."""
    schema = StructType([
        StructField("id", IntegerType(), False),
        StructField("nome", StringType(), False),
    ])
    df = spark.createDataFrame([(1, "  João Silva  "), (2, "Maria")], schema)
    df = df.withColumn("nome", F.trim(F.col("nome")))
    resultado = {r.id: r.nome for r in df.collect()}
    assert resultado[1] == "João Silva"
    assert resultado[2] == "Maria"
