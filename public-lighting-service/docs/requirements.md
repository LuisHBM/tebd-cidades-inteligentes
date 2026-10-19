# Escopo da entrega de 19/10/2026

## Problema e pergunta

Como organizar as solicitações publicadas de iluminação pública para identificar concentrações por bairro e serviço e diferenças na situação e no intervalo até o atendimento registrado?

A solução proposta é um banco relacional reproduzível e uma camada multidimensional de apoio à revisão das demandas. A gestão pode usar os resultados para selecionar bairros e tipos de serviço que mereçam investigação. Mais chamados não provam maior taxa de falhas: faltam denominadores como número de luminárias e população atendida.

## Relação com ODS 11

A iluminação é uma condição de uso de ruas e espaços públicos. O projeto se relaciona à meta 11.7, voltada a espaços públicos seguros, inclusivos e acessíveis, e à gestão urbana da meta 11.3. Trata-se de uma contribuição proposta ao planejamento; as métricas de chamados não são os indicadores oficiais dessas metas e não medem redução da criminalidade, consumo de energia ou emissões. Referência: https://www.ipea.gov.br/ods/ods11.html.

## Requisitos funcionais

| ID | Requisito | Evidência na parcial |
|---|---|---|
| RF01 | Importar o grupo de iluminação no período fixado, com origem rastreável | Script de preparação, manifesto e hashes |
| RF02 | Organizar RPA, bairro, grupo, serviço, situação e solicitação em entidades relacionadas | Seis tabelas OLTP com PK/FK |
| RF03 | Preservar as datas de demanda e de última situação e o endereço publicado | Tabela solicitação |
| RF04 | Rejeitar referências inexistentes, duplicidade de chave e datas invertidas | Restrições e validação PostgreSQL |
| RF05 | Consultar volume e situação por serviço, bairro, RPA e mês de demanda | Modelo estrela e consultas de conferência |
| RF06 | Calcular intervalo até a última situação, distinguindo ATENDIDA das demais | Fato com intervalo em dias e dimensão de situação |
| RF07 | Refazer a carga analítica com o mesmo resultado | Recarga transacional e comparação do conteúdo |

## Requisitos não funcionais e regras

- PostgreSQL 16; execução local, sem serviço pago ou API autenticada.
- Python 3 com biblioteca padrão para preparar os CSVs. O relatório usa bibliotecas opcionais.
- Nenhum scraping, dado simulado, geocodificação ou coleta de dados pessoais de solicitantes.
- A posição no CSV original identifica o registro somente nessa versão. Nunca apresentar essa chave como protocolo.
- Uma fotografia da última situação por solicitação; não há histórico de mudanças.
- Não deduplicar por endereço: duas demandas no mesmo endereço podem ser registros legítimos diferentes.
- Sem coordenadas no modelo mínimo. Bairro e RPA bastam para o agrupamento territorial.
- O OLAP descreve o conjunto publicado, sem reconstruir pendências em datas passadas.
- Grupo de serviço tem uma linha no recorte, mas preserva o domínio e a dependência grupo-serviço existentes na fonte; nenhuma categoria foi inventada para completar o modelo.
- O OLTP é um protótipo de persistência dos registros publicados. Não é uma integração com o sistema operacional real da prefeitura.

## Fora do escopo

Aplicativo de abertura de chamados, cadastro de cidadãos ou equipes, despacho de ordens de serviço, inventário de postes, medição de energia, previsão de defeitos e mapas por coordenadas. Esses itens exigiriam novas fontes ou simulação e não são necessários à parcial.
