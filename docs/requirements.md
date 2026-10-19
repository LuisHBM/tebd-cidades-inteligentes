# Requisitos do sistema

## Problema e solução

Os registros públicos da Central 156 precisam ser organizados e relacionados para comparar a concentração de solicitações de iluminação pública por bairro e serviço, a situação publicada e o intervalo até o atendimento registrado.

A solução é um banco relacional com carga reproduzível e um modelo multidimensional. As consultas apoiam a seleção de demandas para revisão. O volume de solicitações reflete os registros publicados e não mede sozinho a taxa de falhas da rede.

## Requisitos funcionais

Os requisitos funcionais (RF) definem as operações sobre a versão selecionada dos dados.

| Código | Requisito | Implementação |
|---|---|---|
| RF01 | Importar o recorte de iluminação pública e registrar sua origem | Preparação dos CSVs, manifesto e hashes |
| RF02 | Relacionar região político-administrativa (RPA), bairro, grupo de serviço, serviço, situação e solicitação | Seis tabelas transacionais com chaves primárias e estrangeiras |
| RF03 | Preservar endereço e datas de abertura e de última situação | Tabela `oltp.solicitacao` |
| RF04 | Rejeitar chaves duplicadas, referências inexistentes e datas invertidas | Restrições do banco e validação das cargas |
| RF05 | Consultar volume e situação por bairro, RPA, serviço e mês de abertura | Esquema estrela e consultas SQL |
| RF06 | Calcular o intervalo até a última situação, distinguindo `ATENDIDA` das demais | Medida em dias e dimensão de situação |
| RF07 | Refazer a carga analítica com o mesmo conteúdo | Recarga transacional e comparação dos registros |

## Requisitos técnicos

- Executar localmente com PostgreSQL 16 e cliente `psql`.
- Preparar os CSVs com Python 3 e biblioteca padrão.
- Identificar a versão da fonte por hash SHA-256.
- Usar arquivos oficiais por download direto, sem scraping ou preenchimento de dados por simulação.
- Manter os nomes dos identificadores da modelagem em português e os nomes de apoio do código em inglês.

## Regras dos dados

- A chave de uma solicitação é a posição da linha no CSV original. Ela só identifica o registro nessa versão e não é um protocolo municipal.
- Cada solicitação possui a última situação publicada. A carga não cria um histórico de transições.
- Registros no mesmo endereço são mantidos, pois podem representar solicitações distintas.
- A data da última situação deve ser igual ou posterior à abertura.
- O intervalo até atendimento registrado considera apenas a situação `ATENDIDA`. As demais situações não fornecem um tempo de resolução.
- O território é agrupado por bairro e RPA. Coordenadas não fazem parte do modelo.
- Cada linha da fato representa uma solicitação publicada. A dimensão de data possui os papéis de abertura e de última situação.
- O cadastro de grupos contém um registro porque o recorte fixa iluminação pública. A relação entre grupo e serviço é preservada da fonte.
- A carga recompõe uma única versão do OLAP. Ela não combina extrações nem reconstitui pendências históricas.

## Relação com o ODS 11

A iluminação integra as condições de uso de ruas e espaços públicos. O sistema pode apoiar a gestão urbana associada às metas 11.3 e 11.7 do Objetivo de Desenvolvimento Sustentável 11 (ODS 11). Os indicadores de atendimento não substituem os indicadores oficiais dessas metas e não demonstram efeitos sobre criminalidade, consumo de energia ou emissões. [Referência do Ipea](https://www.ipea.gov.br/ods/ods11.html).

## Fora do escopo

Aplicativo de abertura de chamados, cadastro de cidadãos ou equipes, despacho de ordens de serviço, inventário de postes, medição de energia, previsão de defeitos e mapas por coordenadas. A implementação usa os registros públicos e não se integra ao sistema interno da prefeitura.
