# Consultas operacionais, táticas e estratégicas

As consultas usam o esquema `olap`, exceto uma consulta operacional que precisa do logradouro e lê `oltp.solicitacao`. As consultas que dependem do tempo usam uma **data de referência** calculada na própria base: o último dia com abertura de chamado. Nesta versão dos dados, ela é **31/08/2025**. Em operação, basta trocá-la por `CURRENT_DATE`. Os scripts estão em `sql/06_operational_dashboard.sql`, `sql/07_tactical_dashboard.sql` e `sql/08_strategic_dashboard.sql`. Exemplo de execução:

```bash
psql -h localhost -U postgres -d lighting_service -v ON_ERROR_STOP=1 -f sql/06_operational_dashboard.sql
```

Os resultados abaixo foram obtidos com a versão dos dados incluída no repositório. Listas longas aparecem truncadas.

## Nível operacional

Uso diário pela equipe de campo e pela supervisão. Responde o que precisa ser verificado agora, a partir dos chamados não atendidos e dos chamados mais recentes.

### Q1. Chamados não atendidos há mais tempo em aberto

Quais chamados não constam como `ATENDIDA` e estão há mais tempo em aberto na data de referência?

```sql
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
```

| solicitacao_id | bairro | rpa_id | servico | situacao | abertura | ultima_situacao | dias_em_aberto |
|---|---|---|---|---|---|---|---|
| 27685 | Santo Amaro | 1 | LUMINARIAS | PENDENCIA | 2025-01-02 | 2025-01-08 | 241 |
| 27850 | Dois Unidos | 2 | LUMINARIAS | PENDENCIA | 2025-01-02 | 2025-01-03 | 241 |
| 28057 | Santo Amaro | 1 | LUMINARIAS | PENDENCIA | 2025-01-02 | 2025-01-08 | 241 |
| 27877 | Mangueira | 5 | LUMINARIAS | PENDENCIA | 2025-01-03 | 2025-01-08 | 240 |
| 27919 | Casa Amarela | 3 | LUMINARIAS | PENDENCIA | 2025-01-03 | 2025-01-13 | 240 |
| 62888 | Boa Viagem | 6 | REPOSICAO DE LUMINARIA | PENDENCIA | 2025-01-03 | 2025-01-13 | 240 |
| 27738 | Campo Grande | 2 | LUMINARIAS | PENDENCIA | 2025-01-04 | 2025-01-13 | 239 |
| 28092 | Jiquia | 5 | LUMINARIAS | PENDENCIA | 2025-01-04 | 2025-01-08 | 239 |

Data de referência: 31/08/2025. A consulta retorna 15 linhas. Os mais antigos estão há 241 dias em aberto e são quase todos `LUMINARIAS` em `PENDENCIA`, com a última situação registrada poucos dias após a abertura, em janeiro.

### Q2. Não atendidos por situação e tempo em aberto

Quantos chamados não atendidos existem em cada situação, separados pelo tempo em aberto na data de referência?

```sql
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
```

| situacao | ate_30_dias | de_31_a_90 | de_91_a_180 | acima_180 | total |
|---|---|---|---|---|---|
| PENDENCIA | 199 | 155 | 200 | 106 | 660 |
| PREPARACAO | 52 | 54 | 12 | 3 | 121 |
| EXECUCAO | 24 | 11 | 5 | 2 | 42 |
| CADASTRADA | 0 | 0 | 7 | 0 | 7 |

Data de referência: 31/08/2025. São 830 chamados não atendidos. Em `PENDENCIA`, 306 dos 660 estão há mais de 90 dias em aberto. Os sete `CADASTRADA` estão entre 91 e 180 dias e não passaram para outra situação.

### Q3. Bairros e serviços com mais não atendidos

Em quais combinações de bairro e serviço se concentram os chamados não atendidos?

```sql
SELECT b.nome AS bairro,b.rpa_id,sv.descricao AS servico,count(*) AS nao_atendidos,
 min(dd.data) AS abertura_mais_antiga
 FROM olap.fato_solicitacao f
 JOIN olap.dim_situacao st ON st.situacao_sk=f.situacao_sk
 JOIN olap.dim_bairro b ON b.bairro_sk=f.bairro_sk
 JOIN olap.dim_servico sv ON sv.servico_sk=f.servico_sk
 JOIN olap.dim_data dd ON dd.data_sk=f.data_demanda_sk
 WHERE st.descricao<>'ATENDIDA'
 GROUP BY b.nome,b.rpa_id,sv.descricao ORDER BY nao_atendidos DESC,bairro LIMIT 15;
```

