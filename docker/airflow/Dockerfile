FROM apache/airflow:2.9.3-python3.11

USER root

# Java (necessário para PySpark/Delta)
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jdk-headless \
    wget \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

USER airflow

# PySpark + Delta Lake + conector Postgres
RUN pip install --no-cache-dir \
    pyspark==3.5.1 \
    delta-spark==3.2.0 \
    psycopg2-binary==2.9.9 \
    minio==7.2.7

USER root

RUN mkdir -p /opt/spark/jars && \
    wget -O /opt/spark/jars/postgresql-42.7.3.jar \
        https://jdbc.postgresql.org/download/postgresql-42.7.3.jar && \
    wget -O /opt/spark/jars/delta-spark_2.12-3.2.0.jar \
        https://repo1.maven.org/maven2/io/delta/delta-spark_2.12/3.2.0/delta-spark_2.12-3.2.0.jar && \
    wget -O /opt/spark/jars/delta-storage-3.2.0.jar \
        https://repo1.maven.org/maven2/io/delta/delta-storage/3.2.0/delta-storage-3.2.0.jar

USER airflow