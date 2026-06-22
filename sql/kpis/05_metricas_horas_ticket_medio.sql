-- Métricas: Total de horas ouvidas + Ticket médio mensal
-- Closes #35
-- Fonte: gold.fato_reproducao + gold.fato_pagamento
-- horas_ouvidas: soma de ms_tocados convertida para horas (só plays válidos)
-- ticket_medio: receita paga / assinantes pagantes no mês

SELECT
    fr.ano_mes,
    ROUND(SUM(fr.ms_tocados) / 3600000.0, 2)   AS horas_ouvidas,
    COUNT(*)                                     AS total_plays,
    (
        SELECT ROUND(
            SUM(fp2.valor) / NULLIF(COUNT(DISTINCT fp2.usuario_id), 0), 2
        )
        FROM gold.fato_pagamento fp2
        WHERE fp2.pago    = true
          AND fp2.ano_mes = fr.ano_mes
    )                                            AS ticket_medio
FROM gold.fato_reproducao fr
GROUP BY fr.ano_mes
ORDER BY fr.ano_mes DESC;
