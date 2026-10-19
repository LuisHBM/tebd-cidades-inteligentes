-- Cria as tabelas do OLTP em um banco vazio.
BEGIN;
CREATE SCHEMA oltp;
CREATE TABLE oltp.rpa (
 rpa_id smallint PRIMARY KEY CHECK (rpa_id BETWEEN 1 AND 6)
);
CREATE TABLE oltp.bairro (
 bairro_id integer PRIMARY KEY,
 rpa_id smallint NOT NULL REFERENCES oltp.rpa,
 nome text NOT NULL CHECK (btrim(nome) <> ''),
 UNIQUE (rpa_id, nome)
);
CREATE TABLE oltp.grupo_servico (
 grupo_id integer PRIMARY KEY,
 descricao text NOT NULL CHECK (btrim(descricao) <> '')
);
CREATE TABLE oltp.servico (
 servico_id integer PRIMARY KEY,
 grupo_id integer NOT NULL REFERENCES oltp.grupo_servico,
 descricao text NOT NULL CHECK (btrim(descricao) <> '')
);
CREATE TABLE oltp.situacao (
 situacao_id smallint PRIMARY KEY,
 descricao text NOT NULL UNIQUE CHECK (btrim(descricao) <> '')
);
CREATE TABLE oltp.solicitacao (
 solicitacao_id bigint PRIMARY KEY CHECK (solicitacao_id > 0),
 bairro_id integer NOT NULL REFERENCES oltp.bairro,
 servico_id integer NOT NULL REFERENCES oltp.servico,
 situacao_id smallint NOT NULL REFERENCES oltp.situacao,
 logradouro text NOT NULL,
 numero text NOT NULL,
 data_demanda date NOT NULL,
 data_ultima_situacao date NOT NULL CHECK (data_ultima_situacao >= data_demanda)
);
COMMENT ON COLUMN oltp.solicitacao.solicitacao_id IS 'Identifica a linha do CSV original desta versão. Não corresponde ao protocolo municipal.';
COMMENT ON COLUMN oltp.solicitacao.data_ultima_situacao IS 'Registra a data do último status publicado. A fonte não informa o histórico nem garante que essa seja a data do reparo.';
CREATE INDEX ON oltp.solicitacao (bairro_id, data_demanda);
CREATE INDEX ON oltp.solicitacao (servico_id);
CREATE INDEX ON oltp.solicitacao (situacao_id);
COMMIT;
BEGIN;
CREATE SCHEMA olap;
CREATE TABLE olap.dim_data (
 data_sk integer PRIMARY KEY,
 data date NOT NULL UNIQUE,
 ano smallint NOT NULL,
 mes smallint NOT NULL CHECK (mes BETWEEN 1 AND 12),
 dia smallint NOT NULL CHECK (dia BETWEEN 1 AND 31),
 dia_semana smallint NOT NULL CHECK (dia_semana BETWEEN 1 AND 7)
);
CREATE TABLE olap.dim_bairro (
 bairro_sk integer PRIMARY KEY,
 nome text NOT NULL,
 rpa_id smallint NOT NULL
);
CREATE TABLE olap.dim_servico (
 servico_sk integer PRIMARY KEY,
 descricao text NOT NULL,
 grupo_id integer NOT NULL,
 grupo_descricao text NOT NULL
);
CREATE TABLE olap.dim_situacao (
 situacao_sk smallint PRIMARY KEY,
 descricao text NOT NULL UNIQUE
);
-- Cada linha da fato corresponde a uma solicitação na versão selecionada.
CREATE TABLE olap.fato_solicitacao (
 solicitacao_id bigint PRIMARY KEY,
 data_demanda_sk integer NOT NULL REFERENCES olap.dim_data,
 data_situacao_sk integer NOT NULL REFERENCES olap.dim_data,
 bairro_sk integer NOT NULL REFERENCES olap.dim_bairro,
 servico_sk integer NOT NULL REFERENCES olap.dim_servico,
 situacao_sk smallint NOT NULL REFERENCES olap.dim_situacao,
 quantidade smallint NOT NULL DEFAULT 1 CHECK (quantidade = 1),
 intervalo_ate_situacao_dias integer NOT NULL CHECK (intervalo_ate_situacao_dias >= 0)
);
COMMENT ON COLUMN olap.fato_solicitacao.intervalo_ate_situacao_dias IS 'Conta os dias entre a demanda e a última situação. Em ATENDIDA, indica o intervalo até o atendimento registrado. Não mede a duração física do reparo.';
COMMIT;
