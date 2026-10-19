# Atendimento de iluminação pública

Banco de dados para analisar as solicitações de iluminação pública da Central 156 do Recife. Permite consultar volumes por bairro, serviço e período, comparar as situações publicadas e calcular o intervalo até o atendimento registrado.

Os registros são organizados em um modelo transacional (OLTP, Online Transaction Processing) e em um modelo analítico (OLAP, Online Analytical Processing). A carga usa um CSV oficial, obtido por download direto.

## Dados

A fonte é a Central 156 da Autarquia de Manutenção e Limpeza Urbana do Recife (EMLURB), publicada no [portal de dados abertos municipal](https://dados.recife.pe.gov.br/dataset/central-de-atendimento-de-servicos-da-emlurb-156/resource/06872af2-9350-4c34-aa39-6337a1822ff7), sob licença Open Database License (ODbL).

O recorte contém **34.492 registros** do grupo `ILUMINACAO PUBLICA`, abertos entre 01/01 e 31/08/2025. Abrange 93 bairros, seis regiões político-administrativas (RPAs), dez serviços e cinco situações.

O arquivo original está em `data/raw/`. Os CSVs normalizados para importação estão em `data/processed/`. O [manifesto dos dados](docs/data_manifest.json) registra a origem, o recorte, as transformações e os hashes SHA-256. A preparação preserva a versão original e dispensa scraping.

## Executar

Requisitos: PostgreSQL 16 e cliente `psql`. Os CSVs para a carga já estão incluídos. Execute os comandos na raiz do repositório, ajustando host e usuário à sua instalação:

```bash
createdb -h localhost -U postgres lighting_service
psql -h localhost -U postgres -d lighting_service -f sql/00_run_all.sql
```

O roteiro cria os esquemas, importa os dados e carrega o OLAP. Os scripts de criação e importação devem ser executados em um banco vazio. A carga analítica pode ser refeita:

```bash
psql -h localhost -U postgres -d lighting_service -v ON_ERROR_STOP=1 -f sql/04_load_olap.sql
```

Para conferir contagens e indicadores:

```bash
psql -h localhost -U postgres -d lighting_service -v ON_ERROR_STOP=1 -f sql/05_validate_data.sql
```

Os comandos `\ir` e `\copy` dependem do `psql`. Para criar apenas os esquemas em outro editor SQL, use `sql/create_all.sql` como alternativa aos scripts 01 e 02.

## Reproduzir e validar

A preparação dos dados usa apenas a biblioteca padrão do Python 3. Ela exige o mesmo CSV original identificado no manifesto:

```bash
python3 scripts/prepare_data.py
```

A validação verifica as restrições, compara cada solicitação com o fato correspondente e confirma que repetir a carga mantém o conteúdo:

```bash
python3 scripts/validate_database.py localhost 5432 lighting_service
```

Os resultados ficam em `docs/validation/`. Na versão incluída, os dois modelos têm 34.492 registros e nenhuma divergência na reconciliação.

Os diagramas estão disponíveis em PNG, SVG e Mermaid, com cardinalidades em pé de galinha. Os scripts de preparação e validação usam apenas a biblioteca padrão do Python 3.

## Modelos e documentação

- [Requisitos e regras do sistema](docs/requirements.md)
- [Dicionário de dados](docs/data_dictionary.md)
- [DER transacional](docs/diagrams/oltp_model.svg)
- [DER analítico](docs/diagrams/olap_model.svg)
- [Fontes dos dados](references/README.md)
- [Relatório em PDF](reports/relatorio_parcial_2026_10_19.pdf)

Arquivos, funções e variáveis de apoio usam nomes em inglês. Os identificadores da modelagem, como `solicitacao` e `bairro_id`, e as colunas da fonte permanecem em português.

## Limites de interpretação

A base contém a última situação publicada de cada registro. As datas de última situação chegam a 10/09/2025. Os 33.662 registros `ATENDIDA` e os 830 em outras situações descrevem essa versão, sem reconstituir o estoque pendente em 31/08/2025 ou o atendimento atual.

O intervalo entre a abertura e a última situação só é interpretado como intervalo até o atendimento registrado quando a situação é `ATENDIDA`. Ele não comprova a duração física do reparo.

A fonte não publica protocolo, histórico de situações ou identificação de cada ponto de luz. A chave local corresponde à posição da linha no CSV original e não permite unir versões diferentes. Registros distintos também podem se referir ao mesmo defeito.

A análise territorial usa bairro e RPA. Mais solicitações em um bairro não demonstram maior taxa de falhas sem conhecer o tamanho da rede e o uso dos canais de atendimento.
