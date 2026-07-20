# Instruções para agentes de IA

Quando o usuário pedir algo como **"realize o relatório"**, faça todo o processo sem exigir conhecimento de programação.

## Preparação automática

1. Confirme que existem arquivos CSV na pasta `data`.
2. Verifique se o Python 3.10 ou superior está disponível.
3. Se a pasta `.venv` não existir, crie o ambiente virtual.
4. Instale ou atualize o projeto e as dependências no ambiente virtual.
5. Execute a análise de todos os CSVs da pasta `data`.

No Windows, use:

```powershell
python -m venv .venv
$python_venv = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { ".venv\bin\python.exe" }
& $python_venv -m pip install -e .
& $python_venv -m analise_ab
```

No Linux ou macOS, use:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m analise_ab
```

Se o ambiente já existir, reutilize-o e execute novamente a instalação antes da análise. Localize o interpretador em `.venv/Scripts/python.exe` ou `.venv/bin/python` conforme a instalação. Se uma distribuição tentar compilar `numpy` ou `pandas` e falhar, remova o ambiente incompleto e tente outro Python 3.10 ou superior disponível no sistema. Só peça uma ação ao usuário se nenhum Python compatível estiver instalado ou se o sistema exigir uma permissão que o agente não possa conceder.

## Geração do relatório

1. Localize cada pasta criada em `relatorios`.
2. Leia `prompt_relatorio.md` e o arquivo `contexto_llm.json` de cada teste.
3. Revise `relatorio.md`, preenchendo `### Leitura executiva` e `### Próximos passos` sem alterar números calculados.
4. Insira as narrativas revisadas na planilha com:

```powershell
& $python_venv -m analise_ab.planilha
```

5. Confirme que `relatorios/acompanhamento_testes.csv` foi atualizado.
6. Confirme que `relatorios/Resultados_Testes_AB_Meliuz.xlsx` foi recriada e recebeu as conclusões do agente.
7. Informe ao usuário a decisão de cada teste, as limitações e os caminhos dos arquivos gerados.

Nunca calcule métricas financeiras apenas pelo prompt. O código Python é a fonte dos números; a LLM é responsável pela interpretação e comunicação.
