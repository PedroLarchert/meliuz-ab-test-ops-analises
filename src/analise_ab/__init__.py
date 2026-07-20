"""Ferramentas para analise de testes A/B de cashback."""

from analise_ab.analise import ConfiguracaoAnalise


def executar_pipeline(*argumentos, **opcoes):
    """Carrega a orquestracao apenas quando a funcao publica for chamada."""

    from analise_ab.pipeline import executar_pipeline as _executar_pipeline

    return _executar_pipeline(*argumentos, **opcoes)

__all__ = ["ConfiguracaoAnalise", "executar_pipeline"]
