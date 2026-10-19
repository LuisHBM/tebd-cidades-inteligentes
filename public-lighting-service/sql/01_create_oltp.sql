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
