# Dicionário de dados

O dicionário cobre as 42 colunas de seis tabelas OLTP e cinco tabelas OLAP. Tipos e nulabilidade conferidos no PostgreSQL 16. Todas as colunas são NOT NULL. PKs são únicas; FKs usam a ação padrão NO ACTION.

## Origem e transformação

Fonte oficial EMLURB 156 / Emprel, recurso 2025, licença ODbL. `data_manifest.json` registra URL, SHA-256, recorte e contagens. O número da linha identifica apenas a versão congelada. Chaves de bairro e situação são atribuídas pelo projeto; códigos de RPA, grupo e serviço vêm da fonte.

Campos originais de grupo, serviço e situação alimentam os cadastros homônimos; BAIRRO/RPA alimentam bairro e RPA; LOGRADOURO, NUMERO, DATA_DEMANDA e DATA_ULT_SITUACAO alimentam solicitação. Latitude e longitude não são importadas. Não há imputação, histórico simulado ou protocolo inventado.

## olap.dim_bairro

| Coluna | Tipo PostgreSQL | Nulo? | Definição e regra |
|---|---|---|---|
| bairro_sk | integer | Não | PK. Chave da dimensão, igual à chave local do bairro na versão congelada. |
| nome | text | Não | Nome do bairro. |
| rpa_id | smallint | Não | Código da RPA desnormalizado para análise; atributo, não dimensão separada. |
## olap.dim_data

| Coluna | Tipo PostgreSQL | Nulo? | Definição e regra |
|---|---|---|---|
| data_sk | integer | Não | PK. Data no formato inteiro AAAAMMDD. |
| data | date | Não | Data de calendário. UNIQUE. |
| ano | smallint | Não | Ano civil. |
| mes | smallint | Não | Mês de 1 a 12. |
| dia | smallint | Não | Dia do mês de 1 a 31. |
| dia_semana | smallint | Não | Dia ISO: segunda = 1; domingo = 7. |
## olap.dim_servico

| Coluna | Tipo PostgreSQL | Nulo? | Definição e regra |
|---|---|---|---|
| servico_sk | integer | Não | PK. Chave da dimensão, igual ao código oficial de serviço nesta versão. |
| descricao | text | Não | Descrição do serviço. |
| grupo_id | integer | Não | Código oficial do grupo, desnormalizado. |
| grupo_descricao | text | Não | Descrição do grupo, desnormalizada. |
## olap.dim_situacao

| Coluna | Tipo PostgreSQL | Nulo? | Definição e regra |
|---|---|---|---|
| situacao_sk | smallint | Não | PK. Mesma chave local da situação da versão congelada. |
| descricao | text | Não | Situação publicada. UNIQUE. |
## olap.fato_solicitacao

| Coluna | Tipo PostgreSQL | Nulo? | Definição e regra |
|---|---|---|---|
| solicitacao_id | bigint | Não | PK. Identificador degenerado do registro; mesma chave técnica do OLTP. Uma linha por registro da versão. |
| data_demanda_sk | integer | Não | FK → olap.dim_data.data_sk; papel data de abertura. |
| data_situacao_sk | integer | Não | FK → olap.dim_data.data_sk; papel data da última situação. |
| bairro_sk | integer | Não | FK → olap.dim_bairro.bairro_sk. |
| servico_sk | integer | Não | FK → olap.dim_servico.servico_sk. |
| situacao_sk | smallint | Não | FK → olap.dim_situacao.situacao_sk. |
| quantidade | smallint | Não | Medida aditiva. DEFAULT 1 e CHECK = 1; contar registros, não postes. |
| intervalo_ate_situacao_dias | integer | Não | Medida em dias, >= 0: data_ultima_situacao menos data_demanda. Somente ATENDIDA permite interpretar como intervalo até atendimento registrado. |
## oltp.bairro

| Coluna | Tipo PostgreSQL | Nulo? | Definição e regra |
|---|---|---|---|
| bairro_id | integer | Não | PK. Chave local atribuída à combinação RPA e nome. |
| rpa_id | smallint | Não | FK → oltp.rpa.rpa_id. |
| nome | text | Não | Nome publicado, sem espaços nas extremidades. UNIQUE(rpa_id, nome). Não vazio. |
## oltp.grupo_servico

