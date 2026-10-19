# Atendimento de iluminação pública

Projeto acadêmico de banco de dados: análise das solicitações de iluminação pública da Central 156 do Recife. Entrega parcial: **19/10/2026**. Dados reais por download direto, sem scraping ou simulação.

## Estrutura

```text
public-lighting-service/
├── README.md
├── requirements.txt              # Somente geração do relatório
├── data/
│   ├── raw/                      # CSV original preservado
│   └── processed/                # Seis CSVs normalizados para carga
├── docs/
│   ├── data_dictionary.md        # Todos os campos, chaves e regras
│   ├── requirements.md           # Escopo e requisitos verificáveis
│   ├── data_manifest.json        # Fonte, recorte e hashes
│   ├── final_delivery_plan.md    # Continuidade até 06/11
│   ├── diagrams/                 # DERs em PNG, SVG e Mermaid
│   └── validation/               # Evidências da execução PostgreSQL
├── references/                   # Dicionário da fonte e template SBC
├── reports/                      # Relatório em PDF e DOCX
├── scripts/                      # Preparação, validação e geração do relatório
└── sql/                          # DDL, importação, OLAP e conferências
```

A organização adapta a separação entre dados originais, dados tratados, documentação e relatórios do [Cookiecutter Data Science](https://cookiecutter-data-science.drivendata.org/). É uma convenção comum em projetos de dados, ajustada a este trabalho. Nomes de arquivos e pastas seguem o inglês. Os arquivos do relatório usam nomes em português por decisão da equipe: `relatorio_parcial_2026_10_19.pdf` e `relatorio_parcial_2026_10_19.docx`. Texto e nomes de domínio do banco também permanecem em português.

## Relatório

- [Versão em PDF](reports/relatorio_parcial_2026_10_19.pdf)
- [Versão editável em Word](reports/relatorio_parcial_2026_10_19.docx)

O PDF é uma exportação do DOCX. Ao revisar o relatório, atualizar também o PDF.

## Executar

Requer PostgreSQL 16 e cliente `psql`. Na raiz do projeto, criar um banco vazio dedicado e executar:

```bash
createdb -h localhost -U postgres lighting_service
psql -h localhost -U postgres -d lighting_service -f sql/00_run_all.sql
```

Ajustar host e usuário à instalação. A senha é solicitada pelo PostgreSQL, quando necessária. Os comandos `\ir` e `\copy` exigem `psql`; o arquivo completo não é executável diretamente no editor SQL do pgAdmin.

O roteiro cria seis tabelas OLTP, quatro dimensões e uma fato, importa os CSVs e executa consultas de conferência. Usar os scripts 01 a 03 uma vez em banco vazio. `create_all.sql` é uma alternativa que reúne apenas os dois DDLs; não é uma etapa adicional. A carga OLAP pode ser refeita:

```bash
psql -h localhost -U postgres -d lighting_service -v ON_ERROR_STOP=1 -f sql/04_load_olap.sql
```

Para refazer o recorte da mesma fonte congelada (Python 3, biblioteca padrão):

```bash
python3 scripts/prepare_data.py
```

Para validar as restrições e reconciliar cada registro dos dois modelos:

```bash
python3 scripts/validate_database.py localhost 5432 lighting_service
```

Para gerar o relatório a partir do template incluído, instalar as dependências de `requirements.txt` em ambiente virtual e executar `python3 scripts/build_report.py`. Os diagramas são gerados como SVG vetorial e PNG, com cardinalidades em pé de galinha e chaves PK/FK. A geração de PNG usa também o comando `pdftoppm` do Poppler. Para gerar apenas os diagramas, executar `python3 scripts/build_diagrams.py`. As versões Mermaid incluem todos os atributos e relacionamentos. A preparação e a carga do banco não dependem dessas bibliotecas ou do Poppler.

## Recorte e interpretação

Fonte: [EMLURB 156, recurso oficial de 2025](https://dados.recife.pe.gov.br/dataset/central-de-atendimento-de-servicos-da-emlurb-156/resource/06872af2-9350-4c34-aa39-6337a1822ff7), Prefeitura do Recife / Emprel. Licença ODbL, conforme o catálogo. Atribuir essa origem e observar os termos da licença na redistribuição da base derivada.

Inclui somente o grupo `ILUMINACAO PUBLICA`, com data de demanda entre 01/01 e 31/08/2025: **34.492 registros**, 93 bairros, seis RPAs, dez serviços e cinco situações. Não corresponde a todo o ano de 2025. O manifesto identifica a versão original por SHA-256 e registra as transformações.

Há 33.662 registros `ATENDIDA` e 830 em outras situações **na versão publicada**. As últimas situações têm datas até 10/09/2025. Esses números não reconstituem o estoque pendente em 31/08/2025 e não descrevem o atendimento atual de 2026.

O CSV não publica protocolo, ponto de luz identificado, equipe, custos, SLA ou histórico de situações. A chave técnica é o número da linha no arquivo original de hash fixo. Não juntar versões usando essa chave. Um registro é tratado como uma solicitação publicada, sem garantir que registros distintos correspondam a defeitos físicos distintos.

A diferença entre `DATA_ULT_SITUACAO` e `DATA_DEMANDA` mede um intervalo documental. Para `ATENDIDA`, pode apoiar uma análise do intervalo até o atendimento registrado; não comprova a duração do reparo. Para outras situações, não é tempo de resolução. As coordenadas não são usadas: faltam em 31.127 dos 34.492 registros do recorte.

## Entrega

O relatório SBC apresenta contextualização, relação com ODS 11, requisitos e modelos. O dicionário completo e os scripts acompanham o texto como artefatos técnicos. A modelagem OLTP representa o estado publicado, sem transições inventadas. A estrela tem uma linha por solicitação e duas referências à mesma dimensão de data (demanda e última situação).

Mineração, dashboards com cinco consultas em cada nível e 5W2H ficam para 06/11/2026. A continuidade prevista está em `docs/final_delivery_plan.md`; não há resultados de mineração antecipados.

## Convenção de nomes

Arquivos e funções usam `snake_case` em inglês. Constantes Python usam `UPPER_SNAKE_CASE`. As pastas do projeto usam nomes em inglês. Os arquivos do relatório são uma exceção deliberada, com nomes em português.

Identificadores da modelagem, como `solicitacao`, `bairro_id` e `data_demanda`, permanecem em português. As colunas da fonte também mantêm seus nomes originais. Os comentários e a documentação usam português, com explicações curtas sobre as regras e decisões do código. No artigo, os identificadores da modelagem citados no texto aparecem em itálico.