| bairro | rpa_id | servico | nao_atendidos | abertura_mais_antiga |
|---|---|---|---|---|
| Brasilia Teimosa | 6 | LUMINARIAS | 61 | 2025-02-10 |
| Boa Viagem | 6 | LUMINARIAS | 26 | 2025-02-03 |
| Cohab Ibura de Cima | 6 | LUMINARIAS | 21 | 2025-01-24 |
| Santo Amaro | 1 | LUMINARIAS | 20 | 2025-01-02 |
| Varzea | 4 | LUMINARIAS | 20 | 2025-01-21 |
| Brasilia Teimosa | 6 | ACENDER CIRCUITO | 19 | 2025-07-17 |
| Iputinga | 4 | LUMINARIAS | 16 | 2025-01-17 |
| Pina | 6 | MANUTENCAO EM LAMPADA APAGADA | 16 | 2025-06-29 |
| Boa Viagem | 6 | MANUTENCAO EM LAMPADA APAGADA | 15 | 2025-04-24 |
| Imbiribeira | 6 | LUMINARIAS | 15 | 2025-01-23 |

A consulta retorna 15 linhas. Brasília Teimosa reúne 61 chamados de `LUMINARIAS` não atendidos e mais 19 de `ACENDER CIRCUITO`, abertos a partir de 17/07/2025.

### Q4. Logradouros com chamados repetidos nos últimos 30 dias

Quais logradouros, no mesmo bairro, receberam três ou mais chamados nos 30 dias anteriores à data de referência?

```sql
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
```

| logradouro | bairro | chamados | nao_atendidos | primeiro | ultimo |
|---|---|---|---|---|---|
| AV Norte Miguel Arraes de Alencar | Macaxeira | 52 | 1 | 2025-08-04 | 2025-08-31 |
| AV Engenheiro Domingos Ferreira | Boa Viagem | 32 | 2 | 2025-08-03 | 2025-08-31 |
| ROD BR Cento e Um | Cidade Universitaria | 32 | 1 | 2025-08-02 | 2025-08-31 |
| AV Brasilia Formosa | Brasilia Teimosa | 31 | 5 | 2025-08-03 | 2025-08-29 |
| AV Boa Viagem | Boa Viagem | 27 | 0 | 2025-08-04 | 2025-08-29 |
| AV Celso Furtado | Boa Viagem | 26 | 1 | 2025-08-08 | 2025-08-31 |
| AV Conde da Boa Vista | Boa Vista | 25 | 0 | 2025-08-04 | 2025-08-28 |
| AV Governador Agamenon Magalhaes | Campo Grande | 25 | 0 | 2025-08-05 | 2025-08-30 |

Data de referência: 31/08/2025. A consulta retorna 15 linhas. As primeiras posições são avenidas longas, onde 52 chamados podem corresponder a pontos diferentes. O campo `numero` não ajuda a separá-los, pois cerca de 14 mil registros têm `00`, `0`, `0000`, `SN` ou `S/N`.

### Q5. Chamados abertos nos últimos 7 dias

Quantos chamados foram abertos por dia nos 7 dias até a data de referência, e quantos ainda não constam como atendidos?

```sql
WITH ref AS (SELECT max(d.data) AS hoje FROM olap.fato_solicitacao f JOIN olap.dim_data d ON d.data_sk=f.data_demanda_sk)
SELECT dd.data,dd.dia_semana,count(*) AS abertos,
 count(*) FILTER (WHERE st.descricao='ATENDIDA') AS atendidos,
 count(*) FILTER (WHERE st.descricao<>'ATENDIDA') AS nao_atendidos
 FROM olap.fato_solicitacao f CROSS JOIN ref
 JOIN olap.dim_situacao st ON st.situacao_sk=f.situacao_sk
 JOIN olap.dim_data dd ON dd.data_sk=f.data_demanda_sk
 WHERE dd.data>ref.hoje-7
 GROUP BY dd.data,dd.dia_semana ORDER BY dd.data;
```

