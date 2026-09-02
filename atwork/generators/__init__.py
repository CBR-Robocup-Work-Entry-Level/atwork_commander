"""Registro dos geradores de prova.

Um modulo por prova, todos com a mesma interface (`bloqueios` e `gerar`), o que
deixa a GUI e a CLI genericas: elas so consultam o registro.
"""

from __future__ import annotations

from types import ModuleType

from atwork import rules
from atwork.arena.model import Metaarena
from atwork.core.task import Task
from atwork.generators import amt, att1, att2, bmt, btt1, btt2, final
from atwork.generators.base import Opcoes, nova_seed

REGISTRO: dict[str, ModuleType] = {
    "BMT": bmt,
    "BTT1": btt1,
    "BTT2": btt2,
    "AMT": amt,
    "ATT1": att1,
    "ATT2": att2,
    "FINAL": final,
}

__all__ = ["REGISTRO", "Opcoes", "bloqueios", "gerar", "nova_seed", "provas"]


def provas() -> tuple[str, ...]:
    return rules.PROVAS


def _modulo(prova: str) -> ModuleType:
    try:
        return REGISTRO[prova.upper()]
    except KeyError:
        raise KeyError(
            f"prova desconhecida: {prova!r} (validas: {', '.join(rules.PROVAS)})"
        ) from None


def bloqueios(meta: Metaarena, prova: str) -> list[str]:
    """O que impede gerar esta prova nesta arena. Lista vazia = pode gerar."""
    return _modulo(prova).bloqueios(meta)


def gerar(meta: Metaarena, prova: str, opcoes: Opcoes | None = None) -> Task:
    """Gera a task, valida o resultado e devolve o cenario pronto."""
    from atwork.validation import validar  # tardio: evita ciclo de import

    task = _modulo(prova).gerar(meta, opcoes)
    erros = validar(task)
    if erros:
        from atwork.core.errors import GenerationError

        raise GenerationError(
            f"a task {prova} gerada saiu invalida (bug no gerador):\n  - " + "\n  - ".join(erros)
        )
    return task
