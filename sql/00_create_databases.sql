-- Cria bancos auxiliares para Airflow e Metabase
-- Executado antes do DDL principal (ordem alfabética garante 00_ antes de 01_)

SELECT 'CREATE DATABASE airflow'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow')\gexec

SELECT 'CREATE DATABASE metabase'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'metabase')\gexec