# Relatório do teste A/B: Parceiro B

## Resumo executivo

**Decisão:** Escalar Grupo 1: apresentou a maior margem e as variantes ficaram abaixo do controle no intervalo de confiança.

**Resultado:** Maior margem diária na fase principal: Grupo 1, R$ 4.697,87; GMV diário de R$ 67.111,77.

**Status:** `escalar`  
**Variante recomendada:** `Grupo 1`

### Leitura executiva

O aumento de cashback não trouxe crescimento para compensar a perda econômica. Em relação ao Grupo 1, o Grupo 2 apresentou 31,8% menos compradores, 30,1% menos GMV e 50,0% menos margem; o Grupo 3 apresentou quedas de 37,1%, 35,8% e 81,6%, respectivamente. Como os intervalos de 95% da diferença de margem ficaram integralmente abaixo de zero, a evidência favorece manter a oferta de 4,0% do Grupo 1.

## Fases detectadas

| Fase | Início | Fim | Dias | Cashback por grupo | Comissão | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 01/05/2011 | 30/06/2011 | 61 | Grupo 1=4.00%; Grupo 2=6.00%; Grupo 3=9.00% | 11.00% | valida |

## Indicadores por variante

| Fase | Grupo | Cashback | Compradores/dia | GMV/dia | Margem/dia | Margem/GMV |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Grupo 1 | 4.00% | 131.0 | R$ 67.111,77 | R$ 4.697,87 | 7.00% |
| 1 | Grupo 2 | 6.00% | 89.4 | R$ 46.934,74 | R$ 2.346,84 | 5.00% |
| 1 | Grupo 3 | 9.00% | 82.4 | R$ 43.114,15 | R$ 862,18 | 2.00% |

## Evidência estatística

- Fase 1, Grupo 2 vs. Grupo 1: uplift de margem -50.0%, intervalo de R$ -2.655,89 a R$ -2.059,85 por dia.
- Fase 1, Grupo 3 vs. Grupo 1: uplift de margem -81.6%, intervalo de R$ -4.266,11 a R$ -3.449,58 por dia.

## Qualidade dos dados

- Nenhum problema de qualidade foi encontrado.

## Recomendação operacional

Escalar Grupo 1: apresentou a maior margem e as variantes ficaram abaixo do controle no intervalo de confiança.

Antes da implantação, valide a quantidade de usuários expostos em cada grupo. Sem esse denominador, compradores representam volume observado, não taxa de conversão.

### Impacto e próximos passos

Em um cenário de tráfego equilibrado, a projeção do Grupo 1 para 100% do tráfego por 30 dias é de R$ 422.808,20 de margem. Essa projeção deve ser tratada como cenário, não como previsão garantida.

1. Validar a quantidade de usuários expostos por grupo antes da mudança.
2. Escalar o Grupo 1 e monitorar diariamente margem, compradores e GMV.
3. Interromper ou revisar a implantação se a distribuição real de tráfego ou o comportamento pós-escala divergir do período analisado.

## Limitações

- Dados agregados por grupo e dia não permitem analisar propensão individual.
- A projeção para 100% do tráfego pressupõe alocação equilibrada.
- A inferência usa diferenças diárias pareadas dentro de cada fase.
- O arquivo `contexto_llm.json` contém os números utilizados neste relatório.
