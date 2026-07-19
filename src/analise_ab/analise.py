"""Leitura, validacao e analise dos testes A/B de cashback."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ConfiguracaoAnalise:
    """Centraliza os parametros ajustaveis da analise."""

    grupo_controle: str = "Grupo 1"
    tolerancia_cashback: float = 0.003
    tolerancia_comissao: float = 0.003
    minimo_dias_fase: int = 3
    minimo_dias_decisao: int = 14
    repeticoes_bootstrap: int = 10_000
    repeticoes_permutacao: int = 20_000
    dias_projecao: int = 30
    semente_aleatoria: int = 20_260_718


class ErroDados(ValueError):
    """Indica que os dados nao permitem executar a analise."""


COLUNAS_ESPERADAS = {
    "data": "data",
    "grupos_de_usuarios": "grupo",
    "grupo_de_usuarios": "grupo",
    "grupo": "grupo",
    "parceiro": "parceiro",
    "compradores": "compradores",
    "comissao": "comissao",
    "cashback": "cashback",
    "vendas_totais": "vendas_totais",
}
COLUNAS_OBRIGATORIAS = {
    "data",
    "grupo",
    "parceiro",
    "compradores",
    "comissao",
    "cashback",
    "vendas_totais",
}
COLUNAS_NUMERICAS = ["compradores", "comissao", "cashback", "vendas_totais"]
CHAVES_FASE = ["teste_id", "parceiro", "fase_id"]


def normalizar_texto(texto: object) -> str:
    """Remove acentos e padroniza textos usados como identificadores."""

    valor = unicodedata.normalize("NFKD", str(texto))
    valor = "".join(caractere for caractere in valor if not unicodedata.combining(caractere))
    valor = re.sub(r"[^a-zA-Z0-9]+", "_", valor.strip().lower())
    return valor.strip("_")


def criar_identificador(texto: object) -> str:
    """Cria um identificador estavel para arquivos e pastas."""

    return normalizar_texto(texto) or "sem_identificador"


def _converter_moeda(serie: pd.Series) -> pd.Series:
    """Converte valores monetarios brasileiros para numero."""

    texto = serie.astype("string").str.strip()
    texto = texto.str.replace("R$", "", regex=False).str.replace(" ", "", regex=False)
    texto = texto.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(texto, errors="coerce")


def _listar_arquivos(entrada: str | Path) -> list[Path]:
    """Localiza um CSV ou todos os CSVs de uma pasta."""

    caminho = Path(entrada)
    if caminho.is_file() and caminho.suffix.lower() == ".csv":
        return [caminho]
    if caminho.is_dir():
        return sorted(arquivo for arquivo in caminho.glob("*.csv") if arquivo.is_file())
    raise ErroDados(f"Entrada inexistente ou sem suporte: {caminho}")


def _carregar_arquivo(arquivo: Path) -> pd.DataFrame:
    """Le um CSV e converte o schema externo para o schema interno."""

    try:
        dados = pd.read_csv(arquivo)
    except (OSError, UnicodeError, pd.errors.ParserError) as erro:
        raise ErroDados(f"Nao foi possivel ler {arquivo.name}: {erro}") from erro

    dados = dados.rename(columns={coluna: normalizar_texto(coluna) for coluna in dados.columns})
    dados = dados.rename(columns=COLUNAS_ESPERADAS)
    ausentes = sorted(COLUNAS_OBRIGATORIAS.difference(dados.columns))
    if ausentes:
        raise ErroDados(f"{arquivo.name} nao possui as colunas: {', '.join(ausentes)}")

    dados = dados[list(sorted(COLUNAS_OBRIGATORIAS))].copy()
    dados["data"] = pd.to_datetime(dados["data"], errors="coerce")
    dados["compradores"] = pd.to_numeric(dados["compradores"], errors="coerce")
    for coluna in ("comissao", "cashback", "vendas_totais"):
        dados[coluna] = _converter_moeda(dados[coluna])

    dados["arquivo_origem"] = arquivo.name
    dados["teste_id"] = criar_identificador(arquivo.stem)
    dados["parceiro"] = dados["parceiro"].astype("string").str.strip()
    dados["grupo"] = dados["grupo"].astype("string").str.strip()
    return dados


def carregar_dados(entrada: str | Path) -> pd.DataFrame:
    """Une os CSVs encontrados sem perder a origem de cada teste."""

    arquivos = _listar_arquivos(entrada)
    if not arquivos:
        raise ErroDados(f"Nenhum CSV encontrado em {entrada}")
    return pd.concat([_carregar_arquivo(arquivo) for arquivo in arquivos], ignore_index=True)


def validar_dados(dados: pd.DataFrame) -> pd.DataFrame:
    """Registra problemas de qualidade antes dos calculos."""

    alertas: list[dict[str, object]] = []
    colunas_chave = ["teste_id", "parceiro", "data", "grupo"]
    for (teste_id, parceiro), recorte in dados.groupby(["teste_id", "parceiro"], dropna=False):
        verificacoes = [
            (
                int(recorte[colunas_chave + COLUNAS_NUMERICAS].isna().any(axis=1).sum()),
                "critica",
                "valores_invalidos",
                "linha(s) possuem campos obrigatorios nulos ou invalidos.",
            ),
            (
                int(recorte.duplicated(["data", "grupo", "parceiro"], keep=False).sum()),
                "critica",
                "duplicidade",
                "linha(s) repetem a combinacao data, grupo e parceiro.",
            ),
            (
                int((recorte[COLUNAS_NUMERICAS] < 0).any(axis=1).sum()),
                "critica",
                "valor_negativo",
                "linha(s) possuem valores negativos.",
            ),
        ]
        for quantidade, severidade, tipo, mensagem in verificacoes:
            if quantidade:
                alertas.append({
                    "teste_id": teste_id,
                    "parceiro": parceiro,
                    "severidade": severidade,
                    "tipo": tipo,
                    "descricao": f"{quantidade} {mensagem}",
                })

        contagem_datas = recorte.groupby("grupo")["data"].nunique()
        if len(contagem_datas) > 1 and contagem_datas.min() != contagem_datas.max():
            alertas.append({
                "teste_id": teste_id,
                "parceiro": parceiro,
                "severidade": "atencao",
                "tipo": "datas_desbalanceadas",
                "descricao": "Os grupos possuem quantidades diferentes de datas observadas.",
            })

    colunas = ["teste_id", "parceiro", "severidade", "tipo", "descricao"]
    return pd.DataFrame(alertas, columns=colunas)


def preparar_dados(dados: pd.DataFrame) -> pd.DataFrame:
    """Mantem linhas validas e calcula os indicadores diarios."""

    colunas_chave = ["teste_id", "parceiro", "data", "grupo"]
    preparados = dados.dropna(subset=colunas_chave + COLUNAS_NUMERICAS).copy()
    preparados = preparados[(preparados[COLUNAS_NUMERICAS] >= 0).all(axis=1)]
    preparados = preparados[preparados["vendas_totais"] > 0]
    preparados = preparados.drop_duplicates(colunas_chave)
    preparados["margem"] = preparados["comissao"] - preparados["cashback"]
    preparados["taxa_comissao"] = preparados["comissao"] / preparados["vendas_totais"]
    preparados["taxa_cashback"] = preparados["cashback"] / preparados["vendas_totais"]
    preparados["taxa_margem"] = preparados["margem"] / preparados["vendas_totais"]
    preparados["ticket_medio"] = preparados["vendas_totais"] / preparados["compradores"].replace(0, pd.NA)
    return preparados.sort_values(colunas_chave).reset_index(drop=True)


def _montar_matriz_configuracao(recorte: pd.DataFrame) -> pd.DataFrame:
    """Representa as taxas de todos os grupos em cada data."""

    cashback = recorte.pivot_table(
        index="data",
        columns="grupo",
        values="taxa_cashback",
        aggfunc="median",
    ).sort_index()
    cashback.columns = [f"cashback__{coluna}" for coluna in cashback.columns]
    comissao = recorte.groupby("data")["taxa_comissao"].median().rename("comissao")
    return cashback.join(comissao).dropna().sort_index()


def _encontrar_limites(
    matriz: pd.DataFrame,
    configuracao: ConfiguracaoAnalise,
) -> list[int]:
    """Encontra mudancas que permanecem por varios dias."""

    quantidade = len(matriz)
    minimo = configuracao.minimo_dias_fase
    if quantidade < minimo * 2:
        return [0, quantidade]

    valores = matriz.to_numpy(dtype=float)
    limites = [0]
    inicio = 0
    indice = minimo
    tolerancias = np.array([
        configuracao.tolerancia_comissao if coluna == "comissao"
        else configuracao.tolerancia_cashback
        for coluna in matriz.columns
    ])

    while indice <= quantidade - minimo:
        referencia = np.nanmedian(valores[inicio:indice], axis=0)
        futuro = np.nanmedian(valores[indice : indice + minimo], axis=0)
        if np.any(np.abs(futuro - referencia) > tolerancias):
            limite_refinado = indice
            for candidato in range(indice, min(indice + minimo, quantidade)):
                distancia_referencia = np.nanmean(
                    np.abs(valores[candidato] - referencia) / tolerancias
                )
                distancia_futuro = np.nanmean(np.abs(valores[candidato] - futuro) / tolerancias)
                if distancia_futuro < distancia_referencia:
                    limite_refinado = candidato
                    break
            limites.append(limite_refinado)
            inicio = limite_refinado
            indice = limite_refinado + minimo
        else:
            indice += 1

    limites.append(quantidade)
    return sorted(set(limites))


def _resumir_fase(
    recorte: pd.DataFrame,
    fase_id: int,
    configuracao: ConfiguracaoAnalise,
) -> dict[str, object]:
    """Resume a configuracao e a duracao de uma fase."""

    taxas = recorte.groupby("grupo")["taxa_cashback"].median().sort_index().to_dict()
    valores = list(taxas.values())
    contraste = max(valores) - min(valores) if len(valores) > 1 else 0.0
    return {
        "teste_id": recorte["teste_id"].iloc[0],
        "parceiro": recorte["parceiro"].iloc[0],
        "fase_id": fase_id,
        "data_inicio": recorte["data"].min(),
        "data_fim": recorte["data"].max(),
        "dias": int(recorte["data"].nunique()),
        "quantidade_grupos": int(recorte["grupo"].nunique()),
        "taxa_comissao": float(recorte["comissao"].sum() / recorte["vendas_totais"].sum()),
        "contraste_cashback": contraste,
        "configuracao_cashback": "; ".join(
            f"{grupo}={taxa:.2%}" for grupo, taxa in taxas.items()
        ),
        "taxas_cashback_json": json.dumps(taxas, ensure_ascii=False),
        "status_fase": (
            "valida" if contraste > configuracao.tolerancia_cashback else "sem_contraste"
        ),
    }


def detectar_fases(
    dados: pd.DataFrame,
    configuracao: ConfiguracaoAnalise,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Detecta qualquer quantidade de fases e grupos."""

    partes: list[pd.DataFrame] = []
    resumos: list[dict[str, object]] = []
    for (_, _), recorte in dados.groupby(["teste_id", "parceiro"], sort=False):
        recorte = recorte.copy()
        matriz = _montar_matriz_configuracao(recorte)
        limites = _encontrar_limites(matriz, configuracao)
        recorte["fase_id"] = 1
        if not matriz.empty:
            for fase_id, indice in enumerate(limites[:-1], start=1):
                recorte.loc[recorte["data"] >= matriz.index[indice], "fase_id"] = fase_id
        for fase_id, fase in recorte.groupby("fase_id", sort=True):
            resumos.append(_resumir_fase(fase, int(fase_id), configuracao))
        partes.append(recorte)
    return pd.concat(partes, ignore_index=True), pd.DataFrame(resumos)


