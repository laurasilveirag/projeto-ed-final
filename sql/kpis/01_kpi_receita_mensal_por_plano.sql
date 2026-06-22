-- KPI 1: Receita mensal por plano
-- Closes #31
-- Fonte: gold.fato_pagamento + gold.dim_plano
-- Regra: soma de valor onde pago = true, agrupado por plano e ano_mes

SELECT
    fp.ano_mes,
    dp.nome                 AS plano,
    SUM(fp.valor)           AS receita_total,
    COUNT(*)                AS total_pagamentos
FROM gold.fato_pagamento fp
JOIN gold.dim_plano dp ON fp.plano_id = dp.plano_id
WHERE fp.pago = true
GROUP BY fp.ano_mes, dp.nome
ORDER BY fp.ano_mes DESC, receita_total DESC;