| data | dia_semana | abertos | atendidos | nao_atendidos |
|---|---|---|---|---|
| 2025-08-25 | 1 | 94 | 83 | 11 |
| 2025-08-26 | 2 | 190 | 179 | 11 |
| 2025-08-27 | 3 | 214 | 196 | 18 |
| 2025-08-28 | 4 | 170 | 163 | 7 |
| 2025-08-29 | 5 | 169 | 149 | 20 |
| 2025-08-30 | 6 | 75 | 73 | 2 |
| 2025-08-31 | 7 | 89 | 84 | 5 |

Data de referência: 31/08/2025. Foram 1.001 chamados nos últimos 7 dias, dos quais 74 não constam como atendidos.

## Nível tático

Uso mensal pela coordenação do serviço. Acompanha volume, prazo e situação por RPA, serviço e bairro, comparando o último mês com os anteriores.

### Q1. Último mês por RPA

Quantos chamados cada RPA abriu no último mês, e como isso se compara à média mensal dos meses anteriores?

```sql
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
```

| rpa_id | ultimo_mes | media_meses_anteriores | variacao_pct |
|---|---|---|---|
| 6 | 1154 | 1002.6 | 15.1 |
| 1 | 786 | 755.7 | 4.0 |
| 4 | 645 | 662.3 | -2.6 |
| 2 | 425 | 442.1 | -3.9 |
| 3 | 710 | 767.4 | -7.5 |
| 5 | 597 | 680.6 | -12.3 |

Data de referência: 31/08/2025. O último mês é agosto de 2025. A RPA 6 abriu 1.154 chamados, 15,1% acima da sua média mensal anterior, a maior alta entre as RPAs. A RPA 5 ficou 12,3% abaixo.

### Q2. Prazo até o atendimento registrado por serviço

Qual a mediana e o percentil 90 de dias entre abertura e situação `ATENDIDA` em cada serviço?

```sql
SELECT sv.descricao AS servico,count(*) AS atendidos,
 percentile_disc(0.5) WITHIN GROUP (ORDER BY f.intervalo_ate_situacao_dias) AS mediana_dias,
 percentile_disc(0.9) WITHIN GROUP (ORDER BY f.intervalo_ate_situacao_dias) AS p90_dias,
 round(avg(f.intervalo_ate_situacao_dias),1) AS media_dias
 FROM olap.fato_solicitacao f
 JOIN olap.dim_situacao st ON st.situacao_sk=f.situacao_sk
 JOIN olap.dim_servico sv ON sv.servico_sk=f.servico_sk
 WHERE st.descricao='ATENDIDA'
 GROUP BY sv.descricao ORDER BY atendidos DESC;
```

| servico | atendidos | mediana_dias | p90_dias | media_dias |
|---|---|---|---|---|
| MANUTENCAO EM LAMPADA APAGADA | 26026 | 2 | 5 | 2.5 |
| ACENDER CIRCUITO | 6015 | 1 | 4 | 2.1 |
| APAGAR LAMPADA | 501 | 1 | 3 | 1.6 |
| REPOSICAO VAO DE REDE | 353 | 0 | 0 | 0.6 |
| REPOSICAO DE LUMINARIA | 253 | 0 | 0 | 3.0 |
| LUMINARIAS | 202 | 0 | 63 | 12.8 |
| REPOSICAO DESL. E RET. DE POSTE | 122 | 0 | 4 | 2.6 |
| APAGAR CIRCUITO | 114 | 1 | 4 | 2.4 |
| POSICIONAR LUMINARIA | 75 | 2 | 5 | 3.0 |
| IMPLANTACAO DE VAO DE REDE | 1 | 0 | 0 | 0.0 |

O serviço mais frequente tem mediana de 2 dias e P90 de 5. `LUMINARIAS` combina mediana 0 com P90 de 63 dias: 71,8% dos atendidos foram encerrados no mesmo dia da abertura, e uma parcela levou meses.

### Q3. Percentual atendido por mês de abertura

Que parcela dos chamados de cada mês consta como `ATENDIDA`, e que parcela foi atendida em até 7 dias?