def resumir_variantes(
    dados: pd.DataFrame,
    configuracao: ConfiguracaoAnalise,
) -> pd.DataFrame:
    """Resume volumes, taxas e projecoes por fase e grupo."""

    resumo = dados.groupby(CHAVES_FASE + ["grupo"], as_index=False).agg(
        dias=("data", "nunique"),
        compradores=("compradores", "sum"),
        comissao=("comissao", "sum"),
        cashback=("cashback", "sum"),
        vendas_totais=("vendas_totais", "sum"),
        margem=("margem", "sum"),
        compradores_dia=("compradores", "mean"),
        vendas_dia=("vendas_totais", "mean"),
        margem_dia=("margem", "mean"),
    )
    resumo["taxa_comissao"] = resumo["comissao"] / resumo["vendas_totais"]
    resumo["taxa_cashback"] = resumo["cashback"] / resumo["vendas_totais"]
    resumo["taxa_margem"] = resumo["margem"] / resumo["vendas_totais"]
    resumo["ticket_medio"] = resumo["vendas_totais"] / resumo["compradores"].replace(0, pd.NA)
    resumo["margem_por_comprador"] = resumo["margem"] / resumo["compradores"].replace(0, pd.NA)
    quantidade_grupos = resumo.groupby(CHAVES_FASE)["grupo"].transform("nunique")
    resumo["projecao_margem_100_trafego"] = (
        resumo["margem_dia"] * quantidade_grupos * configuracao.dias_projecao
    )
    resumo["dias_projecao"] = configuracao.dias_projecao
    return resumo


