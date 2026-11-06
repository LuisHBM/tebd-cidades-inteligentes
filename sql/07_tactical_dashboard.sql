-- Consultas táticas: acompanhamento mensal por RPA, serviço e bairro.
-- Q1. Chamados por RPA no último mês, comparados à média mensal dos meses anteriores.
WITH ref AS (SELECT date_trunc('month',max(d.data))::date AS mes_atual
  FROM olap.fato_solicitacao f JOIN olap.dim_data d ON d.data_sk=f.data_demanda_sk),
m AS (SELECT b.rpa_id,date_trunc('month',d.data)::date AS mes,count(*) AS chamados
  FROM olap.fato_solicitacao f
  JOIN olap.dim_bairro b ON b.bairro_sk=f.bairro_sk
  JOIN olap.dim_data d ON d.data_sk=f.data_demanda_sk
  GROUP BY b.rpa_id,date_trunc('month',d.data))
SELECT m.rpa_id,
 sum(m.chamados) FILTER (WHERE m.mes=ref.mes_atual) AS ultimo_mes,
 round(avg(m.chamados) FILTER (WHERE m.mes<ref.mes_atual),1) AS media_meses_anteriores,
 round(100.0*sum(m.chamados) FILTER (WHERE m.mes=ref.mes_atual)
  /avg(m.chamados) FILTER (WHERE m.mes<ref.mes_atual)-100,1) AS variacao_pct
 FROM m CROSS JOIN ref
 GROUP BY m.rpa_id ORDER BY variacao_pct DESC;
-- Q2. Mediana e P90 de dias até o atendimento registrado por serviço.
SELECT sv.descricao AS servico,count(*) AS atendidos,
 percentile_disc(0.5) WITHIN GROUP (ORDER BY f.intervalo_ate_situacao_dias) AS mediana_dias,
 percentile_disc(0.9) WITHIN GROUP (ORDER BY f.intervalo_ate_situacao_dias) AS p90_dias,
 round(avg(f.intervalo_ate_situacao_dias),1) AS media_dias
 FROM olap.fato_solicitacao f
 JOIN olap.dim_situacao st ON st.situacao_sk=f.situacao_sk
 JOIN olap.dim_servico sv ON sv.servico_sk=f.servico_sk
 WHERE st.descricao='ATENDIDA'
 GROUP BY sv.descricao ORDER BY atendidos DESC;
-- Q3. Percentual atendido e atendido em até 7 dias por mês de abertura.
SELECT d.mes,count(*) AS abertos,
 round(100.0*count(*) FILTER (WHERE st.descricao='ATENDIDA')/count(*),1) AS pct_atendida,
 round(100.0*count(*) FILTER (WHERE st.descricao='ATENDIDA' AND f.intervalo_ate_situacao_dias<=7)/count(*),1) AS pct_atendida_ate_7_dias
 FROM olap.fato_solicitacao f
 JOIN olap.dim_situacao st ON st.situacao_sk=f.situacao_sk
 JOIN olap.dim_data d ON d.data_sk=f.data_demanda_sk
 GROUP BY d.mes ORDER BY d.mes;
-- Q4. Ranking dos bairros por volume e participação na própria RPA.
SELECT rank() OVER (ORDER BY count(*) DESC) AS posicao,b.nome AS bairro,b.rpa_id,count(*) AS chamados,
 round(100.0*count(*)/sum(count(*)) OVER (PARTITION BY b.rpa_id),1) AS pct_da_rpa
 FROM olap.fato_solicitacao f
 JOIN olap.dim_bairro b ON b.bairro_sk=f.bairro_sk
 GROUP BY b.nome,b.rpa_id ORDER BY chamados DESC LIMIT 15;
-- Q5. Média de chamados abertos por dia da semana.
SELECT d.dia_semana,count(DISTINCT d.data) AS dias,count(*) AS chamados,
 round(count(*)::numeric/count(DISTINCT d.data),1) AS media_por_dia
 FROM olap.fato_solicitacao f
 JOIN olap.dim_data d ON d.data_sk=f.data_demanda_sk
 GROUP BY d.dia_semana ORDER BY d.dia_semana;
