"""Excecoes do gerador."""

from __future__ import annotations


class GenerationError(Exception):
    """A arena montada nao comporta a prova pedida, ou o sorteio ficou inviavel.

    Reservada para o que nenhum ajuste de sorteio resolve (faltam areas, faltam
    cubos no inventario). Deficiencias que apenas *afastam* a task do previsto
    no rulebook nao levantam erro: viram desvios registrados na Task e
    impressos no guia do juiz.
    """
