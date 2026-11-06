-- Consultas operacionais. A data de referência (ref.hoje) é o último dia com abertura na base; em operação, usar CURRENT_DATE.
-- Q1. Chamados não atendidos há mais tempo em aberto.
WITH ref AS (SELECT max(d.data) AS hoje FROM olap.fato_solicitacao f JOIN olap.dim_data d ON d.data_sk=f.data_demanda_sk)
SELECT f.solicitacao_id,b.nome AS bairro,b.rpa_id,sv.descricao AS servico,st.descricao AS situacao,
 dd.data AS abertura,ds.data AS ultima_situacao,ref.hoje-dd.data AS dias_em_aberto
 FROM olap.fato_solicitacao f CROSS JOIN ref
 JOIN olap.dim_situacao st ON st.situacao_sk=f.situacao_sk
 JOIN olap.dim_bairro b ON b.bairro_sk=f.bairro_sk
 JOIN olap.dim_servico sv ON sv.servico_sk=f.servico_sk
 JOIN olap.dim_data dd ON dd.data_sk=f.data_demanda_sk
 JOIN olap.dim_data ds ON ds.data_sk=f.data_situacao_sk
 WHERE st.descricao<>'ATENDIDA'
 ORDER BY dias_em_aberto DESC,f.solicitacao_id LIMIT 15;
-- Q2. Não atendidos por situação e tempo em aberto.
WITH ref AS (SELECT max(d.data) AS hoje FROM olap.fato_solicitacao f JOIN olap.dim_data d ON d.data_sk=f.data_demanda_sk)
SELECT st.descricao AS situacao,
 count(*) FILTER (WHERE ref.hoje-dd.data<=30) AS ate_30_dias,
 count(*) FILTER (WHERE ref.hoje-dd.data BETWEEN 31 AND 90) AS de_31_a_90,
 count(*) FILTER (WHERE ref.hoje-dd.data BETWEEN 91 AND 180) AS de_91_a_180,
 count(*) FILTER (WHERE ref.hoje-dd.data>180) AS acima_180,
 count(*) AS total
 FROM olap.fato_solicitacao f CROSS JOIN ref
 JOIN olap.dim_situacao st ON st.situacao_sk=f.situacao_sk
 JOIN olap.dim_data dd ON dd.data_sk=f.data_demanda_sk
 WHERE st.descricao<>'ATENDIDA'
 GROUP BY st.descricao ORDER BY total DESC;
-- Q3. Bairros e serviços com mais chamados não atendidos.
SELECT b.nome AS bairro,b.rpa_id,sv.descricao AS servico,count(*) AS nao_atendidos,
 min(dd.data) AS abertura_mais_antiga
 FROM olap.fato_solicitacao f
 JOIN olap.dim_situacao st ON st.situacao_sk=f.situacao_sk
 JOIN olap.dim_bairro b ON b.bairro_sk=f.bairro_sk
 JOIN olap.dim_servico sv ON sv.servico_sk=f.servico_sk
 JOIN olap.dim_data dd ON dd.data_sk=f.data_demanda_sk
 WHERE st.descricao<>'ATENDIDA'
 GROUP BY b.nome,b.rpa_id,sv.descricao ORDER BY nao_atendidos DESC,bairro LIMIT 15;
-- Q4. Logradouros com três ou mais chamados nos últimos 30 dias.
WITH ref AS (SELECT max(data_demanda) AS hoje FROM oltp.solicitacao)
SELECT s.logradouro,b.nome AS bairro,count(*) AS chamados,
 count(*) FILTER (WHERE st.descricao<>'ATENDIDA') AS nao_atendidos,
 min(s.data_demanda) AS primeiro,max(s.data_demanda) AS ultimo
 FROM oltp.solicitacao s CROSS JOIN ref
 JOIN oltp.bairro b ON b.bairro_id=s.bairro_id
 JOIN oltp.situacao st ON st.situacao_id=s.situacao_id
 WHERE s.data_demanda>ref.hoje-30
 GROUP BY s.logradouro,b.nome HAVING count(*)>=3
 ORDER BY chamados DESC,nao_atendidos DESC,s.logradouro LIMIT 15;
-- Q5. Chamados abertos por dia nos últimos 7 dias e situação publicada.
WITH ref AS (SELECT max(d.data) AS hoje FROM olap.fato_solicitacao f JOIN olap.dim_data d ON d.data_sk=f.data_demanda_sk)
SELECT dd.data,dd.dia_semana,count(*) AS abertos,
 count(*) FILTER (WHERE st.descricao='ATENDIDA') AS atendidos,
 count(*) FILTER (WHERE st.descricao<>'ATENDIDA') AS nao_atendidos
 FROM olap.fato_solicitacao f CROSS JOIN ref
 JOIN olap.dim_situacao st ON st.situacao_sk=f.situacao_sk
 JOIN olap.dim_data dd ON dd.data_sk=f.data_demanda_sk
 WHERE dd.data>ref.hoje-7
 GROUP BY dd.data,dd.dia_semana ORDER BY dd.data;