def _intervalo_bootstrap(
    diferencas: np.ndarray,
    repeticoes: int,
    gerador: np.random.Generator,
) -> tuple[float, float]:
    """Estima o intervalo da diferenca media por reamostragem."""

    if len(diferencas) < 2:
        return float("nan"), float("nan")
    medias = np.empty(repeticoes, dtype=float)
    for inicio in range(0, repeticoes, 1_000):
        fim = min(inicio + 1_000, repeticoes)
        amostras = gerador.choice(diferencas, size=(fim - inicio, len(diferencas)), replace=True)
        medias[inicio:fim] = amostras.mean(axis=1)
    inferior, superior = np.quantile(medias, [0.025, 0.975])
    return float(inferior), float(superior)


def _valor_p_permutacao(
    diferencas: np.ndarray,
    repeticoes: int,
    gerador: np.random.Generator,
) -> float:
    """Calcula um valor p aproximado por inversao de sinais."""

    if len(diferencas) < 2:
        return float("nan")
    observado = abs(float(diferencas.mean()))
    extremos = 0
    realizados = 0
    while realizados < repeticoes:
        quantidade = min(1_000, repeticoes - realizados)
        sinais = gerador.choice(np.array([-1.0, 1.0]), size=(quantidade, len(diferencas)))
        extremos += int((np.abs((sinais * diferencas).mean(axis=1)) >= observado).sum())
        realizados += quantidade
    return float((extremos + 1) / (repeticoes + 1))


