-- KPI 4: Top 10 artistas por reproduções
-- Closes #34
-- Fonte: gold.fato_reproducao + gold.dim_artista
-- Regra: contagem de plays válidos agrupados por artista, top 10

SELECT
    da.nome                                             AS artista,
    da.pais,
    COUNT(*)                                            AS total_reproducoes,
    ROUND(SUM(fr.ms_tocados) / 3600000.0, 2)           AS horas_ouvidas
FROM gold.fato_reproducao fr
JOIN gold.dim_artista da ON fr.artista_id = da.artista_id
GROUP BY da.artista_id, da.nome, da.pais
ORDER BY total_reproducoes DESC
LIMIT 10;
