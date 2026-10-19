BEGIN;
\copy oltp.rpa FROM 'data/processed/regions.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy oltp.bairro FROM 'data/processed/neighborhoods.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy oltp.grupo_servico FROM 'data/processed/service_groups.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy oltp.servico FROM 'data/processed/services.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy oltp.situacao FROM 'data/processed/statuses.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy oltp.solicitacao FROM 'data/processed/requests.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
COMMIT;
