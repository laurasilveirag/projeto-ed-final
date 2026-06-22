-- KPI 3: Usuários Ativos Mensais (MAU)
-- Closes #33
-- Fonte: gold.fato_reproducao
-- Regra: usuários distintos com pelo menos 1 play válido no mês
-- Play válido já filtrado na camada Silver (ms_tocados >= 30.000 ms)

SELECT
    ano_mes,
    COUNT(DISTINCT usuario_id) AS usuarios_ativos
FROM gold.fato_reproducao
GROUP BY ano_mes
ORDER BY ano_mes DESC;