```sql
SELECT d.mes,count(*) AS abertos,
 round(100.0*count(*) FILTER (WHERE st.descricao='ATENDIDA')/count(*),1) AS pct_atendida,
 round(100.0*count(*) FILTER (WHERE st.descricao='ATENDIDA' AND f.intervalo_ate_situacao_dias<=7)/count(*),1) AS pct_atendida_ate_7_dias
 FROM olap.fato_solicitacao f
 JOIN olap.dim_situacao st ON st.situacao_sk=f.situacao_sk
 JOIN olap.dim_data d ON d.data_sk=f.data_demanda_sk
 GROUP BY d.mes ORDER BY d.mes;
```

| mes | abertos | pct_atendida | pct_atendida_ate_7_dias |
|---|---|---|---|
| 1 | 4296 | 98.8 | 97.2 |
| 2 | 4303 | 98.6 | 96.6 |
| 3 | 4030 | 98.6 | 95.9 |
| 4 | 4081 | 98.2 | 95.6 |
| 5 | 4481 | 98.0 | 95.7 |
| 6 | 4359 | 97.9 | 93.3 |
| 7 | 4625 | 97.2 | 94.4 |
| 8 | 4317 | 93.6 | 88.6 |

O percentual em até 7 dias caiu de 97,2% em janeiro para 93,3% em junho. O último mês não é comparável aos outros: seus chamados tiveram menos tempo para chegar a `ATENDIDA`.

### Q4. Ranking de bairros por volume

Quais bairros abriram mais chamados e quanto cada um representa na própria RPA?

```sql
SELECT rank() OVER (ORDER BY count(*) DESC) AS posicao,b.nome AS bairro,b.rpa_id,count(*) AS chamados,
 round(100.0*count(*)/sum(count(*)) OVER (PARTITION BY b.rpa_id),1) AS pct_da_rpa
 FROM olap.fato_solicitacao f
 JOIN olap.dim_bairro b ON b.bairro_sk=f.bairro_sk
 GROUP BY b.nome,b.rpa_id ORDER BY chamados DESC LIMIT 15;
```

| posicao | bairro | rpa_id | chamados | pct_da_rpa |
|---|---|---|---|---|
| 1 | Boa Viagem | 6 | 2420 | 29.6 |
| 2 | Santo Amaro | 1 | 1937 | 31.9 |
| 3 | Boa Vista | 1 | 1345 | 22.1 |
| 4 | Imbiribeira | 6 | 1257 | 15.4 |
| 5 | Pina | 6 | 1135 | 13.9 |
| 6 | Varzea | 4 | 1115 | 21.1 |
| 7 | Iputinga | 4 | 1031 | 19.5 |
| 8 | Brasilia Teimosa | 6 | 956 | 11.7 |
| 9 | Cohab Ibura de Cima | 6 | 922 | 11.3 |
| 10 | Areias | 5 | 888 | 16.6 |

A consulta retorna 15 linhas. Boa Viagem lidera com 2.420 chamados, e Santo Amaro responde por 31,9% da RPA 1. O ranking mede volume de registros, não taxa de falhas.

### Q5. Distribuição por dia da semana

Qual a média de chamados abertos em cada dia da semana?

```sql
SELECT d.dia_semana,count(DISTINCT d.data) AS dias,count(*) AS chamados,
 round(count(*)::numeric/count(DISTINCT d.data),1) AS media_por_dia
 FROM olap.fato_solicitacao f
 JOIN olap.dim_data d ON d.data_sk=f.data_demanda_sk
 GROUP BY d.dia_semana ORDER BY d.dia_semana;
```

| dia_semana | dias | chamados | media_por_dia |
|---|---|---|---|
| 1 | 34 | 4752 | 139.8 |
| 2 | 34 | 6808 | 200.2 |
| 3 | 35 | 6352 | 181.5 |
| 4 | 35 | 6013 | 171.8 |
| 5 | 35 | 6090 | 174.0 |
| 6 | 35 | 2364 | 67.5 |
| 7 | 35 | 2113 | 60.4 |

Terça-feira tem a maior média (200,2 por dia), e sábado e domingo ficam abaixo de 70. A segunda-feira (139,8) fica abaixo dos demais dias úteis. O dia 1 é segunda-feira, conforme a numeração ISO.

## Nível estratégico

Uso pela direção da EMLURB e pela prefeitura. Resume todo o período disponível na base (aberturas de 01/01 a 31/08/2025) por território e tipo de serviço.

### Q1. Comparação das RPAs