def comparar_variantes(
    dados: pd.DataFrame,
    configuracao: ConfiguracaoAnalise,
) -> pd.DataFrame:
    """Compara cada variante ao controle nos mesmos dias."""

    resultados: list[dict[str, object]] = []
    gerador = np.random.default_rng(configuracao.semente_aleatoria)
    for chaves, fase in dados.groupby(CHAVES_FASE, sort=False):
        grupos = sorted(fase["grupo"].dropna().unique())
        controle = configuracao.grupo_controle if configuracao.grupo_controle in grupos else grupos[0]
        dados_controle = fase[fase["grupo"] == controle].set_index("data")
        for variante in grupos:
            if variante == controle:
                continue
            dados_variante = fase[fase["grupo"] == variante].set_index("data")
            datas = dados_controle.index.intersection(dados_variante.index)
            for metrica in ("compradores", "vendas_totais", "margem"):
                valores_controle = dados_controle.loc[datas, metrica].astype(float)
                valores_variante = dados_variante.loc[datas, metrica].astype(float)
                diferencas = (valores_variante - valores_controle).to_numpy()
                inferior, superior = _intervalo_bootstrap(
                    diferencas, configuracao.repeticoes_bootstrap, gerador
                )
                media_controle = float(valores_controle.mean())
                media_variante = float(valores_variante.mean())
                resultados.append({
                    "teste_id": chaves[0],
                    "parceiro": chaves[1],
                    "fase_id": chaves[2],
                    "grupo_controle": controle,
                    "grupo_variante": variante,
                    "metrica": metrica,
                    "dias_pareados": len(datas),
                    "media_controle": media_controle,
                    "media_variante": media_variante,
                    "diferenca_media": float(diferencas.mean()),
                    "uplift_percentual": (
                        media_variante / media_controle - 1 if media_controle else float("nan")
                    ),
                    "limite_inferior_95": inferior,
                    "limite_superior_95": superior,
                    "valor_p_permutacao": _valor_p_permutacao(
                        diferencas, configuracao.repeticoes_permutacao, gerador
                    ),
                })
    colunas = [
        "teste_id", "parceiro", "fase_id", "grupo_controle", "grupo_variante",
        "metrica", "dias_pareados", "media_controle", "media_variante",
        "diferenca_media", "uplift_percentual", "limite_inferior_95",
        "limite_superior_95", "valor_p_permutacao",
    ]
    return pd.DataFrame(resultados, columns=colunas)


