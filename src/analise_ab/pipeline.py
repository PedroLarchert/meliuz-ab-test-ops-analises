"""Orquestracao e linha de comando da analise de testes A/B."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from analise_ab.analise import (
    ConfiguracaoAnalise,
    ErroDados,
    calcular_economia_incremental,
    carregar_dados,
    comparar_variantes,
    criar_identificador,
    detectar_fases,
    preparar_dados,
    resumir_variantes,
    tomar_decisoes,
    validar_dados,
)
from analise_ab.planilha import gerar_planilha_excel
from analise_ab.relatorio import gerar_contexto_llm, gerar_relatorio_markdown, salvar_csv


def _filtrar(dados: pd.DataFrame, teste_id: str, parceiro: str) -> pd.DataFrame:
    """Seleciona as linhas de um teste e parceiro."""

    if dados.empty or "teste_id" not in dados.columns or "parceiro" not in dados.columns:
        return dados.copy()
    return dados[
        (dados["teste_id"] == teste_id) & (dados["parceiro"] == parceiro)
    ].copy()


def _atualizar_acompanhamento(destino: Path, decisoes: pd.DataFrame) -> pd.DataFrame:
    """Atualiza o historico sem duplicar testes ja processados."""

    colunas = [
        "teste_id",
        "parceiro",
        "descricao",
        "resultado",
        "status",
        "variante_recomendada",
        "decisao",
        "quantidade_fases",
        "alertas",
    ]
    acompanhamento = decisoes[colunas].copy()
    if destino.exists():
        anterior = pd.read_csv(destino)
        colunas_comuns = [coluna for coluna in colunas if coluna in anterior.columns]
        anterior = anterior[colunas_comuns]
        acompanhamento = pd.concat([anterior, acompanhamento], ignore_index=True)
        acompanhamento = acompanhamento.drop_duplicates(
            ["teste_id", "parceiro"], keep="last"
        )
    salvar_csv(acompanhamento.sort_values(["teste_id", "parceiro"]), destino)
    return acompanhamento.sort_values(["teste_id", "parceiro"]).reset_index(drop=True)


def executar_pipeline(
    entrada: str | Path = "data",
    saida: str | Path = "relatorios",
    configuracao: ConfiguracaoAnalise | None = None,
) -> pd.DataFrame:
    """Executa a analise e devolve uma decisao por teste."""

    parametros = configuracao or ConfiguracaoAnalise()
    diretorio_saida = Path(saida)
    diretorio_saida.mkdir(parents=True, exist_ok=True)

    dados_brutos = carregar_dados(entrada)
    alertas_qualidade = validar_dados(dados_brutos)
    dados = preparar_dados(dados_brutos)
    if dados.empty:
        raise ErroDados("Nenhuma linha valida permaneceu apos a preparacao.")

    dados, fases = detectar_fases(dados, parametros)
    resumo = resumir_variantes(dados, parametros)
    comparacoes = comparar_variantes(dados, parametros)
    economia = calcular_economia_incremental(resumo, parametros)
    decisoes = tomar_decisoes(fases, resumo, comparacoes, parametros)

    acompanhamento = _atualizar_acompanhamento(
        diretorio_saida / "acompanhamento_testes.csv",
        decisoes,
    )

    for _, decisao in decisoes.iterrows():
        teste_id = str(decisao["teste_id"])
        parceiro = str(decisao["parceiro"])
        pasta_teste = diretorio_saida / (
            f"{teste_id}__{criar_identificador(parceiro)}"
        )

        fases_teste = _filtrar(fases, teste_id, parceiro)
        resumo_teste = _filtrar(resumo, teste_id, parceiro)
        comparacoes_teste = _filtrar(comparacoes, teste_id, parceiro)
        economia_teste = _filtrar(economia, teste_id, parceiro)
        qualidade_teste = _filtrar(alertas_qualidade, teste_id, parceiro)

        for nome_arquivo, tabela in {
            "fases.csv": fases_teste,
            "resumo_variantes.csv": resumo_teste,
            "comparacoes_estatisticas.csv": comparacoes_teste,
            "economia_incremental.csv": economia_teste,
        }.items():
            salvar_csv(tabela, pasta_teste / nome_arquivo)

        gerar_contexto_llm(
            pasta_teste / "contexto_llm.json",
            decisao,
            fases_teste,
            resumo_teste,
            comparacoes_teste,
            economia_teste,
            qualidade_teste,
        )
        gerar_relatorio_markdown(
            pasta_teste / "relatorio.md",
            decisao,
            fases_teste,
            resumo_teste,
            comparacoes_teste,
            economia_teste,
            qualidade_teste,
        )

    gerar_planilha_excel(
        diretorio_saida / "Resultados_Testes_AB_Meliuz.xlsx",
        dados,
        fases,
        resumo,
        comparacoes,
        economia,
        decisoes,
        acompanhamento,
        alertas_qualidade,
    )

    return decisoes


def _criar_argumentos() -> argparse.ArgumentParser:
    """Define opcoes para usos tecnicos ocasionais."""

    analisador = argparse.ArgumentParser(
        description="Analisa os testes A/B encontrados na pasta data."
    )
    analisador.add_argument("--entrada", default="data")
    analisador.add_argument("--saida", default="relatorios")
    analisador.add_argument("--grupo-controle", default="Grupo 1")
    return analisador


def executar() -> None:
    """Executa o pipeline a partir da linha de comando."""

    argumentos = _criar_argumentos().parse_args()
    parametros = ConfiguracaoAnalise(grupo_controle=argumentos.grupo_controle)
    try:
        decisoes = executar_pipeline(argumentos.entrada, argumentos.saida, parametros)
    except ErroDados as erro:
        raise SystemExit(f"Nao foi possivel gerar o relatorio: {erro}") from erro

    for linha in decisoes.itertuples():
        print(f"{linha.parceiro}: {linha.decisao}")


if __name__ == "__main__":
    executar()
