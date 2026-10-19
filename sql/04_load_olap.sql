-- Recria o OLAP a partir do OLTP em uma única transação.
BEGIN;
DELETE FROM olap.fato_solicitacao;
DELETE FROM olap.dim_data;
DELETE FROM olap.dim_bairro;
DELETE FROM olap.dim_servico;
DELETE FROM olap.dim_situacao;
INSERT INTO olap.dim_data
SELECT to_char(d,'YYYYMMDD')::integer,d::date,
 extract(year FROM d),extract(month FROM d),extract(day FROM d),extract(isodow FROM d)
FROM generate_series((SELECT min(data_demanda) FROM oltp.solicitacao),
 (SELECT max(data_ultima_situacao) FROM oltp.solicitacao),interval '1 day') d;
INSERT INTO olap.dim_bairro SELECT bairro_id,nome,rpa_id FROM oltp.bairro;
INSERT INTO olap.dim_servico
 SELECT s.servico_id,s.descricao,g.grupo_id,g.descricao
 FROM oltp.servico s JOIN oltp.grupo_servico g USING(grupo_id);
INSERT INTO olap.dim_situacao SELECT situacao_id,descricao FROM oltp.situacao;
INSERT INTO olap.fato_solicitacao
 SELECT solicitacao_id,to_char(data_demanda,'YYYYMMDD')::integer,
 to_char(data_ultima_situacao,'YYYYMMDD')::integer,bairro_id,servico_id,situacao_id,1,
 data_ultima_situacao-data_demanda FROM oltp.solicitacao;
COMMIT;
