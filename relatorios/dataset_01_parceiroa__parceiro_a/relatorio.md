# Relatório do teste A/B: Parceiro A

## Resumo executivo

**Decisão:** Não escalar automaticamente. O tratamento mudou durante o período; analise as fases e reexecute o teste com taxas fixas.

**Resultado:** Maior margem diária na fase principal: Grupo 1, R$ 5.420,19; GMV diário de R$ 68.042,98.

**Status:** `reexecutar`  
**Variante recomendada:** `nenhuma`

### Leitura executiva

O teste não representa um único experimento: cashback e comissão mudaram quatro vezes ao longo do período. Na fase 1, os Grupos 2 e 3 elevaram compradores e GMV, mas reduziram a margem diária em 14,4% e 48,7% contra o Grupo 1. Essa relação não pode ser extrapolada para todo o período porque as fases seguintes usaram outras taxas; nas fases 3 e 4, os grupos sequer receberam tratamentos de cashback distintos. A decisão mais segura é não escolher um vencedor e executar um novo teste controlado.

## Fases detectadas

| Fase | Início | Fim | Dias | Cashback por grupo | Comissão | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 01/01/2011 | 22/02/2011 | 53 | Grupo 1=3.01%; Grupo 2=5.50%; Grupo 3=7.99% | 11.00% | valida |
| 2 | 23/02/2011 | 10/03/2011 | 16 | Grupo 1=5.00%; Grupo 2=5.50%; Grupo 3=4.02% | 11.00% | valida |
| 3 | 11/03/2011 | 14/03/2011 | 4 | Grupo 1=9.99%; Grupo 2=9.99%; Grupo 3=10.00% | 15.50% | sem_contraste |
| 4 | 15/03/2011 | 02/04/2011 | 19 | Grupo 1=5.00%; Grupo 2=5.00%; Grupo 3=5.00% | 11.00% | sem_contraste |

## Indicadores por variante

| Fase | Grupo | Cashback | Compradores/dia | GMV/dia | Margem/dia | Margem/GMV |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Grupo 1 | 3.03% | 118.2 | R$ 68.042,98 | R$ 5.420,19 | 7.97% |
| 1 | Grupo 2 | 5.50% | 138.6 | R$ 84.346,00 | R$ 4.638,87 | 5.50% |
| 1 | Grupo 3 | 7.97% | 150.9 | R$ 91.801,11 | R$ 2.781,21 | 3.03% |
| 2 | Grupo 1 | 5.00% | 69.8 | R$ 37.872,31 | R$ 2.270,38 | 5.99% |
| 2 | Grupo 2 | 5.50% | 70.4 | R$ 38.336,88 | R$ 2.108,81 | 5.50% |
| 2 | Grupo 3 | 4.31% | 66.0 | R$ 35.063,88 | R$ 2.345,69 | 6.69% |
| 3 | Grupo 1 | 9.99% | 189.5 | R$ 119.812,25 | R$ 6.603,25 | 5.51% |
| 3 | Grupo 2 | 9.99% | 204.8 | R$ 120.171,00 | R$ 6.626,50 | 5.51% |
| 3 | Grupo 3 | 9.92% | 208.8 | R$ 118.965,75 | R$ 6.636,75 | 5.58% |
| 4 | Grupo 1 | 5.01% | 78.6 | R$ 48.088,89 | R$ 2.879,05 | 5.99% |
| 4 | Grupo 2 | 5.01% | 80.2 | R$ 45.193,89 | R$ 2.705,89 | 5.99% |
| 4 | Grupo 3 | 5.02% | 79.9 | R$ 46.500,63 | R$ 2.779,21 | 5.98% |

## Evidência estatística

- Fase 1, Grupo 2 vs. Grupo 1: uplift de margem -14.4%, intervalo de R$ -1.120,43 a R$ -459,74 por dia.
- Fase 1, Grupo 3 vs. Grupo 1: uplift de margem -48.7%, intervalo de R$ -3.088,02 a R$ -2.232,26 por dia.
- Fase 2, Grupo 2 vs. Grupo 1: uplift de margem -7.1%, intervalo de R$ -417,33 a R$ 90,63 por dia.
- Fase 2, Grupo 3 vs. Grupo 1: uplift de margem +3.3%, intervalo de R$ -329,44 a R$ 514,63 por dia.
- Fase 3, Grupo 2 vs. Grupo 1: uplift de margem +0.4%, intervalo de R$ -1.503,00 a R$ 1.320,75 por dia.
- Fase 3, Grupo 3 vs. Grupo 1: uplift de margem +0.5%, intervalo de R$ -1.814,50 a R$ 1.493,00 por dia.
- Fase 4, Grupo 2 vs. Grupo 1: uplift de margem -6.0%, intervalo de R$ -552,32 a R$ 202,21 por dia.
- Fase 4, Grupo 3 vs. Grupo 1: uplift de margem -3.5%, intervalo de R$ -514,37 a R$ 309,48 por dia.

## Qualidade dos dados

- Nenhum problema de qualidade foi encontrado.

## Recomendação operacional

Não escalar automaticamente. O tratamento mudou durante o período; analise as fases e reexecute o teste com taxas fixas.

Antes da implantação, valide a quantidade de usuários expostos em cada grupo. Sem esse denominador, compradores representam volume observado, não taxa de conversão.

### Próximos passos

1. Definir uma taxa fixa de cashback por grupo e manter a comissão do parceiro estável durante todo o novo teste.
2. Registrar usuários expostos por grupo para calcular conversão e confirmar que a distribuição de tráfego está equilibrada.
3. Manter a nova configuração por pelo menos 14 dias e acompanhar margem como métrica principal, com compradores e GMV como guardrails.
4. Reaplicar o pipeline ao novo CSV antes de escalar qualquer variante.

## Limitações

- Dados agregados por grupo e dia não permitem analisar propensão individual.
- A projeção para 100% do tráfego pressupõe alocação equilibrada.
- A inferência usa diferenças diárias pareadas dentro de cada fase.
- O arquivo `contexto_llm.json` contém os números utilizados neste relatório.
