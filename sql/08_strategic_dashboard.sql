-- Consultas estratégicas: visão consolidada de janeiro a agosto de 2025.
-- Q1. Comparação das seis RPAs por volume, bairros e percentual atendido.
SELECT b.rpa_id,count(DISTINCT b.bairro_sk) AS bairros,count(*) AS chamados,
 round(100.0*count(*)/sum(count(*)) OVER (),1) AS pct_do_total,
 round(count(*)::numeric/count(DISTINCT b.bairro_sk),0) AS chamados_por_bairro,
 round(100.0*count(*) FILTER (WHERE st.descricao='ATENDIDA')/count(*),1) AS pct_atendida
 FROM olap.fato_solicitacao f
 JOIN olap.dim_bairro b ON b.bairro_sk=f.bairro_sk
 JOIN olap.dim_situacao st ON st.situacao_sk=f.situacao_sk
 GROUP BY b.rpa_id ORDER BY chamados DESC;
-- Q2. Tendência mensal com média diária e variação sobre o mês anterior.
SELECT d.mes,count(*) AS chamados,count(DISTINCT d.data) AS dias,
 round(count(*)::numeric/count(DISTINCT d.data),1) AS media_diaria,
 round(100.0*(count(*)::numeric/count(DISTINCT d.data))
  /lag(count(*)::numeric/count(DISTINCT d.data)) OVER (ORDER BY d.mes)-100,1) AS var_media_diaria_pct
 FROM olap.fato_solicitacao f
 JOIN olap.dim_data d ON d.data_sk=f.data_demanda_sk
 GROUP BY d.mes ORDER BY d.mes;
-- Q3. Concentração dos chamados nos bairros com maior volume.
WITH r AS (
 SELECT b.bairro_sk,count(*) AS chamados,row_number() OVER (ORDER BY count(*) DESC) AS posicao
 FROM olap.fato_solicitacao f JOIN olap.dim_bairro b ON b.bairro_sk=f.bairro_sk
 GROUP BY b.bairro_sk)
SELECT faixa,count(*) AS bairros,sum(chamados) AS chamados,
 round(100.0*sum(chamados)/(SELECT sum(chamados) FROM r),1) AS pct_chamados
 FROM (SELECT chamados,CASE WHEN posicao<=10 THEN '1. top 10' WHEN posicao<=30 THEN '2. 11 a 30'
  ELSE '3. demais' END AS faixa FROM r) x
 GROUP BY faixa ORDER BY faixa;
-- Q4. Mix de serviços: participação no total e percentual atendido.
SELECT sv.descricao AS servico,count(*) AS chamados,
 round(100.0*count(*)/sum(count(*)) OVER (),1) AS pct_do_total,
 round(100.0*count(*) FILTER (WHERE st.descricao='ATENDIDA')/count(*),1) AS pct_atendida,
 count(*) FILTER (WHERE st.descricao<>'ATENDIDA') AS nao_atendidos
 FROM olap.fato_solicitacao f
 JOIN olap.dim_servico sv ON sv.servico_sk=f.servico_sk
 JOIN olap.dim_situacao st ON st.situacao_sk=f.situacao_sk
 GROUP BY sv.descricao ORDER BY chamados DESC;
-- Q5. Percentis de dias até o atendimento registrado por RPA.
SELECT b.rpa_id,count(*) AS atendidos,
 percentile_disc(0.5) WITHIN GROUP (ORDER BY f.intervalo_ate_situacao_dias) AS p50_dias,
 percentile_disc(0.75) WITHIN GROUP (ORDER BY f.intervalo_ate_situacao_dias) AS p75_dias,
 percentile_disc(0.9) WITHIN GROUP (ORDER BY f.intervalo_ate_situacao_dias) AS p90_dias,
 round(100.0*count(*) FILTER (WHERE f.intervalo_ate_situacao_dias<=3)/count(*),1) AS pct_ate_3_dias
 FROM olap.fato_solicitacao f
 JOIN olap.dim_situacao st ON st.situacao_sk=f.situacao_sk
 JOIN olap.dim_bairro b ON b.bairro_sk=f.bairro_sk
 WHERE st.descricao='ATENDIDA'
 GROUP BY b.rpa_id ORDER BY b.rpa_id;