Como as seis RPAs se comparam em volume, número de bairros, chamados por bairro e percentual atendido?

```sql
SELECT b.rpa_id,count(DISTINCT b.bairro_sk) AS bairros,count(*) AS chamados,
 round(100.0*count(*)/sum(count(*)) OVER (),1) AS pct_do_total,
 round(count(*)::numeric/count(DISTINCT b.bairro_sk),0) AS chamados_por_bairro,
 round(100.0*count(*) FILTER (WHERE st.descricao='ATENDIDA')/count(*),1) AS pct_atendida
 FROM olap.fato_solicitacao f
 JOIN olap.dim_bairro b ON b.bairro_sk=f.bairro_sk
 JOIN olap.dim_situacao st ON st.situacao_sk=f.situacao_sk
 GROUP BY b.rpa_id ORDER BY chamados DESC;
```

| rpa_id | bairros | chamados | pct_do_total | chamados_por_bairro | pct_atendida |
|---|---|---|---|---|---|
| 6 | 8 | 8172 | 23.7 | 1022 | 96.4 |
| 3 | 28 | 6082 | 17.6 | 217 | 97.8 |
| 1 | 11 | 6076 | 17.6 | 552 | 98.6 |
| 5 | 16 | 5361 | 15.5 | 335 | 97.7 |
| 4 | 12 | 5281 | 15.3 | 440 | 97.7 |
| 2 | 18 | 3520 | 10.2 | 196 | 97.9 |

A RPA 6 tem 8 bairros e 23,7% dos chamados, com média de 1.022 por bairro, e o menor percentual atendido (96,4%). A RPA 3 tem 28 bairros e um volume próximo ao da RPA 1.

### Q2. Tendência mensal

O número de chamados está crescendo? A média diária corrige a diferença de dias entre os meses.

```sql
SELECT d.mes,count(*) AS chamados,count(DISTINCT d.data) AS dias,
 round(count(*)::numeric/count(DISTINCT d.data),1) AS media_diaria,
 round(100.0*(count(*)::numeric/count(DISTINCT d.data))
  /lag(count(*)::numeric/count(DISTINCT d.data)) OVER (ORDER BY d.mes)-100,1) AS var_media_diaria_pct
 FROM olap.fato_solicitacao f
 JOIN olap.dim_data d ON d.data_sk=f.data_demanda_sk
 GROUP BY d.mes ORDER BY d.mes;
```

| mes | chamados | dias | media_diaria | var_media_diaria_pct |
|---|---|---|---|---|
| 1 | 4296 | 31 | 138.6 | |
| 2 | 4303 | 28 | 153.7 | 10.9 |
| 3 | 4030 | 31 | 130.0 | -15.4 |
| 4 | 4081 | 30 | 136.0 | 4.6 |
| 5 | 4481 | 31 | 144.5 | 6.3 |
| 6 | 4359 | 30 | 145.3 | 0.5 |
| 7 | 4625 | 31 | 149.2 | 2.7 |
| 8 | 4317 | 31 | 139.3 | -6.7 |

A média diária ficou entre 130 e 154 chamados, e agosto (139,3) ficou próximo de janeiro (138,6). No total da cidade não há tendência de alta. A maior alta no último mês foi a da RPA 6 (tática, Q1).

### Q3. Concentração territorial

Os chamados se concentram em poucos bairros?

```sql
WITH r AS (
 SELECT b.bairro_sk,count(*) AS chamados,row_number() OVER (ORDER BY count(*) DESC) AS posicao
 FROM olap.fato_solicitacao f JOIN olap.dim_bairro b ON b.bairro_sk=f.bairro_sk
 GROUP BY b.bairro_sk)
SELECT faixa,count(*) AS bairros,sum(chamados) AS chamados,
 round(100.0*sum(chamados)/(SELECT sum(chamados) FROM r),1) AS pct_chamados
 FROM (SELECT chamados,CASE WHEN posicao<=10 THEN '1. top 10' WHEN posicao<=30 THEN '2. 11 a 30'
  ELSE '3. demais' END AS faixa FROM r) x
 GROUP BY faixa ORDER BY faixa;
```

| faixa | bairros | chamados | pct_chamados |
|---|---|---|---|
| 1. top 10 | 10 | 13006 | 37.7 |
| 2. 11 a 30 | 20 | 11297 | 32.8 |
| 3. demais | 63 | 10189 | 29.5 |

