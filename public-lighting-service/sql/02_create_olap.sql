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