def calcular_economia_incremental(
    resumo: pd.DataFrame,
    configuracao: ConfiguracaoAnalise,
) -> pd.DataFrame:
    """Calcula custo incremental e crescimento para break-even."""

    resultados: list[dict[str, object]] = []
    for chaves, fase in resumo.groupby(CHAVES_FASE, sort=False):
        grupos = sorted(fase["grupo"].unique())
        controle = configuracao.grupo_controle if configuracao.grupo_controle in grupos else grupos[0]
        linha_controle = fase[fase["grupo"] == controle].iloc[0]
        for _, linha in fase[fase["grupo"] != controle].iterrows():
            delta_compradores = linha["compradores_dia"] - linha_controle["compradores_dia"]
            delta_cashback = linha["cashback"] / linha["dias"] - linha_controle["cashback"] / linha_controle["dias"]
            taxa_margem_variante = float(linha["taxa_margem"])
            resultados.append({
                "teste_id": chaves[0],
                "parceiro": chaves[1],
                "fase_id": chaves[2],
                "grupo_controle": controle,
                "grupo_variante": linha["grupo"],
                "delta_compradores_dia": delta_compradores,
                "delta_vendas_dia": linha["vendas_dia"] - linha_controle["vendas_dia"],
                "delta_cashback_dia": delta_cashback,
                "delta_margem_dia": linha["margem_dia"] - linha_controle["margem_dia"],
                "custo_cashback_por_comprador_incremental": (
                    delta_cashback / delta_compradores if delta_compradores > 0 else float("nan")
                ),
                "uplift_gmv_observado": linha["vendas_dia"] / linha_controle["vendas_dia"] - 1,
                "uplift_gmv_break_even": (
                    float(linha_controle["taxa_margem"] / taxa_margem_variante - 1)
                    if taxa_margem_variante > 0 else float("inf")
                ),
            })
    colunas = [
        "teste_id", "parceiro", "fase_id", "grupo_controle", "grupo_variante",
        "delta_compradores_dia", "delta_vendas_dia", "delta_cashback_dia",
        "delta_margem_dia", "custo_cashback_por_comprador_incremental",
        "uplift_gmv_observado", "uplift_gmv_break_even",
    ]
    return pd.DataFrame(resultados, columns=colunas)


def _formatar_moeda(valor: float) -> str:
    """Formata moeda para os textos do relatorio."""

    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def _possivel_desequilibrio(fase: pd.DataFrame) -> bool:
    """Sinaliza diferencas de volume que exigem dados de exposicao."""

    compradores = fase.set_index("grupo")["compradores_dia"]
    return bool(
        len(compradores) > 1
        and compradores.max() > 0
        and compradores.min() / compradores.max() < 0.80
    )


