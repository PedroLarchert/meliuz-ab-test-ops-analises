# Análise reutilizável de testes A/B de cashback

Solução que lê todos os CSVs da pasta `data`, identifica automaticamente parceiros, grupos e mudanças de tratamento, calcula o resultado econômico e recomenda qual variante deve receber 100% do tráfego.

## Como usar

Abra esta pasta em um agente como Codex, Claude Code ou Cursor e escreva:

```text
Realize o relatório dos testes A/B.
```

Isso é tudo. As instruções do [`AGENTS.md`](AGENTS.md) orientam o agente a:

- criar o ambiente Python;
- instalar as dependências;
- analisar todos os CSVs da pasta `data`;
- revisar os relatórios executivos;
- apresentar as decisões e os arquivos gerados.

Para analisar novos testes, substitua ou adicione CSVs em `data` mantendo o mesmo schema e repita o pedido. Não é necessário alterar o código.

## Planilha de acompanhamento

[Resultados_Testes_AB_Meliuz](https://docs.google.com/spreadsheets/d/1p1tP9KXMCsG7f15vszWBoykMv_3W1RVqZH0wvkCLIvg/edit?usp=sharing)

O mesmo conteúdo é gerado em [`relatorios/acompanhamento_testes.csv`](relatorios/acompanhamento_testes.csv). A pasta também contém uma planilha pronta para reuniões em [`relatorios/Resultados_Testes_AB_Meliuz.xlsx`](relatorios/Resultados_Testes_AB_Meliuz.xlsx).

A planilha não é um arquivo estático: o pipeline a recria do zero em toda execução e substitui a versão anterior somente depois de concluir a gravação. As abas de testes, tabelas e gráficos se adaptam automaticamente à quantidade de arquivos, parceiros, grupos e fases encontrados.

## Resultados incluídos

| Parceiro | Decisão | Relatório executivo |
| --- | --- | --- |
| Parceiro A | Reexecutar com taxas fixas; quatro fases foram detectadas | [Abrir relatório](relatorios/dataset_01_parceiroa__parceiro_a/relatorio.md) |
| Parceiro B | Escalar o Grupo 1, com 4% de cashback | [Abrir relatório](relatorios/dataset_02_parceirob__parceiro_b/relatorio.md) |
| Parceiro C | Escalar o Grupo 1, com 5% de cashback | [Abrir relatório](relatorios/dataset_03_parceiroc__parceiro_c/relatorio.md) |

Cada pasta também contém as fases detectadas, o resumo das variantes, as comparações estatísticas, a economia incremental e o contexto estruturado usado pelo agente.

## O que a solução analisa

- quantidade variável de arquivos, parceiros e grupos;
- fases detectadas quando cashback ou comissão mudam de forma persistente;
- compradores, GMV, comissão, cashback, margem e ticket médio;
- comparação diária pareada, bootstrap e teste de permutação;
- uplift, custo incremental e crescimento necessário para break-even;
- projeção de margem por 30 dias para 100% do tráfego;
- qualidade básica dos dados, como nulos, duplicidades e datas desbalanceadas.

A métrica principal é:

```text
margem = comissão - cashback
```

Compradores e GMV são guardrails. A solução evita forçar um vencedor quando o tratamento mudou, não há contraste entre grupos ou a fase é curta.

## Fluxo de resolução

```text
CSV(s) -> validação -> fases -> métricas -> comparação estatística
       -> decisão determinística -> revisão do agente -> relatórios
```

### 1. Preparação pelo agente

Ao receber o pedido em linguagem natural, o agente verifica os CSVs, prepara o ambiente Python, instala as dependências e executa o pipeline. A quantidade de arquivos, parceiros, grupos e fases não precisa ser informada previamente.

### 2. Leitura e qualidade dos dados

O Python une os CSVs sem perder o arquivo de origem, converte datas e valores em reais e padroniza os nomes das colunas. Antes dos cálculos, registra valores inválidos, duplicidades, números negativos e diferenças na quantidade de datas entre os grupos. Linhas que não permitem cálculo confiável são removidas da análise.

### 3. Detecção das fases

Para cada dia, o Python calcula as taxas de cashback e comissão sobre o GMV. Uma nova fase é aberta quando a configuração muda de forma persistente por pelo menos três dias, considerando uma tolerância para pequenas diferenças de arredondamento. Assim, cada configuração de tratamento é analisada separadamente.

### 4. Métricas calculadas pelo Python

| Métrica | Cálculo ou uso |
| --- | --- |
| Resultado direto ou margem | `comissão - cashback`; principal métrica de decisão |
| Taxa de comissão | `comissão / GMV` |
| Taxa de cashback | `cashback / GMV` |
| Taxa de margem | `margem / GMV` |
| Ticket médio | `GMV / compradores` |
| Margem por comprador | `margem / compradores` |
| Médias diárias | compradores, GMV e margem por dia |
| Uplift | variação percentual da variante em relação ao Grupo 1 |
| Custo incremental | cashback adicional por comprador incremental, quando há ganho de compradores |
| Break-even | crescimento de GMV necessário para compensar a menor taxa de margem |
| Projeção para 100% | margem diária da variante multiplicada pelos grupos e por 30 dias |

Compradores e GMV funcionam como guardrails de crescimento. Como o dataset não informa usuários expostos, compradores representam volume observado, e não taxa de conversão.

### 5. Comparação estatística

Cada variante é comparada ao `Grupo 1` usando somente as datas presentes nos dois grupos e dentro da mesma fase. O Python calcula as diferenças diárias de compradores, GMV e margem, o uplift, um intervalo de confiança de 95% por bootstrap pareado e um valor-p aproximado por teste de permutação. A decisão automática usa o intervalo da margem; o valor-p é apresentado como evidência complementar.

### 6. Regra de decisão

O pipeline aplica uma regra conservadora e reproduzível:

1. Se houver mais de uma fase, recomenda **reexecutar** o teste com taxas fixas.
2. Se não houver diferença persistente de cashback, o resultado é **inconclusivo**.
3. Se a fase tiver menos de 14 dias, nenhuma variante é escalada automaticamente.
4. Entre fases válidas, identifica o grupo com maior margem diária.
5. Se o controle tiver a maior margem, ele só é escalado quando o limite superior de 95% de todas as variantes fica abaixo de zero; caso contrário, o controle é mantido.
6. Se uma variante tiver a maior margem, ela só é escalada quando o limite inferior de 95% da diferença de margem fica acima de zero; caso contrário, o controle é mantido.

Diferenças relevantes de compradores entre grupos geram um alerta para validar a distribuição de tráfego antes da implantação.

### 7. Trabalho da LLM e entrega

O Python é a fonte de todos os números e da decisão inicial. Para cada teste, ele gera tabelas, `contexto_llm.json` e uma primeira versão de `relatorio.md`. Orientado pelo [`prompt_relatorio.md`](prompt_relatorio.md), o agente:

1. lê a decisão, as fases, as métricas, os intervalos e os alertas;
2. verifica se a narrativa está coerente com os dados calculados;
3. explica o impacto econômico, os guardrails e as limitações em linguagem executiva;
4. complementa o relatório sem modificar ou inventar valores;
5. apresenta a recomendação e atualiza os arquivos de acompanhamento.

A LLM não substitui a regra estatística nem calcula métricas pelo prompt. Seu papel é interpretar, revisar e comunicar o resultado produzido pelo Python.

## Arquitetura

O código principal foi mantido em poucos arquivos:

```text
src/analise_ab/
  analise.py
  planilha.py
  relatorio.py
  pipeline.py
  __init__.py
  __main__.py
```

## Arquivos gerados

```text
relatorios/
  acompanhamento_testes.csv
  Resultados_Testes_AB_Meliuz.xlsx  # recriada automaticamente
  <teste_id>__<parceiro>/
    fases.csv
    resumo_variantes.csv
    comparacoes_estatisticas.csv
    economia_incremental.csv
    contexto_llm.json
    relatorio.md
```

## Execução manual opcional

Este caminho é útil apenas para quem deseja operar pelo terminal.

No Windows:

```powershell
python -m venv .venv
$python_venv = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { ".venv\bin\python.exe" }
& $python_venv -m pip install -e .
& $python_venv -m analise_ab
```

No Linux ou macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m analise_ab
```

Por padrão, o comando lê `data` e grava em `relatorios`. Para um arquivo específico:

```bash
python -m analise_ab --entrada data/dataset_02_parceiroB.csv
```

## Detecção de fases

Para cada data, a solução compara o cashback de todos os grupos e a comissão do parceiro. Uma nova fase começa quando a configuração muda além da tolerância e permanece por pelo menos três dias.

Pequenas diferenças de arredondamento são tratadas como a mesma taxa. A quantidade de fases e grupos não é definida previamente.

## Limitações

- Não existe o número de usuários expostos por grupo, portanto compradores não representam taxa de conversão.
- Não existem dados individuais para modelar propensão de usuários.
- A projeção para 100% do tráfego pressupõe divisão equilibrada entre grupos.
- A inferência usa observações diárias agregadas e pareadas dentro de cada fase.