| Coluna | Tipo PostgreSQL | Nulo? | Definição e regra |
|---|---|---|---|
| grupo_id | integer | Não | PK. Código oficial do grupo; 4 no recorte. |
| descricao | text | Não | Descrição oficial do grupo. Não vazia. |
## oltp.rpa

| Coluna | Tipo PostgreSQL | Nulo? | Definição e regra |
|---|---|---|---|
| rpa_id | smallint | Não | PK. Código oficial da Região Político-Administrativa; de 1 a 6. |
## oltp.servico

| Coluna | Tipo PostgreSQL | Nulo? | Definição e regra |
|---|---|---|---|
| servico_id | integer | Não | PK. Código oficial do serviço. |
| grupo_id | integer | Não | FK → oltp.grupo_servico.grupo_id. |
| descricao | text | Não | Descrição oficial do serviço. Não vazia. |
## oltp.situacao

| Coluna | Tipo PostgreSQL | Nulo? | Definição e regra |
|---|---|---|---|
| situacao_id | smallint | Não | PK. Chave local da situação, em ordem alfabética. |
| descricao | text | Não | Última situação publicada. UNIQUE e não vazia; não implica histórico. |
## oltp.solicitacao

| Coluna | Tipo PostgreSQL | Nulo? | Definição e regra |
|---|---|---|---|
| solicitacao_id | bigint | Não | PK, > 0. Número da linha de dados no CSV original fixado, sem cabeçalho. Não é protocolo oficial. |
| bairro_id | integer | Não | FK → oltp.bairro.bairro_id. |
| servico_id | integer | Não | FK → oltp.servico.servico_id. |
| situacao_id | smallint | Não | FK → oltp.situacao.situacao_id. |
| logradouro | text | Não | Logradouro publicado; preservado sem espaços nas extremidades. Não identifica um poste. |
| numero | text | Não | Número/complemento publicado como texto; sem conversão numérica. |
| data_demanda | date | Não | Data de abertura publicada. Recorte de 01/01 a 31/08/2025. |
| data_ultima_situacao | date | Não | Data do último status, maior ou igual a data_demanda. Não é necessariamente data do reparo. |

## Granularidade e cálculo

A fato possui uma linha por solicitação publicada nesta versão. A dimensão de data é compartilhada pelos papéis demanda e última situação. Bairro inclui RPA; serviço inclui grupo. As chaves dimensionais reaproveitam os códigos estáveis dentro desta extração, sem controle de versões históricas (SCD). A carga apaga e recompõe o OLAP em transação única; não agrega extrações.

Somar quantidade fornece volume de registros. Para mediana/média do intervalo até atendimento registrado, filtrar dim_situacao.descricao = ATENDIDA. Intervalos das demais situações não representam resolução. O percentual ATENDIDA usa como denominador os registros do mesmo filtro de serviço, território e data de demanda. Não existe SLA contratual na fonte.

33.662 registros ATENDIDA e 830 em outras situações descrevem o estado publicado. Não são o estoque em 31/08/2025 nem a situação atual do município. Não agregar intervalo como se fosse contagem. Não estimar taxa de falhas por poste sem inventário da rede.

## Relacionamentos OLTP

RPA 1:N bairro; bairro 1:N solicitação; grupo_servico 1:N serviço; serviço 1:N solicitação; situação 1:N solicitação. Cada filho exige exatamente um pai; cada pai pode ter zero ou muitos filhos. As seis entidades são domínios presentes no CSV; grupo_servico tem uma linha porque o recorte fixa iluminação.

## Restrições adicionais e índices

O DDL exige descrições e nome do bairro não vazios. Datas de última situação não podem anteceder a demanda. Há índices em solicitação(bairro_id, data_demanda), solicitacao(servico_id) e solicitacao(situacao_id), além dos índices de PK e UNIQUE. No OLAP, mês, dia, dia da semana e medidas têm CHECKs de domínio; as datas são geradas pelo calendário civil.
