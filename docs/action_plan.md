# Plano de ação 5W2H

**Objetivo: reduzir os chamados repetidos de iluminação, agindo antes de o cidadão reclamar.**

O plano trata o mesmo objetivo em três escalas. Cada coluna é uma ação completa, e cada linha compara a mesma pergunta na rua, no bairro e na cidade.

| | Operacional: rua | Tático: bairro | Estratégico: cidade |
|---|---|---|---|
| **What** | Inspecionar as **328 ruas crônicas** apontadas pela rede neural (ex.: Av. Norte Miguel Arraes de Alencar, Av. Governador Agamenon Magalhães) | Revisar os circuitos dos **26 bairros do grupo "circuitos apagados"** do k-means (ex.: Guabiraba, Macaxeira, Casa Amarela) | Adotar a **lista mensal de ruas prioritárias** como rotina da EMLURB |
| **Why** | Essas ruas são **9%** do total, mas geraram **mais de 1/3** dos chamados da primeira semana | Nesses bairros, **1 em cada 4** chamados é de trecho inteiro apagado; na cidade, **1 em 6** | A rede neural acertou **92%** das 200 ruas que indicou como prioritárias |
| **Where** | Ruas da lista do mês (a primeira, de setembro de 2025, tem 328 ruas crônicas) | Principalmente RPAs 2 e 3 | Toda a cidade, começando pela RPA 6, onde os chamados mais cresceram |
| **When** | Toda primeira semana do mês | A cada trimestre | A partir do próximo ano |
| **Who** | Equipe de campo | Coordenação de iluminação | Direção da EMLURB |
| **How** | Vistoria preventiva de lâmpadas e circuito | Checar relés e alimentação dos trechos que apagam | Gerar a lista todo mês e cadastrar os postes |
| **How much** | Tempo das equipes já existentes | Equipe de rede elétrica e troca de peças quando necessário | Cadastro dos postes (investimento único) |

## Origem dos dados

| Dado | Origem |
|---|---|
| 328 ruas crônicas; 9% das ruas e mais de 1/3 dos chamados da primeira semana | Rede neural de sobrevivência: tipos de rua validados em agosto de 2025 e lista de setembro ([survival.md](analysis/survival.md), [inspection_plan_2025_09.csv](analysis/inspection_plan_2025_09.csv)) |
| 92% de acerto nas 200 ruas prioritárias | Rede neural de sobrevivência: teste em agosto de 2025 ([survival.md](analysis/survival.md)) |
| 26 bairros do grupo "circuitos apagados"; 1 em 4 chamados de trecho apagado; RPAs 2 e 3 | k-means de bairros, perfil 2 ([kmeans.md](analysis/kmeans.md)) |
| Na cidade, 1 em 6 chamados de trecho apagado | Consulta estratégica Q4: ACENDER CIRCUITO é 17,6% dos chamados ([dashboards.md](dashboards.md)) |
| RPA 6 com maior crescimento | Consulta tática Q1: 851 chamados em janeiro e 1.154 em agosto ([dashboards.md](dashboards.md)) |

## Premissas

- A inspeção preventiva orienta a manutenção para os locais certos. Os dados não medem se ela evita o chamado.
- A base não informa custos, equipes ou produtividade. Por isso, o How much indica recursos, não valores.
