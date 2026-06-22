-- KPI 2: Taxa de churn mensal
-- Closes #32
-- Fonte: gold.fato_pagamento
-- Regra: usuários que pagaram no mês M-1 mas não pagaram no mês M
-- Nota: dados sintéticos (Faker) tendem a gerar churn ~0 pois todos renovam

SELECT
    TO_CHAR(
        TO_DATE(p_ant.ano_mes, 'YYYY-MM') + INTERVAL '1 month',
        'YYYY-MM'
    ) AS ano_mes,
    COUNT(DISTINCT p_ant.usuario_id)  AS ativos_mes_anterior,
    COUNT(DISTINCT CASE
        WHEN p_atual.usuario_id IS NULL
        THEN p_ant.usuario_id
    END)                              AS churned,
    ROUND(
        COUNT(DISTINCT CASE
            WHEN p_atual.usuario_id IS NULL
            THEN p_ant.usuario_id
        END)::numeric
        / NULLIF(COUNT(DISTINCT p_ant.usuario_id), 0) * 100, 2
    )                                 AS taxa_churn_pct
FROM (
    SELECT DISTINCT usuario_id, ano_mes
    FROM gold.fato_pagamento
    WHERE pago = true
) p_ant
LEFT JOIN (
    SELECT DISTINCT usuario_id, ano_mes
    FROM gold.fato_pagamento
    WHERE pago = true
) p_atual
    ON  p_ant.usuario_id = p_atual.usuario_id
    AND p_atual.ano_mes  = TO_CHAR(
            TO_DATE(p_ant.ano_mes, 'YYYY-MM') + INTERVAL '1 month',
            'YYYY-MM'
        )
GROUP BY 1
ORDER BY 1 DESC;
