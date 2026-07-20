"""Geracao dos arquivos usados pelo agente e pela planilha."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def salvar_csv(dados: pd.DataFrame, destino: Path) -> None:
    """Salva uma tabela com codificacao compativel com Excel e Sheets."""

    destino.parent.mkdir(parents=True, exist_ok=True)
    dados.to_csv(destino, index=False, encoding="utf-8-sig")


def _converter_json(valor: Any) -> Any:
    """Converte tipos do pandas e numpy para JSON."""

    if isinstance(valor, pd.Timestamp):
        return valor.isoformat()
    if isinstance(valor, np.integer):
        return int(valor)
    if isinstance(valor, np.floating):
        return None if not np.isfinite(valor) else float(valor)
    if pd.isna(valor):
        return None
    raise TypeError(f"Tipo sem conversao para JSON: {type(valor)!r}")


def _registros(dados: pd.DataFrame) -> list[dict[str, Any]]:
    """Converte uma tabela em registros serializaveis."""

    return json.loads(dados.to_json(orient="records", date_format="iso"))


def gerar_contexto_llm(
    destino: Path,
    decisao: pd.Series,
    fases: pd.DataFrame,
    resumo: pd.DataFrame,
    comparacoes: pd.DataFrame,
    economia: pd.DataFrame,
    alertas_qualidade: pd.DataFrame,
) -> None:
    """Entrega ao agente os dados necessarios para redigir o relatorio."""

    contexto = {
        "objetivo": "Escolher a variante de cashback para 100% do trafego.",
        "decisao_deterministica": decisao.to_dict(),
        "fases": _registros(fases),
        "resumo_variantes": _registros(resumo),
        "comparacoes_estatisticas": _registros(comparacoes),
        "economia_incremental": _registros(economia),
        "alertas_qualidade": _registros(alertas_qualidade),
        "limitacoes_obrigatorias": [
            "Os dados sao agregados por dia e nao possuem usuarios expostos por grupo.",
            "A projecao para 100% assume divisao equilibrada de trafego.",
            "Os dados nao permitem modelar propensao individual.",
            "Mudancas persistentes de taxa devem ser analisadas como fases diferentes.",
        ],
    }
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(contexto, ensure_ascii=False, indent=2, default=_converter_json),
        encoding="utf-8",
    )


def _formatar_moeda(valor: float) -> str:
    """Formata moeda brasileira para o relatorio."""

    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def _tabela_markdown(linhas: list[list[str]], cabecalhos: list[str]) -> str:
    """Monta uma tabela Markdown simples."""

    cabecalho = "| " + " | ".join(cabecalhos) + " |"
    separador = "| " + " | ".join(["---"] * len(cabecalhos)) + " |"
    corpo = ["| " + " | ".join(linha) + " |" for linha in linhas]
    return "\n".join([cabecalho, separador, *corpo])


def gerar_relatorio_markdown(
    destino: Path,
    decisao: pd.Series,
    fases: pd.DataFrame,
    resumo: pd.DataFrame,
    comparacoes: pd.DataFrame,
    economia: pd.DataFrame,
    alertas_qualidade: pd.DataFrame,
) -> None:
    """Gera o relatorio base que sera revisado pelo agente."""

    linhas_fases = [
        [
            str(int(linha.fase_id)),
            linha.data_inicio.strftime("%d/%m/%Y"),
            linha.data_fim.strftime("%d/%m/%Y"),
            str(int(linha.dias)),
            linha.configuracao_cashback,
            f"{linha.taxa_comissao:.2%}",
            linha.status_fase,
        ]
        for linha in fases.itertuples()
    ]
    linhas_variantes = [
        [
            str(int(linha.fase_id)),
            str(linha.grupo),
            f"{linha.taxa_cashback:.2%}",
            f"{linha.compradores_dia:.1f}",
            _formatar_moeda(linha.vendas_dia),
            _formatar_moeda(linha.margem_dia),
            f"{linha.taxa_margem:.2%}",
        ]
        for linha in resumo.itertuples()
    ]
    evidencias = [
        (
            f"- Fase {linha.fase_id}, {linha.grupo_variante} vs. {linha.grupo_controle}: "
            f"uplift de margem {linha.uplift_percentual:+.1%}, intervalo de "
            f"{_formatar_moeda(linha.limite_inferior_95)} a "
            f"{_formatar_moeda(linha.limite_superior_95)} por dia."
        )
        for linha in comparacoes[comparacoes["metrica"] == "margem"].itertuples()
    ] or ["- Não houve comparação estatística aplicável."]
    qualidade = [
        f"- **{linha.severidade}:** {linha.descricao}"
        for linha in alertas_qualidade.itertuples()
    ] or ["- Nenhum problema de qualidade foi encontrado."]

    conteudo = f"""# Relatório do teste A/B: {decisao['parceiro']}

## Resumo executivo

**Decisão:** {decisao['decisao']}

**Resultado:** {decisao['resultado']}

**Status:** `{decisao['status']}`  
**Variante recomendada:** `{decisao['variante_recomendada']}`

### Leitura executiva

Substitua este texto por uma conclusao executiva baseada somente nos dados calculados.

## Fases detectadas

{_tabela_markdown(linhas_fases, ['Fase', 'Início', 'Fim', 'Dias', 'Cashback por grupo', 'Comissão', 'Status'])}

## Indicadores por variante

{_tabela_markdown(linhas_variantes, ['Fase', 'Grupo', 'Cashback', 'Compradores/dia', 'GMV/dia', 'Margem/dia', 'Margem/GMV'])}

## Evidência estatística

{chr(10).join(evidencias)}

## Qualidade dos dados

{chr(10).join(qualidade)}

## Recomendação operacional

{decisao['decisao']}

Antes da implantação, valide a quantidade de usuários expostos em cada grupo. Sem esse denominador, compradores representam volume observado, não taxa de conversão.

### Próximos passos

Substitua este texto por acoes objetivas, riscos e validacoes recomendadas.

## Limitações

- Dados agregados por grupo e dia não permitem analisar propensão individual.
- A projeção para 100% do tráfego pressupõe alocação equilibrada.
- A inferência usa diferenças diárias pareadas dentro de cada fase.
- O arquivo `contexto_llm.json` contém os números utilizados neste relatório.
"""
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(conteudo, encoding="utf-8")
