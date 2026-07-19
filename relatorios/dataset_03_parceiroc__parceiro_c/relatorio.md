# Relatório do teste A/B: Parceiro C

## Resumo executivo

**Decisão:** Escalar Grupo 1: apresentou a maior margem e as variantes ficaram abaixo do controle no intervalo de confiança.

**Resultado:** Maior margem diária na fase principal: Grupo 1, R$ 772,64; GMV diário de R$ 38.632,44.

**Status:** `escalar`  
**Variante recomendada:** `Grupo 1`

### Leitura executiva

O Grupo 2 elevou o cashback de 5,0% para 7,0%, igualando a taxa de comissão e reduzindo a margem direta a zero. Ao mesmo tempo, não houve evidência de crescimento: compradores variaram -0,6% e o GMV -3,1%, com intervalos inconclusivos para ambos. A perda de margem foi de 100,0%, com intervalo de 95% integralmente abaixo de zero, portanto o Grupo 1 preserva o resultado sem sacrificar os guardrails observados.

## Fases detectadas

| Fase | Início | Fim | Dias | Cashback por grupo | Comissão | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 01/07/2011 | 14/08/2011 | 45 | Grupo 1=5.00%; Grupo 2=7.00% | 7.00% | valida |

## Indicadores por variante

| Fase | Grupo | Cashback | Compradores/dia | GMV/dia | Margem/dia | Margem/GMV |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Grupo 1 | 5.00% | 101.1 | R$ 38.632,44 | R$ 772,64 | 2.00% |
| 1 | Grupo 2 | 7.00% | 100.5 | R$ 37.449,67 | R$ 0,00 | 0.00% |

## Evidência estatística

- Fase 1, Grupo 2 vs. Grupo 1: uplift de margem -100.0%, intervalo de R$ -831,56 a R$ -714,93 por dia.

## Qualidade dos dados

- Nenhum problema de qualidade foi encontrado.

## Recomendação operacional

Escalar Grupo 1: apresentou a maior margem e as variantes ficaram abaixo do controle no intervalo de confiança.

Antes da implantação, valide a quantidade de usuários expostos em cada grupo. Sem esse denominador, compradores representam volume observado, não taxa de conversão.

### Impacto e próximos passos

Em um cenário de tráfego equilibrado, a projeção do Grupo 1 para 100% do tráfego por 30 dias é de R$ 46.358,67 de margem, enquanto a configuração do Grupo 2 projeta margem zero. Essa projeção depende da estabilidade do tráfego e do comportamento após a escala.

1. Validar a quantidade de usuários expostos em cada grupo.
2. Escalar o Grupo 1 e acompanhar margem, compradores e GMV durante a implantação.
3. Não repetir a oferta de 7,0% sem aumento de comissão ou evidência prévia de crescimento suficiente para compensar a margem zerada.

## Limitações

- Dados agregados por grupo e dia não permitem analisar propensão individual.
- A projeção para 100% do tráfego pressupõe alocação equilibrada.
- A inferência usa diferenças diárias pareadas dentro de cada fase.
- O arquivo `contexto_llm.json` contém os números utilizados neste relatório.