def tomar_decisoes(
    fases: pd.DataFrame,
    resumo: pd.DataFrame,
    comparacoes: pd.DataFrame,
    configuracao: ConfiguracaoAnalise,
) -> pd.DataFrame:
    """Aplica uma regra conservadora baseada em margem e qualidade."""

    decisoes: list[dict[str, object]] = []
    for (teste_id, parceiro), fases_teste in fases.groupby(["teste_id", "parceiro"], sort=False):
        quantidade_fases = int(fases_teste["fase_id"].nunique())
        fase_principal = fases_teste.sort_values("dias", ascending=False).iloc[0]
        fase_id = int(fase_principal["fase_id"])
        resumo_fase = resumo[
            (resumo["teste_id"] == teste_id)
            & (resumo["parceiro"] == parceiro)
            & (resumo["fase_id"] == fase_id)
        ].copy()
        grupos = sorted(resumo_fase["grupo"].unique())
        controle = configuracao.grupo_controle if configuracao.grupo_controle in grupos else grupos[0]
        melhor = resumo_fase.sort_values("margem_dia", ascending=False).iloc[0]
        melhor_grupo = str(melhor["grupo"])
        alertas = ["A projeção pressupõe tráfego equilibrado entre os grupos."]
        if _possivel_desequilibrio(resumo_fase):
            alertas.append("Confirme o número de usuários expostos em cada grupo.")

        if quantidade_fases > 1:
            status = "reexecutar"
            recomendada = "nenhuma"
            decisao = (
                "Não escalar automaticamente. O tratamento mudou durante o período; "
                "analise as fases e reexecute o teste com taxas fixas."
            )
        elif fase_principal["status_fase"] == "sem_contraste":
            status = "inconclusivo"
            recomendada = "nenhuma"
            decisao = "Não há contraste persistente de cashback entre os grupos."
        elif int(fase_principal["dias"]) < configuracao.minimo_dias_decisao:
            status = "inconclusivo"
            recomendada = "nenhuma"
            decisao = "A fase é curta demais para uma decisão automática confiável."
        elif melhor_grupo == controle:
            comparacoes_margem = comparacoes[
                (comparacoes["teste_id"] == teste_id)
                & (comparacoes["parceiro"] == parceiro)
                & (comparacoes["fase_id"] == fase_id)
                & (comparacoes["metrica"] == "margem")
            ]
            controle_superior = (
                len(comparacoes_margem) == len(grupos) - 1
                and (comparacoes_margem["limite_superior_95"] < 0).all()
            )
            status = "escalar" if controle_superior else "manter_controle"
            recomendada = controle
            decisao = (
                f"Escalar {controle}: apresentou a maior margem e as variantes ficaram "
                "abaixo do controle no intervalo de confiança."
                if controle_superior
                else f"Manter {controle} enquanto o resultado permanece inconclusivo."
            )
        else:
            comparacao = comparacoes[
                (comparacoes["teste_id"] == teste_id)
                & (comparacoes["parceiro"] == parceiro)
                & (comparacoes["fase_id"] == fase_id)
                & (comparacoes["grupo_variante"] == melhor_grupo)
                & (comparacoes["metrica"] == "margem")
            ]
            superior = not comparacao.empty and float(comparacao.iloc[0]["limite_inferior_95"]) > 0
            status = "escalar" if superior else "inconclusivo"
            recomendada = melhor_grupo if superior else controle
            decisao = (
                f"Escalar {melhor_grupo}: ganho de margem consistente contra o controle."
                if superior
                else f"Manter {controle}; a evidência ainda não é suficiente para escalar."
            )

        decisoes.append({
            "teste_id": teste_id,
            "parceiro": parceiro,
            "descricao": (
                f"Teste com {len(grupos)} grupo(s), {quantidade_fases} fase(s), de "
                f"{fases_teste['data_inicio'].min():%Y-%m-%d} a "
                f"{fases_teste['data_fim'].max():%Y-%m-%d}."
            ),
            "resultado": (
                f"Maior margem diária na fase principal: {melhor_grupo}, "
                f"{_formatar_moeda(float(melhor['margem_dia']))}; "
                f"GMV diário de {_formatar_moeda(float(melhor['vendas_dia']))}."
            ),
            "status": status,
            "variante_recomendada": recomendada,
            "decisao": decisao,
            "fase_principal": fase_id,
            "quantidade_fases": quantidade_fases,
            "alertas": " | ".join(alertas),
        })
    return pd.DataFrame(decisoes)
