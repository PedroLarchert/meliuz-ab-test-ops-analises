"""Geracao da planilha executiva recriada a cada analise."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.worksheet import Worksheet


COR_VERDE = "00856A"
COR_VERDE_CLARO = "DDF3EC"
COR_AMARELO = "F4B400"
COR_AMARELO_CLARO = "FFF4CC"
COR_VERMELHO = "C43D4E"
COR_VERMELHO_CLARO = "FBE5E8"
COR_TEXTO = "263238"
COR_CINZA = "607D8B"
COR_CINZA_CLARO = "EEF2F4"
COR_BRANCO = "FFFFFF"
BORDA_CLARA = Side(style="thin", color="D5DEE2")

ROTULOS = {
    "teste_id": "Teste",
    "parceiro": "Parceiro",
    "data": "Data",
    "grupo": "Grupo",
    "fase_id": "Fase",
    "data_inicio": "Inicio",
    "data_fim": "Fim",
    "dias": "Dias",
    "quantidade_grupos": "Grupos",
    "quantidade_fases": "Fases",
    "taxa_comissao": "Taxa de comissao",
    "taxa_cashback": "Taxa de cashback",
    "taxa_margem": "Taxa de margem",
    "contraste_cashback": "Contraste de cashback",
    "configuracao_cashback": "Cashback por grupo",
    "status_fase": "Status da fase",
    "compradores": "Compradores",
    "compradores_dia": "Compradores por dia",
    "comissao": "Comissao (R$)",
    "cashback": "Cashback (R$)",
    "vendas_totais": "GMV (R$)",
    "vendas_dia": "GMV por dia (R$)",
    "margem": "Resultado direto (R$)",
    "margem_dia": "Resultado direto por dia (R$)",
    "ticket_medio": "Ticket medio (R$)",
    "margem_por_comprador": "Resultado por comprador (R$)",
    "projecao_margem_100_trafego": "Projecao para 100% (R$)",
    "dias_projecao": "Dias da projecao",
    "grupo_controle": "Controle",
    "grupo_variante": "Variante",
    "metrica": "Metrica",
    "dias_pareados": "Dias pareados",
    "media_controle": "Media do controle",
    "media_variante": "Media da variante",
    "diferenca_media": "Diferenca media",
    "uplift_percentual": "Uplift",
    "limite_inferior_95": "Limite inferior 95%",
    "limite_superior_95": "Limite superior 95%",
    "valor_p_permutacao": "Valor-p",
    "delta_compradores_dia": "Delta compradores por dia",
    "delta_vendas_dia": "Delta GMV por dia (R$)",
    "delta_cashback_dia": "Delta cashback por dia (R$)",
    "delta_margem_dia": "Delta resultado por dia (R$)",
    "custo_cashback_por_comprador_incremental": "Custo por comprador incremental (R$)",
    "uplift_gmv_observado": "Uplift de GMV observado",
    "uplift_gmv_break_even": "Uplift de GMV para break-even",
    "descricao": "Descricao",
    "resultado": "Resultado",
    "status": "Status",
    "variante_recomendada": "Variante recomendada",
    "decisao": "Decisao",
    "alertas": "Alertas",
    "periodo": "Periodo analisado",
    "configuracao": "Configuracao",
    "severidade": "Severidade",
    "tipo": "Tipo",
}


def _valor_excel(valor: object) -> object:
    """Converte escalares do pandas e numpy para tipos aceitos pelo Excel."""

    if valor is None or pd.isna(valor):
        return None
    if isinstance(valor, pd.Timestamp):
        return valor.to_pydatetime()
    if isinstance(valor, np.generic):
        return valor.item()
    return valor


def _nome_aba(nome: str, existentes: set[str]) -> str:
    """Cria um nome de aba valido e unico."""

    base = re.sub(r"[\\/*?:\[\]]", "-", nome).strip() or "Teste"
    base = base[:31]
    candidato = base
    contador = 2
    while candidato.lower() in existentes:
        sufixo = f" ({contador})"
        candidato = f"{base[:31 - len(sufixo)]}{sufixo}"
        contador += 1
    existentes.add(candidato.lower())
    return candidato


def _nome_tabela(nome: str, usados: set[str]) -> str:
    """Cria um identificador unico aceito por tabelas do Excel."""

    base = re.sub(r"[^A-Za-z0-9_]", "_", nome)
    if not base or base[0].isdigit():
        base = f"Tabela_{base}"
    candidato = base[:240]
    contador = 2
    while candidato.lower() in usados:
        sufixo = f"_{contador}"
        candidato = f"{base[:240 - len(sufixo)]}{sufixo}"
        contador += 1
    usados.add(candidato.lower())
    return candidato


def _formatacao_numero(coluna: str) -> str | None:
    """Escolhe a formatacao numerica de acordo com a metrica."""

    if coluna in {"data", "data_inicio", "data_fim"}:
        return "dd/mm/yyyy"
    if coluna.startswith("taxa_") or coluna in {
        "contraste_cashback",
        "uplift_percentual",
        "uplift_gmv_observado",
        "uplift_gmv_break_even",
    }:
        return "0.0%"
    if coluna in {
        "comissao",
        "cashback",
        "vendas_totais",
        "vendas_dia",
        "margem",
        "margem_dia",
        "ticket_medio",
        "margem_por_comprador",
        "projecao_margem_100_trafego",
        "delta_vendas_dia",
        "delta_cashback_dia",
        "delta_margem_dia",
        "custo_cashback_por_comprador_incremental",
    }:
        return '"R$" #,##0.00'
    if coluna in {
        "fase_id",
        "dias",
        "quantidade_grupos",
        "quantidade_fases",
        "compradores",
        "dias_pareados",
        "dias_projecao",
    }:
        return "#,##0"
    if coluna == "valor_p_permutacao":
        return "0.0000"
    return None


def _titulo(aba: Worksheet, texto: str, subtitulo: str, ultima_coluna: int = 8) -> None:
    """Cria o cabecalho visual de uma aba."""

    aba.merge_cells(start_row=1, start_column=1, end_row=2, end_column=ultima_coluna)
    celula = aba.cell(1, 1, texto)
    celula.font = Font(name="Aptos Display", size=20, bold=True, color=COR_BRANCO)
    celula.fill = PatternFill("solid", fgColor=COR_VERDE)
    celula.alignment = Alignment(vertical="center")
    aba.row_dimensions[1].height = 28
    aba.row_dimensions[2].height = 10

    aba.merge_cells(start_row=3, start_column=1, end_row=3, end_column=ultima_coluna)
    celula_subtitulo = aba.cell(3, 1, subtitulo)
    celula_subtitulo.font = Font(size=10, color=COR_CINZA)
    celula_subtitulo.alignment = Alignment(vertical="center")
    aba.row_dimensions[3].height = 22
    aba.sheet_view.showGridLines = False


def _secao(aba: Worksheet, linha: int, texto: str, ultima_coluna: int) -> None:
    """Destaca o inicio de uma secao."""

    aba.merge_cells(
        start_row=linha,
        start_column=1,
        end_row=linha,
        end_column=max(1, ultima_coluna),
    )
    celula = aba.cell(linha, 1, texto)
    celula.font = Font(bold=True, color=COR_TEXTO, size=11)
    celula.fill = PatternFill("solid", fgColor=COR_CINZA_CLARO)
    celula.alignment = Alignment(vertical="center")
    aba.row_dimensions[linha].height = 22


def _escrever_tabela(
    aba: Worksheet,
    dados: pd.DataFrame,
    linha: int,
    coluna: int,
    nome: str,
    tabelas_usadas: set[str],
) -> tuple[int, int]:
    """Escreve um DataFrame como tabela formatada e devolve seus limites."""

    if dados.empty:
        aba.cell(linha, coluna, "Sem dados aplicaveis.")
        aba.cell(linha, coluna).font = Font(italic=True, color=COR_CINZA)
        return linha, coluna

    colunas = list(dados.columns)
    for deslocamento, nome_coluna in enumerate(colunas):
        celula = aba.cell(linha, coluna + deslocamento, ROTULOS.get(nome_coluna, nome_coluna))
        celula.font = Font(bold=True, color=COR_BRANCO)
        celula.fill = PatternFill("solid", fgColor=COR_VERDE)
        celula.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        celula.border = Border(bottom=BORDA_CLARA)

    registros = dados.itertuples(index=False, name=None)
    for deslocamento_linha, registro in enumerate(registros, start=1):
        for deslocamento_coluna, valor in enumerate(registro):
            nome_coluna = colunas[deslocamento_coluna]
            celula = aba.cell(
                linha + deslocamento_linha,
                coluna + deslocamento_coluna,
                _valor_excel(valor),
            )
            celula.alignment = Alignment(vertical="top", wrap_text=True)
            formato = _formatacao_numero(nome_coluna)
            if formato is None and pd.api.types.is_numeric_dtype(dados[nome_coluna]):
                formato = "#,##0.00"
            if formato:
                celula.number_format = formato

    ultima_linha = linha + len(dados)
    ultima_coluna = coluna + len(colunas) - 1
    referencia = (
        f"{get_column_letter(coluna)}{linha}:"
        f"{get_column_letter(ultima_coluna)}{ultima_linha}"
    )
    tabela = Table(displayName=_nome_tabela(nome, tabelas_usadas), ref=referencia)
    tabela.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium4",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    aba.add_table(tabela)
    return ultima_linha, ultima_coluna


def _ajustar_colunas(aba: Worksheet, limite: int = 45) -> None:
    """Dimensiona as colunas sem deixar textos longos dominar a tela."""

    for indice in range(1, aba.max_column + 1):
        valores = [
            str(aba.cell(linha, indice).value)
            for linha in range(1, min(aba.max_row, 150) + 1)
            if aba.cell(linha, indice).value is not None
        ]
        largura = min(limite, max(11, max((len(valor) for valor in valores), default=8) + 2))
        aba.column_dimensions[get_column_letter(indice)].width = largura


def _grafico_barras(
    aba: Worksheet,
    linha_inicio: int,
    linha_fim: int,
    coluna_categorias: int,
    coluna_valores: int,
    titulo: str,
    ancora: str,
) -> None:
    """Adiciona um grafico de barras para uma tabela existente."""

    if linha_fim <= linha_inicio:
        return
    grafico = BarChart()
    grafico.type = "bar"
    grafico.style = 10
    grafico.title = titulo
    grafico.y_axis.title = "Configuracao"
    grafico.x_axis.title = "R$"
    grafico.x_axis.numFmt = '"R$" #,##0'
    grafico.height = min(12, max(7, (linha_fim - linha_inicio) * 0.55))
    grafico.width = 15
    valores = Reference(
        aba,
        min_col=coluna_valores,
        min_row=linha_inicio,
        max_row=linha_fim,
    )
    categorias = Reference(
        aba,
        min_col=coluna_categorias,
        min_row=linha_inicio + 1,
        max_row=linha_fim,
    )
    grafico.add_data(valores, titles_from_data=True)
    grafico.set_categories(categorias)
    grafico.legend = None
    aba.add_chart(grafico, ancora)


def _dados_decisoes(
    decisoes: pd.DataFrame,
    fases: pd.DataFrame,
    resumo: pd.DataFrame,
) -> pd.DataFrame:
    """Monta a tabela executiva com periodo e quantidade de grupos."""

    periodos = fases.groupby(["teste_id", "parceiro"], as_index=False).agg(
        data_inicio=("data_inicio", "min"),
        data_fim=("data_fim", "max"),
    )
    grupos = resumo.groupby(["teste_id", "parceiro"], as_index=False).agg(
        quantidade_grupos=("grupo", "nunique")
    )
    tabela = decisoes.merge(periodos, on=["teste_id", "parceiro"], how="left")
    tabela = tabela.merge(grupos, on=["teste_id", "parceiro"], how="left")
    tabela["periodo"] = tabela.apply(
        lambda linha: (
            f"{linha['data_inicio']:%d/%m/%Y} a {linha['data_fim']:%d/%m/%Y}"
            if pd.notna(linha["data_inicio"]) and pd.notna(linha["data_fim"])
            else "-"
        ),
        axis=1,
    )
    return tabela[
        [
            "teste_id",
            "parceiro",
            "periodo",
            "quantidade_grupos",
            "quantidade_fases",
            "variante_recomendada",
            "status",
            "decisao",
            "alertas",
        ]
    ]


def _resumo_fases_principais(resumo: pd.DataFrame, decisoes: pd.DataFrame) -> pd.DataFrame:
    """Seleciona as variantes da fase usada pela regra de decisao."""

    chaves = decisoes[["teste_id", "parceiro", "fase_principal"]].rename(
        columns={"fase_principal": "fase_id"}
    )
    principal = resumo.merge(chaves, on=["teste_id", "parceiro", "fase_id"], how="inner")
    principal = principal.copy()
    principal.insert(
        0,
        "configuracao",
        principal["parceiro"].astype(str) + " - " + principal["grupo"].astype(str),
    )
    return principal


def _criar_dashboard(
    pasta: Workbook,
    decisoes: pd.DataFrame,
    fases: pd.DataFrame,
    resumo: pd.DataFrame,
    tabelas_usadas: set[str],
) -> None:
    """Cria a visao executiva da pasta de trabalho."""

    aba = pasta.create_sheet("Dashboard")
    _titulo(
        aba,
        "Analise de Testes A/B de Cashback | Meliuz",
        "Visao executiva gerada automaticamente pelo pipeline Python.",
    )

    indicadores = [
        ("Testes analisados", len(decisoes), COR_VERDE_CLARO),
        (
            "Decisoes de escala",
            int((decisoes["status"] == "escalar").sum()),
            COR_VERDE_CLARO,
        ),
        (
            "Reexecutar ou inconclusivos",
            int(
                decisoes["status"]
                .isin(["reexecutar", "inconclusivo", "manter_controle"])
                .sum()
            ),
            COR_AMARELO_CLARO,
        ),
    ]
    for indice, (rotulo, valor, cor) in enumerate(indicadores):
        coluna = 1 + indice * 3
        aba.merge_cells(start_row=5, start_column=coluna, end_row=5, end_column=coluna + 1)
        aba.merge_cells(start_row=6, start_column=coluna, end_row=7, end_column=coluna + 1)
        aba.cell(5, coluna, rotulo)
        aba.cell(5, coluna).font = Font(bold=True, color=COR_CINZA)
        aba.cell(6, coluna, valor)
        aba.cell(6, coluna).font = Font(bold=True, size=20, color=COR_TEXTO)
        for linha in range(5, 8):
            for coluna_cartao in range(coluna, coluna + 2):
                aba.cell(linha, coluna_cartao).fill = PatternFill("solid", fgColor=cor)
                aba.cell(linha, coluna_cartao).alignment = Alignment(vertical="center")

    tabela_decisoes = _dados_decisoes(decisoes, fases, resumo)
    _secao(aba, 9, "Decisoes executivas", len(tabela_decisoes.columns))
    fim_decisoes, _ = _escrever_tabela(
        aba,
        tabela_decisoes,
        10,
        1,
        "DecisoesExecutivas",
        tabelas_usadas,
    )
    for linha in range(11, fim_decisoes + 1):
        aba.row_dimensions[linha].height = 42

    principal = _resumo_fases_principais(resumo, decisoes)[
        ["configuracao", "margem_dia", "vendas_dia", "taxa_cashback", "taxa_margem"]
    ]
    linha_graficos = fim_decisoes + 3
    _secao(aba, linha_graficos, "Base dos graficos da fase principal", len(principal.columns))
    inicio_tabela = linha_graficos + 1
    fim_graficos, _ = _escrever_tabela(
        aba,
        principal,
        inicio_tabela,
        1,
        "BaseGraficosDashboard",
        tabelas_usadas,
    )
    _grafico_barras(
        aba,
        inicio_tabela,
        fim_graficos,
        1,
        2,
        "Resultado direto diario da fase principal",
        "K5",
    )
    _grafico_barras(
        aba,
        inicio_tabela,
        fim_graficos,
        1,
        3,
        "GMV diario da fase principal",
        "K22",
    )
    aba.freeze_panes = "A10"
    _ajustar_colunas(aba, limite=38)


def _criar_aba_teste(
    pasta: Workbook,
    decisao: pd.Series,
    fases: pd.DataFrame,
    resumo: pd.DataFrame,
    comparacoes: pd.DataFrame,
    economia: pd.DataFrame,
    nomes_abas: set[str],
    tabelas_usadas: set[str],
) -> None:
    """Cria uma pagina executiva para um teste e parceiro."""

    teste_id = str(decisao["teste_id"])
    parceiro = str(decisao["parceiro"])
    filtro = (fases["teste_id"] == teste_id) & (fases["parceiro"] == parceiro)
    fases_teste = fases[filtro].copy()
    resumo_teste = resumo[
        (resumo["teste_id"] == teste_id) & (resumo["parceiro"] == parceiro)
    ].copy()
    comparacoes_teste = comparacoes[
        (comparacoes["teste_id"] == teste_id) & (comparacoes["parceiro"] == parceiro)
    ].copy()
    economia_teste = economia[
        (economia["teste_id"] == teste_id) & (economia["parceiro"] == parceiro)
    ].copy()

    nome = _nome_aba(parceiro, nomes_abas)
    aba = pasta.create_sheet(nome)
    periodo = (
        f"Teste: {teste_id} | Periodo analisado: "
        f"{fases_teste['data_inicio'].min():%d/%m/%Y} a "
        f"{fases_teste['data_fim'].max():%d/%m/%Y}"
    )
    _titulo(aba, f"{parceiro} | Resultado do teste A/B", periodo)

    cor_status = COR_VERDE_CLARO if decisao["status"] == "escalar" else COR_AMARELO_CLARO
    aba.merge_cells("A5:H5")
    aba["A5"] = "RECOMENDACAO"
    aba["A5"].font = Font(bold=True, color=COR_CINZA)
    aba.merge_cells("A6:H7")
    aba["A6"] = str(decisao["decisao"])
    aba["A6"].font = Font(bold=True, size=13, color=COR_TEXTO)
    aba["A6"].alignment = Alignment(vertical="center", wrap_text=True)
    for linha in range(5, 8):
        for coluna in range(1, 9):
            aba.cell(linha, coluna).fill = PatternFill("solid", fgColor=cor_status)

    resumo_exibicao = resumo_teste[
        [
            "fase_id",
            "grupo",
            "dias",
            "taxa_cashback",
            "compradores_dia",
            "vendas_dia",
            "margem_dia",
            "taxa_margem",
            "projecao_margem_100_trafego",
        ]
    ].copy()
    resumo_exibicao.insert(
        0,
        "configuracao",
        "Fase "
        + resumo_exibicao["fase_id"].astype(str)
        + " - "
        + resumo_exibicao["grupo"].astype(str),
    )
    _secao(aba, 9, "Desempenho por variante e fase", len(resumo_exibicao.columns))
    inicio_resumo = 10
    fim_resumo, _ = _escrever_tabela(
        aba,
        resumo_exibicao,
        inicio_resumo,
        1,
        f"Resumo_{teste_id}_{parceiro}",
        tabelas_usadas,
    )
    _grafico_barras(
        aba,
        inicio_resumo,
        fim_resumo,
        1,
        8,
        "Resultado direto por configuracao",
        "L5",
    )
    _grafico_barras(
        aba,
        inicio_resumo,
        fim_resumo,
        1,
        7,
        "GMV por configuracao",
        "L22",
    )

    linha_fases = fim_resumo + 3
    fases_exibicao = fases_teste[
        [
            "fase_id",
            "data_inicio",
            "data_fim",
            "dias",
            "quantidade_grupos",
            "configuracao_cashback",
            "taxa_comissao",
            "status_fase",
        ]
    ]
    _secao(aba, linha_fases, "Fases detectadas", len(fases_exibicao.columns))
    fim_fases, _ = _escrever_tabela(
        aba,
        fases_exibicao,
        linha_fases + 1,
        1,
        f"Fases_{teste_id}_{parceiro}",
        tabelas_usadas,
    )

    comparacoes_margem = comparacoes_teste[comparacoes_teste["metrica"] == "margem"][
        [
            "fase_id",
            "grupo_controle",
            "grupo_variante",
            "dias_pareados",
            "uplift_percentual",
            "limite_inferior_95",
            "limite_superior_95",
            "valor_p_permutacao",
        ]
    ]
    linha_comparacoes = fim_fases + 3
    _secao(
        aba,
        linha_comparacoes,
        "Comparacao estatistica da margem",
        max(1, len(comparacoes_margem.columns)),
    )
    fim_comparacoes, _ = _escrever_tabela(
        aba,
        comparacoes_margem,
        linha_comparacoes + 1,
        1,
        f"Comparacoes_{teste_id}_{parceiro}",
        tabelas_usadas,
    )

    economia_exibicao = economia_teste.drop(columns=["teste_id", "parceiro"], errors="ignore")
    linha_economia = fim_comparacoes + 3
    _secao(aba, linha_economia, "Economia incremental", max(1, len(economia_exibicao.columns)))
    _escrever_tabela(
        aba,
        economia_exibicao,
        linha_economia + 1,
        1,
        f"Economia_{teste_id}_{parceiro}",
        tabelas_usadas,
    )
    aba.freeze_panes = "A10"
    _ajustar_colunas(aba)


def _criar_aba_dados(
    pasta: Workbook,
    nome: str,
    dados: pd.DataFrame,
    tabelas_usadas: set[str],
    colunas: list[str] | None = None,
) -> None:
    """Cria uma aba tabular para auditoria dos resultados."""

    aba = pasta.create_sheet(nome)
    tabela = dados[colunas].copy() if colunas else dados.copy()
    _titulo(aba, nome, "Dados calculados pelo pipeline Python.", max(8, len(tabela.columns)))
    _escrever_tabela(aba, tabela, 5, 1, f"Tabela_{nome}", tabelas_usadas)
    aba.freeze_panes = "A6"
    aba.auto_filter.ref = aba.dimensions
    _ajustar_colunas(aba)


def _criar_metodologia(pasta: Workbook) -> None:
    """Registra as definicoes usadas para interpretar a planilha."""

    aba = pasta.create_sheet("Metodologia")
    _titulo(
        aba,
        "Metodologia",
        "Definicoes e criterios usados pela analise automatizada.",
    )
    linhas = [
        ("Metrica principal", "Resultado direto = comissao - cashback."),
        (
            "Guardrails",
            "Compradores e GMV sao comparados ao controle, mas nao representam "
            "conversao sem dados de exposicao.",
        ),
        (
            "Fases",
            "Mudancas persistentes de cashback ou comissao por pelo menos tres "
            "dias criam uma nova fase.",
        ),
        (
            "Inferencia",
            "Bootstrap e permutacao usam diferencas diarias pareadas dentro de "
            "cada fase.",
        ),
        (
            "Escala",
            "Uma variante so e escalada quando o intervalo de 95% da diferenca "
            "de resultado direto sustenta a superioridade.",
        ),
        (
            "Reexecucao",
            "Testes com mais de uma fase devem ser reexecutados com tratamentos "
            "fixos.",
        ),
        (
            "Projecao",
            "A projecao de 30 dias pressupoe distribuicao equilibrada de trafego "
            "entre os grupos.",
        ),
    ]
    _secao(aba, 5, "Regras", 8)
    for indice, (tema, explicacao) in enumerate(linhas, start=6):
        aba.cell(indice, 1, tema)
        aba.cell(indice, 1).font = Font(bold=True, color=COR_TEXTO)
        aba.merge_cells(start_row=indice, start_column=2, end_row=indice, end_column=8)
        aba.cell(indice, 2, explicacao)
        aba.cell(indice, 2).alignment = Alignment(wrap_text=True, vertical="top")
        aba.row_dimensions[indice].height = 34
    _ajustar_colunas(aba)
    aba.column_dimensions["A"].width = 22
    aba.column_dimensions["B"].width = 70


def gerar_planilha_excel(
    destino: str | Path,
    dados: pd.DataFrame,
    fases: pd.DataFrame,
    resumo: pd.DataFrame,
    comparacoes: pd.DataFrame,
    economia: pd.DataFrame,
    decisoes: pd.DataFrame,
    acompanhamento: pd.DataFrame,
    alertas_qualidade: pd.DataFrame,
) -> Path:
    """Recria a planilha completa e substitui o arquivo anterior com seguranca."""

    caminho = Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(f".{caminho.stem}.temporario.xlsx")

    pasta = Workbook()
    pasta.remove(pasta.active)
    nomes_abas: set[str] = set()
    tabelas_usadas: set[str] = set()

    _criar_dashboard(pasta, decisoes, fases, resumo, tabelas_usadas)
    nomes_abas.add("dashboard")
    _criar_aba_dados(pasta, "Acompanhamento", acompanhamento, tabelas_usadas)
    _criar_aba_dados(pasta, "Consolidado", resumo, tabelas_usadas)
    _criar_aba_dados(pasta, "Fases", fases, tabelas_usadas)
    _criar_aba_dados(pasta, "Comparacoes", comparacoes, tabelas_usadas)
    _criar_aba_dados(pasta, "Economia", economia, tabelas_usadas)
    _criar_aba_dados(pasta, "Qualidade", alertas_qualidade, tabelas_usadas)
    _criar_aba_dados(pasta, "Dados", dados, tabelas_usadas)
    _criar_metodologia(pasta)
    nomes_abas.update(aba.title.lower() for aba in pasta.worksheets)

    for _, decisao in decisoes.iterrows():
        _criar_aba_teste(
            pasta,
            decisao,
            fases,
            resumo,
            comparacoes,
            economia,
            nomes_abas,
            tabelas_usadas,
        )

    try:
        pasta.save(temporario)
        temporario.replace(caminho)
    finally:
        if temporario.exists():
            temporario.unlink()
    return caminho
