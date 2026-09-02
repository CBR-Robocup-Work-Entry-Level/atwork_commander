"""Validacao da task gerada, antes de qualquer exportacao."""

from atwork.validation.schema import validar_estrutura
from atwork.validation.tests import validar_prova


def validar(task) -> list[str]:
    """Erros da task. Lista vazia = task valida e exportavel.

    Erro aqui e sempre bug do gerador, nunca limitacao da arena: o que a arena
    nao comporta ja saiu como desvio durante a geracao.
    """
    erros = validar_estrutura(task)
    if not erros:
        erros = validar_prova(task)
    return [f"[{task.prova}] {e}" for e in erros]


__all__ = ["validar", "validar_estrutura", "validar_prova"]