Os 10 maiores bairros, de 93, somam 37,7% dos chamados, e os 30 maiores somam 70,5%. A concentração também reflete população, extensão da rede e uso da Central 156.

### Q4. Mix de serviços

Qual a participação de cada serviço no total e qual o percentual atendido em cada um?

```sql
SELECT sv.descricao AS servico,count(*) AS chamados,
 round(100.0*count(*)/sum(count(*)) OVER (),1) AS pct_do_total,
 round(100.0*count(*) FILTER (WHERE st.descricao='ATENDIDA')/count(*),1) AS pct_atendida,
 count(*) FILTER (WHERE st.descricao<>'ATENDIDA') AS nao_atendidos
 FROM olap.fato_solicitacao f
 JOIN olap.dim_servico sv ON sv.servico_sk=f.servico_sk
 JOIN olap.dim_situacao st ON st.situacao_sk=f.situacao_sk
 GROUP BY sv.descricao ORDER BY chamados DESC;
```

| servico | chamados | pct_do_total | pct_atendida | nao_atendidos |
|---|---|---|---|---|
| MANUTENCAO EM LAMPADA APAGADA | 26164 | 75.9 | 99.5 | 138 |
| ACENDER CIRCUITO | 6080 | 17.6 | 98.9 | 65 |
| LUMINARIAS | 645 | 1.9 | 31.3 | 443 |
| APAGAR LAMPADA | 501 | 1.5 | 100.0 | 0 |
| REPOSICAO DE LUMINARIA | 364 | 1.1 | 69.5 | 111 |
| REPOSICAO VAO DE REDE | 355 | 1.0 | 99.4 | 2 |
| REPOSICAO DESL. E RET. DE POSTE | 191 | 0.6 | 63.9 | 69 |
| APAGAR CIRCUITO | 115 | 0.3 | 99.1 | 1 |
| POSICIONAR LUMINARIA | 76 | 0.2 | 98.7 | 1 |
| IMPLANTACAO DE VAO DE REDE | 1 | 0.0 | 100.0 | 0 |

Lâmpada apagada (75,9%) e circuito apagado, que afeta um trecho inteiro (17,6%), somam 93,5% dos chamados. `LUMINARIAS` tem 1,9% do volume e 443 dos 830 não atendidos (53,4%).

### Q5. Percentis do prazo por RPA

Como se distribui o prazo até o atendimento registrado em cada RPA?

```sql
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
```

| rpa_id | atendidos | p50_dias | p75_dias | p90_dias | pct_ate_3_dias |
|---|---|---|---|---|---|
| 1 | 5993 | 1 | 3 | 4 | 83.5 |
| 2 | 3447 | 1 | 2 | 2 | 98.4 |
| 3 | 5947 | 1 | 2 | 2 | 98.1 |
| 4 | 5160 | 2 | 4 | 6 | 72.7 |
| 5 | 5238 | 2 | 4 | 5 | 73.7 |
| 6 | 7877 | 2 | 4 | 5 | 72.3 |

As RPAs 2 e 3 registram mais de 98% dos atendimentos em até 3 dias. Nas RPAs 4, 5 e 6, a parcela fica entre 72% e 74%, e o P90 chega a 5 ou 6 dias. Na cidade, a mediana é 2 dias e 81,8% dos atendimentos ocorrem em até 3 dias.

## Limites

- A base contém apenas a última situação publicada de cada chamado. "Não atendido" significa que o chamado não constava como `ATENDIDA` nesta versão, com situações até 10/09/2025. O tempo em aberto é contado até a data de referência (31/08/2025).
- `intervalo_ate_situacao_dias` só é interpretado como prazo até o atendimento quando a situação é `ATENDIDA`. As consultas de prazo filtram essa situação. O intervalo mede datas de registro, não a duração física do reparo.
- Volume de chamados não é taxa de falhas. A fonte não informa o tamanho da rede, o número de pontos de luz nem a população de cada bairro.
- Chamados recentes tiveram menos tempo para chegar a `ATENDIDA`, por isso o último mês aparece com percentual atendido menor.
- Logradouro e número não identificam um ponto de luz, e chamados repetidos podem descrever o mesmo defeito ou defeitos diferentes.
