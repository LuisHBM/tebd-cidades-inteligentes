# Continuidade para 06/11/2026

Esta é uma proposta de continuidade; mineração, dashboards e 5W2H ainda não foram implementados.

## Dashboards e quinze consultas

Cada item abaixo deverá ter uma consulta SQL própria, indicador definido e visualização correspondente.

| Nível | Cinco perguntas previstas |
|---|---|
| Operacional | Lista de registros não ATENDIDA na versão; volume por situação; registros por bairro; registros por serviço; intervalos até última situação nos registros não ATENDIDA |
| Tático | Volume mensal por bairro; composição dos serviços por RPA; percentual ATENDIDA por bairro com denominador explícito; mediana até status ATENDIDA por serviço; percentil 90 até status ATENDIDA por RPA |
| Estratégico | Volume mensal municipal; distribuição das demandas entre RPAs; concentração dos registros não ATENDIDA por bairro; proporção de registros com intervalo até ATENDIDA acima de um limiar analítico declarado; participação dos tipos de serviço no conjunto do período |

O operacional será uma demonstração histórica da fotografia publicada, sem atualização em tempo real. O limiar de dias será apenas critério exploratório, sem chamá-lo de SLA ou atraso contratual. Médias e percentis de atendimento usarão somente ATENDIDA, sempre com quantidade de observações.

## Método de mineração

Proposta mínima: agrupamento K-means de bairros com volume, proporção de registros não ATENDIDA e mediana do intervalo até status ATENDIDA. Padronizar atributos e avaliar poucos valores de k com silhueta. Declarar os bairros excluídos por insuficiência de registros ATENDIDA, analisar sensibilidade e mostrar o tamanho dos grupos. Os grupos são perfis para investigação, sem interpretação causal nem classificação de bairros como seguros ou inseguros. Volume reflete também diferenças de uso dos canais e tamanho da rede, não apenas defeitos. Verificar se os perfis acrescentam informação às análises descritivas antes de adotá-los.

## Ação defensável

Usar os perfis para propor uma revisão amostral de registros e uma agenda de verificação por bairro/serviço, sujeita à confirmação com o órgão responsável. O 5W2H deverá detalhar responsáveis propostos, prazo, procedimento e custos estimados com hipóteses explícitas. Sem equipes ou custos na fonte, esses elementos serão uma proposta do grupo, não fatos municipais observados. O trabalho poderá sustentar prioridades de investigação; não provará economia de energia, redução de violência ou melhora do atendimento sem dados posteriores.
