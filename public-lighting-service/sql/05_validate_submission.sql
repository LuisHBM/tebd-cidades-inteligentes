-- Consultas de conferência da entrega parcial.
SELECT 'oltp' AS ambiente,count(*) AS tabelas FROM information_schema.tables
 WHERE table_schema='oltp' AND table_type='BASE TABLE';
SELECT count(*) AS solicitacoes_oltp FROM oltp.solicitacao;
SELECT count(*) AS solicitacoes_olap,sum(quantidade) AS quantidade FROM olap.fato_solicitacao;
SELECT s.descricao,count(*) AS registros
 FROM olap.fato_solicitacao f JOIN olap.dim_situacao s ON s.situacao_sk=f.situacao_sk
 GROUP BY s.descricao ORDER BY registros DESC;
SELECT d.ano,d.mes,count(*) AS registros
 FROM olap.fato_solicitacao f JOIN olap.dim_data d ON d.data_sk=f.data_demanda_sk
 GROUP BY d.ano,d.mes ORDER BY d.ano,d.mes;
-- Calcula a mediana dos registros ATENDIDA com as datas publicadas na fonte.
SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY intervalo_ate_situacao_dias) AS mediana_dias_ate_status_atendida
 FROM olap.fato_solicitacao f JOIN olap.dim_situacao s ON s.situacao_sk=f.situacao_sk
 WHERE s.descricao='ATENDIDA';
